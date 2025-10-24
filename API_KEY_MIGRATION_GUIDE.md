# 🔄 API Key 配置迁移指南

## 📋 更新内容

将项目中所有使用 `api_key` 的代码统一迁移到新的多 API Key 配置方案，支持 Qwen 和 DeepSeek 分别配置不同的密钥。

## ✅ 已修改的文件

### Qwen 相关文件（使用 `qwen_api_key`）

| 文件名 | 修改内容 | 状态 |
|--------|---------|------|
| `anaByQwen2.py` | 第1202行：`api_key = config.get('qwen_api_key', config.get('api_key', ''))` | ✅ 已完成 |
| `anaByQwenMax.py` | 第554行：`api_key = config.get('qwen_api_key', config.get('api_key', ''))` | ✅ 已完成 |
| `retestqwen.py` | 第238行：`api_key = config.get('qwen_api_key', config.get('api_key', ''))` | ✅ 已完成 |
| `anylizeByQwen.py` | 第291行：`api_key = config.get('qwen_api_key', config.get('api_key', ''))` | ✅ 已完成 |

### DeepSeek 相关文件（使用 `deepseek_api_key`）

| 文件名 | 修改内容 | 状态 |
|--------|---------|------|
| `retestwithdeepseek.py` | 第160行：`api_key = config.get('deepseek_api_key', config.get('api_key', 'YOUR_API_KEY'))` | ✅ 已完成 |
| `retestwithdeepseek2.py` | 第108行：`api_key = config.get('deepseek_api_key', config.get('api_key', 'YOUR_API_KEY'))` | ✅ 已完成 |

### 配置文件

| 文件名 | 修改内容 | 状态 |
|--------|---------|------|
| `keys.json` | 添加 `qwen_api_key` 和 `deepseek_api_key` 字段 | ✅ 已完成 |
| `intraday_trading_system/intraday_trading_main.py` | 智能选择 API Key | ✅ 已完成 |
| `intraday_trading_system/intraday_trading_example_keys.json` | 更新示例配置 | ✅ 已完成 |

## 🔑 新的 keys.json 格式

### 之前（旧格式）：

```json
{
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "email_password": "your_email_password",
    "email_sender": "your_email@example.com",
    "email_receivers": ["receiver@example.com"]
}
```

### 现在（新格式）：

```json
{
    "qwen_api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "deepseek_api_key": "sk-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
    "email_password": "your_email_password",
    "email_sender": "your_email@example.com",
    "email_receivers": ["receiver@example.com"]
}
```

## 🔄 向后兼容性

所有修改都保持**完全向后兼容**：

### 兼容逻辑：

```python
# Qwen 脚本
api_key = config.get('qwen_api_key', config.get('api_key', ''))

# DeepSeek 脚本
api_key = config.get('deepseek_api_key', config.get('api_key', 'YOUR_API_KEY'))
```

**工作原理：**
1. 优先使用新字段（`qwen_api_key` 或 `deepseek_api_key`）
2. 如果新字段不存在，回退到旧字段（`api_key`）
3. 如果都不存在，使用默认值

### 兼容场景：

| keys.json 内容 | Qwen 脚本行为 | DeepSeek 脚本行为 |
|---------------|--------------|------------------|
| 只有 `api_key` | ✅ 使用 `api_key` | ✅ 使用 `api_key` |
| 只有 `qwen_api_key` | ✅ 使用 `qwen_api_key` | ⚠️ 使用默认值 |
| 只有 `deepseek_api_key` | ⚠️ 使用空字符串 | ✅ 使用 `deepseek_api_key` |
| 同时有新旧字段 | ✅ 优先使用 `qwen_api_key` | ✅ 优先使用 `deepseek_api_key` |

## 📚 使用指南

### 场景1：仅使用 Qwen

```json
{
    "qwen_api_key": "sk-your-qwen-key",
    "email_password": "xxx",
    "email_sender": "xxx@163.com",
    "email_receivers": ["xxx@163.com"]
}
```

**可以运行：**
- ✅ `anaByQwen2.py`
- ✅ `anaByQwenMax.py`
- ✅ `retestqwen.py`
- ✅ `anylizeByQwen.py`
- ✅ `intraday_trading_system/intraday_trading_main.py`（配置为 qwen）

