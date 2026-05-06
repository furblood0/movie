"""
preprocessing.py
----------------
enriched_movie_data.csv  →  final_movie_data.csv

Adımlar:
  1. Tarih ayrıştırma (Türkçe ay adları → release_month, release_week)
  2. Mevsim (release_season)
  3. Genre temizleme + genre_count
  4. Sequel tespiti (is_sequel)
  5. Dağıtıcı özellikleri — leakage-free (distributor_film_count, distributor_domestic_ratio)
  6. Rekabet endeksi (competition_index)
  7. Tatil haftası — düzeltilmiş (holiday_week + holiday_type)
  8. Veri kalitesi düzeltmeleri (runtime_minutes sıfırları, rating ordinal)
  9. Final sütun seçimi ve kayıt

Çalıştırmak için (proje kökünden):
  python scripts/preprocessing.py

Pipeline:
  data_scraper.py   → data/raw/raw_movie_data.csv
  detail_scraper.py → data/processed/enriched_movie_data.csv
  preprocessing.py  → data/processed/final_movie_data.csv   ← bu dosya
"""

import pandas as pd
import numpy as np
import datetime
import os
import re

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

MONTHS_TR = {
    'Ocak': 1, 'Şubat': 2, 'Mart': 3, 'Nisan': 4, 'Mayıs': 5, 'Haziran': 6,
    'Temmuz': 7, 'Ağustos': 8, 'Eylül': 9, 'Ekim': 10, 'Kasım': 11, 'Aralık': 12
}

# Rating → ordinal eşleşmesi.
# Sıralama: kısıtlama arttıkça değer artar (0 = herkese açık, 4 = yalnız yetişkin).
# "7 yaş altı aile" kasıtlı olarak 1'e konuyor: 7 yaş sınırından DAHA gevşek
# (çocuk izleyebilir, ama yalnız değil).
RATING_ORDER = {
    'Genel İzleyici Kitlesi.':                                      0,
    '7 yaş altı izleyici kitlesi aile eşliğinde izleyebilir.':     1,
    '7 yaş ve üzeri izleyici kitlesi içindir.':                    2,
    '13 yaş ve üzeri izleyici kitlesi içindir.':                   3,
    '18 yaş ve üzeri izleyici kitlesi içindir.':                   4,
}

_RATING_DEFAULT = 'Genel İzleyici Kitlesi.'

# Dini bayram tarihleri — Diyanet İşleri Başkanlığı resmi ilanlarından alındı.
# Kaynak: https://www.diyanet.gov.tr
#
# Hicri takvim her yıl ~11 gün öne kaydığı için bu tarihlerin elle güncellenmesi gerekir.
# Yeni bir yıl eklemek için o yılın Diyanet tatil ilanından başlangıç tarihine bakılır.
#
# Pencere: arife dahil bayram süresi + 2 gün tolerans.
# Ramazan Bayramı: 3 gün  + arife = 4 gün  → pencere: arife – 2. gün
# Kurban Bayramı:  4 gün  + arife = 5 gün  → pencere: arife – 3. gün
# Pratikte bir film bayramdan 1 hafta önce çıkıp izleyici çekebilir;
# burada resmi bayram haftasıyla sınırlı tutuyoruz.
#
# Formatı: (başlangıç_tarihi, bitiş_tarihi, tür)

