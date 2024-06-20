import akshare as ak
import pandas as pd
import numpy as np

# 获取股票数据函数
def get_stock_data(stock_code, start_date):
    stock_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, adjust="qfq")
    stock_df = stock_df[['日期', '开盘', '收盘']]
    stock_df.columns = ['date', 'open', 'close']
    stock_df['date'] = pd.to_datetime(stock_df['date'])
    stock_df.set_index('date', inplace=True)
    return stock_df

# 模拟交易策略函数
def simulate_strategy(stock_df, initial_balance=100000):
    balance = initial_balance
    shares = 0
    transactions = []

    stock_df['ma20'] = stock_df['close'].rolling(window=20).mean()
    stock_df['ma50'] = stock_df['close'].rolling(window=50).mean()

    for i in range(1, len(stock_df)):
        today = stock_df.iloc[i]
        yesterday = stock_df.iloc[i - 1]

        if yesterday['ma20'] <= yesterday['ma50'] and today['ma20'] > today['ma50']:
            # 买入信号（次日开盘价买入）
            buy_price = today['open']
            shares_to_buy = balance // buy_price
            cost = shares_to_buy * buy_price
            balance -= cost
            shares += shares_to_buy
            transactions.append((today.name, 'buy', shares_to_buy, buy_price, balance))

        if shares > 0:
            current_value = shares * today['close']
            if current_value >= (1.1 * (initial_balance - balance)):
                # 卖出信号
                sell_price = today['close']
                income = shares * sell_price
                balance += income
                transactions.append((today.name, 'sell', shares, sell_price, balance))
                shares = 0

    return transactions, balance

# 主函数
def main():
    # 随机选择一只股票
    stock_list = ak.stock_zh_a_spot()
    random_stock = stock_list.sample(1)['代码'].values[0]

    # 获取股票数据
    start_date = '2022-01-01'
    stock_df = get_stock_data(random_stock, start_date)

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