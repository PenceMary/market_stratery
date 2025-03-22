import akshare as ak
stockdata = ak.stock_intraday_sina(symbol="sz000001", date="20250210")
print(stockdata)
#可获取过去15个交易日的成交记录
