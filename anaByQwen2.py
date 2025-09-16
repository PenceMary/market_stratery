import akshare as ak
import random
import json
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from openai import OpenAI
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
import time as t

def send_email(subject: str, body: str, receivers: List[str], sender: str, password: str, file_path: str = None) -> bool:
    """发送邮件并返回是否成功"""
    # 创建文本邮件
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = sender  # 发件人
    msg['To'] = ', '.join(receivers)  # 将收件人列表转换为逗号分隔的字符串
    msg['Subject'] = subject

    # SMTP服务器设置
    smtp_server = 'applesmtp.163.com'
    smtp_port = 465

    # 登录凭证（使用授权码）
    username = sender

    # 发送邮件
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(username, password)
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        print("邮件发送成功！")
        # 如果邮件发送成功且提供了文件路径，则删除本地文件
        if file_path and os.path.exists(file_path):
            #os.remove(file_path)
            print(f"本地文件 {file_path} 已删除")
        return True
    except Exception as e:
        print(f"邮件发送失败：{e}")
        return False

def load_config(config_file: str, keys_file: str) -> Dict[str, Any]:
    """读取 JSON 配置文件并返回配置字典"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        with open(keys_file, 'r', encoding='utf-8') as f:
            keys = json.load(f)
        config.update(keys)  # 合并 keys.json 中的配置
        return config
    except Exception as e:
        raise Exception(f"读取配置文件失败: {e}")

def select_stocks(config: Dict[str, Any]) -> List[str]:
    """根据配置文件选择股票"""
    if config['stock_selection'] == 'specified':
        return config['specified_stocks']
    elif config['stock_selection'] == 'random':
        all_stocks = ak.stock_zh_a_spot_em()['代码'].tolist()
        return random.sample(all_stocks, min(config['random_stock_count'], len(all_stocks)))
    else:
        raise ValueError("配置文件中的 'stock_selection' 必须是 'specified' 或 'random'")

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
        max_retries = 3  # 最大重试次数
        for attempt in range(max_retries):
            try:
                daily_data = ak.stock_intraday_sina(symbol=minute_code, date=date)
                if not daily_data.empty:
                    daily_data['ticktime'] = pd.to_datetime(date + ' ' + daily_data['ticktime'])
                    stock_data_list.append(daily_data)
                    print(f"成功获取 {minute_code} 在 {date} 的数据")
                    # 如果不是最后一个交易日，等待 2 分钟
                    if date != trading_dates[-1]:
                        print("稍等一下...")
                        for _ in range(random.randint(1, 10)):  # 等待随机秒数，每秒打印一个“.”
                            print(".", end="", flush=True)
                            t.sleep(1)
                        print()  # 换行
                    break  # 成功获取数据，跳出重试循环
            except Exception as e:
                print(f"获取股票 {minute_code} 在 {date} 的数据时出错: {e}")
                if attempt < max_retries - 1:  # 如果不是最后一次尝试，则等待重试
                    print("等待20秒后重试...")
                    for _ in range(10):  # 等待600秒（10分钟），每2秒打印一个“.”
                        print(".", end="", flush=True)
                        t.sleep(2)
                    print()  # 换行
                else:
                    print(f"股票 {minute_code} 在 {date} 的数据获取失败，跳过")
                    break  # 达到最大重试次数，跳出循环

    if not stock_data_list:
        raise ValueError(f"无法获取 {minute_code} 的逐笔成交数据")
    stock_name = daily_data['name'][0]
    all_data = pd.concat(stock_data_list)
    all_data = all_data.sort_values('ticktime').reset_index(drop=True)
    all_data = all_data.drop(columns=['symbol', 'name'], errors='ignore')
    return all_data, stock_name

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

def get_market_index_data(stock_code: str, start_date: str, end_date: str) -> tuple:
    """
    根据股票代码获取对应的大盘指数日K线数据和指数名称。

    :param stock_code: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: tuple, (pd.DataFrame, str) - 大盘指数日K线数据和指数名称
    """
    print(f"正在获取股票 {stock_code} 对应的大盘指数数据...")

    # 根据股票代码确定大盘指数
    if stock_code.startswith(('60', '688')):
        index_code = "000001"  # 上证指数
        index_name = "上证指数"
        print(f"识别为上海市场股票，使用上证指数 ({index_code})")
    elif stock_code.startswith(('00', '30')):
        index_code = "399001"  # 深圳成指
        index_name = "深圳成指"
        print(f"识别为深圳市场股票，使用深圳成指 ({index_code})")
    elif stock_code.startswith(('83', '43', '87')):
        index_code = "899050"  # 北证50
        index_name = "北证50"
        print(f"识别为北京市场股票，使用北证50 ({index_code})")
    else:
        index_code = "000001"  # 默认使用上证指数
        index_name = "上证指数(默认)"
        print(f"无法识别市场类型，默认使用上证指数 ({index_code})")

    try:
        # 获取大盘指数数据
        index_data = ak.stock_zh_a_hist(symbol=index_code, period="daily",
                                      start_date=start_date, end_date=end_date, adjust="")

        if index_data.empty:
            print(f"❌ 获取 {index_name} 数据失败，返回空数据")
            return pd.DataFrame(), "未知指数"

        print(f"✅ {index_name} 数据获取成功，共 {len(index_data)} 条记录")
        print(f"   时间范围: {index_data['日期'].min()} 到 {index_data['日期'].max()}")

        return index_data, index_name

    except Exception as e:
        print(f"❌ 获取 {index_name} 数据时出错: {e}")
        return pd.DataFrame(), "未知指数"

def get_industry_sector_data(stock_code: str, start_date: str, end_date: str) -> tuple:
    """
    获取股票所属行业板块的日K线数据和板块名称。

    :param stock_code: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: tuple, (pd.DataFrame, str) - 行业板块日K线数据和板块名称
    """
    print(f"正在获取股票 {stock_code} 所属行业板块数据...")

    try:
        # 步骤1: 获取股票基本信息
        stock_info_df = ak.stock_individual_info_em(symbol=stock_code)

        if stock_info_df.empty:
            print("❌ 获取股票基本信息失败")
            return pd.DataFrame(), "未知板块"

        # 从DataFrame中提取信息
        info_dict = dict(zip(stock_info_df['item'], stock_info_df['value']))

        stock_name = info_dict.get('股票简称', '未知')
        industry_name = info_dict.get('行业', '未知')

        print(f"✅ 股票信息获取成功: {stock_name}")
        print(f"   行业分类: {industry_name}")

        if industry_name == '未知' or not industry_name:
            print("❌ 无法获取行业分类信息")
            return pd.DataFrame(), "未知板块"

        # 步骤2: 获取行业板块数据
        print(f"正在获取 '{industry_name}' 行业板块数据...")
        industry_data = ak.stock_board_industry_hist_em(symbol=industry_name,
                                                       start_date=start_date,
                                                       end_date=end_date)

        if industry_data.empty:
            print(f"❌ 获取 '{industry_name}' 行业板块数据失败")
            print("   可能原因: 行业名称格式不匹配或数据不可用")
            return pd.DataFrame(), f"{industry_name}(数据获取失败)"

        print(f"✅ 行业板块数据获取成功，共 {len(industry_data)} 条记录")
        print(f"   时间范围: {industry_data['日期'].min()} 到 {industry_data['日期'].max()}")

        return industry_data, industry_name

    except Exception as e:
        print(f"❌ 获取行业板块数据时出错: {e}")
        return pd.DataFrame(), "未知板块"

def get_and_save_stock_data(stock: str, start_date: str, end_date: str, kline_days: int) -> str:
    """
    获取股票的分时成交数据、日K线数据、大盘指数数据和行业板块数据，并保存到Excel文件中。

    :param stock: str, 股票代码，例如 '300680'
    :param start_date: str, 分时数据的起始日期，格式 'YYYYMMDD'
    :param end_date: str, 分时数据的结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 日K线数据的天数，例如 60
    :return: str, 文件路径，如果失败返回 None
    """
    try:
        # 分时数据使用传递的日期范围（来自daysBeforeToday）
        df_intraday, stock_name = get_intraday_data(stock=stock, start_date=start_date, end_date=end_date)

        # K线数据使用基于kline_days计算的日期范围
        kline_start_date, kline_end_date = get_kline_date_range(kline_days)
        df_daily = get_daily_kline_data(symbol=stock, end_date=kline_end_date, kline_days=kline_days)

        # 大盘指数数据使用K线数据的日期范围
        df_market, market_index_name = get_market_index_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 行业板块数据使用K线数据的日期范围
        df_industry, industry_sector_name = get_industry_sector_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 生成三位随机数，避免文件名冲突
        random_suffix = str(random.randint(0, 999)).zfill(3)
        file_name = f"{stock}_{stock_name}_{start_date}_to_{end_date}_{random_suffix}.xlsx"

        # 保存到Excel文件
        with pd.ExcelWriter(file_name) as writer:
            df_intraday.to_excel(writer, sheet_name='intraday', index=False)
            df_daily.to_excel(writer, sheet_name='daily', index=False)
            if not df_market.empty:
                df_market.to_excel(writer, sheet_name='market_index', index=False)
            if not df_industry.empty:
                df_industry.to_excel(writer, sheet_name='industry_sector', index=False)

        print(f"✅ 所有数据已保存到 {file_name}")
        print(f"   包含工作表: intraday, daily, market_index, industry_sector")
        return file_name, stock_name

    except Exception as e:
        print(f"❌ 处理股票 {stock} 时出错: {e}")
        return None

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

def chat_with_qwen(file_id: str, question: Any, api_key: str) -> str:
    """
    使用通义千问的 API 进行聊天，支持字典或字符串类型的 question。
    
    :param file_id: str, 文件 ID
    :param question: Any, 用户提示或问题，可以是字符串或字典
    :param api_key: str, API 密钥
    :return: str, 聊天结果
    """
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 初始化 messages 列表
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'system', 'content': f'fileid://{file_id}'}
    ]

    # 处理 question 参数
    if isinstance(question, dict):
        # 如果 question 是字典，假设它包含 analysis_request
        analysis_request = question.get('analysis_request', {})

        # 构造用户消息内容
        user_content = (
            f"{analysis_request.get('analysis_purpose', {}).get('description', '')}\n\n"
            f"intraday sheet: {analysis_request.get('data_description', {}).get('intraday_sheet', {}).get('description', '')}\n"
            f"字段: {', '.join(analysis_request.get('data_description', {}).get('intraday_sheet', {}).get('fields', []))}\n"
            f"daily sheet: {analysis_request.get('data_description', {}).get('daily_sheet', {}).get('description', '')}\n"
            f"字段: {', '.join(analysis_request.get('data_description', {}).get('daily_sheet', {}).get('fields', []))}\n\n"
            f"分析步骤:\n"
        )

        # 添加分析步骤
        for step in analysis_request.get('analysis_steps', []):
            user_content += f"步骤 {step.get('step', '')}: {step.get('description', '')}\n"

        # 添加输出要求
        user_content += "\n输出要求:\n"
        for req in analysis_request.get('output_requirements', []):
            user_content += f"{req.get('section', '')}. {req.get('title', '')}: {req.get('description', '')}\n"

        messages.append({'role': 'user', 'content': user_content})
    elif isinstance(question, str):
        # 如果 question 是字符串，直接使用（保持后向兼容性）
        messages.append({'role': 'user', 'content': question})
    else:
        raise ValueError("question 参数必须是字符串或字典类型")

    # 调用 API
    completion = client.chat.completions.create(
        model="qwen-long",
        messages=messages,
        stream=True,
        stream_options={"include_usage": True}
    )

    full_content = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_content += chunk.choices[0].delta.content
            print(".", end="", flush=True)

    return full_content

def select_prompt_by_model(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据当前脚本使用的模型智能选择对应的prompt配置。

    :param config: 配置字典
    :return: 对应的prompt配置
    """
    # 对于qwen-long，使用原有的通用prompt（包含分时数据处理）
    if 'prompt' in config:
        print("🎯 检测到文件处理模型专用prompt配置")
        return config['prompt']

    # 回退到通用prompt
    print("ℹ️ 未找到专用prompt，使用默认配置")
    return {}

