# 日内交易分析系统架构说明

## 系统概览

这是一个模块化的A股日内交易分析系统，通过集成实时数据获取、技术指标计算和大模型分析，为交易者提供专业的交易建议。

## 核心模块

### 1. 数据获取层 (`intraday_data_fetcher.py`)

**职责**: 从各种数据源获取股票相关数据

**主要类**: `IntradayDataFetcher`

**核心方法**:
- `get_realtime_quote()` - 获取实时行情
- `get_today_intraday_data()` - 获取今日分时数据
- `get_historical_intraday_data()` - 获取历史分时数据
- `get_order_book()` - 获取五档盘口数据
- `get_market_indices()` - 获取大盘指数
- `get_sector_info()` - 获取板块信息
- `get_market_sentiment()` - 获取市场情绪
- `get_kline_data()` - 获取K线数据

**数据来源**: akshare (A股数据接口库)

---

### 2. 技术指标计算层 (`intraday_indicators.py`)

**职责**: 计算各类技术指标

**主要类**: `TechnicalIndicators`

**支持的指标**:
- EMA (指数移动平均线)
- MACD (指数平滑异同移动平均线)
- RSI (相对强弱指标)
- KDJ (随机指标)
- BOLL (布林带)
- MA (简单移动平均线)
- Volume MA (成交量均线)

**分析方法**:
- `analyze_intraday_data()` - 分析分时数据
- `analyze_kline_data()` - 分析K线数据

---

### 3. 提示词构建层 (`intraday_prompt_builder.py`)

**职责**: 将获取的数据整合并构建发送给大模型的提示词

**主要类**: `PromptBuilder`

**核心功能**:
- 加载提示词模板
- 填充实时数据
- 格式化技术指标
- 构建完整的分析请求

**模板文件**: `a_stock_trading_prompt_template.txt`

---

### 4. 主控制层 (`intraday_trading_main.py`)

**职责**: 协调各个模块，控制整体分析流程

**主要类**: `IntradayTradingAnalyzer`

**工作流程**:
```
1. 加载配置 → 2. 获取数据 → 3. 构建提示词 → 
4. 调用大模型 → 5. 保存结果 → 6. 显示输出
```

**支持功能**:
- 单股分析
- 批量分析
- 交易时间验证
- 结果保存（JSON + Markdown）

---

## 配置系统

### 主配置文件 (`intraday_trading_config.json`)

```json
{
  "api_provider": "qwen",           // API提供商
  "data_config": {...},             // 数据获取配置
  "trading_time": {...},            // 交易时间设置
  "risk_control": {...},            // 风险控制参数
  "output_config": {...}            // 输出配置
}
```

### 密钥配置文件 (`keys.json`)

```json
{
  "api_key": "...",                 // 大模型API密钥
  "email_sender": "...",            // 发件人邮箱
  "email_password": "...",          // 邮箱密码
  "email_receivers": [...]          // 收件人列表
}
```

---

## 数据流

```
                    ┌─────────────────────┐
                    │   用户输入股票代码    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  IntradayTrading    │
                    │     Analyzer        │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ IntradayData     │ │  Technical       │ │  Prompt          │
│ Fetcher          │ │  Indicators      │ │  Builder         │
│                  │ │                  │ │                  │
│ - 实时行情        │ │ - 计算EMA        │ │ - 加载模板        │
│ - 分时数据        │ │ - 计算MACD       │ │ - 填充数据        │
│ - 盘口数据        │ │ - 计算RSI        │ │ - 格式化输出      │
│ - 大盘指数        │ │ - 计算KDJ        │ │                  │
│ - 板块信息        │ │ - 计算BOLL       │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   大模型 API        │
                    │  (Qwen/DeepSeek)    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   分析结果输出       │
                    │  - JSON文件         │
                    │  - Markdown报告     │
                    │  - 控制台显示       │
                    └─────────────────────┘
```

---

## 扩展点

### 1. 添加新的数据源

在 `intraday_data_fetcher.py` 中添加新方法:

```python
def get_custom_data(self, stock_code: str) -> Dict:
    # 实现自定义数据获取逻辑
    pass
```

### 2. 添加新的技术指标

在 `intraday_indicators.py` 中添加静态方法:

```python
@staticmethod
def calculate_custom_indicator(data: pd.Series) -> pd.Series:
    # 实现自定义指标计算逻辑
    pass
```

### 3. 自定义提示词模板

修改 `a_stock_trading_prompt_template.txt` 或在 `PromptBuilder` 类中自定义构建逻辑。

### 4. 支持新的大模型

在 `intraday_trading_config.json` 中添加配置:

```json
{
  "api_config": {
    "new_model": {
      "model": "model-name",
      "base_url": "https://api.example.com",
      "timeout": 300
    }
  }
}
```

---

## 性能优化建议

### 1. 数据缓存

- 可在 `IntradayDataFetcher` 中实现缓存机制
- 避免短时间内重复请求相同数据

### 2. 异步处理

- 对于批量分析，可考虑使用异步IO
- 提高数据获取效率

### 3. 并行计算

- 技术指标计算可以并行处理
- 使用多进程/多线程提升性能

---

## 安全考虑

### 1. API密钥保护

- `keys.json` 不应提交到版本控制
- 建议使用环境变量存储敏感信息

### 2. 数据验证

- 所有外部数据应进行有效性检查
- 防止异常数据导致系统崩溃

### 3. 错误处理

- 完善的异常捕获机制
- 友好的错误提示信息

---

## 测试工具

### 1. 数据获取测试 (`test_intraday_data.py`)

测试所有数据获取功能，不调用大模型API，节省成本。

### 2. 快速启动检查 (`quick_start.py`)

检查环境配置，引导用户快速开始。

---

## 依赖关系

```
intraday_trading_main.py
  ├── intraday_data_fetcher.py
  │     └── akshare
  │     └── pandas
  ├── intraday_indicators.py
  │     └── pandas
  │     └── numpy
  ├── intraday_prompt_builder.py
  └── openai
```

---

## 版本历史

- **v1.0** (2025-10-24)
  - 初始版本
  - 支持基本的日内交易分析
  - 集成Qwen和DeepSeek模型
  - 完整的技术指标体系

---

## 待开发功能

1. **数据可视化**
   - 分时图展示
   - K线图展示
   - 技术指标图表

2. **策略回测**
   - 历史数据回测
   - 策略效果评估

3. **实时监控**
   - Websocket实时推送
   - 价格预警功能

4. **机器学习集成**
   - 价格预测模型
   - 量化因子挖掘

5. **风险管理**
   - 自动仓位计算
   - 动态止损调整

---

## 贡献指南

欢迎贡献代码！请遵循以下原则：

1. **代码规范**: 遵循PEP 8规范
2. **文档完善**: 为新功能添加详细注释
3. **测试覆盖**: 编写单元测试
4. **模块化**: 保持模块职责单一
5. **向后兼容**: 避免破坏现有API

---

**最后更新**: 2025-10-24  
**维护者**: 开发团队  
**许可证**: MIT

