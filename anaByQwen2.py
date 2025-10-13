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
import re
from hourly_volume_analysis import analyze_csv_file
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# ===== 配置常量 =====
MAX_RETRIES = 3
RETRY_DELAY = 20  # 秒
API_TIMEOUT = 180  # 秒
OUTPUT_BASE_DIR = 'data_output'
SMTP_SERVER = 'applesmtp.163.com'
SMTP_PORT = 465
RANDOM_WAIT_MIN = 1
RANDOM_WAIT_MAX = 20

# ===== 配置管理函数 =====
def get_stock_output_dir(stock: str) -> Path:
    """获取股票专属输出目录"""
    return Path(OUTPUT_BASE_DIR) / stock

def get_intraday_cache_path(stock: str, date: str) -> Path:
    """获取分时数据缓存文件路径"""
    return get_stock_output_dir(stock) / f"{stock}_{date}_intraday.csv"

# ===== 通用API调用包装器 =====
def fetch_with_timeout(api_func, *args, **kwargs):
    """
    通用的API调用包装器，带超时和重试机制
    
    :param api_func: API函数
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 获取到的数据
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(api_func, *args, **kwargs)
        try:
            return future.result(timeout=API_TIMEOUT)
        except FutureTimeoutError:
            raise TimeoutError("API call timed out")

def fetch_with_retry(api_func, *args, **kwargs):
    """
    带重试机制的API调用包装器
    
    :param api_func: API函数
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 获取到的数据
    """
    max_retries = MAX_RETRIES
    retry_delay = RETRY_DELAY
    
    for attempt in range(max_retries):
        try:
            print(f"正在调用API... (尝试 {attempt + 1}/{max_retries})")
            result = fetch_with_timeout(api_func, *args, **kwargs)
            print("API调用成功")
            return result
        except Exception as e:
            print(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"将在 {retry_delay} 秒后重试...")
                t.sleep(retry_delay)
            else:
                raise Exception(f"API调用失败，已重试 {max_retries} 次: {str(e)}")

def extract_investment_rating(md_file_path: str) -> str:
    """
    从MD文件中提取投资评级信息

    :param md_file_path: str, MD文件路径
    :return: str, 提取到的投资评级，如果未找到则返回空字符串
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式查找投资评级行
        # 匹配类似：**投资评级** | ✅ **强烈推荐（Strong Buy）** |
        pattern = r'\*\*投资评级\*\*\s*\|\s*(.+?)\s*\|'
        match = re.search(pattern, content)

        if match:
            rating_text = match.group(1).strip()
            # 清理markdown格式，提取实际评级内容
            # 移除markdown的粗体标记和表情符号
            clean_rating = re.sub(r'\*\*', '', rating_text)  # 移除粗体标记
            clean_rating = re.sub(r'[✅❌🟢🟡🔴]', '', clean_rating)  # 移除表情符号
            clean_rating = clean_rating.strip()
            return clean_rating
        else:
            print(f"⚠️ 在文件 {md_file_path} 中未找到投资评级信息")
            return ""

    except Exception as e:
        print(f"❌ 提取投资评级时出错: {e}")
        return ""

