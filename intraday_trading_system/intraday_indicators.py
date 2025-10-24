"""
技术指标计算模块
负责计算各类技术指标：EMA、MACD、RSI、KDJ、BOLL等
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        计算指数移动平均线(EMA)
        
        :param data: 价格序列
        :param period: 周期
        :return: EMA序列
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        计算MACD指标
        
        :param data: 价格序列
        :param fast: 快线周期
        :param slow: 慢线周期
        :param signal: 信号线周期
        :return: 包含DIF、DEA、MACD的字典
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2
        
        return {
            'DIF': dif,
            'DEA': dea,
            'MACD': macd
        }
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        :param data: 价格序列
        :param period: 周期
        :return: RSI序列
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, pd.Series]:
        """
        计算KDJ指标
        
        :param df: 包含最高价、最低价、收盘价的DataFrame
        :param n: RSV周期
        :param m1: K值周期
        :param m2: D值周期
        :return: 包含K、D、J的字典
        """
        low_list = df['最低'].rolling(window=n, min_periods=1).min()
        high_list = df['最高'].rolling(window=n, min_periods=1).max()
        
        rsv = (df['收盘'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {
            'K': k,
            'D': d,
            'J': j
        }
    
    @staticmethod
    def calculate_boll(data: pd.Series, period: int = 20, std_multiplier: float = 2) -> Dict[str, pd.Series]:
        """
        计算布林带指标
        
        :param data: 价格序列
        :param period: 周期
        :param std_multiplier: 标准差倍数
        :return: 包含上轨、中轨、下轨的字典
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper = middle + std_multiplier * std
        lower = middle - std_multiplier * std
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """
        计算简单移动平均线(MA)
        
        :param data: 价格序列
        :param period: 周期
        :return: MA序列
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_volume_ma(data: pd.Series, period: int) -> pd.Series:
        """
        计算成交量移动平均
        
        :param data: 成交量序列
        :param period: 周期
        :return: 成交量均线
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def analyze_intraday_data(df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析分时数据，计算各种指标
        
        :param df: 分时数据DataFrame，应包含price、volume等列
        :return: 指标分析结果字典
        """
        if df.empty:
            return {}
        
        result = {}
        
        try:
            # 确保数据按时间排序
            df = df.sort_values('ticktime').reset_index(drop=True)
            
            # 使用price列计算技术指标
            if 'price' in df.columns:
                prices = df['price']
                
                # 计算EMA
                result['ema5'] = TechnicalIndicators.calculate_ema(prices, 5).iloc[-1] if len(prices) >= 5 else None
                result['ema10'] = TechnicalIndicators.calculate_ema(prices, 10).iloc[-1] if len(prices) >= 10 else None
                result['ema20'] = TechnicalIndicators.calculate_ema(prices, 20).iloc[-1] if len(prices) >= 20 else None
                
                # 计算MACD
                if len(prices) >= 26:
                    macd_data = TechnicalIndicators.calculate_macd(prices)
                    result['macd_dif'] = macd_data['DIF'].iloc[-1]
                    result['macd_dea'] = macd_data['DEA'].iloc[-1]
                    result['macd_bar'] = macd_data['MACD'].iloc[-1]
                
                # 计算RSI
                if len(prices) >= 6:
                    result['rsi6'] = TechnicalIndicators.calculate_rsi(prices, 6).iloc[-1]
                if len(prices) >= 12:
                    result['rsi12'] = TechnicalIndicators.calculate_rsi(prices, 12).iloc[-1]
                if len(prices) >= 24:
                    result['rsi24'] = TechnicalIndicators.calculate_rsi(prices, 24).iloc[-1]
            
            # 成交量分析
            if 'volume' in df.columns:
                result['avg_volume'] = df['volume'].mean()
                result['total_volume'] = df['volume'].sum()
                
                # 最近10笔成交量趋势
                if len(df) >= 10:
                    recent_volumes = df['volume'].tail(10).tolist()
                    result['recent_volume_trend'] = recent_volumes
            
            # 价格序列（最近10个）
            if 'price' in df.columns and len(df) >= 10:
                result['recent_prices'] = df['price'].tail(10).tolist()
            
        except Exception as e:
            print(f"⚠️ 分析分时数据时出错: {e}")
        
        return result
    
    @staticmethod
    def analyze_kline_data(df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析K线数据，计算各种指标
        
        :param df: K线数据DataFrame
        :return: 指标分析结果字典
        """
        if df.empty:
            return {}
        
        result = {}
        
        try:
            # 确保数据按日期排序
            df = df.sort_values('日期').reset_index(drop=True)
            
            closes = df['收盘']
            
            # 计算MA均线
            result['ma5'] = TechnicalIndicators.calculate_ma(closes, 5).iloc[-1] if len(closes) >= 5 else None
            result['ma10'] = TechnicalIndicators.calculate_ma(closes, 10).iloc[-1] if len(closes) >= 10 else None
            result['ma20'] = TechnicalIndicators.calculate_ma(closes, 20).iloc[-1] if len(closes) >= 20 else None
            result['ma60'] = TechnicalIndicators.calculate_ma(closes, 60).iloc[-1] if len(closes) >= 60 else None
            
            # 计算EMA
            result['ema5'] = TechnicalIndicators.calculate_ema(closes, 5).iloc[-1] if len(closes) >= 5 else None
            result['ema10'] = TechnicalIndicators.calculate_ema(closes, 10).iloc[-1] if len(closes) >= 10 else None
            result['ema20'] = TechnicalIndicators.calculate_ema(closes, 20).iloc[-1] if len(closes) >= 20 else None
            result['ema60'] = TechnicalIndicators.calculate_ema(closes, 60).iloc[-1] if len(closes) >= 60 else None
            
            # 计算MACD
            if len(closes) >= 26:
                macd_data = TechnicalIndicators.calculate_macd(closes)
                result['macd_dif'] = macd_data['DIF'].iloc[-1]
                result['macd_dea'] = macd_data['DEA'].iloc[-1]
                result['macd_bar'] = macd_data['MACD'].iloc[-1]
                
                # MACD序列（最近10天）
                result['macd_series'] = macd_data['MACD'].tail(10).tolist()
            
            # 计算RSI
            if len(closes) >= 6:
                result['rsi6'] = TechnicalIndicators.calculate_rsi(closes, 6).iloc[-1]
                result['rsi6_series'] = TechnicalIndicators.calculate_rsi(closes, 6).tail(10).tolist()
            
            if len(closes) >= 12:
                result['rsi12'] = TechnicalIndicators.calculate_rsi(closes, 12).iloc[-1]
                result['rsi12_series'] = TechnicalIndicators.calculate_rsi(closes, 12).tail(10).tolist()
            
            if len(closes) >= 14:
                result['rsi14'] = TechnicalIndicators.calculate_rsi(closes, 14).iloc[-1]
                result['rsi14_series'] = TechnicalIndicators.calculate_rsi(closes, 14).tail(10).tolist()
            
            # 计算KDJ
            if len(df) >= 9:
                kdj_data = TechnicalIndicators.calculate_kdj(df, 9, 3, 3)
                result['kdj_k'] = kdj_data['K'].iloc[-1]
                result['kdj_d'] = kdj_data['D'].iloc[-1]
                result['kdj_j'] = kdj_data['J'].iloc[-1]
            
            # 计算布林带
            if len(closes) >= 20:
                boll_data = TechnicalIndicators.calculate_boll(closes, 20, 2)
                result['boll_upper'] = boll_data['upper'].iloc[-1]
                result['boll_middle'] = boll_data['middle'].iloc[-1]
                result['boll_lower'] = boll_data['lower'].iloc[-1]
            
            # 成交量均线
            if '成交量' in df.columns:
                volumes = df['成交量']
                result['vol_ma5'] = TechnicalIndicators.calculate_volume_ma(volumes, 5).iloc[-1] if len(volumes) >= 5 else None
                result['vol_ma10'] = TechnicalIndicators.calculate_volume_ma(volumes, 10).iloc[-1] if len(volumes) >= 10 else None
            
        except Exception as e:
            print(f"⚠️ 分析K线数据时出错: {e}")
        
        return result

