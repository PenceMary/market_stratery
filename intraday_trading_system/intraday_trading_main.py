"""
A股日内交易分析主程序
实时获取股票数据，通过大模型分析，给出交易建议
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import os

from intraday_data_fetcher import IntradayDataFetcher
from intraday_indicators import TechnicalIndicators
from intraday_prompt_builder import PromptBuilder


class IntradayTradingAnalyzer:
    """日内交易分析器"""
    
    def __init__(self, config_file: str = 'intraday_trading_config.json', 
                 keys_file: str = 'keys.json'):
        """
        初始化分析器
        
        :param config_file: 配置文件路径
        :param keys_file: API密钥文件路径
        """
        self.config = self._load_config(config_file, keys_file)
        
        # 从配置中读取超时和重试参数
        data_config = self.config.get('data_config', {})
        max_retries = data_config.get('max_retries', 3)
        retry_delay = data_config.get('retry_delay', 2)
        api_timeout = data_config.get('api_timeout', 30)
        
        self.data_fetcher = IntradayDataFetcher(
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=api_timeout
        )
        self.indicator_calculator = TechnicalIndicators()
        self.prompt_builder = PromptBuilder()
        
        # 确保输出目录存在
        output_dir = Path(self.config['output_config']['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_file: str, keys_file: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载API密钥（尝试当前目录，然后父目录）
            keys_path = None
            if Path(keys_file).exists():
                keys_path = keys_file
            elif Path('../' + keys_file).exists():
                keys_path = '../' + keys_file
            else:
                print(f"❌ 未找到配置文件: {keys_file}")
                print(f"💡 请在当前目录或父目录创建 {keys_file}")
                sys.exit(1)
            
            with open(keys_path, 'r', encoding='utf-8') as f:
                keys = json.load(f)
            
            config['api_key'] = keys.get('api_key', '')
            print(f"✅ 配置文件加载成功 (keys.json: {keys_path})")
            
            return config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)
    
    def analyze_stock(self, stock_code: str) -> dict:
        """
        分析单只股票
        
        :param stock_code: 股票代码
        :return: 分析结果字典
        """
        print(f"\n{'='*60}")
        print(f"开始分析股票: {stock_code}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 1. 获取所有数据
        print("📊 步骤1: 获取股票数据...")
        all_data = self._fetch_all_data(stock_code)
        
        if not all_data or not all_data.get('quote'):
            print(f"❌ 获取股票 {stock_code} 数据失败")
            return None
        
        # 2. 构建提示词
        print("\n📝 步骤2: 构建分析提示词...")
        prompt = self.prompt_builder.build_prompt(all_data)
        
        # 保存提示词到文件（可选）
        if self.config['output_config']['save_to_file']:
            self._save_prompt(stock_code, prompt, all_data.get('quote', {}).get('stock_name', ''))
        
        # 3. 调用大模型分析
        print("\n🤖 步骤3: 调用大模型进行分析...")
        analysis_result = self._call_llm(prompt)
        
        if not analysis_result:
            print(f"❌ 大模型分析失败")
            return None
        
        # 4. 保存分析结果
        print("\n💾 步骤4: 保存分析结果...")
        result = {
            'stock_code': stock_code,
            'stock_name': all_data.get('quote', {}).get('stock_name', ''),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': all_data.get('quote', {}).get('current_price', 0),
            'price_change': all_data.get('quote', {}).get('price_change', 0),
            'analysis': analysis_result,
            'prompt': prompt
        }
        
        if self.config['output_config']['save_to_file']:
            self._save_result(stock_code, result)
        
        # 5. 显示结果
        if self.config['output_config']['show_realtime']:
            self._display_result(result)
        
        return result
    
    def _fetch_all_data(self, stock_code: str) -> dict:
        """获取所有需要的数据"""
        data = {}
        
        try:
            # 1. 实时行情
            print("  - 获取实时行情...")
            quote = self.data_fetcher.get_realtime_quote(stock_code)
            if not quote:
                return None
            data['quote'] = quote
            
            # 2. 今日分时数据
            print("  - 获取今日分时数据...")
            today_intraday = self.data_fetcher.get_today_intraday_data(stock_code)
            if not today_intraday.empty:
                # 计算分时指标
                intraday_indicators = self.indicator_calculator.analyze_intraday_data(today_intraday)
                data['intraday_indicators'] = intraday_indicators
            
            # 3. 历史分时数据（可选，用于更全面的分析）
            history_days = self.config['data_config']['history_days']
            if history_days > 0:
                print(f"  - 获取最近{history_days}天分时数据...")
                # 这里可以扩展获取历史分时数据
            
            # 4. K线数据
            kline_days = self.config['data_config']['kline_days']
            print(f"  - 获取最近{kline_days}天K线数据...")
            kline_data = self.data_fetcher.get_kline_data(stock_code, kline_days)
            if not kline_data.empty:
                kline_indicators = self.indicator_calculator.analyze_kline_data(kline_data)
                data['kline_indicators'] = kline_indicators
            
            # 5. 盘口数据
            print("  - 获取盘口数据...")
            order_book = self.data_fetcher.get_order_book(stock_code)
            data['order_book'] = order_book
            
            # 6. 大盘指数
            print("  - 获取大盘指数...")
            market_indices = self.data_fetcher.get_market_indices(stock_code)
            data['market_indices'] = market_indices
            
            # 7. 板块信息
            print("  - 获取板块信息...")
            sector_info = self.data_fetcher.get_sector_info(stock_code)
            data['sector_info'] = sector_info
            
            # 8. 市场情绪
            print("  - 获取市场情绪...")
            market_sentiment = self.data_fetcher.get_market_sentiment()
            data['market_sentiment'] = market_sentiment
            
            print("✅ 所有数据获取完成")
            return data
            
        except Exception as e:
            print(f"❌ 获取数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _call_llm(self, prompt: str) -> str:
        """调用大模型API"""
        try:
            api_provider = self.config.get('api_provider', 'qwen')
            api_config = self.config['api_config'][api_provider]
            
            client = OpenAI(
                api_key=self.config['api_key'],
                base_url=api_config['base_url']
            )
            
            print(f"  - 使用模型: {api_config['model']}")
            print(f"  - API地址: {api_config['base_url']}")
            
            # 调用API
            response = client.chat.completions.create(
                model=api_config['model'],
                messages=[
                    {'role': 'system', 'content': '你是一位专业的A股量化交易分析师，擅长技术分析和短线交易策略。'},
                    {'role': 'user', 'content': prompt}
                ],
                stream=True
            )
            
            # 流式输出
            full_response = ""
            print("\n" + "="*60)
            print("💬 大模型分析结果：")
            print("="*60 + "\n")
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    if self.config['output_config']['show_realtime']:
                        print(content, end='', flush=True)
            
            print("\n" + "="*60 + "\n")
            
            return full_response
            
        except Exception as e:
            print(f"❌ 调用大模型API失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _save_prompt(self, stock_code: str, prompt: str, stock_name: str):
        """保存提示词到文件"""
        try:
            output_dir = Path(self.config['output_config']['output_dir'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            filename = f"{stock_code}_{stock_name}_prompt_{timestamp}.txt"
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            print(f"  ✅ 提示词已保存: {filepath}")
            
        except Exception as e:
            print(f"  ⚠️ 保存提示词失败: {e}")
    
    def _save_result(self, stock_code: str, result: dict):
        """保存分析结果到文件"""
        try:
            output_dir = Path(self.config['output_config']['output_dir'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 保存为JSON格式
            json_filename = f"{stock_code}_{result['stock_name']}_result_{timestamp}.json"
            json_filepath = output_dir / json_filename
            
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ 分析结果(JSON)已保存: {json_filepath}")
            
            # 保存为Markdown格式（更易读）
            md_filename = f"{stock_code}_{result['stock_name']}_analysis_{timestamp}.md"
            md_filepath = output_dir / md_filename
            
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {result['stock_name']}({stock_code}) 日内交易分析报告\n\n")
                f.write(f"**分析时间**: {result['analysis_time']}\n")
                f.write(f"**当前价格**: {result['current_price']:.2f} 元\n")
                f.write(f"**涨跌幅**: {result['price_change']:.2f}%\n\n")
                f.write("---\n\n")
                f.write("## 分析结果\n\n")
                f.write(result['analysis'])
            
            print(f"  ✅ 分析报告(Markdown)已保存: {md_filepath}")
            
        except Exception as e:
            print(f"  ⚠️ 保存分析结果失败: {e}")
    
    def _display_result(self, result: dict):
        """显示分析结果摘要"""
        print("\n" + "="*60)
        print(f"📊 {result['stock_name']}({result['stock_code']}) 分析完成")
        print("="*60)
        print(f"分析时间: {result['analysis_time']}")
        print(f"当前价格: {result['current_price']:.2f} 元")
        print(f"涨跌幅: {result['price_change']:.2f}%")
        print("="*60 + "\n")
    
    def batch_analyze(self, stock_codes: list):
        """批量分析多只股票"""
        results = []
        
        for i, stock_code in enumerate(stock_codes, 1):
            print(f"\n{'#'*60}")
            print(f"分析进度: {i}/{len(stock_codes)}")
            print(f"{'#'*60}")
            
            result = self.analyze_stock(stock_code)
            if result:
                results.append(result)
            
            # 如果不是最后一只股票，等待一段时间避免请求过快
            if i < len(stock_codes):
                print("\n⏳ 等待5秒后继续...")
                import time
                time.sleep(5)
        
        return results


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 A股日内交易分析系统")
    print("="*60 + "\n")
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("❌ 请提供股票代码参数")
        print("\n💡 使用方法:")
        print("  python intraday_trading_main.py <股票代码1> [股票代码2] ...")
        print("\n📖 示例:")
        print("  python intraday_trading_main.py 600000")
        print("  python intraday_trading_main.py 600000 000001 300750")
        sys.exit(1)
    
    stock_codes = sys.argv[1:]
    
    # 验证交易时间
    current_time = datetime.now()
    hour = current_time.hour
    minute = current_time.minute
    
    is_trading_time = False
    if (9 <= hour < 11) or (hour == 11 and minute <= 30):
        is_trading_time = True
    elif (13 <= hour < 15):
        is_trading_time = True
    
    if not is_trading_time:
        print("⚠️ 警告: 当前不在交易时间内")
        print(f"当前时间: {current_time.strftime('%H:%M:%S')}")
        print("交易时间: 09:30-11:30, 13:00-15:00")
        
        response = input("\n是否继续分析？(y/n): ")
        if response.lower() != 'y':
            print("已取消分析")
            sys.exit(0)
    
    # 创建分析器
    analyzer = IntradayTradingAnalyzer()
    
    # 分析股票
    if len(stock_codes) == 1:
        analyzer.analyze_stock(stock_codes[0])
    else:
        analyzer.batch_analyze(stock_codes)
    
    print("\n" + "="*60)
    print("✅ 所有分析任务完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

