"""demo_ui için test setinden (Liste_Yili >= 2023) hazır senaryo JSON üretir."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "processed" / "ml_ready_dataset.csv"
FEAT_PATH = ROOT / "demo" / "feature_names.json"
OUT_PATH = ROOT / "demo" / "test_set_presets.json"


def tur_columns(feature_names: list[str]) -> list[str]:
    return [c for c in feature_names if c.startswith("Tur_")]


def col_to_genre_label(col: str) -> str:
    rest = col[4:]
    if rest == "Bilim_Kurgu":
        return "Bilim-Kurgu"
    if rest == "Romantik_Komedi":
        return "Romantik-Komedi"
    if rest == "3_Boyutlu":
        return "3 Boyutlu"
    return rest.replace("_", " ")


def row_to_features(r: pd.Series, tur_cols: list[str]) -> dict:
    genres = []
    for c in tur_cols:
        try:
            if float(r.get(c, 0) or 0) >= 0.5:
                genres.append(col_to_genre_label(c))
        except (TypeError, ValueError):
            pass
    if not genres:
        genres = ["Dram"]

    vd = pd.to_datetime(r.get("Vizyon_Tarihi"), errors="coerce")
    y = int(r["Liste_Yili"]) if pd.notna(r.get("Liste_Yili")) else (int(vd.year) if pd.notna(vd) else 2024)
    m = int(vd.month) if pd.notna(vd) else 6

    def fnum(k: str) -> float | None:
        v = r.get(k)
        if pd.isna(v):
            return None
        return float(v)

    out = {
        "is_domestic": int(r.get("Is_Yerli", 0) or 0),
        "genres": genres,
        "runtime_minutes": float(r["Sure_Dakika"]) if pd.notna(r.get("Sure_Dakika")) else 105.0,
        "imdb_puani": float(r["IMDb_Puani"]) if pd.notna(r.get("IMDb_Puani")) else 6.5,
        "imdb_yok": int(r.get("IMDb_Yok", 0) or 0),
        "release_year": y,
        "release_month": m,
        "competition_index": int(r["Rekabet_Indeksi"]) if pd.notna(r.get("Rekabet_Indeksi")) else 5,
        "is_sequel": int(r.get("Is_Devam_Filmi", 0) or 0),
    }
    for key, col in [
        ("yonetmen_skor", "Yonetmen_Skor"),
        ("yonetmen_film_sayisi", "Yonetmen_Film_Sayisi"),
        ("oyuncu1_skor", "Oyuncu1_Skor"),
        ("oyuncu2_skor", "Oyuncu2_Skor"),
        ("oyuncu3_skor", "Oyuncu3_Skor"),
        ("kadro_veri_var", "Kadro_Veri_Var"),
        ("dagitimci_skor", "Dagitimci_Skor"),
    ]:
        v = fnum(col)
        if v is not None:
            out[key] = v

    return out


def main() -> None:
    feat_names = json.loads(FEAT_PATH.read_text(encoding="utf-8"))
    tur_cols = tur_columns(feat_names)

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    test = df[df["Liste_Yili"] >= 2023].copy()
    test = test.sort_values("Toplam_Seyirci", ascending=False).reset_index(drop=True)
    n = len(test)
    if n == 0:
        raise SystemExit("Test seti boş (Liste_Yili >= 2023 yok).")

    # Çeşitli gişe seviyelerinden örnekler + yıl çeşitliliği
    positions = sorted(
        set(
            [
                0,
                max(0, n // 6),
                max(0, n // 3),
                max(0, n // 2),
                max(0, n - 1),
            ]
        )
    )

    presets = []
    used_names: set[str] = set()
    for pos in positions:
        r = test.iloc[pos]
        name = str(r.get("Film_Adi", f"Film_{pos}"))[:52]
        if name in used_names:
            continue
        used_names.add(name)
        aud = int(r["Toplam_Seyirci"]) if pd.notna(r.get("Toplam_Seyirci")) else 0
        ly = int(r["Liste_Yili"])
        presets.append(
            {
                "emoji": "🎬",
                "name": name,
                "desc": f"Test seti {ly} · Gerçek gişe: {aud:,} seyirci".replace(",", "."),
                "f": row_to_features(r, tur_cols),
                "actual_toplam_seyirci": aud,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(presets)} presets -> {OUT_PATH}")


if __name__ == "__main__":
    main()
