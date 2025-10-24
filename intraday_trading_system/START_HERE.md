# 🚀 日内交易分析系统 - 快速开始

## 📁 当前位置
`market_stratery/intraday_trading_system/`

## ⚡ 快速开始（3步）

### 1️⃣ 检查环境
```bash
cd intraday_trading_system
python quick_start.py
```

### 2️⃣ 配置API密钥
复制并编辑密钥文件：
```bash
copy intraday_trading_example_keys.json keys.json
# 编辑 keys.json，填入您的 Qwen 或 DeepSeek API密钥
```

### 3️⃣ 开始分析
```bash
# 测试数据获取（不消耗API额度）
python test_intraday_data.py 600000

# 完整分析（调用大模型）
python intraday_trading_main.py 600000
```

## 📚 完整文档

- **使用手册**: 查看 `INTRADAY_TRADING_README.md`
- **系统架构**: 查看 `SYSTEM_ARCHITECTURE.md`

## 🎯 常用命令

```bash
# 分析单只股票
python intraday_trading_main.py 600000

# 批量分析多只股票
python intraday_trading_main.py 600000 000001 300750

# 仅测试数据获取
python test_intraday_data.py 600000
```

## 📂 文件结构

```
intraday_trading_system/
├── START_HERE.md                    # 👈 你在这里
├── quick_start.py                   # 环境检查工具
├── intraday_trading_main.py         # 主程序
├── intraday_data_fetcher.py         # 数据获取
├── intraday_indicators.py           # 技术指标
├── intraday_prompt_builder.py       # 提示词构建
├── test_intraday_data.py            # 测试工具
├── intraday_trading_config.json     # 系统配置
├── intraday_trading_example_keys.json  # 密钥示例
├── a_stock_trading_prompt_template.txt # 提示词模板
├── INTRADAY_TRADING_README.md       # 完整文档
├── SYSTEM_ARCHITECTURE.md           # 架构说明
└── keys.json                        # 🔑 需要创建（包含真实API密钥）
```

## ⚠️ 注意事项

1. **API密钥**: 必须先配置 `keys.json` 才能使用完整功能
2. **交易时间**: 建议在交易时间内使用（09:30-11:30, 13:00-15:00）
3. **仅供参考**: 分析结果仅供参考，不构成投资建议

## 🆘 遇到问题？

1. 运行 `python quick_start.py` 检查环境
2. 查看 `INTRADAY_TRADING_README.md` 的故障排除章节
3. 检查是否正确配置了 `keys.json`

---

**立即开始**: 运行 `python quick_start.py` 👈

