import os
import json
import requests
import zipfile
import io
import time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime

DART_API_KEY = os.environ.get('DART_API_KEY')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_dart_corp_codes():
    """DART 전체 고유번호(corp_code) XML 다운로드 및 주식코드(stock_code) 매핑"""
    if not DART_API_KEY:
        print("DART_API_KEY가 설정되지 않았습니다.")
        return {}
    
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={DART_API_KEY}"
    res = requests.get(url)
    
    corp_map = {}
    if res.status_code == 200:
        try:
            with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                xml_data = z.read('CORPCODE.xml')
                root = ET.fromstring(xml_data)
                for list_item in root.findall('list'):
                    stock_code = list_item.findtext('stock_code').strip()
                    corp_code = list_item.findtext('corp_code').strip()
                    if stock_code and stock_code != 'None':
                        corp_map[stock_code.zfill(6)] = corp_code
        except Exception as e:
            print(f"DART corpCode 파싱 실패: {e}")
    return corp_map

def get_dart_financials(corp_code, years=['2024', '2023', '2022']):
    """Open DART API로 연간 주요 재무제표 수집 (사업보고서 11011)"""
    history = {"years": [], "revenues": [], "op_incomes": [], "op_margins": []}
    
    if not DART_API_KEY or not corp_code:
        return None, None, None, history

    for year in sorted(years):
        url = f"https://opendart.fss.or.kr/api/fnlttSinglAcnt.json?crtfc_key={DART_API_KEY}&corp_code={corp_code}&bsns_year={year}&reprt_code=11011"
        try:
            res = requests.get(url, timeout=5)
            data = res.json()
            
            rev, op = None, None
            if data.get('status') == '000' and 'list' in data:
                for item in data['list']:
                    # 연결재무제표 또는 일반재무제표 영업이익/매출액
                    account_nm = item.get('account_nm', '')
                    if '매출액' in account_nm or '수익(매출액)' in account_nm:
                        val_str = item.get('thstrm_amount', '0').replace(',', '')
                        try: rev = round(float(val_str) / 100000000, 1) # 억원 단위 변환
                        except: pass
                    elif '영업이익' in account_nm:
                        val_str = item.get('thstrm_amount', '0').replace(',', '')
                        try: op = round(float(val_str) / 100000000, 1) # 억원 단위 변환
                        except: pass

            if rev is not None or op is not None:
                history["years"].append(f"{year}년")
                history["revenues"].append(rev)
                history["op_incomes"].append(op)
                margin = round((op / rev) * 100, 2) if (rev and op) else None
                history["op_margins"].append(margin)

            time.sleep(0.05)
        except Exception as e:
            continue

    recent_rev = history["revenues"][-1] if history["revenues"] else None
    recent_op = history["op_incomes"][-1] if history["op_incomes"] else None
    recent_margin = history["op_margins"][-1] if history["op_margins"] else None

    return recent_rev, recent_op, recent_margin, history

def fetch_stock_market_data(sosok=0, corp_map={}):
    """시가총액/현재가 기본 정보 + DART 재무정보 결합"""
    stocks = []
    market_label = "KOSPI" if sosok == 0 else "KOSDAQ"
    
    # 상위 2페이지 (총 200개 종목)
    for page in range(1, 3):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.encoding = 'euc-kr'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find('table', {'class': 'type_2'})
            if not table: continue
            
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) <= 1: continue
                
                name_tag = cols[1].find('a')
                if not name_tag: continue
                
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
                    
                    # DART 연동하여 재무 데이터 추출
                    corp_code = corp_map.get(stock_code)
                    recent_rev, recent_op, recent_margin, history = get_dart_financials(corp_code)
                    
                    # PBR 단순 계산 (시총/자본총계 대신 간단 추정)
                    pbr = round(per * (recent_margin / 100), 2) if (per and recent_margin) else None

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
                except Exception:
                    continue
        except Exception as e:
            print(f"시장 데이터 수집 오류: {e}")
            
    return stocks

def main():
    print("Open DART 데이터 수집 시작...")
    corp_map = get_dart_corp_codes()
    print(f"DART 상장법인 {len(corp_map)}개 매핑 완료")
    
    kospi = fetch_stock_market_data(sosok=0, corp_map=corp_map)
    kosdaq = fetch_stock_market_data(sosok=1, corp_map=corp_map)
    all_stocks = kospi + kosdaq
    
    result = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
        "total_count": len(all_stocks),
        "stocks": all_stocks
    }
    
    with open('stocks.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"총 {len(all_stocks)}개 DART 연동 종목 저장 완료!")

if __name__ == "__main__":
    main()
