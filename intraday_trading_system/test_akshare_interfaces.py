import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def test_all_interfaces():
    """测试所有akshare接口"""
    
    stock_code = "920720"  # TCL科技
    
    print("=" * 80)
    print("测试 akshare 接口")
    print("=" * 80)
    
    # 1. 交易日历
    print("\n1. ak.tool_trade_date_hist_sina()")
    try:
        df = ak.tool_trade_date_hist_sina()
        print(f"✅ 成功，共{len(df)}条记录")
        print(df.tail(5))
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 2. 历史行情
    print("\n2. ak.stock_zh_a_hist()")
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date="20251020",
            end_date="20251029",
            adjust=""
        )
        print(f"✅ 成功，共{len(df)}条记录")
        print(df)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 3. 股票基本信息
    print("\n3. ak.stock_individual_info_em()")
    try:
        df = ak.stock_individual_info_em(symbol=stock_code)
        print(f"✅ 成功")
        print(df)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 4. 实时行情（全市场）----测试失败
    print("\n4. ak.stock_zh_a_spot_em()")
    try:
        df = ak.stock_zh_a_spot_em()
        stock_data = df[df['代码'] == stock_code]
        print(f"✅ 成功，全市场共{len(df)}只股票")
        print(stock_data)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 5. 分时数据
    print("\n5. ak.stock_intraday_sina()")
    try:
        symbol = f"sz{stock_code}"
        date = "20251028"
        df = ak.stock_intraday_sina(symbol=symbol, date=date)
        print(f"✅ 成功，共{len(df)}条记录")
        print(df.head(20))
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 6. 五档盘口
    print("\n6. ak.stock_bid_ask_em()")
    try:
        df = ak.stock_bid_ask_em(symbol=stock_code)
        print(f"✅ 成功")
        print(df)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 7. 指数实时行情---失败
    print("\n7. ak.stock_zh_index_spot_em()")
    try:
        df = ak.stock_zh_index_spot_em()
        index_data = df[df['代码'] == '000001']
        print(f"✅ 成功，共{len(df)}个指数")
        print(index_data)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 8. 指数历史数据
    print("\n8. ak.stock_zh_index_daily()")
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        print(f"✅ 成功，共{len(df)}条记录")
        print(df.tail(10))
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 9. 行业板块行情---失败
    print("\n9. ak.stock_board_industry_spot_em()")
    try:
        df = ak.stock_board_industry_spot_em()
        print(f"✅ 成功，共{len(df)}个板块")
        print(df)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 10. 涨停板池
    print("\n10. ak.stock_zt_pool_em()")
    try:
        date = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_em(date=date)
        print(f"✅ 成功，共{len(df)}只涨停股")
        print(df.head(10) if not df.empty else "今日暂无涨停股")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 11. 跌停板池
    print("\n11. ak.stock_zt_pool_dtgc_em()")
    try:
        date = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_dtgc_em(date=date)
        print(f"✅ 成功，共{len(df)}只跌停股")
        print(df.head(10) if not df.empty else "今日暂无跌停股")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 12. 个股资金流向
    print("\n12. ak.stock_individual_fund_flow()")
    try:
        df = ak.stock_individual_fund_flow(stock=stock_code, market="sz")
        print(f"✅ 成功，共{len(df)}条记录")
        print(df.tail(10))
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    test_all_interfaces()