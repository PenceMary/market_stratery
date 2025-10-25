# 快速切换单模型/多模型模式

## 🔄 方法1：修改配置文件

编辑 `intraday_trading_config.json`：

### 切换到单模型模式

```json
{
  "api_provider": "qwen",
  "api_providers": [],
  ...
}
```

或者

```json
{
  "api_provider": "qwen",
  "api_providers": ["qwen"],
  ...
}
```

### 切换到多模型模式

```json
{
  "api_provider": "qwen",
  "api_providers": ["qwen", "deepseek"],
  ...
}
```

## 📋 方法2：使用示例配置文件

### 单模型配置

复制 `intraday_trading_config.json`（默认配置）：
```bash
# Windows PowerShell
copy intraday_trading_config.json intraday_trading_config_backup.json

# Linux/Mac
cp intraday_trading_config.json intraday_trading_config_backup.json
```

### 多模型配置

使用示例配置：
```bash
# Windows PowerShell
copy intraday_trading_config_multi_model_example.json intraday_trading_config.json

# Linux/Mac
cp intraday_trading_config_multi_model_example.json intraday_trading_config.json
```

## 💡 快速测试

### 测试单模型

1. 修改配置：`"api_providers": ["qwen"]`
2. 运行：`python intraday_trading_main.py 688668`
3. 检查输出文件：`688668_鼎通科技_qwen_analysis_*.md`

### 测试多模型

1. 修改配置：`"api_providers": ["qwen", "deepseek"]`
2. 运行：`python intraday_trading_main.py 688668`
3. 检查输出文件：
   - `688668_鼎通科技_qwen_analysis_*.md`
   - `688668_鼎通科技_deepseek_analysis_*.md`

## ⚙️ 配置说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `api_provider` | 默认模型（向后兼容） | `"qwen"` |
| `api_providers` | 多模型列表（优先级更高） | `["qwen", "deepseek"]` |
| 空数组 `[]` | 使用单模型（api_provider） | `"api_providers": []` |
| 单元素数组 | 使用指定的单个模型 | `["qwen"]` |
| 多元素数组 | 使用多个模型对比 | `["qwen", "deepseek"]` |

## 🎯 使用建议

### 日常监控（推荐单模型）
- 节省API费用
- 快速获取分析结果
- 适合大批量股票筛选

配置：
```json
{
  "api_providers": ["qwen"]
}
```

### 重要决策（推荐多模型）
- 对比不同模型观点
- 提高决策准确性
- 适合重点股票深度分析

配置：
```json
{
  "api_providers": ["qwen", "deepseek"]
}
```

### 模型评估（推荐多模型）
- 对比模型表现
- 选择最适合的模型
- 积累历史数据对比

配置：
```json
{
  "api_providers": ["qwen", "deepseek"]
}
```

