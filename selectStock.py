import akshare as ak
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# 获取股票信息的函数，增加重试机制
def get_stock_info_with_retry(retries=5, delay=5):
    for attempt in range(retries):
        try:
            stock_info = ak.stock_info_a_code_name()
            return stock_info
        except Exception as e:
            print(f"获取股票信息失败，重试 {attempt + 1}/{retries}...")
            time.sleep(delay)
    raise Exception("多次重试后仍然无法获取股票信息")

# 获取最近30天的股票数据函数
def get_recent_stock_data(ticker, end):
    start = (datetime.strptime(end, '%Y-%m-%d') - timedelta(days=60)).strftime('%Y%m%d')
    end = end.replace("-", "")
    stock = ak.stock_zh_a_hist(symbol=ticker, period="daily", start_date=start, end_date=end, adjust="qfq")
    stock = stock[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']]
    stock.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
    stock.set_index('date', inplace=True)
    stock.index = pd.to_datetime(stock.index)
    return stock

# 下载股票数据并检查条件
def check_stocks_for_condition(stock_list, end_date):
    selected_stocks = []

    for ticker in stock_list:
        stock_df = get_recent_stock_data(ticker, end_date)
        stock_df['ma5'] = stock_df['close'].rolling(window=5).mean()
        stock_df['ma30'] = stock_df['close'].rolling(window=30).mean()

        if len(stock_df) < 30:
            continue  # 确保有足够的数据计算均线

        yesterday = stock_df.iloc[-2]
        today = stock_df.iloc[-1]

        if yesterday['ma5'] <= yesterday['ma30'] and today['ma5'] > today['ma30']:
            selected_stocks.append(ticker)

    return selected_stocks

# 主函数
def main():
    current_date = datetime.now().strftime('%Y-%m-%d')

    # 获取所有A股股票代码
    stock_info = get_stock_info_with_retry()
    stock_list = stock_info['code'].tolist()
    stock_names = stock_info['name'].tolist()

    # 检查符合条件的股票
    selected_stocks = check_stocks_for_condition(stock_list, current_date)

    # 打印符合条件的股票代码和名称
    for stock in selected_stocks:
        stock_name = stock_info[stock_info['code'] == stock]['name'].values[0]
        print(f"Stock: {stock}, Name: {stock_name}")

if __name__ == "__main__":
    main()