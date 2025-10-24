"""
日内交易数据获取模块
负责获取实时行情、分时数据、盘口数据、大盘指数等
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import time
from functools import wraps


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
    
    def get_realtime_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票实时行情（带重试机制）
        
        :param stock_code: 股票代码
        :return: 实时行情数据字典
        """
        print(f"📊 获取 {stock_code} 实时行情...")
        
        # 使用重试机制
        for attempt in range(self.max_retries):
            try:
                # 获取实时行情
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
                
                print(f"✅ 实时行情获取成功: {quote['stock_name']} 当前价 {quote['current_price']}")
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
        获取今日分时数据
        
        :param stock_code: 股票代码
        :return: 分时数据DataFrame
        """
        try:
            print(f"📈 获取 {stock_code} 今日分时数据...")
            
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
            
            # 获取今日日期
            today = datetime.now().strftime('%Y%m%d')
            
            # 获取分时数据
            df = ak.stock_intraday_sina(symbol=symbol, date=today)
            
            if df.empty:
                print(f"⚠️ 今日暂无分时数据")
                return pd.DataFrame()
            
            print(f"✅ 分时数据获取成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"❌ 获取分时数据失败: {e}")
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
            
            # 使用实时行情接口获取盘口数据
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]
            
            if stock_data.empty:
                return None
            
            row = stock_data.iloc[0]
            
            order_book = {
                'bid': [
                    {'price': row.get('买一', 0), 'volume': row.get('买一量', 0)},
                    {'price': row.get('买二', 0), 'volume': row.get('买二量', 0)},
                    {'price': row.get('买三', 0), 'volume': row.get('买三量', 0)},
                    {'price': row.get('买四', 0), 'volume': row.get('买四量', 0)},
                    {'price': row.get('买五', 0), 'volume': row.get('买五量', 0)},
                ],
                'ask': [
                    {'price': row.get('卖一', 0), 'volume': row.get('卖一量', 0)},
                    {'price': row.get('卖二', 0), 'volume': row.get('卖二量', 0)},
                    {'price': row.get('卖三', 0), 'volume': row.get('卖三量', 0)},
                    {'price': row.get('卖四', 0), 'volume': row.get('卖四量', 0)},
                    {'price': row.get('卖五', 0), 'volume': row.get('卖五量', 0)},
                ]
            }
            
            print(f"✅ 盘口数据获取成功")
            return order_book
            
        except Exception as e:
            print(f"❌ 获取盘口数据失败: {e}")
            return None
    
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
        """获取指数实时数据"""
        try:
            # 使用指数实时行情接口
            if index_code == '000001':
                # 上证指数特殊处理
                df = ak.stock_zh_index_spot_em()
                index_data = df[df['代码'] == 'sh000001']
            else:
                df = ak.stock_zh_index_spot_em()
                # 尝试匹配指数代码
                index_data = df[df['代码'].str.contains(index_code)]
            
            if index_data.empty:
                return None
            
            row = index_data.iloc[0]
            return {
                'code': index_code,
                'name': row['名称'],
                'current': row['最新价'],
                'change': row['涨跌幅'],
                'change_amount': row['涨跌额'],
                'volume': row['成交量'],
                'amount': row['成交额']
            }
        except Exception as e:
            print(f"⚠️ 获取指数 {index_code} 失败: {e}")
            return None
    
    def get_sector_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取板块信息
        
        :param stock_code: 股票代码
        :return: 板块信息字典
        """
        try:
            print(f"📊 获取 {stock_code} 板块信息...")
            
            # 获取股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            
            if stock_info.empty:
                return None
            
            info_dict = dict(zip(stock_info['item'], stock_info['value']))
            
            sector_name = info_dict.get('行业', '未知')
            
            # 获取板块实时数据
            try:
                sector_df = ak.stock_board_industry_spot_em()
                sector_data = sector_df[sector_df['板块名称'] == sector_name]
                
                if not sector_data.empty:
                    row = sector_data.iloc[0]
                    sector_info = {
                        'name': sector_name,
                        'change': row.get('涨跌幅', 0),
                        'leader': row.get('领涨股票', ''),
                        'leader_change': row.get('领涨股票涨跌幅', 0),
                        'rank': row.get('排名', 0)
                    }
                else:
                    sector_info = {
                        'name': sector_name,
                        'change': 0,
                        'leader': '',
                        'leader_change': 0,
                        'rank': 0
                    }
            except Exception as e:
                print(f"⚠️ 获取板块行情失败: {e}")
                sector_info = {
                    'name': sector_name,
                    'change': 0,
                    'leader': '',
                    'leader_change': 0,
                    'rank': 0
                }
            
            print(f"✅ 板块信息获取成功: {sector_name}")
            return sector_info
            
        except Exception as e:
            print(f"❌ 获取板块信息失败: {e}")
            return None
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """
        获取市场情绪指标
        
        :return: 市场情绪数据字典
        """
        try:
            print(f"📊 获取市场情绪数据...")
            
            # 获取涨跌停数据
            limit_up_df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
            limit_down_df = ak.stock_fb_pool_em(date=datetime.now().strftime('%Y%m%d'))
            
            # 获取两市成交额
            market_df = ak.stock_zh_a_spot_em()
            total_amount = market_df['成交额'].sum() / 100000000  # 转换为亿元
            
            # 计算涨跌家数
            up_count = len(market_df[market_df['涨跌幅'] > 0])
            down_count = len(market_df[market_df['涨跌幅'] < 0])
            
            sentiment = {
                'limit_up_count': len(limit_up_df),
                'limit_down_count': len(limit_down_df),
                'up_count': up_count,
                'down_count': down_count,
                'up_down_ratio': round(up_count / down_count, 2) if down_count > 0 else 0,
                'total_amount': round(total_amount, 2)
            }
            
            print(f"✅ 市场情绪数据获取成功")
            return sentiment
            
        except Exception as e:
            print(f"❌ 获取市场情绪失败: {e}")
            return None
    
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

