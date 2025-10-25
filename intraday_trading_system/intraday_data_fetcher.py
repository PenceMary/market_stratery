"""
日内交易数据获取模块
负责获取实时行情、分时数据、盘口数据、大盘指数等
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List
import time
from functools import wraps
from pathlib import Path
import os
import warnings
import socket

# 禁用SSL警告
warnings.filterwarnings('ignore')

# 禁用代理，避免代理连接问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

# 设置默认socket超时时间为60秒
socket.setdefaulttimeout(60)


def retry_on_failure(max_retries=3, delay=2, timeout=30):
    """
    重试装饰器，用于处理网络请求失败
    
    :param max_retries: 最大重试次数
    :param delay: 重试间隔（秒）
    :param timeout: 超时时间（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, Exception) as e:
                    error_msg = str(e)
                    
                    # 判断是否为超时或网络错误
                    is_network_error = any(keyword in error_msg.lower() for keyword in 
                                          ['timeout', 'connection', 'proxy', 'max retries'])
                    
                    if attempt < max_retries - 1 and is_network_error:
                        wait_time = delay * (attempt + 1)  # 指数退避
                        print(f"  ⚠️ 第{attempt + 1}次尝试失败: {error_msg[:100]}...")
                        print(f"  ⏳ {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        if attempt == max_retries - 1:
                            print(f"  ❌ 已重试{max_retries}次仍失败")
                        raise e
            return None
        return wrapper
    return decorator


class IntradayDataFetcher:
    """日内数据获取器"""
    
    def __init__(self, max_retries=3, retry_delay=2, timeout=30):
        """
        初始化数据获取器
        
        :param max_retries: 最大重试次数
        :param retry_delay: 重试延迟（秒）
        :param timeout: 超时时间（秒）
        """
        self.cache = {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._trading_calendar = None  # 交易日历缓存
    
    def _get_trading_calendar(self):
        """获取交易日历(带缓存)"""
        if self._trading_calendar is None:
            try:
                self._trading_calendar = ak.tool_trade_date_hist_sina()
                self._trading_calendar['trade_date'] = pd.to_datetime(self._trading_calendar['trade_date'])
            except Exception as e:
                print(f"⚠️ 获取交易日历失败: {e}")
                self._trading_calendar = pd.DataFrame()
        return self._trading_calendar
    
    def is_trading_day(self, date_str: str) -> bool:
        """
        判断指定日期是否为交易日
        
        :param date_str: 日期字符串,格式YYYYMMDD
        :return: True表示是交易日,False表示非交易日
        """
        try:
            calendar = self._get_trading_calendar()
            if calendar.empty:
                return False
            
            target_date = pd.to_datetime(date_str)
            return target_date in calendar['trade_date'].values
        except Exception as e:
            print(f"⚠️ 判断交易日失败: {e}")
            return False
    
    def get_latest_trading_day(self, before_date: str = None) -> str:
        """
        获取指定日期之前(含当天)的最近交易日
        
        :param before_date: 日期字符串,格式YYYYMMDD,如果为None则使用今天
        :return: 最近交易日,格式YYYYMMDD
        """
        try:
            if before_date is None:
                before_date = datetime.now().strftime('%Y%m%d')
            
            calendar = self._get_trading_calendar()
            if calendar.empty:
                return before_date
            
            target_date = pd.to_datetime(before_date)
            # 获取所有<=目标日期的交易日
            valid_dates = calendar[calendar['trade_date'] <= target_date]['trade_date']
            
            if valid_dates.empty:
                return before_date
            
            # 返回最近的交易日
            latest_trading_day = valid_dates.max()
            return latest_trading_day.strftime('%Y%m%d')
        except Exception as e:
            print(f"⚠️ 获取最近交易日失败: {e}")
            return before_date if before_date else datetime.now().strftime('%Y%m%d')
    
    def get_realtime_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票实时行情（带重试机制）
        优先使用快速接口,失败后使用备用接口
        
        :param stock_code: 股票代码
        :return: 实时行情数据字典
        """
        print(f"📊 获取 {stock_code} 实时行情...")
        
        # 使用重试机制
        for attempt in range(self.max_retries):
            try:
                # 方法1: 优先使用历史行情接口(更快,单个股票)
                try:
                    today = datetime.now().strftime('%Y%m%d')
                    yesterday = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    
                    # 获取最近几天的K线数据
                    hist_df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=yesterday,
                        end_date=today,
                        adjust=""
                    )
                    
                    if not hist_df.empty:
                        latest = hist_df.iloc[-1]
                        
                        # 获取股票名称
                        info_df = ak.stock_individual_info_em(symbol=stock_code)
                        info_dict = dict(zip(info_df['item'], info_df['value']))
                        stock_name = info_dict.get('股票简称', stock_code)
                        
                        # 计算昨收(如果有多天数据,取倒数第二天的收盘价)
                        pre_close = hist_df.iloc[-2]['收盘'] if len(hist_df) > 1 else latest['开盘']
                        
                        quote = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'current_price': latest['收盘'],
                            'open_price': latest['开盘'],
                            'high_price': latest['最高'],
                            'low_price': latest['最低'],
                            'pre_close': pre_close,
                            'price_change': latest['涨跌幅'],
                            'price_change_amount': latest['涨跌额'],
                            'volume': latest['成交量'],
                            'amount': latest['成交额'],
                            'amplitude': latest['振幅'],
                            'turnover_rate': latest['换手率'],
                            'volume_ratio': 1.0,  # 历史数据无量比,设为1.0
                            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # 计算涨跌停价
                        limit_up_price = round(pre_close * 1.10, 2)
                        limit_down_price = round(pre_close * 0.90, 2)
                        
                        # 科创板和创业板是20%
                        if stock_code.startswith('688') or stock_code.startswith('300'):
                            limit_up_price = round(pre_close * 1.20, 2)
                            limit_down_price = round(pre_close * 0.80, 2)
                        # 北交所是30%
                        elif stock_code.startswith(('83', '43', '87', '920')):
                            limit_up_price = round(pre_close * 1.30, 2)
                            limit_down_price = round(pre_close * 0.70, 2)
                        
                        quote['limit_up_price'] = limit_up_price
                        quote['limit_down_price'] = limit_down_price
                        
                        print(f"✅ 实时行情获取成功(快速接口): {quote['stock_name']} 当前价 {quote['current_price']}")
                        return quote
                    else:
                        raise Exception("历史数据为空")
                        
                except Exception as e1:
                    # 方法2: 备用方案 - 使用完整市场数据(较慢但更完整)
                    print(f"   快速接口失败({str(e1)[:50]}),尝试备用接口...")
                    df = ak.stock_zh_a_spot_em()
                    stock_data = df[df['代码'] == stock_code]
                    
                    if stock_data.empty:
                        print(f"❌ 未找到股票 {stock_code} 的实时行情")
                        return None
                    
                    row = stock_data.iloc[0]
                    
                    quote = {
                        'stock_code': stock_code,
                        'stock_name': row['名称'],
                        'current_price': row['最新价'],
                        'open_price': row['今开'],
                        'high_price': row['最高'],
                        'low_price': row['最低'],
                        'pre_close': row['昨收'],
                        'price_change': row['涨跌幅'],
                        'price_change_amount': row['涨跌额'],
                        'volume': row['成交量'],
                        'amount': row['成交额'],
                        'amplitude': row['振幅'],
                        'turnover_rate': row['换手率'],
                        'volume_ratio': row['量比'],
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 计算涨跌停价
                    limit_up_price = round(row['昨收'] * 1.10, 2)
                    limit_down_price = round(row['昨收'] * 0.90, 2)
                    
                    # 科创板和创业板是20%
                    if stock_code.startswith('688') or stock_code.startswith('300'):
                        limit_up_price = round(row['昨收'] * 1.20, 2)
                        limit_down_price = round(row['昨收'] * 0.80, 2)
                    # 北交所是30%
                    elif stock_code.startswith(('83', '43', '87', '920')):
                        limit_up_price = round(row['昨收'] * 1.30, 2)
                        limit_down_price = round(row['昨收'] * 0.70, 2)
                    
                    quote['limit_up_price'] = limit_up_price
                    quote['limit_down_price'] = limit_down_price
                    
                    print(f"✅ 实时行情获取成功(备用接口): {quote['stock_name']} 当前价 {quote['current_price']}")
                    return quote
                
            except Exception as e:
                error_msg = str(e)
                is_network_error = any(keyword in error_msg.lower() for keyword in 
                                      ['timeout', 'connection', 'proxy', 'max retries', 'read timed out'])
                
                if attempt < self.max_retries - 1 and is_network_error:
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"  ⚠️ 第{attempt + 1}次尝试失败: {error_msg[:80]}...")
                    print(f"  ⏳ {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    if attempt == self.max_retries - 1:
                        print(f"  ❌ 已重试{self.max_retries}次仍失败")
                    print(f"❌ 获取实时行情失败: {e}")
                    return None
        
        return None
    
    def get_today_intraday_data(self, stock_code: str) -> pd.DataFrame:
        """
        获取今日分时数据(智能判断交易日)
        
        :param stock_code: 股票代码
        :return: 分时数据DataFrame
        """
        try:
            print(f"📈 获取 {stock_code} 今日分时数据...")
            
            # 获取今日日期
            today = datetime.now().strftime('%Y%m%d')
            
            # 判断今天是否为交易日
            if not self.is_trading_day(today):
                # 获取最近的交易日
                latest_trading_day = self.get_latest_trading_day(today)
                print(f"⚠️ 今天({today})不是交易日,最近的交易日是: {latest_trading_day}")
                print(f"⚠️ 今日无分时数据(非交易日)")
                return pd.DataFrame()
            
            # 确定市场代码
            if stock_code.startswith('688'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('83', '43', '87', '920')):
                symbol = f"bj{stock_code}"
            elif stock_code.startswith('60'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('00', '30')):
                symbol = f"sz{stock_code}"
            else:
                symbol = stock_code
            
            # 获取分时数据
            df = ak.stock_intraday_sina(symbol=symbol, date=today)
            
            if df.empty:
                print(f"⚠️ 今日暂无分时数据(可能还未开盘或已收盘)")
                return pd.DataFrame()
            
            # 检查必要字段
            if 'ticktime' not in df.columns:
                print(f"⚠️ 分时数据格式异常,缺少ticktime字段")
                return pd.DataFrame()
            
            print(f"✅ 分时数据获取成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"⚠️ 获取分时数据异常: {e}")
            return pd.DataFrame()
    
    def get_historical_intraday_data(self, stock_code: str, days: int = 3) -> pd.DataFrame:
        """
        获取最近几天的分时数据
        
        :param stock_code: 股票代码
        :param days: 天数
        :return: 分时数据DataFrame
        """
        try:
            print(f"📊 获取 {stock_code} 最近{days}天的分时数据...")
            
            # 确定市场代码
            if stock_code.startswith('688'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('83', '43', '87', '920')):
                symbol = f"bj{stock_code}"
            elif stock_code.startswith('60'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('00', '30')):
                symbol = f"sz{stock_code}"
            else:
                symbol = stock_code
            
            # 获取交易日历
            calendar = ak.tool_trade_date_hist_sina()
            calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
            
            # 获取最近的交易日
            today = datetime.now()
            recent_dates = calendar[calendar['trade_date'] <= today].tail(days)
            
            all_data = []
            for date in recent_dates['trade_date']:
                date_str = date.strftime('%Y%m%d')
                try:
                    df = ak.stock_intraday_sina(symbol=symbol, date=date_str)
                    if not df.empty:
                        df['date'] = date_str
                        all_data.append(df)
                    time.sleep(1)  # 避免请求过快
                except Exception as e:
                    print(f"⚠️ 获取 {date_str} 数据失败: {e}")
                    continue
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                print(f"✅ 历史分时数据获取成功，共 {len(result)} 条记录")
                return result
            else:
                print(f"❌ 未获取到历史分时数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取历史分时数据失败: {e}")
            return pd.DataFrame()
    
    def get_order_book(self, stock_code: str) -> Dict[str, Any]:
        """
        获取五档盘口数据
        
        :param stock_code: 股票代码
        :return: 盘口数据字典
        """
        try:
            print(f"📋 获取 {stock_code} 盘口数据...")
            
            # 非交易时间盘口数据无意义,直接返回空数据
            current_time = datetime.now()
            hour = current_time.hour
            minute = current_time.minute
            
            is_trading_time = False
            if (9 <= hour < 11) or (hour == 11 and minute <= 30):
                is_trading_time = True
            elif (13 <= hour < 15):
                is_trading_time = True
            
            if not is_trading_time:
                print(f"⚠️ 非交易时间,跳过盘口数据获取")
                return {
                    'bid': [{'price': 0, 'volume': 0} for _ in range(5)],
                    'ask': [{'price': 0, 'volume': 0} for _ in range(5)]
                }
            
            # 交易时间内尝试获取实时盘口(使用快速接口备选方案)
            try:
                # 尝试使用个股实时行情接口
                df = ak.stock_bid_ask_em(symbol=stock_code)
                if not df.empty and len(df) >= 10:
                    order_book = {
                        'bid': [
                            {'price': df.iloc[i]['价格'], 'volume': df.iloc[i]['成交量']} 
                            for i in range(5)
                        ],
                        'ask': [
                            {'price': df.iloc[i+5]['价格'], 'volume': df.iloc[i+5]['成交量']} 
                            for i in range(5)
                        ]
                    }
                    print(f"✅ 盘口数据获取成功")
                    return order_book
            except:
                pass
            
            # 备用方案: 返回基础结构
            print(f"⚠️ 盘口数据暂不可用,使用默认值")
            return {
                'bid': [{'price': 0, 'volume': 0} for _ in range(5)],
                'ask': [{'price': 0, 'volume': 0} for _ in range(5)]
            }
            
        except Exception as e:
            print(f"⚠️ 获取盘口数据异常: {e}, 使用默认值")
            return {
                'bid': [{'price': 0, 'volume': 0} for _ in range(5)],
                'ask': [{'price': 0, 'volume': 0} for _ in range(5)]
            }
    
    def get_market_indices(self, stock_code: str) -> Dict[str, Any]:
        """
        获取大盘指数数据
        
        :param stock_code: 股票代码
        :return: 指数数据字典
        """
        try:
            print(f"📊 获取大盘指数数据...")
            
            indices = {}
            
            # 根据股票代码确定主要指数
            if stock_code.startswith('60'):
                # 上证
                indices['上证指数'] = self._get_index_realtime('000001')
            elif stock_code.startswith('688'):
                # 科创板
                indices['上证指数'] = self._get_index_realtime('000001')
                indices['科创50'] = self._get_index_realtime('000688')
            elif stock_code.startswith('00'):
                # 深圳主板
                indices['深证成指'] = self._get_index_realtime('399001')
            elif stock_code.startswith('30'):
                # 创业板
                indices['深证成指'] = self._get_index_realtime('399001')
                indices['创业板指'] = self._get_index_realtime('399006')
            elif stock_code.startswith(('83', '43', '87', '920')):
                # 北交所
                indices['北证50'] = self._get_index_realtime('899050')
            else:
                # 默认上证指数
                indices['上证指数'] = self._get_index_realtime('000001')
            
            print(f"✅ 大盘指数数据获取成功")
            return indices
            
        except Exception as e:
            print(f"❌ 获取大盘指数失败: {e}")
            return {}
    
    def _get_index_realtime(self, index_code: str) -> Dict[str, Any]:
        """获取指数实时数据(使用快速接口)"""
        try:
            # 使用指数历史数据接口(更快更稳定)
            today = datetime.now().strftime('%Y%m%d')
            yesterday = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            
            # 构建指数symbol
            if index_code == '000001':
                symbol = 'sh000001'  # 上证指数
            elif index_code == '399001':
                symbol = 'sz399001'  # 深证成指
            elif index_code == '399006':
                symbol = 'sz399006'  # 创业板指
            elif index_code == '000688':
                symbol = 'sh000688'  # 科创50
            elif index_code == '899050':
                symbol = 'bj899050'  # 北证50
            else:
                symbol = index_code
            
            # 尝试获取指数历史数据
            try:
                df = ak.stock_zh_index_daily(symbol=symbol)
                if not df.empty:
                    latest = df.iloc[-1]
                    # 计算涨跌幅
                    pre_close = df.iloc[-2]['close'] if len(df) > 1 else latest['close']
                    change = ((latest['close'] - pre_close) / pre_close * 100) if pre_close > 0 else 0
                    change_amount = latest['close'] - pre_close
                    
                    return {
                        'code': index_code,
                        'name': symbol,
                        'current': latest['close'],
                        'change': round(change, 2),
                        'change_amount': round(change_amount, 2),
                        'volume': latest.get('volume', 0),
                        'amount': latest.get('amount', 0)
                    }
            except Exception as e:
                # 如果快速接口失败,返回None而不是再尝试慢速接口
                print(f"⚠️ 获取指数 {index_code} 失败: {e}")
                return None
            
            return None
            
        except Exception as e:
            print(f"⚠️ 获取指数 {index_code} 异常: {e}")
            return None
    
    def get_sector_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取板块信息(简化版,只获取板块名称)
        
        :param stock_code: 股票代码
        :return: 板块信息字典
        """
        try:
            print(f"📊 获取 {stock_code} 板块信息...")
            
            # 获取股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            
            if stock_info.empty:
                print(f"⚠️ 无法获取股票基本信息")
                return {
                    'name': '未知',
                    'change': 0,
                    'leader': '',
                    'leader_change': 0,
                    'rank': 0
                }
            
            info_dict = dict(zip(stock_info['item'], stock_info['value']))
            sector_name = info_dict.get('行业', '未知')
            
            # 只返回板块名称,不获取涨跌幅数据
            # 原因: 板块行情接口(stock_board_industry_hist_em/spot_em)不稳定,
            #       经常超时失败,而板块涨跌幅对分析影响较小,因此简化处理
            sector_info = {
                'name': sector_name,
                'change': 0,  # 不获取涨跌幅,使用默认值
                'leader': '',
                'leader_change': 0,
                'rank': 0
            }
            
            print(f"✅ 板块信息获取成功: {sector_name}")
            return sector_info
            
        except Exception as e:
            print(f"⚠️ 获取板块信息异常: {e}")
            return {
                'name': '未知',
                'change': 0,
                'leader': '',
                'leader_change': 0,
                'rank': 0
            }
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """
        获取市场情绪指标
        
        :return: 市场情绪数据字典
        """
        try:
            print(f"📊 获取市场情绪数据...")
            
            # 获取涨停数据
            limit_up_count = 0
            try:
                limit_up_df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
                limit_up_count = len(limit_up_df) if not limit_up_df.empty else 0
            except Exception as e:
                print(f"⚠️ 获取涨停数据失败: {e}")
            
            # 获取跌停数据 (API名称可能已变更,尝试多个可能的名称)
            limit_down_count = 0
            try:
                # 尝试几个可能的API名称
                try:
                    limit_down_df = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime('%Y%m%d'))
                    limit_down_count = len(limit_down_df) if not limit_down_df.empty else 0
                except:
                    # 如果上面的API不存在,跳过跌停数据
                    pass
            except Exception as e:
                print(f"⚠️ 获取跌停数据失败: {e}")
            
            # 简化版本:使用上证和深证指数数据来判断市场情绪
            # 避免使用需要获取全部股票的慢速接口
            sentiment = {
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'up_count': 0,  # 简化版不统计
                'down_count': 0,  # 简化版不统计
                'up_down_ratio': 0,  # 简化版不统计
                'total_amount': 0  # 简化版不统计
            }
            
            print(f"✅ 市场情绪数据获取成功 (涨停:{limit_up_count}, 跌停:{limit_down_count})")
            return sentiment
            
        except Exception as e:
            print(f"⚠️ 获取市场情绪失败: {e}, 返回默认值")
            return {
                'limit_up_count': 0,
                'limit_down_count': 0,
                'up_count': 0,
                'down_count': 0,
                'up_down_ratio': 0,
                'total_amount': 0
            }
    
    def get_kline_data(self, stock_code: str, days: int = 20) -> pd.DataFrame:
        """
        获取日K线数据
        
        :param stock_code: 股票代码
        :param days: 天数
        :return: K线数据DataFrame
        """
        try:
            print(f"📊 获取 {stock_code} 最近{days}天的K线数据...")
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
            
            if df.empty:
                print(f"❌ 未获取到K线数据")
                return pd.DataFrame()
            
            # 只保留最近的days条记录
            df = df.tail(days)
            
            print(f"✅ K线数据获取成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"❌ 获取K线数据失败: {e}")
            return pd.DataFrame()
    
    def _get_stock_output_dir(self, stock_code: str) -> Path:
        """获取股票专属输出目录"""
        output_dir = Path('../data_output') / stock_code
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def _get_intraday_cache_path(self, stock_code: str, date: str) -> Path:
        """获取分时数据缓存文件路径"""
        return self._get_stock_output_dir(stock_code) / f"{stock_code}_{date}_intraday.csv"
    
    def _check_intraday_data_completeness(self, csv_file_path: str) -> bool:
        """
        检查分时数据文件的完整性
        
        :param csv_file_path: CSV文件路径
        :return: bool, True表示数据完整，False表示数据不完整
        """
        try:
            # 尝试多种编码方式读取CSV文件
            df = None
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'cp936']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                print(f"  ⚠️ 无法读取文件，尝试了所有编码方式")
                return False
            
            if df.empty or 'ticktime' not in df.columns:
                print(f"  ⚠️ 文件为空或缺少ticktime列")
                return False
            
            # 转换ticktime为datetime格式
            df['ticktime'] = pd.to_datetime(df['ticktime'])
            
            # 提取小时信息并去重
            hours = df['ticktime'].dt.hour.unique()
            
            # 检查是否包含完整的交易时间段：9、10、11、13、14、15点
            required_hours = {9, 10, 11, 13, 14, 15}
            actual_hours = set(hours)
            
            missing_hours = required_hours - actual_hours
            
            if missing_hours:
                print(f"  ⚠️ 缺少以下小时的数据: {sorted(missing_hours)}")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ⚠️ 检查文件完整性时出错: {e}")
            return False
    
    def _get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取指定日期范围内的交易日列表(使用缓存的交易日历)
        
        :param start_date: str, 起始日期，格式 'YYYYMMDD'
        :param end_date: str, 结束日期，格式 'YYYYMMDD'
        :return: list, 交易日列表，格式为 'YYYYMMDD'
        """
        calendar = self._get_trading_calendar()
        if calendar.empty:
            return []
        
        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        trading_dates = calendar[(calendar['trade_date'] >= start_date_dt) & 
                                 (calendar['trade_date'] <= end_date_dt)]['trade_date']
        return trading_dates.dt.strftime('%Y%m%d').tolist()
    
    def get_historical_intraday_with_cache(self, stock_code: str, days: int) -> pd.DataFrame:
        """
        获取历史分时数据（带缓存机制）
        
        :param stock_code: 股票代码
        :param days: 获取最近几天的数据
        :return: 分时数据DataFrame
        """
        try:
            print(f"📊 获取 {stock_code} 最近{days}天的历史分时数据...")
            
            # 确定市场代码
            if stock_code.startswith('688'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('83', '43', '87', '920')):
                symbol = f"bj{stock_code}"
            elif stock_code.startswith('60'):
                symbol = f"sh{stock_code}"
            elif stock_code.startswith(('00', '30')):
                symbol = f"sz{stock_code}"
            else:
                symbol = stock_code
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            # 获取交易日
            trading_dates = self._get_trading_dates(start_date, end_date)
            trading_dates = trading_dates[-days:]  # 只取最近days个交易日
            
            all_data = []
            
            for date in trading_dates:
                cache_path = self._get_intraday_cache_path(stock_code, date)
                
                # 检查缓存
                if cache_path.exists():
                    # 检查数据完整性
                    if self._check_intraday_data_completeness(str(cache_path)):
                        print(f"  ✅ 从缓存加载 {date} 数据")
                        daily_data = pd.read_csv(cache_path, encoding='utf-8-sig')
                        daily_data['ticktime'] = pd.to_datetime(daily_data['ticktime']).dt.tz_localize(None) if daily_data['ticktime'].dtype == 'object' else daily_data['ticktime']
                        all_data.append(daily_data)
                        continue
                    else:
                        print(f"  ⚠️ {date} 数据不完整，删除并重新获取")
                        os.remove(cache_path)
                
                # 从接口获取数据
                for attempt in range(self.max_retries):
                    try:
                        print(f"  📥 获取 {date} 数据...")
                        daily_data = ak.stock_intraday_sina(symbol=symbol, date=date)
                        
                        if not daily_data.empty:
                            daily_data['ticktime'] = pd.to_datetime(date + ' ' + daily_data['ticktime'])
                            daily_data.to_csv(cache_path, index=False, encoding='utf-8-sig')
                            print(f"  ✅ {date} 数据获取成功")
                            all_data.append(daily_data)
                            time.sleep(1)  # 避免请求过快
                            break
                    except Exception as e:
                        if attempt < self.max_retries - 1:
                            wait_time = self.retry_delay * (attempt + 1)
                            print(f"  ⚠️ 获取失败，{wait_time}秒后重试...")
                            time.sleep(wait_time)
                        else:
                            print(f"  ❌ {date} 数据获取失败: {e}")
            
            if not all_data:
                print(f"❌ 未获取到任何历史分时数据")
                return pd.DataFrame()
            
            # 合并所有数据
            result = pd.concat(all_data, ignore_index=True)
            result = result.sort_values('ticktime').reset_index(drop=True)
            print(f"✅ 历史分时数据获取完成，共 {len(result)} 条记录，涵盖 {len(all_data)} 个交易日")
            
            return result
            
        except Exception as e:
            print(f"❌ 获取历史分时数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_hourly_volume(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        计算每日每小时的量能分布
        
        :param df: 分时数据DataFrame
        :return: 量能统计字典 {日期: {时间段: 统计数据}}
        """
        if df.empty:
            return {}
        
        print(f"📊 计算量能分布...")
        
        date_period_stats = {}
        
        # 定义交易时间段
        trading_periods = [
            {'name': '09:25', 'start_hour': 9, 'start_minute': 25, 'end_hour': 9, 'end_minute': 25, 'is_single_time': True},
            {'name': '09:30-10:30', 'start_hour': 9, 'start_minute': 30, 'end_hour': 10, 'end_minute': 30},
            {'name': '10:30-11:30', 'start_hour': 10, 'start_minute': 30, 'end_hour': 11, 'end_minute': 30},
            {'name': '13:00-14:00', 'start_hour': 13, 'start_minute': 0, 'end_hour': 14, 'end_minute': 0},
            {'name': '14:00-15:00', 'start_hour': 14, 'start_minute': 0, 'end_hour': 15, 'end_minute': 0}
        ]
        
        # 确保ticktime是datetime类型
        df['ticktime'] = pd.to_datetime(df['ticktime'])
        df['date'] = df['ticktime'].dt.date
        df['hour'] = df['ticktime'].dt.hour
        df['minute'] = df['ticktime'].dt.minute
        
        # 计算量能
        df['volume_energy'] = df['price'] * df['volume']
        
        # 获取所有唯一的日期
        unique_dates = sorted(df['date'].unique())
        
        for date in unique_dates:
            date_data = df[df['date'] == date]
            date_period_stats[str(date)] = {}
            
            for period in trading_periods:
                period_name = period['name']
                
                # 筛选该时间段内的数据
                if period.get('is_single_time', False):
                    # 特殊处理单个时间点（如09:25）
                    period_data = date_data[
                        (date_data['hour'] == period['start_hour']) & 
                        (date_data['minute'] == period['start_minute'])
                    ]
                else:
                    # 处理时间段
                    period_data = date_data[
                        ((date_data['hour'] > period['start_hour']) | 
                         ((date_data['hour'] == period['start_hour']) & (date_data['minute'] >= period['start_minute']))) &
                        ((date_data['hour'] < period['end_hour']) | 
                         ((date_data['hour'] == period['end_hour']) & (date_data['minute'] < period['end_minute'])))
                    ]
                
                if len(period_data) == 0:
                    continue
                
                # 分别统计U、D、E的量能和成交量
                u_data = period_data[period_data['kind'] == 'U']
                d_data = period_data[period_data['kind'] == 'D']
                e_data = period_data[period_data['kind'] == 'E']
                
                u_volume = u_data['volume_energy'].sum() if len(u_data) > 0 else 0
                d_volume = d_data['volume_energy'].sum() if len(d_data) > 0 else 0
                e_volume = e_data['volume_energy'].sum() if len(e_data) > 0 else 0
                
                # 计算成交量（股数）
                u_volume_count = u_data['volume'].sum() if len(u_data) > 0 else 0
                d_volume_count = d_data['volume'].sum() if len(d_data) > 0 else 0
                e_volume_count = e_data['volume'].sum() if len(e_data) > 0 else 0
                total_volume_count = u_volume_count + d_volume_count + e_volume_count
                
                total_volume = u_volume + d_volume + e_volume
                
                # 计算占比
                u_ratio = u_volume / total_volume if total_volume > 0 else 0
                d_ratio = d_volume / total_volume if total_volume > 0 else 0
                e_ratio = e_volume / total_volume if total_volume > 0 else 0
                
                # 计算U/D比例
                if period.get('is_single_time', False):
                    ud_ratio = 'NA'
                else:
                    ud_ratio = u_volume / d_volume if d_volume > 0 else (u_volume if u_volume > 0 else 0)
                
                date_period_stats[str(date)][period_name] = {
                    'total_volume': total_volume,
                    'total_volume_count': total_volume_count,
                    'u_volume': u_volume,
                    'd_volume': d_volume,
                    'e_volume': e_volume,
                    'u_ratio': u_ratio,
                    'd_ratio': d_ratio,
                    'e_ratio': e_ratio,
                    'ud_ratio': ud_ratio,
                    'transaction_count': len(period_data),
                    'period_name': period_name
                }
        
        print(f"✅ 量能分布计算完成，共 {len(date_period_stats)} 个交易日")
        return date_period_stats

