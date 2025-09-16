import akshare as ak
import random
import json
import pandas as pd
import numpy as np
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
                    print("等待10分钟后重试...")
                    for _ in range(300):  # 等待600秒（10分钟），每2秒打印一个“.”
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

def get_stock_data(stock: str, start_date: str, end_date: str, kline_days: int) -> tuple:
    """
    获取股票的日K线数据、大盘指数数据和行业板块数据（跳过分时数据以减少token使用）。

    :param stock: str, 股票代码，例如 '300680'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'（已废弃，K线数据使用kline_days计算）
    :param end_date: str, 结束日期，格式 'YYYYMMDD'（已废弃，K线数据使用kline_days计算）
    :param kline_days: int, 日K线数据的天数，例如 60
    :return: tuple, (daily_df, market_df, industry_df, stock_name)
    """
    try:
        # 跳过分时成交数据，直接获取K线数据
        print(f"正在获取股票 {stock} 的K线数据...")

        # 使用kline_days计算K线数据的正确日期范围
        kline_start_date, kline_end_date = get_kline_date_range(kline_days)

        # 获取日K线数据
        df_daily = get_daily_kline_data(symbol=stock, end_date=kline_end_date, kline_days=kline_days)

        # 从日K线数据中提取股票名称
        stock_name = "未知"
        if df_daily is not None and not df_daily.empty:
            # 可以通过其他方式获取股票名称，这里暂时使用代码作为名称
            stock_name = f"股票{stock}"

        # 大盘指数数据使用K线数据的日期范围
        df_market, market_index_name = get_market_index_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 行业板块数据使用K线数据的日期范围
        df_industry, industry_sector_name = get_industry_sector_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        print(f"✅ 股票 {stock} K线数据获取完成")
        return df_daily, df_market, df_industry, stock_name, market_index_name, industry_sector_name

    except Exception as e:
        print(f"❌ 获取股票 {stock} 数据时出错: {e}")
        return None, None, None, None, "未知指数", "未知板块"

def format_data_for_analysis(daily_df: pd.DataFrame, market_df: pd.DataFrame,
                           industry_df: pd.DataFrame, stock_name: str, stock_code: str,
                           market_index_name: str = "大盘指数", industry_sector_name: str = "行业板块") -> str:
    """
    将K线数据格式化为适合大模型分析的文本格式。

    :param daily_df: 日K线数据
    :param market_df: 大盘指数数据
    :param industry_df: 行业板块数据
    :param stock_name: 股票名称
    :param stock_code: 股票代码
    :param market_index_name: 大盘指数名称
    :param industry_sector_name: 行业板块名称
    :return: str, 格式化的数据文本
    """

    def format_dataframe(df: pd.DataFrame, name: str) -> str:
        """格式化DataFrame为文本"""
        if df is None or df.empty:
            return f"{name}: 无数据"

        total_rows = len(df)
        data_str = df.to_string(index=False)
        return f"{name} (共{total_rows}行):\n{data_str}"

    formatted_text = f"""股票代码: {stock_code}
股票名称: {stock_name}

数据概览:
- 日K线数据: {len(daily_df) if daily_df is not None else 0} 条记录
- 大盘指数数据: {len(market_df) if market_df is not None else 0} 条记录 ({market_index_name})
- 行业板块数据: {len(industry_df) if industry_df is not None else 0} 条记录 ({industry_sector_name})

=== 日K线数据 (Daily) ===
{format_dataframe(daily_df, "日K线数据")}

=== 大盘指数数据 ({market_index_name}) ===
{format_dataframe(market_df, f"{market_index_name}数据")}

=== 行业板块数据 ({industry_sector_name}) ===
{format_dataframe(industry_df, f"{industry_sector_name}板块数据")}
"""

    return formatted_text

