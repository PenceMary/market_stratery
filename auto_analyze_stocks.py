#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动股票分析脚本

功能：
- 在非交易时间（17:00-次日6:00）自动随机分析股票
- 避免重复分析同一只股票
- 智能控制API调用间隔，防止被封IP
- 持续运行，除非人工干预退出

使用方法：
python auto_analyze_stocks.py

配置文件：
- analyzeconfig.json: 主要配置文件（必须）
- keys.json: 密钥文件（必须）

配置文件模板已提供：analyzeconfig_template.json

依赖：
- anaByQwen2.py: 复用股票分析相关函数
- md_to_html.py: Markdown转HTML工具
"""

import akshare as ak
import random
import json
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from pathlib import Path
import time as t
import sys
import signal
import traceback
import logging
from logging.handlers import RotatingFileHandler
import os

# 从anaByQwen2.py导入需要的函数
from anaByQwen2 import (
    load_config,
    get_and_save_stock_data,
    upload_file,
    chat_with_qwen,
    send_email,
    cleanup_stock_data,
    extract_investment_rating,
    select_prompt_by_model,
    get_kline_date_range,
    get_intraday_date_range,
    get_stock_output_dir
)
from md_to_html import MarkdownToHTMLConverter

# ===== 配置常量 =====
DEFAULT_STOCKS_LIST_FILE = 'all_stocks_list.csv'
DEFAULT_ANALYZED_RECORDS_FILE = 'analyzed_stocks.json'
DEFAULT_LOG_FILE = 'auto_analyze_log.txt'
DEFAULT_CONFIG_FILE = 'analyzeconfig.json'
DEFAULT_KEYS_FILE = 'keys.json'

# ===== API调用间隔控制器 =====
class APICallIntervalController:
    """
    API调用间隔控制器
    
    功能：
    - 正常间隔：1-2分钟随机
    - 连续失败3次后：等待15分钟，间隔延长至2-4分钟
    - 成功一次后重置失败计数和间隔
    """
    
    def __init__(self, 
                 normal_min: int = 60, 
                 normal_max: int = 120,
                 extended_min: int = 120,
                 extended_max: int = 240,
                 failure_wait_time: int = 900,
                 failure_threshold: int = 3):
        """
        初始化间隔控制器
        
        :param normal_min: 正常间隔最小值（秒）
        :param normal_max: 正常间隔最大值（秒）
        :param extended_min: 延长间隔最小值（秒）
        :param extended_max: 延长间隔最大值（秒）
        :param failure_wait_time: 连续失败后等待时间（秒）
        :param failure_threshold: 连续失败阈值
        """
        self.normal_min = normal_min
        self.normal_max = normal_max
        self.extended_min = extended_min
        self.extended_max = extended_max
        self.failure_wait_time = failure_wait_time
        self.failure_threshold = failure_threshold
        
        self.consecutive_failures = 0
        self.is_extended_interval = False
        self.last_failure_time = None
    
    def get_next_interval(self) -> int:
        """
        获取下次API调用的间隔时间（秒）
        
        :return: 间隔时间（秒）
        """
        if self.is_extended_interval:
            # 延长间隔：2-4分钟
            interval = random.randint(self.extended_min, self.extended_max)
            print(f"⏱️  使用延长间隔: {interval}秒 ({interval//60}分{interval%60}秒)")
        else:
            # 正常间隔：1-2分钟
            interval = random.randint(self.normal_min, self.normal_max)
            print(f"⏱️  使用正常间隔: {interval}秒 ({interval//60}分{interval%60}秒)")
        
        return interval
    
    def record_success(self):
        """记录成功调用，重置失败计数和间隔"""
        if self.consecutive_failures > 0:
            print(f"✅ API调用成功，重置失败计数（之前连续失败{self.consecutive_failures}次）")
        self.consecutive_failures = 0
        self.is_extended_interval = False
        self.last_failure_time = None
    
    def record_failure(self):
        """记录失败调用，检查是否需要延长间隔"""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        
        print(f"❌ API调用失败，连续失败次数: {self.consecutive_failures}/{self.failure_threshold}")
        
        if self.consecutive_failures >= self.failure_threshold:
            if not self.is_extended_interval:
                print(f"⚠️  连续失败{self.failure_threshold}次，将延长间隔并等待{self.failure_wait_time//60}分钟")
                self.is_extended_interval = True
                return True  # 需要等待
        return False  # 不需要等待
    
    def wait_after_failures(self):
        """连续失败后的等待"""
        if self.consecutive_failures >= self.failure_threshold:
            print(f"⏳ 等待{self.failure_wait_time//60}分钟后继续...")
            for i in range(self.failure_wait_time):
                if i % 60 == 0:
                    remaining = self.failure_wait_time - i
                    print(f"   剩余等待时间: {remaining//60}分{remaining%60}秒", end='\r')
                t.sleep(1)
            print(f"\n✅ 等待完成，继续执行（间隔已延长至{self.extended_min//60}-{self.extended_max//60}分钟）")


# ===== 股票列表管理 =====
def get_all_stocks_list(cache_file: str = DEFAULT_STOCKS_LIST_FILE) -> pd.DataFrame:
    """
    获取所有A股股票列表
    
    :param cache_file: 缓存文件路径
    :return: DataFrame，包含所有A股股票信息
    """
    cache_path = Path(cache_file)
    
    # 如果缓存文件存在，直接读取
    if cache_path.exists():
        try:
            print(f"📂 从缓存文件读取股票列表: {cache_file}")
            df = pd.read_csv(cache_file, encoding='utf-8-sig')
            print(f"✅ 成功读取 {len(df)} 只股票")
            return df
        except Exception as e:
            print(f"⚠️  读取缓存文件失败: {e}，将重新下载")
    
    # 如果缓存文件不存在或读取失败，从接口获取
    print("📥 正在从接口获取所有A股股票列表...")
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            # 保存到缓存文件
            df.to_csv(cache_file, index=False, encoding='utf-8-sig')
            print(f"✅ 成功获取 {len(df)} 只股票，已保存到: {cache_file}")
            return df
        else:
            raise Exception("获取的股票列表为空")
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        raise


def update_stocks_list_if_needed(cache_file: str = DEFAULT_STOCKS_LIST_FILE, force_update: bool = False) -> pd.DataFrame:
    """
    如果需要，更新股票列表
    
    :param cache_file: 缓存文件路径
    :param force_update: 是否强制更新
    :return: DataFrame，包含所有A股股票信息
    """
    cache_path = Path(cache_file)
    
    # 如果强制更新或文件不存在，重新获取
    if force_update or not cache_path.exists():
        return get_all_stocks_list(cache_file)
    
    # 否则直接读取缓存
    return get_all_stocks_list(cache_file)


# ===== 已分析股票记录管理 =====
def load_analyzed_stocks(record_file: str = DEFAULT_ANALYZED_RECORDS_FILE) -> Dict[str, str]:
    """
    加载已分析股票记录
    
    :param record_file: 记录文件路径
    :return: 字典，格式为 {"股票代码": "分析日期时间"}
    """
    record_path = Path(record_file)
    
    if record_path.exists():
        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            print(f"📋 加载已分析股票记录: {len(records)} 只")
            return records
        except Exception as e:
            print(f"⚠️  加载已分析记录失败: {e}，将创建新记录")
    
    return {}


def save_analyzed_stocks(record_file: str, records: Dict[str, str]):
    """
    保存已分析股票记录
    
    :param record_file: 记录文件路径
    :param records: 记录字典
    """
    try:
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存已分析记录失败: {e}")


def is_stock_analyzed(stock_code: str, records: Dict[str, str]) -> bool:
    """
    检查股票是否已分析
    
    :param stock_code: 股票代码
    :param records: 已分析记录字典
    :return: True表示已分析，False表示未分析
    """
    return stock_code in records


def mark_stock_analyzed(stock_code: str, record_file: str, records: Dict[str, str], logger: logging.Logger = None):
    """
    标记股票为已分析
    
    :param stock_code: 股票代码
    :param record_file: 记录文件路径
    :param records: 已分析记录字典（会被修改）
    :param logger: 日志记录器（可选）
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    records[stock_code] = timestamp
    save_analyzed_stocks(record_file, records)
    if logger:
        logger.info(f"已标记股票 {stock_code} 为已分析（{timestamp}）")
    else:
        print(f"✅ 已标记股票 {stock_code} 为已分析（{timestamp}）")


