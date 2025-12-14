from pyspark.ml import Pipeline
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

# Download the UNSW-NB15 dataset, then adjust the path accordingly
path = '../CSV_Files/Training_and_Testing_Sets/UNSW_NB15_training-set.csv'  # path to your csv file

df = (spark.read
      .option("header", True)
      .option("inferSchema", True)   # ok pour commencer, en prod on met un schema explicite
      .csv(path))

feature_cols = [
    f.name for f in df.schema.fields
    if isinstance(f.dataType, NumericType)
    and f.name != "label"      # exclude target column
]

print(feature_cols)

imputer = Imputer(
    inputCols=feature_cols,
    outputCols=feature_cols
).setStrategy("mean")


assembler = VectorAssembler(
    inputCols=feature_cols,
    outputCol="features",
    handleInvalid="keep"
)

model = LogisticRegression(featuresCol="features", labelCol="label")

pipeline = Pipeline(stages=[imputer, assembler, model])

train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

pipeline_model = pipeline.fit(train_df)


pred_valid = pipeline_model.transform(test_df)

auc = BinaryClassificationEvaluator(
    labelCol="label",
    rawPredictionCol="rawPrediction",
    metricName="areaUnderROC"
).evaluate(pred_valid)
print("AUC =", auc)

# Save the whole thing (preprocess + model)
pipeline_model.write().overwrite().save("models/pipeline_lr_v1")