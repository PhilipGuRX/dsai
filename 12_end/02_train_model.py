# 02_train_model.py
# XGBoost regressor: Brussels (metro_id) vehicle_count ~ day_of_week + hour_of_day
# Uses rows from data/traffic.db when available; augments with synthetic data if needed.
# Saves XGBoost JSON to data/modelpy.json (run 03_serve_model.py to serve).
# Tim Fraser
#
# Run from 12_end/:  python3 02_train_model.py
#
# macOS: if XGBoost fails to load libomp, run:  brew install libomp
# (GitHub Actions Ubuntu image already has OpenMP.)

# 0. SETUP ###################################

import sqlite3  # for reading traffic.db
import warnings  # to keep XGBoost output readable

import numpy as np  # for noise and RMSE
import pandas as pd  # for training tables
import xgboost as xgb  # for gradient boosted trees
from pathlib import Path  # for paths
from sklearn.metrics import mean_squared_error  # for RMSE
from sklearn.model_selection import train_test_split  # for holdout RMSE

warnings.filterwarnings("ignore", category=UserWarning)

## 0.1 Configuration #################################

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# TomTom / course metro id for Brussels
METRO_ID = 948

OUT_PATH = DATA_DIR / "modelpy.json"
DB_PATH = DATA_DIR / "traffic.db"
RNG = np.random.default_rng(42)

# 1. BUILD TRAINING DATA ###################################


def _rows_from_sqlite():
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["day_of_week", "hour_of_day", "vehicle_count"])
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(
            "SELECT ingested_at, free_flow_speed, current_speed FROM traffic WHERE metro_id = ?",
            con,
            params=(METRO_ID,),
        )
    finally:
        con.close()
    if len(df) == 0:
        return pd.DataFrame(columns=["day_of_week", "hour_of_day", "vehicle_count"])
    ts = pd.to_datetime(df["ingested_at"], utc=True)
    # Monday = 1 … Sunday = 7 (match course convention)
    dow = ts.dt.dayofweek.to_numpy() + 1
    hod = ts.dt.hour.to_numpy()
    gap = (pd.to_numeric(df["free_flow_speed"], errors="coerce") - pd.to_numeric(df["current_speed"], errors="coerce")).fillna(0.0)
    # Synthetic vehicle_count: interpretable function of time + congestion gap + noise
    noise = RNG.normal(0.0, 45.0, size=len(df))
    vc = 1000.0 + 85.0 * dow + 12.5 * hod + 4.5 * gap.to_numpy() + noise
    return pd.DataFrame({"day_of_week": dow, "hour_of_day": hod, "vehicle_count": vc})


def _synthetic_grid(n_target=400):
    """Ensure enough rows for stable tree fitting."""
    rows = []
    for _ in range(n_target):
        dow = int(RNG.integers(1, 8))
        hod = int(RNG.integers(0, 24))
        noise = float(RNG.normal(0.0, 48.0))
        vc = 1200.0 + 95.0 * dow + 14.0 * hod + noise
        rows.append({"day_of_week": dow, "hour_of_day": hod, "vehicle_count": vc})
    return pd.DataFrame(rows)


def build_training_frame():
    real = _rows_from_sqlite()
    syn = _synthetic_grid(max(400, 500 - len(real)))
    combined = pd.concat([real, syn], ignore_index=True)
    return combined


# 2. TRAIN AND SAVE ###################################

df = build_training_frame()
feature_cols = ["day_of_week", "hour_of_day"]
X = df[feature_cols].astype(float)
y = df["vehicle_count"].astype(float)

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_cols)

params = {
    "objective": "reg:squarederror",
    "max_depth": 4,
    "eta": 0.08,
    "subsample": 0.9,
    "seed": 42,
}
booster = xgb.train(
    params,
    dtrain,
    num_boost_round=80,
    verbose_eval=False,
)

y_hat = booster.predict(dval)
rmse = float(np.sqrt(mean_squared_error(y_val, y_hat)))
print(f"Model saved to {OUT_PATH}")
print(f"Training RMSE: {rmse:.2f}")

booster.save_model(str(OUT_PATH))
print(f"metro_id={METRO_ID} (Brussels); features={feature_cols}")
