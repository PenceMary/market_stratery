import akshare as ak

stock_intraday_sina_df = ak.stock_intraday_sina(symbol="sz000001", date="20251013")
print(stock_intraday_sina_df)