"""
create_clean_dataset.py
=======================
Ham veri setindeki sorunlu sütunları temizleyip movie_data_v2.csv oluşturur.

Kaldırılan sütunlar ve gerekçeleri:
  distributor_film_count   — Tam veri seti üzerinden önceden hesaplanmış → CSV'de
                             sızıntı riski. Pipeline zaten train-only olarak yeniden
                             hesaplıyor, CSV'deki halinin tutulması gereksiz/yanıltıcı.
  distributor_domestic_ratio — Aynı gerekçe.
  has_awards               — log_total_audience ile korelasyonu 0.050; modele
                             anlamlı katkı sağlamıyor, gürültü ekliyor.

NOT: release_week (-0.020 korelasyon) sütunu CSV'de bırakıldı çünkü ham verinin
bir parçası; model pipeline'ında DROP listesine alınarak zaten kullanılmıyor.
"""

import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC  = os.path.join(PROJECT_ROOT, "data", "processed", "llm_enriched_movie_data.csv")
DEST = os.path.join(PROJECT_ROOT, "data", "processed", "movie_data_v2.csv")

print("=" * 55)
print("  Veri Seti Temizleme -> movie_data_v2.csv")
print("=" * 55)

df = pd.read_csv(SRC, encoding="utf-8-sig")
print(f"\nOrijinal: {df.shape[0]} film, {df.shape[1]} sütun")
print("Sütunlar:", list(df.columns))

# ── Kaldırılacak sütunlar ──────────────────────────────────────────────────────
REMOVE = [
    "distributor_film_count",    # CSV'de tüm dataset üzerinden hesaplanmış → sızıntı riski
    "distributor_domestic_ratio",# aynı gerekçe
    "has_awards",                # korelasyon 0.05 — gürültü
]

missing = [c for c in REMOVE if c not in df.columns]
if missing:
    print(f"\n⚠ Şu sütunlar zaten yok (atlandı): {missing}")

to_drop = [c for c in REMOVE if c in df.columns]
df_clean = df.drop(columns=to_drop)

print(f"\nKaldırılan ({len(to_drop)} sütun): {to_drop}")
print(f"Temizlenmiş: {df_clean.shape[0]} film, {df_clean.shape[1]} sütun")
print("Kalan sütunlar:", list(df_clean.columns))

# ── Kaydet ────────────────────────────────────────────────────────────────────
df_clean.to_csv(DEST, index=False, encoding="utf-8-sig")
print(f"\n✓ Kaydedildi → {DEST}")
print("\nSonraki adım: python demo/save_model.py")
