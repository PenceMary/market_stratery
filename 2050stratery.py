import akshare as ak
import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

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

# 获取股票数据函数
def get_stock_data(ticker, start, end):
    start = start.replace("-", "")
    end = end.replace("-", "")
    stock = ak.stock_zh_a_hist(symbol=ticker, period="daily", start_date=start, end_date=end, adjust="qfq")
    stock = stock[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']]
    stock.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
    stock.set_index('date', inplace=True)
    stock.index = pd.to_datetime(stock.index)
    return stock

# 下载所有需要的股票数据
def download_all_stock_data(tickers, start_date, end_date):
    all_stock_data = {}
    for ticker in tickers:
        all_stock_data[ticker] = get_stock_data(ticker, start_date, end_date)
    return all_stock_data

# 模拟交易策略函数
def simulate_strategy(stock_df, initial_balance=100000):
    balance = initial_balance
    shares = 0
    transactions = []
    buy_price = 0

    stock_df['ma10'] = stock_df['close'].rolling(window=10).mean()
    stock_df['ma40'] = stock_df['close'].rolling(window=40).mean()

    for i in range(1, len(stock_df)):
        today = stock_df.iloc[i]
        yesterday = stock_df.iloc[i - 1]

        if yesterday['ma10'] <= yesterday['ma40'] and today['ma10'] > today['ma40'] and shares == 0:
            # 买入信号（次日开盘价买入）
            buy_price = today['open']
            shares_to_buy = balance // buy_price
            cost = shares_to_buy * buy_price
            balance -= cost
            shares += shares_to_buy
            transactions.append((today.name, 'buy', shares_to_buy, buy_price, balance))
        elif shares > 0 and (today['high'] >= (1.5 * buy_price) or today['low'] <= 0.95 * buy_price):
            # 卖出信号（当日最高价达到10%涨幅时卖出）
            if today['high'] >= 1.1 * buy_price:
                sell_price = 1.1 * buy_price  # 设定卖出价格为涨幅10%的价格
            else:
                sell_price = 0.95 * buy_price
            income = shares * sell_price
            balance += income
            transactions.append((today.name, 'sell', shares, sell_price, balance))
            shares = 0
            buy_price = 0

    return transactions, balance, shares

# 主函数
def main():
    init_date = '2023-01-01'
    current_date = datetime.now().strftime('%Y-%m-%d')
    num_stocks = 50

    # 随机选择多支股票
    stock_info = get_stock_info_with_retry()
    stock_list = stock_info['code'].tolist()
    stock_names = stock_info['name'].tolist()
    selected_indices = random.sample(range(len(stock_list)), num_stocks)
    tickers = [stock_list[i] for i in selected_indices]
    stock_names = [stock_names[i] for i in selected_indices]

    # 预先下载所有股票数据
    all_stock_data = download_all_stock_data(tickers, init_date, current_date)

    total_cash = 0
    total_stock_value = 0
    num_profitable = 0
    num_loss = 0
    total_profit = 0
    total_loss = 0

    for ticker in all_stock_data.keys():
        print(f"模拟交易策略 {ticker} 的数据")
        transactions, final_balance, shares = simulate_strategy(all_stock_data[ticker])

        # 计算截止到当前日期的股票市值
        current_stock_price = all_stock_data[ticker]['close'].iloc[-1]
        stock_value = shares * current_stock_price

        # 累计总现金和股票市值
        total_cash += final_balance
        total_stock_value += stock_value

        # 计算利润或损失
        total_balance = final_balance + stock_value
        profit_or_loss = total_balance - 100000

        if profit_or_loss > 0:
            num_profitable += 1
            total_profit += profit_or_loss
        else:
            num_loss += 1
            total_loss += profit_or_loss

        # 打印交易信息
        for transaction in transactions:
            print(f"Date: {transaction[0]}, Type: {transaction[1]}, Shares: {transaction[2]}, Price: {transaction[3]:.2f}, Balance: {transaction[4]:.2f}")

        # 打印最终结果
        initial_balance = 100000
        print(f"{ticker} Initial Balance: {initial_balance:.2f}")
        print(f"{ticker} Final Balance: {final_balance:.2f}")
        print(f"{ticker} Stock Value: {stock_value:.2f}")
        print(f"{ticker} Total Profit/Loss: {profit_or_loss:.2f}")
        print("===")

    # 打印累计结果
    total_value = total_cash + total_stock_value
    avg_profit = total_profit / num_profitable if num_profitable > 0 else 0
    avg_loss = total_loss / num_loss if num_loss > 0 else 0

    print(f"Total Cash: {total_cash:.2f}")
    print(f"Total Stock Value: {total_stock_value:.2f}")
    print(f"Total Portfolio Value: {total_value:.2f}")
    print(f"Number of Stocks Simulated: {num_stocks}")
    print(f"Number of Profitable Stocks: {num_profitable}")
    print(f"Number of Losing Stocks: {num_loss}")
    print(f"Average Profit: {avg_profit:.2f}")
    print(f"Average Loss: {avg_loss:.2f}")

if __name__ == "__main__":
    main()
