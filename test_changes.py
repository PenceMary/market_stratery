#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 auto_analyze_stocks.py 的修改
"""

import sys
import pandas as pd
from datetime import date, datetime, timedelta

# 导入需要测试的函数
from auto_analyze_stocks import (
    is_next_day_trading_day,
    get_high_turnover_stocks,
    get_current_analysis_mode,
    is_execution_time,
    update_stocks_list_on_trading_day,
    DEFAULT_STOCKS_LIST_FILE
)

def test_is_next_day_trading_day():
    """测试判断下一个日期是否为交易日"""
    print("=" * 60)
    print("测试 1: 判断下一个日期是否为交易日")
    print("=" * 60)

    try:
        result = is_next_day_trading_day()
        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"✅ 函数执行成功")
        print(f"   明天的日期: {tomorrow}")
        print(f"   明天是否为交易日: {'是' if result else '否'}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_high_turnover_stocks():
    """测试获取高换手率股票"""
    print("\n" + "=" * 60)
    print("测试 2: 获取高换手率股票")
    print("=" * 60)

    try:
        # 读取股票列表
        print(f"正在读取股票列表: {DEFAULT_STOCKS_LIST_FILE}")
        df = pd.read_csv(DEFAULT_STOCKS_LIST_FILE, encoding='utf-8-sig')
        print(f"✅ 成功读取 {len(df)} 只股票")

        # 检查换手率列
        if '换手率' in df.columns:
            print(f"✅ 换手率列存在")
            print(f"   换手率统计:")
            print(f"   - 平均值: {df['换手率'].mean():.2f}%")
            print(f"   - 中位数: {df['换手率'].median():.2f}%")
            print(f"   - 最大值: {df['换手率'].max():.2f}%")
        else:
            print(f"❌ 换手率列不存在")
            return False

        # 测试获取高换手率股票
        high_turnover_stocks = get_high_turnover_stocks(df, turnover_threshold=20.0)
        print(f"✅ 成功获取高换手率股票")
        print(f"   换手率 > 20% 的股票数量: {len(high_turnover_stocks)}")

        if len(high_turnover_stocks) > 0:
            print(f"\n   示例股票（前10只）:")
            for i, code in enumerate(high_turnover_stocks[:10], 1):
                stock_data = df[df['代码'] == code]
                if not stock_data.empty:
                    name = stock_data.iloc[0]['名称']
                    turnover = stock_data.iloc[0]['换手率']
                    print(f"   {i}. {code} - {name} - 换手率: {turnover:.2f}%")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_current_analysis_mode():
    """测试获取当前分析模式"""
    print("\n" + "=" * 60)
    print("测试 3: 获取当前分析模式")
    print("=" * 60)

    try:
        mode = get_current_analysis_mode()
        print(f"✅ 成功获取分析模式")
        print(f"   当前分析模式: {mode}")

        if mode == 'high_turnover':
            print(f"   说明: 连续交易日模式（只分析换手率 > 20% 的股票）")
        else:
            print(f"   说明: 非交易日间隔模式（对所有股票随机分析）")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_is_execution_time():
    """测试判断执行时间"""
    print("\n" + "=" * 60)
    print("测试 4: 判断执行时间")
    print("=" * 60)

    try:
        result = is_execution_time()
        now = datetime.now()
        print(f"✅ 函数执行成功")
        print(f"   当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   是否在执行时间范围内（17:00-次日06:00）: {'是' if result else '否'}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_update_stocks_list():
    """测试更新股票列表"""
    print("\n" + "=" * 60)
    print("测试 5: 更新股票列表（获取最新换手率）")
    print("=" * 60)

    try:
        df = update_stocks_list_on_trading_day()
        print(f"✅ 成功获取股票列表")
        print(f"   股票数量: {len(df)}")
        print(f"   列名: {list(df.columns)}")

        if '换手率' in df.columns:
            print(f"   换手率数据示例（前5只）:")
            for i, row in df.head(5).iterrows():
                print(f"   {row['代码']} - {row['名称']} - 换手率: {row['换手率']:.2f}%")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n")
    print("█" * 60)
    print("█" + " " * 58 + "█")
    print("█" + "  测试 auto_analyze_stocks.py 的修改".center(56) + "█")
    print("█" + " " * 58 + "█")
    print("█" * 60)
    print("\n")

    results = []

    # 运行测试
    results.append(("判断下一个日期是否为交易日", test_is_next_day_trading_day()))
    results.append(("获取高换手率股票", test_get_high_turnover_stocks()))
    results.append(("获取当前分析模式", test_get_current_analysis_mode()))
    results.append(("判断执行时间", test_is_execution_time()))
    results.append(("更新股票列表", test_update_stocks_list()))

    # 打印测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 60)
    print(f"总计: {len(results)} 个测试，{passed} 个通过，{failed} 个失败")
    print("-" * 60)

    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
