import akshare as ak

index_code = "000001"
start_date = "20250901"
end_date = "20250915"
index_data = ak.stock_zh_a_hist(symbol=index_code, period="daily",
                             start_date=start_date,end_date=end_date,adjust='')

if index_data.empty:
    print(f"❌ 获取 {index_code} 数据失败，返回空数据")
else:
    print(f"✅ {index_code} 数据获取成功，共 {len(index_data)} 条记录")
    print(f"{index_data}")
