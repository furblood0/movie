# Türkiye Sinema Box Office Veri Seti (2016–2025)

Türkiye gişe verilerini [boxofficeturkiye.com](https://boxofficeturkiye.com) kaynağından derleyen, 10 yıllık (2016–2025) dönemi kapsayan bir web kazıma, veri analizi ve makine öğrenmesi hazırlık projesi.

---

## Geliştirme Versiyonları

| Versiyon | Kapsam | Temel Çıktı |
|----------|--------|-------------|
| **v1 — Veri Toplama & Analiz** | Web kazıma, ham veri analizi | `turkiye_sinema_full_dataset.csv` |
| **v2 — Öznitelik Mühendisliği** | Klasör yapısı, Bayesian yumuşatmalı tarihsel skorlar, takvim/başlık bayrakları, ML matrisi | `data/processed/ml_ready_dataset.csv` |

---

## İçindekiler

### v1 — Veri Toplama & Analiz
1. [Proje Özeti](#1-proje-özeti)
2. [Proje Yapısı (v1)](#2-proje-yapısı-v1)
3. [Veri Toplama Süreci](#3-veri-toplama-süreci)
4. [Veri Seti Açıklaması](#4-veri-seti-açıklaması)
5. [Ham Veri Analizi](#5-ham-veri-analizi)
   - [5.1 Genel İstatistikler](#51-genel-i̇statistikler)
   - [5.2 Yıllık Seyirci Trendi](#52-yıllık-seyirci-trendi)
   - [5.3 Türk Film / Yabancı Film Dengesi](#53-türk-film--yabancı-film-dengesi)
   - [5.4 Tür Analizi](#54-tür-analizi)
   - [5.5 Tüm Zamanların En Çok İzlenen Filmleri](#55-tüm-zamanların-en-çok-i̇zlenen-filmleri)
   - [5.6 Dağıtıcı Performansı](#56-dağıtıcı-performansı)
   - [5.7 Yönetmen Sıralaması](#57-yönetmen-sıralaması)
   - [5.8 Bilet Fiyatı ve Pazar Verisi](#58-bilet-fiyatı-ve-pazar-verisi)
6. [Veri Kalitesi ve Eksiklikler](#6-veri-kalitesi-ve-eksiklikler)
7. [Kurulum ve Kullanım](#7-kurulum-ve-kullanım)

### v2 — Öznitelik Mühendisliği
8. [Proje Yapısı (v2)](#8-proje-yapısı-v2)
9. [Öznitelik Mühendisliği](#9-öznitelik-mühendisliği)
   - [9.1 Çalıştırma ve Ön Koşullar](#91-çalıştırma-ve-ön-koşullar)
   - [9.2 Adım Adım İşlem Hattı](#92-adım-adım-i̇şlem-hattı)
   - [9.3 ML-Ready Veri Seti Şeması](#93-ml-ready-veri-seti-şeması)
   - [9.4 Tasarım Kararları ve Gerekçeler](#94-tasarım-kararları-ve-gerekçeler)
   - [9.5 Eksik Değer Özeti (Güncel)](#95-eksik-değer-özeti-güncel)
10. [Veri Temizleme Süreci ve Karşılaşılan Sorunlar](#10-veri-temizleme-süreci-ve-karşılaşılan-sorunlar)
    - [10.1 CSV Encoding Sorunu](#101-csv-encoding-sorunu-bom)
    - [10.2 Sure_Dakika Veri Kalitesi](#102-sure_dakika-veri-kalitesi)
    - [10.3 IMDb Eksikliği — API ile Otomasyon](#103-imdb-eksikliği--api-ile-otomasyon)
    - [10.4 Feature Engineering'de Index Kaybı](#104-feature-engineeringde-index-kaybı)
    - [10.5 Terminal Unicode Hatası](#105-terminal-unicode-hatası)
    - [10.6 Oyuncu verisi ve kadro özelliklerinin evrimi](#106-oyuncu-verisi-eksikliği-ve-kadro-özelliklerinin-evrimi)
    - [10.7 Veri sızıntısı ve sıralı skorların tutarlılığı](#107-veri-sızıntısı-ve-sıralı-skorların-tutarlılığı)
    - [10.8 Dagitimci sirali skoru](#108-dagitimci-sirali-skoru)

---

## 1. Proje Özeti

Bu proje üç aşamalı bir veri toplama hattından oluşmaktadır:

| Aşama | Script | Çıktı |
|-------|--------|-------|
| Yıllık gişe tablosu | `scraper.py` | `turkiye_sinema_veriseti_2016_2025.csv` |
| Film detay zenginleştirme | `detay_scraper.py` | `turkiye_sinema_full_dataset.csv` |
| Pazar özet verisi | `pazar_verileri_scraper.py` | `turkiye_sinema_pazar_verileri.csv` |

Sonuç olarak 2016–2025 arasında vizyona giren **1.976 filmin** gişe ve meta verileri derlenmektedir.

---

## 2. Proje Yapısı (v1)

> Bu yapı v2'de yeniden düzenlendi. Güncel yapı için [Bölüm 8](#8-proje-yapısı-v2)'e bakın.

```
box_office_project/
│
├── scraper.py                              # Aşama 1: Yıllık gişe tabloları
├── detay_scraper.py                        # Aşama 2: Film detay sayfaları
├── pazar_verileri_scraper.py               # Aşama 3: Yıllık pazar özeti
│
├── turkiye_sinema_veriseti_2016_2025.csv   # Aşama 1 çıktısı (ham)
├── turkiye_sinema_full_dataset.csv         # Aşama 2 çıktısı (zengin, ana veri seti)
├── turkiye_sinema_pazar_verileri.csv       # Aşama 3 çıktısı (pazar özeti)
│
└── venv/                                   # Python sanal ortamı
```

---

## 3. Veri Toplama Süreci

### Aşama 1 — `scraper.py`

`https://boxofficeturkiye.com/yillik/{yil}` adresindeki yıllık sıralama sayfaları 2016'dan 2025'e kadar taranır. Her yıl için en fazla 200 film kaydedilir. Elde edilen sütunlar:

- `Film_Adi`, `Vizyon_Tarihi`, `Dagitimci`, `Hafta_Sayisi`, `Toplam_Seyirci`, `Liste_Yili`, `Film_Linki`

### Aşama 2 — `detay_scraper.py`

Aşama 1'de elde edilen her film için `Film_Linki` adresi ziyaret edilir. Sayfa üzerindeki JSON-LD yapılandırılmış verisinden ve HTML içeriğinden şu alanlar çekilir:

- **JSON-LD'den:** `Tur`, `Yonetmen`, `Oyuncular`, `Sure_Dakika`, `IMDb_Puani`
- **HTML parse'dan:** `Ulke`, `Yapimci`

Veri kaybına karşı `zengin_veriseti_checkpoint.csv` ara kayıt dosyası tutulur.

### Aşama 3 — `pazar_verileri_scraper.py`

`https://boxofficeturkiye.com/yillik` adresindeki "Tüm Yıl Karşılaştırması" tablosundan pazar düzeyi özet veriler alınır:

- `Toplam_Seyirci`, `Yeni_Film` sayısı, `Ort_Bilet_TL`

---

## 4. Veri Seti Açıklaması

### `turkiye_sinema_full_dataset.csv` — Ana Veri Seti

**Boyut:** 1.976 satır × 14 sütun

| Sütun | Tür | Açıklama | Örnek |
|-------|-----|----------|-------|
| `Film_Adi` | string | Filmin Türkçe adı | `Recep İvedik 5` |
| `Vizyon_Tarihi` | date | Türkiye'deki ilk vizyon tarihi | `2017-02-17` |
| `Dagitimci` | string | Türkiye'deki dağıtım şirketi | `UIP`, `CGV Mars`, `WB` |
| `Hafta_Sayisi` | int | Vizyon süresi (hafta) | `14` |
| `Toplam_Seyirci` | int | Türkiye toplam seyirci sayısı | `7437050` |
| `Liste_Yili` | int | Veri setindeki yıl etiketi | `2017` |
| `Film_Linki` | string | Kaynak URL | `https://boxofficeturkiye.com/...` |
| `Tur` | string | Virgülle ayrılmış film türleri | `Dram, Komedi` |
| `Yonetmen` | string | Yönetmen adı | `Togan Gökbakar` |
| `Oyuncular` | string | Virgülle ayrılmış oyuncu listesi | `Şahan Gökbakar, ...` |
| `Sure_Dakika` | int | Film süresi (dakika) | `98` |
| `IMDb_Puani` | float | IMDb puanı (1.0–10.0) | `7.4` |
| `Ulke` | string | Yapım ülkesi / ülkeleri | `Türkiye` |
| `Yapimci` | string | Yapımcı şirket(ler) | `BKM, TAFF` |

### `turkiye_sinema_pazar_verileri.csv` — Pazar Özeti

| Sütun | Açıklama |
|-------|----------|
| `Yil` | Yıl |
| `Toplam_Seyirci` | O yıl toplam sinema seyircisi |
| `Yeni_Film` | O yıl vizyona giren film sayısı |
| `Ort_Bilet_TL` | Ortalama bilet ücreti (TL) |

---

## 5. Ham Veri Analizi

### 5.1 Genel İstatistikler

| Metrik | Değer |
|--------|-------|
| Toplam film sayısı | 1.976 |
| Kapsanan dönem | 2016 – 2025 (10 yıl) |
| Toplam seyirci | ~408.8 milyon |
| Tek film rekoru | 7.437.050 (Recep İvedik 5, 2017) |
| IMDb aralığı | 1.0 – 9.1 |
| IMDb ortalaması | ~6.4 (puanı olan filmler için) |
| IMDb verisi eksik | 432 film (%21.9) |

---

### 5.2 Yıllık Seyirci Trendi

```
Yıl   Seyirci        Film   Not
────  ─────────────  ─────  ──────────────────────────────────────
2016   56.453.105     200
2017   71.544.153     200   ← Dönemin zirvesi
2018   68.250.896     200
2019   60.557.998     200
2020   12.125.305     177   ← COVID-19 sinemalara erişimi kapattı
2021   14.211.786     199   ← Kısmi açılma, değerler hâlâ baskılı
2022   35.545.877     200   ← Güçlü toparlanma
2023   29.748.471     200   ← Enflasyon baskısı belirginleşiyor
2024   33.562.253     200
2025   27.258.813     200   ← Bilet fiyatlarındaki artış seyirciyi baskılıyor
```

**Temel çıkarımlar:**

- **2017**, bu on yılın gişe rekoru yılıdır; Recep İvedik 5, Müslüm, Ayla ve Aile Arasında gibi çok izlenen filmler bu yıla aittir.
- **2020**, COVID-19 nedeniyle en düşük seviyeye (12.1M) geriledi; bu dönemde yabancı stüdyolar büyük yapımlarını erteledi, yerli filmler göreceli olarak ayakta kaldı.
- **2022–2024 toparlanması** kısmen gerçekleşti ancak 2017–2019 zirvesinin çok altında kalmaya devam etti.
- **2025**, 2024'e kıyasla gerileyen bir yıl oldu (33.5M → 27.2M). Güçlü bir yerli yapım olmaması ve yükselen bilet fiyatlarının (208 TL) etkisi belirleyici oldu.

---

### 5.3 Türk Film / Yabancı Film Dengesi

```
Yıl   Türkiye %   Yabancı %   Yorum
────  ──────────  ──────────  ────────────────────────────────
2016     %52         %47
2017     %54         %45
2018     %62         %37      ← Türk filmler zirveye çıkıyor
2019     %59         %40
2020     %76         %23      ← Yabancı filmler ertelendi; oran yanıltıcı
2021     %23         %76      ← Marvel dalgası (Spider-Man, Venom 2, Eternals...)
2022     %52         %47
2023     %47         %52      ← Yabancı film üstünlüğü döndü
2024     %60         %39
2025     %52         %47
```

**Temel çıkarımlar:**

- Türkiye, 739 filmle toplamda **224.3 milyon seyirci** üretirken ABD filmleri 683 filmle **153.6 milyon** seyirciye ulaşıyor. Türk filmler daha az yapımla daha fazla izleyici topluyor.
- 2020'deki %76 Türk oranı yanıltıcıdır; yabancı stüdyolar yapımlarını ertelediğinden bu oran seyirci sayısı azken gerçekleşti.
- 2021'de yabancı filmler geri döndüğünde Türk filmlerin payı keskin biçimde geriledi (%23): Spider-Man: Eve Dönüş Yok bu yılın yabancı gişe lideridir (2.88M seyirci).

---

### 5.4 Tür Analizi

#### Film Sayısına Göre

| Tür | Film Sayısı | Toplam Seyirci | Seyirci/Film Ort. |
|-----|------------|----------------|-------------------|
| Dram | 534 | 97.1M | 181.900 |
| Komedi | 469 | 136.1M | 290.200 |
| Korku | 405 | 23.2M | 57.300 |
| Animasyon | 377 | 77.4M | 205.300 |
| Aksiyon | 340 | 103.9M | 305.700 |
| Macera | 307 | 89.0M | 289.900 |
| Gerilim | 297 | 23.0M | 77.400 |
| Aile | 133 | 21.0M | 157.900 |
| Bilim-Kurgu | 112 | 32.8M | 292.700 |
| IMAX | 96 | 57.7M | 600.900 |

> Not: Bir film birden fazla türe ait olabilir; sayımlar buna göre üst üste binebilir.

**Temel çıkarımlar:**

- **Komedi**, film başına ortalamada **en verimli tür**dür (290.200 seyirci/film). Recep İvedik, Organize İşler, Ailecek Şaşkınız gibi seriler bu türü taşıyor.
- **Korku**, 405 filmle en kalabalık üçüncü tür olmasına karşın film başına yalnızca **57.300 seyirci** çekiyor — en düşük verim. Bu durum, ucuz yapım maliyetinin korku filmlerini cazip kıldığını ancak büyük seyirci kitlesine ulaşmalarının zor olduğunu gösteriyor.
- **IMAX etiketli filmler** film başına **600.900** seyirciyle açık ara en yüksek performansı gösteriyor; ancak bu filmler zaten büyük bütçeli blockbuster'lar olduğundan IMAX etiketi değil yapım büyüklüğü belirleyici.
- **Dram**, en fazla film sayısına sahip tür (534) olmasına rağmen komedi ve aksiyonun gerisinde kalıyor.

---

### 5.5 Tüm Zamanların En Çok İzlenen Filmleri

| Sıra | Film | Yıl | Seyirci | Ülke | Tür |
|------|------|-----|---------|------|-----|
| 1 | Recep İvedik 5 | 2017 | 7.437.050 | Türkiye | Komedi |
| 2 | Müslüm | 2018 | 6.480.563 | Türkiye | Biyografi |
| 3 | Ayla | 2017 | 5.589.872 | Türkiye | Dram |
| 4 | Bergen | 2022 | 5.486.175 | Türkiye | Biyografi |
| 5 | 7. Koğuştaki Mucize | 2019 | 5.365.822 | Türkiye | Dram |
| 6 | Aile Arasında | 2017 | 5.294.459 | Türkiye | Komedi |
| 7 | Arif v 216 | 2018 | 4.976.367 | Türkiye | Komedi |
| 8 | Ailecek Şaşkınız | 2018 | 4.034.858 | Türkiye | Komedi |
| 9 | Recep İvedik 6 | 2019 | 3.986.797 | Türkiye | Komedi |
| 10 | Eltilerin Savaşı | 2020 | 3.638.553 | Türkiye | Komedi |
| 11 | Dağ 2 | 2016 | 3.602.511 | Türkiye | Dram |
| 12 | Organize İşler: Sazan Sarmalı | 2019 | 3.537.429 | Türkiye | Komedi |
| 13 | Rafadan Tayfa Göbeklitepe | 2019 | 3.444.814 | Türkiye | Animasyon |
| 14 | Soyut Dışav. Bir Dostluğun Anatomisi | 2025 | 2.946.886 | Türkiye | Komedi |
| 15 | Örümcek-Adam: Eve Dönüş Yok | 2021 | 2.882.960 | **ABD** | Aksiyon |

**Temel çıkarımlar:**

- İlk **14 sırada yalnızca Türk filmler** yer alıyor. İlk 15'e giren tek yabancı film Spider-Man: No Way Home (2021).
- Listenin büyük çoğunluğunu **2017–2019 arası** filmler oluşturuyor; bu dönem Türkiye sinemasının altın çağıdır.
- **Biyografi türü** beklenmedik biçimde güçlü: Müslüm (6.5M) ve Bergen (5.5M) iki büyük Türk sanatçının hayatını konu alan filmlerdir — bu durum, kültürel özdeşleşmenin gişe üzerinde belirleyici etkisini gösteriyor.
- 2020 listesinde **Eltilerin Savaşı** (3.6M) bulunuyor; COVID kısıtlamalarına rağmen böyle bir rakama ulaşması dikkat çekici.

---

### 5.6 Dağıtıcı Performansı

| Dağıtıcı | Toplam Seyirci | Film Sayısı | Seyirci/Film Ort. |
|----------|---------------|-------------|-------------------|
| UIP | 112.5M | 323 | 348.300 |
| CGV Mars | 106.2M | 403 | 263.600 |
| CJ ENM | 64.0M | 288 | 222.200 |
| TME | 49.9M | 317 | 157.500 |
| WB | 44.8M | 133 | 336.600 |
| A90 | 10.8M | 70 | 154.200 |
| Bir Film | 8.6M | 209 | 41.000 |
| Pin. | 5.5M | 29 | 190.500 |
| ChF | 4.7M | 50 | 93.600 |
| Başka S. | 0.96M | 72 | 13.300 |

**Temel çıkarımlar:**

- **UIP** (Universal Pictures International) toplam seyircide lider (112.5M); Marvel/Disney ve Universal'ın büyük yapımlarını dağıtıyor.
- **CGV Mars**, en fazla filmi dağıtan şirket (403 film) — geniş bir katalog stratejisi izliyor.
- **Warner Bros (WB)**, daha az filmle (133) yüksek verim sağlıyor; film başına 336.600 seyirci ortalaması UIP'e yakın.
- **Bir Film**, 209 film dağıtmasına karşın film başına yalnızca 41.000 seyirci çekiyor — bağımsız ve sanat sinemasına yönelik dağıtımcı profilini yansıtıyor.

---

### 5.7 Yönetmen Sıralaması

| Yönetmen | Toplam Seyirci | Film Sayısı |
|----------|---------------|-------------|
| Togan Gökbakar | 14.194.830 | 5 |
| İsmail Fidan | 13.226.040 | 5 |
| Kıvanç Baruönü | 12.629.033 | 6 |
| Selçuk Aydemir | 9.034.799 | 7 |
| Mehmet Ada Öztekin | 8.203.636 | 5 |
| Bedran Güzel | 7.176.481 | 6 |
| "Ketche" Hakan Kırvavaş | 7.167.058 | 2 |
| Can Ulkay | 6.996.126 | 3 |
| Kamil Çetin | 5.871.891 | 9 |
| Mert Baykal | 5.591.440 | 3 |

**Temel çıkarımlar:**

- **Togan Gökbakar** (Recep İvedik serisi), tek bir karaktere dayanan devam filmleriyle 14.2M seyirciye ulaşan en verimli yönetmen.
- **"Ketche" Hakan Kırvavaş** yalnızca 2 filmle 7.2M seyirci topluyor — yüksek verimlilik göstergesi.
- **Kamil Çetin** 9 film yönetmiş olmasına karşın toplam olarak 5.9M seyirci; film başına ortalama daha düşük.

---

### 5.8 Bilet Fiyatı ve Pazar Verisi

```
Yıl   Toplam Seyirci   Yeni Film   Ort. Bilet (TL)   Notlar
────  ───────────────  ─────────  ────────────────   ────────────────────────
2016    58.287.772        360          11.87
2017    71.188.594        392          12.23          Seyirci rekoru
2018    70.409.779        430          12.74
2019    59.556.020        404          16.46
2020    17.415.304        177          17.21          COVID
2021    12.488.382        202          22.87          COVID sonrası en düşük
2022    36.198.982        370          37.30          Güçlü toparlanma
2023    31.542.707        366          89.66          Enflasyon ivmesi başlıyor
2024    33.149.053        452          150.64
2025    27.932.751        379          208.18
```

> Kaynak: `turkiye_sinema_pazar_verileri.csv` — boxofficeturkiye.com "Tüm Yıl Karşılaştırması" tablosu

**Temel çıkarımlar:**

- 2016–2019 arasında bilet fiyatı sabit kaldı (11–16 TL arası); enflasyon etkisi bu dönemde minimal.
- 2022'den itibaren enflasyon bilet fiyatlarını dramatik biçimde artırdı: 2 yılda **37 TL → 150 TL** (%306).
- Seyirci sayısı ile bilet fiyatı **ters ilişki** sergilemiyor gibi görünse de 2023–2025 verileri, fiyat artışının seyirciyi caydırdığına işaret ediyor.
- `pazar_verileri.csv` ile `full_dataset.csv` arasındaki toplam seyirci farkı (~600.000 kişi), yıllık listedeki Top 200 kırpmasından kaynaklanmaktadır; pazar tablosu tüm filmleri kapsıyor.

---

## 6. Veri Kalitesi ve Eksiklikler

### Eksik Değerler

| Sütun | Eksik Kayıt | Oran | Açıklama |
|-------|------------|------|----------|
| `IMDb_Puani` | 432 | %21.9 | Çoğunlukla yeni çıkan veya düşük profilli Türk filmleri |
| `Yapimci` | ~400+ | ~%20 | Yabancı yapımlarda genellikle boş |
| `Ulke` | 4 | %0.2 | Çok küçük, göz ardı edilebilir |
| `Tur` | 3 | %0.2 | Çok küçük, göz ardı edilebilir |

### Bilinen Sorunlar

1. **Yıl sınırı etkisi:** Her yıl en fazla 200 film listeye alınmaktadır. Gerçek vizyona giren film sayısı daha yüksek olabilir (örn. 2018'de 430 yeni film girilmiş ancak 200'ü kayıtlı).

2. **Vizyon tarihi vs. liste yılı uyumsuzluğu:** D.I.S.C.O. gibi Ocak 2026'da vizyona giren filmler `Liste_Yili = 2025` olarak etiketlenmiştir; yıl bazlı analizde dikkat edilmeli.

3. **Ortak yapımlar:** `Ulke` alanında "Türkiye, ABD" gibi çoklu değerler bulunabiliyor; ülke bazlı analiz için önce normalize edilmesi gerekiyor.

4. **Tür alanı normalize edilmemiş:** `3 Boyutlu` bir tür değil, gösterim formatı olmasına rağmen tür listesine eklenmiş.

5. **`Oyuncular` sütunu kırpılmış:** Genellikle yalnızca ilk 5 oyuncu kayıtlıdır.

6. **`Yapimci` sütunu dağınık:** Virgül, nokta ve farklı ayraçlar kullanılmış; birleştirme ve bölme analizi zorlaştırabiliyor.

---

## 7. Kurulum ve Kullanım

### Gereksinimler

```bash
pip install requests beautifulsoup4 pandas isodate
```

### Veri Toplamayı Başlatmak

```bash
# Aşama 1: Yıllık tabloları çek
python scraper.py

# Aşama 2: Film detaylarını zenginleştir (uzun sürebilir)
python detay_scraper.py

# Aşama 3: Pazar özetini çek
python pazar_verileri_scraper.py
```

### Analizi Çalıştırmak

```bash
python analyze.py
```

### Python ile Veri Okumak

```python
import pandas as pd

df = pd.read_csv("turkiye_sinema_full_dataset.csv", encoding="utf-8-sig")

# Yıllara göre toplam seyirci
print(df.groupby("Liste_Yili")["Toplam_Seyirci"].sum())

# En çok izlenen Türk filmleri
turkiye = df[df["Ulke"] == "Türkiye"].sort_values("Toplam_Seyirci", ascending=False)
print(turkiye.head(10)[["Film_Adi", "Liste_Yili", "Toplam_Seyirci"]])
```

> **Önemli:** Dosyayı `encoding="utf-8-sig"` parametresiyle açmak gerekmektedir; aksi hâlde BOM karakteri nedeniyle ilk sütun adı hatalı okunur.

---

*Veri kaynağı: [boxofficeturkiye.com](https://boxofficeturkiye.com) — Yalnızca araştırma ve eğitim amaçlıdır.*

---

---

# v2 — Öznitelik Mühendisliği

Bu bölüm, `data/processed/turkiye_sinema_full_dataset.csv` dosyasının makine öğrenmesi için tek bir **öznitelik matrisine** (`data/processed/ml_ready_dataset.csv`) dönüştürülmesini anlatır. v2 boyunca yalnızca veriyi “daha çok sütun” yapmak değil; **veri sızıntısını engellemek**, **eksikliğin bilgisini korumak** ve **kategorik patlamayı** (ör. onlarca dağıtımcı için one-hot) kontrol etmek hedeflendi. Aşağıda her ana adımda karşılaşılan problem ile seçilen çözüm birlikte verilmiştir; ayrıntılı teşhis günlüğü [Bölüm 10](#10-veri-temizleme-süreci-ve-karşılaşılan-sorunlar)'dadır.

---

## 8. Proje Yapısı (v2)

v2'de dosyalar işlevlerine göre klasörde toplandı. Scriptler proje kökünü `Path(__file__).parent.parent` ile çözer; `__file__` her zaman scriptin yolu olduğundan hem `python scripts/feature_engineering.py` hem `cd scripts` sonrası `python feature_engineering.py` kök olarak aynı `data/` ağacını bulur.

```
box_office_project/
│
├── scripts/
│   ├── scraper.py                  # Aşama 1: Yıllık gişe tabloları
│   ├── detay_scraper.py            # Aşama 2: Film detay zenginleştirme
│   ├── pazar_verileri_scraper.py   # Aşama 3: Yıllık pazar özeti
│   ├── feature_engineering.py      # Aşama 4: ML öznitelik mühendisliği
│   ├── imdb_doldurucu.py           # Yardımcı: OMDb ile IMDb puanı doldurma
│   └── oyuncu_doldurucu.py         # Yardımcı: OMDb ile oyuncu/yönetmen (deneysel)
│
├── data/
│   ├── raw/
│   │   ├── turkiye_sinema_veriseti_2016_2025.csv
│   │   └── turkiye_sinema_pazar_verileri.csv
│   ├── interim/                    # Checkpoint + API ara çıktıları (gerektiğinde oluşur)
│   └── processed/
│       ├── turkiye_sinema_full_dataset.csv
│       └── ml_ready_dataset.csv
│
├── README.md
├── requirements.txt
└── venv/
```

`detay_scraper.py` ara kaydı `data/interim/zengin_veriseti_checkpoint.csv` dosyasına yazar; `imdb_doldurucu.py` ise belgedeki ara CSV yapısı üzerinden ilerlemek üzere tasarlanmıştır (dosyalar yoksa scripti kullanmadan önce ara listeleri oluşturmak veya güncellenmiş ara dosyaları sağlamak gerekir).

---

## 9. Öznitelik Mühendisliği

### 9.1 Çalıştırma ve ön koşullar

| | |
|--|--|
| **Script** | `scripts/feature_engineering.py` |
| **Girdi** | `data/processed/turkiye_sinema_full_dataset.csv`, `data/raw/turkiye_sinema_pazar_verileri.csv` |
| **Çıktı** | `data/processed/ml_ready_dataset.csv` |

Proje kökünden örnek:

```bash
python scripts/feature_engineering.py
```

**Bağımlılıklar:** `requirements.txt`; tam hat için ek olarak detay scraper’a `isodate`, istemcilere `numpy` ile birlikte `lxml` (BeautifulSoup kullanımı). Tüm çıktılarda BOM sorunundan kaçınmak için `encoding="utf-8-sig"` kullanılıyor.

---

### 9.2 Adım adım işlem hattı

#### Adım 1 — Kimlik ve gürültülü sütunları eleme

- **Ne:** `Film_Linki` URL’sinin son segmenti (`dag-2--2013143`) benzersiz anahtardır (CSV’ye index olarak yazılır).
- **Problem → çözüm:** `Yapimci` çok eksik ve metin olarak dağınık → girdi düşürüldü. `Hafta_Sayisi` hedef ile **sonuçsal** bağlantılı (uzun koşum ↔ yüksek seyirci) → **sızıntı** nedeniyle düşürüldü ([10.7](#107-veri-sızıntısı-ve-sıralı-skorların-tutarlılığı)).

#### Adım 2 — Yıllık pazar bağlamı

- **Ne:** Pazar özeti `Liste_Yili` üzerinden **left merge** ile eklenir: `Sektor_Toplam_Seyirci`, `Ort_Bilet_TL`.
- **Problem → çözüm:** `merge()` index’i sıfırlar → önce `reset_index()` ile `Film_Linki` sütun yapılıp birleştirme sonrası yeniden index’lenir ([10.4](#104-feature-engineeringde-index-kaybı)).

#### Adım 3 — Hedef

```
Log_Toplam_Seyirci = np.log1p(Toplam_Seyirci)
```

- **Problem → çözüm:** Seyirci sağa çarpık → `log1p` ile regresyon ve tarihsel skorların ölçeği uyumlu hale gelir; `Toplam_Seyirci` referans için korunur.

#### Adım 4 — Bayraklar, mevsim, “devam filmi” ve rekabet indeksi

| Öznitelik | Mantık | Problem → çözüm |
|-----------|--------|----------------|
| `Sure_Dakika` | Scraper’dan gelen **0** → `NaN` | Sahte sıfır yanlış sinyal üretirdi ([10.2](#102-sure_dakika-veri-kalitesi)). |
| `Is_Pandemi` | Vizyon tarihinin **yılı** 2020 veya 2021 → 1 | COVID için kaba takvim sinyali (daha ince tarih politikası gelecekte eklenebilir). |
| `Is_Yerli` | `Ulke` içinde `"Türkiye"` | Ortak yapımlar için metin kullanımdan sonra **`Ulke` düşürülür**. |
| `IMDb_Yok` | IMDb yok → 1 | Eksiklik rastgele değildir (`IMDb_Yok` ile MNAR örüntüsü) ([10.3](#103-imdb-eksikliği--api-ile-otomasyon)). |
| `Is_Devam_Filmi` | `is_devam_film()` (regex + istisna) | Başlıktan sequel/sıra yakalama; yanlış pozitifi azaltmak için başlangıçtaki sıra kalıpları ve belirli özel durumlar elendi (`7. Koğuştaki…`, başta iki haneli sayı vb.). Kod: `scripts/feature_engineering.py` içinde. |
| `Mevsim_*` | Türkiye’de sık kullanılan meteorolojik mevsim (Mart–Mayıs ilkbahar, … Aralık–Şubat kış) ile **4 ikili** sütun | `Vizyon_Tarihi` bozuksa mevsim sütunları anlamlı olmayabilir. |

**Rekabet indeksi:** Her filmin `Vizyon_Tarihi` için **ISO 8601 yıl + hafta** (`strftime("%G_%V")`) hesaplanır. `Rekabet_Indeksi`, veri kümesinde aynı ISO haftasında vizyona giren **diğer** film sayısıdır (yalnızca kendisi varsa **0**). Vizyon tarihi `NaN` ise sütun `NaN`. Liste dışı yapımlar sayılmadığından değer alt sınır rekabet ölçüsüdür.

#### Adım 5 — Tarihsel sıra ve Bayesian yumuşatma

Veri **`Vizyon_Tarihi`** ile eski → yeniye sıralanır. Her satır için skor **önce** hesaplanır, **sonra** aynı satır güncellenerek “geçmiş” sözlüklere eklenir; böylece o filme ve geleceğe **sızmaz**.

- **`Yonetmen_Skor`** ve **`Yonetmen_Film_Sayisi`:** Yönetmenin daha önceki filmleri üzerinden `Log_Toplam_Seyirci` için **Bayesian güç ortalaması**: kişisel geçmiş ortalaması (x̄), geçmiş film sayısı n, küresel önsel µ₀ ve yumuşatma katsayısı k=5 birleştirilerek kodda `(n × x̄ + k × µ₀)/(n+k)` biçiminde hesaplanır (`SMOOTHING_K`, güncellenen `global_ort`; geçmiş yoksa `PRIOR = np.log1p(50_000)`).

- **`Oyuncu1_Skor`**, **`Oyuncu2_Skor`**, **`Oyuncu3_Skor`**, **`Kadro_Veri_Var`:** Oyuncu listesinden ilk üç isim için aynı yumuşatmalı sıralı mantık.  
  **`Oyuncular` yoksa** üç skor `NaN`, `Kadro_Veri_Var = 0`; **liste kısa ise** kalan slotlar **bilinçli `NaN`**. Böylece tek sayısal `Kadro_Skor` ortalamasının sıkıştırdığı bilgi korundu ([10.6](#106-oyuncu-verisi-eksikliği-ve-kadro-özelliklerinin-evrimi)).

#### Adım 6 — Tür sadeleştirme ve dağıtıcıyı sıkıştırma

**Tür:** `Tur.str.get_dummies(sep=", ")`, ardından toplamı **10’un altında** olan türler eleniyor (espor ve benzeri seyreklikler). Sütun adları `temiz_sutun_adi()` ile **ASCII dostu** hale getiriliyor (ör. `Tur_Bilim_Kurgu`).  
**Dağıtıcı:** One-hot yerine **`Dagitimci_Skor`**: o ana kadarki aynı dağıtıcının geçmiş `Log_Toplam_Seyirci` ortalaması; geçmiş yoksa o güne dek tüm film ortalaması; globalde hiç gözlem yoksa ilk satırda `NaN` (veri setinde **1 satır**) ([10.8](#108-dagitimci-sirali-skoru)).

#### Adım 7 — Dışa aktarım

- `ml_ready_dataset.csv`, `Film_Linki` index’li, **`utf-8-sig`**; çalıştırma sonunda eksik özeti yazdırılır.

---

### 9.3 ML-ready veri seti şeması

| | |
|--|--|
| **Dosya** | `data/processed/ml_ready_dataset.csv` |
| **Boyut** | **1.976 satır × 52 sütun** |

#### Sütun grupları

| Grup | Sütunlar | Adet |
|------|-----------|------|
| Kimlik / zaman | `Film_Linki`, `Film_Adi`, `Vizyon_Tarihi`, `Liste_Yili` | 4 |
| Sayısal ham | `Toplam_Seyirci`, `Sure_Dakika`, `IMDb_Puani` | 3 |
| Hedef | `Log_Toplam_Seyirci` | 1 |
| Makro bağlam | `Sektor_Toplam_Seyirci`, `Ort_Bilet_TL` | 2 |
| Bayraklar | `Is_Pandemi`, `Is_Yerli`, `IMDb_Yok`, `Is_Devam_Filmi` | 4 |
| Mevsim (OHE) | `Mevsim_Ilkbahar`, `Mevsim_Yaz`, `Mevsim_Sonbahar`, `Mevsim_Kis` | 4 |
| Rekabet indeksi | `Rekabet_Indeksi` | 1 |
| Geçmiş başarı (sıralı) | `Yonetmen_Skor`, `Yonetmen_Film_Sayisi`, `Oyuncu1_Skor`, `Oyuncu2_Skor`, `Oyuncu3_Skor`, `Kadro_Veri_Var`, `Dagitimci_Skor` | 7 |
| Tür (güncel OHE listesi) | `Tur_3_Boyutlu`, `Tur_Aile`, `Tur_Aksiyon`, `Tur_Animasyon`, `Tur_Belgesel`, `Tur_Bilim_Kurgu`, `Tur_Biyografi`, `Tur_Dram`, `Tur_Fantastik`, `Tur_Genclik`, `Tur_Gerilim`, `Tur_Gizem`, `Tur_IMAX`, `Tur_Komedi`, `Tur_Korku`, `Tur_Macera`, `Tur_Muzik`, `Tur_Muzikal`, `Tur_Romantik`, `Tur_Romantik_Komedi`, `Tur_Savas`, `Tur_Spor`, `Tur_Suc`, `Tur_Tarihi` | 24 |
| Metin | `Yonetmen`, `Oyuncular` | 2 |

Eğitimde metinleri gizlemek için `Yonetmen` / `Oyuncular` çıkarılabilir; ham referans olarak dosyada bırakıldı.

---

### 9.4 Tasarım kararları ve gerekçeler

| Karar | Gerekçe |
|-------|---------|
| `Yapimci` yok | Eksik + dağınık metin; sinyal/gürültü zayıf |
| `Ulke` ham yok | `Is_Yerli` özü yeterli; çok-etiketli yapı doğrudan OHE olarak şişirdi |
| `Hafta_Sayisi` yok | Sonuç değişkene yakın bilgi → sızıntı riski ([10.7](#107-veri-sızıntısı-ve-sıralı-skorların-tutarlılığı)) |
| `NaN` dışarıda tutulması | Özellikle IMDb ve kadro süresi eksikleri bilgilendiricidir |
| `IMDb_Yok` ve `Kadro_Veri_Var` | Eksikliğin rastgele olmadığı filmlerde yardımcı kovaryat |
| Bayesian `SMOOTHING_K = 5` ve `PRIOR` | Az geçmişi olan kişilerde uçmuş ortalamaların basılması |
| Üç oyuncu kolonu | 2 oyunculu filmde fazla slotların `NaN` kalması doğal |
| `Dagitimci_Skor` | Yüksek kardinalite yerine sıralı, sızdırmaz sürekli sinyal |
| `Rekabet_Indeksi` | Aynı ISO haftasında (veri kümesinde) **diğer** vizyon sayısı; hedef sızdırmaz; liste dışı filmler yoktur ([9.2 — Adım 4](#92-adım-adım-işlem-hattı)) |
| Tür başlığı normalizasyonu | Unicode/boşluk sorunları ve formül araçları için ASCII sütun adı |

---

### 9.5 Eksik değer özeti (güncel)

Üretilmiş `ml_ready_dataset.csv` üzerinden tipik görünüm (*son çalıştırmaya göre*):

| Sütun | Eksik | Not |
|-------|-------|-----|
| `IMDb_Puani` | 101 (**%5,1**) | `IMDb_Yok == 1` ile birlikte kullanılıyor |
| `Sure_Dakika` | ~2 | Ham veride doğrulanamayan süreler |
| `Yonetmen` | ~4 | Ham metin; skor küreselliğe yakınsıyor |
| `Oyuncular` / ilk iki oyuncu skoru | **337** | `Kadro_Veri_Var = 0` |
| `Oyuncu3_Skor` | ~350 kayıtta `NaN` | İlk **iki** isim kadar oyuncudan sonra üçüncü slot **bilinçli boş** bırakıldı |
| `Dagitimci_Skor` | **1** | Kronolojik sıranın ilk elemanında global geçmiş yokken |

---

## 10. Veri Temizleme Süreci ve Karşılaşılan Sorunlar

Bu bölüm projenin her aşamasında karşılaşılan gerçek sorunları, teşhis sürecini ve uygulanan çözümleri belgelemektedir. Doğrusal bir süreç gibi görünse de her adım kendi içinde bir keşif döngüsü barındırıyordu.

---

### 10.1 CSV Encoding Sorunu (BOM)

**Sorun:** Ham veri seti `pd.read_csv()` ile okunduğunda `KeyError: 'Film_Adi'` hatası alındı. Sütun adı gerçekten yokmuş gibi görünüyordu.

**Teşhis:** DataFrame'in `.columns` listesi incelendiğinde ilk sütunun `'Film_Adi'` değil `'\ufeffFilm_Adi'` olduğu görüldü. `\ufeff`, UTF-8 dosyalarının başına Windows araçlarınca eklenen bir **BOM (Byte Order Mark)** karakteridir; Python'un varsayılan `utf-8` codec'i bu karakteri şeffaf biçimde atlamaz.

**Çözüm:** `pd.read_csv(..., encoding="utf-8-sig")` parametresi BOM'u otomatik olarak yoksayar. Projedeki tüm `read_csv` ve `to_csv` çağrıları bu encoding'e geçirildi.

```python
# Hatalı
df = pd.read_csv("veri.csv")

# Doğru
df = pd.read_csv("veri.csv", encoding="utf-8-sig")
```

---

### 10.2 `Sure_Dakika` Veri Kalitesi

**Sorun:** Film süresi (`Sure_Dakika`) sütununda bir kısım filmde `0` değeri vardı. Bu filmler scraping sırasında süre bilgisi alınamamış ancak varsayılan olarak `0` yazılmıştı.

**Teşhis:** `df[df["Sure_Dakika"] == 0]` sorgusu çalıştırıldı. Sonuç: 9 film. Bu filmlerin bazıları tanınan yapımlardı (Azem 3, Ammar 2 gibi), bu da `0`'ın gerçek bir veri değil kayıp olduğunu doğruladı.

**Çözüm:** İki aşamalı yaklaşım uygulandı:

1. Filmlerin gerçek süreleri çevrimiçi kaynaklardan manuel olarak araştırıldı. Bulunan 7 film için doğru değerler `full_dataset.csv`'ye yazıldı.
2. Bulunamayan 2 film için `0 → NaN` dönüşümü `feature_engineering.py`'de kalıcı hâle getirildi.

```python
df.loc[df["Sure_Dakika"] == 0, "Sure_Dakika"] = np.nan
```

Bu yaklaşım `0` değerini modele yanlış bilgi olarak sunmak yerine eksikliği açıkça işaretler (`feature_engineering.py` ile üretilen matriste güncel hali budur).

---

### 10.3 IMDb Eksikliği — API ile Otomasyon

**Sorun:** 1.976 filmin 432'sinde (%21.9) IMDb puanı yoktu. Bu oran, öznitelik olarak `IMDb_Puani`'nı kullanmayı riskli hâle getiriyordu.

**Teşhis:** Eksik filmlerin büyük bölümünün düşük profilli Türk yapımları olduğu görüldü. IMDb'de kayıtları var mıydı? Bunu test etmenin en iyi yolu bir API denemesiydi.

**Çözüm:** OMDb API entegrasyonu (`scripts/imdb_doldurucu.py`) ile her film için 3 kademeli arama stratejisi uygulandı:

1. Türkçe başlık + yıl
2. Türkçe başlık (yılsız)
3. ASCII normalleştirilmiş başlık + yıl (Türkçe karakterler İngilizceye dönüştürüldü)

Her 20 filmde bir **checkpoint** kaydedildi; böylece script kesilirse sıfırdan başlanmadı. API hız sınırını aşmamak için istekler arasına `time.sleep(0.25)` eklendi.

**Sonuç — Aşama 1 (OMDb API):** 432 eksikten 193 tanesi otomatik olarak dolduruldu (432 → 239, %12.1).

**Sonuç — Aşama 2 (Manuel araştırma):** Kalan 239 eksikten 138 tanesi çevrimiçi kaynaklardan araştırılıp elle eklendi (239 → 101, %5.1).

Hâlâ bulunamayanlar (101 film) için `IMDb_Yok = 1` bayrağı eklenerek eksiklik örüntüsü modele taşındı.

---

### 10.4 Feature Engineering'de Index Kaybı

**Sorun:** `feature_engineering.py`'de `Film_Linki` sütunu index olarak ayarlandıktan sonra `df.merge()` çağrıldığında `KeyError: 'Film_Linki'` hatası alındı.

**Teşhis:** Pandas'ın `merge()` fonksiyonu, mevcut index'i korumadan yeni bir integer index atar. `Film_Linki` index olduğu için merge sırasında erişilemez hâle geldi.

**Çözüm:** Merge işlemi etrafında açık bir `reset_index` / `set_index` döngüsü kuruldu:

```python
df = df.reset_index()            # Film_Linki → normal sütun
df = df.merge(pazar, ...)        # merge güvenli
df = df.set_index("Film_Linki") # tekrar index'e al
```

Teşhis küçük bir `print(df.columns)` çağrısıyla yapıldı.

---

### 10.5 Terminal Unicode Hatası

**Sorun:** API script'leri çalıştırılırken Türkçe karakter içeren film adları yazdırıldığında `UnicodeEncodeError: 'charmap' codec can't encode character` hatası alındı.

**Teşhis:** Windows PowerShell terminali varsayılan olarak `cp1254` (Windows-1254) encoding kullanıyordu. Bazı özel karakterler bu kod sayfasında karşılıksız kalıyordu.

**Çözüm:** Script'lerin başında `sys.stdout` UTF-8 olarak yeniden sarmalandı:

```python
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
```

`errors="replace"` parametresi, hâlâ encode edilemeyen karakterleri `?` ile değiştirerek script'in çökmeden devam etmesini sağladı.

---

### 10.6 Oyuncu verisi eksikliği ve kadro özelliklerinin evrimi

**Sorun:** 1.976 filmin yaklaşık 340’ında (%17,2) `Oyuncular` verisi yoktu. Oyuncuya dayalı öznitelikler bu yüzden **sistematik boş** kalabilirdi ve model yalancı sıfırlarla oyuncunun “orta” olduğunu sanabilirdi.

**Teşhis ve karar süreci — üç aşamalı:**

**Aşama 1 — Otomasyon denendi.** `oyuncu_doldurucu.py` ile OMDb API üzerinden doldurma denendi; script **yavaş** kaldı ve **kesinti** yaşandı.

**Aşama 2 — Yapı analizi.** Boş oyuncunun tür dağılımı incelendi:

```
Animasyon      → 313 film  (%92)
Canlı oyuncu   →  27 film  (%8)
```

Çoğu kayıp **animasyon** (sayfa yapısı / seslendirme listesi nedeniyle) olduğundan, tüm liste için API brute-force beklenenden az getiri vadeder.

**Aşama 3 — Öncelikli güncelleme.** Canlı oyunculu üst sıra filmlerde en yüksek etki için seçilen 3 film manuel araştırıldı:

| Film | Yönetmen | Oyuncular |
|------|----------|-----------|
| Aile Arasında | Ozan Açıktan | Engin Günaydın, Demet Evgâr, Erdal Özyagcilar |
| Orman Çocuğu | Jon Favreau *(zaten vardı)* | Neel Sethi, Bill Murray, Ben Kingsley |
| Beterböcek Beterböcek | Tim Burton | Michael Keaton, Winona Ryder, Catherine O'Hara |

**Çözüm (v2 matris mimarisi):** Tek bir `Kadro_Skor` yerine üç ayrı **`Oyuncu1_Skor` … `Oyuncu3_Skor`** + **`Kadro_Veri_Var`** kullanılıyor: liste tamamen eksikken skor kolonları `NaN`, bayrak 0 olur; yalnızca bir veya iki isim olduğunda kalan kolonlar **bilinçli `NaN`** bırakılır ki ağaç / eksik-değeri destekleyen modeller isimsayı yapısal bilgisinden yararlansın.

**Ders:** Eksikliği görmezden gelmeden önce **kimde** eksik olduğunun tipolojisini çıkarmak, hangi araçların hakkını vereceğini netleştirdi ([9.5](#95-eksik-değer-özeti-güncel)).

---

### 10.7 Veri sızıntısı ve sıralı skorların tutarlılığı

**Sorun:** `Hafta_Sayisi` ilk etapta özellik adayıydı; oysa **gösterim süresi** hedef olan seyirci hacminden doğan bir **fonksiyon** olabilir.

**Teşhis:** Süreleri modele dahil etmek, pratikte hedef çevresinden bilgi sızdırır — üretim bağlamında “yayına düşük performans bile olsa daha çok yerde tutulmuş” yapı yapay şekilde yüksek R² üretirdi.

**Çözüm:** `Hafta_Sayisi` `feature_engineering.py` çizgisinden çıkarıldı. **`Yonetmen_Skor`**, oyuncu skorları ve **`Dagitimci_Skor`** sıralı tarih sırasına dayanarak üretilir: skor **hesaplanır**, ardından aynı filmin çıktısı “geçmiş” havuzlarına yazılır. Böylece tek film veya geleceğin etketi **aynı sırayı okuyan kod** için erişilemez kalır ([9.2 — Adım 5](#92-adım-adım-işlem-hattı)).

---

### 10.8 Dagitimci sirali skoru

**Sorun:** Aktif distribütör listesi kategorisel olarak yüzün üzerine çıkıyordu; one-hot matrisi **seyrek** ve parametre seçimine **duyarlı** hâle geliyordu.

**Çözüm:** Çok düzeyli `Dagitimci_*` kolonları yerine sıralı **tek özellik** `Dagitimci_Skor` üretildi: tarih sırasında güncellenen, ilgili dağıtıcının o güne kadarki **`Log_Toplam_Seyirci` ortalaması** ([9.2 — Adım 6](#92-adım-adım-işlem-hattı)). Boyut küçüldü; sızdırmazlık yine sıralı pencerenin garantisi altında kalır.

---


*Veri kaynağı: [boxofficeturkiye.com](https://boxofficeturkiye.com) — Yalnızca araştırma ve eğitim amaçlıdır.*
