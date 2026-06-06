from __future__ import annotations

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator

from app.db import get_db
from app.repository import Repository

FEATURES = ["lag1", "lag2", "lag3", "sma3"]


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("acme-dwh-ml")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def build_features(df):
    w = Window.orderBy("observation_date")
    return (
        df.withColumn("lag1", F.lag("close", 1).over(w))
        .withColumn("lag2", F.lag("close", 2).over(w))
        .withColumn("lag3", F.lag("close", 3).over(w))
        .withColumn("sma3", F.avg("close").over(w.rowsBetween(-3, -1)))
        .dropna()
    )


def train_model(spark, rows):
    df = spark.createDataFrame(rows, ["observation_date", "close"])
    feats = build_features(df)
    assembler = VectorAssembler(inputCols=FEATURES, outputCol="features")
    lr = LinearRegression(featuresCol="features", labelCol="close")
    model = Pipeline(stages=[assembler, lr]).fit(feats)
    predictions = model.transform(feats)
    rmse = RegressionEvaluator(
        labelCol="close", predictionCol="prediction", metricName="rmse"
    ).evaluate(predictions)
    return model, feats.count(), rmse


def forecast_next(spark, model, closes):
    recent = closes[-3:]
    row = [(float(closes[-1]), float(closes[-2]), float(closes[-3]), sum(recent) / 3.0)]
    ndf = spark.createDataFrame(row, FEATURES)
    return float(model.transform(ndf).first()["prediction"])


def analyze_asset_ml(spark, repo, asset_id, source_id):
    points = repo.get_timeseries(asset_id, source_id)
    rows = [
        (p["observation_date"], float(p["indicators"]["close"]))
        for p in points
        if "close" in p.get("indicators", {})
    ]
    if len(rows) < 6:
        return {"asset_id": asset_id, "error": "not enough data to train"}
    model, n_train, rmse = train_model(spark, rows)
    closes = [c for _, c in rows]
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "model": "LinearRegression",
        "features": FEATURES,
        "n_train": n_train,
        "rmse": round(rmse, 4),
        "last_close": closes[-1],
        "predicted_next_close": round(forecast_next(spark, model, closes), 4),
    }


def run():
    spark = get_spark()
    repo = Repository(get_db())
    for asset in repo.list_assets():
        result = analyze_asset_ml(spark, repo, asset["asset_id"], asset["source_id"])
        print(result)
    spark.stop()


if __name__ == "__main__":
    run()