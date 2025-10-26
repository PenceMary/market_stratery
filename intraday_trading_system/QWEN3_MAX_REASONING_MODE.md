# Qwen3-Max 推理模式配置说明

## 概述
Qwen3-Max 模型支持推理模式（思考模式），能够进行更深入的逻辑推理和分析，特别适合复杂的股票分析任务。

## 配置方法

### 1. 配置文件设置
在 `intraday_trading_config.json` 中为 qwen 配置添加推理模式参数：

```json
{
  "api_config": {
    "qwen": {
      "model": "qwen3-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 300,
      "reasoning_mode": true
    }
  }
}
```

### 2. 参数说明
- `reasoning_mode`: 设置为 `true` 开启推理模式

### 3. 工作原理
当 `reasoning_mode` 为 `true` 时，系统会：
1. 在用户prompt末尾自动添加 `/think` 指令
2. 模型将进入深度思考模式，进行多步推理

## 使用效果
- **更深入的分析**：模型会进行更复杂的逻辑推理
- **更准确的判断**：适合需要多步分析的复杂交易决策
- **思考过程可见**：通过流式输出可以看到模型的思考过程

## 注意事项
1. 推理模式会增加响应时间，但提高分析质量
2. 确保API密钥有足够的token配额
3. 推理模式主要适用于复杂分析任务，简单任务可能不需要

## 关闭推理模式
如需关闭推理模式，将配置中的 `reasoning_mode` 设置为 `false` 即可。
