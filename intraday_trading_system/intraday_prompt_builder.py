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
距离开盘：{elapsed_minutes} 分钟(负数为未开盘-距离开盘倒计时，正数为已开盘时长)

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
        """构建分析提示词"""
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
        
        # 构建资金流向部分
        fund_flow = self._build_fund_flow(data.get('fund_flow', {}))
        
        # 构建分时数据部分
        intraday_analysis = self._build_intraday_analysis(data)
        
        # 构建K线数据部分
        kline_analysis = self._build_kline_analysis(data)
        
        # 构建量能分析部分
        hourly_volume = self._build_hourly_volume(data.get('hourly_volume_stats', {}))
        
        # 填充模板
        prompt = f"""======== A股日内交易分析 ========

⏰ 当前时间：{current_time.strftime('%Y年%m月%d日 %H:%M:%S')}
📅 星期：{self._get_weekday_cn(current_time)}
⏱️ 距离开盘：{elapsed_minutes} 分钟(负数为未开盘-距离开盘倒计时，正数为已开盘时长)

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

{technical_indicators}

{intraday_analysis}

{order_book}

{kline_analysis}

{hourly_volume}

---

=== 大盘整体状态 ===

{market_indices}

---

=== 市场情绪指标 ===

{market_sentiment}

---

=== 资金流向分析 ===

{fund_flow}

---

=== 分析任务 ===

        请基于以上实时数据，从以下维度进行深度分析并尽可能地使用推理来给出明确的交易决策：
        注意：A股交易策略为T+1（当日买入次日方可卖出），请在交易建议中充分考虑该约束。但是如果账户中有股票仓位，可以日内做T，实现高抛低吸。请同时考虑两种情况。

**1. 技术面分析**
   - 当前趋势判断（多头/空头/震荡）
   - 价格所处位置（相对支撑位和压力位）
   - 技术指标多空信号（EMA、MACD、RSI、KDJ、BOLL）
   - 是否存在背离

**2. 量能分析**
   - 量价配合关系
   - OBV能量潮趋势（是否与价格同步）
   - VR成交量变异率（市场活跃度评估）
   - 资金流向判断（主力、超大单、大单行为）
   - 连续流入/流出天数分析

**3. 波动率分析**
   - ATR平均真实波幅（用于止损设置参考）
   - 历史波动率水平（市场风险评估）
   - 当前波动率是否适合交易

**4. 资金流向分析**
   - 主力资金净流入/流出情况
   - 超大单与大单的配合
   - 散户行为（小单流向）
   - 近5日资金累计情况

**5. 盘口分析**
   - 买卖力量对比
   - 是否存在主力动作

**6. 市场环境**
   - 大盘走势影响
   - 板块联动效应
   - 市场情绪评估

**7. 交易决策（重点）**
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
            
            # 成交量指标
            text += f"\n【成交量指标】\n"
            obv = kline_indicators.get('obv', None)
            if obv is not None:
                text += f"OBV能量潮 = {obv:.0f}\n"
                obv_ma5 = kline_indicators.get('obv_ma5', None)
                obv_ma10 = kline_indicators.get('obv_ma10', None)
                if obv_ma5:
                    text += f"OBV-MA5 = {obv_ma5:.0f}\n"
                if obv_ma10:
                    text += f"OBV-MA10 = {obv_ma10:.0f}\n"
            
            vr = kline_indicators.get('vr', None)
            if vr is not None:
                text += f"VR成交量变异率 = {vr:.2f}\n"
                # VR解读提示
                if vr < 70:
                    text += f"  (VR<70，成交量极度萎缩，市场低迷)\n"
                elif vr < 150:
                    text += f"  (VR在正常区间，市场交投平稳)\n"
                elif vr < 450:
                    text += f"  (VR>150，成交量放大，市场活跃)\n"
                else:
                    text += f"  (VR>450，成交量过度放大，警惕反转)\n"
            
            # 波动率指标
            text += f"\n【波动率指标】\n"
            atr = kline_indicators.get('atr', None)
            if atr is not None:
                text += f"ATR平均真实波幅 = {atr:.4f}\n"
                atr_percent = kline_indicators.get('atr_percent', None)
                if atr_percent:
                    text += f"ATR百分比 = {atr_percent:.2f}% (相对当前价格的波动幅度)\n"
            
            hv = kline_indicators.get('historical_volatility', None)
            if hv is not None:
                text += f"历史波动率(20日年化) = {hv:.2f}%\n"
                # 波动率解读
                if hv < 20:
                    text += f"  (低波动，市场平稳)\n"
                elif hv < 40:
                    text += f"  (中等波动，正常波动水平)\n"
                else:
                    text += f"  (高波动，市场剧烈波动)\n"
        
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
        
        # 卖盘 (API返回的是股数，需转换为手数：1手=100股)
        asks = order_book.get('ask', [])
        for i, ask in enumerate(asks[:5], 1):
            volume_shares = int(ask.get('volume', 0))
            volume_hands = volume_shares // 100  # 转换为手数
            text += f"卖{['一', '二', '三', '四', '五'][i-1]}：{ask.get('price', 0):.2f} 元 × {volume_hands} 手 ({volume_shares} 股)\n"
        
        text += "\n"
        
        # 买盘 (API返回的是股数，需转换为手数：1手=100股)
        bids = order_book.get('bid', [])
        for i, bid in enumerate(bids[:5], 1):
            volume_shares = int(bid.get('volume', 0))
            volume_hands = volume_shares // 100  # 转换为手数
            text += f"买{['一', '二', '三', '四', '五'][i-1]}：{bid.get('price', 0):.2f} 元 × {volume_hands} 手 ({volume_shares} 股)\n"
        
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
                text += f"成交额 = {data.get('amount', 0):.0f} 元\n\n"
        
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
        # text += f"上涨家数 = {sentiment.get('up_count', 0)}\n"
        # text += f"下跌家数 = {sentiment.get('down_count', 0)}\n"
        # text += f"涨跌比 = {sentiment.get('up_down_ratio', 0):.2f}\n"
        text += f"两市成交额 = {sentiment.get('total_amount', 0):.0f} 亿元\n\n"
        
        return text
    
    def _build_fund_flow(self, fund_flow: Dict[str, Any]) -> str:
        """构建资金流向部分"""
        if not fund_flow or fund_flow.get('main_net_inflow', 0) == 0:
            return "暂无资金流向数据"
        
        text = f"【资金流向数据】\n"
        text += f"数据日期：{fund_flow.get('date', 'N/A')}\n\n"
        
        # 主力资金
        main_inflow = fund_flow.get('main_net_inflow', 0)
        main_rate = fund_flow.get('main_net_inflow_rate', 0)
        text += f"主力净流入：{main_inflow:,.0f} 元 ({main_rate:.2f}%)\n"
        
        # 判断资金流向状态
        if main_inflow > 0:
            text += f"  ✅ 主力资金流入，甄别主力是否大单拆中小单\n"
        else:
            text += f"  ⚠️ 主力资金流出，甄别主力是否大单拆中小单\n"
        
        # 超大单和大单
        super_large = fund_flow.get('super_large_net_inflow', 0)
        super_large_rate = fund_flow.get('super_large_net_inflow_rate', 0)
        text += f"超大单净流入：{super_large:,.0f} 元 ({super_large_rate:.2f}%)\n"
        
        large = fund_flow.get('large_net_inflow', 0)
        large_rate = fund_flow.get('large_net_inflow_rate', 0)
        text += f"大单净流入：{large:,.0f} 元 ({large_rate:.2f}%)\n"
        
        # 中单和小单
        medium = fund_flow.get('medium_net_inflow', 0)
        medium_rate = fund_flow.get('medium_net_inflow_rate', 0)
        text += f"中单净流入：{medium:,.0f} 元 ({medium_rate:.2f}%)\n"
        
        small = fund_flow.get('small_net_inflow', 0)
        small_rate = fund_flow.get('small_net_inflow_rate', 0)
        text += f"小单净流入：{small:,.0f} 元 ({small_rate:.2f}%)\n\n"
        
        # 连续流入天数
        consecutive_days = fund_flow.get('consecutive_inflow_days', 0)
        if consecutive_days > 0:
            text += f"🔥 连续{consecutive_days}日主力净流入\n"
        elif consecutive_days < 0:
            text += f"❄️ 连续{abs(consecutive_days)}日主力净流出\n"
        
        # 5日累计
        main_5d = fund_flow.get('main_net_inflow_5d', 0)
        text += f"近5日主力累计：{main_5d:,.0f} 元\n\n"
        
        # 资金流向解读
        text += f"【资金流向解读】\n"
        if main_inflow > 0 and super_large > 0:
            text += f"✅ 大资金持续流入，注意甄别\n"
        elif main_inflow > 0 and super_large < 0:
            text += f"⚠️ 主力流入但超大单流出\n"
        elif main_inflow < 0 and small > 0:
            text += f"⚠️ 主力流出但小单接盘，注意甄别\n"
        elif main_inflow < 0:
            text += f"❌ 主力资金持续流出\n"
        
        return text
    
    def _build_hourly_volume(self, hourly_volume_stats: Dict[str, Any]) -> str:
        """构建量能分析部分"""
        if not hourly_volume_stats:
            return ""
        
        text = "\n【历史量能分析（外盘内盘分布）】\n\n"
        text += "说明：U=外盘（主动性买入），D=内盘（主动性卖出），E=中性盘，UD比（外盘/内盘）越大表示买盘力量越强，成交量单位为股数，成交量占比为该时段占全天成交量的比例\n\n"
        
        # 表头
        text += "| 日期 | 时间段 | 总笔数 | 成交量 | U占比 | D占比 | E占比 | UD比 | 成交量占比 |\n"
        text += "|------|--------|--------|--------|-------|-------|-------|------|------------|\n"
        
        # 按日期排序
        sorted_dates = sorted(hourly_volume_stats.keys())
        
        for date in sorted_dates:
            # 将日期转换为简短格式 (YYYY/M/D)
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%Y/%-m/%-d') if hasattr(date_obj, 'strftime') else date_obj.strftime('%Y/%m/%d').replace('/0', '/')
            except:
                formatted_date = date
            
            period_stats = hourly_volume_stats[date]
            
            # 计算全天总量（用于计算成交量占比）
            daily_total_volume_count = sum(stats['total_volume_count'] for stats in period_stats.values())
            
            # 定义时间段顺序
            period_order = ['09:25', '09:30-10:30', '10:30-11:30', '13:00-14:00', '14:00-15:00']
            
            # 按顺序输出数据
            for period_name in period_order:
                if period_name in period_stats:
                    stats = period_stats[period_name]
                    
                    # 提取数据
                    transaction_count = stats['transaction_count']
                    total_volume_count = stats['total_volume_count']
                    u_ratio = stats['u_ratio']
                    d_ratio = stats['d_ratio']
                    e_ratio = stats['e_ratio']
                    ud_ratio = stats['ud_ratio']
                    
                    # 计算成交量占比
                    volume_ratio = total_volume_count / daily_total_volume_count if daily_total_volume_count > 0 else 0
                    
                    # 格式化U/D比
                    if ud_ratio == 'NA':
                        ud_ratio_str = 'NA'
                    else:
                        ud_ratio_str = f"{ud_ratio:.2f}"
                    
                    # 格式化时间段名称
                    period_display = period_name.replace('09:25', '9:25')
                    
                    text += f"| {formatted_date} | {period_display} | {transaction_count} | {total_volume_count} | {u_ratio:.4f} | {d_ratio:.4f} | {e_ratio:.4f} | {ud_ratio_str} | {volume_ratio:.4f} |\n"
            
            # 计算全天汇总（排除09:25）
            filtered_stats = [stats for name, stats in period_stats.items() if name != '09:25']
            if filtered_stats:
                # 汇总数据
                total_transactions = sum(s['transaction_count'] for s in filtered_stats)
                total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                total_u_volume_count = sum(s['u_volume_count'] for s in filtered_stats)
                total_d_volume_count = sum(s['d_volume_count'] for s in filtered_stats)
                total_e_volume_count = sum(s['e_volume_count'] for s in filtered_stats)
                
                # 计算比例
                if total_volume_count > 0:
                    u_ratio = total_u_volume_count / total_volume_count
                    d_ratio = total_d_volume_count / total_volume_count
                    e_ratio = total_e_volume_count / total_volume_count
                    ud_ratio = total_u_volume_count / total_d_volume_count if total_d_volume_count > 0 else 0
                    
                    # 全天成交量占比（排除09:25）
                    volume_ratio = total_volume_count / daily_total_volume_count if daily_total_volume_count > 0 else 0
                    
                    text += f"| {formatted_date} | 09:30-15:00 | {total_transactions} | {total_volume_count} | {u_ratio:.4f} | {d_ratio:.4f} | {e_ratio:.4f} | {ud_ratio:.2f} | {volume_ratio:.4f} |\n"
        
        text += "\n"
        return text