def send_email(subject: str, body: str, receivers: List[str], sender: str, password: str, attachment_paths: List[str] = None) -> bool:
    """发送邮件并返回是否成功，如果提供attachment_paths则发送多个附件"""
    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = sender  # 发件人
    msg['To'] = ', '.join(receivers)  # 将收件人列表转换为逗号分隔的字符串
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 如果提供了附件路径列表，添加所有附件
    if attachment_paths:
        for attachment_path in attachment_paths:
            if attachment_path and os.path.exists(attachment_path):
                try:
                    with open(attachment_path, 'rb') as f:
                        # 根据文件扩展名确定MIME类型
                        file_ext = os.path.splitext(attachment_path)[1].lower()
                        if file_ext == '.html':
                            attachment = MIMEApplication(f.read(), _subtype='html')
                        elif file_ext == '.md':
                            attachment = MIMEApplication(f.read(), _subtype='text')
                        else:
                            attachment = MIMEApplication(f.read())
                        
                        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                        msg.attach(attachment)
                    print(f"已添加附件: {attachment_path}")
                except Exception as e:
                    print(f"添加附件失败: {attachment_path}, 错误: {e}")
                    continue  # 继续添加其他附件
            else:
                print(f"附件文件不存在: {attachment_path}")

    # SMTP服务器设置
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT

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
        if attachment_paths:
            for attachment_path in attachment_paths:
                if attachment_path and os.path.exists(attachment_path):
                    #os.remove(attachment_path)
                    print(f"本地文件 {attachment_path} 已删除（为方便调试，目前需手动删除）")
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
    stock_name = None
    output_dir = get_stock_output_dir(stock)
    output_dir.mkdir(parents=True, exist_ok=True)


    for date in trading_dates:
        local_path = get_intraday_cache_path(stock, date)
        max_retries = MAX_RETRIES  # 最大重试次数
        loaded_from_local = False

        if local_path.exists():
            try:
                daily_data = pd.read_csv(local_path, encoding='utf-8-sig')
                # Handle potential timezone in ticktime
                daily_data['ticktime'] = pd.to_datetime(daily_data['ticktime'], utc=True).dt.tz_localize(None)
                print(f"从本地加载 {minute_code} 在 {date} 的数据")
                loaded_from_local = True
            except Exception as e:
                print(f"加载本地文件 {local_path} 失败: {e}，将从接口重新获取")

        if not loaded_from_local:
            try:
                daily_data = fetch_with_retry(ak.stock_intraday_sina, symbol=minute_code, date=date)
                if not daily_data.empty:
                    daily_data['ticktime'] = pd.to_datetime(date + ' ' + daily_data['ticktime'])
                    daily_data.to_csv(local_path, index=False, encoding='utf-8-sig')
                    print(f"成功获取并保存 {minute_code} 在 {date} 的数据到 {local_path}")
                    # 如果不是最后一个交易日，等待随机时间
                    if date != trading_dates[-1]:
                        print("稍等一下...")
                        for _ in range(random.randint(RANDOM_WAIT_MIN, RANDOM_WAIT_MAX)):
                            print("+", end="", flush=True)
                            t.sleep(1)
                        print()  # 换行
            except Exception as e:
                print(f"获取股票 {minute_code} 在 {date} 的数据失败: {e}")
                continue

        if 'daily_data' in locals() and not daily_data.empty:
            # 获取 stock_name，如果尚未设置
            if stock_name is None and 'name' in daily_data.columns:
                stock_name = daily_data['name'][0]
            stock_data_list.append(daily_data)

    if not stock_data_list:
        raise ValueError(f"无法获取 {minute_code} 的逐笔成交数据")

    # 如果 stock_name 仍为 None（所有数据从本地加载，且本地无 name 列），则从接口获取一个日期的 name
    if stock_name is None:
        try:
            # 使用最后一个交易日获取 name
            sample_data = ak.stock_intraday_sina(symbol=minute_code, date=trading_dates[-1])
            if not sample_data.empty:
                stock_name = sample_data['name'][0]
                print(f"从接口获取股票名称: {stock_name}")
        except Exception as e:
            print(f"无法获取股票名称: {e}")
            stock_name = "未知"  # 默认值

    all_data = pd.concat(stock_data_list)
    all_data = all_data.sort_values('ticktime').reset_index(drop=True)
    all_data = all_data.drop(columns=['symbol', 'name'], errors='ignore')
    return all_data, stock_name

