import akshare as ak
import traceback
import sys

# 强制输出缓冲
sys.stdout = sys.stdout

print("=" * 80)
print("调试三个失败的接口")
print("=" * 80)
sys.stdout.flush()

# 1. 测试 stock_zh_a_spot_em
print("\n【测试1】ak.stock_zh_a_spot_em()")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"✅ 成功，共{len(df)}条记录")
    print(f"列名: {df.columns.tolist()}")
    print(df.head(2))
except Exception as e:
    print(f"❌ 失败:")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {str(e)[:200]}")
    traceback.print_exc()

# 2. 测试 stock_zh_index_spot_em
print("\n【测试2】ak.stock_zh_index_spot_em()")
try:
    df = ak.stock_zh_index_spot_em()
    print(f"✅ 成功，共{len(df)}个指数")
    print(f"列名: {df.columns.tolist()}")
    print(df.head(2))
except Exception as e:
    print(f"❌ 失败:")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {str(e)[:200]}")
    traceback.print_exc()

# 3. 测试 stock_board_industry_spot_em (无参数)
print("\n【测试3a】ak.stock_board_industry_spot_em() - 无参数")
try:
    df = ak.stock_board_industry_spot_em()
    print(f"✅ 成功，共{len(df)}个板块")
    print(df.head(2))
except Exception as e:
    print(f"❌ 失败:")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {str(e)[:200]}")

# 3. 测试 stock_board_industry_spot_em (有参数)
print("\n【测试3b】ak.stock_board_industry_spot_em(symbol='小金属') - 有参数")
try:
    df = ak.stock_board_industry_spot_em(symbol="小金属")
    print(f"✅ 成功")
    print(df)
except Exception as e:
    print(f"❌ 失败:")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {str(e)[:200]}")
    traceback.print_exc()

# 搜索可能的板块列表接口
print("\n【查找板块列表接口】")
try:
    # 搜索是否有获取板块列表的接口
    import inspect
    func_list = [name for name in dir(ak) if 'board' in name.lower() and 'industry' in name.lower()]
    print(f"可能的板块相关接口: {func_list[:10]}")
except Exception as e:
    print(f"查找失败: {e}")

