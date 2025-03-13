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
    if config['stock_selection'] == 'specified':
        return config['specified_stocks']
    elif config['stock_selection'] == 'random':
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
    start_date_dt = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    trading_dates = calendar[(calendar['trade_date'] >= start_date_dt) & 
                             (calendar['trade_date'] <= end_date_dt)]['trade_date']
    return trading_dates.dt.strftime('%Y%m%d').tolist()

# 获取分时成交数据
def get_intraday_data(stock: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定股票在指定日期范围内的分时成交数据。
    
    :param stock: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: pd.DataFrame, 分时成交数据，symbol 和 name 列已删除
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
    all_data = all_data.drop(columns=['symbol', 'name'], errors='ignore')
    return all_data

# 获取日K线数据
def get_daily_kline_data(symbol: str, end_date: str, kline_days: int) -> pd.DataFrame:
    """
    获取指定股票最近 kline_days 个交易日的日K线数据。
    
    :param symbol: str, 股票代码，例如 '300680'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 需要的交易日数量，例如 60
    :return: pd.DataFrame, 日K线数据
    """
    calendar = ak.tool_trade_date_hist_sina()
    calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
    end_dt = pd.to_datetime(end_date)
    
    # 获取所有交易日 <= end_dt，降序排序，取前 kline_days 个（最新的）
    trading_dates_filtered = calendar[calendar['trade_date'] <= end_dt]['trade_date'].sort_values(ascending=False).head(kline_days)
    
    if len(trading_dates_filtered) < kline_days:
        print(f"Warning: Only {len(trading_dates_filtered)} trading days available up to {end_date}")
    
    start_dt_kline = trading_dates_filtered.iloc[-1]  # 最早的日期在最后面，因为是降序
    end_dt_kline = trading_dates_filtered.iloc[0]  # 最晚的日期在最前面
    
    start_date_kline = start_dt_kline.strftime('%Y%m%d')
    end_date_kline = end_dt_kline.strftime('%Y%m%d')
    
    # 获取日K线数据
    stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date_kline, end_date=end_date_kline, adjust="")
    return stock_data

# 获取并保存股票数据到Excel文件
def get_and_save_stock_data(stock: str, start_date: str, end_date: str, kline_days: int) -> str:
    """
    获取股票的分时成交数据和日K线数据，并保存到Excel文件中，分别在'intraday'和'daily'两个sheet中。
    
    :param stock: str, 股票代码，例如 '300680'
    :param start_date: str, 分时数据的起始日期，格式 'YYYYMMDD'
    :param end_date: str, 数据的结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 日K线数据的天数，例如 60
    :return: str, 文件路径，如果失败返回 None
    """
    try:
        df_intraday = get_intraday_data(stock=stock, start_date=start_date, end_date=end_date)
        df_daily = get_daily_kline_data(symbol=stock, end_date=end_date, kline_days=kline_days)
        
        file_name = f"{stock}_{start_date}_to_{end_date}.xlsx"
        
        with pd.ExcelWriter(file_name) as writer:
            df_intraday.to_excel(writer, sheet_name='intraday', index=False)
            df_daily.to_excel(writer, sheet_name='daily', index=False)
        
        print(f"Data saved to {file_name}")
        return file_name
    except Exception as e:
        print(f"Error processing stock {stock}: {e}")
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
    kline_days = config.get('kline_days', 60)  # 默认60天，如果未指定

    # 2. 循环处理每只股票
    for stock in stocks:
        print(f"正在处理股票: {stock}")
        try:
            # 获取数据并保存到Excel文件
            file_path = get_and_save_stock_data(stock=stock, start_date=start_date, end_date=end_date, kline_days=kline_days)
            if file_path is None:
                print(f"股票 {stock} 获取数据失败，跳过")
                continue

            # 上传文件到平台
            file_id = upload_file(file_path=file_path, api_key=api_key)
            if file_id is None:
                print(f"股票 {stock} 的文件上传失败，跳过")
                continue

            # 与通义千问模型交互
            response = chat_with_qwen(file_id=file_id, question=prompt_template.format(stock_data=""), api_key=api_key)
            if response:
                print(f"股票 {stock} 的分析结果: {response}\n")
            else:
                print(f"股票 {stock} 的聊天请求失败！\n")

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

# 运行程序
if __name__ == "__main__":
    analyze_stocks('retestconfig.json')
