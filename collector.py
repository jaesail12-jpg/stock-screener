import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_naver_stock_data(sosok=0):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    stocks = []
    market_label = "KOSPI" if sosok == 0 else "KOSDAQ"
    
    # 코스피/코스닥 각각 상위 10페이지 (총 1,000개 종목 수집)
    for page in range(1, 11):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'euc-kr'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find('table', {'class': 'type_2'})
            if not table:
                continue
                
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) <= 1:
                    continue
                
                name_tag = cols[1].find('a')
                if not name_tag:
                    continue
                
                stock_name = name_tag.text.strip()
                stock_code = name_tag['href'].split('code=')[-1]
                
                try:
                    price = int(cols[2].text.strip().replace(',', ''))
                    
                    change_str = cols[4].text.strip().replace('%', '').replace('+', '').strip()
                    change_rate = float(change_str) if change_str and change_str != 'N/A' else 0.0
                    
                    marcap_str = cols[6].text.strip().replace(',', '')
                    marcap = float(marcap_str) if marcap_str and marcap_str != 'N/A' else 0.0
                    
                    per_str = cols[10].text.strip().replace(',', '')
                    per = float(per_str) if per_str and per_str != 'N/A' else None
                    
                    stocks.append({
                        "code": stock_code,
                        "name": stock_name,
                        "market": market_label,
                        "price": price,
                        "change_rate": round(change_rate, 2),
                        "marcap": marcap,
                        "per": per,
                        "pbr": None
                    })
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"페이지 수집 오류: {e}")
            continue
            
    return stocks

def main():
    print("주식 데이터 수집 시작...")
    kospi = fetch_naver_stock_data(sosok=0)
    kosdaq = fetch_naver_stock_data(sosok=1)
    all_stocks = kospi + kosdaq
    
    result = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
        "total_count": len(all_stocks),
        "stocks": all_stocks
    }
    
    with open('stocks.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"총 {len(all_stocks)}개 데이터 저장 완료!")

if __name__ == "__main__":
    main()
