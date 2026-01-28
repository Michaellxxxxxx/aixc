# GitHub 上传指南

## 前提条件

1. 已安装 Git
2. 已有 GitHub 账号
3. 已创建 GitHub 仓库

## 上传步骤

### 1. 首次上传

如果这是第一次上传到 GitHub:

```bash
# 初始化 Git 仓库(如果还没有)
git init

# 添加远程仓库
git remote add origin https://github.com/你的用户名/你的仓库名.git

# 推送到 GitHub
git push -u origin main
```

### 2. 后续更新

如果已经上传过,只需要:

```bash
# 推送更新
git push origin main
```

## 验证敏感信息已排除

在推送前,请确认以下文件**不会**被上传:

- ✅ `accounts.csv` - 包含私钥,已在 .gitignore 中
- ✅ `config.json` - 包含代理信息,已在 .gitignore 中
- ✅ `session_cache.json` - 包含会话信息,已在 .gitignore 中
- ✅ `.venv/` - 虚拟环境,已在 .gitignore 中

可以使用以下命令查看将要上传的文件:

```bash
git status
```

## 常见问题

### Q: 如何撤销已添加的文件?

```bash
git restore --staged 文件名
```

### Q: 如何查看提交历史?

```bash
git log --oneline
```

### Q: 如何强制推送(谨慎使用)?

```bash
git push -f origin main
```

## 注意事项

⚠️ **重要**: 
- 推送前务必检查 `.gitignore` 是否正确配置
- 确认敏感文件(私钥、配置)不在提交列表中
- 如果不小心上传了敏感信息,需要立即删除仓库或使用 `git filter-branch` 清理历史
