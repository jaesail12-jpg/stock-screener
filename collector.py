import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def parse_stock_detail(code):
    """개별 종목 상세 페이지에서 PBR 및 연간 재무제표 추이 스크래핑"""
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. PBR 수집
        pbr = None
        pbr_tag = soup.find('em', id='_pbr')
        if pbr_tag:
            try:
                pbr = float(pbr_tag.text.strip().replace(',', ''))
            except ValueError:
                pass

        # 2. 연간 재무제표 추이 수집
        years, revenues, op_incomes, op_margins = [], [], [], []
        recent_rev, recent_op, recent_margin = None, None, None

        cop_section = soup.find('div', class_='section cop_analysis')
        if cop_section:
            table = cop_section.find('table')
            if table:
                # 연도 헤더 추출 (최근 4개 연도)
                thead_trs = table.find('thead').find_all('tr')
                if len(thead_trs) >= 2:
                    ths = thead_trs[1].find_all('th')[:4]
                    years = [th.text.strip().replace('\n', '').replace('\t', '') for th in ths]

                # 행 데이터 추출 (매출액, 영업이익, 영업이익률)
                tbody_trs = table.find('tbody').find_all('tr')
                for tr in tbody_trs:
                    th_text = tr.find('th').text.strip() if tr.find('th') else ''
                    tds = tr.find_all('td')[:len(years)]

                    def clean_val(td):
                        val_str = td.text.strip().replace(',', '').replace('N/A', '').replace('-', '')
                        try:
                            return float(val_str)
                        except ValueError:
                            return None

                    if '매출액' in th_text and '률' not in th_text:
                        revenues = [clean_val(td) for td in tds]
                    elif '영업이익률' in th_text:
                        op_margins = [clean_val(td) for td in tds]
                    elif '영업이익' in th_text and '률' not in th_text:
                        op_incomes = [clean_val(td) for td in tds]

                # 가장 최근 확정 실적 값 세팅
                for r in reversed(revenues):
                    if r is not None:
                        recent_rev = r
                        break
                for o in reversed(op_incomes):
                    if o is not None:
                        recent_op = o
                        break
                for m in reversed(op_margins):
                    if m is not None:
                        recent_margin = m
                        break

        history = {
            "years": years,
            "revenues": revenues,
            "op_incomes": op_incomes,
            "op_margins": op_margins
        }

        return pbr, recent_rev, recent_op, recent_margin, history
    except Exception as e:
        return None, None, None, None, {"years": [], "revenues": [], "op_incomes": [], "op_margins": []}

def fetch_naver_stock_list(sosok=0):
    """시가총액 순위 기본 목록 수집"""
    stocks = []
    market_label = "KOSPI" if sosok == 0 else "KOSDAQ"
    
    # 코스피/코스닥 각각 상위 3페이지 (총 300개 종목 상세 수집)
    for page in range(1, 4):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
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
                    
                    # 상세 재무 추이 및 PBR 수집
                    pbr, recent_rev, recent_op, recent_margin, history = parse_stock_detail(stock_code)
                    
                    stocks.append({
                        "code": stock_code,
                        "name": stock_name,
                        "market": market_label,
                        "price": price,
                        "change_rate": round(change_rate, 2),
                        "marcap": marcap,
                        "per": per,
                        "pbr": pbr,
                        "recent_revenue": recent_rev,
                        "recent_op_income": recent_op,
                        "recent_op_margin": recent_margin,
                        "history": history
                    })
                    time.sleep(0.05) # 서버 매너 대기시간
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"목록 수집 오류: {e}")
            continue
            
    return stocks

def main():
    print("주식 데이터 및 상세 재무 추이 수집 시작...")
    kospi = fetch_naver_stock_list(sosok=0)
    kosdaq = fetch_naver_stock_list(sosok=1)
    all_stocks = kospi + kosdaq
    
    result = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
        "total_count": len(all_stocks),
        "stocks": all_stocks
    }
    
    with open('stocks.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"총 {len(all_stocks)}개 종목 상세 수집 완료!")

if __name__ == "__main__":
    main()
