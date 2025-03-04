import akshare as ak
import time

# 设置要监控的股票代码（示例：600000 浦发银行）
stock_code = "600000"

def get_realtime_price(stock_code):
    """获取指定股票的实时价格"""
    try:
        # 使用新版本接口
        df = ak.stock_zh_a_spot_em()
        # 筛选指定股票数据
        stock_data = df[df['代码'] == stock_code]
        if not stock_data.empty:
            return stock_data.iloc[0]['最新价']
        return None
    except Exception as e:
        print(f"获取数据失败: {str(e)[:50]}")  # 截断错误信息
        return None

if __name__ == "__main__":
    print(f"开始监控 {stock_code} 的实时价格（按 Ctrl+C 终止）")
    try:
        while True:
            price = get_realtime_price(stock_code)
            if price is not None:
                print(f"\r当前价格: {price}", end="", flush=True)
            else:
                print("\r正在尝试重新获取数据...", end="")
            time.sleep(5)  # 添加5秒间隔
    except KeyboardInterrupt:
        print("\n监控已停止")
