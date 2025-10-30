import akshare as ak

def test_common_interfaces():
    """测试不依赖股票代码的通用接口"""
    print("\n" + "=" * 80)
    print("📊 测试通用接口（不依赖股票代码）")
    print("=" * 80)
    
    # 2. 实时行情（全市场）
    print("\n【2/7】ak.stock_zh_a_spot_em()")
    try:
        df = ak.stock_zh_a_spot_em()
        print(f"✅ 成功，全市场共{len(df)}只股票")
        print(df.head(5))
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 3. 指数实时行情
    print("\n【3/7】ak.stock_zh_index_spot_em()")
    try:
        df = ak.stock_zh_index_spot_em()
        index_data = df[df['代码'] == '000001']
        print(f"✅ 成功，共{len(df)}个指数")
        print(index_data)
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 5. 行业板块行情
    print("\n【5/7】ak.stock_board_industry_spot_em()")
    try:
        df = ak.stock_board_industry_name_ths()
        print(f"✅ 成功，共{len(df)}个板块")
        print(df.head(10))
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    test_common_interfaces()