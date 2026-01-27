@echo off
chcp 65001 >nul
echo ========================================
echo   AIX 自动化交易系统 - GitHub 上传助手
echo ========================================
echo.

REM 检查是否已配置 Git 用户信息
git config user.name >nul 2>&1
if errorlevel 1 (
    echo [!] 检测到未配置 Git 用户信息
    echo.
    set /p username="请输入您的 GitHub 用户名: "
    set /p email="请输入您的 GitHub 邮箱: "
    
    git config user.name "!username!"
    git config user.email "!email!"
    
    echo.
    echo [✓] Git 用户信息配置完成
    echo.
)

REM 显示当前用户信息
echo 当前 Git 配置:
git config user.name
git config user.email
echo.

REM 安全检查
echo [1/5] 执行安全检查...
echo.
echo 检查敏感文件是否被忽略:
git check-ignore -v accounts.csv 2>nul
if errorlevel 1 (
    echo [!] 警告: accounts.csv 可能会被上传！
    pause
    exit /b 1
)

git check-ignore -v config.json 2>nul
if errorlevel 1 (
    echo [!] 警告: config.json 可能会被上传！
    pause
    exit /b 1
)

git check-ignore -v session_cache.json 2>nul
if errorlevel 1 (
    echo [!] 警告: session_cache.json 可能会被上传！
    pause
    exit /b 1
)

echo [✓] 安全检查通过 - 敏感文件已被忽略
echo.

REM 查看将要提交的文件
echo [2/5] 查看将要提交的文件...
echo.
git status
echo.

echo 按任意键继续提交，或 Ctrl+C 取消...
pause >nul

REM 提交代码
echo.
echo [3/5] 提交代码到本地仓库...
git add .
git commit -m "Initial commit: AIX Auto Trading System v2.0.0

✨ 核心功能
- 精准卡点下注系统
- 多账号动态替补并发
- 增强版浏览器 API 客户端
- Playwright Stealth 反检测
- 会话缓存与预热机制

🔧 技术亮点
- 完全模拟真实浏览器请求
- CloudFlare 自动绕过
- HTTP 连接池优化
- 双重数据源策略"

if errorlevel 1 (
    echo [!] 提交失败，请检查错误信息
    pause
    exit /b 1
)

echo [✓] 代码已提交到本地仓库
echo.

REM 提示创建 GitHub 仓库
echo [4/5] 请在 GitHub 创建仓库
echo.
echo 请按照以下步骤操作:
echo 1. 访问 https://github.com/new
echo 2. Repository name: aix-auto-trading (或您喜欢的名称)
echo 3. Description: 高性能多账号自动化交易系统
echo 4. 选择 Public 或 Private
echo 5. 不要勾选任何初始化选项
echo 6. 点击 Create repository
echo.
echo 创建完成后，复制仓库 URL (例如: https://github.com/username/aix-auto-trading.git)
echo.
set /p repo_url="请粘贴您的仓库 URL: "

REM 添加远程仓库
echo.
echo [5/5] 推送到 GitHub...
git remote add origin %repo_url% 2>nul
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo [!] 推送失败，可能的原因:
    echo   1. 仓库 URL 不正确
    echo   2. 需要身份验证 (Personal Access Token)
    echo   3. 网络连接问题
    echo.
    echo 请参考 GITHUB_UPLOAD_GUIDE.md 获取详细帮助
    pause
    exit /b 1
)

echo.
echo ========================================
echo   🎉 上传成功！
echo ========================================
echo.
echo 您的项目已成功上传到 GitHub!
echo 仓库地址: %repo_url%
echo.
echo 下一步:
echo 1. 访问您的 GitHub 仓库查看代码
echo 2. 添加 LICENSE 文件 (推荐 MIT)
echo 3. 设置仓库 Topics 标签
echo 4. 分享您的项目！
echo.
pause
