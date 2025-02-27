import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from queue import Queue

def get_previous_trading_day(date, stock_code):
    """获取指定日期前一个交易日的日期和收盘价"""
    earliest_date = datetime(2000, 1, 1)
    current_date = date - timedelta(days=1)
    attempts = 60

    print(f"开始查找 {date.strftime('%Y-%m-%d')} 前的一个交易日...")
    while attempts > 0 and current_date >= earliest_date:
        start = (current_date - timedelta(days=30)).strftime("%Y%m%d")
        end = current_date.strftime("%Y%m%d")
        print(f"尝试日期范围: {start} 至 {end}")
        try:
            stock_data = ak.stock_zh_a_daily(symbol=stock_code, start_date=start, end_date=end)
            print(f"获取到的数据:\n{stock_data}")
            if not stock_data.empty and len(stock_data) > 0:
                last_date = pd.to_datetime(stock_data['date'].iloc[-1])
                if last_date < date:
                    print(f"找到有效交易日: {last_date.strftime('%Y-%m-%d')}")
                    return last_date, stock_data['close'].iloc[-1]
        except Exception as e:
            print(f"获取数据失败 ({start} 至 {end}): {str(e)}")
        current_date -= timedelta(days=1)
        attempts -= 1

    raise ValueError(f"无法在 {date.strftime('%Y-%m-%d')} 前找到有效的交易日数据")