def get_daily_kline_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定股票在指定日期范围内的日K线数据。

    :param symbol: str, 股票代码，例如 '300680'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
    :return: pd.DataFrame, 日K线数据
    """
    # 获取日K线数据，带重试机制
    try:
        stock_data = fetch_with_retry(ak.stock_zh_a_hist, symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
        if stock_data is not None and not stock_data.empty:
            print(f"成功获取股票 {symbol} 的K线数据，共 {len(stock_data)} 条记录")
            return stock_data
        else:
            print(f"警告：股票 {symbol} 的K线数据为空")
            return pd.DataFrame()
    except Exception as e:
        raise Exception(f"获取股票 {symbol} 的K线数据失败: {str(e)}")

def _fetch_index_data_with_retry(api_func, *args, **kwargs):
    """
    带重试机制的指数数据获取函数

    :param api_func: API函数
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 获取到的数据
    """
    return fetch_with_retry(api_func, *args, **kwargs)

def get_market_index_data(stock_code: str, start_date: str, end_date: str) -> dict:
    """
    根据股票代码获取对应的大盘指数日K线数据，支持多个指数（主板指数+板块指数）。

    :param stock_code: str, 股票代码，例如 '600000'
    :param start_date: str, 起始日期，格式 'YYYYMMDD'
    :param end_date: str, 结束日期，格式 'YYYYMMDD'
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
                # 使用指数专用API获取上证指数数据（带重试机制）
                index_data = _fetch_index_data_with_retry(ak.stock_zh_index_daily, symbol="sh000001")
                # 筛选指定日期范围的数据
                index_data['date'] = pd.to_datetime(index_data['date'])
                index_data = index_data[(index_data['date'] >= pd.to_datetime(start_date)) & (index_data['date'] <= pd.to_datetime(end_date))]
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
                # 其他指数使用原有的方法（带重试机制）
                index_data = _fetch_index_data_with_retry(
                    ak.stock_zh_a_hist,
                    symbol=index_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )

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

    def fetch_with_timeout(func, *args, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=API_TIMEOUT)
            except FutureTimeoutError:
                raise TimeoutError("API call timed out")

    try:
        # 步骤1: 获取股票基本信息（带重试机制）
        stock_info_df = _fetch_index_data_with_retry(fetch_with_timeout, ak.stock_individual_info_em, symbol=stock_code)

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

        # 步骤2: 获取行业板块数据（带重试机制）
        print(f"正在获取 '{industry_name}' 行业板块数据...")
        industry_data = _fetch_index_data_with_retry(
            fetch_with_timeout,
            ak.stock_board_industry_hist_em,
            symbol=industry_name,
            start_date=start_date,
            end_date=end_date
        )

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

# ===== 数据获取模块 =====
def fetch_all_stock_data(stock: str, start_date: str, end_date: str, kline_days: int) -> tuple:
    """
    获取股票的所有相关数据
    
    :param stock: str, 股票代码
    :param start_date: str, 分时数据的起始日期
    :param end_date: str, 分时数据的结束日期
    :param kline_days: int, 日K线数据的天数
    :return: tuple, (df_intraday, stock_name, df_daily, market_index_data, df_industry, industry_sector_name)
    """
    # 分时数据使用传递的日期范围
    df_intraday, stock_name = get_intraday_data(stock=stock, start_date=start_date, end_date=end_date)

    # K线数据使用基于kline_days计算的日期范围
    kline_start_date, kline_end_date = get_kline_date_range(kline_days, end_date)
    df_daily = get_daily_kline_data(symbol=stock, start_date=kline_start_date, end_date=kline_end_date)

    # 大盘指数数据使用K线数据的日期范围
    market_index_data = get_market_index_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

    # 行业板块数据使用K线数据的日期范围
    df_industry, industry_sector_name = get_industry_sector_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)
    
    return df_intraday, stock_name, df_daily, market_index_data, df_industry, industry_sector_name

def create_complete_csv_file(stock: str, stock_name: str, start_date: str, end_date: str, 
                           kline_start_date: str, kline_end_date: str, industry_sector_name: str,
                           df_intraday: pd.DataFrame, df_daily: pd.DataFrame, 
                           market_index_data: dict, df_industry: pd.DataFrame, 
                           hourly_start_date: str = None, hourly_end_date: str = None) -> str:
    """
    创建包含所有数据的完整CSV文件
    
    :param stock: str, 股票代码
    :param stock_name: str, 股票名称
    :param start_date: str, 分时数据起始日期
    :param end_date: str, 分时数据结束日期
    :param kline_start_date: str, K线数据起始日期
    :param kline_end_date: str, K线数据结束日期
    :param industry_sector_name: str, 行业板块名称
    :param df_intraday: pd.DataFrame, 分时数据
    :param df_daily: pd.DataFrame, 日K线数据
    :param market_index_data: dict, 大盘指数数据
    :param df_industry: pd.DataFrame, 行业板块数据
    :return: str, 文件路径
    """
    # 生成三位随机数，避免文件名冲突
    random_suffix = str(random.randint(0, 999)).zfill(3)
    base_filename = f"{stock}_{stock_name}_{start_date}_to_{end_date}_{random_suffix}"
    
    # 确保输出目录存在
    output_dir = get_stock_output_dir(stock)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建完整CSV文件
    main_file = str(output_dir / f"{base_filename}_complete.csv")
    with open(main_file, 'w', encoding='utf-8-sig', newline='') as f:
        # 写入标题信息
        f.write(f"股票代码: {stock}\n")
        f.write(f"股票名称: {stock_name}\n")
        f.write(f"所属板块: {industry_sector_name}\n")
        f.write(f"分时数据时间范围: {start_date} 到 {end_date}\n")
        f.write(f"K线数据时间范围: {kline_start_date} 到 {kline_end_date}\n")
        # 使用小时量能专用时间范围，如果没有提供则使用分时数据时间范围
        hourly_range_start = hourly_start_date if hourly_start_date else start_date
        hourly_range_end = hourly_end_date if hourly_end_date else end_date
        f.write(f"小时量能数据时间范围: {hourly_range_start} 到 {hourly_range_end}\n\n")

        # 写入分时数据
        f.write("=== 分时成交数据 ===\n")
        df_intraday.to_csv(f, index=False)
        f.write("\n\n")

        # 写入日K线数据
        f.write("=== 日K线数据 ===\n")
        df_daily.to_csv(f, index=False)
        f.write("\n\n")

        # 写入大盘指数数据
        f.write("=== 大盘指数数据 ===\n")
        for index_name, (index_df, index_full_name) in market_index_data.items():
            f.write(f"--- {index_full_name} ---\n")
            index_df.to_csv(f, index=False)
            f.write("\n")

        # 写入行业板块数据
        f.write("=== 行业板块数据 ===\n")
        df_industry.to_csv(f, index=False)
        f.write("\n\n")

    return main_file

