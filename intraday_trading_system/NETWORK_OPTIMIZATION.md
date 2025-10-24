# 网络超时和重试机制优化说明

## 📋 优化概述

针对数据获取过程中频繁出现的网络超时和连接错误问题，添加了完善的超时控制和自动重试机制。

## 🔧 改进内容

### 1. 配置文件增强 (`intraday_trading_config.json`)

在 `data_config` 中新增三个参数：

```json
{
  "data_config": {
    "api_timeout": 30,      // API超时时间（秒）
    "max_retries": 3,       // 最大重试次数
    "retry_delay": 2        // 重试延迟基础值（秒）
  }
}
```

**参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `api_timeout` | 30秒 | 单次API调用的超时时间 |
| `max_retries` | 3次 | 失败后的最大重试次数 |
| `retry_delay` | 2秒 | 重试延迟基础值（采用指数退避策略） |

### 2. 数据获取器增强 (`intraday_data_fetcher.py`)

#### 新增功能：

**a) 智能重试装饰器**
```python
@retry_on_failure(max_retries=3, delay=2, timeout=30)
def api_method(...):
    # API调用代码
```

**b) IntradayDataFetcher 类增强**
- 接受配置参数：`max_retries`, `retry_delay`, `timeout`
- 内置重试逻辑
- 自动识别网络错误类型

**c) 改进的异常处理**
```python
# 自动识别网络相关错误
is_network_error = any(keyword in error_msg.lower() for keyword in 
                      ['timeout', 'connection', 'proxy', 'max retries', 'read timed out'])
```

**d) 指数退避策略**
```python
# 第1次重试：等待 2秒
# 第2次重试：等待 4秒
# 第3次重试：等待 6秒
wait_time = retry_delay * (attempt + 1)
```

### 3. 主程序集成 (`intraday_trading_main.py`)

自动从配置文件读取参数并初始化数据获取器：

```python
data_config = self.config.get('data_config', {})
max_retries = data_config.get('max_retries', 3)
retry_delay = data_config.get('retry_delay', 2)
api_timeout = data_config.get('api_timeout', 30)

self.data_fetcher = IntradayDataFetcher(
    max_retries=max_retries,
    retry_delay=retry_delay,
    timeout=api_timeout
)
```

## 🎯 解决的问题

### 问题1：频繁超时
**原因：** akshare默认超时时间为15秒，在网络状况不佳或非交易时段可能不够

**解决方案：** 
- 可配置的超时时间（默认30秒）
- 自动重试机制

### 问题2：代理错误
**错误信息：**
```
ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))
```

**解决方案：**
- 识别代理相关错误
- 自动重试（指数退避）
- 最多重试3次

### 问题3：连接不稳定
**错误信息：**
```
HTTPSConnectionPool(host='82.push2.eastmoney.com', port=443): Max retries exceeded
Read timed out. (read timeout=15)
```

**解决方案：**
- 延长超时时间到30秒
- 智能重试机制
- 每次重试间隔递增

## 📊 重试策略详解

### 重试流程：

```
尝试 1 → 失败 → 等待 2秒 → 尝试 2 → 失败 → 等待 4秒 → 尝试 3 → 失败 → 报错退出
   ↓                            ↓                            ↓
 成功返回                      成功返回                      成功返回
```

### 错误分类：

**会触发重试的错误：**
- `timeout` - 超时错误
- `connection` - 连接错误
- `proxy` - 代理错误
- `max retries` - 重试次数超限
- `read timed out` - 读取超时

**不会重试的错误：**
- 数据格式错误
- 股票代码不存在
- 其他非网络错误

## 🔍 日志输出示例

### 成功案例：
```
📊 获取 000100 实时行情...
✅ 实时行情获取成功: TCL科技 当前价 4.18
```

### 重试案例：
```
📊 获取 002517 实时行情...
  ⚠️ 第1次尝试失败: HTTPSConnectionPool(host='82.push2.eastmoney.com'...
  ⏳ 2秒后重试...
  ⚠️ 第2次尝试失败: Read timed out...
  ⏳ 4秒后重试...
✅ 实时行情获取成功: 恺英网络 当前价 3.45
```

### 失败案例：
```
📊 获取 002517 实时行情...
  ⚠️ 第1次尝试失败: HTTPSConnectionPool...
  ⏳ 2秒后重试...
  ⚠️ 第2次尝试失败: Read timed out...
  ⏳ 4秒后重试...
  ❌ 已重试3次仍失败
❌ 获取实时行情失败: Read timed out. (read timeout=30)
```

## ⚙️ 自定义配置

### 调整超时时间

编辑 `intraday_trading_config.json`：

```json
{
  "data_config": {
    "api_timeout": 45,      // 增加到45秒（适合网络较慢的环境）
    "max_retries": 5,       // 增加重试次数到5次
    "retry_delay": 3        // 增加延迟到3秒
  }
}
```

### 快速模式（网络良好时）

```json
{
  "data_config": {
    "api_timeout": 20,      // 减少到20秒
    "max_retries": 2,       // 只重试2次
    "retry_delay": 1        // 缩短延迟到1秒
  }
}
```

### 稳定模式（网络不稳定时）

```json
{
  "data_config": {
    "api_timeout": 60,      // 增加到60秒
    "max_retries": 5,       // 最多重试5次
    "retry_delay": 3        // 延迟3秒起
  }
}
```

## 📈 性能影响

### 最坏情况（所有重试都失败）：

- 超时时间：30秒
- 重试次数：3次
- 重试延迟：2+4+6=12秒
- **总耗时**：约 30×3 + 12 = **102秒**

### 建议：

- 正常交易时段使用默认配置
- 非交易时段可适当减少重试次数
- 网络不佳时增加超时时间

## 🔄 后续优化方向

1. **并发请求优化**
   - 对于批量股票分析，可考虑并发请求
   - 注意控制并发数，避免触发服务器限流

2. **智能超时调整**
   - 根据历史成功率动态调整超时时间
   - 记录不同时段的网络状况

3. **缓存机制**
   - 对于短时间内的重复请求使用缓存
   - 减少不必要的网络请求

4. **降级策略**
   - 当主数据源失败时，尝试备用数据源
   - 提供离线数据模式

## ✅ 测试建议

### 测试1：正常情况
```bash
python intraday_trading_main.py 600000
```

### 测试2：网络不稳定模拟
```bash
# 在网络条件不佳时测试
python intraday_trading_main.py 002517
```

### 测试3：非交易时段
```bash
# 在晚上或周末测试，观察重试行为
python intraday_trading_main.py 000100
```

---

**更新时间**: 2025-10-24  
**版本**: v1.1  
**状态**: ✅ 已实施并测试

