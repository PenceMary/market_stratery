"""
提示词构建模块
负责根据获取的数据构建发送给大模型的提示词
"""

from datetime import datetime
from typing import Dict, Any, List
import json


class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self, template_file: str = 'a_stock_trading_prompt_template.txt'):
        """
        初始化提示词构建器
        
        :param template_file: 提示词模板文件路径
        """
        self.template_file = template_file
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """加载提示词模板"""
        try:
            with open(self.template_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ 模板文件 {self.template_file} 不存在，使用默认模板")
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """获取默认提示词模板"""
        return """======== A股日内交易分析 ========

当前时间：{current_time}
距离开盘：{elapsed_minutes} 分钟

=== 个股行情 ===
股票代码：{stock_code}
股票名称：{stock_name}
当前价格：{current_price} 元
涨跌幅：{price_change}%
成交量：{volume}
换手率：{turnover_rate}%
量比：{volume_ratio}

=== 技术指标 ===
{technical_indicators}

=== 盘口数据 ===
{order_book}

=== 大盘状况 ===
{market_indices}

=== 板块情况 ===
{sector_info}

=== 市场情绪 ===
{market_sentiment}

=== 分析要求 ===
请基于以上数据，给出明确的交易建议：
1. 当前趋势判断（多头/空头/震荡）
2. 关键支撑位和压力位
3. 操作建议（买入/卖出/观望）
4. 建议买入/卖出价位
5. 止损位和止盈位
6. 风险提示
"""
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """
        构建完整的提示词
        
        :param data: 包含所有数据的字典
        :return: 构建好的提示词字符串
        """
        current_time = datetime.now()
        
        # 计算距离开盘的时间
        elapsed_minutes = self._calculate_elapsed_minutes(current_time)
        
        # 基础信息
        quote = data.get('quote', {})
        
        # 构建技术指标部分
        technical_indicators = self._build_technical_indicators(data)
        
        # 构建盘口数据部分
        order_book = self._build_order_book(data.get('order_book', {}))
        
        # 构建大盘指数部分
        market_indices = self._build_market_indices(data.get('market_indices', {}))
        
        # 构建板块信息部分
        sector_info = self._build_sector_info(data.get('sector_info', {}))
        
        # 构建市场情绪部分
        market_sentiment = self._build_market_sentiment(data.get('market_sentiment', {}))
        
        # 构建分时数据部分
        intraday_analysis = self._build_intraday_analysis(data)
        
        # 构建K线数据部分
        kline_analysis = self._build_kline_analysis(data)
        
        # 填充模板
        prompt = f"""======== A股日内交易分析 ========

⏰ 当前时间：{current_time.strftime('%Y年%m月%d日 %H:%M:%S')}
📅 星期：{self._get_weekday_cn(current_time)}
⏱️ 距离开盘：{elapsed_minutes} 分钟

---

=== 标的股票详细数据 ===

【基本信息】
股票代码：{quote.get('stock_code', 'N/A')}
股票名称：{quote.get('stock_name', 'N/A')}
当前价格：{quote.get('current_price', 0):.2f} 元
今日开盘：{quote.get('open_price', 0):.2f} 元
最高价：{quote.get('high_price', 0):.2f} 元
最低价：{quote.get('low_price', 0):.2f} 元
涨跌幅：{quote.get('price_change', 0):.2f}%
涨停价：{quote.get('limit_up_price', 0):.2f} 元
跌停价：{quote.get('limit_down_price', 0):.2f} 元
振幅：{quote.get('amplitude', 0):.2f}%

【成交情况】
成交量：{quote.get('volume', 0)} 手
成交额：{quote.get('amount', 0):.2f} 元
换手率：{quote.get('turnover_rate', 0):.2f}%
量比：{quote.get('volume_ratio', 0):.2f}

{technical_indicators}

{intraday_analysis}

{order_book}

{kline_analysis}

---

=== 大盘整体状态 ===

{market_indices}

---

=== 板块联动 ===

{sector_info}

---

=== 市场情绪指标 ===

{market_sentiment}

---

=== 分析任务 ===

请基于以上实时数据，从以下维度进行深度分析并给出明确的交易决策：

**1. 技术面分析**
   - 当前趋势判断（多头/空头/震荡）
   - 价格所处位置（相对支撑位和压力位）
   - 技术指标多空信号
   - 是否存在背离

**2. 量能分析**
   - 量价配合关系
   - 资金流向判断
   - 大单行为分析

**3. 盘口分析**
   - 买卖力量对比
   - 是否存在主力动作

**4. 市场环境**
   - 大盘走势影响
   - 板块联动效应
   - 市场情绪评估

**5. 交易决策（重点）**
   ⚠️ 请给出明确、具体的交易建议：
   
   📊 **操作方向**：买入/卖出/观望（必须明确选择一个）
   
   💰 **建议价位**：
   - 如果买入：建议买入价格区间
   - 如果卖出：建议卖出价格区间
   - 如果观望：观察等待的关键价位
   
   🎯 **仓位管理**：建议操作仓位比例（轻仓/半仓/重仓）
   
   🛡️ **风险控制**：
   - 止损位（必须给出具体价格）
   - 止盈位（必须给出具体价格）
   
   ⏰ **时机把握**：
   - 最佳入场/出场时间段
   - 需要等待的确认信号
   
   ⚠️ **风险提示**：当前操作的主要风险点

请以专业量化交易员的角度，给出精准、可执行的交易方案。

---
"""
        
        return prompt
    
    def _calculate_elapsed_minutes(self, current_time: datetime) -> int:
        """计算距离开盘的分钟数"""
        hour = current_time.hour
        minute = current_time.minute
        
        # 上午交易时段 09:30-11:30
        if 9 <= hour < 11 or (hour == 11 and minute <= 30):
            if hour == 9 and minute < 30:
                return -(30 - minute)  # 还未开盘
            elif hour == 9:
                return minute - 30
            else:
                return (hour - 9) * 60 + minute - 30
        
        # 下午交易时段 13:00-15:00
        elif 13 <= hour < 15:
            morning_minutes = 120  # 上午120分钟
            afternoon_minutes = (hour - 13) * 60 + minute
            return morning_minutes + afternoon_minutes
        
        # 中午休息
        elif 11 < hour < 13 or (hour == 11 and minute > 30):
            return 120  # 上午已交易120分钟
        
        # 收盘后
        elif hour >= 15:
            return 240  # 全天240分钟
        
        # 开盘前
        else:
            open_time = current_time.replace(hour=9, minute=30, second=0)
            minutes_to_open = int((open_time - current_time).total_seconds() / 60)
            return -minutes_to_open
    
    def _get_weekday_cn(self, dt: datetime) -> str:
        """获取中文星期"""
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[dt.weekday()]
    
    def _build_technical_indicators(self, data: Dict[str, Any]) -> str:
        """构建技术指标部分"""
        intraday_indicators = data.get('intraday_indicators', {})
        kline_indicators = data.get('kline_indicators', {})
        
        text = "【技术指标 - 当前值】\n"
        
        # 从K线数据获取的指标
        if kline_indicators:
            text += f"EMA5 = {kline_indicators.get('ema5', 'N/A')}\n"
            text += f"EMA10 = {kline_indicators.get('ema10', 'N/A')}\n"
            text += f"EMA20 = {kline_indicators.get('ema20', 'N/A')}\n"
            text += f"EMA60 = {kline_indicators.get('ema60', 'N/A')}\n"
            text += f"MACD(DIF) = {kline_indicators.get('macd_dif', 'N/A')}\n"
            text += f"MACD(DEA) = {kline_indicators.get('macd_dea', 'N/A')}\n"
            text += f"MACD(柱) = {kline_indicators.get('macd_bar', 'N/A')}\n"
            text += f"RSI(6) = {kline_indicators.get('rsi6', 'N/A')}\n"
            text += f"RSI(12) = {kline_indicators.get('rsi12', 'N/A')}\n"
            text += f"KDJ(K) = {kline_indicators.get('kdj_k', 'N/A')}\n"
            text += f"KDJ(D) = {kline_indicators.get('kdj_d', 'N/A')}\n"
            text += f"KDJ(J) = {kline_indicators.get('kdj_j', 'N/A')}\n"
            text += f"BOLL上轨 = {kline_indicators.get('boll_upper', 'N/A')}\n"
            text += f"BOLL中轨 = {kline_indicators.get('boll_middle', 'N/A')}\n"
            text += f"BOLL下轨 = {kline_indicators.get('boll_lower', 'N/A')}\n"
        
        return text
    
    def _build_intraday_analysis(self, data: Dict[str, Any]) -> str:
        """构建分时数据分析部分"""
        intraday_indicators = data.get('intraday_indicators', {})
        
        if not intraday_indicators:
            return ""
        
        text = "\n【分时数据分析】\n"
        
        # 最近价格序列
        recent_prices = intraday_indicators.get('recent_prices', [])
        if recent_prices:
            prices_str = ', '.join([f'{p:.2f}' for p in recent_prices])
            text += f"最近价格序列（最旧→最新）：[{prices_str}]\n"
        
        # 最近成交量序列
        recent_volumes = intraday_indicators.get('recent_volume_trend', [])
        if recent_volumes:
            volumes_str = ', '.join([f'{int(v)}' for v in recent_volumes])
            text += f"最近成交量序列（手）：[{volumes_str}]\n"
        
        # 分时均线
        if intraday_indicators.get('ema5'):
            text += f"分时EMA5 = {intraday_indicators['ema5']:.2f}\n"
        if intraday_indicators.get('ema10'):
            text += f"分时EMA10 = {intraday_indicators['ema10']:.2f}\n"
        if intraday_indicators.get('ema20'):
            text += f"分时EMA20 = {intraday_indicators['ema20']:.2f}\n"
        
        # 分时MACD
        if intraday_indicators.get('macd_dif'):
            text += f"分时MACD(DIF) = {intraday_indicators['macd_dif']:.4f}\n"
            text += f"分时MACD(DEA) = {intraday_indicators['macd_dea']:.4f}\n"
            text += f"分时MACD(柱) = {intraday_indicators['macd_bar']:.4f}\n"
        
        return text
    
    def _build_kline_analysis(self, data: Dict[str, Any]) -> str:
        """构建K线数据分析部分"""
        kline_indicators = data.get('kline_indicators', {})
        
        if not kline_indicators:
            return ""
        
        text = "\n【日线级别背景】\n"
        
        text += f"5日均线 = {kline_indicators.get('ma5', 'N/A')}\n"
        text += f"10日均线 = {kline_indicators.get('ma10', 'N/A')}\n"
        text += f"20日均线 = {kline_indicators.get('ma20', 'N/A')}\n"
        text += f"60日均线 = {kline_indicators.get('ma60', 'N/A')}\n\n"
        
        text += f"5日均量 = {kline_indicators.get('vol_ma5', 'N/A')}\n"
        text += f"10日均量 = {kline_indicators.get('vol_ma10', 'N/A')}\n\n"
        
        # MACD序列
        macd_series = kline_indicators.get('macd_series', [])
        if macd_series:
            macd_str = ', '.join([f'{m:.4f}' for m in macd_series])
            text += f"日线MACD序列（最近10天）：[{macd_str}]\n"
        
        # RSI序列
        rsi6_series = kline_indicators.get('rsi6_series', [])
        if rsi6_series:
            rsi_str = ', '.join([f'{r:.2f}' for r in rsi6_series])
            text += f"日线RSI(6)序列：[{rsi_str}]\n"
        
        rsi12_series = kline_indicators.get('rsi12_series', [])
        if rsi12_series:
            rsi_str = ', '.join([f'{r:.2f}' for r in rsi12_series])
            text += f"日线RSI(12)序列：[{rsi_str}]\n"
        
        return text
    
    def _build_order_book(self, order_book: Dict[str, Any]) -> str:
        """构建盘口数据部分"""
        if not order_book:
            return ""
        
        text = "【盘口数据（五档）】\n"
        
        # 卖盘
        asks = order_book.get('ask', [])
        for i, ask in enumerate(asks[:5], 1):
            text += f"卖{['一', '二', '三', '四', '五'][i-1]}：{ask.get('price', 0):.2f} 元 × {int(ask.get('volume', 0))} 手\n"
        
        text += "\n"
        
        # 买盘
        bids = order_book.get('bid', [])
        for i, bid in enumerate(bids[:5], 1):
            text += f"买{['一', '二', '三', '四', '五'][i-1]}：{bid.get('price', 0):.2f} 元 × {int(bid.get('volume', 0))} 手\n"
        
        # 买卖力道比
        if bids and asks:
            bid_total = sum([b.get('volume', 0) for b in bids[:5]])
            ask_total = sum([a.get('volume', 0) for a in asks[:5]])
            if ask_total > 0:
                strength_ratio = bid_total / ask_total
                text += f"\n买卖力道比 = {strength_ratio:.2f}\n"
        
        return text
    
    def _build_market_indices(self, indices: Dict[str, Any]) -> str:
        """构建大盘指数部分"""
        if not indices:
            return "暂无大盘指数数据"
        
        text = ""
        for name, data in indices.items():
            if data:
                text += f"【{data.get('name', name)}】\n"
                text += f"当前点位 = {data.get('current', 0):.2f}\n"
                text += f"涨跌幅 = {data.get('change', 0):.2f}%\n"
                text += f"成交额 = {data.get('amount', 0):.2f} 元\n\n"
        
        return text if text else "暂无大盘指数数据"
    
    def _build_sector_info(self, sector: Dict[str, Any]) -> str:
        """构建板块信息部分"""
        if not sector:
            return "暂无板块信息"
        
        text = f"所属板块：{sector.get('name', 'N/A')}\n"
        text += f"板块涨跌幅 = {sector.get('change', 0):.2f}%\n"
        
        if sector.get('leader'):
            text += f"板块领涨股：{sector.get('leader', 'N/A')} ({sector.get('leader_change', 0):.2f}%)\n"
        
        if sector.get('rank'):
            text += f"板块排名 = {sector.get('rank', 0)}\n"
        
        return text
    
    def _build_market_sentiment(self, sentiment: Dict[str, Any]) -> str:
        """构建市场情绪部分"""
        if not sentiment:
            return "暂无市场情绪数据"
        
        text = f"涨停家数 = {sentiment.get('limit_up_count', 0)}\n"
        text += f"跌停家数 = {sentiment.get('limit_down_count', 0)}\n"
        text += f"上涨家数 = {sentiment.get('up_count', 0)}\n"
        text += f"下跌家数 = {sentiment.get('down_count', 0)}\n"
        text += f"涨跌比 = {sentiment.get('up_down_ratio', 0):.2f}\n"
        text += f"两市成交额 = {sentiment.get('total_amount', 0):.2f} 亿元\n"
        
        return text

