import akshare as ak
import random
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
import time as t
import requests
import re
from io import StringIO
import math

def get_tqdm(enable: bool = True):
    """
    返回适用于当前环境的 tqdm 对象。

    Args:
        enable (bool): 是否启用进度条。默认为 True。

    Returns:
        tqdm 对象。
    """
    if not enable:
        # 如果进度条被禁用，返回一个不显示进度条的 tqdm 对象
        return lambda iterable, *args, **kwargs: iterable

    try:
        # 尝试检查是否在 jupyter notebook 环境中，有利于退出进度条
        # noinspection PyUnresolvedReferences
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm
    except (NameError, ImportError):
        # 如果不在 Jupyter 环境中，就使用标准 tqdm
        from tqdm import tqdm

    return tqdm


def stock_intraday_sina_with_proxy(symbol: str = "sz000001", date: str = "20240321", proxies: dict = None) -> pd.DataFrame:
    """
    新浪财经-日内分时数据（支持代理）
    https://vip.stock.finance.sina.com.cn/quotes_service/view/cn_bill.php?symbol=sz000001
    :param symbol: 股票代码，如 'sz000001'
    :param date: 交易日，格式 'YYYYMMDD'
    :param proxies: 代理字典，如 {'http': 'http://91.236.74.10:8080'}
    :return: 分时数据 DataFrame
    """
    url_count = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_Bill.GetBillListCount"
    params = {
        "symbol": f"{symbol}",
        "num": "60",
        "page": "1",
        "sort": "ticktime",
        "asc": "0",
        "volume": "0",
        "amount": "0",
        "type": "0",
        "day": "-".join([date[:4], date[4:6], date[6:]]),
    }
    headers = {
        "Referer": f"https://vip.stock.finance.sina.com.cn/quotes_service/view/cn_bill.php?symbol={symbol}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/107.0.0.0 Safari/537.36",
    }
    try:
        r = requests.get(url=url_count, params=params, headers=headers, proxies=proxies, timeout=20)
        r.raise_for_status()
        data_json = r.json()
        total_page = math.ceil(int(data_json) / 60)
    except Exception as e:
        print(f"获取 {symbol} 在 {date} 的总页数失败: {e}")
        return pd.DataFrame()

    url_data = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_Bill.GetBillList"
    big_df = pd.DataFrame()
    tqdm = get_tqdm()
    for page in tqdm(range(1, total_page + 1), leave=False):
        params.update({"page": page})
        try:
            r = requests.get(url=url_data, params=params, headers=headers, proxies=proxies, timeout=20)
            r.raise_for_status()
            data_json = r.json()
            temp_df = pd.DataFrame(data_json)
            big_df = pd.concat(objs=[big_df, temp_df], ignore_index=True)
        except Exception as e:
            print(f"获取 {symbol} 在 {date} 的第 {page} 页数据失败: {e}")
            continue

    if big_df.empty:
        print(f"{symbol} 在 {date} 无数据")
        return pd.DataFrame()

    big_df.sort_values(by=["ticktime"], inplace=True, ignore_index=True)
    big_df["price"] = pd.to_numeric(big_df["price"], errors="coerce")
    big_df["volume"] = pd.to_numeric(big_df["volume"], errors="coerce")
    big_df["prev_price"] = pd.to_numeric(big_df["prev_price"], errors="coerce")
    print(f"成功获取 {symbol} 在 {date} 的数据:{big_df}")
    return big_df

if __name__ == "__main__":
    stock='sh600030'
    date='20250321'
    proxies = {'http': '101.231.178.155:7028'}
    stock_intraday_sina_with_proxy(symbol=stock, date=date, proxies=proxies)
