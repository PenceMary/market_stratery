# 🔑 API Key 配置说明

## 📋 配置文件结构

现在系统支持**分别配置** Qwen 和 DeepSeek 的 API Key，系统会根据您选择的 API 提供商自动使用对应的密钥。

### keys.json 配置格式

```json
{
    "qwen_api_key": "sk-your-qwen-api-key-here",
    "deepseek_api_key": "sk-your-deepseek-api-key-here",
    "email_password": "your_email_password",
    "email_sender": "your_email@163.com",
    "email_receivers": [
        "receiver@example.com"
    ]
}
```

## 🔄 自动密钥选择机制

系统会根据 `intraday_trading_config.json` 中的 `api_provider` 设置自动选择对应的 API Key：

**配置 Qwen：**
```json
{
  "api_provider": "qwen",
  ...
}
```
→ 系统自动使用 `qwen_api_key`

**配置 DeepSeek：**
```json
{
  "api_provider": "deepseek",
  ...
}
```
→ 系统自动使用 `deepseek_api_key`

## 🚀 快速配置步骤

### 步骤1：获取 API Key

**Qwen (通义千问):**
1. 访问：https://dashscope.aliyuncs.com/
2. 注册/登录阿里云账号
3. 进入"API-KEY管理"
4. 创建新的 API Key
5. 复制密钥（格式：`sk-xxxxxxxx`）

**DeepSeek:**
1. 访问：https://platform.deepseek.com/
2. 注册/登录账号
3. 进入"API Keys"页面
4. 创建新的 API Key
5. 复制密钥（格式：`sk-xxxxxxxx`）

### 步骤2：配置 keys.json

在项目根目录的 `keys.json` 中填入真实的 API Key：

```json
{
    "qwen_api_key": "sk-your-real-qwen-api-key-here",
    "deepseek_api_key": "sk-your-real-deepseek-api-key-here",
    "email_password": "your_email_password",
    "email_sender": "your_email@example.com",
    "email_receivers": [
        "receiver@example.com"
    ]
}
```

### 步骤3：选择 API 提供商

在 `intraday_trading_config.json` 中设置：

```json
{
  "api_provider": "deepseek",   // 或 "qwen"
  ...
}
```

### 步骤4：运行系统

```bash
cd intraday_trading_system
python intraday_trading_main.py 000100
```

运行时会显示：
```
✅ 配置文件加载成功 (keys.json: ../keys.json)
✅ 使用 deepseek API Key
```

## 🔐 安全建议

1. **不要提交到 Git**
   - `keys.json` 已在 `.gitignore` 中
   - 请勿将真实密钥推送到代码仓库

2. **定期更换密钥**
   - 建议每3-6个月更换一次 API Key
   - 如发现密钥泄露，立即在平台上删除并重新生成

3. **权限管理**
   - 仅授予必要的 API 权限
   - 设置合理的调用限额

## 🔄 切换 API 提供商

随时可以在配置文件中切换，无需修改代码：

**切换到 Qwen：**
```json
{
  "api_provider": "qwen"
}
```

**切换到 DeepSeek：**
```json
{
  "api_provider": "deepseek"
}
```

## ⚠️ 常见问题

### Q1: 提示"未配置 API Key"

**问题：** 运行时提示 `❌ 未配置 deepseek 的 API Key`

**解决：**
- 检查 `keys.json` 中是否有 `deepseek_api_key` 字段
- 确认 API Key 不是占位符（不能是 `sk-请填入...`）
- 确认 API Key 格式正确（以 `sk-` 开头）

### Q2: API Key 无效

**问题：** 调用时提示 API Key 无效

**解决：**
- 确认在对应平台上 API Key 状态为"启用"
- 检查是否复制完整（没有遗漏或多余空格）
- 确认账户余额充足（部分平台需要充值）

### Q3: 兼容旧配置

**问题：** 之前用的是 `api_key` 字段

**解决：**
系统自动兼容旧配置：
- 如果使用 `qwen` 且只有 `api_key` 字段，系统会自动使用它
- 建议迁移到新格式：将 `api_key` 改为 `qwen_api_key`

## 💡 最佳实践

### 推荐配置（两个都配）

```json
{
    "qwen_api_key": "sk-qwen-key-here",
    "deepseek_api_key": "sk-deepseek-key-here",
    ...
}
```

**好处：**
- 可以随时在配置文件中切换
- 不同任务使用不同模型
- 一个模型限流时可以切换到另一个

### 使用场景建议

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| **大量历史数据分析** | Qwen-Long | 超长上下文（百万token） |
| **复杂技术推理** | DeepSeek | 推理能力强，成本低 |
| **快速日内分析** | DeepSeek | 响应速度快 |
| **多日数据对比** | Qwen-Long | 可处理更多历史数据 |

## 📊 成本对比

| 模型 | 输入价格 | 输出价格 | 上下文长度 |
|------|---------|---------|------------|
| Qwen-Long | 约0.5元/百万token | 约2元/百万token | 1000万token |
| DeepSeek-Chat | 约0.1元/百万token | 约0.5元/百万token | 64K token |

**建议：**
- 日常分析使用 DeepSeek（成本低）
- 重要决策使用 Qwen-Long（分析更全面）

## 🔗 相关链接

- **Qwen API 文档**: https://help.aliyun.com/zh/dashscope/
- **DeepSeek API 文档**: https://platform.deepseek.com/api-docs/
- **项目配置文件**: `intraday_trading_config.json`
- **示例配置**: `intraday_trading_example_keys.json`

---

**更新时间**: 2025-10-25  
**版本**: v2.0  
**状态**: ✅ 支持多 API Key 配置

