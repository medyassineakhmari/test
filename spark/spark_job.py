
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType

# 1️⃣ Create Spark session
spark = (
    SparkSession.builder
    .appName("KafkaOrdersStream")
    .getOrCreate()
)


topics_name = "demo"

orders_raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka-broker-0.kafka-broker-service:19092")
    .option("subscribe", topics_name)
    .option("startingOffsets", "earliest")  # or earliest
    .load()
)


orders_str = orders_raw.selectExpr(
    "CAST(value AS STRING) as json_str",
    "topic", "partition", "offset", "timestamp"
)


schema = (
    StructType()
    .add("order_id", StringType())
    .add("amount", DoubleType())
)


orders = orders_str.select(
    from_json(col("json_str"), schema).alias("data"),
    "topic", "partition", "offset", "timestamp"
).select(
    col("data.order_id"),
    col("data.amount"),
    col("timestamp"),
    col("topic"),
    col("partition"),
    col("offset")
)


query = (
    orders.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", False)
    .option("checkpointLocation", "/tmp/checkpoints/orders-stream")  # shared folder or local
    .start()
)

query.awaitTermination()