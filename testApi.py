import akshare

    try:
        # 获取大盘指数数据
        index_data = ak.stock_zh_a_hist(symbol=index_code, period="daily",
                                      start_date=start_date, end_date=end_date, adjust="")

        if index_data.empty:
            print(f"❌ 获取 {index_name} 数据失败，返回空数据")
            return pd.DataFrame(), "未知指数"

        print(f"✅ {index_name} 数据获取成功，共 {len(index_data)} 条记录")
        print(f"   时间范围: {index_data['日期'].min()} 到 {index_data['日期'].max()}")

        return index_data, index_name