_EID_PERIODS = [
    # ---------- Ramazan Bayramı ----------
    (datetime.date(2015,  7, 16), datetime.date(2015,  7, 19), 'ramazan_bayrami'),
    (datetime.date(2016,  7,  5), datetime.date(2016,  7,  8), 'ramazan_bayrami'),
    (datetime.date(2017,  6, 24), datetime.date(2017,  6, 27), 'ramazan_bayrami'),
    (datetime.date(2018,  6, 14), datetime.date(2018,  6, 17), 'ramazan_bayrami'),
    (datetime.date(2019,  6,  3), datetime.date(2019,  6,  6), 'ramazan_bayrami'),
    (datetime.date(2020,  5, 23), datetime.date(2020,  5, 26), 'ramazan_bayrami'),
    (datetime.date(2021,  5, 12), datetime.date(2021,  5, 15), 'ramazan_bayrami'),
    (datetime.date(2022,  5,  1), datetime.date(2022,  5,  4), 'ramazan_bayrami'),
    (datetime.date(2023,  4, 20), datetime.date(2023,  4, 23), 'ramazan_bayrami'),
    (datetime.date(2024,  4,  9), datetime.date(2024,  4, 12), 'ramazan_bayrami'),
    (datetime.date(2025,  3, 29), datetime.date(2025,  4,  1), 'ramazan_bayrami'),
    # ---------- Kurban Bayramı ----------
    (datetime.date(2015,  9, 23), datetime.date(2015,  9, 27), 'kurban_bayrami'),
    (datetime.date(2016,  9, 11), datetime.date(2016,  9, 15), 'kurban_bayrami'),
    (datetime.date(2017,  8, 31), datetime.date(2017,  9,  4), 'kurban_bayrami'),
    (datetime.date(2018,  8, 20), datetime.date(2018,  8, 24), 'kurban_bayrami'),
    (datetime.date(2019,  8, 10), datetime.date(2019,  8, 14), 'kurban_bayrami'),
    (datetime.date(2020,  7, 30), datetime.date(2020,  8,  3), 'kurban_bayrami'),
    (datetime.date(2021,  7, 19), datetime.date(2021,  7, 23), 'kurban_bayrami'),
    (datetime.date(2022,  7,  8), datetime.date(2022,  7, 12), 'kurban_bayrami'),
    (datetime.date(2023,  6, 27), datetime.date(2023,  7,  1), 'kurban_bayrami'),
    (datetime.date(2024,  6, 15), datetime.date(2024,  6, 19), 'kurban_bayrami'),
    (datetime.date(2025,  6,  5), datetime.date(2025,  6,  9), 'kurban_bayrami'),
]

# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def parse_tr_date(date_str):
    """'13 Kasım 2015' gibi Türkçe tarih stringini datetime'a çevirir."""
    try:
        parts = str(date_str).split()
        return datetime.datetime(int(parts[2]), MONTHS_TR[parts[1]], int(parts[0]))
    except Exception:
        return None


def get_season(month):
    if month in [12, 1, 2]:  return 'Winter'
    if month in [3, 4, 5]:   return 'Spring'
    if month in [6, 7, 8]:   return 'Summer'
    return 'Fall'


def clean_genre(genre_str):
    """
    Genre stringini normalize eder.

    Yapılan işlemler:
      - Her tag'in başındaki/sonundaki boşlukları temizler
      - None / NaN → 'Bilinmiyor'
      - Virgülle ayrılmış tagları yeniden birleştirir (tek boşluk sağlar)

    Örnekler:
      "Komedi ,  Dram "  →  "Komedi, Dram"
      ""                 →  "Bilinmiyor"
      NaN                →  "Bilinmiyor"
    """
    if pd.isna(genre_str) or str(genre_str).strip() in ('', 'Unknown', 'unknown'):
        return 'Bilinmiyor'
    tags = [t.strip() for t in str(genre_str).split(',') if t.strip()]
    return ', '.join(tags)


def get_genre_count(genre_str):
    """Temizlenmiş genre stringindeki tag sayısını döndürür."""
    if genre_str == 'Bilinmiyor':
        return 0
    return len([t for t in str(genre_str).split(',') if t.strip()])