def get_unanalyzed_stocks(all_stocks_df: pd.DataFrame, analyzed_records: Dict[str, str]) -> List[str]:
    """
    获取未分析的股票列表
    
    :param all_stocks_df: 所有股票DataFrame
    :param analyzed_records: 已分析记录字典
    :return: 未分析的股票代码列表（字符串类型）
    """
    all_stock_codes = all_stocks_df['代码'].tolist()
    # 确保股票代码转换为字符串类型
    unanalyzed = [str(code) for code in all_stock_codes if not is_stock_analyzed(str(code), analyzed_records)]
    return unanalyzed


def reset_daily_records_if_needed(record_file: str, records: Dict[str, str]) -> Dict[str, str]:
    """
    如果需要，每日重置已分析记录（可选功能）
    
    :param record_file: 记录文件路径
    :param records: 当前记录字典
    :return: 更新后的记录字典
    """
    # 检查最后一条记录的时间
    if not records:
        return records
    
    # 获取今天的日期
    today = date.today().strftime('%Y-%m-%d')
    
    # 检查是否有今天的记录
    has_today_record = any(today in timestamp for timestamp in records.values())
    
    # 如果没有今天的记录，说明是新的一天，可以选择重置
    # 这里暂时不实现自动重置，保留历史记录
    # 如果需要每日重置，可以取消下面的注释
    # if not has_today_record:
    #     print("🔄 新的一天，重置已分析记录")
    #     records = {}
    #     save_analyzed_stocks(record_file, records)
    
    return records


