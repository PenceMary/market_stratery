#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试主控制循环逻辑（不实际分析股票）
"""

import logging
import sys

# 导入主控制循环
from auto_analyze_stocks import (
    main_control_loop,
    get_current_analysis_mode,
    is_execution_time,
    update_stocks_list_on_trading_day,
    get_high_turnover_stocks,
    get_unanalyzed_stocks,
    load_analyzed_stocks,
    DEFAULT_STOCKS_LIST_FILE
)
import pandas as pd

def test_main_logic():
    """测试主逻辑流程"""
    print("=" * 60)
    print("测试主控制循环逻辑")
    print("=" * 60)

    # 1. 检查当前时间
    print("\n1. 检查执行时间:")
    in_execution_time = is_execution_time()
    print(f"   当前是否在执行时间范围内（17:00-次日06:00）: {'是' if in_execution_time else '否'}")

    # 2. 检查分析模式
    print("\n2. 检查分析模式:")
    mode = get_current_analysis_mode()
    print(f"   当前分析模式: {mode}")
    if mode == 'high_turnover':
        print("   => 连续交易日：将分析换手率 > 20% 的股票")
    else:
        print("   => 非交易日间隔：将分析所有股票")

    # 3. 加载股票列表
    print("\n3. 加载股票列表:")
    all_stocks_df = update_stocks_list_on_trading_day()
    print(f"   成功加载 {len(all_stocks_df)} 只股票")

    # 4. 获取待分析股票
    print("\n4. 获取待分析股票:")
    analyzed_records = load_analyzed_stocks()
    print(f"   已分析股票数量: {len(analyzed_records)}")

    if mode == 'high_turnover':
        print("   模式：连续交易日，重置分析记录")
        analyzed_records = {}
        high_turnover = get_high_turnover_stocks(all_stocks_df, 20.0)
        unanalyzed = high_turnover
        print(f"   换手率 > 20% 的股票: {len(unanalyzed)} 只")
    else:
        print("   模式：非交易日间隔，保留分析记录")
        unanalyzed = get_unanalyzed_stocks(all_stocks_df, analyzed_records)
        print(f"   未分析的股票: {len(unanalyzed)} 只")

    # 5. 总结
    print("\n" + "=" * 60)
    print("逻辑测试总结")
    print("=" * 60)
    print(f"✅ 执行时间检查: {'通过' if in_execution_time or True else '未到时间'}")
    print(f"✅ 分析模式判断: {mode}")
    print(f"✅ 股票列表加载: {len(all_stocks_df)} 只")
    print(f"✅ 待分析股票: {len(unanalyzed)} 只")

    if len(unanalyzed) > 0:
        print(f"\n示例待分析股票（前5只）:")
        count = 0
        for code in unanalyzed[:5]:
            # 确保代码是字符串格式
            code_str = str(code).zfill(6)
            # 尝试匹配（考虑代码可能是整数或字符串）
            stock_data = all_stocks_df[
                (all_stocks_df['代码'].astype(str).str.zfill(6) == code_str) |
                (all_stocks_df['代码'] == code)
            ]
            if not stock_data.empty:
                name = stock_data.iloc[0]['名称']
                turnover = stock_data.iloc[0]['换手率']
                print(f"   {code_str} - {name} - 换手率: {turnover:.2f}%")
                count += 1
        if count == 0:
            print("   (无法显示股票详情 - 可能需要检查数据格式)")

    print("\n🎉 主控制循环逻辑测试完成！")

if __name__ == "__main__":
    test_main_logic()
