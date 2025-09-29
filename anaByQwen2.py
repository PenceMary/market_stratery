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
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import time as t
from md_to_html import MarkdownToHTMLConverter

def send_email(subject: str, body: str, receivers: List[str], sender: str, password: str, attachment_path: str = None) -> bool:
    """发送邮件并返回是否成功，如果提供attachment_path则发送HTML附件"""
    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = sender  # 发件人
    msg['To'] = ', '.join(receivers)  # 将收件人列表转换为逗号分隔的字符串
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 如果提供了附件路径，添加HTML附件
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype='html')
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attachment)
            print(f"已添加附件: {attachment_path}")
        except Exception as e:
            print(f"添加附件失败: {e}")
            return False

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
        # 如果邮件发送成功且提供了附件路径，则删除本地文件
        if attachment_path and os.path.exists(attachment_path):
            #os.remove(attachment_path)
            print(f"本地文件 {attachment_path} 已删除")
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

def get_market_index_data(stock_code: str, start_date: str, end_date: str, kline_days: int = 30) -> dict:
    """
    根据股票代码获取对应的大盘指数日K线数据，支持多个指数（主板指数+板块指数）。

    :param stock_code: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 获取的K线天数，默认30天
    :return: dict, {指数名称: (pd.DataFrame, 指数全称)} - 多个指数的数据字典
    """
    print(f"正在获取股票 {stock_code} 对应的大盘指数数据...")

    # 根据股票代码确定需要获取的指数列表
    index_configs = {}

    if stock_code.startswith('60'):
        # 上海主板：上证指数
        index_configs = {
            "上证指数": ("000001", "上证指数")
        }
        print("识别为上海主板股票，使用上证指数")
    elif stock_code.startswith('688'):
        # 科创板：上证指数 + 科创50
        index_configs = {
            "上证指数": ("000001", "上证指数"),
            "科创50": ("000688", "科创50指数")
        }
        print("识别为科创板股票，使用上证指数和科创50指数")
    elif stock_code.startswith('00'):
        # 深圳主板：深圳成指
        index_configs = {
            "深圳成指": ("399001", "深圳成指")
        }
        print("识别为深圳主板股票，使用深圳成指")
    elif stock_code.startswith('30'):
        # 创业板：深圳成指 + 创业板指数
        index_configs = {
            "深圳成指": ("399001", "深圳成指"),
            "创业板指数": ("399006", "创业板指数")
        }
        print("识别为创业板股票，使用深圳成指和创业板指数")
    elif stock_code.startswith(('83', '43', '87')):
        # 北交所：北证50
        index_configs = {
            "北证50": ("899050", "北证50指数")
        }
        print("识别为北交所股票，使用北证50指数")
    else:
        # 默认使用上证指数
        index_configs = {
            "上证指数": ("000001", "上证指数")
        }
        print("无法识别市场类型，默认使用上证指数")

    result_data = {}

    for short_name, (index_code, full_name) in index_configs.items():
        try:
            # 特殊处理上证指数，避免与平安银行代码冲突
            if index_code == "000001":
                # 使用指数专用API获取上证指数数据
                index_data = ak.stock_zh_index_daily(symbol="sh000001")
                # 获取最近 kline_days 天的上证指数数据
                index_data = index_data.tail(kline_days)
                # 将英文列名转换为中文列名，与其他指数保持一致
                index_data = index_data.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量'
                })
                print(f"✅ 使用指数专用API获取 {full_name} 数据成功")
            else:
                # 其他指数使用原有的方法
                index_data = ak.stock_zh_a_hist(symbol=index_code, period="daily",
                                              start_date=start_date, end_date=end_date, adjust="")

            if index_data.empty:
                print(f"❌ 获取 {full_name} 数据失败，跳过")
                continue

            print(f"✅ {full_name} 数据获取成功，共 {len(index_data)} 条记录")
            if not index_data.empty:
                print(f"   时间范围: {index_data['日期'].min()} 到 {index_data['日期'].max()}")

            result_data[short_name] = (index_data, full_name)

        except Exception as e:
            print(f"❌ 获取 {full_name} 数据时出错: {e}")
            continue

    if not result_data:
        print("❌ 未能获取任何指数数据")
        return {"未知指数": (pd.DataFrame(), "未知指数")}

    return result_data

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

