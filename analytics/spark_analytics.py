from __future__ import annotations


def run_with_connector() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.appName("acme-dwh-analytics")
        .config("spark.mongodb.read.connection.uri", "mongodb://localhost:27017")
        .config("spark.mongodb.read.database", "acme_dwh")
        .config("spark.mongodb.read.collection", "time_series")
        .getOrCreate()
    )

    df = spark.read.format("mongodb").load()
    df = df.withColumn("close", F.col("indicators.close"))

    (
        df.groupBy("asset_id", "source_id")
        .agg(
            F.count("*").alias("n"),
            F.min("close").alias("min_close"),
            F.max("close").alias("max_close"),
            F.round(F.avg("close"), 4).alias("avg_close"),
            F.round(F.stddev("close"), 4).alias("stddev_close"),
        )
        .show(truncate=False)
    )
    spark.stop()


def run_fallback() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    from app.db import get_db
    from app.repository import Repository

    repo = Repository(get_db())
    rows = []
    for asset in repo.list_assets():
        for p in repo.get_timeseries(asset["asset_id"], asset["source_id"]):
            rows.append(
                (asset["asset_id"], asset["source_id"], float(p["indicators"]["close"]))
            )

    spark = SparkSession.builder.appName("acme-dwh-analytics-fallback").getOrCreate()
    df = spark.createDataFrame(rows, ["asset_id", "source_id", "close"])
    (
        df.groupBy("asset_id", "source_id")
        .agg(
            F.count("*").alias("n"),
            F.round(F.avg("close"), 4).alias("avg_close"),
            F.round(F.stddev("close"), 4).alias("stddev_close"),
        )
        .show(truncate=False)
    )
    spark.stop()


if __name__ == "__main__":
    try:
        run_with_connector()
    except Exception as exc:  # connector jar missing, etc.
        print(f"Connector path failed ({exc}); using repository fallback.\n")
        run_fallback()
