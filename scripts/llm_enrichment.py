"""
LLM Enrichment Script — Gemini API (Batch Mode)
================================================
Her BATCH_SIZE filmlik grubu tek bir API isteğinde işler.
Günlük 20 istek limiti ile:
  - batch=10  → 200 film/gün  (~6 gün)
  - batch=50  → 1000 film/gün (~2 gün)
  - batch=100 → 2000 film/gün (1 günde tamamlanır)

Üretilen 6 LLM özelliği:
  director_has_hit  : Yönetmenin önceki gişe başarısı (0/1)
  star_power        : Başrol popülaritesi Türkiye'de (0-3)
  budget_tier       : Yapım bütçesi tieri (0=mikro...4=blockbuster)
  is_franchise      : Büyük franchise parçası mı? (0/1)
  is_adaptation     : Kitap/oyun/IP uyarlaması mı? (0/1)
  has_awards        : Büyük ödül adaylığı/kazanımı (0/1)

Kullanım:
    python scripts/llm_enrichment.py                    # .env'den API key
    python scripts/llm_enrichment.py --batch-size 50   # daha büyük batch
    python scripts/llm_enrichment.py --limit 20         # test modu
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from google import genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
INPUT_CSV  = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "final_movie_data.csv")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "llm_enriched_movie_data.csv")

GEMINI_MODEL     = "gemini-2.5-flash"
DEFAULT_BATCH    = 20       # tek API çağrısında kaç film
SLEEP_BETWEEN    = 3.0      # batch'ler arası bekleme (saniye)
CHECKPOINT_EVERY = 5        # kaç batch'te bir ara kayıt

LLM_COLUMNS = ["director_has_hit", "star_power", "budget_tier",
               "is_franchise", "is_adaptation", "has_awards"]

FALLBACK = {"director_has_hit": 0, "star_power": 0, "budget_tier": 1,
            "is_franchise": 0, "is_adaptation": 0, "has_awards": 0}

COLUMN_ORDER = [
    "movie_name",
    "genre", "genre_count",
    "is_sequel", "is_adaptation", "is_franchise",
    "rating", "runtime_minutes", "has_awards",
    "director_has_hit", "star_power",
    "budget_tier", "is_domestic",
    "distributor", "distributor_film_count", "distributor_domestic_ratio",
    "release_year", "release_month", "release_week", "release_season",
    "holiday_type", "holiday_week",
    "competition_index",
    "is_covid_period",
    "total_audience", "log_total_audience",
]

# ---------------------------------------------------------------------------
# Batch prompt
# ---------------------------------------------------------------------------

def build_batch_prompt(films: list[tuple[str, int]]) -> str:
    """films: [(movie_name, release_year), ...]"""
    film_list = "\n".join(
        f'{i+1}. "{name}" ({year})'
        for i, (name, year) in enumerate(films)
    )
    return f"""You are a film industry expert. Analyze each movie below and return ONLY a valid JSON array — no explanation, no markdown, no extra text.

Movies:
{film_list}

