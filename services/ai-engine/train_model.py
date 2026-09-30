import json
import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    root_mean_squared_error,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "services" / "traffic-monitoring" / "data" / "historical_traffic.csv"
MODEL_DIR = Path(__file__).resolve().parent / "app"
MODEL_PATH = MODEL_DIR / "model.joblib"
MODEL_CARD_PATH = MODEL_DIR / "model_card.json"


def load_and_prep_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Historical traffic data not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    # Parse datetime features
    df["dt"] = pd.to_datetime(df["recorded_at"])
    df["hour"] = df["dt"].dt.hour
    df["day_of_week"] = df["dt"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Compute ground truth delay in minutes (assuming base speed is free-flow 60 km/h for a standard 5km segment)
    # base_time = (5.0 / 60) * 60 = 5.0 mins
    # actual_time = (5.0 / average_speed) * 60
    base_mins = (5.0 / 60.0) * 60.0
    actual_mins = (5.0 / np.maximum(df["average_speed"], 5.0)) * 60.0
    df["delay_minutes"] = np.maximum(0.0, actual_mins - base_mins).round(2)

    return df


def train_models():
    print(f"Loading training data from {DATA_PATH}...")
    df = load_and_prep_data()
    print(f"Loaded {len(df)} records. Training features and labels...")

    feature_cols = ["road_id", "hour", "day_of_week", "is_weekend", "vehicle_count", "average_speed", "density"]
    X = df[feature_cols]
    y_class = df["congestion_level"]
    y_reg = df["delay_minutes"]

    categorical_features = ["road_id"]
    numeric_features = ["hour", "day_of_week", "is_weekend", "vehicle_count", "average_speed", "density"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    # 1. Train Classifier for Congestion Level
    clf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)),
    ])

    # 2. Train Regressor for Delay Minutes
    reg_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)),
    ])

    X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
        X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class
    )

    print("Fitting Congestion Classifier...")
    clf_pipeline.fit(X_train, y_class_train)
    y_pred_class = clf_pipeline.predict(X_test)
    acc = accuracy_score(y_class_test, y_pred_class)
    report = classification_report(y_class_test, y_pred_class, output_dict=True)
    print(f"Congestion Classifier Accuracy: {acc * 100:.2f}%")

    print("Fitting Delay Regressor...")
    reg_pipeline.fit(X_train, y_reg_train)
    y_pred_reg = reg_pipeline.predict(X_test)
    mae = mean_absolute_error(y_reg_test, y_pred_reg)
    rmse = root_mean_squared_error(y_reg_test, y_pred_reg)
    print(f"Delay Regressor MAE: {mae:.2f} mins, RMSE: {rmse:.2f} mins")

    # Save artifacts
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "model_version": "model-v2-rf",
        "classifier": clf_pipeline,
        "regressor": reg_pipeline,
        "classes": list(clf_pipeline.named_steps["classifier"].classes_),
        "feature_names": feature_cols,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "accuracy": round(float(acc), 4),
            "mae_minutes": round(float(mae), 4),
            "rmse_minutes": round(float(rmse), 4),
        },
    }

    joblib.dump(artifacts, MODEL_PATH)
    print(f"Saved trained model artifacts to {MODEL_PATH}")

    # Save Model Card
    model_card = {
        "model_name": "TrafficVision AI Congestion & Delay Predictor",
        "model_version": "model-v2-rf",
        "framework": "scikit-learn RandomForest",
        "trained_at": artifacts["trained_at"],
        "dataset_records": len(df),
        "features": feature_cols,
        "target_congestion_levels": artifacts["classes"],
        "metrics": {
            "test_accuracy": round(float(acc), 4),
            "mae_delay_minutes": round(float(mae), 4),
            "rmse_delay_minutes": round(float(rmse), 4),
        },
        "classification_summary": {
            k: v for k, v in report.items() if isinstance(v, dict)
        },
        "notes": "Trained on multi-week historical traffic telemetry across all monitored network corridors.",
    }

    with open(MODEL_CARD_PATH, "w", encoding="utf-8") as f:
        json.dump(model_card, f, indent=2)
    print(f"Saved model card to {MODEL_CARD_PATH}")

    return artifacts


if __name__ == "__main__":
    train_models()