def get_recent_trading_days(stock_code, num_days=5):
    """获取最近 num_days 个交易日的日期"""
    today = datetime.now()
    start = (today - timedelta(days=30)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    print(f"获取最近 {num_days} 个交易日的数据范围: {start} 至 {end}")
    try:
        stock_data = ak.stock_zh_a_daily(symbol=stock_code, start_date=start, end_date=end)
        if stock_data.empty:
            raise ValueError("无法获取最近交易日数据")
        trading_days = pd.to_datetime(stock_data['date']).sort_values()
        recent_days = trading_days[-num_days:].tolist()
        print(f"最近 {num_days} 个交易日: {[d.strftime('%Y-%m-%d') for d in recent_days]}")
        return recent_days
    except Exception as e:
        raise ValueError(f"获取最近交易日失败: {str(e)}")

def backtest_stock_strategy(stock_code, a_percent, b_percent, commission_rate, stamp_duty_rate, buy_amount=100, sell_amount=100):
    """基于最近 5 个交易日分钟线数据的回测，支持配置买入和卖出数量"""
    # 将百分比转换为小数
    a = a_percent / 100.0  # 下跌幅度
    b = b_percent / 100.0  # 上涨幅度

    # 获取最近 5 个交易日
    recent_trading_days = get_recent_trading_days(stock_code, num_days=5)
    start_date = recent_trading_days[0]
    end_date = recent_trading_days[-1]

    # 获取初始基准股价：起始日期前一个交易日的收盘价
    try:
        prev_day, base_price = get_previous_trading_day(start_date, stock_code)
    except Exception as e:
        raise ValueError(f"获取基准股价失败: {str(e)}")

    # 获取分钟线数据（最近 5 个交易日）
    print("正在获取分钟线数据...")
    try:
        stock_data = ak.stock_zh_a_minute(symbol=stock_code, period='1', adjust="qfq")
        print(f"原始分钟线数据样本:\n{stock_data.head()}")
    except Exception as e:
        raise ValueError(f"获取分钟线数据失败: {str(e)}")

    stock_data['day'] = pd.to_datetime(stock_data['day'])
    stock_data = stock_data[(stock_data['day'] >= start_date) & (stock_data['day'] <= end_date)]
    if stock_data.empty:
        raise ValueError("分钟线数据为空，请检查股票代码或数据源")

    # 初始化变量
    position = 10000  # 初始持有大量股票（10,000 股）
    cash = 1000000  # 初始持有大量现金（1,000,000 元）
    buy_count = 0  # 买入次数
    sell_count = 0  # 卖出次数
    total_profit = 0  # 总盈亏
    total_commission = 0  # 总佣金
    total_stamp_duty = 0  # 总印花税
    trade_records = []  # 交易记录
    buy_queue = Queue()  # 买入队列

    # 假设初始持仓的买入价格为基准股价，按照 buy_amount 分批记录
    initial_lots = position // buy_amount
    for _ in range(initial_lots):
        buy_queue.put({'price': base_price, 'amount': buy_amount})
    if position % buy_amount > 0:
        buy_queue.put({'price': base_price, 'amount': position % buy_amount})

    # 输出初始信息
    print(f"初始基准股价 ({prev_day.strftime('%Y-%m-%d')}): {base_price:.2f}")
    print(f"初始持仓: {position} 股 | 初始现金: {cash:.2f} 元")
    print(f"回测分钟线数据范围: {stock_data['day'].min()} 至 {stock_data['day'].max()}")
    print(f"分钟线数据行数: {len(stock_data)}")
    print(f"配置参数: 买入数量={buy_amount} 股, 卖出数量={sell_amount} 股")

    # 遍历每分钟数据
    current_price = base_price
    for index, row in stock_data.iterrows():
        time = row['day']
        high = row['high']
        low = row['low']

        # 在每分钟内检查交易
        price = current_price
        iteration = 0
        while iteration < 100:  # 限制最大迭代次数
            # 先检查卖出条件
            if position >= sell_amount and high >= price * (1 + b):
                sell_price = price * (1 + b)
                if sell_price > high:
                    break
                transaction_amount = sell_price * sell_amount
                commission = transaction_amount * commission_rate
                stamp_duty = transaction_amount * stamp_duty_rate
                total_commission += commission
                total_stamp_duty += stamp_duty
                cash += transaction_amount - commission - stamp_duty
                position -= sell_amount

                if not buy_queue.empty():
                    buy_record = buy_queue.get()
                    buy_price = buy_record['price']
                    buy_amount_recorded = buy_record['amount']
                    profit = (sell_price - buy_price) * min(sell_amount, buy_amount_recorded)
                    total_profit += profit
                    if buy_amount_recorded > sell_amount:
                        buy_queue.put({'price': buy_price, 'amount': buy_amount_recorded - sell_amount})
                else:
                    profit = 0

                trade_records.append({
                    'time': time,
                    'type': '卖出',
                    'price': sell_price,
                    'amount': sell_amount,
                    'transaction_amount': transaction_amount,
                    'commission': commission,
                    'stamp_duty': stamp_duty,
                    'profit': profit
                })
                sell_count += 1
                price = sell_price
                iteration += 1
                continue

            # 再检查买入条件
            if low <= price * (1 - a):
                buy_price = price * (1 - a)
                if buy_price < low:
                    break
                transaction_amount = buy_price * buy_amount
                commission = transaction_amount * commission_rate
                total_commission += commission
                cash -= transaction_amount + commission
                position += buy_amount
                buy_queue.put({'price': buy_price, 'amount': buy_amount})

                trade_records.append({
                    'time': time,
                    'type': '买入',
                    'price': buy_price,
                    'amount': buy_amount,
                    'transaction_amount': transaction_amount,
                    'commission': commission,
                    'stamp_duty': 0,
                    'profit': 0
                })
                buy_count += 1
                price = buy_price
                iteration += 1
                continue

            break  # 无法触发更多交易

        current_price = price  # 更新当前价格

    # 输出交易记录
    print("\n交易记录：")
    print("-" * 80)
    for record in trade_records:
        print(f"时间: {record['time']} | 类型: {record['type']} | 价格: {record['price']:.2f} | "
              f"数量: {record['amount']} | 交易金额: {record['transaction_amount']:.2f} | "
              f"佣金: {record['commission']:.2f} | 印花税: {record['stamp_duty']:.2f} | 盈亏: {record['profit']:.2f}")
    print("-" * 80)

    # 输出统计信息
    print("\n统计信息：")
    print(f"买入次数: {buy_count}")
    print(f"卖出次数: {sell_count}")
    print(f"总交易费用: {total_commission + total_stamp_duty:.2f} 元")
    print(f"总盈亏: {total_profit:.2f} 元")
    print(f"最终现金: {cash:.2f} 元")
    print(f"最终持仓: {position} 股")

# 示例调用（使用最近 5 个交易日数据）
if __name__ == "__main__":
    try:
        backtest_stock_strategy("sh688981", 1.2, 1.8, 0.0003, 0.001, 300, 300)  # 买入 300 股，卖出 300 股
    except ValueError as e:
        print(f"错误: {e}")
