import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import os

def scrape_box_office():
    all_movies = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for year in range(2015, 2026):
        year_movies_count = 0
        print(f"\n--- {year} yılı taranıyor ---")
        
        for page in range(1, 3): 
            if year_movies_count >= 100:
                break
                
            if page == 1:
                url = f"https://boxofficeturkiye.com/yillik/{year}"
            else:
                url = f"https://boxofficeturkiye.com/yillik/{year},sayfa-{page}"
            
            try:
                response = requests.get(url, headers=headers)
                if response.status_code != 200: break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='box-office-table')
                if not table: break
                
                rows = table.find('tbody').find_all('tr')
                
                for row in rows:
                    if year_movies_count >= 100: break
                    
                    cols = row.find_all('td')
                    if len(cols) < 8: continue
                    
                    movie_cell = cols[1].find('a', class_='movie-link')
                    movie_name = movie_cell.text.strip()
                    detail_link = "https://boxofficeturkiye.com" + movie_cell['href']
                    release_date = cols[1].find('span', class_='release-date').text.strip()
                    distributor = cols[2].text.strip()
                    audience_raw = cols[7].text.replace('.', '').strip()
                    
                    try:
                        total_audience = int(audience_raw)
                        log_audience = np.log(total_audience) if total_audience > 0 else 0
                    except:
                        continue

                    all_movies.append({
                        'movie_name': movie_name,
                        'distributor': distributor,
                        'release_date': release_date,
                        'release_year': year,
                        'total_audience': total_audience,
                        'log_total_audience': log_audience,
                        'detail_url': detail_link
                    })
                    year_movies_count += 1
                
                print(f"{year} yılından şu ana kadar {year_movies_count} film alındı...")
                time.sleep(1)
                
            except Exception as e:
                print(f"Hata: {e}")
                break

    # --- DOSYA YOLU DÜZELTMESİ ---
    # scripts içinden bir üst dizine çık (..) ve data/raw altına kaydet
    output_path = os.path.join('..', 'data', 'raw', 'raw_movie_data.csv')
    
    # Klasörün varlığından emin olalım
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df = pd.DataFrame(all_movies)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\nİşlem Tamamlandı! Toplam {len(df)} film '{output_path}' dosyasına kaydedildi.")

if __name__ == "__main__":
    scrape_box_office()