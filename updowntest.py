import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_previous_trading_day(date, stock_code):
    """获取指定日期前一个交易日的日期和收盘价"""
    earliest_date = datetime(2000, 1, 1)
    current_date = date - timedelta(days=1)
    attempts = 60

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

    try:
        stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if stock_data.empty:
            raise ValueError("无法获取最近交易日数据")
        trading_days = pd.to_datetime(stock_data['日期']).sort_values()
        recent_days = trading_days[-num_days:].tolist()
        return recent_days
    except Exception as e:
        raise ValueError(f"获取最近交易日失败: {str(e)}")

def backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate):
    """基于最近 5 个交易日分钟线数据的回测"""
    a = buy_percent / 100.0
    b = sell_percent / 100.0

    recent_trading_days = get_recent_trading_days(stock_code, num_days=5)
    start_date = recent_trading_days[0]
    end_date = recent_trading_days[-1]

    if end_date.date() == datetime.now().date():
        end_date = datetime.combine(end_date.date(), datetime.max.time())

    prev_day, base_price = get_previous_trading_day(start_date, stock_code)

    # 根据股票代码前缀调整分钟线代码
    if stock_code.startswith('688'):
        minute_code = f"sh{stock_code}"
    elif stock_code.startswith(('83', '43', '87')):
        minute_code = f"bj{stock_code}"  # 北交所股票在分钟线数据中需要 'bj' 前缀
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
    stock_data = stock_data.reset_index(drop=True)

    if stock_data.empty:
        raise ValueError("分钟线数据为空，请检查股票代码或数据源")

    # 计算初始持仓数量：100万元市值的股票数量
    initial_market_value_target = 1000000  # 100万元
    position = int(initial_market_value_target / base_price)
    cash = 1000000  # 现金不变

    # 计算每次交易的数量：1万元市值的股票数量
    transaction_value_target = 10000  # 1万元
    transaction_amount = int(transaction_value_target / base_price)
    buy_amount = transaction_amount
    sell_amount = transaction_amount

    initial_market_value = base_price * position
    initial_total_assets = initial_market_value + cash

    print(f"\n--- {stock_name} ({stock_code}) 回测开始 ---")
    print(f"初始持仓数量: {position}, 初始股票价格: {base_price:.2f}, 初始持仓市值: {initial_market_value:.2f}, 初始现金: {cash:.2f}, 初始总资产: {initial_total_assets:.2f}")

    current_price = base_price
    last_transaction_row_num = -1

    buy_count = 0
    sell_count = 0
    total_commission = 0
    total_stamp_duty = 0

    for row_num, row in stock_data.iterrows():
        time = row['day']
        high = row['high']
        low = row['low']
        #print(f"row_num:{row_num},row:{row}")
        price = current_price
        iteration = 0
        while iteration < 2:
            # 卖出逻辑
            if position >= sell_amount and high >= price * (1 + b):
                sell_price = price * (1 + b)
                if sell_price > high:
                    break
                transaction_amount_value = sell_price * sell_amount
                commission = transaction_amount_value * commission_rate
                stamp_duty = transaction_amount_value * stamp_duty_rate
                total_commission += commission
                total_stamp_duty += stamp_duty
                cash += transaction_amount_value - commission - stamp_duty
                position -= sell_amount

                print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 卖出 | 价格: {sell_price:.2f} | 数量: {sell_amount} | 成交额: {transaction_amount_value:.2f} | 印花税: {stamp_duty:.2f} | 佣金: {commission:.2f} | 持仓数量: {position}, 现金数量: {cash:.2f}, 总资产: {sell_price * position + cash:.2f}")

                sell_count += 1
                price = sell_price
                iteration += 1
                last_transaction_row_num = row_num
                continue

            # 买入逻辑
            if low <= price * (1 - a):
                buy_price = price * (1 - a)
                if buy_price < low:
                    break
                transaction_amount_value = buy_price * buy_amount
                commission = transaction_amount_value * commission_rate
                total_commission += commission
                cash -= transaction_amount_value + commission
                position += buy_amount

                print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 买入 | 价格: {buy_price:.2f} | 数量: {buy_amount} | 成交额: {transaction_amount_value:.2f} | 印花税: 0.00 | 佣金: {commission:.2f} | 持仓数量: {position}, 现金数量: {cash:.2f}, 总资产: {buy_price * position + cash:.2f}")

                buy_count += 1
                price = buy_price
                iteration += 1
                last_transaction_row_num = row_num
                continue

            break

        current_price = price

    if last_transaction_row_num != -1:
        final_close_price = stock_data.iloc[last_transaction_row_num]['close']
    else:
        final_close_price = stock_data.iloc[-1]['close']

    final_market_value = final_close_price * position
    final_total_assets = final_market_value + cash
    asset_change = final_total_assets - initial_total_assets - total_commission - total_stamp_duty

    print(f"\n--- {stock_name} ({stock_code}) 回测结束 ---")
    print(f"最终持仓数量: {position}, 最终股票价格: {final_close_price:.2f}, 最终持仓市值: {final_market_value:.2f}, 最终现金: {cash:.2f}, 最终总资产: {final_total_assets:.2f}")
    print(f"买入次数: {buy_count}, 卖出次数: {sell_count}, 总佣金: {total_commission:.2f}, 总印花税: {total_stamp_duty:.2f}, 总资产差值（考虑费用）: {asset_change:.2f}")

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_commission": total_commission,
        "total_stamp_duty": total_stamp_duty,
        "final_cash": cash,
        "final_position": position,
        "final_total_assets": final_total_assets,
        "initial_position": position,
        "initial_price": base_price,
        "initial_market_value": initial_market_value,
        "initial_cash": 1000000,
        "initial_total_assets": initial_total_assets,
        "final_price": final_close_price,
        "final_market_value": final_market_value,
        "asset_change": asset_change,
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
    N = 1  # 随机选择20只股票进行测试

    # 新增配置：支持场内基金回测
    use_fixed_stocks = True  # 设置为True以使用固定股票和场内基金
    fixed_stocks = [
        ("600030", "中信证券"),     # 上海主板股票
        ("600584", "长电科技"),     # 深圳主板股票
        ("600000", "浦发银行"),     # 深圳主板股票
    ]

    # 根据开关选择股票列表
    if use_fixed_stocks:
        stock_info = fixed_stocks
    else:
        stock_info = random_stocks(N)

    all_results = []

    for stock_code, stock_name in stock_info:
        print(f"\n开始回测: {stock_code} - {stock_name}")
        try:
            result = backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate)
            all_results.append(result)
        except Exception as e:
            print(f"回测 {stock_code} 失败: {str(e)}")

    # 按总资产差值（考虑费用）从小到大排序
    all_results.sort(key=lambda x: x["asset_change"])

    # 打印所有股票的交易汇总信息
    print("\n--- 所有股票交易汇总 ---")
    for result in all_results:
        print(f"\n股票代码: {result['stock_code']}, 股票名称: {result['stock_name']}")
        print(f"初始持仓数量: {result['initial_position']}, 初始股票价格: {result['initial_price']:.2f}, 初始持仓市值: {result['initial_market_value']:.2f}, 初始现金: {result['initial_cash']:.2f}, 初始总资产: {result['initial_total_assets']:.2f}")
        print(f"最终持仓数量: {result['final_position']}, 最终股票价格: {result['final_price']:.2f}, 最终持仓市值: {result['final_market_value']:.2f}, 最终现金: {result['final_cash']:.2f}, 最终总资产: {result['final_total_assets']:.2f}")
        print(f"买入次数: {result['buy_count']}, 卖出次数: {result['sell_count']}, 总佣金: {result['total_commission']:.2f}, 总印花税: {result['total_stamp_duty']:.2f}, 总资产差值（考虑费用）: {result['asset_change']:.2f}")

    # 统计盈利和亏损股票
    profitable_stocks = [result for result in all_results if result['asset_change'] > 0]
    losing_stocks = [result for result in all_results if result['asset_change'] < 0]
    total_asset_change = sum(result['asset_change'] for result in all_results)

    # 打印要求的四行统计信息
    print("\n测试股票数量: {}".format(len(all_results)))
    print("盈利股票情况: {} 支股票盈利，股票名称: {}".format(len(profitable_stocks), ', '.join([result['stock_name'] for result in profitable_stocks])))
    print("亏损股票情况: {} 支股票亏损，股票名称: {}".format(len(losing_stocks), ', '.join([result['stock_name'] for result in losing_stocks])))
    print("总盈亏: {:.2f}".format(total_asset_change))

if __name__ == "__main__":
    main()
