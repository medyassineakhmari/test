
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, pandas_udf, struct
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType, FloatType, StructField
from pyspark.ml.feature import IndexToString
from pyspark.ml import PipelineModel
from pymongo import MongoClient
import json


BOOTSTRAP = (
    "kafka-broker-0.kafka-broker-service:19092,"
    "kafka-broker-1.kafka-broker-service:19092,"
    "kafka-broker-2.kafka-broker-service:19092"
)
TOPIC = "demo"

fields = [
    ("id", IntegerType()),
    ("rate", FloatType()),
    ("proto", StringType()),
    ("state", StringType()),
    ("dur", FloatType()),
    ("sbytes", IntegerType()),
    ("dbytes", IntegerType()),
    ("sttl", IntegerType()),
    ("dttl", IntegerType()),
    ("sloss", IntegerType()),
    ("dloss", IntegerType()),
    ("service", StringType()),
    ("sload", FloatType()),
    ("dload", FloatType()),
    ("spkts", IntegerType()),
    ("dpkts", IntegerType()),
    ("swin", IntegerType()),
    ("dwin", IntegerType()),
    ("stcpb", IntegerType()),
    ("dtcpb", IntegerType()),
    ("smean", IntegerType()),
    ("dmean", IntegerType()),
    ("trans_depth", IntegerType()),
    ("response_body_len", IntegerType()),
    ("sjit", FloatType()),
    ("djit", FloatType()),
    ("sinpkt", FloatType()),
    ("dinpkt", FloatType()),
    ("tcprtt", FloatType()),
    ("synack", FloatType()),
    ("ackdat", FloatType()),
    ("is_sm_ips_ports", IntegerType()),
    ("ct_state_ttl", IntegerType()),
    ("ct_flw_http_mthd", IntegerType()),
    ("is_ftp_login", IntegerType()),
    ("ct_ftp_cmd", IntegerType()),
    ("ct_srv_src", IntegerType()),
    ("ct_srv_dst", IntegerType()),
    ("ct_dst_ltm", IntegerType()),
    ("ct_src_ltm", IntegerType()),
    ("ct_src_dport_ltm", IntegerType()),
    ("ct_dst_sport_ltm", IntegerType()),
    ("ct_dst_src_ltm", IntegerType())
]
schema = StructType([StructField(name, dtype, True) for name, dtype in fields])

    

if __name__ == "__main__":
    # Spark session
    spark = (
        SparkSession.builder
        .appName("KafkaOrdersStream")
        .getOrCreate()
    )
    
    # load model
    pipelie_model = PipelineModel.load("models/pipeline_rf_v1")

    logs_raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "earliest")  # or earliest
        .load()
    )

    # parse the "value" column (which contains the message) as JSON
    logs_df = logs_raw.select(
        from_json(col("value").cast("string"), schema).alias("data"),
        "topic", "partition", "offset", "timestamp"
    ).select("data.*", "topic", "partition", "offset", "timestamp")

    # fill missing values
    logs_df = logs_df.fillna(0)

    # Apply trained pipeline model
    predictions_df = pipelie_model.transform(logs_df)

    converter = IndexToString(
        inputCol="prediction", 
        outputCol="prediction_label", 
        labels=pipelie_model.stages[0].labels # see the stages defined in pipeline of training
    )
    pred_with_labels = converter.transform(predictions_df)

    # Select only useful columns for output
    result_df = pred_with_labels.select(
    "prediction",
    "prediction_label",
    "probability",
    "topic",
    "partition",
    "offset",
    "timestamp"
    )

    # Define function to write batch to MongoDB using pymongo
    def write_to_mongodb(batch_df, batch_id):
        """Write batch dataframe to MongoDB using pymongo"""
        try:
            # Read MongoDB credentials from environment variables (injected from Sealed Secret)
            import os
            mongo_url = os.getenv('MONGO_URL', 'mongodb://admin:password@mongodb-service:27017/')
            client = MongoClient(mongo_url)
            db = client["cybersecurity_db"]
            collection = db["predictions"]
            
            # Convert Spark DataFrame to list of dicts and insert into MongoDB
            records = batch_df.toJSON().map(lambda x: json.loads(x)).collect()
            if records:
                collection.insert_many(records)
                print(f"✅ Batch {batch_id}: Successfully wrote {len(records)} predictions to MongoDB")
            else:
                print(f"⚠️  Batch {batch_id}: No records to write")
            
            client.close()
        except Exception as e:
            print(f"❌ Batch {batch_id}: Failed to write to MongoDB - {str(e)}")

    # Write to both console (for monitoring) and MongoDB (for storage)
    query = (
        result_df.writeStream
        .format("console")
        .outputMode("append")
        .option("truncate", False)
        .option("checkpointLocation", "/tmp/checkpoints/logs-stream")
        .foreachBatch(write_to_mongodb)
        .start()
    )

    query.awaitTermination()

