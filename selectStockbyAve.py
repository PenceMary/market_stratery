import json
import random
import akshare as ak
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import time as t

def load_config(config_path='selectbyAve.json'):
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def send_email(subject: str, body: str, receivers: str, sender: str, password: str) -> None:

    # 创建文本邮件
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = sender  # 发件人
    msg['To'] = ', '.join(receivers)  # 将收件人列表转换为逗号分隔的字符串
    msg['Subject'] = subject

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
    except Exception as e:
        print(f"邮件发送失败：{e}")
        
def get_stock_list():
    return ak.stock_info_a_code_name()

def fetch_stock_data(stock_code):
    stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
    stock_zh_a_hist_df['日期'] = pd.to_datetime(stock_zh_a_hist_df['日期'])
    stock_zh_a_hist_df.set_index('日期', inplace=True)
    return stock_zh_a_hist_df

def analyze_stock(stock_code, stock_name, config):
    stock_data = fetch_stock_data(stock_code)
    # 计算成交量基准天数的成交量均线
    vol_ma = stock_data['成交量'].rolling(window=config['成交量基准天数']).mean()

    # 获取最近n天的成交量数据
    recent_vol = stock_data['成交量'].iloc[-config['上涨天数']:]
    recent_vol_ma = recent_vol.mean()

    # 获取60日均线值（取最近上涨天数前一天的值）
    vol_ma_60 = vol_ma.iloc[-config['上涨天数']-1]

    # 判断是否满足条件
    if all(recent_vol > vol_ma_60 * (1 + config['成交量上涨比例x'] / 100)):
        # 获取上涨天数前一个交易日的数据
        prev_vol = stock_data['成交量'].iloc[-config['上涨天数']-1]
        if prev_vol > vol_ma.iloc[-config['上涨天数']-2] * (1 + config['成交量上涨比例x'] / 100):
            return None  # 如果前一天也满足条件，则不纳入候选

        vol_ratio = (recent_vol_ma - vol_ma_60) / vol_ma_60 * 100
        print(f"Stock {stock_code} selected: {stock_name}")
        return {
            '股票名称': stock_name,
            '股票代码': stock_code,
            '60日均线值': vol_ma_60,
            '近{}日的成交量'.format(config['上涨天数']): recent_vol.tolist(),
            '{}日成交量均值'.format(config['上涨天数']): recent_vol_ma,
            '{}日成交量均值较60日均值的上涨比例'.format(config['上涨天数']): vol_ratio
        }
    return None

def main():
    config = load_config()
    stock_list = get_stock_list()

    if config['是否全量股票']:
        selected_stocks = stock_list['code'].tolist()
    else:
        selected_stocks = random.sample(stock_list['code'].tolist(), config['股票数量'])

    result = []
    total_stocks = len(selected_stocks)

    for index, stock_code in enumerate(selected_stocks):
        try:
            print(f"Processing {index + 1}/{total_stocks}: {stock_code}")
            stock_name = stock_list[stock_list['code'] == stock_code]['name'].values[0]
            stock_result = analyze_stock(stock_code, stock_name, config)
            if stock_result:
                result.append(stock_result)
        except Exception as e:
            print(f"Error processing stock {stock_code}: {e}")

    # 按上涨比例排序
    sorted_result = sorted(result, key=lambda x: x['{}日成交量均值较60日均值的上涨比例'.format(config['上涨天数'])])

    # 打印结果
    for stock in sorted_result:
        print(stock)

    # 发送邮件
    print("准备发送邮件 \n")
    send_email(subject="hi 贱人，这是今天的候选佳丽！", body=sorted_result, receivers=config['email_receivers'], sender=config['email_sender'], password=config['email_password'])

if __name__ == "__main__":
    main()
