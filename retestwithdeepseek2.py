import akshare as ak
import random
import json
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI

# 读取配置文件
def load_config(config_file: str) -> Dict[str, Any]:
    """读取 JSON 配置文件并返回配置字典"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"读取配置文件失败: {e}")

# 选择股票
def select_stocks(config: Dict[str, Any]) -> List[str]:
    """根据配置文件选择股票"""
    if config['stock_selection'] == 'specified':
        return config['specified_stocks']
    elif config['stock_selection'] == 'random':
        all_stocks = ak.stock_zh_a_spot_em()['代码'].tolist()
        return random.sample(all_stocks, min(config['random_stock_count'], len(all_stocks)))
    else:
        raise ValueError("配置文件中的 'stock_selection' 必须是 'specified' 或 'random'")

# 获取交易日历
def get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """获取指定日期范围内的交易日列表"""
    calendar = ak.tool_trade_date_hist_sina()
    calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    trading_dates = calendar[(calendar['trade_date'] >= start_date) & 
                             (calendar['trade_date'] <= end_date)]['trade_date']
    return trading_dates.dt.strftime('%Y%m%d').tolist()

# 获取股票分时成交数据
def get_stock_data(stock: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取指定股票在指定日期范围内的分时成交数据"""
    if stock.startswith('688'):
        minute_code = f"sh{stock}"
    elif stock.startswith(('83', '43', '87')):
        minute_code = f"bj{stock}"
    elif stock.startswith('60'):
        minute_code = f"sh{stock}"
    elif stock.startswith(('00', '30')):
        minute_code = f"sz{stock}"
    else:
        minute_code = stock

    print(f"minute_code: {minute_code}")
    trading_dates = get_trading_dates(start_date, end_date)
    stock_data_list = []
    
    for date in trading_dates:
        try:
            daily_data = ak.stock_intraday_sina(symbol=minute_code, date=date)
            if not daily_data.empty:
                daily_data['ticktime'] = pd.to_datetime(date + ' ' + daily_data['ticktime'])
                stock_data_list.append(daily_data)
        except Exception as e:
            print(f"获取股票 {minute_code} 在 {date} 的数据时出错: {e}")
            continue

    if not stock_data_list:
        raise ValueError(f"无法获取 {minute_code} 的逐笔成交数据")

    all_data = pd.concat(stock_data_list)
    all_data = all_data.sort_values('ticktime').reset_index(drop=True)
    return all_data

# 调用 DeepSeek API
def call_deepseek_api(messagein: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": messagein}],
        max_tokens=1024,
        temperature=0.7,
        stream=False
    )
    return response.choices[0].message.content

# 分析股票数据
def analyze_stocks(config_file: str = 'config.json'):
    """分析股票数据"""
    config = load_config(config_file)
    stocks = select_stocks(config)
    start_date = config['start_date']
    end_date = config['end_date']
    prompt_template = config['prompt']
    api_key = config.get('api_key', 'YOUR_API_KEY')

    chunk_size = 1000  # 设定数据块大小

    for stock in stocks:
        print(f"正在处理股票: {stock}")
        try:
            stock_data = get_stock_data(stock, start_date, end_date)
            stock_json = stock_data.to_json(orient='records', force_ascii=False)

            # 分割数据
            data_chunks = [stock_json[i:i + chunk_size] for i in range(0, len(stock_json), chunk_size)]

            # 发送初始化 prompt
            init_prompt = (
                f"{prompt_template}\n\n"
                "由于我要发送给你的数据比较多，我将分段发送，期间你不需要解答，"
                "等我把数据全部发完之后，我会告诉你，你再解答。"
            )
            call_deepseek_api(init_prompt, api_key)

            # 依次发送数据分块
            for idx, chunk_json in enumerate(data_chunks):
                call_deepseek_api(chunk_json, api_key)
                print(f"股票 {stock} - 已发送分段 {idx + 1}")

            # 发送完成提示
            call_deepseek_api("数据已发送完毕，请根据我的要求进行解读。", api_key)

        except Exception as e:
            print(f"分析股票 {stock} 失败: {e}")
            continue

# 运行分析
if __name__ == "__main__":
    analyze_stocks()
