# Türkiye Box-Office Seyirci Tahmin Projesi

Türkiye'de gösterime giren filmlerin toplam seyirci sayısını makine öğrenmesi ile tahmin eden bir regresyon projesi.
Veri web scraping ile toplanmış, deterministic özellik mühendisliği ve Google Gemini API ile zenginleştirilmiştir.

**Takım:** Furkan Fidan · Beyza Nur Selvi · Enes Kocakanat

---

## İçindekiler

- [Proje Özeti](#proje-özeti)
- [Veri Seti](#veri-seti)
- [Özellikler](#özellikler)
- [Pipeline](#pipeline)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Model Sonuçları](#model-sonuçları)
- [Proje Yapısı](#proje-yapısı)

---

## Proje Özeti

**Hedef değişken:** `log_total_audience` — Türkiye gişesindeki toplam seyirci sayısının doğal logaritması.

**Veri:** 2015–2025 yılları arasında Türkiye'de gösterime giren ~1 100 film.

**Yaklaşım:**
1. Box-office verileri `boxofficeturkiye.com`'dan scrape edilir.
2. Deterministic özellik mühendisliği ile 25+ sayısal özellik üretilir.
3. Google Gemini API ile 6 LLM tabanlı özellik (yönetmen prestiji, oyuncu gücü, bütçe kademesi, vb.) eklenir.
4. 6 regresyon modeli eğitilir, 4 metrik ile karşılaştırılır, K-Fold CV ve GridSearchCV ile optimize edilir.

---

## Veri Seti

| Dosya | Açıklama | Satır |
|---|---|---|
| `data/raw/raw_movie_data.csv` | Ham scrape çıktısı | ~1 100 |
| `data/processed/enriched_movie_data.csv` | Detay scraper sonrası | ~1 100 |
| `data/processed/final_movie_data.csv` | Preprocessing sonrası | ~1 100 |
| `data/processed/llm_enriched_movie_data.csv` | LLM + COVID özellikleri eklenmiş final veri | ~1 100 |

---

## Özellikler

### Temel Özellikler (Deterministic)

| Özellik | Açıklama |
|---|---|
| `genre`, `genre_count` | Film türleri ve tür sayısı |
| `is_sequel`, `is_adaptation` | Devam filmi / uyarlama bayrağı |
| `rating` | Yaş sınırı (ordinal: G=0 → NC17=5) |
| `runtime_minutes` | Film süresi |
| `distributor_film_count` | Dağıtıcı geçmiş film sayısı |
| `distributor_domestic_ratio` | Yerli film oranı (dağıtıcı) |
| `release_year/month/week/season` | Yayın tarihi özellikleri |
| `holiday_type`, `holiday_week` | Tatil dönemi bilgisi |
| `competition_index` | Aynı hafta çıkan rakip film sayısı |
| `is_domestic` | Yerli film bayrağı |

### LLM Özellikleri (Google Gemini API)

| Özellik | Açıklama |
|---|---|
| `director_has_hit` | Yönetmenin önceki gişe başarısı (0/1) |
| `star_power` | Oyuncu kadrosunun Türkiye'deki popülerliği (0–3) |
| `budget_tier` | Bütçe kademesi: 0=mikro (<$1M) → 4=blockbuster (>$150M) |
| `is_franchise` | MCU/DC/büyük franchise parçası (0/1) |
| `is_adaptation` | Kitap/oyun/IP uyarlaması (0/1) |
| `has_awards` | Ödül kazanmış/adaylık almış (0/1) |

### COVID Özelliği (Deterministic)

| Özellik | Açıklama |
|---|---|
| `is_covid_period` | Türkiye sinema kapanma döneminde çıktıysa 1 (Mar 2020 – Haz 2021) |

---

## Pipeline

```
data_scraper.py
      │
      ▼
raw_movie_data.csv
      │
detail_scraper.py
      │
      ▼
enriched_movie_data.csv
      │
preprocessing.py
      │
      ▼
final_movie_data.csv
      │
llm_enrichment.py  ←── Google Gemini API
      │
      ▼
llm_enriched_movie_data.csv
      │
model_training_v3.ipynb
      │
      ▼
Eğitilmiş modeller + görseller
```

---

## Kurulum

### 1. Sanal ortam oluştur ve bağımlılıkları yükle

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Gemini API anahtarını ayarla

Proje kökünde `.env` dosyası oluştur:

```
GEMINI_API_KEY=your_api_key_here
```

> API anahtarı [Google AI Studio](https://aistudio.google.com/app/apikey)'dan alınabilir.
> `.env` dosyası `.gitignore`'a eklenmiştir — asla commit etme.

---

## Kullanım

### Scraping (veri toplama)

```bash
python scripts/data_scraper.py
python scripts/detail_scraper.py
```

### Preprocessing

```bash
python scripts/preprocessing.py
```

### LLM Zenginleştirme

```bash
# Tüm filmler için (varsayılan batch boyutu 20)
python scripts/llm_enrichment.py

# Büyük batch ile daha az API isteği
python scripts/llm_enrichment.py --batch-size 55
```

> **Not:** Gemini ücretsiz katmanında günlük ~20 istek limiti vardır.
> `--batch-size 55` ile 1 100 filmi tek günde işleyebilirsiniz.

### Model Eğitimi

Jupyter'da `notebooks/model_training_v3.ipynb` dosyasını sırayla çalıştır.

```bash
jupyter notebook notebooks/model_training_v3.ipynb
```

---

## Model Sonuçları

`log_total_audience` tahmininde 6 model karşılaştırması (test seti, %20):

| Model | R² | MAE | RMSE | MAPE |
|---|---|---|---|---|
| Linear Regression | — | — | — | — |
| Ridge | — | — | — | — |
| Lasso | — | — | — | — |
| Decision Tree | — | — | — | — |
| **Random Forest** | **—** | **—** | **—** | **—** |
| Gradient Boosting | — | — | — | — |

> Sonuçlar notebook çalıştırıldıktan sonra tabloya eklenecektir.

### Notebook Bölümleri (model_training_v3.ipynb)

| # | Bölüm | İçerik |
|---|---|---|
| 1 | Setup & Data Loading | Kütüphaneler, veri yükleme, shape/null/describe |
| 2 | Preprocessing & Split | Multi-hot, target enc., OHE, StandardScaler, 80/20 split |
| 3 | Model Training | 6 model (linear → scaled, tree → raw) |
| 4 | Evaluation Metrics | R², MAE, RMSE, MAPE |
| 5 | Visual Comparison | Bar chart + overfitting check (train vs test R²) |
| 6 | Residual Analysis | Scatter, histogram, % error dağılımı |
| 7 | Feature Importance | Top 25 özellik + grup bazlı özet (LLM kırmızı, COVID turuncu) |
| 8 | Cross-Validation | 5-Fold KFold, mean ± std, stabilite analizi |
| 9 | Hyperparameter Tuning | GridSearchCV — RF için en iyi parametreler |

---

## Proje Yapısı

```
movie/
├── data/
│   ├── raw/
│   │   └── raw_movie_data.csv          # Ham scrape verisi
│   └── processed/
│       ├── enriched_movie_data.csv     # Detay scraper çıktısı
│       ├── final_movie_data.csv        # Preprocessing çıktısı
│       └── llm_enriched_movie_data.csv # LLM + COVID özellikleri (nihai veri)
├── notebooks/
│   ├── model_training_v2.ipynb         # Temel model (LLM özellikleri yok)
│   └── model_training_v3.ipynb         # Akademik pipeline (9 bölüm)
├── scripts/
│   ├── data_scraper.py                 # boxofficeturkiye.com → ham veri
│   ├── detail_scraper.py               # Film detayları scraper
│   ├── preprocessing.py                # Deterministic özellik mühendisliği
│   └── llm_enrichment.py              # Gemini API ile LLM zenginleştirme
├── .env                                # API anahtarı (commit etme!)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Gereksinimler

```
pandas · numpy · scikit-learn · matplotlib · seaborn
requests · beautifulsoup4
google-genai · python-dotenv
ipykernel · jinja2
```
