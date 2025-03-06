import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json
import time as t

def get_previous_trading_day(date, stock_code):
    """获取指定日期前一个交易日的日期和收盘价"""
    earliest_date = datetime(2000, 1, 1)
    current_date = date - timedelta(days=1)
    attempts = 60

    while attempts > 0 and current_date >= earliest_date:
        start = (current_date - timedelta(days=30)).strftime("%Y%m%d")
        end = current_date.strftime("%Y%m%d")
        try:
            if stock_code.startswith(('15', '16', '51')):  # ETF 代码
                stock_data = ak.fund_etf_hist_em(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
            else:
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

def get_recent_trading_days(stock_code, num_days=15):
    """获取最近 num_days 个交易日的日期，确保不包含未来日期"""
    today = datetime.now()
    start = (today - timedelta(days=60)).strftime("%Y%m%d")  # 扩大范围以确保足够数据
    end = today.strftime("%Y%m%d")

    try:
        if stock_code.startswith(('15', '16', '51')):  # ETF 代码
            stock_data = ak.fund_etf_hist_em(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        else:
            stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if stock_data.empty:
            raise ValueError("无法获取最近交易日数据")
        trading_days = pd.to_datetime(stock_data['日期'])
        # 过滤掉未来的日期
        trading_days = trading_days[trading_days <= pd.to_datetime(today)]
        trading_days = trading_days.sort_values()
        recent_days = trading_days[-num_days:].tolist()
        print(f"最近交易日: {[d.strftime('%Y%m%d') for d in recent_days]}")  # 调试输出
        return recent_days
    except Exception as e:
        raise ValueError(f"获取最近交易日失败: {str(e)}")

def backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate):
    """基于最近 15 个交易日逐笔成交数据的回测"""
    a = buy_percent / 100.0
    b = sell_percent / 100.0

    # 获取最近15个交易日
    recent_trading_days = get_recent_trading_days(stock_code, num_days=10)

    # 根据股票代码前缀调整分钟线代码，支持场内基金
    if stock_code.startswith('688'):
        minute_code = f"sh{stock_code}"  # 上海科创板
    elif stock_code.startswith(('83', '43', '87')):
        minute_code = f"bj{stock_code}"  # 北京证券交易所
    elif stock_code.startswith('60'):
        minute_code = f"sh{stock_code}"  # 上海主板或上海ETF
    elif stock_code.startswith(('00', '30')):
        minute_code = f"sz{stock_code}"  # 深圳主板、创业板或深圳ETF
    else:
        minute_code = stock_code
    print(f"minute_code:{minute_code}")

    # 获取逐笔成交数据
    stock_data_list = []

    for trade_date in recent_trading_days:
        trade_date_str = trade_date.strftime("%Y%m%d")
        try:
            if stock_code.startswith(('15', '16', '51')):  # ETF 代码，暂不支持
                print(f"警告: {stock_code} 是场内基金，逐笔成交数据暂不支持，跳过此股票")
                return None
            else:
                tick_data = ak.stock_intraday_sina(symbol=minute_code, date=trade_date_str)
                if not tick_data.empty:
                    tick_data['ticktime'] = pd.to_datetime(trade_date_str + ' ' + tick_data['ticktime'])
                    stock_data_list.append(tick_data)
                else:
                    print(f"警告: {trade_date_str} 无逐笔成交数据")
                for i in range(6):  # 等待 6 秒，避免请求过于频繁
                    print(".", end="", flush=True)
                    t.sleep(1)  # 避免请求过于频繁
        except Exception as e:
            print(f"获取 {trade_date_str} 的逐笔成交数据失败: {str(e)}")
            for i in range(200):  # 等待 200 秒，避免请求过于频繁
                print(".", end="", flush=True)
                t.sleep(1)  # 避免请求过于频繁

    if not stock_data_list:
        raise ValueError(f"无法获取 {stock_code} 的逐笔成交数据")

    # 合并所有交易日的 tick 数据
    stock_data = pd.concat(stock_data_list)
    stock_data = stock_data.sort_values('ticktime').reset_index(drop=True)

    # 获取前一个交易日的收盘价
    prev_day, base_price = get_previous_trading_day(recent_trading_days[0], stock_code)

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
    print(f"初始持仓数量: {position}, 初始股票价格: {base_price:.3f}, 初始持仓市值: {initial_market_value:.3f}, 初始现金: {cash:.3f}, 初始总资产: {initial_total_assets:.3f}")

    current_price = base_price
    last_transaction_time = None

    buy_count = 0
    sell_count = 0
    total_commission = 0
    total_stamp_duty = 0

    # 遍历每一笔成交记录
    for index, row in stock_data.iterrows():
        time = row['ticktime']
        tick_price = row['price']

        # 卖出逻辑
        if position >= sell_amount and tick_price >= current_price * (1 + b):
            sell_price = tick_price
            transaction_amount_value = sell_price * sell_amount
            commission = transaction_amount_value * commission_rate
            stamp_duty = transaction_amount_value * stamp_duty_rate
            total_commission += commission
            total_stamp_duty += stamp_duty
            cash += transaction_amount_value - commission - stamp_duty
            position -= sell_amount

            print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 卖出 | 价格: {sell_price:.3f} | 数量: {sell_amount} | 成交额: {transaction_amount_value:.3f} | 印花税: {stamp_duty:.3f} | 佣金: {commission:.3f} | 持仓数量: {position}, 现金数量: {cash:.3f}, 总资产: {sell_price * position + cash:.3f}")

            sell_count += 1
            current_price = sell_price
            last_transaction_time = time
            continue

        # 买入逻辑
        if tick_price <= current_price * (1 - a):
            buy_price = tick_price
            transaction_amount_value = buy_price * buy_amount
            commission = transaction_amount_value * commission_rate
            total_commission += commission
            cash -= transaction_amount_value + commission
            position += buy_amount

            print(f"交易时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 类型: 买入 | 价格: {buy_price:.3f} | 数量: {buy_amount} | 成交额: {transaction_amount_value:.3f} | 印花税: 0.00 | 佣金: {commission:.3f} | 持仓数量: {position}, 现金数量: {cash:.3f}, 总资产: {buy_price * position + cash:.3f}")

            buy_count += 1
            current_price = buy_price
            last_transaction_time = time
            continue

    # 计算最终资产
    if last_transaction_time is not None:
        final_close_price = stock_data[stock_data['ticktime'] <= last_transaction_time].iloc[-1]['price']
    else:
        final_close_price = stock_data.iloc[-1]['price']

    final_market_value = final_close_price * position
    final_total_assets = final_market_value + cash
    asset_change = final_total_assets - initial_total_assets - total_commission - total_stamp_duty

    print(f"\n--- {stock_name} ({stock_code}) 回测结束 ---")
    print(f"最终持仓数量: {position}, 最终股票价格: {final_close_price:.3f}, 最终持仓市值: {final_market_value:.3f}, 最终现金: {cash:.3f}, 最终总资产: {final_total_assets:.3f}")
    print(f"买入次数: {buy_count}, 卖出次数: {sell_count}, 总佣金: {total_commission:.3f}, 总印花税: {total_stamp_duty:.3f}, 总资产差值（考虑费用）: {asset_change:.3f}")

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
    # 读取配置文件
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 从配置文件中获取参数
    buy_percent = config['buy_percent']
    sell_percent = config['sell_percent']
    commission_rate = config['commission_rate']
    stamp_duty_rate = config['stamp_duty_rate']
    N = config['N']
    use_fixed_stocks = config['use_fixed_stocks']
    fixed_stocks = config['fixed_stocks']
    gap = config['gap']

    if use_fixed_stocks:
        stock_info = fixed_stocks
    else:
        stock_info = random_stocks(N)

    all_results = []

    for stock_code, stock_name in stock_info:
        print(f"\n开始回测: {stock_code} - {stock_name}")
        try:
            result = backtest_stock_strategy(stock_code, stock_name, buy_percent, sell_percent, commission_rate, stamp_duty_rate)
            if result is not None:
                all_results.append(result)
        except Exception as e:
            print(f"回测 {stock_code} 失败: {str(e)}")

        for i in range(gap):  # 等待 60 秒，避免请求过于频繁
            print(".", end="", flush=True)
            t.sleep(1)  # 避免请求过于频繁

    # 按总资产差值排序
    all_results.sort(key=lambda x: x["asset_change"])

    # 打印汇总信息
    print("\n--- 所有股票交易汇总 ---")
    for result in all_results:
        print(f"\n股票代码: {result['stock_code']}, 股票名称: {result['stock_name']}")
        print(f"初始持仓数量: {result['initial_position']}, 初始股票价格: {result['initial_price']:.3f}, 初始持仓市值: {result['initial_market_value']:.3f}, 初始现金: {result['initial_cash']:.3f}, 初始总资产: {result['initial_total_assets']:.3f}")
        print(f"最终持仓数量: {result['final_position']}, 最终股票价格: {result['final_price']:.3f}, 最终持仓市值: {result['final_market_value']:.3f}, 最终现金: {result['final_cash']:.3f}, 最终总资产: {result['final_total_assets']:.3f}")
        print(f"买入次数: {result['buy_count']}, 卖出次数: {result['sell_count']}, 总佣金: {result['total_commission']:.3f}, 总印花税: {result['total_stamp_duty']:.3f}, 总资产差值（考虑费用）: {result['asset_change']:.3f}")

    # 统计盈亏
    profitable_stocks = [result for result in all_results if result['asset_change'] > 0]
    losing_stocks = [result for result in all_results if result['asset_change'] < 0]
    total_asset_change = sum(result['asset_change'] for result in all_results)

    print("\n--- 统计信息 ---")
    print(f"测试股票数量: {len(all_results)}")
    print(f"盈利股票情况: {len(profitable_stocks)} 支股票盈利，股票名称: {', '.join([result['stock_name'] for result in profitable_stocks])}")
    print(f"亏损股票情况: {len(losing_stocks)} 支股票亏损，股票名称: {', '.join([result['stock_name'] for result in losing_stocks])}")
    print(f"总盈亏: {total_asset_change:.3f}")

if __name__ == "__main__":
    main()
