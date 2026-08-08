import json
import requests
from bs4 import BeautifulSoup

def fetch_naver_stock_data(sosok=0):
    """
    네이버 증권 시가총액 순위 스크래핑
    sosok = 0 : KOSPI
    sosok = 1 : KOSDAQ
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    stocks = []
    
    # KOSPI/KOSDAQ 각각 상위 10페이지(페이지당 50개, 총 1,000개 종목) 수집
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
                    
                    change_str = cols[4].text.strip().replace('%', '').replace('+', '')
                    change_rate = float(change_str) if change_str and change_str != 'N/A' else 0.0
                    
                    market_cap_str = cols[6].text.strip().replace(',', '')
                    # 억 원 단위를 원 단위로 변환
                    market_cap = int(market_cap_str) * 100000000 if market_cap_str and market_cap_str != 'N/A' else 0
                    
                    per_str = cols[10].text.strip().replace(',', '')
                    per = float(per_str) if per_str and per_str != 'N/A' else None
                    
                    pbr = None  # 기본 목록 페이지 구성에 맞춰 처리
                    
                    market = "KOSPI" if sosok == 0 else "KOSDAQ"
                    
                    stocks.append({
                        "code": stock_code,
                        "name": stock_name,
                        "market": market,
                        "price": price,
                        "change_rate": round(change_rate, 2),
                        "market_cap": market_cap,
                        "per": per,
                        "pbr": pbr
                    })
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"페이지 {page} 수집 중 오류: {e}")
            continue
            
    return stocks

def main():
    print("주식 데이터 수집 시작 (Naver Finance)...")
    try:
        kospi_stocks = fetch_naver_stock_data(sosok=0)
        print(f"KOSPI {len(kospi_stocks)}개 수집 완료")
        
        kosdaq_stocks = fetch_naver_stock_data(sosok=1)
        print(f"KOSDAQ {len(kosdaq_stocks)}개 수집 완료")
        
        all_stocks = kospi_stocks + kosdaq_stocks
        
        if not all_stocks:
            print("수집된 주식 데이터가 없습니다.")
            return

        # stocks.json 저장
        with open('stocks.json', 'w', encoding='utf-8') as f:
            json.dump(all_stocks, f, ensure_ascii=False, indent=2)
            
        print(f"총 {len(all_stocks)}개 데이터 저장 완료 (stocks.json)")
        
    except Exception as e:
        print(f"데이터 수집 중 예외 발생: {e}")

if __name__ == "__main__":
    main()
