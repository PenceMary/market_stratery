import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

"""
本文件自动提炼并测试 intraday_trading_system/intraday_data_fetcher.py 中使用到的 akshare 接口。

接口清单与功能说明：
- ak.tool_trade_date_hist_sina: 获取交易日历（含历史交易日列表）
- ak.stock_zh_a_hist: 获取A股日K历史行情
- ak.stock_individual_info_em: 获取个股基本信息（东方财富）
- ak.stock_bid_ask_em: 获取个股五档盘口（东方财富）
 
- ak.stock_zh_index_spot_sina: 获取指数实时行情（新浪）
- ak.stock_zh_index_daily: 获取指数历史日线数据
- ak.stock_intraday_sina: 获取个股分时成交明细（新浪）
- ak.stock_zt_pool_em: 涨停板池（东方财富）
- ak.stock_zt_pool_dtgc_em: 跌停板池（东方财富，可能受时间或权限影响）
- ak.stock_individual_fund_flow: 个股资金流向（东方财富）
"""

# ===== 配置区域 =====
DEFAULT_STOCK_CODE = "600100"  # 上交所主板（代表性个股）
TODAY = datetime.now().strftime('%Y%m%d')
START_DATE = (datetime.now() - timedelta(days=20)).strftime('%Y%m%d')
END_DATE = TODAY
INTRADAY_DATE = TODAY  # 若非交易日可能为空，脚本会容错


def get_market_prefix(stock_code: str) -> str:
    """根据股票代码获取市场前缀（用于新浪分时接口）"""
    if stock_code.startswith('688'):
        return 'sh'  # 科创板
    elif stock_code.startswith(('83', '43', '87', '920')):
        return 'bj'  # 北交所
    elif stock_code.startswith('60'):
        return 'sh'  # 上交所主板
    elif stock_code.startswith(('00', '30')):
        return 'sz'  # 深交所
    else:
        return 'sz'  # 默认深交所


def get_market_code(stock_code: str) -> str:
    """根据股票代码获取市场标识（用于资金流向等接口）"""
    if stock_code.startswith('6'):
        return 'sh'
    elif stock_code.startswith(('0', '3')):
        return 'sz'
    elif stock_code.startswith(('8', '4', '920')):
        return 'bj'
    return 'sh'


def safe_show_df(df: pd.DataFrame, head: int = 5):
    if isinstance(df, pd.DataFrame):
        print(f"形状: {df.shape}, 列数: {len(df.columns)}")
        if not df.empty:
            print(df.head(head))
        else:
            print("返回空表")
    else:
        print(type(df), df)


def test_all_used_apis(stock_code: str = DEFAULT_STOCK_CODE):
    print("\n" + "=" * 80)
    print("🚀 开始测试 intraday_data_fetcher.py 中用到的 akshare 接口")
    print("=" * 80)
    print(f"📌 股票代码: {stock_code}")
    print(f"📅 区间: {START_DATE} ~ {END_DATE}, 分时日期: {INTRADAY_DATE}")

    # 1) 交易日历
    print("\n[1] ak.tool_trade_date_hist_sina — 交易日历")
    try:
        df = ak.tool_trade_date_hist_sina()
        print(f"✅ 记录数: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"❌ {e}")

    # 2) 指数实时（新浪）
    print("\n[2] ak.stock_zh_index_spot_sina — 指数实时（新浪）")
    try:
        df = ak.stock_zh_index_spot_sina()
        print(f"✅ 指数数: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"⚠️ 实时指数可能受时段影响: {e}")

    # 3) 指数历史（日线）
    print("\n[3] ak.stock_zh_index_daily — 指数日线历史")
    try:
        df = ak.stock_zh_index_daily(symbol='sh000001')
        print(f"✅ 记录数: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"❌ {e}")

    # 4) 个股日K（历史）
    print("\n[4] ak.stock_zh_a_hist — 个股日K历史")
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust=''  # 不复权，保持与业务方一致
        )
        print(f"✅ 记录数: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"❌ {e}")

    # 5) 个股基本信息（东财）
    print("\n[5] ak.stock_individual_info_em — 个股基本信息（东财）")
    try:
        df = ak.stock_individual_info_em(symbol=stock_code)
        print("✅ 成功")
        safe_show_df(df)
    except Exception as e:
        print(f"❌ {e}")

    # 6) 五档盘口（东财）
    print("\n[6] ak.stock_bid_ask_em — 五档盘口（东财）")
    try:
        df = ak.stock_bid_ask_em(symbol=stock_code)
        print("✅ 成功")
        safe_show_df(df)
    except Exception as e:
        print(f"⚠️ 可能受交易时段/频控影响: {e}")

    # 7) 分时成交（新浪）
    print("\n[7] ak.stock_intraday_sina — 分时成交（新浪）")
    try:
        symbol = f"{get_market_prefix(stock_code)}{stock_code}"
        df = ak.stock_intraday_sina(symbol=symbol, date=INTRADAY_DATE)
        print(f"✅ 记录数: {len(df)}")
        safe_show_df(df, head=20)
    except Exception as e:
        print(f"⚠️ 非交易日或盘中外，可能为空: {e}")

    # 8) 涨停板池（东财）
    print("\n[8] ak.stock_zt_pool_em — 涨停板池（东财）")
    try:
        df = ak.stock_zt_pool_em(date=TODAY)
        print(f"✅ 数量: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"⚠️ {e}")

    # 9) 跌停板池（东财）
    print("\n[9] ak.stock_zt_pool_dtgc_em — 跌停板池（东财）")
    try:
        df = ak.stock_zt_pool_dtgc_em(date=TODAY)
        print(f"✅ 数量: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"⚠️ {e}")

    # 10) 个股资金流向（东财）
    print("\n[10] ak.stock_individual_fund_flow — 个股资金流向（东财）")
    try:
        market = get_market_code(stock_code)
        df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        print(f"✅ 记录数: {len(df)}")
        safe_show_df(df)
    except Exception as e:
        print(f"⚠️ {e}")

    print("\n" + "=" * 80)
    print("✅ 接口测试结束")
    print("=" * 80)


if __name__ == "__main__":
    test_all_used_apis()


