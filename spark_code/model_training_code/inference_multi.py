from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import VectorAssembler, Imputer
from pyspark.sql.types import NumericType

# from spark_ml.drop_column import DropColumns
from pyspark.sql import SparkSession
from pyspark.ml.classification import LogisticRegression
from pyspark.sql.functions import col
from pyspark.ml.evaluation import BinaryClassificationEvaluator

spark = SparkSession.builder \
    .appName("spark-ml-test") \
    .master("local[*]") \
    .getOrCreate()


# dropper = DropColumns(cols=["id", "proto", "state", "service", "attack_cat"])


print("Spark ML is ready")

path = 'mini_sample.csv'

df_test = (spark.read
      .option("header", True)
      .option("inferSchema", True)   # ok pour commencer, en prod on met un schema explicite
      .csv(path))

# cast colonne rate en double
df_test = df_test.withColumn("rate", col("rate").cast("double"))


# df_test = df_test.fillna({"rate": 0.0})

df_test.show(10)

model = PipelineModel.load("models/pipeline_rf_v1")

pred = model.transform(df_test)

pred.select("prediction", "probability").show(20, truncate=False)

pred.groupBy("prediction").count().show()