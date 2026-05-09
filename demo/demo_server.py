"""
========================================================
  ML MODEL DEMO — BACKEND SERVER (V5 / ml_ready_dataset)
  Proje : Türkiye Box-Office Seyirci Tahmin
========================================================

KURULUM:
  pip install flask flask-cors joblib scikit-learn numpy pandas

ÇALIŞTIRMA (proje kök klasöründen):
  python demo/demo_server.py
  → Tarayıcıda demo/demo_ui.html dosyasını aç (veya http://localhost:5000)

ÖN KOŞUL:
  demo/model.joblib       — notebooks/model_training_v5.ipynb Model Export
  demo/feature_names.json — aynı
"""

from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

MODEL_PATH = os.path.join(BASE_DIR, "model.joblib")
FEAT_PATH = os.path.join(BASE_DIR, "feature_names.json")
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "ml_ready_dataset.csv")

# boxofficeturkiye.com “Tüm yıl karşılaştırması” ile uyumlu özet (README tablosu)
PAZAR_BY_YEAR: dict[int, tuple[float, float]] = {
    2016: (58_287_772, 11.87),
    2017: (71_188_594, 12.23),
    2018: (70_409_779, 12.74),
    2019: (59_556_020, 16.46),
    2020: (17_415_304, 17.21),
    2021: (12_488_382, 22.87),
    2022: (36_198_982, 37.30),
    2023: (31_542_707, 89.66),
    2024: (33_149_053, 150.64),
    2025: (27_932_751, 208.18),
}

MODEL_INFO = {
    "model_name": "GradientBoostingRegressor (V5 — notebook seçimi)",
    "metric1_label": "Test R² (temporal, ≥2023)",
    "metric1_value": "0.4125",
    "metric2_label": "Test MedAPE",
    "metric2_value": "70.42%",
    "training_note": "Eğitim: Liste_Yili ≤2022 (1376 film) | Test: ≥2023 (600) | Hedef: log1p(seyirci)",
}

# Notebook export ile güncellenir; sunucuyu yeniden başlatınca UI’daki metrikler buna çeker.
_METRICS_PATH = os.path.join(BASE_DIR, "model_metrics.json")
if os.path.isfile(_METRICS_PATH):
    try:
        with open(_METRICS_PATH, encoding="utf-8") as _mf:
            _patch = json.load(_mf)
            for _k, _v in _patch.items():
                if _v is not None and str(_v).strip() != "":
                    MODEL_INFO[_k] = _v
        print(f"[demo_server] Gösterim metrikleri: {_METRICS_PATH}")
    except Exception as _ex:
        print(f"[demo_server] model_metrics.json okunamadı: {_ex}")

# Tür adı (UI) → sütun (ml_ready)
GENRE_TO_TUR: dict[str, str] = {
    "3 Boyutlu": "Tur_3_Boyutlu",
    "Bilim-Kurgu": "Tur_Bilim_Kurgu",
    "Romantik-Komedi": "Tur_Romantik_Komedi",
    "Gençlik": "Tur_Genclik",
    "Savaş": "Tur_Savas",
    "Suç": "Tur_Suc",
    "Müzikal": "Tur_Muzikal",
}


def _genre_list_from_features(feature_names: list[str]) -> list[str]:
    out = []
    for c in feature_names:
        if not c.startswith("Tur_"):
            continue
        rest = c[4:]
        inv = {v: k for k, v in GENRE_TO_TUR.items()}
        if c in inv:
            out.append(inv[c])
            continue
        label = rest.replace("_", " ")
        if rest == "Bilim_Kurgu":
            label = "Bilim-Kurgu"
        if rest == "Romantik_Komedi":
            label = "Romantik-Komedi"
        if rest == "3_Boyutlu":
            label = "3 Boyutlu"
        out.append(label)
    return sorted(out)


def _tur_column(genre_label: str) -> str:
    g = genre_label.strip()
    if g in GENRE_TO_TUR:
        return GENRE_TO_TUR[g]
    slug = g.replace(" ", "_").replace("-", "_")
    return "Tur_" + slug


def _mevsim(month: int) -> tuple[int, int, int, int]:
    """Ilkbahar, Kis, Sonbahar, Yaz — feature_engineering.py ile aynı mantık."""
    if month in (3, 4, 5):
        return 1, 0, 0, 0
    if month in (6, 7, 8):
        return 0, 0, 0, 1
    if month in (9, 10, 11):
        return 0, 0, 1, 0
    return 0, 1, 0, 0


