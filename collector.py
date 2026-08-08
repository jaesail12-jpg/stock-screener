import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def parse_stock_detail(code):
    """네이버 증권 개별 종목 페이지에서 PBR 및 연간 재무제표 추이 스크래핑"""
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    pbr = None
    recent_rev, recent_op, recent_margin = None, None, None
    history = {"years": [], "revenues": [], "op_incomes": [], "op_margins": []}

    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. PBR 파싱
        pbr_tag = soup.find('em', id='_pbr')
        if pbr_tag:
            try:
                pbr = float(pbr_tag.text.replace(',', '').strip())
            except ValueError:
                pass

        # 2. 기업분석 재무제표 연간 추이 파싱
        cop = soup.find('div', class_='section cop_analysis')
        if cop:
            table = cop.find('table')
            if table:
                # 연도 헤더 추출
                thead_trs = table.find('thead').find_all('tr')
                if len(thead_trs) >= 2:
                    ths = thead_trs[1].find_all('th')[:4]
                    history['years'] = [th.text.strip().replace('\n', '').replace('\t', '') for th in ths]

                # 매출액, 영업이익, 영업이익률 행 추출
                tbody_trs = table.find('tbody').find_all('tr')
                for tr in tbody_trs:
                    th = tr.find('th')
                    if not th:
                        continue
                    title = th.text.strip()
                    tds = tr.find_all('td')[:len(history['years'])]

                    vals = []
                    for td in tds:
                        v_str = td.text.strip().replace(',', '').replace('N/A', '').replace('-', '')
                        try:
                            vals.append(float(v_str))
                        except ValueError:
                            vals.append(None)

                    if '매출액' in title and '률' not in title:
                        history['revenues'] = vals
                    elif '영업이익률' in title:
                        history['op_margins'] = vals
                    elif '영업이익' in title and '률' not in title:
                        history['op_incomes'] = vals

                # 최근 유효 수치 세팅
                for v in reversed(history['revenues']):
                    if v is not None:
                        recent_rev = v
                        break
                for v in reversed(history['op_incomes']):
                    if v is not None:
                        recent_op = v
                        break
                for v in reversed(history['op_margins']):
                    if v is not None:
                        recent_margin = v
                        break

    except Exception as e:
        print(f"[{code}] 상세 파싱 예외: {e}")

    return pbr, recent_rev, recent_op, recent_margin, history

def fetch_naver_stock_list(sosok=0):
    stocks = []
    market_label = "KOSPI" if sosok == 0 else "KOSDAQ"
    
    # 코스피/코스닥 상위 2페이지씩 (총 200개 종목 수집)
    for page in range(1, 3):
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
                stock_code = name_tag['href'].split('code=')[-1].zfill(6)
                
                try:
                    price = int(cols[2].text.strip().replace(',', ''))
                    change_str = cols[4].text.strip().replace('%', '').replace('+', '').strip()
                    change_rate = float(change_str) if change_str and change_str != 'N/A' else 0.0
                    marcap_str = cols[6].text.strip().replace(',', '')
                    marcap = float(marcap_str) if marcap_str and marcap_str != 'N/A' else 0.0
                    per_str = cols[10].text.strip().replace(',', '')
                    per = float(per_str) if per_str and per_str != 'N/A' else None
                    
                    # 개별 종목 재무 추이 수집
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
                    time.sleep(0.05)
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"목록 수집 오류: {e}")
            continue
            
    return stocks

def main():
    print("주식 데이터 수집 중...")
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
        
    print(f"총 {len(all_stocks)}개 종목 수집 완료!")

if __name__ == "__main__":
    main()
