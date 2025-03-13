import akshare as ak
import random
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
import os
from pathlib import Path

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
    if config['stock_selection'] == 'spec':
        return config['specified_stocks']
    elif config['stock_selection'] == 'rand':
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

# 获取股票分时成交数据并保存到本地
def get_stock_data(stock: str, start_date: str, end_date: str) -> str:
    """
    获取指定股票在指定日期范围内的分时成交数据，并保存为 CSV 文件。
    
    :param stock: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: str, CSV 文件路径
    """
    # 根据股票代码前缀调整分钟线代码
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
    
    # 删除 symbol 和 name 列
    all_data = all_data.drop(columns=['symbol', 'name'])
    
    # 保存到本地
    try:
        file_name = f"{stock}_{start_date}_to_{end_date}.csv"
        all_data.to_csv(file_name, index=False)
        print(f"数据已保存到 {file_name}")
        return file_name
    except Exception as e:
        print(f"保存数据时出错: {e}")
        return None

# 上传文件到平台
def upload_file(file_path: str, api_key: str) -> str:
    """
    上传文件到通义千问平台。
    
    :param file_path: str, 文件路径
    :param api_key: str, API 密钥
    :return: str, 文件 ID
    """
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    file_object = client.files.create(file=Path(file_path), purpose="file-extract")
    print(f"文件上传成功，文件 ID: {file_object.id}")
    return file_object.id

# 与通义千问模型交互
def chat_with_qwen(file_id: str, question: str, api_key: str) -> str:
    """
    使用通义千问的 API 进行聊天。
    
    :param file_id: str, 文件 ID
    :param question: str, 用户提示或问题
    :param api_key: str, API 密钥
    :return: str, 聊天结果
    """
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    completion = client.chat.completions.create(
        model="qwen-long",
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'system', 'content': f'fileid://{file_id}'},
            {'role': 'user', 'content': question}
        ],
        stream=True,
        stream_options={"include_usage": True}
    )

    full_content = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            # 拼接输出内容
            full_content += chunk.choices[0].delta.content
            print(chunk.model_dump())

    print({full_content})
    return full_content

# 主函数
def analyze_stocks(config_file: str = 'config.json'):
    """分析股票的主函数"""
    # 1. 读取配置
    config = load_config(config_file)
    stocks = select_stocks(config)
    start_date = config['start_date']
    end_date = config['end_date']
    prompt_template = config['prompt']
    api_key = config.get('api_key', 'YOUR_API_KEY')  # 从配置文件读取 API 密钥

    # 2. 循环处理每只股票
    for stock in stocks:
        print(f"正在处理股票: {stock}")
        try:
            # 获取分时成交数据并保存为 CSV 文件
            file_path = get_stock_data(stock, start_date, end_date)
            if file_path is None:
                print(f"股票 {stock} 未获取到数据，跳过")
                continue

            # 上传文件到平台
            file_id = upload_file(file_path, api_key)
            if file_id is None:
                print(f"股票 {stock} 的文件上传失败，跳过")
                continue

            # 与通义千问模型交互
            response = chat_with_qwen(file_id, prompt_template.format(stock_data=""), api_key)
            if response:
                print(f"股票 {stock} 的分析结果: {response}\n")
            else:
                print(f"股票 {stock} 的分析结果: 聊天请求失败！\n")

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

# 运行程序
if __name__ == "__main__":
    analyze_stocks('retestconfig.json')
