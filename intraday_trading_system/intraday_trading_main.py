"""
A股日内交易分析主程序
实时获取股票数据，通过大模型分析,给出交易建议
"""

import sys
import json
import re
import smtplib
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

from intraday_data_fetcher import IntradayDataFetcher
from intraday_indicators import TechnicalIndicators
from intraday_prompt_builder import PromptBuilder

# 导入父目录的md_to_html模块
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
from md_to_html import MarkdownToHTMLConverter


# ===== 辅助函数 =====
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


def extract_trading_action(md_file_path: str) -> str:
    """
    从MD文件中提取操作方向信息
    
    :param md_file_path: str, MD文件路径
    :return: str, 提取到的操作方向，如果未找到则返回空字符串
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配多种可能的操作方向格式
        patterns = [
            r'\*\*操作方向：(.+?)\*\*',  # 格式1: **操作方向：买入（轻仓博弈反弹）**
            r'\*\*操作方向\*\*\s*\|\s*(.+?)\s*\|',  # 格式2: | **操作方向** | ✅ 买入（轻仓做反弹） |
            r'\*\*操作方向\*\*[：:]\s*\*\*(.+?)\*\*',  # 格式3: **操作方向**：**观望**
            r'\*\*[^\*]*?操作方向\*\*[：:]\s*\*\*(.+?)\*\*',  # 格式4: **📊 操作方向**：**买入**（带表情符号）
            r'操作方向[：:]\s*(.+?)[\n\r]',  # 格式5: 操作方向：买入
            r'\*\*交易建议\*\*[：:]\s*(.+?)[\n\r]',  # 格式6: **交易建议：买入**
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                action_text = match.group(1).strip()
                # 清理markdown格式
                clean_action = re.sub(r'\*\*', '', action_text)  # 移除粗体标记
                clean_action = re.sub(r'[✅❌🟢🟡🔴📊]', '', clean_action)  # 移除表情符号
                clean_action = clean_action.strip()
                
                # 提取核心操作（买入/卖出/持有/观望等）
                if clean_action:
                    return clean_action
        
        print(f"⚠️ 在文件 {md_file_path} 中未找到操作方向信息")
        return ""
    
    except Exception as e:
        print(f"❌ 提取操作方向时出错: {e}")
        return ""


def send_email(subject: str, body: str, receivers: list, sender: str, password: str, 
               attachment_paths: list = None) -> bool:
    """
    发送邮件并返回是否成功，如果提供attachment_paths则发送多个附件
    
    :param subject: 邮件主题
    :param body: 邮件正文
    :param receivers: 收件人列表
    :param sender: 发件人邮箱
    :param password: 发件人邮箱密码
    :param attachment_paths: 附件路径列表
    :return: bool, 是否发送成功
    """
    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(receivers)
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
                        
                        attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=os.path.basename(attachment_path))
                        msg.attach(attachment)
                    print(f"  ✅ 已添加附件: {os.path.basename(attachment_path)}")
                except Exception as e:
                    print(f"  ⚠️ 添加附件失败: {attachment_path}, 错误: {e}")
                    continue
            else:
                print(f"  ⚠️ 附件文件不存在: {attachment_path}")
    
    # SMTP服务器设置
    smtp_server = 'applesmtp.163.com'
    smtp_port = 465
    
    # 登录凭证
    username = sender
    
    # 发送邮件
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(username, password)
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        print("  ✅ 邮件发送成功！")
        return True
    except Exception as e:
        print(f"  ❌ 邮件发送失败：{e}")
        return False


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
        
        # 获取要使用的模型提供商列表
        self.api_providers = self.config.get('api_providers', [])
        if not self.api_providers:
            # 如果没有配置api_providers，使用单个api_provider
            self.api_providers = [self.config.get('api_provider', 'qwen')]
        
        print(f"✅ 将使用以下模型进行分析: {', '.join(self.api_providers)}")
        
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
            
            # 获取要使用的模型提供商列表
            api_providers = config.get('api_providers', [])
            if not api_providers:
                api_providers = [config.get('api_provider', 'qwen')]
            
            # 为每个提供商加载API密钥
            config['api_keys'] = {}
            missing_keys = []
            
            for provider in api_providers:
                if provider == 'qwen':
                    api_key = keys.get('qwen_api_key', keys.get('api_key', ''))
                    key_name = 'qwen_api_key'
                elif provider == 'deepseek':
                    api_key = keys.get('deepseek_api_key', '')
                    key_name = 'deepseek_api_key'
                else:
                    api_key = keys.get('api_key', '')
                    key_name = 'api_key'
                
                if not api_key or api_key.startswith('sk-请填入'):
                    missing_keys.append(f"{provider} ({key_name})")
                else:
                    config['api_keys'][provider] = api_key
            
            if missing_keys:
                print(f"❌ 未配置以下模型的 API Key: {', '.join(missing_keys)}")
                print(f"💡 请在 {keys_path} 中配置相应的API密钥")
                sys.exit(1)
            
            # 保留单个api_key用于向后兼容
            config['api_key'] = config['api_keys'].get(config.get('api_provider', 'qwen'), '')
            
            # 加载邮件配置
            config['email_sender'] = keys.get('email_sender', '')
            config['email_password'] = keys.get('email_password', '')
            config['email_receivers'] = keys.get('email_receivers', [])
            
            print(f"✅ 配置文件加载成功 (keys.json: {keys_path})")
            print(f"✅ 已加载 {len(config['api_keys'])} 个模型的API密钥: {', '.join(config['api_keys'].keys())}")
            
            # 检查邮件配置
            if config['email_sender'] and config['email_password'] and config['email_receivers']:
                print(f"✅ 邮件配置已加载")
            else:
                print(f"⚠️ 邮件配置不完整，邮件发送功能将被禁用")
            
            return config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)
    
    def analyze_stock(self, stock_code: str) -> list:
        """
        分析单只股票，使用所有配置的模型
        
        :param stock_code: 股票代码
        :return: 分析结果字典列表（每个模型一个结果）
        """
        print(f"\n{'='*60}")
        print(f"开始分析股票: {stock_code}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"使用模型: {', '.join(self.api_providers)}")
        print(f"{'='*60}\n")
        
        # 1. 获取所有数据（只需要获取一次）
        print("📊 步骤1: 获取股票数据...")
        all_data = self._fetch_all_data(stock_code)
        
        if not all_data or not all_data.get('quote'):
            print(f"❌ 获取股票 {stock_code} 数据失败")
            return []
        
        # 2. 构建提示词（只需要构建一次）
        print("\n📝 步骤2: 构建分析提示词...")
        prompt = self.prompt_builder.build_prompt(all_data)
        
        # 保存提示词到文件（可选）
        if self.config['output_config']['save_to_file']:
            self._save_prompt(stock_code, prompt, all_data.get('quote', {}).get('stock_name', ''))
        
        results = []
        
        # 3. 为每个模型进行分析
        for provider in self.api_providers:
            print(f"\n🤖 步骤3-{provider.upper()}: 调用{provider.upper()}模型进行分析...")
            analysis_result = self._call_llm(prompt, provider)
            
            if not analysis_result:
                print(f"⚠️ {provider.upper()}模型分析失败，跳过")
                continue
            
            # 4. 保存分析结果
            print(f"\n💾 步骤4-{provider.upper()}: 保存{provider.upper()}分析结果...")
            result = {
                'stock_code': stock_code,
                'stock_name': all_data.get('quote', {}).get('stock_name', ''),
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'current_price': all_data.get('quote', {}).get('current_price', 0),
                'price_change': all_data.get('quote', {}).get('price_change', 0),
                'analysis': analysis_result,
                'prompt': prompt,
                'model_provider': provider,
                'model_name': self.config['api_config'][provider]['model']
            }
            
            if self.config['output_config']['save_to_file']:
                self._save_result(stock_code, result)
            
            # 5. 显示结果
            if self.config['output_config']['show_realtime']:
                self._display_result(result)
            
            results.append(result)
            
            # 在多个模型之间稍作等待，避免API限制
            if len(self.api_providers) > 1 and provider != self.api_providers[-1]:
                print("\n⏳ 等待2秒后调用下一个模型...")
                import time
                time.sleep(2)
        
        return results
    
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
            
            # 3. 历史分时数据和量能分析
            history_days = self.config['data_config']['history_days']
            if history_days > 0:
                print(f"  - 获取最近{history_days}天分时数据...")
                historical_intraday = self.data_fetcher.get_historical_intraday_with_cache(stock_code, history_days)
                if not historical_intraday.empty:
                    # 计算量能分布
                    hourly_volume_stats = self.data_fetcher.calculate_hourly_volume(historical_intraday)
                    data['hourly_volume_stats'] = hourly_volume_stats
                else:
                    data['hourly_volume_stats'] = {}
            
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
    
    def _call_llm(self, prompt: str, provider: str) -> str:
        """调用大模型API"""
        try:
            api_config = self.config['api_config'][provider]
            
            # 根据不同的提供商获取对应的API密钥
            api_key = self.config['api_keys'].get(provider)
            
            if not api_key:
                print(f"❌ 未找到 {provider} 的API密钥")
                return None
            
            client = OpenAI(
                api_key=api_key,
                base_url=api_config['base_url']
            )
            
            print(f"  - 使用模型: {api_config['model']}")
            print(f"  - API地址: {api_config['base_url']}")
            
            # 为qwen3-max添加推理模式指令
            enhanced_prompt = prompt
            if provider == 'qwen' and api_config.get('reasoning_mode', False):
                enhanced_prompt = prompt + "\n\n/think"  # 添加推理模式指令
                print(f"  - 推理模式: 已开启 (/think指令)")
            
            # 调用API
            api_params = {
                'model': api_config['model'],
                'messages': [
                    {'role': 'system', 'content': '你是一位专业的A股量化交易分析师，擅长技术分析和短线交易策略。'},
                    {'role': 'user', 'content': enhanced_prompt}
                ],
                'stream': True
            }
            
            # 注意：incremental_output 不是标准 OpenAI API 参数，已移除
            
            response = client.chat.completions.create(**api_params)
            
            # 流式输出
            full_response = ""
            print("\n" + "="*60)
            print(f"💬 {provider.upper()}模型分析结果：")
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
            print(f"❌ 调用{provider.upper()}模型API失败: {e}")
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
        """保存分析结果到文件，并转换为HTML和发送邮件"""
        try:
            output_dir = Path(self.config['output_config']['output_dir'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 获取模型信息（用于文件名）
            model_provider = result.get('model_provider', 'unknown')
            model_name = result.get('model_name', 'unknown')
            
            # 保存为JSON格式（包含模型名称）
            json_filename = f"{stock_code}_{result['stock_name']}_{model_provider}_result_{timestamp}.json"
            json_filepath = output_dir / json_filename
            
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ 分析结果(JSON)已保存: {json_filepath}")
            
            # 保存为Markdown格式（更易读，包含模型名称）
            md_filename = f"{stock_code}_{result['stock_name']}_{model_provider}_analysis_{timestamp}.md"
            md_filepath = output_dir / md_filename
            
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {result['stock_name']}({stock_code}) 日内交易分析报告\n\n")
                f.write(f"**分析模型**: {model_name} ({model_provider})\n")
                f.write(f"**分析时间**: {result['analysis_time']}\n")
                f.write(f"**当前价格**: {result['current_price']:.2f} 元\n")
                f.write(f"**涨跌幅**: {result['price_change']:.2f}%\n\n")
                f.write("---\n\n")
                f.write("## 分析结果\n\n")
                f.write(result['analysis'])
            
            print(f"  ✅ 分析报告(Markdown)已保存: {md_filepath}")
            
            # 转换为HTML格式（包含模型名称）
            html_filename = f"{stock_code}_{result['stock_name']}_{model_provider}_analysis_{timestamp}.html"
            html_filepath = output_dir / html_filename
            
            converter = MarkdownToHTMLConverter()
            if converter.convert_file(str(md_filepath), str(html_filepath)):
                print(f"  ✅ HTML报告已生成: {html_filepath}")
            else:
                print(f"  ⚠️ HTML转换失败")
                html_filepath = None
            
            # 发送邮件
            email_sender = self.config.get('email_sender', '')
            email_password = self.config.get('email_password', '')
            email_receivers = self.config.get('email_receivers', [])
            
            if email_sender and email_password and email_receivers:
                print(f"\n📧 准备发送邮件...")
                
                # 获取模型名称（从result中获取）
                model_name = result.get('model_name', model_provider)
                
                # 提取操作方向和投资评级
                trading_action = extract_trading_action(str(md_filepath))
                investment_rating = extract_investment_rating(str(md_filepath))
                
                # 构建邮件主题
                subject_parts = [f"[{model_name}]"]
                
                # 添加操作方向（如果有）
                if trading_action:
                    subject_parts.append(trading_action)
                
                # 添加股票信息
                subject_parts.append(f"{result['stock_name']}({stock_code})")
                
                # 添加投资评级（如果有）
                if investment_rating:
                    subject_parts.append(f"- {investment_rating}")
                
                email_subject = " ".join(subject_parts)
                
                # 准备邮件正文
                email_body = (
                    f"股票 {result['stock_name']}({stock_code}) 的日内交易分析报告已生成。\n\n"
                    f"分析时间: {result['analysis_time']}\n"
                    f"当前价格: {result['current_price']:.2f} 元\n"
                    f"涨跌幅: {result['price_change']:.2f}%\n\n"
                    f"请查看附件中的详细分析报告（HTML格式）和分析提示词文件。\n"
                )
                
                # 准备附件列表：HTML分析报告 + 提示词文件
                attachment_list = []
                if html_filepath and html_filepath.exists():
                    attachment_list.append(str(html_filepath))
                # 获取提示词文件路径
                prompt_filepath = output_dir / f"{stock_code}_{result['stock_name']}_prompt_{timestamp}.txt"
                if prompt_filepath.exists():
                    attachment_list.append(str(prompt_filepath))
                
                # 发送邮件
                send_result = send_email(
                    subject=email_subject,
                    body=email_body,
                    receivers=email_receivers,
                    sender=email_sender,
                    password=email_password,
                    attachment_paths=attachment_list
                )
                
                if not send_result:
                    print(f"  ⚠️ 邮件发送失败，但文件已保存到本地")
            else:
                print(f"  ⚠️ 邮件配置不完整，跳过邮件发送")
            
        except Exception as e:
            print(f"  ⚠️ 保存分析结果失败: {e}")
            import traceback
            traceback.print_exc()
    
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
        print("💡 自动继续分析(将使用历史数据)...\n")
    
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

