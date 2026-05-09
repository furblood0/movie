"""
save_model.py  — V4
====================
Notebook açmadan modeli sıfırdan eğitip demo/ klasörüne kaydeder.

Çalıştırma (proje kökünden veya demo/ klasöründen):
    python demo/save_model.py
"""

import json
import os
import sys

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PATH    = os.path.join(PROJECT_ROOT, "data", "processed", "movie_data_v2.csv")

print("=" * 55)
print("  Box-Office Demo V4 — Model Eğitim & Kayıt")
print("=" * 55)

# ── 1. Load data ───────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"\n[1/7] Veri yüklendi: {len(df)} film, {df.shape[1]} sütun")

# ── 2. Genre multi-hot encoding ────────────────────────────────────────────────
all_genres = sorted({
    t.strip()
    for g in df["genre"]
    for t in str(g).split(",")
    if t.strip() and t.strip() != "Bilinmiyor"
})
make_col = lambda g: "is_genre_" + g.lower().replace(" ", "_").replace("-", "_")
for g in all_genres:
    df[make_col(g)] = df["genre"].apply(
        lambda x: 1 if g in [t.strip() for t in str(x).split(",")] else 0
    )
print(f"[2/7] Genre encoding: {len(all_genres)} tür → {len(all_genres)} binary sütun")

# ── 3. Temporal split ──────────────────────────────────────────────────────────
df_sorted  = df.sort_values("release_year").reset_index(drop=True)
train_mask = df_sorted["release_year"] <= 2022
train_df   = df_sorted[train_mask].copy()
test_df    = df_sorted[~train_mask].copy()
print(f"[3/7] Temporal split: train={len(train_df)}, test={len(test_df)}")

# ── 4. Distributor target encoding (train-only) ────────────────────────────────
grp           = train_df.groupby("distributor")
dist_power    = grp["log_total_audience"].mean()
dist_std      = grp["log_total_audience"].std().fillna(0)
dist_count    = train_df["distributor"].value_counts()
dist_domestic = grp["is_domestic"].mean()

fb_power    = float(train_df["log_total_audience"].mean())
fb_std      = float(dist_std.mean())
fb_count    = int(dist_count.median())
fb_domestic = float(dist_domestic.median())

for split in [train_df, test_df]:
    split["distributor_power"]          = split["distributor"].map(dist_power).fillna(fb_power)
    split["distributor_std"]            = split["distributor"].map(dist_std).fillna(fb_std)
    split["distributor_film_count"]     = split["distributor"].map(dist_count).fillna(fb_count).astype(int)
    split["distributor_domestic_ratio"] = split["distributor"].map(dist_domestic).fillna(fb_domestic)
print(f"[4/6] Dağıtıcı encoding tamamlandı")

# ── 5. OHE ─────────────────────────────────────────────────────────────────────
DROP = ["movie_name", "genre", "holiday_week", "release_week", "total_audience", "log_total_audience", "distributor"]
OHE  = ["release_season", "holiday_type"]

X_train = pd.get_dummies(train_df.drop(DROP, axis=1, errors="ignore"), columns=OHE)
X_test  = pd.get_dummies(test_df.drop(DROP,  axis=1, errors="ignore"), columns=OHE)
X_test  = X_test.reindex(columns=X_train.columns, fill_value=0)

y_train = train_df["log_total_audience"].values
y_test  = test_df["log_total_audience"].values
feature_names = X_train.columns.tolist()

print(f"[5/6] OHE tamamlandı: {len(feature_names)} feature")

# ── 7. LightGBM eğitimi ────────────────────────────────────────────────────────
print("[6/6] LightGBM eğitiliyor...")

lgbm = lgb.LGBMRegressor(
    n_estimators=300,
    learning_rate=0.05,
    num_leaves=5,          # best from grid search (4-fold TimeSeriesSplit CV)
    min_child_samples=30,
    reg_alpha=0.05,
    reg_lambda=2.0,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1,
)
lgbm.fit(X_train.values, y_train)
best_iter = 300

r2_train = r2_score(y_train, lgbm.predict(X_train.values))
r2_test  = r2_score(y_test,  lgbm.predict(X_test.values))
print(f"      Train R²: {r2_train:.4f}  |  Test R²: {r2_test:.4f}  (best_iter={best_iter})")

# ── Kaydet ────────────────────────────────────────────────────────────────────
os.makedirs(SCRIPT_DIR, exist_ok=True)

joblib.dump(lgbm, os.path.join(SCRIPT_DIR, "model.joblib"))

with open(os.path.join(SCRIPT_DIR, "feature_names.json"), "w", encoding="utf-8") as f:
    json.dump(feature_names, f, ensure_ascii=False, indent=2)

dist_enc = {
    "power":          dist_power.to_dict(),
    "std":            dist_std.to_dict(),
    "fallback_power": fb_power,
    "fallback_std":   fb_std,
}
with open(os.path.join(SCRIPT_DIR, "dist_encoding.json"), "w", encoding="utf-8") as f:
    json.dump(dist_enc, f, ensure_ascii=False, indent=2)

print(f"\nDosyalar kaydedildi → {SCRIPT_DIR}/")
print("  model.joblib")
print(f"  feature_names.json  ({len(feature_names)} özellik)")
print("  dist_encoding.json")
print("\nDemo sunucuyu başlatmak için:")
print("  python demo_server.py")
