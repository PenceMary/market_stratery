#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分时数据小时量能分析脚本
分析每小时的外盘（U）、内盘（D）、中性盘（E）分布
计算UD比（外盘/内盘）
"""

import pandas as pd
from datetime import datetime
import numpy as np
import os


def load_and_parse_data(file_path):
    """加载并解析CSV数据"""
    data = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到分时成交数据开始和结束的位置
    data_start = -1
    data_end = -1
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped == '=== 分时成交数据 ===':
            data_start = i
        elif line_stripped == '=== 日K线数据 ===':
            data_end = i
            break
    
    if data_start == -1:
        raise ValueError("未找到分时成交数据开始标记")
    
    if data_end == -1:
        raise ValueError("未找到分时成交数据结束标记")
    
    print(f"找到分时成交数据范围: 第{data_start+1}行到第{data_end}行")
    
    # 在指定范围内查找数据标题行
    title_line = -1
    for i in range(data_start, data_end):
        if lines[i].strip() == 'ticktime,price,volume,prev_price,kind':
            title_line = i
            break
    
    if title_line == -1:
        raise ValueError("在分时成交数据范围内未找到数据标题行")
    
    print(f"找到数据标题行: 第{title_line+1}行")
    print(f"将解析第{title_line+2}行到第{data_end}行的数据")
    
    # 解析数据行（从标题行后开始，到日K线数据前结束）
    for line in lines[title_line + 1:data_end]:
        if not line.strip() or line.startswith('==='):
            continue

        try:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                ticktime = parts[0]
                price = float(parts[1])
                volume = int(parts[2])
                kind = parts[4]

                # 计算量能（成交金额 = 价格 × 成交量）
                volume_energy = price * volume

                # 解析时间
                dt = datetime.strptime(ticktime, '%Y-%m-%d %H:%M:%S')
                date = dt.date()
                hour = dt.hour

                data.append({
                    'datetime': dt,
                    'date': date,
                    'hour': hour,
                    'price': price,
                    'volume': volume,
                    'volume_energy': volume_energy,
                    'kind': kind
                })
        except (ValueError, IndexError) as e:
            print(f"解析行失败: {line.strip()}, 错误: {e}")
            continue

    return pd.DataFrame(data)


def analyze_hourly_volume(df):
    """分析每个日期-交易时间段的量能分布"""
    date_period_stats = {}

    # 定义交易时间段
    trading_periods = [
        {'name': '09:25', 'start_hour': 9, 'start_minute': 25, 'end_hour': 9, 'end_minute': 25, 'is_single_time': True},
        {'name': '09:30-10:30', 'start_hour': 9, 'start_minute': 30, 'end_hour': 10, 'end_minute': 30},
        {'name': '10:30-11:30', 'start_hour': 10, 'start_minute': 30, 'end_hour': 11, 'end_minute': 30},
        {'name': '13:00-14:00', 'start_hour': 13, 'start_minute': 0, 'end_hour': 14, 'end_minute': 0},
        {'name': '14:00-15:00', 'start_hour': 14, 'start_minute': 0, 'end_hour': 15, 'end_minute': 0}
    ]

    # 获取所有唯一的日期
    unique_dates = sorted(df['date'].unique())
    
    for date in unique_dates:
        date_data = df[df['date'] == date]
        date_period_stats[date] = {}
        
        for period in trading_periods:
            period_name = period['name']
            
            # 筛选该时间段内的数据
            if period.get('is_single_time', False):
                # 特殊处理单个时间点（如09:25）
                period_data = date_data[
                    (date_data['hour'] == period['start_hour']) & 
                    (date_data['datetime'].dt.minute == period['start_minute'])
                ]
            else:
                # 处理时间段
                period_data = date_data[
                    ((date_data['hour'] > period['start_hour']) | 
                     ((date_data['hour'] == period['start_hour']) & (date_data['datetime'].dt.minute >= period['start_minute']))) &
                    ((date_data['hour'] < period['end_hour']) | 
                     ((date_data['hour'] == period['end_hour']) & (date_data['datetime'].dt.minute < period['end_minute'])))
                ]

            if len(period_data) == 0:
                continue

            # 分别统计U、D、E的量能和成交量
            # U = 外盘（主动性买入），D = 内盘（主动性卖出），E = 中性盘
            u_data = period_data[period_data['kind'] == 'U']
            d_data = period_data[period_data['kind'] == 'D']
            e_data = period_data[period_data['kind'] == 'E']

            u_volume = u_data['volume_energy'].sum() if len(u_data) > 0 else 0
            d_volume = d_data['volume_energy'].sum() if len(d_data) > 0 else 0
            e_volume = e_data['volume_energy'].sum() if len(e_data) > 0 else 0

            # 计算成交量（股数）
            u_volume_count = u_data['volume'].sum() if len(u_data) > 0 else 0
            d_volume_count = d_data['volume'].sum() if len(d_data) > 0 else 0
            e_volume_count = e_data['volume'].sum() if len(e_data) > 0 else 0
            total_volume_count = u_volume_count + d_volume_count + e_volume_count

            # 计算占比（基于成交量股数）
            total_volume_count_sum = u_volume_count + d_volume_count + e_volume_count
            u_ratio = u_volume_count / total_volume_count_sum if total_volume_count_sum > 0 else 0
            d_ratio = d_volume_count / total_volume_count_sum if total_volume_count_sum > 0 else 0
            e_ratio = e_volume_count / total_volume_count_sum if total_volume_count_sum > 0 else 0

            # 计算UD比（外盘/内盘比例，反映买卖力量对比）
            if period.get('is_single_time', False):
                # 单个时间点（如09:25集合竞价）不计算UD比
                ud_ratio = 'NA'
            else:
                # 时间段计算UD比，比值越大说明买盘越强
                ud_ratio = u_volume_count / d_volume_count if d_volume_count > 0 else (u_volume_count if u_volume_count > 0 else 0)

            date_period_stats[date][period_name] = {
                'total_volume_count': total_volume_count,
                'u_volume_count': u_volume_count,
                'd_volume_count': d_volume_count,
                'e_volume_count': e_volume_count,
                'u_ratio': u_ratio,
                'd_ratio': d_ratio,
                'e_ratio': e_ratio,
                'ud_ratio': ud_ratio,
                'transaction_count': len(period_data),
                'period_name': period_name
            }

    return date_period_stats


def print_hourly_analysis(date_period_stats):
    """打印所有日期-交易时间段分析结果（统一展示）"""
    print("股票分时数据按日期-交易时间段量能分析结果（统一展示）")
    print("=" * 80)

    # 收集所有数据并按日期-时间段排序
    all_data = []
    for date in sorted(date_period_stats.keys()):
        period_stats = date_period_stats[date]
        for period_name in period_stats.keys():
            stats = period_stats[period_name]
            all_data.append({
                'date': date,
                'period_name': period_name,
                'stats': stats
            })
    
    # 按日期分组并显示数据
    current_date = None
    daily_stats = []
    
    for item in all_data:
        date = item['date']
        period_name = item['period_name']
        stats = item['stats']
        
        # 如果是新的日期，先打印前一天的汇总数据
        if current_date is not None and date != current_date:
            # 打印前一天的汇总数据
            if daily_stats:
                # 排除09:25时间段，只计算09:30-15:00的汇总数据
                filtered_stats = [s for s in daily_stats if s.get('period_name') != '09:25']
                
                if filtered_stats:
                    total_transactions = sum(s['transaction_count'] for s in filtered_stats)
                    total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                    total_u_volume_count = sum(s['u_volume_count'] for s in filtered_stats)
                    total_d_volume_count = sum(s['d_volume_count'] for s in filtered_stats)
                    total_e_volume_count = sum(s['e_volume_count'] for s in filtered_stats)
                    
                    u_ratio = total_u_volume_count / total_volume_count if total_volume_count > 0 else 0
                    d_ratio = total_d_volume_count / total_volume_count if total_volume_count > 0 else 0
                    e_ratio = total_e_volume_count / total_volume_count if total_volume_count > 0 else 0
                    ud_ratio = total_u_volume_count / total_d_volume_count if total_d_volume_count > 0 else (total_u_volume_count if total_u_volume_count > 0 else 0)
                    
                    print(f"日期：{current_date}，时间段：09:30-15:00，总笔数：{total_transactions}，成交量：{total_volume_count:,.0f}，外盘占比：{u_ratio:.2%}，内盘占比：{d_ratio:.2%}，中性盘占比：{e_ratio:.2%}，UD比：{ud_ratio:.2f}")
                    print()  # 空行分隔不同日期
            
            daily_stats = []
        
        current_date = date
        daily_stats.append(stats)
        
        # 打印当前时间段数据
        ud_display = stats['ud_ratio'] if stats['ud_ratio'] != 'NA' else 'NA'
        print(f"日期：{date}，时间段：{period_name}，总笔数：{stats['transaction_count']}，成交量：{stats['total_volume_count']:,.0f}，外盘占比：{stats['u_ratio']:.2%}，内盘占比：{stats['d_ratio']:.2%}，中性盘占比：{stats['e_ratio']:.2%}，UD比：{ud_display}")
    
    # 打印最后一天的汇总数据
    if daily_stats:
        # 排除09:25时间段，只计算09:30-15:00的汇总数据
        filtered_stats = [s for s in daily_stats if s.get('period_name') != '09:25']
        
        if filtered_stats:
            total_transactions = sum(s['transaction_count'] for s in filtered_stats)
            total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
            total_u_volume_count = sum(s['u_volume_count'] for s in filtered_stats)
            total_d_volume_count = sum(s['d_volume_count'] for s in filtered_stats)
            total_e_volume_count = sum(s['e_volume_count'] for s in filtered_stats)
            
            u_ratio = total_u_volume_count / total_volume_count if total_volume_count > 0 else 0
            d_ratio = total_d_volume_count / total_volume_count if total_volume_count > 0 else 0
            e_ratio = total_e_volume_count / total_volume_count if total_volume_count > 0 else 0
            ud_ratio = total_u_volume_count / total_d_volume_count if total_d_volume_count > 0 else (total_u_volume_count if total_u_volume_count > 0 else 0)
            
            print(f"日期：{current_date}，时间段：09:30-15:00，总笔数：{total_transactions}，成交量：{total_volume_count:,.0f}，外盘占比：{u_ratio:.2%}，内盘占比：{d_ratio:.2%}，中性盘占比：{e_ratio:.2%}，UD比：{ud_ratio:.2f}")

    print("=" * 80)


def save_hourly_analysis_to_md(date_period_stats, output_path):
    """将分析结果保存到MD文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入MD文件头部
            f.write("# 股票分时数据按日期-交易时间段量能分析结果\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # 写入分析结果
            f.write("## 分析结果\n\n")
            
            # 收集所有数据并按日期-时间段排序
            all_data = []
            for date in sorted(date_period_stats.keys()):
                period_stats = date_period_stats[date]
                for period_name in period_stats.keys():
                    stats = period_stats[period_name]
                    all_data.append({
                        'date': date,
                        'period_name': period_name,
                        'stats': stats
                    })
            
            # 按日期分组并写入数据
            current_date = None
            daily_stats = []
            
            for item in all_data:
                date = item['date']
                period_name = item['period_name']
                stats = item['stats']
                
                # 如果是新的日期，先写入前一天的汇总数据
                if current_date is not None and date != current_date:
                    # 写入前一天的汇总数据
                    if daily_stats:
                        # 排除09:25时间段，只计算09:30-15:00的汇总数据
                        filtered_stats = [s for s in daily_stats if s.get('period_name') != '09:25']
                        
                        if filtered_stats:
                            total_transactions = sum(s['transaction_count'] for s in filtered_stats)
                            total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                            total_u_volume_count = sum(s['u_volume_count'] for s in filtered_stats)
                            total_d_volume_count = sum(s['d_volume_count'] for s in filtered_stats)
                            total_e_volume_count = sum(s['e_volume_count'] for s in filtered_stats)
                            
                            u_ratio = total_u_volume_count / total_volume_count if total_volume_count > 0 else 0
                            d_ratio = total_d_volume_count / total_volume_count if total_volume_count > 0 else 0
                            e_ratio = total_e_volume_count / total_volume_count if total_volume_count > 0 else 0
                            ud_ratio = total_u_volume_count / total_d_volume_count if total_d_volume_count > 0 else (total_u_volume_count if total_u_volume_count > 0 else 0)
                            
                            f.write(f"**日期**: {current_date}，**时间段**: 09:30-15:00，**总笔数**: {total_transactions}，**成交量**: {total_volume_count:,.0f}，**外盘占比**: {u_ratio:.2%}，**内盘占比**: {d_ratio:.2%}，**中性盘占比**: {e_ratio:.2%}，**UD比**: {ud_ratio:.2f}\n\n")
                    
                    daily_stats = []
                
                current_date = date
                daily_stats.append(stats)
                
                # 写入当前时间段数据
                ud_display = stats['ud_ratio'] if stats['ud_ratio'] != 'NA' else 'NA'
                f.write(f"**日期**: {date}，**时间段**: {period_name}，**总笔数**: {stats['transaction_count']}，**成交量**: {stats['total_volume_count']:,.0f}，**外盘占比**: {stats['u_ratio']:.2%}，**内盘占比**: {stats['d_ratio']:.2%}，**中性盘占比**: {stats['e_ratio']:.2%}，**UD比**: {ud_display}\n\n")
            
            # 写入最后一天的汇总数据
            if daily_stats:
                # 排除09:25时间段，只计算09:30-15:00的汇总数据
                filtered_stats = [s for s in daily_stats if s.get('period_name') != '09:25']
                
                if filtered_stats:
                    total_transactions = sum(s['transaction_count'] for s in filtered_stats)
                    total_volume_count = sum(s['total_volume_count'] for s in filtered_stats)
                    total_u_volume_count = sum(s['u_volume_count'] for s in filtered_stats)
                    total_d_volume_count = sum(s['d_volume_count'] for s in filtered_stats)
                    total_e_volume_count = sum(s['e_volume_count'] for s in filtered_stats)
                    
                    u_ratio = total_u_volume_count / total_volume_count if total_volume_count > 0 else 0
                    d_ratio = total_d_volume_count / total_volume_count if total_volume_count > 0 else 0
                    e_ratio = total_e_volume_count / total_volume_count if total_volume_count > 0 else 0
                    ud_ratio = total_u_volume_count / total_d_volume_count if total_d_volume_count > 0 else (total_u_volume_count if total_u_volume_count > 0 else 0)
                    
                    f.write(f"**日期**: {current_date}，**时间段**: 09:30-15:00，**总笔数**: {total_transactions}，**成交量**: {total_volume_count:,.0f}，**外盘占比**: {u_ratio:.2%}，**内盘占比**: {d_ratio:.2%}，**中性盘占比**: {e_ratio:.2%}，**UD比**: {ud_ratio:.2f}\n\n")
            
            # 写入统计信息
            f.write("---\n\n")
            f.write("## 统计信息\n\n")
            f.write(f"- **分析交易日数**: {len(date_period_stats)}\n")
            f.write(f"- **总时间段组合数**: {sum(len(periods) for periods in date_period_stats.values())}\n")
            f.write(f"- **分析完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 写入说明
            f.write("## 说明\n\n")
            f.write("- **U**: 外盘（主动性买入）\n")
            f.write("- **D**: 内盘（主动性卖出）\n")
            f.write("- **E**: 中性盘\n")
            f.write("- **UD比**: 外盘/内盘比例，数值越大说明买盘越强\n")
            f.write("- **时间段**: 09:25（集合竞价）, 09:30-10:30, 10:30-11:30, 13:00-14:00, 14:00-15:00\n")
        
        print(f"分析结果已保存到: {output_path}")
        
    except Exception as e:
        print(f"保存MD文件时出错: {e}")
        import traceback
        traceback.print_exc()


def analyze_csv_file(file_path):
    """
    分析指定的CSV文件，返回分析结果
    
    :param file_path: str, CSV文件路径
    :return: tuple, (date_period_stats, md_path) 分析结果和MD文件路径
    """
    print(f"开始分析文件: {file_path}")
    
    try:
        # 加载和解析数据
        print("正在加载数据...")
        df = load_and_parse_data(file_path)
        print(f"数据加载完成，共 {len(df)} 笔交易记录")

        if len(df) == 0:
            print("警告: 数据为空")
            return None, None

        # 分析每个日期-交易时间段量能
        print("正在分析每个日期-交易时间段量能...")
        date_period_stats = analyze_hourly_volume(df)
        total_combinations = sum(len(periods) for periods in date_period_stats.values())
        print(f"分析完成，共 {len(date_period_stats)} 个交易日，{total_combinations} 个日期-时间段组合")

        # 保存分析结果到MD文件
        print("正在保存分析结果到MD文件...")
        csv_dir = os.path.dirname(file_path)
        csv_name = os.path.splitext(os.path.basename(file_path))[0]
        md_path = os.path.join(csv_dir, f"{csv_name}_hourly_analysis.md")
        
        save_hourly_analysis_to_md(date_period_stats, md_path)

        return date_period_stats, md_path

    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return None, None
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """主函数"""
    print("脚本开始执行...")
    print("此脚本作为模块被其他程序调用，不直接运行")


if __name__ == "__main__":
    main()
