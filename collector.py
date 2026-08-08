import json
from datetime import datetime
import pandas as pd
from pykrx import stock
import FinanceDataReader as fdr

def fetch_krx_stock_data():
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주식 데이터 수집 시작...")

    try:
        df_market = stock.get_market_ohlcv_by_ticker(today_str, market="ALL")
        df_cap = stock.get_market_cap_by_ticker(today_str, market="ALL")
        df_fundamental = stock.get_market_fundamental_by_ticker(today_str, market="ALL")

        df_combined = df_market.join(df_cap[['시가총액']]).join(df_fundamental[['PER', 'PBR']])
        
        krx_listing = fdr.StockListing('KRX')
        name_market_map = krx_listing.set_index('Code')[['Name', 'Market']].to_dict(orient='index')

        stocks = []
        for ticker, row in df_combined.iterrows():
            if ticker in name_market_map:
                name = name_market_map[ticker]['Name']
                market = name_market_map[ticker]['Market']
                
                close_price = int(row['종가'])
                change_rate = float(row['등락률']) if '등락률' in row and not pd.isna(row['등락률']) else 0.0
                marcap_eok = round(int(row['시가총액']) / 100_000_000, 2)
                
                per = float(row['PER']) if not pd.isna(row['PER']) and row['PER'] != 0 else None
                pbr = float(row['PBR']) if not pd.isna(row['PBR']) and row['PBR'] != 0 else None

                if marcap_eok >= 100 and close_price > 0:
                    stocks.append({
                        "code": str(ticker),
                        "name": name,
                        "market": market,
                        "price": close_price,
                        "change_rate": change_rate,
                        "marcap": marcap_eok,
                        "per": per,
                        "pbr": pbr
                    })

        stocks.sort(key=lambda x: x['marcap'], reverse=True)

        result_data = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
            "total_count": len(stocks),
            "stocks": stocks
        }

        with open('stocks.json', 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 수집 완료! 총 {len(stocks)}개 종목 저장됨.")
    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")
        raise e

if __name__ == "__main__":
    fetch_krx_stock_data()
