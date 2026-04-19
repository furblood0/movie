import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import os

def parse_runtime(runtime_str):
    """ '2s 28dk' formatını toplam dakikaya çevirir """
    try:
        hours = re.search(r'(\d+)s', runtime_str)
        minutes = re.search(r'(\d+)dk', runtime_str)
        
        total = 0
        if hours: total += int(hours.group(1)) * 60
        if minutes: total += int(minutes.group(1))
        return total
    except:
        return 0

def get_movie_details(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}

        # 1. Tür (Genre) - Teklifteki 'genre' değişkeni 
        genre_header = soup.find('strong', string="Filmin Türü")
        details['genre'] = genre_header.find_next('p').text.strip() if genre_header else "Unknown"

        # 2. Süre (Runtime) - Teklifteki 'runtime_minutes' değişkeni 
        runtime_span = soup.find('span', class_='title__runtime')
        details['runtime_minutes'] = parse_runtime(runtime_span.text.strip()) if runtime_span else 0

        # 3. Ülke (is_domestic) - Teklifteki 'is_domestic' ve 'language' değişkenleri 
        country_header = soup.find('strong', string="Ülke")
        country_text = country_header.find_next('p').text.strip() if country_header else ""
        details['is_domestic'] = 1 if "Türkiye" in country_text else 0
        details['language'] = "Turkish" if details['is_domestic'] == 1 else "Foreign"

        # 4. Yaş Sınırı (Rating) - Teklifteki 'rating' değişkeni 
        rating_wrapper = soup.find('div', class_='title-content-rating-wrapper')
        if rating_wrapper:
            rating_span = rating_wrapper.find('span')
            details['rating'] = rating_span.get('title', 'Genel İzleyici') if rating_span else 'Genel İzleyici'
        else:
            details['rating'] = 'Genel İzleyici'

        return details
    except Exception as e:
        print(f"URL işlenirken hata: {url} -> {e}")
        return None

def main():
    # DOSYA YOLLARI TANIMLAMALARI
    input_file = os.path.join('..', 'data', 'raw', 'raw_movie_data.csv')
    output_dir = os.path.join('..', 'data', 'processed')
    output_file = os.path.join(output_dir, 'enriched_movie_data.csv')
    partial_file = os.path.join(output_dir, 'enriched_movie_data_partial.csv')

    # İşlenmiş veriler için klasörün var olduğundan emin olalım
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"Hata: Girdi dosyası bulunamadı -> {input_file}")
        return

    df = pd.read_csv(input_file)
    print(f"Toplam {len(df)} film için detaylar toplanıyor...")

    # Başlangıç değerleri
    df['genre'] = "Unknown"
    df['runtime_minutes'] = 0
    df['is_domestic'] = 0
    df['language'] = "Foreign"
    df['rating'] = "Genel İzleyici"

    for index, row in df.iterrows():
        print(f"[{index+1}/{len(df)}] {row['movie_name']} işleniyor...")
        movie_details = get_movie_details(row['detail_url'])
        
        if movie_details:
            df.at[index, 'genre'] = movie_details['genre']
            df.at[index, 'runtime_minutes'] = movie_details['runtime_minutes']
            df.at[index, 'is_domestic'] = movie_details['is_domestic']
            df.at[index, 'language'] = movie_details['language']
            df.at[index, 'rating'] = movie_details['rating']
        
        # Her 20 filmde bir yedek al
        if (index + 1) % 20 == 0:
            df.to_csv(partial_file, index=False, encoding='utf-8-sig')
            print(f"--- Yedek kaydedildi: {partial_file} ---")
        
        time.sleep(0.5)

    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nİşlem TAMAMLANDI! '{output_file}' dosyasını kontrol edebilirsin.")

if __name__ == "__main__":
    main()