Return a JSON array with exactly {len(films)} objects, one per movie, in the same order:
[
  {{
    "director_has_hit": <0 or 1 — director had a prior box office hit>,
    "star_power": <0-3 — lead cast popularity in Turkish market>,
    "budget_tier": <0-4 — budget: 0=micro(<$1M), 1=low($1-10M), 2=medium($10-50M), 3=high($50-150M), 4=blockbuster(>$150M)>,
    "is_franchise": <0 or 1 — part of any film series or franchise, including Turkish series such as Recep İvedik, Düğün Dernek, Organize İşler>,
    "is_adaptation": <0 or 1 — adapted from book/game/IP>,
    "has_awards": <0 or 1 — major award win or nomination>
  }},
  ...
]"""


def parse_result(data: dict) -> dict:
    return {
        "director_has_hit": int(bool(data.get("director_has_hit", 0))),
        "star_power":        max(0, min(3, int(data.get("star_power", 0)))),
        "budget_tier":       max(0, min(4, int(data.get("budget_tier", 1)))),
        "is_franchise":      int(bool(data.get("is_franchise", 0))),
        "is_adaptation":     int(bool(data.get("is_adaptation", 0))),
        "has_awards":        int(bool(data.get("has_awards", 0))),
    }


# ---------------------------------------------------------------------------
# Gemini batch çağrısı
# ---------------------------------------------------------------------------

def call_gemini_batch(client, films: list[tuple[str, int]], retries: int = 3) -> list[dict]:
    """films listesi için sırayla eşleşen sonuç listesi döndürür."""
    prompt = build_batch_prompt(films)

    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            raw = response.text.strip()

            # ```json ... ``` bloğu temizle
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)

            if not isinstance(parsed, list):
                raise ValueError(f"Beklenen liste, gelen: {type(parsed)}")

            results = []
            for i, item in enumerate(parsed):
                try:
                    results.append(parse_result(item))
                except Exception:
                    print(f"  [uyari] batch[{i}] parse hatasi, fallback")
                    results.append(FALLBACK.copy())

            # Eksik kayıt varsa fallback ile tamamla
            while len(results) < len(films):
                results.append(FALLBACK.copy())

            return results[:len(films)]

        except json.JSONDecodeError as e:
            print(f"  [JSON parse hatasi] deneme {attempt}/{retries}: {e}")
        except Exception as e:
            msg = str(e)
            print(f"  [API hatasi] deneme {attempt}/{retries}: {msg[:120]}")
            # 429 → hata mesajındaki retry süresini parse et
            if "429" in msg and "retryDelay" in msg:
                try:
                    delay_str = msg.split('"retryDelay": "')[1].split('"')[0]
                    delay_sec = int(delay_str.replace("s", "")) + 5
                    print(f"  Rate limit: {delay_sec} saniye bekleniyor...")
                    time.sleep(delay_sec)
                    continue
                except Exception:
                    pass
            if attempt < retries:
                time.sleep(15 * attempt)

    print(f"  [FALLBACK] {len(films)} film için varsayılan değerler kullanılıyor.")
    return [FALLBACK.copy() for _ in films]


# ---------------------------------------------------------------------------
# Önbellek yükleme
# ---------------------------------------------------------------------------

def load_existing_results(output_path: str) -> dict:
    if not os.path.exists(output_path):
        return {}
    existing = pd.read_csv(output_path, encoding="utf-8-sig")
    cache = {}
    for _, row in existing.iterrows():
        key = str(row["movie_name"])
        cache[key] = {col: row[col] for col in LLM_COLUMNS if col in existing.columns}
    return cache


def save_df(df: pd.DataFrame, path: str) -> None:
    extra = [c for c in df.columns if c not in COLUMN_ORDER]
    order = [c for c in COLUMN_ORDER if c in df.columns] + extra
    df[order].to_csv(path, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Ana işlev
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gemini ile film verisi zenginleştirme (batch)")
    parser.add_argument("--api-key",    default=None, help="Gemini API anahtarı")
    parser.add_argument("--input",      default=INPUT_CSV)
    parser.add_argument("--output",     default=OUTPUT_CSV)
    parser.add_argument("--limit",      type=int, default=None, help="Test için film sayısı")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH,
                        help=f"Bir API çağrısındaki film sayısı (varsayılan: {DEFAULT_BATCH})")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("HATA: GEMINI_API_KEY bulunamadi. .env dosyasini veya --api-key kullanin.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # --- Veriyi yükle ---
    df = pd.read_csv(args.input, encoding="utf-8-sig")
    print(f"Girdi : {len(df)} film -> {args.input}")

    if args.limit:
        df = df.head(args.limit)
        print(f"Test modu: ilk {args.limit} film")

    # --- Önbellek ---
    cache = load_existing_results(args.output)
    print(f"Oncebellekte: {len(cache)} film zaten islenms")

    # --- COVID (deterministik) ---
    def _is_covid(y, m):
        return 1 if (y == 2020 and m >= 3) or (y == 2021 and m <= 6) else 0

    if "is_covid_period" not in df.columns:
        df["is_covid_period"] = df.apply(
            lambda r: _is_covid(int(r["release_year"]), int(r["release_month"])), axis=1
        )
        print(f"COVID ozelligi eklendi: {int(df['is_covid_period'].sum())} film")

    # --- LLM sütunları ---
    for col in LLM_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # --- Önbellekten doldurulan filmler ---
    for idx, row in df.iterrows():
        name = str(row["movie_name"])
        if name in cache:
            for col in LLM_COLUMNS:
                df.at[idx, col] = cache[name].get(col, FALLBACK[col])

    # --- İşlenmesi gereken filmler ---
    todo_idx = [i for i, r in df.iterrows() if str(r["movie_name"]) not in cache]
    total_todo = len(todo_idx)

    print(f"Islenecek: {total_todo} film | Batch boyutu: {args.batch_size}")
    if total_todo == 0:
        print("Tum filmler zaten islenmis!")
        save_df(df, args.output)
        return

    # Tahmini süre
    n_batches = -(-total_todo // args.batch_size)  # ceiling div
    est_min = n_batches * SLEEP_BETWEEN / 60
    print(f"Tahmini: {n_batches} batch, ~{est_min:.0f} dk (API yanit suresi haric)")
    print("-" * 55)

    processed = 0
    batch_count = 0

    for b_start in range(0, total_todo, args.batch_size):
        batch_idx = todo_idx[b_start: b_start + args.batch_size]
        films = [(str(df.at[i, "movie_name"]), int(df.at[i, "release_year"])) for i in batch_idx]

        batch_count += 1
        first_film = films[0][0][:35]
        print(f"[Batch {batch_count}/{n_batches}] {len(films)} film | {first_film}...")

        results = call_gemini_batch(client, films)

        for i, result in zip(batch_idx, results):
            for col in LLM_COLUMNS:
                df.at[i, col] = result[col]
            cache[str(df.at[i, "movie_name"])] = result

        processed += len(films)

        if batch_count % CHECKPOINT_EVERY == 0:
            save_df(df, args.output)
            print(f"  [Checkpoint] {processed}/{total_todo} film kaydedildi")

        if b_start + args.batch_size < total_todo:
            time.sleep(SLEEP_BETWEEN)

    # --- Final kayıt ---
    save_df(df, args.output)
    print(f"\nTamamlandi!")
    print(f"  Yeni islenen : {processed} film")
    print(f"  Oncebellekten: {len(cache) - processed} film")
    print(f"  Cikti        : {args.output}")

    print("\n--- LLM Ozellik Ozeti ---")
    for col in LLM_COLUMNS:
        vals = df[col].dropna()
        if len(vals):
            print(f"  {col:20s} | ort={vals.mean():.2f} | min={vals.min()} | max={vals.max()}")


if __name__ == "__main__":
    main()
