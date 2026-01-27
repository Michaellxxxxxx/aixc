# GitHub 上传指南

本文档将指导您如何将 AIX 自动化交易系统上传到 GitHub。

## 📋 准备工作检查清单

### ✅ 已完成的安全措施

1. **`.gitignore` 已配置完成**
   - ✅ 账号私钥文件 (`accounts.csv`) 已被忽略
   - ✅ 会话缓存 (`session_cache.json`) 已被忽略
   - ✅ 配置文件 (`config.json`) 已被忽略
   - ✅ 所有敏感信息都不会被上传

2. **示例文件已创建**
   - ✅ `config.example.json` - 配置文件示例
   - ✅ `accounts.example.csv` - 账号文件示例

3. **Git 仓库已初始化**
   - ✅ 本地仓库已创建
   - ✅ 文件已暂存 (staged)

---

## 🚀 上传步骤

### 第 1 步：配置 Git 用户信息

在命令行中运行以下命令（替换为您的信息）：

```bash
# 配置全局用户名和邮箱
git config --global user.name "您的GitHub用户名"
git config --global user.email "您的GitHub邮箱"

# 或者仅为本项目配置（推荐）
cd d:\脚本\aixs
git config user.name "您的GitHub用户名"
git config user.email "您的GitHub邮箱"
```

### 第 2 步：提交代码

```bash
cd d:\脚本\aixs

# 提交代码
git commit -m "Initial commit: AIX Auto Trading System v2.0.0"
```

### 第 3 步：在 GitHub 创建仓库

1. 访问 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `aix-auto-trading` (或您喜欢的名称)
   - **Description**: `高性能多账号自动化交易系统 | AIX Prediction Market`
   - **Visibility**: 
     - ✅ **Public** (公开，推荐) - 开源分享
     - ⚠️ **Private** (私有) - 仅自己可见
   - ⚠️ **不要勾选** "Add a README file"
   - ⚠️ **不要勾选** "Add .gitignore"
   - ⚠️ **不要勾选** "Choose a license"
3. 点击 **Create repository**

### 第 4 步：关联远程仓库并推送

GitHub 会显示推送指令，复制并执行：

```bash
cd d:\脚本\aixs

# 添加远程仓库（替换为您的仓库地址）
git remote add origin https://github.com/您的用户名/aix-auto-trading.git

# 推送到 GitHub（首次推送）
git branch -M main
git push -u origin main
```

**如果遇到认证问题**，可能需要：
- 使用 Personal Access Token (推荐)
- 或配置 SSH 密钥

---

## 🔐 安全检查

### 推送前最后确认

运行以下命令，确保敏感文件不会被上传：

```bash
cd d:\脚本\aixs

# 查看将要提交的文件
git status

# 查看 .gitignore 是否生效
git check-ignore -v accounts.csv config.json session_cache.json
```

**预期输出**：
```
.gitignore:2:accounts.csv       accounts.csv
.gitignore:16:config.json       config.json
.gitignore:7:session_cache.json session_cache.json
```

如果看到这些文件被忽略，说明配置正确！✅

### 被忽略的敏感文件列表

以下文件**不会**被上传到 GitHub：

```
✅ accounts.csv          # 账号私钥
✅ config.json           # 配置文件（包含代理信息）
✅ session_cache.json    # 会话缓存
✅ .env                  # 环境变量
✅ *.log                 # 日志文件
✅ *.png, *.jpg          # 截图
✅ __pycache__/          # Python 缓存
✅ .venv/                # 虚拟环境
```

---

## 📝 后续维护

### 更新代码到 GitHub

```bash
cd d:\脚本\aixs

# 查看修改
git status

# 添加修改的文件
git add .

# 提交修改
git commit -m "描述您的修改"

# 推送到 GitHub
git push
```

### 常用 Git 命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v

# 拉取最新代码
git pull

# 创建新分支
git checkout -b feature/新功能名称
```

---

## ⚠️ 重要提醒

### 绝对不能上传的文件

1. **accounts.csv** - 包含私钥，泄露会导致资金损失！
2. **config.json** - 包含代理账号密码
3. **session_cache.json** - 包含登录凭证
4. **任何包含真实私钥的文件**

### 如果不小心上传了敏感信息

**立即执行以下操作**：

1. **删除远程仓库**（GitHub 网页操作）
2. **更换所有泄露的私钥**
3. **修改所有泄露的密码**
4. **重新创建仓库并正确配置 .gitignore**

### 使用 git-filter-repo 清理历史

如果已经推送了敏感文件，需要清理 Git 历史：

```bash
# 安装 git-filter-repo
pip install git-filter-repo

# 从历史中删除文件
git filter-repo --path accounts.csv --invert-paths
git filter-repo --path config.json --invert-paths
git filter-repo --path session_cache.json --invert-paths

# 强制推送（危险操作！）
git push origin --force --all
```

---

## 🎯 推荐的仓库设置

### 添加 LICENSE

建议添加 MIT 许可证：

1. 在 GitHub 仓库页面点击 "Add file" → "Create new file"
2. 文件名输入 `LICENSE`
3. 点击右侧 "Choose a license template"
4. 选择 "MIT License"
5. 填写年份和您的名字
6. 提交

### 添加 Topics (标签)

在仓库页面点击 ⚙️ Settings → Topics，添加：
- `python`
- `automation`
- `trading-bot`
- `playwright`
- `web-scraping`
- `cryptocurrency`

### 启用 GitHub Actions (可选)

可以添加自动化测试、代码检查等功能。

---

## 📞 获取帮助

如果遇到问题：

1. **Git 配置问题**: https://git-scm.com/book/zh/v2
2. **GitHub 认证**: https://docs.github.com/cn/authentication
3. **Personal Access Token**: https://github.com/settings/tokens

---

## ✅ 完成检查清单

上传完成后，请确认：

- [ ] GitHub 仓库已创建
- [ ] 代码已成功推送
- [ ] README.md 正常显示
- [ ] 敏感文件未被上传（检查仓库文件列表）
- [ ] 示例文件已上传（`config.example.json`, `accounts.example.csv`）
- [ ] LICENSE 已添加（可选）
- [ ] 仓库描述和 Topics 已设置

**恭喜！您的项目已成功上传到 GitHub！** 🎉

---

## 🔗 下一步

1. 在 README.md 中更新仓库 URL
2. 分享您的项目
3. 接受 Issues 和 Pull Requests
4. 持续改进和维护

**祝您的开源项目获得成功！** 🚀