def normalize_rating(rating_str):
    """
    Ham rating stringini normalize edip ordinal tamsayıya çevirir.

    Adımlar:
      1. NaN / boş string → varsayılan ('Genel İzleyici Kitlesi.')
      2. Başındaki / sonundaki boşlukları temizle
      3. RATING_ORDER tablosundan ordinal değeri al
         Tabloda bulunmayan beklenmedik değerler → 0 (en gevşek kısıtlama)

    Döndürür: int  (0–4)
    """
    if pd.isna(rating_str) or str(rating_str).strip() == '':
        cleaned = _RATING_DEFAULT
    else:
        cleaned = str(rating_str).strip()
    return RATING_ORDER.get(cleaned, 0)


def check_sequel(name):
    """
    Film adından sequel olup olmadığını regex ile tahmin eder.

    Kural: Sayı veya Roma rakamı SADECE ismin sonunda ya da ': Alt Başlık'
    öncesinde ise sequel sayılır.

    Doğru yakalaması gerekenler:
        "Recep İvedik 6"            → sonda tek rakam
        "Hızlı ve Öfkeli 7"        → sonda tek rakam
        "Kaptan Pengu 2"            → sonda tek rakam
        "Düğün Dernek 2: Sünnet"   → rakam + iki nokta (alt başlık var)
        "Rocky IV"                  → sonda Roma rakamı
        "Çakallarla Dans 5"        → sonda tek rakam

    Yanlış yakalamaması gerekenler:
        "Ali Baba ve 7 Cüceler"    → ortada rakam, sequel değil
        "7. Koğuştaki Mucize"      → başta rakam, sequel değil
        "İki Gözüm Ahmet"          → ortada rakam yok (sayı yazıyla)
    """
    name = str(name)
    patterns = [
        r'\s\d+$',           # sonda rakam:    "Recep İvedik 6", "Fast 10"
        r'\s\d+\s*:',        # rakam + iki nokta: "Düğün Dernek 2: Sünnet"
        r'\s[IVX]{1,4}$',    # sonda Roma rakamı: "Rocky IV", "Alien III"
        r'\bBölüm\b',        # "2. Bölüm" gibi ifadeler
        r'\bSerisi\b',       # "X Serisi"
        r'\bDevam\b',        # "Devam Filmi"
    ]
    for p in patterns:
        if re.search(p, name):
            return 1
    return 0


# Milli tatillerin sabit tarihleri: (ay, gün, etiket, min_yıl)
#
#   min_yıl = None  → veri setinin tüm yıllarında (2015+) geçerli
#   min_yıl = 2017  → yalnızca 2017 ve sonrasında tatil sayılır
#
# 15 Temmuz neden 2017?
#   15 Temmuz 2016 darbe girişiminin ardından resmi tatil ilan edildi.
#   İlk kez 2017'de uygulandı. 2015–2016'da bu tarih tatil değildi.
_NATIONAL_HOLIDAYS = [
    (4,  23, '23_nisan',    None),  # Ulusal Egemenlik ve Çocuk Bayramı
    (5,   1, '1_mayis',     None),  # Emek ve Dayanışma Günü (2009'dan beri resmi)
    (5,  19, '19_mayis',    None),  # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7,  15, '15_temmuz',   2017),  # Demokrasi ve Millî Birlik Günü (2017'den itibaren)
    (8,  30, '30_agustos',  None),  # Zafer Bayramı
    (10, 29, '29_ekim',     None),  # Cumhuriyet Bayramı
]

# Milli tatil etki penceresi: tatil günü ± kaç gün?
# Köprü günleri dahil 7 günlük pencere (±3 gün) makul.
_NATIONAL_HOLIDAY_WINDOW = datetime.timedelta(days=3)

# Yılbaşı dönemi: 25 Aralık – 7 Ocak
# Türkiye'de "yılbaşı dönemi" bu aralıkta. Ocak başı ve Aralık ortası dahil değil.
_YILBASI_START = (12, 25)  # (ay, gün)
_YILBASI_END   = (1,  7)   # (ay, gün)