def get_and_save_stock_data(stock: str, start_date: str, end_date: str, kline_days: int) -> tuple:
    """
    获取股票的分时成交数据、日K线数据、大盘指数数据和行业板块数据，并保存到CSV文件中。

    :param stock: str, 股票代码，例如 '300680'
    :param start_date: str, 分时数据的起始日期，格式 'YYYYMMDD'
    :param end_date: str, 分时数据的结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 日K线数据的天数，例如 60
    :return: tuple, (file_paths, stock_name) 文件路径字典和股票名称，失败返回 (None, None)
    """
    try:
        # 分时数据使用传递的日期范围（来自daysBeforeToday）
        df_intraday, stock_name = get_intraday_data(stock=stock, start_date=start_date, end_date=end_date)

        # K线数据使用基于kline_days计算的日期范围
        kline_start_date, kline_end_date = get_kline_date_range(kline_days)
        df_daily = get_daily_kline_data(symbol=stock, end_date=kline_end_date, kline_days=kline_days)

        # 大盘指数数据使用K线数据的日期范围
        market_index_data = get_market_index_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date, kline_days=kline_days)

        # 行业板块数据使用K线数据的日期范围
        df_industry, industry_sector_name = get_industry_sector_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 生成三位随机数，避免文件名冲突
        random_suffix = str(random.randint(0, 999)).zfill(3)
        base_filename = f"{stock}_{stock_name}_{start_date}_to_{end_date}_{random_suffix}"

        # 确保data_output目录存在
        output_dir = Path('data_output')
        output_dir.mkdir(exist_ok=True)

        # 保存到CSV文件 - 仅创建合并的完整文件
        file_paths = {}

        # 创建一个合并的CSV文件用于上传到通义千问（包含所有数据）
        main_file = str(output_dir / f"{base_filename}_complete.csv")
        with open(main_file, 'w', encoding='utf-8-sig', newline='') as f:
            # 写入标题信息
            f.write(f"股票代码: {stock}\n")
            f.write(f"股票名称: {stock_name}\n")
            f.write(f"所属板块: {industry_sector_name}\n")
            f.write(f"分时数据时间范围: {start_date} 到 {end_date}\n")
            f.write(f"K线数据时间范围: {kline_start_date} 到 {kline_end_date}\n\n")

            # 写入分时数据
            f.write("=== 分时成交数据 ===\n")
            df_intraday.to_csv(f, index=False)
            f.write("\n\n")

            # 写入日K线数据
            f.write("=== 日K线数据 ===\n")
            df_daily.to_csv(f, index=False)
            f.write("\n\n")

            # 写入大盘指数数据
            if market_index_data:
                for index_short_name, (df_market, market_index_name) in market_index_data.items():
                    if not df_market.empty:
                        f.write(f"=== {market_index_name}数据 ===\n")
                        df_market.to_csv(f, index=False)
                        f.write("\n\n")

            # 写入行业板块数据
            if not df_industry.empty:
                f.write("=== 行业板块数据 ===\n")
                df_industry.to_csv(f, index=False)
                f.write("\n\n")

        file_paths['complete'] = main_file
        print(f"✅ 合并数据文件已保存到 {main_file} (用于上传)")

        return file_paths, stock_name

    except Exception as e:
        print(f"❌ 处理股票 {stock} 时出错: {e}")
        return None, None

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

    print(f"📄 数据已保存到文件: {filepath}")
    return filepath

