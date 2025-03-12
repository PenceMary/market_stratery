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
        # 获取所有A股股票列表
        all_stocks = ak.stock_zh_a_spot_em()['代码'].tolist()
        return random.sample(all_stocks, min(config['random_stock_count'], len(all_stocks)))
    else:
        raise ValueError("配置文件中的 'stock_selection' 必须是 'specified' 或 'random'")

# 获取交易日历
def get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """
    获取指定日期范围内的交易日列表。
    
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: list, 交易日列表，格式为 'YYYYMMDD'
    """
    calendar = ak.tool_trade_date_hist_sina()
    calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    trading_dates = calendar[(calendar['trade_date'] >= start_date) & 
                             (calendar['trade_date'] <= end_date)]['trade_date']
    return trading_dates.dt.strftime('%Y%m%d').tolist()

# 获取股票分时成交数据
def get_stock_data(stock: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定股票在指定日期范围内的分时成交数据。
    
    :param stock: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: DataFrame, 合并后的分时成交数据
    """
    # 根据股票代码前缀调整分钟线代码，支持场内基金
    if stock.startswith('688'):
        minute_code = f"sh{stock}"  # 上海科创板
    elif stock.startswith(('83', '43', '87')):
        minute_code = f"bj{stock}"  # 北京证券交易所
    elif stock.startswith('60'):
        minute_code = f"sh{stock}"  # 上海主板或上海ETF
    elif stock.startswith(('00', '30')):
        minute_code = f"sz{stock}"  # 深圳主板、创业板或深圳ETF
    else:
        minute_code = stock  # 其他股票
    print(f"minute_code:{minute_code}")

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
    
    # 合并所有交易日的 tick 数据
    all_data = pd.concat(stock_data_list)
    all_data = all_data.sort_values('ticktime').reset_index(drop=True)

    # 保存数据到当前目录
    try:
        file_name = f"{stock}_{start_date}_to_{end_date}.csv"
        all_data.to_csv(file_name, index=False)
        print(f"数据已保存到 {file_name}")
        return file_name
    except Exception as e:
        print(f"保存数据时出错: {e}")
    
    return None

# 调用 DeepSeek API
# def call_deepseek_api(messagein: str, api_key: str) -> str:
    
#     client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
#     print(f"messagein: {messagein}")
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "user", "content": "{}".format(messagein)}
#     ],
#         max_tokens=1024,
#         temperature=0.7,
#         stream=False
#     )

#     print(response.choices[0].message.content)

def upload_file(file_path, api_key):
    files = {"file": open(file_path, "rb")}
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post("https://api.deepseek.com/v1/upload", files=files, headers=headers)
    if response.status_code == 200:
        return response.json()["file_id"]  # 返回文件 ID
    else:
        print("文件上传失败！")
        print("状态码：", response.status_code)
        print("错误信息：", response.text)
        return None
    
def chat_with_file(file_id, question, api_key):
    payload = {
        "file_id": file_id,
        "question": question,
        "max_tokens": 500
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post("https://api.deepseek.com/v1/chat", json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["response"]  # 返回对话结果
    else:
        print("对话失败！")
        print("状态码：", response.status_code)
        print("错误信息：", response.text)
        return None

# 主函数
def analyze_stocks(config_file: str = 'config.json'):
    """分析股票的主函数"""
    # 1. 读取配置
    config = load_config(config_file)
    stocks = select_stocks(config)
    start_date = config['start_date']
    end_date = config['end_date']
    prompt_template = config['prompt']
    api_key = config.get('api_key', 'YOUR_API_KEY')  # 从配置文件读取 API 密钥，或使用默认值

    # 2. 循环处理每只股票
    for stock in stocks:
        print(f"正在处理股票: {stock}")
        try:
        # 获取分时成交数据
            filename = get_stock_data(stock, start_date, end_date)
            if None == filename:
                print(f"股票 {stock} 未获取到数据，跳过")
                continue

            file_id = upload_file(filename,api_key)
            if file_id != None:
                response = chat_with_file(file_id, prompt_template.format(stock_data=""),api_key)
                print(f"股票 {stock} 的分析结果: {response}\n")
            else:
                print(f"股票 {stock} 的分析结果: 上传文件失败！\n")

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

# 运行程序
if __name__ == "__main__":
    analyze_stocks('retestconfig.json')
