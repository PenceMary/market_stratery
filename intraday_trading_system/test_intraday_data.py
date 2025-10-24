"""
日内交易数据获取测试脚本
用于测试数据获取功能，不调用大模型API
"""

import sys
from intraday_data_fetcher import IntradayDataFetcher
from intraday_indicators import TechnicalIndicators
import json


def test_stock_data(stock_code: str):
    """测试获取股票数据"""
    
    print(f"\n{'='*60}")
    print(f"测试股票数据获取: {stock_code}")
    print(f"{'='*60}\n")
    
    fetcher = IntradayDataFetcher()
    calculator = TechnicalIndicators()
    
    # 1. 测试实时行情
    print("1️⃣ 测试实时行情获取...")
    quote = fetcher.get_realtime_quote(stock_code)
    if quote:
        print(f"✅ 成功获取实时行情")
        print(json.dumps(quote, ensure_ascii=False, indent=2))
    else:
        print("❌ 获取实时行情失败")
        return
    
    print("\n" + "-"*60 + "\n")
    
    # 2. 测试今日分时数据
    print("2️⃣ 测试今日分时数据获取...")
    intraday_df = fetcher.get_today_intraday_data(stock_code)
    if not intraday_df.empty:
        print(f"✅ 成功获取分时数据，共 {len(intraday_df)} 条记录")
        print(f"数据列: {list(intraday_df.columns)}")
        print(f"\n最新5条数据:")
        print(intraday_df.tail())
        
        # 计算分时指标
        print("\n📊 计算分时技术指标...")
        indicators = calculator.analyze_intraday_data(intraday_df)
        if indicators:
            print(json.dumps(indicators, ensure_ascii=False, indent=2, default=str))
    else:
        print("⚠️ 未获取到分时数据")
    
    print("\n" + "-"*60 + "\n")
    
    # 3. 测试K线数据
    print("3️⃣ 测试K线数据获取...")
    kline_df = fetcher.get_kline_data(stock_code, days=20)
    if not kline_df.empty:
        print(f"✅ 成功获取K线数据，共 {len(kline_df)} 条记录")
        print(f"数据列: {list(kline_df.columns)}")
        print(f"\n最新5条数据:")
        print(kline_df.tail())
        
        # 计算K线指标
        print("\n📊 计算K线技术指标...")
        indicators = calculator.analyze_kline_data(kline_df)
        if indicators:
            print(json.dumps(indicators, ensure_ascii=False, indent=2, default=str))
    else:
        print("⚠️ 未获取到K线数据")
    
    print("\n" + "-"*60 + "\n")
    
    # 4. 测试盘口数据
    print("4️⃣ 测试盘口数据获取...")
    order_book = fetcher.get_order_book(stock_code)
    if order_book:
        print(f"✅ 成功获取盘口数据")
        print("\n买盘（五档）:")
        for i, bid in enumerate(order_book['bid'][:5], 1):
            print(f"  买{i}: {bid['price']:.2f} × {int(bid['volume'])} 手")
        print("\n卖盘（五档）:")
        for i, ask in enumerate(order_book['ask'][:5], 1):
            print(f"  卖{i}: {ask['price']:.2f} × {int(ask['volume'])} 手")
    else:
        print("⚠️ 未获取到盘口数据")
    
    print("\n" + "-"*60 + "\n")
    
    # 5. 测试大盘指数
    print("5️⃣ 测试大盘指数获取...")
    indices = fetcher.get_market_indices(stock_code)
    if indices:
        print(f"✅ 成功获取大盘指数数据")
        for name, data in indices.items():
            if data:
                print(f"\n{data['name']}:")
                print(f"  当前: {data['current']:.2f}")
                print(f"  涨跌幅: {data['change']:.2f}%")
    else:
        print("⚠️ 未获取到大盘指数数据")
    
    print("\n" + "-"*60 + "\n")
    
    # 6. 测试板块信息
    print("6️⃣ 测试板块信息获取...")
    sector = fetcher.get_sector_info(stock_code)
    if sector:
        print(f"✅ 成功获取板块信息")
        print(json.dumps(sector, ensure_ascii=False, indent=2))
    else:
        print("⚠️ 未获取到板块信息")
    
    print("\n" + "-"*60 + "\n")
    
    # 7. 测试市场情绪
    print("7️⃣ 测试市场情绪获取...")
    sentiment = fetcher.get_market_sentiment()
    if sentiment:
        print(f"✅ 成功获取市场情绪数据")
        print(json.dumps(sentiment, ensure_ascii=False, indent=2))
    else:
        print("⚠️ 未获取到市场情绪数据")
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60 + "\n")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🧪 日内交易数据获取测试")
    print("="*60 + "\n")
    
    if len(sys.argv) < 2:
        print("❌ 请提供股票代码参数")
        print("\n💡 使用方法:")
        print("  python test_intraday_data.py <股票代码>")
        print("\n📖 示例:")
        print("  python test_intraday_data.py 600000")
        print("  python test_intraday_data.py 000001")
        print("  python test_intraday_data.py 300750")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    
    try:
        test_stock_data(stock_code)
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

