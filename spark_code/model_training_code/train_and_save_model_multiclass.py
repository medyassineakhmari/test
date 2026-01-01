from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, Imputer, StringIndexer
from pyspark.sql.types import NumericType

# from spark_ml.drop_column import DropColumns
from pyspark.sql import SparkSession
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.sql.functions import col
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql import functions as F

spark = SparkSession.builder \
    .appName("spark-ml-test") \
    .master("local[*]") \
    .config("spark.driver.memory", "8g") \
    .config("spark.driver.memoryOverhead", "2g") \
    .getOrCreate()


# dropper = DropColumns(cols=["id", "proto", "state", "service", "attack_cat"])


print("Spark ML is ready")

path = '../CSV_Files/Training_and_Testing_Sets/UNSW_NB15_training-set.csv'

df = (spark.read
      .option("header", True)
      .option("inferSchema", True)   # ok pour commencer, en prod on met un schema explicite
      .csv(path))

# cast the attack_cat column to string
df = df.withColumn("label", F.col("attack_cat").cast("string"))



# --- 1) Label encoding (string -> numeric) ---
# here we convert attack_cat to label_index
label_indexer = StringIndexer(
    inputCol= "attack_cat",
    outputCol="label_index",
    handleInvalid="keep"   # important if streaming / missing labels
)

df_indexed = label_indexer.fit(df).transform(df)
df_indexed.select("label", "label_index").show(40, truncate=False)
df_indexed.groupBy("label", "label_index").count().orderBy("label_index").show()

excluded_cols = ["label", "label_index", "id"]

numeric_cols = [
    f.name for f in df.schema.fields
    if isinstance(f.dataType, NumericType)  # exclude non-numeric columns
    and f.name not in excluded_cols     # exclude target column
]
print(numeric_cols)

cat_cols = ["proto", "state", "service"]
cat_cols_indexed = ["proto_index", "state_index", "service_index"]

feature_indexer = StringIndexer(
    inputCols=cat_cols,
    outputCols=cat_cols_indexed,
    handleInvalid="keep"
)

imputer = Imputer(
    inputCols=numeric_cols,
    outputCols=numeric_cols
).setStrategy("mean")


assembler = VectorAssembler(
    inputCols=numeric_cols + cat_cols_indexed,
    outputCol="features",
    handleInvalid="keep"
)

# Option B: RandomForest (works well without scaling)
clf = RandomForestClassifier(
    featuresCol="features",
    labelCol="label_index",
    numTrees=50,
    maxDepth=6,
    maxBins=256,
    featureSubsetStrategy="sqrt",
    subsamplingRate=0.7
)

pipeline = Pipeline(stages=[label_indexer, feature_indexer, imputer, assembler, clf])

train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

pipeline_model = pipeline.fit(train_df)
pred_valid = pipeline_model.transform(test_df)

# --- 6) Evaluate (multi-class) ---
evaluator_acc = MulticlassClassificationEvaluator(
    labelCol="label_index", predictionCol="prediction", metricName="accuracy"
)
evaluator_f1 = MulticlassClassificationEvaluator(
    labelCol="label_index", predictionCol="prediction", metricName="f1"
)

acc = evaluator_acc.evaluate(pred_valid)
f1 = evaluator_f1.evaluate(pred_valid)

print("accuracy =", acc)
print("f1 =", f1)

# Save the whole thing (preprocess + model)
pipeline_model.write().overwrite().save("models/pipeline_rf_v1")