# 多模型对比分析功能说明

## 🎯 功能概述

系统现在支持同时使用多个大模型（如Qwen和DeepSeek）对同一只股票进行分析，帮助你对比不同模型的分析结果，做出更全面的投资决策。

## 📋 配置方法

### 1. 配置文件设置

在 `intraday_trading_config.json` 中配置要使用的模型：

```json
{
  "api_provider": "qwen",
  "api_providers": ["qwen", "deepseek"],
  "api_config": {
    "qwen": {
      "model": "qwen3-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 300
    },
    "deepseek": {
      "model": "deepseek-reasoner",
      "base_url": "https://api.deepseek.com/v1",
      "timeout": 300
    }
  }
}
```

**配置说明：**
- `api_provider`: 单模型模式下使用的默认模型
- `api_providers`: 多模型对比模式，配置要使用的模型列表
  - 如果配置了此项，系统会依次调用列表中的所有模型
  - 如果留空或不配置，则只使用 `api_provider` 指定的单个模型

### 2. API密钥配置

在 `keys.json` 中配置每个模型的API密钥：

```json
{
  "qwen_api_key": "sk-your-qwen-api-key",
  "deepseek_api_key": "sk-your-deepseek-api-key",
  "email_sender": "your-email@163.com",
  "email_password": "your-email-password",
  "email_receivers": ["receiver@example.com"]
}
```

## 🚀 使用方法

### 单模型模式

如果只想使用一个模型，有两种方式：

**方式1：** 只配置 `api_provider`，不配置 `api_providers`
```json
{
  "api_provider": "qwen"
}
```

**方式2：** 配置 `api_providers` 为单个模型
```json
{
  "api_providers": ["qwen"]
}
```

### 多模型对比模式

配置 `api_providers` 为多个模型：
```json
{
  "api_providers": ["qwen", "deepseek"]
}
```

然后运行分析：
```bash
python intraday_trading_main.py 688668
```

## 📊 输出结果

### 文件命名规则

每个模型会生成独立的分析文件，文件名包含模型标识：

**单模型模式：**
- `688668_鼎通科技_analysis_20251025_213911.md`
- `688668_鼎通科技_analysis_20251025_213911.html`
- `688668_鼎通科技_result_20251025_213911.json`

**多模型模式：**
- `688668_鼎通科技_qwen_analysis_20251025_213911.md`
- `688668_鼎通科技_qwen_analysis_20251025_213911.html`
- `688668_鼎通科技_qwen_result_20251025_213911.json`
- `688668_鼎通科技_deepseek_analysis_20251025_213911.md`
- `688668_鼎通科技_deepseek_analysis_20251025_213911.html`
- `688668_鼎通科技_deepseek_result_20251025_213911.json`

### 邮件通知

每个模型的分析结果会单独发送邮件，邮件主题格式：

```
[qwen3-max] 观望 鼎通科技(688668)
[deepseek-reasoner] 买入 鼎通科技(688668) - 强烈推荐
```

## 💡 使用场景

### 场景1：对比不同模型的观点

当你不确定某只股票的走势时，可以同时使用多个模型分析，对比它们的：
- 操作方向（买入/卖出/持有/观望）
- 价格预测
- 风险评估
- 技术分析角度

### 场景2：验证分析结论

如果多个模型给出相同的建议，可以增强你的决策信心；如果观点分歧较大，则需要更谨慎地评估。

### 场景3：学习不同的分析思路

不同模型可能从不同角度分析同一只股票，帮助你学习更全面的分析方法。

## ⚙️ 高级配置

### 调整模型顺序

模型会按照 `api_providers` 数组中的顺序依次调用：
```json
{
  "api_providers": ["deepseek", "qwen"]
}
```

### 模型间等待时间

为避免API限制，系统会在调用不同模型之间等待2秒。如需调整，可修改代码中的 `time.sleep(2)`。

## 🔍 运行日志

多模型模式下的日志示例：

```
============================================================
开始分析股票: 688668
分析时间: 2025-10-25 21:39:11
使用模型: qwen, deepseek
============================================================

📊 步骤1: 获取股票数据...
  - 获取实时行情...
  - 获取今日分时数据...
  ...

📝 步骤2: 构建分析提示词...

🤖 步骤3-QWEN: 调用QWEN模型进行分析...
  - 使用模型: qwen3-max
  - API地址: https://dashscope.aliyuncs.com/compatible-mode/v1

============================================================
💬 QWEN模型分析结果：
============================================================
[分析内容...]

💾 步骤4-QWEN: 保存QWEN分析结果...
  ✅ 分析结果(JSON)已保存: ...
  ✅ 分析报告(Markdown)已保存: ...
  ✅ HTML报告已生成: ...

📧 准备发送邮件...
  ✅ 已添加附件: ...
  ✅ 邮件发送成功！

⏳ 等待2秒后调用下一个模型...

🤖 步骤3-DEEPSEEK: 调用DEEPSEEK模型进行分析...
  - 使用模型: deepseek-reasoner
  - API地址: https://api.deepseek.com/v1
...
```

## ⚠️ 注意事项

1. **API费用**：使用多个模型会产生多次API调用费用，请注意控制成本
2. **API限制**：注意各个API提供商的调用频率限制
3. **分析时间**：多模型模式会增加总体分析时间
4. **邮件数量**：每个模型会发送一封邮件，请确保邮箱不会被标记为垃圾邮件

## 🔧 故障排除

### 问题1：某个模型调用失败

系统会自动跳过失败的模型，继续调用其他模型：
```
⚠️ DEEPSEEK模型分析失败，跳过
```

### 问题2：API密钥未配置

系统会在启动时检查所有模型的API密钥：
```
❌ 未配置以下模型的 API Key: deepseek (deepseek_api_key)
💡 请在 keys.json 中配置相应的API密钥
```

### 问题3：只想临时使用单个模型

修改配置文件中的 `api_providers`：
```json
{
  "api_providers": ["qwen"]
}
```

或者注释掉该配置项，系统会自动使用 `api_provider` 的值。

## 📝 示例配置

### 示例1：只使用Qwen

```json
{
  "api_provider": "qwen",
  "api_providers": [],
  "api_config": {
    "qwen": {
      "model": "qwen3-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 300
    }
  }
}
```

### 示例2：同时使用Qwen和DeepSeek

```json
{
  "api_provider": "qwen",
  "api_providers": ["qwen", "deepseek"],
  "api_config": {
    "qwen": {
      "model": "qwen3-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 300
    },
    "deepseek": {
      "model": "deepseek-reasoner",
      "base_url": "https://api.deepseek.com/v1",
      "timeout": 300
    }
  }
}
```

### 示例3：使用三个模型

```json
{
  "api_provider": "qwen",
  "api_providers": ["qwen", "deepseek", "custom"],
  "api_config": {
    "qwen": {
      "model": "qwen3-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 300
    },
    "deepseek": {
      "model": "deepseek-reasoner",
      "base_url": "https://api.deepseek.com/v1",
      "timeout": 300
    },
    "custom": {
      "model": "your-custom-model",
      "base_url": "https://your-api-endpoint/v1",
      "timeout": 300
    }
  }
}
```

## 🎓 最佳实践

1. **先测试单模型**：确保每个模型单独运行正常后，再启用多模型模式
2. **合理选择模型**：根据分析需求选择合适的模型组合
3. **定期对比结果**：积累一段时间后，分析哪个模型的建议更准确
4. **控制成本**：对于日常监控，可以只用一个模型；重要决策时再启用多模型对比

