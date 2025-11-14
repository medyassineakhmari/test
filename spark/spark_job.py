from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType, FloatType

spark = (SparkSession.builder.appName("KafkaUNSWStream").getOrCreate())

TOPIC = "demo"
BOOTSTRAP = (
    "kafka-broker-0.kafka-broker-service:19092,"
    "kafka-broker-1.kafka-broker-service:19092,"
    "kafka-broker-2.kafka-broker-service:19092"
)

logs_raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", BOOTSTRAP)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "earliest")
    .option("failOnDataLoss", "false")
    .option("maxOffsetsPerTrigger", "5000")
    .load()
)

logs_str = logs_raw.selectExpr(
    "CAST(value AS STRING) as json_str",
    "topic", "partition", "offset", "timestamp"
)

schema = (
    StructType()
    # only keep fields that are in your JSON
    .add("dur", FloatType())
    .add("proto", StringType())
    .add("service", StringType())
    .add("state", StringType())
    .add("spkts", IntegerType())
    .add("dpkts", IntegerType())
    .add("sbytes", IntegerType())
    .add("dbytes", IntegerType())
    .add("rate", FloatType())           # To verify if it is sent by the producer
    .add("sttl", IntegerType())
    .add("dttl", IntegerType())
    .add("sload", FloatType())
    .add("dload", FloatType())
    .add("sloss", IntegerType())
    .add("dloss", IntegerType())
    .add("sinpkt", FloatType())
    .add("dinpkt", FloatType())
    .add("sjit", FloatType())
    .add("djit", FloatType())
    .add("swin", IntegerType())
    .add("stcpb", IntegerType())
    .add("dtcpb", IntegerType())
    .add("dwin", IntegerType())
    .add("tcprtt", FloatType())
    .add("synack", FloatType())
    .add("ackdat", FloatType())
    .add("smean", IntegerType())
    .add("dmean", IntegerType())
    .add("trans_depth", IntegerType())
    .add("response_body_len", IntegerType())
    .add("ct_srv_src", IntegerType())
    .add("ct_state_ttl", IntegerType())
    .add("ct_dst_ltm", IntegerType())
    .add("ct_src_dport_ltm", IntegerType())
    .add("ct_dst_sport_ltm", IntegerType())
    .add("ct_dst_src_ltm", IntegerType())
    .add("is_ftp_login", IntegerType())
    .add("ct_ftp_cmd", IntegerType())
    .add("ct_flw_http_mthd", IntegerType())
    .add("ct_src_ltm", IntegerType())
    .add("ct_srv_dst", IntegerType())
    .add("is_sm_ips_ports", IntegerType())
)


logs = logs_str.select(
    from_json(col("json_str"), schema).alias("data"),
    "topic", "partition", "offset", "timestamp"
).select(
    col("data.*"),
    "topic", "partition", "offset", "timestamp"
)

query = (
    logs.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", False)
    .option("checkpointLocation", "file:/mnt/checkpoints/logs-stream")  # <-- mets un chemin persistant
    .trigger(processingTime="5 seconds")
    .start()
)

query.awaitTermination()