def get_and_save_stock_data(stock: str, start_date: str, end_date: str, kline_days: int, hourly_start_date: str = None, hourly_end_date: str = None) -> tuple:
    """
    获取股票的分时成交数据、日K线数据、大盘指数数据和行业板块数据，并保存到CSV文件中。

    :param stock: str, 股票代码，例如 '300680'
    :param start_date: str, 分时数据的起始日期，格式 'YYYYMMDD'
    :param end_date: str, 分时数据的结束日期，格式 'YYYYMMDD'
    :param kline_days: int, 日K线数据的天数，例如 60
    :param hourly_start_date: str, 小时量能分析的起始日期，格式 'YYYYMMDD'，可选
    :param hourly_end_date: str, 小时量能分析的结束日期，格式 'YYYYMMDD'，可选
    :return: tuple, (file_paths, stock_name) 文件路径字典和股票名称，失败返回 (None, None)
    """
    try:
        # 分时数据使用传递的日期范围（来自daysBeforeToday）
        df_intraday, stock_name = get_intraday_data(stock=stock, start_date=start_date, end_date=end_date)

        # K线数据使用基于kline_days计算的日期范围，使用与分时数据相同的结束日期
        kline_start_date, kline_end_date = get_kline_date_range(kline_days, end_date)
        df_daily = get_daily_kline_data(symbol=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 大盘指数数据使用K线数据的日期范围
        market_index_data = get_market_index_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 行业板块数据使用K线数据的日期范围
        df_industry, industry_sector_name = get_industry_sector_data(stock_code=stock, start_date=kline_start_date, end_date=kline_end_date)

        # 创建完整CSV文件
        main_file = create_complete_csv_file(
            stock, stock_name, start_date, end_date, kline_start_date, kline_end_date,
            industry_sector_name, df_intraday, df_daily, market_index_data, df_industry,
            hourly_start_date, hourly_end_date
        )
        
        file_paths = {'complete': main_file}
        print(f"✅ 数据已保存到: {main_file}")

        # 调用小时量能分析并插入结果
        print(f"🔍 开始对 {stock} 进行小时量能分析...")
        try:
            # 如果提供了小时量能专用日期范围，则使用专用范围进行分析
            if hourly_start_date and hourly_end_date:
                print(f"📊 使用小时量能专用日期范围: {hourly_start_date} 到 {hourly_end_date}")
                # 获取小时量能专用的分时数据
                df_hourly_intraday, _ = get_intraday_data(stock=stock, start_date=hourly_start_date, end_date=hourly_end_date)
                # 创建临时CSV文件用于小时量能分析
                output_dir = get_stock_output_dir(stock)
                base_filename = f"{stock}_{stock_name}_{start_date}_to_{end_date}_{str(random.randint(0, 999)).zfill(3)}"
                temp_hourly_file = str(output_dir / f"{base_filename}_hourly_temp.csv")
                with open(temp_hourly_file, 'w', encoding='utf-8-sig', newline='') as f_temp:
                    f_temp.write(f"股票代码: {stock}\n")
                    f_temp.write(f"股票名称: {stock_name}\n")
                    f_temp.write(f"小时量能数据时间范围: {hourly_start_date} 到 {hourly_end_date}\n\n")
                    f_temp.write("=== 分时成交数据 ===\n")
                    df_hourly_intraday.to_csv(f_temp, index=False)
                    f_temp.write("\n\n")
                    f_temp.write("=== 日K线数据 ===\n")  # 添加结束标记
                hourly_analysis_result, hourly_md_path = analyze_csv_file(temp_hourly_file)
                # 删除临时文件
                os.remove(temp_hourly_file)
            else:
                # 使用原有的完整文件进行分析（向后兼容）
                hourly_analysis_result, hourly_md_path = analyze_csv_file(main_file)
            if hourly_analysis_result is not None and hourly_md_path is not None:
                print(f"✅ 小时量能分析完成")
                # 删除MD文件，因为数据已包含在CSV中
                try:
                    os.remove(hourly_md_path)
                    print(f"🗑️ 已删除临时MD文件: {hourly_md_path}")
                except Exception as e:
                    print(f"⚠️ 删除MD文件失败: {e}")
                
                # 将小时量能分析数据追加到主CSV文件
                with open(main_file, 'a', encoding='utf-8-sig', newline='') as f_append:
                    f_append.write("=== 小时量能分析数据 ===\n")
                    f_append.write("日期,时间段,总笔数,成交量,总量能,U占比,D占比,E占比,U/D,成交量占比\n")
                    
                    for date in sorted(hourly_analysis_result.keys()):
                        period_stats = hourly_analysis_result[date]
                        daily_stats = []
                        
                        # 计算当天的成交量总和（包含所有时间段，包括09:25）
                        daily_total_volume_count = 0
                        for period_name, stats in period_stats.items():
                            daily_total_volume_count += stats['total_volume_count']
                        
                        # 写入每个时间段
                        for period_name, stats in period_stats.items():
                            ud_display = stats['ud_ratio'] if stats['ud_ratio'] != 'NA' else 'NA'
                            # 计算成交量占比
                            if daily_total_volume_count > 0:
                                volume_ratio = stats['total_volume_count'] / daily_total_volume_count
                            else:
                                volume_ratio = 0
                            f_append.write(f"{date},{stats['period_name']},{stats['transaction_count']},{stats['total_volume_count']:.0f},{stats['total_volume']:.0f},{stats['u_ratio']:.4f},{stats['d_ratio']:.4f},{stats['e_ratio']:.4f},{ud_display},{volume_ratio:.4f}\n")
                            daily_stats.append(stats)
                        
                        # 计算并写入每天汇总
                        if daily_stats:
                            # 排除09:25时间段，只计算09:30-15:00的汇总数据
                            filtered_stats = [s for s in daily_stats if s.get('period_name') != '09:25']
                            
                            if filtered_stats:
                                total_transactions = sum(s['transaction_count'] for s in filtered_stats)
                                total_volume = sum(s['total_volume'] for s in filtered_stats)
                                total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                                total_u_volume = sum(s['u_volume'] for s in filtered_stats)
                                total_d_volume = sum(s['d_volume'] for s in filtered_stats)
                                total_e_volume = sum(s['e_volume'] for s in filtered_stats)
                                
                                u_ratio = total_u_volume / total_volume if total_volume > 0 else 0
                                d_ratio = total_d_volume / total_volume if total_volume > 0 else 0
                                e_ratio = total_e_volume / total_volume if total_volume > 0 else 0
                                ud_ratio = total_u_volume / total_d_volume if total_d_volume > 0 else (total_u_volume if total_u_volume > 0 else 0)
                                
                                # 计算09:30-15:00的成交量占比（排除09:25）
                                filtered_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                                filtered_volume_ratio = filtered_volume_count / daily_total_volume_count if daily_total_volume_count > 0 else 0
                                f_append.write(f"{date},09:30-15:00,{total_transactions},{total_volume_count:.0f},{total_volume:.0f},{u_ratio:.4f},{d_ratio:.4f},{e_ratio:.4f},{ud_ratio:.2f},{filtered_volume_ratio:.4f}\n")
                    
                    f_append.write("\n\n")
            else:
                print(f"⚠️ 股票 {stock} 的小时量能分析失败")
        except Exception as e:
            print(f"❌ 股票 {stock} 的小时量能分析出错: {e}")

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
    data_dir = f"data_output/{stock_code}"
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

def chat_with_qwen(file_id: str, question: Any, api_key: str, intraday_days: int = 7, kline_days: int = 30, stock_code: str = "", specified_date: str = None, hourly_volume_days: int = None) -> str:
    """
    使用通义千问的 API 进行聊天，支持字典或字符串类型的 question。

    :param file_id: str, 文件 ID
    :param question: Any, 用户提示或问题，可以是字符串或字典
    :param api_key: str, API 密钥
    :param intraday_days: int, 分时数据的天数，默认7天
    :param kline_days: int, K线数据的天数，默认30天
    :param stock_code: str, 股票代码，默认空字符串
    :param specified_date: str, 指定的日期（YYYYMMDD格式），如果为空则使用系统时间
    :param hourly_volume_days: int, 小时量能数据的天数，如果为None则使用intraday_days
    :return: str, 聊天结果
    """
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 处理hourly_volume_days参数，如果没有提供则使用intraday_days
    if hourly_volume_days is None:
        hourly_volume_days = intraday_days

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

        # 获取当前时间：如果指定了日期则使用指定日期，否则使用系统时间
        if specified_date:
            # 使用指定的日期
            current_datetime = datetime.strptime(specified_date, '%Y%m%d')
        else:
            # 使用系统时间
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
            f"📊 csv文件中的数据和时间范围说明：\n"
            f"- 分时成交数据：包含最近 {intraday_days} 个交易日的日内分时数据，用于分析短期资金流向和主力行为模式\n"
            f"- 日K线数据：包含最近 {kline_days} 个交易日的K线数据，用于识别中长期趋势和关键技术位\n"
            f"- 市场指数数据：对应股票所属市场的指数（可能包含多个指数，根据板块自动匹配），时间范围与K线数据一致，用于评估系统性风险和市场beta系数\n"
            f"- 行业板块数据：股票所属行业的板块指数，时间范围与K线数据一致，用于分析行业相对强度和轮动机会\n"
            f"- 小时量能数据：基于最近 {hourly_volume_days} 个交易日的日内分时数据进行按小时级别统计（避免数据量过大），用于分析中期资金流向和主力行为模式\n\n"
            f"📋 数据结构说明：\n"
            f"{analysis_request.get('data_description', {}).get('data_structure', '')}\n\n"
            f"🔍 数据工作表详细说明：\n"
            f"• 分时成交数据段: {analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('fields', []))}\n"
            f"  分析重点: {', '.join(analysis_request.get('data_description', {}).get('intraday_data_section', {}).get('analysis_focus', []))}\n\n"
            f"• 日K线数据段: {analysis_request.get('data_description', {}).get('daily_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('daily_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('daily_data_section', {}).get('fields', []))}\n"
            f"  分析重点: {', '.join(analysis_request.get('data_description', {}).get('daily_data_section', {}).get('analysis_focus', []))}\n\n"
            f"• 市场指数数据段: {analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('section_markers', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('fields', []))}\n"
            f"  分析重点: {', '.join(analysis_request.get('data_description', {}).get('market_index_data_sections', {}).get('analysis_focus', []))}\n\n"
            f"• 行业板块数据段: {analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('fields', []))}\n"
            f"  分析重点: {', '.join(analysis_request.get('data_description', {}).get('industry_sector_data_section', {}).get('analysis_focus', []))}\n\n"
            f"• 小时量能分析数据段: {analysis_request.get('data_description', {}).get('hourly_volume_analysis_section', {}).get('description', '')}\n"
            f"  标识符: {analysis_request.get('data_description', {}).get('hourly_volume_analysis_section', {}).get('section_marker', '')}\n"
            f"  字段: {', '.join(analysis_request.get('data_description', {}).get('hourly_volume_analysis_section', {}).get('fields', []))}\n"
            f"  分析重点: {', '.join(analysis_request.get('data_description', {}).get('hourly_volume_analysis_section', {}).get('analysis_focus', []))}\n\n"
            f"📈 多日数据分析要求：\n"
            f"请对提供的多日分时数据进行逐日深度分析（按时间顺序由远及近）\n"
            f"🔬 分析步骤（应用于每一天的分时数据分析结果输出）：\n"
        )

        # 添加分析步骤 - 针对多日数据进行逐日分析
        for step in analysis_request.get('analysis_steps', []):
            user_content += f"步骤 {step.get('step', '')}: {step.get('description', '')}\n"
            if step.get('output_focus'):
                user_content += f"  输出重点: {step.get('output_focus', '')}\n"

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

        # 处理quantitative_metrics（量化指标）
        quantitative_metrics = req.get('quantitative_metrics', [])
        if quantitative_metrics:
            formatted_content += "\n量化指标要求：\n"
            for i, metric in enumerate(quantitative_metrics, 1):
                formatted_content += f"{i}. {metric}\n"

        # 处理decision_framework（决策框架）
        decision_framework = req.get('decision_framework', {})
        if decision_framework:
            formatted_content += "\n决策框架：\n"
            for key, value in decision_framework.items():
                formatted_content += f"{key}: {value}\n"

        # 处理output_format
        output_format = req.get('output_format', {})
        if output_format:
            formatted_content += "\n输出格式要求：\n"
            # 通用处理所有output_format中的键值对
            for key, value in output_format.items():
                formatted_content += f"{key}: {value}\n"

        formatted_content += "\n"

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