def save_data_to_file(data_text: str, stock_code: str, file_suffix: str = "") -> str:
    """
    将格式化的数据保存到文件中。

    :param data_text: str, 格式化的数据文本
    :param stock_code: str, 股票代码
    :param file_suffix: str, 文件后缀，用于区分不同版本
    :return: str, 保存的文件路径
    """
    import os
    from datetime import datetime

    # 创建数据目录
    data_dir = "data_output"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{data_dir}/{stock_code}_data_{timestamp}{file_suffix}.txt"
    filepath = filename

    # 保存数据到文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"=== 发送给大模型的数据 ===\n")
        f.write(f"股票代码: {stock_code}\n")
        f.write(f"保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(data_text)

    print(f"✅ 数据已保存到文件: {filepath}")
    return filepath

def select_prompt_by_model(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据当前脚本使用的模型智能选择对应的prompt配置。

    :param config: 配置字典
    :return: 对应的prompt配置
    """
    # 检查是否有推理模型专用prompt
    if 'prompt_inference' in config:
        print("🎯 检测到推理模型专用prompt配置")
        return config['prompt_inference']

    # 回退到通用prompt
    print("ℹ️ 未找到推理模型专用prompt，使用通用prompt")
    return config.get('prompt', {})

def chat_with_qwen_max(data_text: str, question: Any, api_key: str) -> str:
    """
    使用通义千问 qwen-max 模型进行聊天，直接发送数据文本。

    :param data_text: str, 格式化的股票数据文本
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
        {'role': 'system', 'content': 'You are a helpful assistant specializing in stock market analysis.'}
    ]

    # 处理 question 参数
    if isinstance(question, dict):
        # 如果 question 是字典，假设它包含 analysis_request
        analysis_request = question.get('analysis_request', {})

        # 构造用户消息内容
        user_content = (
            f"{analysis_request.get('analysis_purpose', {}).get('description', '')}\n\n"
            f"=== 股票数据 ===\n{data_text}\n\n"
            f"请基于以上数据进行专业分析：\n\n"
        )

        # 添加数据描述
        data_desc = analysis_request.get('data_description', {})
        if 'daily_sheet' in data_desc:
            daily = data_desc['daily_sheet']
            user_content += f"日K线数据说明: {daily.get('description', '')}\n"
            user_content += f"日K线数据字段: {', '.join(daily.get('fields', []))}\n\n"

        # 添加分析步骤
        user_content += "分析步骤:\n"
        for step in analysis_request.get('analysis_steps', []):
            user_content += f"步骤 {step.get('step', '')}: {step.get('description', '')}\n"

        # 添加输出要求
        user_content += "\n输出要求:\n"
        for req in analysis_request.get('output_requirements', []):
            user_content += f"{req.get('section', '')}. {req.get('title', '')}: {req.get('description', '')}\n"

        messages.append({'role': 'user', 'content': user_content})
    elif isinstance(question, str):
        # 如果 question 是字符串，直接使用（保持后向兼容性）
        user_content = f"=== 股票数据 ===\n{data_text}\n\n{question}"
        messages.append({'role': 'user', 'content': user_content})
    else:
        raise ValueError("question 参数必须是字符串或字典类型")

    # 调用 qwen-max API
    completion = client.chat.completions.create(
        model="qwen-max",
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

def analyze_stocks_max(config_file: str = 'anylizeconfig.json', keys_file: str = 'keys.json'):
    """使用 qwen-max 分析股票的主函数"""
    # 1. 读取配置
    config = load_config(config_file, keys_file)
    stocks = select_stocks(config)

    # 根据kline_days计算K线数据的日期范围
    kline_days = config.get('kline_days', 60)  # 默认60天
    start_date, end_date = get_kline_date_range(kline_days)
    print(f"📅 K线数据日期范围: {start_date} 到 {end_date} (共{kline_days}个交易日)")

    # 智能选择prompt配置
    prompt_template = select_prompt_by_model(config)
    print(f"🎯 使用推理模型专用prompt (qwen-max)")

    api_key = config['api_key']  # 从 keys.json 读取 API 密钥
    email_sender = config['email_sender']  # 从配置文件读取发件人邮箱地址
    email_password = config['email_password']  # 从 keys.json 读取发件人邮箱密码
    email_receivers = config['email_receivers']  # 从配置文件读取收件人邮箱地址

    # 2. 循环处理每只股票
    total = len(stocks)
    for index, stock in enumerate(stocks):
        print(f"正在处理股票: {stock} ({index+1}/{total})")
        try:
            # 获取股票数据（不保存文件）
            result = get_stock_data(stock=stock, start_date=start_date, end_date=end_date, kline_days=kline_days)
            if result[0] is None:
                print(f"股票 {stock} 获取数据失败，跳过")
                continue

            df_daily, df_market, df_industry, stock_name, market_index_name, industry_sector_name = result

            # 格式化数据为文本
            data_text = format_data_for_analysis(
                daily_df=df_daily,
                market_df=df_market,
                industry_df=df_industry,
                stock_name=stock_name,
                stock_code=stock,
                market_index_name=market_index_name,
                industry_sector_name=industry_sector_name
            )

            # 保存数据到文件供检查（完整数据，未压缩）
            saved_file = save_data_to_file(data_text, stock, "_complete")
            print(f"📄 完整数据文件已保存，您可以查看: {saved_file}")

            # 保存完整的用户消息（调试用）
            if isinstance(prompt_template, dict):
                analysis_request = prompt_template.get('analysis_request', {})
                full_message = (
                    f"{analysis_request.get('analysis_purpose', {}).get('description', '')}\n\n"
                    f"=== 股票数据 ===\n{data_text}\n\n"
                    f"请基于以上数据进行专业分析：\n\n"
                )

                # 添加数据描述和分析步骤
                data_desc = analysis_request.get('data_description', {})
                if 'daily_sheet' in data_desc:
                    daily = data_desc['daily_sheet']
                    full_message += f"日K线数据说明: {daily.get('description', '')}\n"
                    full_message += f"日K线数据字段: {', '.join(daily.get('fields', []))}\n\n"

                full_message += "分析步骤:\n"
                for step in analysis_request.get('analysis_steps', []):
                    full_message += f"步骤 {step.get('step', '')}: {step.get('description', '')}\n"

                full_message += "\n输出要求:\n"
                for req in analysis_request.get('output_requirements', []):
                    full_message += f"{req.get('section', '')}. {req.get('title', '')}: {req.get('description', '')}\n"
            else:
                full_message = f"=== 股票数据 ===\n{data_text}\n\n{prompt_template}"

            # 保存完整消息
            full_message_file = save_data_to_file(full_message, stock, "_full_message")
            print(f"📄 完整消息已保存，您可以查看: {full_message_file}")

            # 与 qwen-max 模型交互
            print(f"正在使用 qwen-max 分析股票 {stock}...")
            response = chat_with_qwen_max(data_text=data_text, question=prompt_template, api_key=api_key)
            if response:
                print(f"\n股票 {stock} 的分析结果: {response}\n")
            else:
                print(f"股票 {stock} 的聊天请求失败！\n")

            # 发送邮件
            print(f"股票 {stock} 准备发送邮件 \n")
            send_email(
                subject=f"股票 {stock} 分析结果 (qwen-max)",
                body=response,
                receivers=email_receivers,
                sender=email_sender,
                password=email_password
            )

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

        if index < total - 1:
            for i in range(60):  # 等待 300 秒，避免请求过于频繁
                print(".", end="", flush=True)
                t.sleep(1)  # 避免请求过于频繁

# 测试数据保存功能（验证完整数据，未压缩）
def test_data_save():
    """测试数据保存功能，验证数据完整性"""
    # 创建测试数据（K线数据格式，完整显示，无压缩）
    test_data = """股票代码: 000001
股票名称: 平安银行

数据概览:
- 日K线数据: 5 条记录
- 大盘指数数据: 5 条记录
- 行业板块数据: 5 条记录

=== 日K线数据 (Daily) ===
日K线数据 (共5行):
日期        开盘价  收盘价  最高价  最低价  成交量     成交额
2025-08-01  10.20  10.50  10.80  10.10  1000000  10500000
2025-08-02  10.50  10.70  10.90  10.40   800000   8600000
2025-08-03  10.70  10.60  10.85  10.55   900000   9650000
2025-08-04  10.60  10.80  11.00  10.50  1100000  11800000
2025-08-05  10.80  10.90  11.20  10.75  1200000  13000000

=== 大盘指数数据 (Market Index) ===
大盘指数数据 (共5行):
日期        开盘价  收盘价  最高价  最低价  成交量
2025-08-01  3200.00  3250.50  3270.80  3180.10  1500000000
2025-08-02  3250.50  3260.80  3280.00  3240.40  1600000000
2025-08-03  3260.80  3240.20  3270.50  3230.10  1550000000
2025-08-04  3240.20  3270.90  3290.50  3235.80  1700000000
2025-08-05  3270.90  3285.60  3310.20  3265.40  1750000000

=== 行业板块数据 (Industry Sector) ===
行业板块数据 (共5行):
日期        开盘价  收盘价  最高价  最低价  成交量
2025-08-01   850.00   875.50   880.80   840.10   80000000
2025-08-02   875.50   870.20   885.50   865.10   85000000
2025-08-03   870.20   885.90   890.50   868.80   90000000
2025-08-04   885.90   880.60   895.20   880.10   95000000
2025-08-05   880.60   892.30   900.80   878.50  100000000"""

    # 测试保存功能
    saved_file = save_data_to_file(test_data, "000001", "_complete_test")
    print(f"✅ 测试数据已保存到: {saved_file}")
    print("📊 数据状态: 完整显示，无压缩")

    # 读取并验证数据完整性
    with open(saved_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否包含所有5行数据
    lines = content.split('\n')
    kline_count = sum(1 for line in lines if '2025-08-' in line and '10.' in line)
    market_count = sum(1 for line in lines if '2025-08-' in line and '3200' in line)
    industry_count = sum(1 for line in lines if '2025-08-' in line and '850' in line)

    print(f"验证结果:")
    print(f"- 日K线数据: {kline_count}/5 行 ✓" if kline_count == 5 else f"- 日K线数据: {kline_count}/5 行 ❌")
    print(f"- 大盘指数数据: {market_count}/5 行 ✓" if market_count == 5 else f"- 大盘指数数据: {market_count}/5 行 ❌")
    print(f"- 行业板块数据: {industry_count}/5 行 ✓" if industry_count == 5 else f"- 行业板块数据: {industry_count}/5 行 ❌")

    # 检查是否没有压缩标记
    has_compression = "... (省略" in content or "[数据已被压缩" in content
    print(f"- 数据压缩: {'❌ 有压缩' if has_compression else '✅ 无压缩'}")

    return saved_file

# 运行程序
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 运行测试
        print("🧪 运行数据保存功能测试...")
        test_data_save()
    else:
        # 运行主程序
        analyze_stocks_max('anylizeconfig.json', 'keys.json')