def chat_with_qwen(file_id: str, question: Any, api_key: str, intraday_days: int = 7, kline_days: int = 30, stock_code: str = "") -> str:
    """
    使用通义千问的 API 进行聊天，支持字典或字符串类型的 question。

    :param file_id: str, 文件 ID
    :param question: Any, 用户提示或问题，可以是字符串或字典
    :param api_key: str, API 密钥
    :param intraday_days: int, 分时数据的天数，默认7天
    :param kline_days: int, K线数据的天数，默认30天
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

        # 使用传入的参数，优先使用传入的参数，其次从question中获取
        intraday_days = intraday_days
        kline_days = kline_days

        # 获取当前系统时间并格式化
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime('%Y年%m月%d日')
        current_weekday = current_datetime.strftime('%A')  # 英文星期
        # 转换为中文星期
        weekday_map = {
            'Monday': '星期一', 'Tuesday': '星期二', 'Wednesday': '星期三',
            'Thursday': '星期四', 'Friday': '星期五', 'Saturday': '星期六', 'Sunday': '星期日'
        }
        current_weekday_cn = weekday_map.get(current_weekday, current_weekday)

        # 在提示词开头明确声明当前时间
        time_declaration = f"""⚠️ 重要时间声明：当前系统时间为 {current_date_str} {current_weekday_cn}。请在整个分析报告中使用此时间作为基准，确保所有日期相关的内容都基于此当前时间进行计算和描述。