def _pazar_for_year(y: int) -> tuple[float, float]:
    if y in PAZAR_BY_YEAR:
        return PAZAR_BY_YEAR[y]
    keys = sorted(PAZAR_BY_YEAR)
    if y < keys[0]:
        return PAZAR_BY_YEAR[keys[0]]
    if y > keys[-1]:
        return PAZAR_BY_YEAR[keys[-1]]
    lo = max(k for k in keys if k <= y)
    hi = min(k for k in keys if k >= y)
    if lo == hi:
        return PAZAR_BY_YEAR[lo]
    a0, p0 = PAZAR_BY_YEAR[lo]
    a1, p1 = PAZAR_BY_YEAR[hi]
    w = (y - lo) / (hi - lo)
    return a0 + w * (a1 - a0), p0 + w * (p1 - p0)


def _get_estimator(m):
    """Pipeline veya düz modelden tahmin ediciyi al."""
    if hasattr(m, "named_steps"):
        steps = list(m.named_steps.values())
        return steps[-1]
    return m


print(f"\n[demo_server] Model: {MODEL_PATH}")
try:
    model = joblib.load(MODEL_PATH)
    print(f"[demo_server] Yüklendi: {type(model).__name__}")
except FileNotFoundError:
    print("[demo_server] HATA: model.joblib yok — V5 notebook Model Export çalıştırın.")
    model = None

try:
    with open(FEAT_PATH, encoding="utf-8") as f:
        FEATURE_NAMES: list[str] | None = json.load(f)
    print(f"[demo_server] {len(FEATURE_NAMES)} özellik (feature_names.json).")
except FileNotFoundError:
    FEATURE_NAMES = None
    print("[demo_server] UYARI: feature_names.json yok.")

FEAT_MEDIANS: dict[str, float] = {}

if FEATURE_NAMES and os.path.isfile(DATA_PATH):
    try:
        df0 = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
        tr = df0[df0["Liste_Yili"] <= 2022]
        for col in FEATURE_NAMES:
            if col in tr.columns:
                med = tr[col].median()
                FEAT_MEDIANS[col] = float(med) if pd.notna(med) else 0.0
            else:
                FEAT_MEDIANS[col] = 0.0
        print(f"[demo_server] Eğitim medyanları: {DATA_PATH}")
    except Exception as ex:
        print(f"[demo_server] CSV okunamadı ({ex}); sabit varsayılanlar.")
        FEAT_MEDIANS = {c: 0.0 for c in (FEATURE_NAMES or [])}
elif FEATURE_NAMES:
    FEAT_MEDIANS = {c: 0.0 for c in FEATURE_NAMES}

GENRE_LABELS = _genre_list_from_features(FEATURE_NAMES or [])


def _float(raw: dict, key: str, median_key: str | None = None) -> float:
    median_key = median_key or key
    v = raw.get(key)
    if v is None or v == "":
        return FEAT_MEDIANS.get(median_key, 0.0)
    try:
        return float(v)
    except (TypeError, ValueError):
        return FEAT_MEDIANS.get(median_key, 0.0)


