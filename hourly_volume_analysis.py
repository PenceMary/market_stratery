#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分时数据小时量能分析脚本
分析每小时的U（上涨）、D（下跌）、E（平盘）量能占比
绘制柱状图并计算U/D比例
"""

import pandas as pd
from datetime import datetime
import numpy as np
#import tkinter as tk
#from tkinter import filedialog
import os

# 尝试导入matplotlib，如果失败则给出提示
# try:
#     import matplotlib.pyplot as plt
#     import matplotlib.dates as mdates
#     import matplotlib.font_manager as fm
#     MATPLOTLIB_AVAILABLE = True
#     
#     # 设置中文字体支持
#     plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 支持中文显示
#     plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# except ImportError:
#     MATPLOTLIB_AVAILABLE = False
#     print("警告: matplotlib库未安装，无法生成图表。请运行: pip install matplotlib")
MATPLOTLIB_AVAILABLE = False  # 临时禁用matplotlib


# def select_file():
#     """弹出文件选择对话框"""
#     root = tk.Tk()
#     root.withdraw()  # 隐藏主窗口
    
#     file_path = filedialog.askopenfilename(
#         title="选择股票数据CSV文件",
#         filetypes=[
#             ("CSV文件", "*.csv"),
#             ("所有文件", "*.*")
#         ],
#         initialdir="data_output"  # 默认打开data_output目录
#     )
    
#     root.destroy()  # 销毁窗口
#     return file_path


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

                # 计算量能
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
        {'name': '09:20-10:30', 'start_hour': 9, 'start_minute': 20, 'end_hour': 10, 'end_minute': 30},
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
            period_data = date_data[
                ((date_data['hour'] > period['start_hour']) | 
                 ((date_data['hour'] == period['start_hour']) & (date_data['datetime'].dt.minute >= period['start_minute']))) &
                ((date_data['hour'] < period['end_hour']) | 
                 ((date_data['hour'] == period['end_hour']) & (date_data['datetime'].dt.minute < period['end_minute'])))
            ]

            if len(period_data) == 0:
                continue

            # 分别统计U、D、E的量能
            u_data = period_data[period_data['kind'] == 'U']
            d_data = period_data[period_data['kind'] == 'D']
            e_data = period_data[period_data['kind'] == 'E']

            u_volume = u_data['volume_energy'].sum() if len(u_data) > 0 else 0
            d_volume = d_data['volume_energy'].sum() if len(d_data) > 0 else 0
            e_volume = e_data['volume_energy'].sum() if len(e_data) > 0 else 0

            total_volume = u_volume + d_volume + e_volume

            # 计算占比
            u_ratio = u_volume / total_volume if total_volume > 0 else 0
            d_ratio = d_volume / total_volume if total_volume > 0 else 0
            e_ratio = e_volume / total_volume if total_volume > 0 else 0

            # 计算U/D比例
            ud_ratio = u_volume / d_volume if d_volume > 0 else (u_volume if u_volume > 0 else 0)

            date_period_stats[date][period_name] = {
                'total_volume': total_volume,
                'u_volume': u_volume,
                'd_volume': d_volume,
                'e_volume': e_volume,
                'u_ratio': u_ratio,
                'd_ratio': d_ratio,
                'e_ratio': e_ratio,
                'ud_ratio': ud_ratio,
                'transaction_count': len(period_data),
                'period_name': period_name
            }

    return date_period_stats


# def plot_hourly_volume_text(date_period_stats):
#     """生成文本格式的图表（统一展示）"""
#     print("\n" + "=" * 130)
#     print("股票分时数据按日期-交易时间段量能分布文本图表（统一展示）")
#     print("=" * 130)

#     # 表头
#     print(f"{'日期':<12} {'时间段':<12} {'上涨量能':<15} {'下跌量能':<15} {'平盘量能':<15} {'U占比':<10} {'D占比':<10} {'E占比':<10} {'U/D比例':<12}")
#     print("-" * 130)

#     # 收集所有数据并按日期-时间段排序
#     all_data = []
#     for date in sorted(date_period_stats.keys()):
#         period_stats = date_period_stats[date]
#         for period_name in period_stats.keys():
#             stats = period_stats[period_name]
#             all_data.append({
#                 'date': date,
#                 'period_name': period_name,
#                 'stats': stats
#             })
    
#     # 统一显示所有数据
#     for item in all_data:
#         date = item['date']
#         period_name = item['period_name']
#         stats = item['stats']
#         u_vol = stats['u_volume']
#         d_vol = stats['d_volume']
#         e_vol = stats['e_volume']

#         print(f"{date} {period_name:<12} {u_vol:<13,.0f} {d_vol:<13,.0f} {e_vol:<13,.0f} "
#               f"{stats['u_ratio']:<10.1%} {stats['d_ratio']:<10.1%} {stats['e_ratio']:<10.1%} "
#               f"{stats['ud_ratio']:<12.2f}")

#         # 创建简单的文本柱状图
#         max_vol = max(u_vol, d_vol, e_vol) if max(u_vol, d_vol, e_vol) > 0 else 1
#         u_bar = '█' * int((u_vol / max_vol) * 15) if max_vol > 0 else ''
#         d_bar = '█' * int((d_vol / max_vol) * 15) if max_vol > 0 else ''
#         e_bar = '█' * int((e_vol / max_vol) * 15) if max_vol > 0 else ''

#         # 显示柱状图（简化版）
#         print(f"{'':<25} U:{u_bar:<15} D:{d_bar:<15} E:{e_bar:<15}")
#         print()

#     # U/D比例分析（统一展示）
#     print("\nU/D比例分析（按日期-交易时间段排序）:")
#     print("-" * 80)
#     for item in all_data:
#         date = item['date']
#         period_name = item['period_name']
#         ratio = item['stats']['ud_ratio']
        
#         if ratio > 1.2:
#             trend = "▲▲"  # 上升三角形，表示上涨强势
#         elif ratio > 0.8:
#             trend = "●"   # 圆点，表示相对平衡
#         else:
#             trend = "▼▼"  # 下降三角形，表示下跌强势

#         print(f"{date} {period_name} - U/D比例: {ratio:.2f} {trend}")

#     print("=" * 130)


# def create_ud_ratio_chart(date_period_stats, output_path):
#     """创建U/D比例柱状图并保存为PNG"""
#     if not MATPLOTLIB_AVAILABLE:
#         print("无法生成图表：matplotlib库未安装")
#         return
    
#     # 收集所有数据
#     all_data = []
#     for date in sorted(date_period_stats.keys()):
#         period_stats = date_period_stats[date]
#         for period_name in period_stats.keys():
#             stats = period_stats[period_name]
#             all_data.append({
#                 'date': date,
#                 'period_name': period_name,
#                 'ud_ratio': stats['ud_ratio']
#             })
    
#     if not all_data:
#         print("没有数据可以绘制图表")
#         return
    
#     # 准备数据
#     labels = []
#     ratios = []
#     colors = []
#     display_ratios = []  # 用于显示的数值标签
    
#     for item in all_data:
#         date_str = item['date'].strftime('%m-%d') if hasattr(item['date'], 'strftime') else str(item['date'])
#         period_name = item['period_name']
#         ratio = item['ud_ratio']
        
#         labels.append(f"{date_str}\n{period_name}")
        
#         # 根据U/D比例决定显示方式和颜色
#         if ratio > 1.2:
#             # 上涨强势：显示U/D比例，红色
#             ratios.append(ratio)
#             colors.append('#ff4444')  # 红色
#             display_ratios.append(f"U/D:{ratio:.2f}")
#         elif ratio > 0.8:
#             # 相对平衡：显示U/D比例，橙色
#             ratios.append(ratio)
#             colors.append('#ffaa00')  # 橙色
#             display_ratios.append(f"U/D:{ratio:.2f}")
#         else:
#             # 下跌强势：转换为D/U比例，绿色
#             d_u_ratio = 1.0 / ratio if ratio > 0 else 0
#             ratios.append(d_u_ratio)
#             colors.append('#44aa44')  # 绿色
#             display_ratios.append(f"D/U:{d_u_ratio:.2f}")
    
#     # 创建图表
#     plt.figure(figsize=(16, 10))
#     bars = plt.bar(range(len(labels)), ratios, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
#     # 设置图表属性
#     plt.title('股票U/D比例分析 - 按日期和交易时间段\n(下跌时显示D/U比例，便于直观对比)', fontsize=16, fontweight='bold', pad=20)
#     plt.xlabel('日期-时间段', fontsize=12)
#     plt.ylabel('比例值 (U/D 或 D/U)', fontsize=12)
    
#     # 设置x轴标签
#     plt.xticks(range(len(labels)), labels, rotation=45, ha='right', fontsize=10)
    
#     # 添加水平参考线
#     plt.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='平衡线 (U/D=1.0)')
#     plt.axhline(y=1.2, color='red', linestyle=':', alpha=0.7, label='上涨强势线 (U/D=1.2)')
#     plt.axhline(y=1.25, color='green', linestyle=':', alpha=0.7, label='下跌强势线 (D/U=1.25)')
    
#     # 在柱子上添加数值标签
#     for i, (bar, display_text) in enumerate(zip(bars, display_ratios)):
#         height = bar.get_height()
#         plt.text(bar.get_x() + bar.get_width()/2., height + 0.05,
#                 display_text, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
#     # 添加图例
#     plt.legend(loc='upper right', fontsize=10)
    
#     # 设置网格
#     plt.grid(True, alpha=0.3, axis='y')
    
#     # 调整布局
#     plt.tight_layout()
    
#     # 保存图片
#     plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
    
#     print(f"U/D比例柱状图已保存到: {output_path}")


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
        total_vol = stats['total_volume']
        
        # 如果是新的日期，先打印前一天的汇总数据
        if current_date is not None and date != current_date:
            # 打印前一天的汇总数据
            if daily_stats:
                total_transactions = sum(s['transaction_count'] for s in daily_stats)
                total_volume = sum(s['total_volume'] for s in daily_stats)
                total_u_volume = sum(s['u_volume'] for s in daily_stats)
                total_d_volume = sum(s['d_volume'] for s in daily_stats)
                total_e_volume = sum(s['e_volume'] for s in daily_stats)
                
                u_ratio = total_u_volume / total_volume if total_volume > 0 else 0
                d_ratio = total_d_volume / total_volume if total_volume > 0 else 0
                e_ratio = total_e_volume / total_volume if total_volume > 0 else 0
                ud_ratio = total_u_volume / total_d_volume if total_d_volume > 0 else (total_u_volume if total_u_volume > 0 else 0)
                
                print(f"日期：{current_date}，时间段：09:20-15:00，总笔数：{total_transactions}，总量能：{total_volume:,.0f}，U占比：{u_ratio:.2%}，D占比：{d_ratio:.2%}，E占比：{e_ratio:.2%}，U/D：{ud_ratio:.2f}")
                print()  # 空行分隔不同日期
            
            daily_stats = []
        
        current_date = date
        daily_stats.append(stats)
        
        # 打印当前时间段数据
        print(f"日期：{date}，时间段：{period_name}，总笔数：{stats['transaction_count']}，总量能：{total_vol:,.0f}，U占比：{stats['u_ratio']:.2%}，D占比：{stats['d_ratio']:.2%}，E占比：{stats['e_ratio']:.2%}，U/D：{stats['ud_ratio']:.2f}")
    
    # 打印最后一天的汇总数据
    if daily_stats:
        total_transactions = sum(s['transaction_count'] for s in daily_stats)
        total_volume = sum(s['total_volume'] for s in daily_stats)
        total_u_volume = sum(s['u_volume'] for s in daily_stats)
        total_d_volume = sum(s['d_volume'] for s in daily_stats)
        total_e_volume = sum(s['e_volume'] for s in daily_stats)
        
        u_ratio = total_u_volume / total_volume if total_volume > 0 else 0
        d_ratio = total_d_volume / total_volume if total_volume > 0 else 0
        e_ratio = total_e_volume / total_volume if total_volume > 0 else 0
        ud_ratio = total_u_volume / total_d_volume if total_d_volume > 0 else (total_u_volume if total_u_volume > 0 else 0)
        
        print(f"日期：{current_date}，时间段：09:20-15:00，总笔数：{total_transactions}，总量能：{total_volume:,.0f}，U占比：{u_ratio:.2%}，D占比：{d_ratio:.2%}，E占比：{e_ratio:.2%}，U/D：{ud_ratio:.2f}")

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
                total_vol = stats['total_volume']
                
                # 如果是新的日期，先写入前一天的汇总数据
                if current_date is not None and date != current_date:
                    # 写入前一天的汇总数据
                    if daily_stats:
                        total_transactions = sum(s['transaction_count'] for s in daily_stats)
                        total_volume = sum(s['total_volume'] for s in daily_stats)
                        total_u_volume = sum(s['u_volume'] for s in daily_stats)
                        total_d_volume = sum(s['d_volume'] for s in daily_stats)
                        total_e_volume = sum(s['e_volume'] for s in daily_stats)
                        
                        u_ratio = total_u_volume / total_volume if total_volume > 0 else 0
                        d_ratio = total_d_volume / total_volume if total_volume > 0 else 0
                        e_ratio = total_e_volume / total_volume if total_volume > 0 else 0
                        ud_ratio = total_u_volume / total_d_volume if total_d_volume > 0 else (total_u_volume if total_u_volume > 0 else 0)
                        
                        f.write(f"**日期**: {current_date}，**时间段**: 09:20-15:00，**总笔数**: {total_transactions}，**总量能**: {total_volume:,.0f}，**U占比**: {u_ratio:.2%}，**D占比**: {d_ratio:.2%}，**E占比**: {e_ratio:.2%}，**U/D**: {ud_ratio:.2f}\n\n")
                    
                    daily_stats = []
                
                current_date = date
                daily_stats.append(stats)
                
                # 写入当前时间段数据
                f.write(f"**日期**: {date}，**时间段**: {period_name}，**总笔数**: {stats['transaction_count']}，**总量能**: {total_vol:,.0f}，**U占比**: {stats['u_ratio']:.2%}，**D占比**: {stats['d_ratio']:.2%}，**E占比**: {stats['e_ratio']:.2%}，**U/D**: {stats['ud_ratio']:.2f}\n\n")
            
            # 写入最后一天的汇总数据
            if daily_stats:
                total_transactions = sum(s['transaction_count'] for s in daily_stats)
                total_volume = sum(s['total_volume'] for s in daily_stats)
                total_u_volume = sum(s['u_volume'] for s in daily_stats)
                total_d_volume = sum(s['d_volume'] for s in daily_stats)
                total_e_volume = sum(s['e_volume'] for s in daily_stats)
                
                u_ratio = total_u_volume / total_volume if total_volume > 0 else 0
                d_ratio = total_d_volume / total_volume if total_volume > 0 else 0
                e_ratio = total_e_volume / total_volume if total_volume > 0 else 0
                ud_ratio = total_u_volume / total_d_volume if total_d_volume > 0 else (total_u_volume if total_u_volume > 0 else 0)
                
                f.write(f"**日期**: {current_date}，**时间段**: 09:20-15:00，**总笔数**: {total_transactions}，**总量能**: {total_volume:,.0f}，**U占比**: {u_ratio:.2%}，**D占比**: {d_ratio:.2%}，**E占比**: {e_ratio:.2%}，**U/D**: {ud_ratio:.2f}\n\n")
            
            # 写入统计信息
            f.write("---\n\n")
            f.write("## 统计信息\n\n")
            f.write(f"- **分析交易日数**: {len(date_period_stats)}\n")
            f.write(f"- **总时间段组合数**: {sum(len(periods) for periods in date_period_stats.values())}\n")
            f.write(f"- **分析完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 写入说明
            f.write("## 说明\n\n")
            f.write("- **U**: 上涨交易\n")
            f.write("- **D**: 下跌交易\n")
            f.write("- **E**: 平盘交易\n")
            f.write("- **U/D**: 上涨量能与下跌量能的比例\n")
            f.write("- **量能**: 价格 × 成交量\n")
            f.write("- **时间段**: 09:20-10:30, 10:30-11:30, 13:00-14:00, 14:00-15:00\n")
        
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

        # 打印分析结果
        print_hourly_analysis(date_period_stats)

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
    
    # 弹出文件选择对话框
    print("请选择要分析的股票数据CSV文件...")
    #file_path = select_file()
    
    # if not file_path:
    #     print("未选择文件，程序退出")
    #     return
    
    # print(f"已选择文件: {file_path}")

    # # 调用分析函数
    # analyze_csv_file(file_path)


if __name__ == "__main__":
    main()