def compute_competition_index(df):
    """
    Her film için aynı vizyona giriş ayındaki rakip film sayısını hesaplar.

    Tanım: "Bu filmle aynı (yıl, ay) içinde vizyona giren BAŞKA film sayısı."
    Kendisi hariç tutulur → competition_index = 0 demek o ay tek film.

    Neden ay bazlı, hafta değil?
        release_week artık mevcut; ancak ~1100 film / ~520 hafta = ortalama
        2 film/hafta → çok seyrek. Ay bazı istatistiksel olarak daha kararlı.

    Döndürür: pd.Series (df ile aynı index)
    """
    monthly_counts = df.groupby(['release_year', 'release_month'])['movie_name'].transform('count')
    return (monthly_counts - 1).astype(int)


def compute_distributor_features(df):
    """
    Dağıtıcı bazlı iki istatistiksel özellik hesaplar.
    Her ikisi de hedef değişkeni (log_total_audience) KULLANMAZ → hedef leakage yok.

    distributor_film_count
        Bu dağıtıcının veri setindeki toplam film sayısı.
        Büyük/köklü dağıtıcıları küçüklerden ayırır.

    distributor_domestic_ratio
        Bu dağıtıcının filmlerinin yüzde kaçı yerli (is_domestic == 1)?
        0.0 → tamamen yabancı içerik,  1.0 → tamamen yerli içerik.
        CGV Mars/yerli odaklı ile UIP/yabancı odaklı dağıtıcıları ayırt eder.

    *** TEMPORAL LEAKAGE UYARISI ***
        Bu fonksiyon istatistikleri TÜM veri seti üzerinde hesaplar.
        Örneğin 2015'teki bir film, 2022–2025 filmlerini de içeren
        bir dağıtıcı sayısını "görür" — bu temporal leakage'dir.
        Doğru kullanım: model_training notebook'unda train/test split'ten
        SONRA bu istatistikler yalnızca train seti üzerinden yeniden
        hesaplanır ve test setine map edilir (bkz. Section 2, adım 3).

    Not: distributor_power (ortalama) ve distributor_std (std) hedef tabanlıdır;
         data leakage riski nedeniyle train/test split'ten SONRA notebook'ta hesaplanır.

    Döndürür: df — iki yeni sütun eklenmiş hâli
    """
    film_count = df.groupby('distributor')['movie_name'].transform('count')
    df['distributor_film_count']     = film_count.astype(int)

    domestic_ratio = df.groupby('distributor')['is_domestic'].transform('mean')
    df['distributor_domestic_ratio'] = domestic_ratio.round(3)

    return df


def classify_holiday(release_date):
    """
    Filmin tam çıkış tarihine göre tatil türünü döndürür; tatil yoksa None.

    Öncelik sırası:
      1. Dini bayram (Ramazan / Kurban) — Diyanet tarihlerine göre kesin aralık
      2. Yılbaşı dönemi             — 25 Aralık – 7 Ocak
      3. Milli tatiller             — her tatil günü ±3 gün pencere
            23 Nisan, 1 Mayıs, 19 Mayıs, 30 Ağustos, 29 Ekim (tüm yıllar)
            15 Temmuz (yalnızca 2017+)

    Neden bu pencereler?
      - Dini bayramlar: arife dahil resmi tatil süresi (3-5 gün)
      - Yılbaşı: Türkiye'de tatil atmosferi 25 Aralık'ta başlar, 7 Ocak'a kadar sürer
      - Milli tatiller: tek günlük resmi tatil; köprü günleriyle birlikte ~7 günlük
        etki penceresi oluşabilir (±3 gün)
    """
    if release_date is None:
        return None

    # Pandas Timestamp veya datetime.datetime → date'e indir
    if hasattr(release_date, 'date'):
        d = release_date.date()
    else:
        d = release_date

    # ------------------------------------------------------------------
    # 1. Dini bayramlar — kesin tarih aralığı
    # ------------------------------------------------------------------
    for start, end, eid_type in _EID_PERIODS:
        if start <= d <= end:
            return eid_type

    month, day = d.month, d.day

    # ------------------------------------------------------------------
    # 2. Yılbaşı dönemi — 25 Aralık ile 7 Ocak arasındaki her tarih
    # ------------------------------------------------------------------
    is_late_december = (month == 12 and day >= _YILBASI_START[1])
    is_early_january = (month == 1  and day <= _YILBASI_END[1])
    if is_late_december or is_early_january:
        return 'yilbasi'

    # ------------------------------------------------------------------
    # 3. Milli tatiller — tatil günü ±3 gün penceresi
    #    min_year varsa o yıldan itibaren geçerlidir (ör. 15 Temmuz → 2017+).
    # ------------------------------------------------------------------
    for hol_month, hol_day, hol_name, min_year in _NATIONAL_HOLIDAYS:
        if min_year is not None and d.year < min_year:
            continue
        holiday_date = datetime.date(d.year, hol_month, hol_day)
        if abs((d - holiday_date).days) <= _NATIONAL_HOLIDAY_WINDOW.days:
            return hol_name

    return None