# ===== 时间判断 =====
def is_execution_time(start_hour: int = 17, end_hour: int = 6) -> bool:
    """
    判断当前时间是否在执行时间范围内（17:00-次日6:00）
    
    :param start_hour: 开始时间（小时）
    :param end_hour: 结束时间（小时）
    :return: True表示在执行时间范围内
    """
    now = datetime.now()
    current_hour = now.hour
    
    # 17:00-23:59 或 00:00-06:00
    if current_hour >= start_hour or current_hour < end_hour:
        return True
    return False


def get_time_until_execution(start_hour: int = 17) -> int:
    """
    获取距离执行时间的秒数
    
    :param start_hour: 开始时间（小时）
    :return: 需要等待的秒数
    """
    now = datetime.now()
    current_hour = now.hour
    
    # 如果当前时间已经在执行时间范围内，返回0
    if is_execution_time(start_hour):
        return 0
    
    # 计算到下一个执行时间点的秒数
    if current_hour < start_hour:
        # 今天还没到17:00，等待到今天17:00
        target_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        # 已经过了17:00但还没到次日6:00，这种情况不应该发生（因为is_execution_time会返回True）
        # 但为了安全，计算到明天17:00
        target_time = (now + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    delta = target_time - now
    return int(delta.total_seconds())


def wait_until_execution_time(start_hour: int = 17, check_interval: int = 60):
    """
    等待直到执行时间
    
    :param start_hour: 开始时间（小时）
    :param check_interval: 检查间隔（秒）
    """
    while not is_execution_time(start_hour):
        wait_seconds = get_time_until_execution(start_hour)
        if wait_seconds > check_interval:
            wait_seconds = check_interval
        
        print(f"⏳ 当前时间不在执行范围内，等待 {wait_seconds} 秒后检查...")
        for i in range(wait_seconds):
            if i % 60 == 0:
                remaining = wait_seconds - i
                print(f"   剩余等待时间: {remaining}秒", end='\r')
            t.sleep(1)
        print()  # 换行

# ===== 主控制循环 =====
def analyze_stock(stock_code: str, 
                interval_controller: APICallIntervalController,
                analyzed_records: Dict[str, str],
                record_file: str,
                config: Dict[str, Any],
                logger: logging.Logger) -> bool:
    """
    分析单个股票
    
    :param stock_code: 股票代码（字符串或整数，会自动转换为字符串）
    :param interval_controller: API调用间隔控制器
    :param analyzed_records: 已分析记录字典
    :param record_file: 记录文件路径
    :param config: 配置字典
    :param logger: 日志记录器
    :return: True表示分析成功，False表示失败
    """
    # 确保 stock_code 是字符串类型
    stock_code = str(stock_code)
    logger.info(f"开始分析股票: {stock_code}")
    
    try:
        # 从 config 中获取日期范围参数（使用get方法确保安全）
        specified_date = config.get('specified_date', '').strip() or None
        intraday_days = config.get('intraday_days', 3)
        intraday_start_date, intraday_end_date = get_intraday_date_range(intraday_days, specified_date)
        hourly_volume_days = config.get('hourly_volume_days', intraday_days)
        hourly_start_date, hourly_end_date = get_intraday_date_range(hourly_volume_days, specified_date)
        kline_days = config.get('kline_days', 60)
        
        # 在调用akshare接口之前等待，避免API调用过快被封IP
        # 使用analyzeconfig.json中的normal_min_interval和normal_max_interval作为等待时间（1-2分钟）
        api_control = config.get('api_control', {})
        wait_min = api_control.get('normal_min_interval', 60)  # 默认1分钟
        wait_max = api_control.get('normal_max_interval', 120)  # 默认2分钟
        wait_time = random.randint(wait_min, wait_max)
        logger.info(f"⏳ 等待 {wait_time} 秒（{wait_time//60}分{wait_time%60}秒）后开始获取股票数据，避免API调用过快被封IP...")
        for i in range(wait_time):
            if i % 60 == 0 and i > 0:
                remaining = wait_time - i
                logger.info(f"   剩余等待时间: {remaining//60}分{remaining%60}秒")
            t.sleep(1)
        logger.info("✅ 等待完成，开始获取股票数据")
        
        # 1. 下载股票数据
        logger.info("正在下载股票数据...")
        result = get_and_save_stock_data(
            stock=stock_code,
            start_date=intraday_start_date,
            end_date=intraday_end_date,
            kline_days=kline_days,
            hourly_start_date=hourly_start_date,
            hourly_end_date=hourly_end_date
        )
        
        if result[0] is None:
            logger.error(f"股票 {stock_code} 数据下载失败")
            interval_controller.record_failure()
            cleanup_stock_data(stock_code)
            return False
        
        file_paths, stock_name = result
        interval_controller.record_success()
        
        # 2. 上传文件并获取 file_id
        logger.info("正在上传文件...")
        main_file_path = file_paths['complete']
        api_key = config.get('qwen_api_key', config.get('api_key', ''))
        file_id = upload_file(file_path=main_file_path, api_key=api_key)
        
        if file_id is None:
            logger.error(f"股票 {stock_code} 的文件上传失败")
            cleanup_stock_data(stock_code)
            interval_controller.record_failure()
            return False
        
        # 3. 大模型分析
        logger.info("正在进行大模型分析...")
        prompt_template = select_prompt_by_model(config)
        response = chat_with_qwen(
            file_id=file_id,
            question=prompt_template,
            api_key=api_key,
            intraday_days=intraday_days,
            kline_days=kline_days,
            stock_code=stock_code,
            specified_date=specified_date,
            hourly_volume_days=hourly_volume_days
        )
        
        if not response:
            logger.error(f"股票 {stock_code} 大模型分析失败")
            cleanup_stock_data(stock_code)
            return False
        
        # 4. 保存分析结果到MD文件
        logger.info("正在保存分析结果...")
        current_time = datetime.now()
        date_str = current_time.strftime('%Y%m%d')
        time_str = current_time.strftime('%H%M%S')
        
        output_dir = get_stock_output_dir(stock_code)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        clean_stock_name = stock_name.replace('(', '').replace(')', '').replace(' ', '_')
        md_filename = f"{stock_code}_{clean_stock_name}_{intraday_start_date}_to_{intraday_end_date}_{date_str}_{time_str}.md"
        md_filepath = output_dir / md_filename
        
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {stock_name}（{stock_code}）股票分析报告\n\n")
            f.write(f"**分析时间**: {current_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
            f.write(f"---\n\n")
            f.write(response)
        
        logger.info(f"分析结果已保存到: {md_filepath}")
        
        # 5. 转换为HTML
        logger.info("正在转换为HTML...")
        html_filename = md_filename.replace('.md', '.html')
        html_filepath = output_dir / html_filename
        converter = MarkdownToHTMLConverter()
        if not converter.convert_file(str(md_filepath), str(html_filepath)):
            logger.error(f"HTML转换失败: {md_filepath}")
            cleanup_stock_data(stock_code)
            return False
        
        logger.info(f"HTML文件已生成: {html_filepath}")
        
        # 6. 发送邮件通知
        logger.info("正在发送分析结果邮件...")
        email_sender = config.get('email_sender', '')
        email_password = config.get('email_password', '')
        email_receivers = config.get('email_receivers', [])
        
        # 提取投资评级并添加到邮件主题中
        investment_rating = extract_investment_rating(str(md_filepath))
        if investment_rating:
            email_subject = f"股票 {stock_name}（{stock_code}）分析结果 - {investment_rating}"
        else:
            email_subject = f"股票 {stock_name}（{stock_code}）分析结果"
        
        email_body = f"股票 {stock_name}（{stock_code}）的分析报告已生成，请查看附件中的文件。\n\n附件包含：\n1. 主分析报告（HTML格式）\n2. 小时量能分析数据已包含在CSV文件中"
        attachment_list = [str(html_filepath), str(md_filepath)]
        
        email_sent = send_email(
            subject=email_subject,
            body=email_body,
            receivers=email_receivers,
            sender=email_sender,
            password=email_password,
            attachment_paths=attachment_list
        )
        
        if not email_sent:
            logger.warning(f"股票 {stock_code} 邮件发送失败，但分析已完成")
        
        # 7. 清理数据目录
        cleanup_stock_data(stock_code)
        
        # 8. 标记为已分析
        mark_stock_analyzed(stock_code, record_file, analyzed_records)
        
        logger.info(f"股票 {stock_code} 分析完成！")
        return True
        
    except Exception as e:
        logger.error(f"股票 {stock_code} 分析过程中发生错误: {str(e)}", exc_info=True)
        interval_controller.record_failure()
        # 确保在出错时也清理数据
        try:
            cleanup_stock_data(stock_code)
        except:
            pass
        return False


def setup_logging(log_file: str = DEFAULT_LOG_FILE) -> logging.Logger:
    """
    设置日志系统
    
    :param log_file: 日志文件路径
    :return: 日志记录器
    """
    # 创建日志目录（如果不存在）
    log_dir = Path(log_file).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建 rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 创建 console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 创建 logger
    logger = logging.getLogger('auto_analyze_stocks')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def load_config_with_validation(config_file: str = DEFAULT_CONFIG_FILE, keys_file: str = DEFAULT_KEYS_FILE) -> Dict[str, Any]:
    """
    加载并验证配置文件
    
    :param config_file: 配置文件路径
    :param keys_file: 密钥文件路径
    :return: 配置字典
    :raises: FileNotFoundError, ValueError
    """
    # 加载配置文件
    if not Path(config_file).exists():
        raise FileNotFoundError(f"配置文件 {config_file} 不存在")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        raise ValueError(f"配置文件加载失败: {str(e)}")
    
    # 加载密钥文件
    if not Path(keys_file).exists():
        raise FileNotFoundError(f"密钥文件 {keys_file} 不存在")
    
    try:
        with open(keys_file, 'r', encoding='utf-8') as f:
            keys = json.load(f)
    except Exception as e:
        raise ValueError(f"密钥文件加载失败: {str(e)}")
    
    # 验证必要配置项
    required_keys = ['execution_time', 'api_control', 'analysis']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"配置文件缺少必要项: {key}")
    
    # 验证执行时间配置
    exec_time = config['execution_time']
    if 'start_hour' not in exec_time or 'end_hour' not in exec_time:
        raise ValueError("配置文件缺少执行时间配置")
    
    # 验证API控制配置
    api_control = config['api_control']
    required_api_keys = ['normal_min_interval', 'normal_max_interval', 
                      'extended_min_interval', 'extended_max_interval',
                      'failure_wait_time', 'failure_threshold']
    for key in required_api_keys:
        if key not in api_control:
            raise ValueError(f"配置文件缺少API控制配置: {key}")
    
    # 验证分析配置
    analysis_config = config['analysis']
    required_analysis_keys = ['output_base_dir', 'max_retries', 'retry_delay', 'api_timeout']
    for key in required_analysis_keys:
        if key not in analysis_config:
            raise ValueError(f"配置文件缺少分析配置: {key}")
    
    # 合并keys.json中的配置到config中（与anaByQwen2.py的load_config保持一致）
    config.update(keys)
    
    # 尝试从anylizeconfig.json读取缺失的配置项（如果存在）
    analyze_config_file = 'anylizeconfig.json'
    if Path(analyze_config_file).exists():
        try:
            with open(analyze_config_file, 'r', encoding='utf-8') as f:
                analyze_config = json.load(f)
            # 合并分析相关的配置项
            for key in ['intraday_days', 'hourly_volume_days', 'kline_days', 'specified_date', 'prompt']:
                if key in analyze_config and key not in config:
                    config[key] = analyze_config[key]
                    print(f"✅ 从 {analyze_config_file} 读取配置项: {key}")
        except Exception as e:
            print(f"⚠️  读取 {analyze_config_file} 失败: {e}，将使用默认值")
    
    # 设置默认值（如果配置中不存在）
    config.setdefault('intraday_days', 3)
    config.setdefault('hourly_volume_days', 10)
    config.setdefault('kline_days', 60)
    config.setdefault('specified_date', '')
    
    return config


def main_control_loop(logger: logging.Logger, debug_mode: bool = False):
    """
    主控制循环
    
    功能：
    - 持续运行，直到人工干预退出
    - 在执行时间范围内分析股票
    - 管理分析进度和状态
    
    :param logger: 日志记录器
    :param debug_mode: 调试模式，如果为True则跳过时间检测，立即执行
    """
    if debug_mode:
        logger.info("🐛 调试模式已启用：跳过时间检测，立即执行")
    logger.info("自动股票分析系统启动")
    logger.info("=" * 50)
    
    try:
        # 1. 加载配置
        config = load_config_with_validation()
        logger.info("配置加载完成")
        
        # 2. 获取股票列表
        all_stocks_df = update_stocks_list_if_needed()
        logger.info(f"共有 {len(all_stocks_df)} 只股票需要分析")
        
        # 3. 加载已分析记录
        analyzed_records = load_analyzed_stocks()
        analyzed_records = reset_daily_records_if_needed(DEFAULT_ANALYZED_RECORDS_FILE, analyzed_records)
        
        # 4. 初始化API间隔控制器
        api_control = config['api_control']
        interval_controller = APICallIntervalController(
            normal_min=api_control['normal_min_interval'],
            normal_max=api_control['normal_max_interval'],
            extended_min=api_control['extended_min_interval'],
            extended_max=api_control['extended_max_interval'],
            failure_wait_time=api_control['failure_wait_time'],
            failure_threshold=api_control['failure_threshold']
        )
        
        # 5. 主循环
        while True:
            # 检查是否在执行时间范围内（调试模式下跳过）
            if not debug_mode and not is_execution_time():
                logger.info("当前时间不在执行范围内，等待...")
                wait_until_execution_time()
                continue
            
            # 获取未分析的股票
            unanalyzed_stocks = get_unanalyzed_stocks(all_stocks_df, analyzed_records)
            
            if not unanalyzed_stocks:
                logger.info("所有股票都已分析完成！")
                # 等待一段时间后重置记录（可选）
                logger.info("等待24小时后重置分析记录...")
                t.sleep(86400)  # 等待24小时
                analyzed_records = {}  # 重置记录
                save_analyzed_stocks(DEFAULT_ANALYZED_RECORDS_FILE, analyzed_records)
                continue
            
            # 随机选择一只股票进行分析
            stock_to_analyze = random.choice(unanalyzed_stocks)
            logger.info(f"随机选择股票: {stock_to_analyze}")
            
            # 分析股票
            analyze_stock(stock_to_analyze, interval_controller, analyzed_records, 
                        DEFAULT_ANALYZED_RECORDS_FILE, config, logger)
            
            # 获取下一次API调用的间隔时间
            interval = interval_controller.get_next_interval()
            
            # 等待指定间隔时间
            logger.info(f"等待 {interval} 秒后进行下一次分析...")
            t.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"\n程序发生严重错误: {str(e)}")
        logger.error("错误详情:")
        logger.error(traceback.format_exc())
    finally:
        logger.info("\n程序结束")


