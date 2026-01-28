# AIX 自动化交易系统

<div align="center">

**高性能多账号自动化交易系统 | 专为 AIX Prediction Market 设计**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📋 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [快速开始](#-快速开始)
- [详细配置](#-详细配置)
- [功能模块](#-功能模块)
- [常见问题](#-常见问题)
- [免责声明](#-免责声明)

---

## 📖 项目简介

AIX 自动化交易系统是一个基于 Python 的多账号自动化交易工具,专为 AIX Prediction Market 设计。

**主要功能**:
- ⚡ **自动监控**: 实时监控网页倒计时,精准卡点下注
- 🤖 **多账号管理**: 支持无限账号,自动并发执行
- 🔄 **智能替补**: 账户完成 100 次后自动替换,保持满额并发
- 🛡️ **安全可靠**: 集成 CloudFlare 绕过,支持代理,私钥本地签名

---

## 🚀 核心特性

### 智能监控与交易
- **精准卡点下注**: 基于 Playwright 实时监控网页倒计时,在最后 3 秒(可配置)触发批量下注
- **双重数据源**: 网页 DOM 读取开盘价 + 浏览器内 API 获取当前价,确保数据准确性
- **动态替补机制**: 账户完成 100 次后自动替换,保持满额并发,最大化效率

### 多账号管理
- **无限账号支持**: 通过 `accounts.csv` 导入任意数量账号,全自动并发执行
- **智能分组**: 默认 4 个账号并发,动态替补确保所有账号完成每日 100 次任务
- **会话缓存**: 自动缓存登录会话,减少重复登录,提升响应速度
- **并发登录**: 支持批量并发登录,大幅提升登录效率(效率提升 85-90%)

### 安全与稳定
- **CloudFlare 绕过**: 集成 Playwright Stealth 插件,自动通过 CloudFlare 验证
- **代理支持**: 支持动态代理,防止 IP 封禁
- **本地签名**: 私钥仅用于本地签名,不上传服务器,确保资金安全
- **自动任务**: 自动检测并领取每日签到奖励

---

## 🎯 快速开始

### 1. 环境准备

#### Windows 用户

**安装 Python**

1. 访问 [Python 官网](https://www.python.org/downloads/) 下载 Python 3.8 或更高版本
2. 运行安装程序,**务必勾选** "Add Python to PATH"
3. 验证安装:
   ```bash
   python --version
   ```

#### macOS/Linux 用户

```bash
# macOS
brew install python3

# Linux
sudo apt install python3 python3-pip
```

---

### 2. 下载项目

```bash
# 使用 Git
git clone https://github.com/你的用户名/aixs.git
cd aixs

# 或直接下载 ZIP 并解压
```

---

### 3. 安装依赖

```bash
# 安装 Python 依赖包
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

**提示**: 如果网络较慢,可以使用国内镜像源:
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 4. 配置账号

#### 创建账号文件

```bash
# Windows
copy accounts.example.csv accounts.csv

# macOS/Linux
cp accounts.example.csv accounts.csv
```

#### 填写账号信息

使用文本编辑器打开 `accounts.csv`,按以下格式填写:

```csv
label,private_key,privy_session,enabled
主账号,0x你的私钥1,t,TRUE
副账号1,0x你的私钥2,t,TRUE
副账号2,0x你的私钥3,t,FALSE
```

**字段说明**:
- `label`: 账号别名,方便识别
- `private_key`: 钱包私钥,必须以 `0x` 开头
- `privy_session`: 固定填写 `t`
- `enabled`: 是否启用该账号 (`TRUE`/`FALSE`)

**⚠️ 安全提示**:
- 私钥仅用于本地签名,不会上传到任何服务器
- 建议使用专用账号,不要使用主钱包
- 妥善保管 `accounts.csv` 文件,请勿泄露

---

### 5. 配置系统

#### 创建配置文件

```bash
# Windows
copy config.example.json config.json

# macOS/Linux
cp config.example.json config.json
```

#### 修改配置(可选)

使用文本编辑器打开 `config.json`:

```json
{
    "api": {
        "base_url": "https://hub.aixcrypto.ai/api/game",
        "timeout_seconds": 7
    },
    "trigger": {
        "concurrency": 4,
        "auto_bet": {
            "enabled": true
        },
        "browser_trigger": {
            "countdown_seconds": 3,
            "headless": false
        }
    },
    "proxy": {
        "enabled": false,
        "host": "YOUR_PROXY_HOST",
        "start_port": 10000,
        "username": "YOUR_PROXY_USERNAME",
        "password": "YOUR_PROXY_PASSWORD",
        "countries": "sg,gb,hk,jp"
    }
}
```

**重要配置项**:
- `concurrency`: 并发账号数量,建议 4-10 个
- `countdown_seconds`: 触发下注的倒计时秒数,建议 3 秒
- `headless`: 无头模式,`false` 显示浏览器(方便调试),`true` 隐藏浏览器
- `auto_bet.enabled`: 是否开启自动下注

---

### 6. 启动程序

#### 使用启动菜单(推荐)

```bash
python launcher.py
```

启动后会显示菜单:
```
==================================================
       AIX 自动化脚本启动菜单
==================================================

请选择要启动的功能模块:

1. [主程序] AIX 监控 (aix_monitor.py) ★网页开盘价+API当前价
2. [管理] 订单管理 (order_manager.py)
3. [任务] 每日任务检查 (check_tasks.py)
4. [战队] 批量加入战队 (join_teams.py)
5. [登录] 批量登录 (batch_login.py)
0. 退出
--------------------------------------------------
```

输入 `1` 并回车,启动主程序。

#### 直接运行主程序

```bash
python aix_monitor.py
```

#### 首次运行

首次运行时,程序会:
1. 打开浏览器窗口
2. 访问 AIX 网站
3. 自动通过 CloudFlare 验证(可能需要 10-30 秒)
4. 开始监控倒计时

**正常运行的标志**:
```
[10:30:45] 倒计时: 00:05 | 颜色: emerald
[10:30:48] 倒计时: 00:03 | 颜色: emerald
🎯 [10:30:48.123] 触发条件满足! (倒计时=3s)
==================================================
🔔 Round #12345 趋势: UP
   C10 开盘: 1234.5678
   C10 当前: 1235.1234
   涨跌幅:   +0.5556 (+0.0450%)
  [▶] 正在批量下单...
  [✓] 下单完成: 4/4 成功
==================================================
```

---

## ⚙️ 详细配置

### 账号配置 (`accounts.csv`)

| 字段 | 说明 | 示例 | 必填 |
|------|------|------|------|
| `label` | 账号别名(日志显示) | `主账号` | 是 |
| `private_key` | 钱包私钥(0x 开头) | `0x1234...` | 是 |
| `privy_session` | Privy 会话标识 | `t` | 是 |
| `enabled` | 是否启用(TRUE/FALSE) | `TRUE` | 是 |

---

### 系统配置 (`config.json`)

#### API 配置
```json
"api": {
    "base_url": "https://hub.aixcrypto.ai/api/game",
    "timeout_seconds": 7
}
```

#### 触发配置
```json
"trigger": {
    "concurrency": 4,
    "auto_bet": {
        "enabled": true
    },
    "browser_trigger": {
        "countdown_seconds": 3,
        "headless": false
    }
}
```

#### 代理配置(可选)
```json
"proxy": {
    "enabled": false,
    "host": "YOUR_PROXY_HOST",
    "start_port": 10000,
    "username": "YOUR_PROXY_USERNAME",
    "password": "YOUR_PROXY_PASSWORD",
    "countries": "sg,gb,hk,jp"
}
```

---

## 📖 功能模块

### 1. AIX 监控 (主程序)

**功能**: 实时监控网页倒计时,自动触发批量下注

**运行流程**:
```
启动浏览器 → 打开页面 → CloudFlare 验证 → 初始化 API 客户端
    ↓
监控倒计时 → 检测触发条件 → 获取 C10 数据 → 批量下单
    ↓
动态替补 → 继续监控 → 循环执行
```

---

### 2. 批量登录

**功能**: 预先登录所有账号并缓存会话

**使用方法**:
```bash
python batch_login.py
```

**支持两种模式**:
- **顺序登录**: 逐个登录账号(原有功能)
- **并发登录**: 同时登录多个账号(新功能,效率提升 85-90%)

**并发登录流程**:
1. 选择 "2. 并发批量登录"
2. 输入并发登录数量(建议 5-20)
3. 系统自动分批并发登录
4. 实时显示登录结果

**性能对比**:
- 顺序登录 50 个账号: ~100 秒
- 并发登录 50 个账号(并发数=10): ~10-15 秒

---

### 3. 每日任务检查

**功能**: 批量检查并领取所有账号的每日任务

```bash
python check_tasks.py
```

---

### 4. 批量加入战队

**功能**: 让所有账号加入指定邀请码的战队

```bash
python join_teams.py
# 按提示输入战队邀请码
```

---

## ❓ 常见问题

### Q1: 安装依赖时报错怎么办?

**A**: 常见解决方案:
1. 确认 Python 版本 ≥ 3.8: `python --version`
2. 升级 pip: `python -m pip install --upgrade pip`
3. 使用国内镜像源:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

---

### Q2: CloudFlare 验证失败怎么办?

**A**: 
1. 检查网络连接是否正常
2. 尝试关闭无头模式(`headless: false`),观察验证过程
3. 如果使用代理,检查代理配置是否正确
4. 增加等待时间,多尝试几次

---

### Q3: 如何调整触发时机?

**A**: 修改 `config.json` 中的 `trigger.countdown_seconds` 参数:
- 默认值: `3`(倒计时剩余 3 秒触发)
- 建议范围: `1-5` 秒

---

### Q4: 代理是否必须?

**A**: 不是必须的,但强烈推荐:
- **不使用代理**: 可能导致 IP 被封(尤其是多账号)
- **使用代理**: 更稳定,降低封号风险

---

### Q5: 如何停止程序?

**A**: 
- **Windows**: 按 `Ctrl + C`
- **macOS/Linux**: 按 `Ctrl + C`
- 或直接关闭命令行窗口

---

### Q6: 如何更新项目?

**A**: 
```bash
# 使用 Git
git pull origin main

# 手动下载
# 下载最新版本,覆盖除 accounts.csv 和 config.json 外的所有文件
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AIX 自动化交易系统                          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐         ┌──────▼──────┐      ┌──────▼──────┐
   │ 监控层   │         │  数据层      │      │  执行层      │
   └────┬────┘         └──────┬──────┘      └──────┬──────┘
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼────────┐
│ Playwright     │   │ Enhanced        │   │ Order          │
│ 浏览器监控      │   │ Browser API     │   │ Manager        │
│ • 倒计时监控    │   │ • current-round │   │ • 批量下单      │
│ • 颜色检测      │   │ • c10-composition│  │ • 会话管理      │
│ • DOM 读取      │   │ • Stealth 模式  │   │ • 动态替补      │
└────────────────┘   └─────────────────┘   └────────────────┘
```

### 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **主监控程序** | `aix_monitor.py` | 浏览器监控、触发逻辑、批量下单协调 |
| **订单管理器** | `order_manager.py` | 账户登录、会话管理、批量下单、动态替补 |
| **API 客户端** | `enhanced_browser_api_client.py` | 浏览器内 API 调用,完全模拟真实浏览器 |
| **代理管理器** | `proxy_manager.py` | 动态代理配置 |
| **批量登录** | `batch_login.py` | 支持顺序和并发两种登录模式 |
| **启动器** | `launcher.py` | 统一启动菜单 |

---

## ⚠️ 免责声明

**本工具仅供学习与研究使用。**

- ✅ 允许: 个人学习、技术研究、代码参考
- ❌ 禁止: 商业用途、恶意攻击、违反平台规则

**风险提示**:
1. 使用自动化工具可能违反平台服务条款
2. 可能导致账号封禁、资金损失等后果
3. 私钥安全由使用者自行负责
4. 作者不对任何损失承担责任

**使用本工具即表示您已充分理解并接受上述风险。请遵守平台规则,理性使用。**

---

## 📝 更新日志

### v2.1.0 (2026-01-28)
- ✨ 新增并发批量登录功能,效率提升 85-90%
- 🔧 优化代码结构,删除无用文件
- 📝 简化 README 文档

### v2.0.0 (2026-01-27)
- ✨ 集成增强版浏览器 API 客户端
- ✨ 实现动态替补并发模式
- ✨ 添加 Playwright Stealth 插件
- 🔧 优化 HTTP 连接池配置
- 🔧 实现会话预热机制

### v1.0.0 (2026-01-26)
- 🎉 初始版本发布
- ✨ 基础监控与下单功能
- ✨ 多账号管理
- ✨ 每日任务自动领取

---

## 📞 联系与支持

如有问题或建议,欢迎提交 Issue 或 Pull Request。

**祝您使用愉快!** 🚀
