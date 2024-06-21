import akshare as ak
import pandas as pd
import numpy as np
import random

# 获取股票数据函数
def get_stock_data(stock_code, start_date):
    stock_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, adjust="qfq")
    stock_df = stock_df[['日期', '开盘', '收盘', '最高']]
    stock_df.columns = ['date', 'open', 'close', 'high']
    stock_df['date'] = pd.to_datetime(stock_df['date'])
    stock_df.set_index('date', inplace=True)
    return stock_df

# 模拟交易策略函数
def simulate_strategy(stock_df, initial_balance=100000):
    balance = initial_balance
    shares = 0
    transactions = []
    buy_price = 0

    stock_df['ma20'] = stock_df['close'].rolling(window=20).mean()
    stock_df['ma50'] = stock_df['close'].rolling(window=50).mean()

    for i in range(1, len(stock_df)):
        today = stock_df.iloc[i]
        yesterday = stock_df.iloc[i - 1]

        if yesterday['ma20'] <= yesterday['ma50'] and today['ma20'] > today['ma50'] and shares == 0:
            # 买入信号（次日开盘价买入）
            buy_price = today['open']
            shares_to_buy = balance // buy_price
            cost = shares_to_buy * buy_price
            balance -= cost
            shares += shares_to_buy
            transactions.append((today.name, 'buy', shares_to_buy, buy_price, balance))
        elif shares > 0 and today['high'] >= (1.1 * buy_price):
            # 卖出信号（当日最高价达到10%涨幅时卖出）
            sell_price = 1.1 * buy_price  # 设定卖出价格为涨幅10%的价格
            income = shares * sell_price
            balance += income
            transactions.append((today.name, 'sell', shares, sell_price, balance))
            shares = 0
            buy_price = 0

    return transactions, balance

# 主函数
def main():
    # 获取所有A股股票列表
    try:
        stock_list = ak.stock_zh_a_spot()
        stock_list = stock_list[stock_list['代码'].str.startswith('sh') | stock_list['代码'].str.startswith('sz')]
        stock_codes = stock_list['代码'].tolist()
        
        if not stock_codes:
            raise ValueError("股票列表为空，无法进行随机选择。")
    except Exception as e:
        print(f"Error fetching stock list: {e}")
        return

    # 尝试随机选择一只有效股票
    random_stock = None
    max_attempts = 10
    attempts = 0

    while not random_stock and attempts < max_attempts:
        attempts += 1
        try:
            potential_stock = random.choice(stock_codes)
            stock_code = potential_stock  # 使用原始股票代码，不进行前缀处理
            # 获取股票数据
            start_date = '2024-01-01'
            print(f"尝试获取股票数据: {stock_code}")
            stock_df = get_stock_data(stock_code, start_date)
            random_stock = potential_stock
        except KeyError:
            print(f"KeyError: 无法获取股票数据 {potential_stock}")
            continue
        except Exception as e:
            print(f"Error fetching data for {locals().get('potential_stock', 'unknown')}: {e}")
            continue

    if not random_stock:
        print("多次尝试后仍无法获取有效的股票数据，程序终止。")
        return

    # 模拟交易
    transactions, final_balance = simulate_strategy(stock_df)

    # 打印交易信息
    for transaction in transactions:
        print(f"Date: {transaction[0]}, Type: {transaction[1]}, Shares: {transaction[2]}, Price: {transaction[3]:.2f}, Balance: {transaction[4]:.2f}")

    # 打印最终结果
    initial_balance = 100000
    print(f"Initial Balance: {initial_balance:.2f}")
    print(f"Final Balance: {final_balance:.2f}")
    print(f"Total Profit/Loss: {final_balance - initial_balance:.2f}")

if __name__ == "__main__":
    main()