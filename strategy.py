import akshare as ak
import pandas as pd
import numpy as np
import random
import time
import json
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

# 获取股票数据函数，增加重试机制
def get_stock_data_with_retry(ticker, start, end, retries=5, delay=5):
    for attempt in range(retries):
        try:
            start = start.replace("-", "")
            end = end.replace("-", "")
            stock = ak.stock_zh_a_hist(symbol=ticker, period="daily", start_date=start, end_date=end, adjust="qfq")
            stock = stock[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']]
            stock.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
            stock.set_index('date', inplace=True)
            stock.index = pd.to_datetime(stock.index)
            return stock
        except Exception as e:
            print(f"下载股票数据失败 {ticker}，重试 {attempt + 1}/{retries}...")
            time.sleep(delay)
    raise Exception(f"多次重试后仍然无法下载股票数据 {ticker}")

# 下载股票数据，增加异常处理
def download_stock_data(tickers, start_date, end_date):
    stock_data = {}
    total_tickers = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        try:
            stock_data[ticker] = get_stock_data_with_retry(ticker, start_date, end_date)
            print(f"Downloaded {i}/{total_tickers} stocks")
        except Exception as e:
            print(f"下载股票数据失败，提前结束模拟。异常：{e}")
            return stock_data, False  # 提前结束
    return stock_data, True

# 模拟交易策略函数
def simulate_strategy(stock_df, ma_short, ma_long, up_ratio, down_ratio, initial_balance=100000):
    balance = initial_balance
    shares = 0
    transactions = []
    buy_price = 0
    consecutive_losses = 0
    last_loss_date = None

    stock_df[f'ma{ma_short}'] = stock_df['close'].rolling(window=ma_short).mean()
    stock_df[f'ma{ma_long}'] = stock_df['close'].rolling(window=ma_long).mean()

    for i in range(1, len(stock_df)):
        today = stock_df.iloc[i]
        yesterday = stock_df.iloc[i - 1]
        day_before_yesterday = stock_df.iloc[i - 2] if i >= 2 else None

        # 判断长均线是否连续3日上涨
        if i >= 3:
            last_three_days = stock_df.iloc[i-3:i]
            ma_long_trend = last_three_days[f'ma{ma_long}'].diff().dropna() > 0
            is_ma_long_upward = ma_long_trend.all()
        else:
            is_ma_long_upward = False

        if last_loss_date is not None and today.name <= last_loss_date + timedelta(days=60):
            continue  # 如果在两个月内，不进行交易

        if day_before_yesterday is not None and day_before_yesterday[f'ma{ma_short}'] < day_before_yesterday[f'ma{ma_long}'] and yesterday[f'ma{ma_short}'] >= yesterday[f'ma{ma_long}'] and shares == 0:
            # 买入信号（以今天开盘价买入）
            buy_price = today['open']
            shares_to_buy = (balance // buy_price) // 100 * 100  # 使买入的数量是100的整数倍
            cost = shares_to_buy * buy_price
            balance -= cost
            shares += shares_to_buy
            print(f"{today.name.date()}, B, {shares_to_buy}, {buy_price:.2f}, {balance:.2f}")
        elif shares > 0 and (today['high'] >= (1 + up_ratio) * buy_price or today['low'] <= (1 - down_ratio) * buy_price):
            # 卖出信号（当日最高价达到上涨比例时卖出）
            if today['high'] >= (1 + up_ratio) * buy_price:
                sell_price = (1 + up_ratio) * buy_price  # 设定卖出价格为涨幅比例
            else:
                sell_price = (1 - down_ratio) * buy_price
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

# 执行策略函数
def execute_strategy(strategy, all_stock_data):
    ma_short = strategy['ma_short']
    ma_long = strategy['ma_long']
    up_ratio = strategy['up_ratio']
    down_ratio = strategy['down_ratio']
    
    if ma_short < 1 or ma_long < 1 or up_ratio <= 0 or down_ratio <= 0:
        raise ValueError("All input values must be positive and up/down ratios must be greater than 0.")

    # 如果ma_short大于ma_long，交换它们的值
    if ma_short > ma_long:
        ma_short, ma_long = ma_long, ma_short

    total_cash = 0
    total_stock_value = 0
    num_profitable = 0
    num_loss = 0
    total_profit = 0
    total_loss = 0

    for ticker, stock_data in all_stock_data.items():
        transactions, final_balance, shares = simulate_strategy(stock_data, ma_short, ma_long, up_ratio, down_ratio)

        # 计算截止到当前日期的股票市值
        current_stock_price = stock_data['close'].iloc[-1]
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

    # 打印累计结果
    total_value = total_cash + total_stock_value
    avg_profit = total_profit / num_profitable if num_profitable > 0 else 0
    avg_loss = total_loss / num_loss if num_loss > 0 else 0
    win_rate = (num_profitable / len(all_stock_data)) * 100 if len(all_stock_data) > 0 else 0

    result = {
        "strategy_name": strategy['name'],
        "total_cash": total_cash,
        "total_stock_value": total_stock_value,
        "total_value": total_value,
        "num_stocks": len(all_stock_data),
        "num_profitable": num_profitable,
        "num_loss": num_loss,
        "win_rate": win_rate,
        "avg_profit": avg_profit,
        "avg_loss": avg_loss
    }

    print(f"Total Cash: {total_cash:.2f}")
    print(f"Total Stock Value: {total_stock_value:.2f}")
    print(f"Total Portfolio Value: {total_value:.2f}")
    print(f"Number of Stocks Simulated: {len(all_stock_data)}")
    print(f"Number of Profitable Stocks: {num_profitable}")
    print(f"Number of Losing Stocks: {num_loss}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Average Profit: {avg_profit:.2f}")
    print(f"Average Loss: {avg_loss:.2f}")

    return result

# 主函数
def main():
    # 读取配置文件
    with open("2050stratery_conf.json", "r") as file:
        config = json.load(file)

    init_date = config['init_date']
    num_stocks = config['stockNum']
    strategies = {k: v for k, v in config.items() if k.startswith("strategy")}
    results = []

    current_date = datetime.now().strftime('%Y-%m-%d')

    # 获取所有A股股票代码
    stock_info = get_stock_info_with_retry()
    stock_list = stock_info['code'].tolist()
    stock_names = stock_info['name'].tolist()

    # 随机选择指定数量的股票
    selected_indices = random.sample(range(len(stock_list)), num_stocks)
    tickers = [stock_list[i] for i in selected_indices]
    stock_names = [stock_names[i] for i in selected_indices]

    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch_tickers = tickers[i:i + batch_size]
        batch_names = stock_names[i:i + batch_size]

        # 下载当前批次的股票数据
        all_stock_data, success = download_stock_data(batch_tickers, init_date, current_date)
        if not success:
            break  # 如果下载失败，提前结束模拟

        for strategy_name, strat in strategies.items():
            print(f"Executing {strategy_name} for batch {i // batch_size + 1}...")
            result = execute_strategy(strat, all_stock_data)
            results.append(result)

    # 打印所有策略的结果
    print("\nAll Strategies Results:")
    for result in results:
        print(f"{result['strategy_name']}: Win Rate {result['win_rate']:.2f}%")

if __name__ == "__main__":
    main()