"""

        # 构造用户消息内容 - 增强的分析描述
        user_content = time_declaration + (
            f"{analysis_request.get('analysis_purpose', {}).get('description', '')}\n\n"
            f"📊 数据时间范围说明：\n"
            f"- 分时成交数据：包含最近 {intraday_days} 个交易日的日内分时数据，用于分析短期资金流向和主力行为模式\n"
            f"- 日K线数据：包含最近 {kline_days} 个交易日的K线数据，用于识别中长期趋势和关键技术位\n"
            f"- 市场指数数据：对应股票所属市场的指数（可能包含多个指数，根据板块自动匹配），时间范围与K线数据一致，用于评估系统性风险和市场beta系数\n"
            f"- 行业板块数据：股票所属行业的板块指数，时间范围与K线数据一致，用于分析行业相对强度和轮动机会\n\n"
            f"📋 数据结构说明：\n"
            f"{analysis_request.get('data_description', {}).get('data_structure', '')}\n\n"
            f"🔍 数据工作表详细说明：\n"
            f"• 分时成交数据段: {analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('fields', []))}\n\n"
            f"• 日K线数据段: {analysis_request.get('data_description', {}).get('daily_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('daily_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('daily_data_section', {}).get('fields', []))}\n\n"
            f"• 市场指数数据段: {analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('section_markers', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('fields', []))}\n\n"
            f"• 行业板块数据段: {analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('fields', []))}\n\n"
            f"📈 多日数据分析要求：\n"
            f"请对提供的多日分时数据进行逐日深度分析（按时间顺序由远及近）\n"
            f"🔬 分析步骤（应用于每一天的分时数据分析结果输出）：\n"
        )

        # 添加分析步骤 - 针对多日数据进行逐日分析
        for step in analysis_request.get('analysis_steps', []):
            user_content += f"步骤 {step.get('step', '')}: {step.get('description', '')}\n"

        # 使用配置化的输出要求格式化
        output_requirements = analysis_request.get('output_requirements', [])
        user_content += format_output_requirements(output_requirements)

        messages.append({'role': 'user', 'content': user_content})
    elif isinstance(question, str):
        # 如果 question 是字符串，直接使用（保持后向兼容性）
        messages.append({'role': 'user', 'content': question})
    else:
        raise ValueError("question 参数必须是字符串或字典类型")

    print(messages)

    # 保存完整的对话内容到本地文件
    if stock_code:
        # 将messages格式化为可读的文本
        full_message_content = ""
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            full_message_content += f"=== {role.upper()} ===\n{content}\n\n"

        # 保存到文件
        full_message_file = save_data_to_file(full_message_content, stock_code, "_full_message")
        print(f"📄 完整消息已保存，您可以查看: {full_message_file}")

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

def format_output_requirements(output_requirements: List[Dict[str, Any]]) -> str:
    """
    根据output_requirements配置格式化输出要求。

    :param output_requirements: 输出要求列表
    :return: 格式化的输出要求字符串
    """
    formatted_content = "\n📋 输出要求（基于多日数据分析）：\n"

    for req in output_requirements:
        section_num = req.get('section', '')
        title = req.get('title', '')
        description = req.get('description', '')

        # 添加section标题和描述
        formatted_content += f"{section_num}. {title}: {description}\n"

        # 处理output_format
        output_format = req.get('output_format', {})
        if output_format:
            formatted_content += "\n输出格式要求：\n"

            # 通用处理所有output_format中的键值对
            for key, value in output_format.items():
                formatted_content += f"{key}: {value}\n"

    return formatted_content

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

def get_intraday_date_range(days_before_today: int) -> tuple:
    """
    根据days_before_today计算分时数据的日期范围，使用交易日而非自然日。

    :param days_before_today: int, 分时数据往前追溯的交易日数量
    :return: tuple, (start_date, end_date) 格式为YYYYMMDD
    """
    end_date = date.today().strftime('%Y%m%d')

    # 计算分时数据的开始日期（往前days_before_today个交易日）
    calendar = ak.tool_trade_date_hist_sina()
    calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
    end_dt = pd.to_datetime(end_date)

    # 获取所有交易日 <= end_dt，降序排序，取前 days_before_today 个（最新的）
    trading_dates_filtered = calendar[calendar['trade_date'] <= end_dt]['trade_date'].sort_values(ascending=False).head(days_before_today)

    if len(trading_dates_filtered) < days_before_today:
        print(f"⚠️ 警告: 仅找到 {len(trading_dates_filtered)} 个交易日，可用交易日不足 {days_before_today} 天")

    start_dt_intraday = trading_dates_filtered.iloc[-1]  # 最早的日期在最后面，因为是降序
    start_date = start_dt_intraday.strftime('%Y%m%d')

    return start_date, end_date

def analyze_stocks(config_file: str = 'anylizeconfig.json', keys_file: str = 'keys.json', command_line_stocks: List[str] = None):
    """分析股票的主函数

    :param config_file: 配置文件路径
    :param keys_file: 密钥文件路径
    :param command_line_stocks: 命令行传入的股票代码列表，如果提供则优先使用，否则使用配置文件
    """
    # 1. 读取配置
    config = load_config(config_file, keys_file)

    # 如果提供了命令行股票参数，使用命令行参数；否则使用配置文件
    if command_line_stocks:
        stocks = command_line_stocks
        print(f"💴 使用命令行指定的股票: {', '.join(stocks)}")
    else:
        stocks = select_stocks(config)
        print(f"💴 使用配置文件指定的股票: {', '.join(stocks)}")

    # 分时数据使用intraday_days计算日期范围（基于交易日）
    intraday_days = config['intraday_days']
    intraday_start_date, intraday_end_date = get_intraday_date_range(intraday_days)
    print(f"📅 分时数据日期范围: {intraday_start_date} 到 {intraday_end_date} (共{intraday_days}个交易日)")

    # K线数据使用kline_days计算日期范围
    kline_days = config.get('kline_days', 60)  # 默认60天
    kline_start_date, kline_end_date = get_kline_date_range(kline_days)
    print(f"📅 K线数据日期范围: {kline_start_date} 到 {kline_end_date} (共{kline_days}个交易日)")

    # 智能选择prompt配置
    prompt_template = select_prompt_by_model(config)
    print(f"🎯 使用文件处理模型专用prompt (qwen-long)")

    api_key = config['api_key']  # 从 keys.json 读取 API 密钥
    email_sender = config['email_sender']  # 从 keys.json 读取发件人邮箱地址
    email_password = config['email_password']  # 从 keys.json 读取发件人邮箱密码
    email_receivers = config['email_receivers']  # 从 keys.json 读取收件人邮箱地址

    # 2. 循环处理每只股票
    total = len(stocks)
    for index, stock in enumerate(stocks):
        print(f"正在处理股票: {stock} ({index+1}/{total})")
        file_path = None  # 初始化文件路径
        try:
            # 获取数据并保存到CSV文件
            result = get_and_save_stock_data(stock=stock, start_date=intraday_start_date, end_date=intraday_end_date, kline_days=kline_days)
            if result[0] is None:
                print(f"股票 {stock} 获取数据失败，跳过")
                continue
            file_paths, stock_name = result

            # 使用合并的完整文件进行上传
            main_file_path = file_paths['complete']
            file_id = upload_file(file_path=main_file_path, api_key=api_key)
            if file_id is None:
                print(f"股票 {stock} 的文件上传失败，跳过")
                continue

            # 与通义千问模型交互，直接传递字典类型的 prompt_template 和配置参数
            response = chat_with_qwen(
                file_id=file_id,
                question=prompt_template,
                api_key=api_key,
                intraday_days=config['intraday_days'],
                kline_days=config['kline_days'],
                stock_code=stock
            )
            if response:
                print(f"股票 {stock} 的分析结果: {response}\n")

                # 保存分析结果到MD文件
                current_time = datetime.now()
                date_str = current_time.strftime('%Y%m%d')
                time_str = current_time.strftime('%H%M%S')

                # 确保data_output文件夹存在
                output_dir = Path('data_output')
                output_dir.mkdir(exist_ok=True)

                # 清理股票名称中的特殊字符
                clean_stock_name = stock_name.replace('(', '').replace(')', '').replace(' ', '_')

                md_filename = f"{stock}_{clean_stock_name}_{intraday_start_date}_to_{intraday_end_date}_{date_str}_{time_str}.md"
                md_filepath = output_dir / md_filename

                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {stock_name}（{stock}）股票分析报告\n\n")
                    f.write(f"**分析时间**: {current_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
                    f.write(f"---\n\n")
                    f.write(response)

                print(f"✅ 分析结果已保存到: {md_filepath}")

                # 将MD文件转换为HTML
                html_filename = md_filename.replace('.md', '.html')
                html_filepath = output_dir / html_filename
                converter = MarkdownToHTMLConverter()
                if converter.convert_file(str(md_filepath), str(html_filepath)):
                    print(f"✅ HTML文件已生成: {html_filepath}\n")
                else:
                    print(f"❌ HTML转换失败: {md_filepath}\n")
                    continue
            else:
                print(f"股票 {stock} 的聊天请求失败！\n")

            # 发送邮件并根据结果决定是否删除文件
            print(f"股票 {stock} 准备发送邮件 \n")
            send_email(
                subject=f"股票 {stock} 分析结果",
                body=f"股票 {stock_name}（{stock}）的分析报告已生成，请查看附件中的HTML文件。",
                receivers=email_receivers,
                sender=email_sender,
                password=email_password,
                attachment_path=str(html_filepath)  # 发送HTML文件作为附件
            )

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

        if index < total - 1:
            for i in range(60):  # 等待 300 秒，避免请求过于频繁
                print(".", end="", flush=True)
                t.sleep(1)  # 避免请求过于频繁

# 运行程序
if __name__ == "__main__":
    # 检查命令行参数，如果有参数（除了脚本名），则将其作为股票代码使用
    if len(sys.argv) > 1:
        # sys.argv[0] 是脚本名，后面的参数都是股票代码
        command_line_stocks = sys.argv[1:]
        print(f"🔧 检测到命令行参数，使用指定的股票代码: {', '.join(command_line_stocks)}")
        analyze_stocks('anylizeconfig.json', 'keys.json', command_line_stocks)
    else:
        print("🔧 未检测到命令行参数，使用配置文件中的股票设置")
        analyze_stocks('anylizeconfig.json', 'keys.json')
