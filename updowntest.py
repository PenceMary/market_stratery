import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from queue import Queue

def get_previous_trading_day(date, stock_code):
    """获取指定日期前一个交易日的日期和收盘价"""
    earliest_date = datetime(2000, 1, 1)
    current_date = date - timedelta(days=1)
    attempts = 60

    if stock_code.startswith(('83', '43', '87')):
        stock_code = f"bj{stock_code}"

    while attempts > 0 and current_date >= earliest_date:
        start = (current_date - timedelta(days=30)).strftime("%Y%m%d")
        end = current_date.strftime("%Y%m%d")
        try:
            stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
            if not stock_data.empty and len(stock_data) > 0:
                last_date = pd.to_datetime(stock_data['日期'].iloc[-1])
                if last_date < date:
                    return last_date, stock_data['收盘'].iloc[-1]
        except Exception:
            pass
        current_date -= timedelta(days=1)
        attempts -= 1

    raise ValueError(f"无法在 {date.strftime('%Y-%m-%d')} 前找到有效的交易日数据")

def get_recent_trading_days(stock_code, num_days=5):
    """获取最近 num_days 个交易日的日期"""
    today = datetime.now()
    start = (today - timedelta(days=30)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    if stock_code.startswith(('83', '43', '87')):
        stock_code = f"bj{stock_code}"

    try:
        stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if stock_data.empty:
            raise ValueError("无法获取最近交易日数据")
        trading_days = pd.to_datetime(stock_data['日期']).sort_values()
        recent_days = trading_days[-num_days:].tolist()
        return recent_days
    except Exception as e:
        raise ValueError(f"获取最近交易日失败: {str(e)}")

def backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate, buy_amount=100, sell_amount=100):
    """基于最近 5 个交易日分钟线数据的回测"""
    a = buy_percent / 100.0
    b = sell_percent / 100.0

    recent_trading_days = get_recent_trading_days(stock_code, num_days=5)
    start_date = recent_trading_days[0]
    end_date = recent_trading_days[-1]

    if end_date.date() == datetime.now().date():
        end_date = datetime.combine(end_date.date(), datetime.max.time())

    prev_day, base_price = get_previous_trading_day(start_date, stock_code)

    if stock_code.startswith('688'):
        minute_code = f"sh{stock_code}"
    elif stock_code.startswith(('83', '43', '87')):
        minute_code = f"bj{stock_code}"
    elif stock_code.startswith('60'):
        minute_code = f"sh{stock_code}"
    elif stock_code.startswith(('00', '30')):
        minute_code = f"sz{stock_code}"
    else:
        minute_code = stock_code

    try:
        stock_data = ak.stock_zh_a_minute(symbol=minute_code, period='1', adjust="qfq")
        if stock_data is None or stock_data.empty:
            raise ValueError(f"分钟线数据为空，请检查股票代码 {stock_code}")
    except Exception as e:
        raise ValueError(f"获取分钟线数据失败: {str(e)}")

    stock_data['day'] = pd.to_datetime(stock_data['day'])
    stock_data = stock_data[(stock_data['day'] >= start_date) & (stock_data['day'] <= end_date)]

    if stock_data.empty:
        raise ValueError("分钟线数据为空，请检查股票代码或数据源")

    position = 10000
    cash = 1000000
    buy_count = 0
    sell_count = 0
    total_profit = 0
    total_commission = 0
    total_stamp_duty = 0
    total_buy_amount = 0
    total_sell_amount = 0
    buy_queue = Queue()

    initial_lots = position // buy_amount
    for _ in range(initial_lots):
        buy_queue.put({'price': base_price, 'amount': buy_amount})
    if position % buy_amount > 0:
        buy_queue.put({'price': base_price, 'amount': position % buy_amount})

    current_price = base_price
    for index, row in stock_data.iterrows():
        time = row['day']
        high = row['high']
        low = row['low']

        price = current_price
        iteration = 0
        while iteration < 100:
            # 卖出逻辑
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
                total_sell_amount += transaction_amount

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

                # 打印卖出信息（包含时间）
                print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 卖出 | 价格: {sell_price:.2f} | 数量: {sell_amount} | 成交额: {transaction_amount:.2f} | 印花税: {stamp_duty:.2f} | 佣金: {commission:.2f} | 盈亏: {profit:.2f}")

                sell_count += 1
                price = sell_price
                iteration += 1
                continue

            # 买入逻辑
            if low <= price * (1 - a):
                buy_price = price * (1 - a)
                if buy_price < low:
                    break
                transaction_amount = buy_price * buy_amount
                commission = transaction_amount * commission_rate
                total_commission += commission
                cash -= transaction_amount + commission
                position += buy_amount
                total_buy_amount += transaction_amount
                buy_queue.put({'price': buy_price, 'amount': buy_amount})

                # 打印买入信息（包含时间）
                print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 买入 | 价格: {buy_price:.2f} | 数量: {buy_amount} | 成交额: {transaction_amount:.2f} | 印花税: 0.00 | 佣金: {commission:.2f} | 盈亏: 0.00")

                buy_count += 1
                price = buy_price
                iteration += 1
                continue

            break

        current_price = price

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_buy_amount": total_buy_amount,
        "total_sell_amount": total_sell_amount,
        "total_profit": total_profit,
        "total_commission": total_commission,
        "total_stamp_duty": total_stamp_duty,
        "final_cash": cash,
        "final_position": position,
    }

def random_stocks(N=5):
    """随机获取N只股票的代码和名称"""
    try:
        stock_list = ak.stock_zh_a_spot_em()
        selected = stock_list.sample(N)
        return list(zip(selected['代码'].tolist(), selected['名称'].tolist()))
    except Exception as e:
        raise ValueError(f"获取股票列表失败: {str(e)}")

def main():
    buy_percent = 1
    sell_percent = 1
    commission_rate = 0.0003
    stamp_duty_rate = 0.001
    buy_amount = 300
    sell_amount = 300
    N = 1  # 随机选择2只股票进行测试

    stock_info = random_stocks(N)
    all_results = []

    for stock_code, stock_name in stock_info:
        print(f"\n开始回测股票: {stock_code} - {stock_name}")
        try:
            result = backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate, buy_amount, sell_amount)
            #result = backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate, buy_amount, sell_amount)
            all_results.append(result)
        except Exception as e:
            print(f"回测 {stock_code} 失败: {str(e)}")

    # 打印所有股票的交易汇总信息
    print("\n--- 所有股票交易汇总 ---")
    for result in all_results:
        print(f"股票代码: {result['stock_code']}, 股票名称: {result['stock_name']}, 买入次数: {result['buy_count']}, 卖出次数: {result['sell_count']}, 总买入额: {result['total_buy_amount']:.2f}, 总卖出额: {result['total_sell_amount']:.2f}, 总印花税: {result['total_stamp_duty']:.2f}, 总佣金: {result['total_commission']:.2f}, 总盈亏: {result['total_profit']:.2f}")

if __name__ == "__main__":
    main()