### 场景2：仅使用 DeepSeek

```json
{
    "deepseek_api_key": "sk-your-deepseek-key",
    "email_password": "xxx",
    "email_sender": "xxx@163.com",
    "email_receivers": ["xxx@163.com"]
}
```

**可以运行：**
- ✅ `retestwithdeepseek.py`
- ✅ `retestwithdeepseek2.py`
- ✅ `intraday_trading_system/intraday_trading_main.py`（配置为 deepseek）

### 场景3：同时使用两者（推荐）

```json
{
    "qwen_api_key": "sk-your-qwen-key",
    "deepseek_api_key": "sk-your-deepseek-key",
    "email_password": "xxx",
    "email_sender": "xxx@163.com",
    "email_receivers": ["xxx@163.com"]
}
```

**所有脚本都可以运行！** ✅

## 🎯 迁移步骤（推荐）

### 步骤1：备份旧配置

```bash
cp keys.json keys.json.backup
```

### 步骤2：更新 keys.json

如果您之前的 `api_key` 是 Qwen 的：

```json
{
    "qwen_api_key": "sk-原来的api_key值",
    "deepseek_api_key": "sk-新申请的deepseek_key",
    ...
}
```

### 步骤3：验证配置

运行任一脚本测试：

```bash
# 测试 Qwen
python anaByQwen2.py

# 测试 DeepSeek
python retestwithdeepseek2.py

# 测试日内交易系统
cd intraday_trading_system
python intraday_trading_main.py 000100
```

### 步骤4（可选）：删除旧字段

确认一切正常后，可以删除旧的 `api_key` 字段：

```json
{
    "qwen_api_key": "sk-xxx",
    "deepseek_api_key": "sk-xxx",
    // "api_key": "sk-xxx"  ← 可以删除
    ...
}
```

## 🔍 故障排查

### 问题1：提示 API Key 无效

**症状：** 运行时提示 API Key 不正确

**检查步骤：**
1. 确认使用了正确的字段名（`qwen_api_key` 或 `deepseek_api_key`）
2. 确认 API Key 没有多余的空格或换行
3. 确认在对应平台上 API Key 状态为"启用"

### 问题2：脚本找不到 API Key

**症状：** 运行时提示找不到 API Key

**解决方法：**
- 检查 `keys.json` 文件是否存在
- 检查 JSON 格式是否正确（逗号、引号等）
- 确认字段名拼写正确

### 问题3：旧脚本无法运行

**症状：** 旧版本的脚本报错

**解决方法：**
- 如果您不想修改旧脚本，保留 `api_key` 字段即可
- 或者按本文档更新所有脚本

## 📊 修改统计

| 项目 | 数量 |
|------|------|
| 修改的 Python 文件 | 6 个 |
| 修改的配置文件 | 3 个 |
| 新增的文档 | 2 个 |
| 保持向后兼容 | ✅ 是 |
| 语法错误 | 0 个 |

## 📝 相关文档

- **API Key 配置详细说明**: `intraday_trading_system/API_KEY_CONFIG.md`
- **日内交易系统文档**: `intraday_trading_system/INTRADAY_TRADING_README.md`
- **快速开始**: `intraday_trading_system/START_HERE.md`

## ✨ 主要优势

1. **清晰的密钥管理** - 不同服务商的密钥分开管理
2. **灵活切换** - 随时切换不同的 API 提供商
3. **向后兼容** - 旧配置依然可以正常工作
4. **统一代码风格** - 所有脚本使用相同的密钥获取逻辑

## 🎉 总结

✅ **所有修改已完成**  
✅ **保持完全向后兼容**  
✅ **通过语法检查**  
✅ **文档已更新**  

您现在可以：
- 继续使用旧的 `api_key` 字段（向后兼容）
- 或迁移到新的 `qwen_api_key` 和 `deepseek_api_key`（推荐）
- 或同时配置两个服务商的密钥（最佳实践）

---

**更新时间**: 2025-10-25  
**版本**: v2.0  
**状态**: ✅ 迁移完成

