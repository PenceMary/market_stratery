import akshare as ak
import pandas as pd
import numpy as np
import random
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
    consecutive_losses = 0
    last_loss_date = None

    stock_df['ma10'] = stock_df['close'].rolling(window=10).mean()
    stock_df['ma30'] = stock_df['close'].rolling(window=30).mean()

    for i in range(1, len(stock_df)):
        today = stock_df.iloc[i]
        yesterday = stock_df.iloc[i - 1]
        day_before_yesterday = stock_df.iloc[i - 2] if i >= 2 else None

        # 判断30日均线是否连续3日上涨
        if i >= 3:
            last_three_days = stock_df.iloc[i-3:i]
            ma30_trend = last_three_days['ma30'].diff().dropna() > 0
            is_ma30_upward = ma30_trend.all()
        else:
            is_ma30_upward = False

        if last_loss_date is not None and today.name <= last_loss_date + timedelta(days=60):
            continue  # 如果在两个月内，不进行交易

        if day_before_yesterday is not None and day_before_yesterday['ma10'] < day_before_yesterday['ma30'] and yesterday['ma10'] >= yesterday['ma30'] and shares == 0:# and is_ma30_upward:
            # 买入信号（以今天开盘价买入）
            buy_price = today['open']
            shares_to_buy = (balance // buy_price) // 100 * 100  # 使买入的数量是100的整数倍
            cost = shares_to_buy * buy_price
            balance -= cost
            shares += shares_to_buy
            print(f"{today.name.date()}, B, {shares_to_buy}, {buy_price:.2f}, {balance:.2f}")
        elif shares > 0 and (today['high'] >= (1.09 * buy_price) or today['low'] <= 0.94 * buy_price):
            # 卖出信号（当日最高价达到10%涨幅时卖出）
            if today['high'] >= 1.09 * buy_price:
                sell_price = 1.09 * buy_price  # 设定卖出价格为涨幅10%的价格
            else:
                sell_price = 0.94 * buy_price
            income = shares * sell_price
            balance += income
            print(f"{today.name.date()}, S, {shares}, {sell_price:.2f}, {balance:.2f}")
            shares = 0

            # 计算是否亏损
            if sell_price < buy_price:
                consecutive_losses += 1
                if consecutive_losses >= 2:
                    last_loss_date = today.name
            else:
                consecutive_losses = 0

    return transactions, balance, shares

# 主函数
def main():
    init_date = '2024-01-01'
    current_date = datetime.now().strftime('%Y-%m-%d')
    num_stocks = 300

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

    for idx, ticker in enumerate(all_stock_data.keys()):
        stock_name = stock_names[idx]
        print(f"模拟交易策略 {stock_name} ({ticker}) 的数据")
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
        #for transaction in transactions:
            #print(f"D: {transaction[0].date()}, T: {transaction[1]}, S: {transaction[2]}, P: {transaction[3]:.2f}, B: {transaction[4]:.2f}")

        # 打印最终结果
        initial_balance = 100000
        print(f"{ticker} ({stock_name}) Initial Balance: {initial_balance:.2f}")
        print(f"{ticker} ({stock_name}) Final Balance: {final_balance:.2f}")
        print(f"{ticker} ({stock_name}) Stock Value: {stock_value:.2f}")
        print(f"{ticker} ({stock_name}) Total Profit/Loss: {profit_or_loss:.2f}")
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