def get_kline_date_range(kline_days: int) -> tuple:
    """
    根据kline_days计算K线数据的日期范围。

    :param kline_days: int, K线数据的天数
    :return: tuple, (start_date, end_date) 格式为YYYYMMDD
    """
    end_date = date.today().strftime('%Y%m%d')

    # 计算K线数据的开始日期（往前kline_days个交易日）
    calendar = ak.tool_trade_date_hist_sina()
    calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
    end_dt = pd.to_datetime(end_date)

    # 获取所有交易日 <= end_dt，降序排序，取前 kline_days 个（最新的）
    trading_dates_filtered = calendar[calendar['trade_date'] <= end_dt]['trade_date'].sort_values(ascending=False).head(kline_days)

    if len(trading_dates_filtered) < kline_days:
        print(f"⚠️ 警告: 仅找到 {len(trading_dates_filtered)} 个交易日，可用交易日不足 {kline_days} 天")

    start_dt_kline = trading_dates_filtered.iloc[-1]  # 最早的日期在最后面，因为是降序
    start_date = start_dt_kline.strftime('%Y%m%d')

    return start_date, end_date

def analyze_stocks(config_file: str = 'anylizeconfig.json', keys_file: str = 'keys.json'):
    """分析股票的主函数"""
    # 1. 读取配置
    config = load_config(config_file, keys_file)
    stocks = select_stocks(config)

    # 分时数据使用daysBeforeToday计算日期范围
    days_before = config['daysBeforeToday']
    intraday_start_date = (date.today() - timedelta(days=days_before)).strftime('%Y%m%d')
    intraday_end_date = date.today().strftime('%Y%m%d')
    print(f"📅 分时数据日期范围: {intraday_start_date} 到 {intraday_end_date}")

    # K线数据使用kline_days计算日期范围
    kline_days = config.get('kline_days', 60)  # 默认60天
    kline_start_date, kline_end_date = get_kline_date_range(kline_days)
    print(f"📅 K线数据日期范围: {kline_start_date} 到 {kline_end_date} (共{kline_days}个交易日)")

    # 智能选择prompt配置
    prompt_template = select_prompt_by_model(config)
    print(f"🎯 使用文件处理模型专用prompt (qwen-long)")

    api_key = config['api_key']  # 从 keys.json 读取 API 密钥
    email_sender = config['email_sender']  # 从配置文件读取发件人邮箱地址
    email_password = config['email_password']  # 从 keys.json 读取发件人邮箱密码
    email_receivers = config['email_receivers']  # 从配置文件读取收件人邮箱地址

    # 2. 循环处理每只股票
    total = len(stocks)
    for index, stock in enumerate(stocks):
        print(f"正在处理股票: {stock} ({index+1}/{total})")
        file_path = None  # 初始化文件路径
        try:
            # 获取数据并保存到Excel文件
            result = get_and_save_stock_data(stock=stock, start_date=intraday_start_date, end_date=intraday_end_date, kline_days=kline_days)
            if result is None:
                print(f"股票 {stock} 获取数据失败，跳过")
                continue
            file_path, stock_name = result

            # 上传文件到平台
            file_id = upload_file(file_path=file_path, api_key=api_key)
            if file_id is None:
                print(f"股票 {stock} 的文件上传失败，跳过")
                continue

            # 与通义千问模型交互，直接传递字典类型的 prompt_template
            response = chat_with_qwen(file_id=file_id, question=prompt_template, api_key=api_key)
            if response:
                print(f"股票 {stock} 的分析结果: {response}\n")
            else:
                print(f"股票 {stock} 的聊天请求失败！\n")

            # 发送邮件并根据结果决定是否删除文件
            print(f"股票 {stock} 准备发送邮件 \n")
            send_email(
                subject=f"股票 {stock} 分析结果",
                body=response,
                receivers=email_receivers,
                sender=email_sender,
                password=email_password,
                file_path=file_path  # 传递文件路径以便删除
            )

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

        if index < total - 1:
            for i in range(60):  # 等待 300 秒，避免请求过于频繁
                print(".", end="", flush=True)
                t.sleep(1)  # 避免请求过于频繁

# 运行程序
if __name__ == "__main__":
    analyze_stocks('anylizeconfig.json', 'keys.json')
