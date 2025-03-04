import akshare as ak
stockdata = ak.stock_intraday_sina(symbol="sz000001", date="20250304")
print(stockdata)