# ===== 信号处理 =====
def cleanup_resources():
    """
    清理程序资源
    """
    print("\n🧹 正在清理程序资源...")
    # 这里可以添加更多的资源清理逻辑
    print("✅ 资源清理完成")


def signal_handler(sig, frame):
    """
    信号处理函数，用于优雅退出
    """
    print("\n⏹️  收到退出信号，程序将退出...")
    cleanup_resources()
    sys.exit(0)


def setup_signal_handlers():
    """
    设置信号处理
    """
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号


# ===== 主函数 =====
def main():
    """
    主函数
    
    命令行参数：
    - 无参数：正常模式，按时间检测执行
    - 参数为1：调试模式，跳过时间检测，立即执行
    """
    # 解析命令行参数
    debug_mode = False
    if len(sys.argv) > 1:
        try:
            debug_flag = int(sys.argv[1])
            if debug_flag == 1:
                debug_mode = True
                print("🐛 调试模式已启用：跳过时间检测，立即执行")
            else:
                print(f"⚠️  未知参数: {debug_flag}，使用正常模式")
        except ValueError:
            print(f"⚠️  无效参数: {sys.argv[1]}，使用正常模式")
    
    try:
        # 设置信号处理
        setup_signal_handlers()
        
        # 设置日志系统
        logger = setup_logging()
        
        # 运行主控制循环
        main_control_loop(logger, debug_mode=debug_mode)
        
    except Exception as e:
        print(f"❌ 程序启动失败: {str(e)}")
        print("📝 错误详情:")
        traceback.print_exc()
    finally:
        print("\n👋 程序结束")


if __name__ == "__main__":
    main()