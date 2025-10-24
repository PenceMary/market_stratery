# 🔐 安全漏洞修复指南

## ⚠️ 严重安全问题

发现以下文件包含敏感信息并已被 Git 跟踪：

| 文件名 | 包含的敏感信息 | 状态 |
|--------|---------------|------|
| `selectbyAve.json` | 邮箱密码、邮箱地址 | ❌ 已被 Git 跟踪 |
| `retestconfig.json` | 部分API密钥、邮箱密码、邮箱地址 | ❌ 已被 Git 跟踪 |
| `keys.json` | 完整API密钥、邮箱密码 | ✅ 已在 .gitignore 中 |
| `API_KEY_MIGRATION_GUIDE.md` | 真实API密钥（已修复） | ⚠️ 需要重新提交 |
| `intraday_trading_system/API_KEY_CONFIG.md` | 真实密钥（已修复） | ⚠️ 需要重新提交 |

## 🚨 立即行动步骤

### 步骤1：从 Git 索引中删除敏感文件（但保留本地文件）

```bash
# 从Git跟踪中删除，但保留本地文件
git rm --cached selectbyAve.json
git rm --cached retestconfig.json

# 确认.gitignore已更新
git add .gitignore

# 提交变更
git commit -m "security: 移除敏感配置文件的Git跟踪"
```

### 步骤2：添加示例配置文件

```bash
# 添加脱敏的示例文件
git add selectbyAve.json.example
git add retestconfig.json.example
git commit -m "docs: 添加配置文件示例（已脱敏）"
```

### 步骤3：更新已修复的文档

```bash
# 添加已脱敏的文档
git add API_KEY_MIGRATION_GUIDE.md
git add intraday_trading_system/API_KEY_CONFIG.md
git commit -m "security: 脱敏文档中的真实密钥"
```

### 步骤4：推送到远程仓库

```bash
git push origin main
```

## 🔥 如果密钥已经泄露到远程仓库

如果这些文件已经被推送到GitHub/GitLab等远程仓库，**密钥已经泄露**，必须：

### 立即行动：

1. **更换所有API密钥**
   - 登录 Qwen 平台，删除并重新生成 API Key
   - 登录 DeepSeek 平台，删除并重新生成 API Key
   - 更新本地 `keys.json` 文件

2. **更换邮箱授权码**
   - 登录邮箱，撤销旧的授权码
   - 生成新的授权码
   - 更新所有配置文件

3. **清理 Git 历史（可选，但推荐）**

如果要彻底清除历史记录中的敏感信息：

```bash
# 方法1：使用 git filter-branch（适合小仓库）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch selectbyAve.json retestconfig.json" \
  --prune-empty --tag-name-filter cat -- --all

# 方法2：使用 BFG Repo-Cleaner（推荐，更快）
# 下载 BFG: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files selectbyAve.json
java -jar bfg.jar --delete-files retestconfig.json

# 清理和推送
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

⚠️ **警告**：`--force` 推送会重写历史记录，如果有团队成员，需要协调！

## ✅ 已采取的预防措施

### 1. 更新了 .gitignore

```gitignore
# Keys and secrets - DO NOT COMMIT THESE FILES
keys.json
selectbyAve.json
retestconfig.json
**/keys.json
*.key
*.pem
*.p12
*.pfx
```

### 2. 创建了示例配置文件

- ✅ `selectbyAve.json.example` - 脱敏版本
- ✅ `retestconfig.json.example` - 脱敏版本
- ✅ `intraday_trading_system/intraday_trading_example_keys.json` - 已存在

### 3. 脱敏了文档

- ✅ `API_KEY_MIGRATION_GUIDE.md` - 所有密钥已替换为占位符
- ✅ `intraday_trading_system/API_KEY_CONFIG.md` - 所有密钥已脱敏

## 📋 配置文件使用指南

### 首次使用：

```bash
# 1. 复制示例文件
cp selectbyAve.json.example selectbyAve.json
cp retestconfig.json.example retestconfig.json

# 2. 编辑文件，填入真实密钥
nano selectbyAve.json
nano retestconfig.json

# 3. 确认不会被提交
git status  # 应该看不到这两个文件
```

## 🔒 最佳安全实践

### 1. 永远不要提交的文件：

- ❌ `keys.json` - API 密钥
- ❌ `*.json` 包含 `password`, `api_key` 字段的配置文件
- ❌ `.env` 文件
- ❌ 任何包含真实凭证的文件

### 2. 提交前检查：

```bash
# 查看即将提交的内容
git diff --cached

# 搜索敏感关键词
git diff --cached | grep -i "password\|api_key\|secret"
```

### 3. 使用 git-secrets（可选）

安装 git-secrets 防止意外提交密钥：

```bash
# 安装
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets
make install

# 在项目中启用
cd /path/to/your/project
git secrets --install
git secrets --register-aws
git secrets --add 'sk-[0-9a-f]{32}'
git secrets --add 'password.*=.*'
```

## 🎯 检查清单

在推送代码前，请确认：

- [ ] 所有敏感文件已在 `.gitignore` 中
- [ ] 文档中没有真实的 API 密钥
- [ ] 配置文件使用示例版本（.example）
- [ ] 运行 `git status` 确认没有敏感文件
- [ ] 运行 `git diff` 检查提交内容

## 📞 如果已经泄露

1. **立即更换所有密钥**（最重要！）
2. 检查是否有异常 API 调用
3. 联系平台客服说明情况
4. 清理 Git 历史记录（可选）

## 📚 相关资源

- [GitHub - 删除敏感数据](https://docs.github.com/cn/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [git-secrets](https://github.com/awslabs/git-secrets)

---

**创建时间**: 2025-10-25  
**严重程度**: 🔴 高  
**状态**: ⚠️ 需要立即处理