def build_feature_vector(raw: dict, feature_names: list[str]) -> np.ndarray:
    """V5 ml_ready sütun sırasına göre tek satır matris."""
    year = int(raw.get("release_year") or raw.get("liste_yili") or 2024)
    month = int(raw.get("release_month") or 6)
    genres = raw.get("genres") or []
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(",") if g.strip()]

    sektor, bilet = _pazar_for_year(year)
    ikb, kis, son, yaz = _mevsim(month)
    is_pan = 1 if year in (2020, 2021) else 0

    row: dict[str, float] = {k: float(FEAT_MEDIANS.get(k, 0.0)) for k in feature_names}

    row["Liste_Yili"] = float(year)
    row["Sure_Dakika"] = _float(raw, "runtime_minutes", "Sure_Dakika")

    imdb_yok = int(raw.get("imdb_yok", 0))
    row["IMDb_Yok"] = float(imdb_yok)
    if imdb_yok:
        row["IMDb_Puani"] = FEAT_MEDIANS.get("IMDb_Puani", 6.3)
    else:
        row["IMDb_Puani"] = _float(raw, "imdb_puani", "IMDb_Puani")

    row["Sektor_Toplam_Seyirci"] = float(sektor)
    row["Ort_Bilet_TL"] = float(bilet)
    row["Is_Pandemi"] = float(is_pan)
    row["Is_Yerli"] = float(int(raw.get("is_domestic", 0)))
    row["Is_Devam_Filmi"] = float(int(raw.get("is_sequel", 0)))
    row["Rekabet_Indeksi"] = float(int(raw.get("competition_index", FEAT_MEDIANS.get("Rekabet_Indeksi", 5))))

    row["Mevsim_Ilkbahar"] = float(ikb)
    row["Mevsim_Kis"] = float(kis)
    row["Mevsim_Sonbahar"] = float(son)
    row["Mevsim_Yaz"] = float(yaz)

    # İsteğe bağlı sıralı / dağıtıcı skorları — boşsa eğitim medyanı
    row["Yonetmen_Skor"] = _float(raw, "yonetmen_skor", "Yonetmen_Skor")
    row["Yonetmen_Film_Sayisi"] = _float(raw, "yonetmen_film_sayisi", "Yonetmen_Film_Sayisi")
    row["Oyuncu1_Skor"] = _float(raw, "oyuncu1_skor", "Oyuncu1_Skor")
    row["Oyuncu2_Skor"] = _float(raw, "oyuncu2_skor", "Oyuncu2_Skor")
    row["Oyuncu3_Skor"] = _float(raw, "oyuncu3_skor", "Oyuncu3_Skor")
    row["Kadro_Veri_Var"] = _float(raw, "kadro_veri_var", "Kadro_Veri_Var")
    row["Dagitimci_Skor"] = _float(raw, "dagitimci_skor", "Dagitimci_Skor")

    for c in feature_names:
        if c.startswith("Tur_"):
            row[c] = 0.0
    for g in genres:
        col = _tur_column(g)
        if col in row:
            row[col] = 1.0

    vec = np.array([[row[n] for n in feature_names]], dtype=float)
    return vec


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "demo_ui.html")


@app.route("/config")
def get_config():
    return jsonify({
        "model_type": "regression",
        "model_info": MODEL_INFO,
        "model_ready": model is not None and FEATURE_NAMES is not None,
        "genres": GENRE_LABELS,
        "target_label": "Tahmini Seyirci Sayısı",
        "target_unit": "kişi",
        "feature_count": len(FEATURE_NAMES) if FEATURE_NAMES else 0,
        "train_films": 1376,
        "test_films": 600,
    })


@app.route("/test_set_presets")
def test_set_presets():
    path = os.path.join(BASE_DIR, "test_set_presets.json")
    if not os.path.isfile(path):
        return jsonify([])
    try:
        with open(path, encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "model.joblib yok. V5 notebook Model Export çalıştırın."}), 500
    if FEATURE_NAMES is None:
        return jsonify({"error": "feature_names.json yok."}), 500

    data = request.get_json()
    if not data or "features" not in data:
        return jsonify({"error": "İstek 'features' içermelidir."}), 400

    raw = data["features"]
    try:
        X = build_feature_vector(raw, FEATURE_NAMES)
    except Exception as e:
        return jsonify({"error": f"Özellik vektörü: {e}"}), 400

    try:
        pred_log = float(model.predict(X)[0])
        pred_orig = int(max(0.0, round(np.expm1(pred_log))))
    except Exception as e:
        return jsonify({"error": f"Tahmin başarısız: {e}"}), 500

    result = {
        "prediction": pred_orig,
        "prediction_log": round(pred_log, 4),
        "target_label": "Tahmini Seyirci Sayısı",
        "target_unit": "kişi",
        "prediction_low": int(max(0.0, round(np.expm1(pred_log - 0.5)))),
        "prediction_high": int(max(0.0, round(np.expm1(pred_log + 0.5)))),
    }

    est = _get_estimator(model)
    if hasattr(est, "feature_importances_"):
        imp = est.feature_importances_
        top = sorted(zip(FEATURE_NAMES, imp), key=lambda x: x[1], reverse=True)[:10]
        s = float(np.sum(imp)) or 1.0
        result["top_features"] = [
            {"name": n, "importance": round(float(v) / s, 4)} for n, v in top
        ]

    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "features": len(FEATURE_NAMES) if FEATURE_NAMES else 0,
    })


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Türkiye Box-Office — ML Demo (V5)")
    print("  http://localhost:5000")
    print("=" * 55 + "\n")
    app.run(debug=False, port=5000, host="0.0.0.0")