# ---------------------------------------------------------------------------
# Ana pipeline
# ---------------------------------------------------------------------------

def preprocess():
    input_file  = os.path.join(PROJECT_ROOT, 'data', 'processed', 'enriched_movie_data.csv')
    output_file = os.path.join(PROJECT_ROOT, 'data', 'processed', 'final_movie_data.csv')

    if not os.path.exists(input_file):
        print(f"Hata: Girdi dosyası bulunamadı -> {input_file}")
        print("Önce detail_scraper.py çalıştırılmalı.")
        return

    df = pd.read_csv(input_file)
    print(f"Girdi: {len(df)} film yüklendi ({input_file})")

    # ------------------------------------------------------------------
    # 1. Tarih ayrıştırma → release_month, release_week
    # ------------------------------------------------------------------
    df['clean_date']     = df['release_date'].apply(parse_tr_date)
    before               = len(df)
    df                   = df.dropna(subset=['clean_date']).copy()
    dropped              = before - len(df)
    if dropped:
        print(f"  Tarih ayrıştırılamayan {dropped} satır çıkarıldı.")
    df['release_month']  = df['clean_date'].dt.month
    df['release_week']   = df['clean_date'].dt.isocalendar().week.astype(int)

    # ------------------------------------------------------------------
    # 2. Mevsim
    # ------------------------------------------------------------------
    df['release_season'] = df['release_month'].apply(get_season)

    # ------------------------------------------------------------------
    # 3. Genre temizleme + genre_count
    #    Ham string korunur (çok taglar bilgiyi taşıyor).
    #    Encoding (multi-hot) notebook'ta yapılır — modele özgü karar.
    # ------------------------------------------------------------------
    df['genre']       = df['genre'].apply(clean_genre)
    df['genre_count'] = df['genre'].apply(get_genre_count)

    # ------------------------------------------------------------------
    # 4. Sequel tespiti
    # ------------------------------------------------------------------
    df['is_sequel'] = df['movie_name'].apply(check_sequel)

    # ------------------------------------------------------------------
    # 5. Dağıtıcı özellikleri (leakage-free)
    # ------------------------------------------------------------------
    df = compute_distributor_features(df)

    # ------------------------------------------------------------------
    # 6. Rekabet endeksi — aynı ay kaç başka film vizyona giriyor?
    # ------------------------------------------------------------------
    df['competition_index'] = compute_competition_index(df)

    # ------------------------------------------------------------------
    # 7. Tatil haftası (düzeltilmiş)
    #
    #    ESKİ (feature_engineering.py): Nisan/Mayıs/Ekim/Kasım'ı
    #    hep tatil sayıyordu — bu yanlıştı. Ramazan/Kurban yıla göre
    #    değişen aylara düşüyor; Kasım'da büyük tatil yok.
    #
    #    YENİ: (yıl, ay) çiftine bakarak gerçek bayram dönemlerini tespit eder.
    # ------------------------------------------------------------------
    df['holiday_type'] = df['clean_date'].apply(
        lambda d: classify_holiday(d) or 'none'
    )
    df['holiday_week'] = (df['holiday_type'] != 'none').astype(int)

    # ------------------------------------------------------------------
    # 8. COVID dönemi etkisi
    #
    # Türkiye'de sinema kapatma takvimi (Diyanet/Kültür Bakanlığı):
    #   Kapatma 1 : 16 Mar 2020 – 05 Haz 2020  (tam kapanma)
    #   Kapatma 2 : 20 Kas 2020 – 01 Tem 2021  (tam kapanma)
    #   Kısıtlama : Haz 2020 – Kas 2020         (kapasite kısıtlaması ~%50)
    #
    # is_covid_period: Mart 2020 – Haziran 2021 arasında vizyona giren film → 1
    # Bu sürede gerçek izleyici sayısı çok düşüktür; modelin yanlış genelleme
    # yapmaması için bu sinyalin verilmesi gerekir.
    # ------------------------------------------------------------------
    def is_covid(year: int, month: int) -> int:
        if year == 2020 and month >= 3:
            return 1
        if year == 2021 and month <= 6:
            return 1
        return 0

    df['is_covid_period'] = df.apply(
        lambda r: is_covid(int(r['release_year']), int(r['release_month'])), axis=1
    )

    # ------------------------------------------------------------------
    # 9. Veri kalitesi düzeltmeleri
    # ------------------------------------------------------------------
    # runtime_minutes: detail_scraper sıfır bırakabiliyor (ayrıştırma hatası)
    df['runtime_minutes'] = pd.to_numeric(df['runtime_minutes'], errors='coerce')
    df['runtime_minutes'] = df['runtime_minutes'].replace(0, np.nan)
    df['runtime_minutes'] = df['runtime_minutes'].fillna(df['runtime_minutes'].median())

    # rating: normalize + ordinal encoding (0–4)
    df['rating'] = df['rating'].apply(normalize_rating)

    # ------------------------------------------------------------------
    # 10. Final sütun seçimi ve kayıt
    # ------------------------------------------------------------------
    final_columns = [
        'movie_name', 'distributor', 'distributor_film_count', 'distributor_domestic_ratio',
        'is_domestic',
        'genre', 'genre_count',
        'is_sequel', 'holiday_week', 'holiday_type', 'release_season',
        'release_year', 'release_month', 'release_week', 'competition_index',
        'runtime_minutes', 'rating', 'is_covid_period', 'total_audience', 'log_total_audience',
    ]

    df_final = df[final_columns].copy()
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')

    # ------------------------------------------------------------------
    # Özet
    # ------------------------------------------------------------------
    print(f"Çıktı: {len(df_final)} film kaydedildi ({output_file})")
    print(f"\nGenre count dağılımı (kaç filmde kaç tag var):")
    print(df_final['genre_count'].value_counts().sort_index().to_string())
    print(f"\nholiday_week dağılımı:\n{df_final['holiday_week'].value_counts().to_string()}")
    print(f"\nholiday_type dağılımı:\n{df_final['holiday_type'].value_counts().to_string()}")
    print(f"\nrelease_season dağılımı:\n{df_final['release_season'].value_counts().to_string()}")
    print(f"\nrating dağılımı (ordinal):\n{df_final['rating'].value_counts().sort_index().to_string()}")
    print(f"\nis_covid_period dağılımı:\n{df_final['is_covid_period'].value_counts().to_string()}")
    print(f"\nrelease_week aralığı: {df_final['release_week'].min()}–{df_final['release_week'].max()}, "
          f"en yoğun haftalar:\n{df_final['release_week'].value_counts().head(5).to_string()}")
    print(f"\nÖrnek çıktı (ilk 3 satır):")
    print(df_final[['movie_name', 'genre', 'genre_count', 'holiday_type', 'is_sequel']].head(3).to_string(index=False))


if __name__ == "__main__":
    preprocess()