def get_kline_date_range(kline_days: int, end_date: str = None) -> tuple:
    """
    根据kline_days计算K线数据的日期范围。

    :param kline_days: int, K线数据的天数
    :param end_date: str, 结束日期，格式为YYYYMMDD，如果为None则使用今天日期
    :return: tuple, (start_date, end_date) 格式为YYYYMMDD
    """
    if end_date is None:
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

def get_intraday_date_range(days_before_today: int, end_date: str = None) -> tuple:
    """
    根据days_before_today计算分时数据的日期范围，使用交易日而非自然日。

    :param days_before_today: int, 分时数据往前追溯的交易日数量
    :param end_date: str, 结束日期，格式为YYYYMMDD，如果为None则使用今天日期
    :return: tuple, (start_date, end_date) 格式为YYYYMMDD
    """
    if end_date is None:
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

def analyze_stocks(config_file: str = 'anylizeconfig.json', keys_file: str = 'keys.json', command_line_stocks: List[str] = None, mode: int = 1):
    """分析股票的主函数

    :param config_file: 配置文件路径
    :param keys_file: 密钥文件路径
    :param command_line_stocks: 命令行传入的股票代码列表，如果提供则优先使用，否则使用配置文件
    :param mode: int, 处理模式：0=仅获取数据不进行大模型分析，1=完整处理流程，其他值=中止执行
    """
    # 检查处理模式
    if mode == 0:
        print("📊 模式0：仅获取数据，不进行大模型分析")
    elif mode == 1:
        print("🤖 模式1：完整处理流程（包含大模型分析）")
    else:
        print(f"❌ 无效的处理模式: {mode}，仅支持0（仅获取数据）或1（完整流程）")
        return

    # 1. 读取配置
    config = load_config(config_file, keys_file)

    # 如果提供了命令行股票参数，使用命令行参数；否则使用配置文件
    if command_line_stocks:
        stocks = command_line_stocks
        print(f"💴 使用命令行指定的股票: {', '.join(stocks)}")
    else:
        stocks = select_stocks(config)
        print(f"💴 使用配置文件指定的股票: {', '.join(stocks)}")

    # 读取指定的结束日期，如果为空则使用None（表示今天）
    specified_date = config.get('specified_date', '').strip()
    if specified_date:
        print(f"📅 使用指定的结束日期: {specified_date}")
    else:
        print("📅 使用今天的日期作为结束日期")
        specified_date = None

    # 分时数据使用intraday_days计算日期范围（基于交易日）
    intraday_days = config['intraday_days']
    intraday_start_date, intraday_end_date = get_intraday_date_range(intraday_days, specified_date)
    print(f"📅 分时数据日期范围: {intraday_start_date} 到 {intraday_end_date} (共{intraday_days}个交易日)")

    # 小时量能数据使用hourly_volume_days计算日期范围（基于交易日）
    hourly_volume_days = config.get('hourly_volume_days', intraday_days)  # 默认使用intraday_days
    hourly_start_date, hourly_end_date = get_intraday_date_range(hourly_volume_days, specified_date)
    print(f"📅 小时量能数据日期范围: {hourly_start_date} 到 {hourly_end_date} (共{hourly_volume_days}个交易日)")

    # K线数据使用kline_days计算日期范围
    kline_days = config.get('kline_days', 60)  # 默认60天
    kline_start_date, kline_end_date = get_kline_date_range(kline_days, specified_date)
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
            result = get_and_save_stock_data(
                stock=stock, 
                start_date=intraday_start_date, 
                end_date=intraday_end_date, 
                kline_days=kline_days,
                hourly_start_date=hourly_start_date,
                hourly_end_date=hourly_end_date
            )
            if result[0] is None:
                print(f"股票 {stock} 获取数据失败，跳过")
                continue
            file_paths, stock_name = result

            # 如果模式为0，仅获取数据，跳过文件上传和大模型对话
            if mode == 0:
                print(f"✅ 股票 {stock} 数据获取完成，跳过文件上传和大模型分析")
                continue

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
                stock_code=stock,
                specified_date=specified_date,
                hourly_volume_days=config.get('hourly_volume_days', config['intraday_days'])
            )
            if response:
                print(f"股票 {stock} 的分析结果: {response}\n")

                # 保存分析结果到MD文件
                current_time = datetime.now()
                date_str = current_time.strftime('%Y%m%d')
                time_str = current_time.strftime('%H%M%S')

                # 确保data_output文件夹存在
                output_dir = get_stock_output_dir(stock)
                output_dir.mkdir(parents=True, exist_ok=True)

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

            # 提取投资评级并添加到邮件主题中
            investment_rating = extract_investment_rating(str(md_filepath))
            if investment_rating:
                email_subject = f"股票 {stock_name}（{stock}）分析结果 - {investment_rating}"
                print(f"📧 邮件主题包含投资评级: {email_subject}")
            else:
                email_subject = f"股票 {stock_name}（{stock}）分析结果"
                print("📧 未找到投资评级，使用默认邮件主题")

            # 准备邮件正文
            email_body = f"股票 {stock_name}（{stock}）的分析报告已生成，请查看附件中的文件。\n\n附件包含：\n1. 主分析报告（HTML格式）\n2. 小时量能分析数据已包含在CSV文件中"

            # 准备附件列表 - 只包含HTML文件
            attachment_list = [str(html_filepath)]  # 只发送HTML文件

            send_email(
                subject=email_subject,
                body=email_body,
                receivers=email_receivers,
                sender=email_sender,
                password=email_password,
                attachment_paths=attachment_list  # 只发送HTML附件
            )

        except Exception as e:
            print(f"处理股票 {stock} 时出错: {e}\n")

        if index < total - 1:
            for i in range(10):  # 等待 300 秒，避免请求过于频繁
                print(".", end="", flush=True)
                t.sleep(1)  # 避免请求过于频繁

# 运行程序
if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        # sys.argv[0] 是脚本名
        # sys.argv[1] 是处理模式（0或1）
        # sys.argv[2:] 是股票代码列表
        
        try:
            mode = int(sys.argv[1])
            if mode not in [0, 1]:
                print(f"❌ 无效的处理模式: {mode}")
                print("💡 使用方法: python anaByQwen2.py <mode> [股票代码1] [股票代码2] ...")
                print("   mode: 0=仅获取数据，1=完整流程")
                print("   示例: python anaByQwen2.py 0 600000 000001")
                sys.exit(1)
            
            command_line_stocks = sys.argv[2:] if len(sys.argv) > 2 else None
            
            if command_line_stocks:
                print(f"🔧 检测到命令行参数，模式: {mode}, 股票代码: {', '.join(command_line_stocks)}")
            else:
                print(f"🔧 检测到命令行参数，模式: {mode}, 使用配置文件中的股票设置")
            
            analyze_stocks('anylizeconfig.json', 'keys.json', command_line_stocks, mode)
            
        except ValueError:
            print(f"❌ 处理模式必须是数字: {sys.argv[1]}")
            print("💡 使用方法: python anaByQwen2.py <mode> [股票代码1] [股票代码2] ...")
            print("   mode: 0=仅获取数据，1=完整流程")
            print("   示例: python anaByQwen2.py 0 600000 000001")
            sys.exit(1)
    else:
        print("🔧 未检测到命令行参数，使用默认模式1和配置文件中的股票设置")
        analyze_stocks('anylizeconfig.json', 'keys.json', None, 1)
