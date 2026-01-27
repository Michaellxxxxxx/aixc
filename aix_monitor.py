"""
AIX Crypto Prediction Market 浏览器批量监控下单脚本
===================================================
逻辑：Playwright 监控网页倒计时 + 颜色条件 → 触发 C10 API 查询 → 批量下单

触发条件（单一模式，最低延迟优化）：
1. 倒计时剩余时间 = 配置的 countdown_seconds（默认3秒）
2. 倒计时颜色为 unknown/emerald/rose 任一即触发

作者: Antigravity
日期: 2026-01-26
"""

import asyncio
import aiohttp
import json
import os
import csv
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from colorama import init, Fore, Style
from order_manager import OrderManager
from enhanced_browser_api_client import EnhancedBrowserAPIClient

# 初始化终端彩色输出
init()

# ==================== 配置加载 ====================

def load_config():
    """多级配置加载：系统配置(JSON) + 账号列表(CSV)"""
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "config.json")
    csv_path = os.path.join(base_dir, "accounts.csv")
    
    # 1. 加载基础 JSON 配置
    cfg = {
        "api": {"base_url": "https://hub.aixcrypto.ai/api/game", "timeout_seconds": 7},
        "trigger": {
            "target_seconds": 3.0, 
            "visual_offset": 0.0, 
            "auto_bet": {"enabled": False},
            "browser_trigger": {
                "countdown_seconds": 3,
                "required_color": "emerald"
            }
        },
        "accounts": []
    }
    
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cfg.update(json.load(f))
        except:
            print(f"{Fore.RED}⚠ JSON 配置解析失败，将使用默认设置{Style.RESET_ALL}")

    # 2. 自动加载 CSV 账号覆盖 JSON 中的账号
    if os.path.exists(csv_path):
        try:
            csv_accounts = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['enabled'] = row.get('enabled', 'true').lower() == 'true'
                    row = {k.strip(): v for k, v in row.items()}
                    csv_accounts.append(row)
            
            if csv_accounts:
                cfg["accounts"] = csv_accounts
                print(f"{Fore.GREEN}✓ 已从 accounts.csv 成功加载 {len(csv_accounts)} 个账号{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}⚠ 无法读取 accounts.csv: {e}{Style.RESET_ALL}")

    return cfg

_config = load_config()

class Config:
    API = _config.get("api", {})
    BASE_URL = API.get("base_url", "https://hub.aixcrypto.ai/api/game")
    TIMEOUT = API.get("timeout_seconds", 7)
    
    TRIGGER = _config.get("trigger", {})
    CONCURRENCY = TRIGGER.get("concurrency", 4)
    AUTO_BET_ENABLED = TRIGGER.get("auto_bet", {}).get("enabled", False)
    
    # 代理配置
    PROXY = _config.get("proxy", {})
    PROXY_ENABLED = PROXY.get("enabled", False)
    PROXY_HOST = PROXY.get("host", "74.81.81.81")
    PROXY_PORT = PROXY.get("start_port", 10000)
    PROXY_USERNAME = PROXY.get("username", "")
    PROXY_PASSWORD = PROXY.get("password", "")
    PROXY_COUNTRIES = PROXY.get("countries", "sg,gb,hk,jp")
    
    # 浏览器触发配置
    BROWSER_TRIGGER = TRIGGER.get("browser_trigger", {})
    COUNTDOWN_SECONDS = BROWSER_TRIGGER.get("countdown_seconds", 3)
    HEADLESS = BROWSER_TRIGGER.get("headless", True)  # 无头模式，适合服务器
    
    # 触发颜色列表（单一模式：只要是这些颜色之一就触发）
    TRIGGER_COLORS = frozenset(["unknown", "emerald", "rose", "red"])
    
    ACCOUNTS = _config.get("accounts", [])
    
    # 网页配置
    PAGE_URL = "https://hub.aixcrypto.ai/#prediction-market"
    
    # 倒计时容器选择器（包含颜色信息的父元素）
    COUNTDOWN_CONTAINER_SELECTOR = (
        "#root > div > div > main > div > div:nth-child(1) > div > "
        "div.relative.z-10 > div.grid.grid-cols-1.lg\\:grid-cols-12.gap-2 > "
        "div.lg\\:col-span-8.flex.flex-col.gap-2 > "
        "div.grid.grid-cols-1.md\\:grid-cols-2.gap-2.flex-1 > "
        "div:nth-child(1) > div:nth-child(2) > div > "
        "span.text-xl.font-bold.tracking-tight.tabular-nums"
    )
    
    # C10 开盘价选择器（从网页读取）
    C10_OPEN_SELECTOR = (
        "#root > div > div > main > div > div:nth-child(1) > div > "
        "div.relative.z-10 > div.grid.grid-cols-1.lg\\:grid-cols-12.gap-2 > "
        "div.lg\\:col-span-8.flex.flex-col.gap-2 > "
        "div.backdrop-blur-md.rounded-\\[7px\\].border-white\\/5.overflow-hidden.relative.border-0 > "
        "div.p-6.flex.items-end.justify-between > div:nth-child(1) > "
        "div.flex.items-baseline.gap-3 > "
        "span.text-4xl.font-medium.tracking-tight.text-white.tabular-nums.drop-shadow-sm"
    )
    
    # 轮询间隔(毫秒) - 降低间隔可提高触发精度
    POLL_INTERVAL_MS = 50  # 50ms检查一次，更快响应（原100ms）


# ==================== 监控器 ====================

class AIXBrowserBatchMonitor:
    """基于浏览器的AIX批量监控器 - 单浏览器监控 + API批量下单"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.http_session = None
        self.order_manager = None
        self.api_client = None  # 将在页面加载后初始化
        
        self.last_triggered_round = None
        self.current_round = 0
        self.stats = {
            "triggers": 0,
            "api_calls": 0,
            "bets": 0,
            "errors": 0
        }
    
    async def start(self):
        """启动监控"""
        self.print_banner()
        
        print(f"{Fore.CYAN}正在启动浏览器...{Style.RESET_ALL}")
        
        # 启动Playwright
        self.playwright = await async_playwright().start()
        headless_mode = "无头" if Config.HEADLESS else "有窗口"
        print(f"{Fore.CYAN}浏览器模式: {headless_mode}{Style.RESET_ALL}")
        
        # 构建代理配置 (兼容 DataImpulse 动态格式)
        proxy_config = None
        if Config.PROXY_ENABLED and Config.PROXY_HOST and Config.PROXY_USERNAME:
            # 使用第一个备用端口或固定端口进行监控
            proxy_url = f"http://{Config.PROXY_HOST}:{Config.PROXY_PORT}"
            # DataImpulse 特殊格式: username__cr.{countries}
            formatted_username = f"{Config.PROXY_USERNAME}__cr.{Config.PROXY_COUNTRIES}"
            
            proxy_config = {
                "server": proxy_url,
                "username": formatted_username,
                "password": Config.PROXY_PASSWORD
            }
            print(f"{Fore.GREEN}✓ DataImpulse 代理已启用: {Config.PROXY_HOST}:{Config.PROXY_PORT}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  代理身份: {formatted_username}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}[!] 代理未启用或配置不全 (可能导致 IP 被封){Style.RESET_ALL}")
        
        # 启动浏览器 (添加反检测参数)
        self.browser = await self.playwright.chromium.launch(
            headless=Config.HEADLESS,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080'
            ]
        )
        
        # 创建浏览器上下文 (包含代理和真实浏览器特征)
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'Asia/Shanghai'
        }
        
        if proxy_config:
            context_options['proxy'] = proxy_config
        
        context = await self.browser.new_context(**context_options)
        
        
        # 创建页面
        self.page = await context.new_page()
        
        # 注意: Stealth 插件将在页面加载后应用,避免阻止内容渲染
        
        
        # 创建HTTP会话和订单管理器 (优化连接池配置)
        connector = aiohttp.TCPConnector(
            limit=100,              # 总连接数
            limit_per_host=20,      # 每个host的连接数
            ttl_dns_cache=300,      # DNS缓存5分钟
            keepalive_timeout=60,   # 保持连接60秒
            force_close=False,      # 不强制关闭连接
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        
        self.http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        self.order_manager = OrderManager(self.http_session, Config)
        
        print(f"{Fore.CYAN}正在打开页面: {Config.PAGE_URL}{Style.RESET_ALL}")
        
        # 增加超时时间，并使用重试机制
        for attempt in range(3):
            try:
                # 🔑 关键修复: 使用 load 等待策略 (networkidle 会超时)
                # 注意: Stealth 插件需要更长时间初始化
                await self.page.goto(Config.PAGE_URL, wait_until="load", timeout=60000)
                # 额外等待让页面完全渲染 (Stealth + React/Vue 需要更长时间)
                print(f"{Fore.CYAN}等待页面渲染 (Stealth 插件初始化中)...{Style.RESET_ALL}")
                await asyncio.sleep(15)  # 增加到 15 秒,确保 Stealth 和 JS 完全执行
                print(f"{Fore.GREEN}✓ 页面加载完成{Style.RESET_ALL}")
                break
            except Exception as e:
                if attempt < 2:
                    print(f"{Fore.YELLOW}[!] 页面加载超时，重试中... ({attempt + 1}/3){Style.RESET_ALL}")
                    await asyncio.sleep(2)
                else:
                    raise Exception(f"页面加载失败: {e}")
        
        # 🔑 在页面加载后应用 Stealth 插件 (避免阻止内容渲染)
        print(f"{Fore.CYAN}正在应用 Stealth 反检测插件...{Style.RESET_ALL}")
        await stealth_async(self.page)
        print(f"{Fore.GREEN}✓ Stealth 插件已应用{Style.RESET_ALL}")
        
        # 🔑 关键步骤：等待 CloudFlare 验证完成
        print(f"{Fore.CYAN}正在等待 CloudFlare 验证...{Style.RESET_ALL}")
        
        # 智能等待 CloudFlare 验证
        max_wait_time = 30  # 从 15 秒增加到 30 秒,避免 403 错误
        check_interval = 2  # 每2秒检查一次
        waited = 0
        
        while waited < max_wait_time:
            await asyncio.sleep(check_interval)
            waited += check_interval
            
            # 检查页面是否已通过验证 (尝试访问 API)
            try:
                test_result = await self.page.evaluate(f'''async () => {{
                    try {{
                        const response = await fetch("{Config.BASE_URL}/current-round", {{
                            method: 'GET',
                            headers: {{ 'Accept': 'application/json' }},
                            credentials: 'include'
                        }});
                        return {{ status: response.status, ok: response.ok }};
                    }} catch (e) {{
                        return {{ error: e.toString() }};
                    }}
                }}''')
                
                if test_result.get("ok"):
                    print(f"{Fore.GREEN}✓ CloudFlare 验证通过 (耗时: {waited}秒){Style.RESET_ALL}")
                    break
                elif test_result.get("status") == 403:
                    print(f"{Fore.YELLOW}[{waited}s] 仍在验证中...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}[{waited}s] 检测中... (状态: {test_result.get('status', 'unknown')}){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}[{waited}s] 验证检测异常: {e}{Style.RESET_ALL}")
        
        if waited >= max_wait_time:
            print(f"{Fore.YELLOW}[!] 验证超时,但将继续尝试...{Style.RESET_ALL}")
        
        # ⚡ 初始化增强版浏览器 API 客户端 (利用已打开的页面)
        print(f"{Fore.CYAN}初始化增强版浏览器 API 客户端...{Style.RESET_ALL}")
        self.api_client = EnhancedBrowserAPIClient(
            page=self.page,
            timeout=10,
            max_retries=3,
            verbose=True
        )
        
        # 测试 API 连通性
        print(f"{Fore.CYAN}测试 API 连通性...{Style.RESET_ALL}")
        test_data = await self.api_client.get_current_round()
        
        if test_data and test_data.get("round"):
            round_number = test_data.get("round", {}).get("roundNumber")
            print(f"{Fore.GREEN}✓ API 连通性测试成功 (Round #{round_number}){Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}[!] API 测试失败，但将继续运行...{Style.RESET_ALL}")
        
        # ⚡ 预热Session (减少首次下单延迟)
        if Config.AUTO_BET_ENABLED and len(Config.ACCOUNTS) > 0:
            warmup_count = min(Config.CONCURRENCY, len(Config.ACCOUNTS))
            await self.order_manager.warmup_sessions(count=warmup_count)
        
        print(f"{Fore.GREEN}✓ 监控已启动{Style.RESET_ALL}")
        print(f"  触发条件: 倒计时 = {Config.COUNTDOWN_SECONDS}秒")
        print(f"  颜色条件: {Fore.CYAN}unknown/emerald/rose 任一即触发{Style.RESET_ALL}")
        print(f"  账号总数: {len(Config.ACCOUNTS)}")
        print(f"  全局下单: {'开启' if Config.AUTO_BET_ENABLED else '关闭'}")
        print("-" * 60)
        
        try:
            await self.monitor_loop()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠ 监控已停止{Style.RESET_ALL}")
        finally:
            await self.cleanup()
    

    
    async def monitor_loop(self):
        """监控循环"""
        print(f"\n{Fore.CYAN}[DEBUG] 进入监控循环...{Style.RESET_ALL}")
        last_status = None
        
        while True:
            try:
                # 获取倒计时状态（秒数和颜色）
                countdown_info = await self.get_countdown_info()
                
                # 调试: 首次获取时输出 (降低日志频率)
                if last_status is None and countdown_info is None:
                    # 仅在页面还没加载出来时偶尔提示一次，不刷屏
                    pass
                
                if countdown_info:
                    seconds = countdown_info["seconds"]
                    color = countdown_info["color"]
                    raw_text = countdown_info["raw_text"]
                    
                    # 构建状态字符串用于去重显示
                    status_key = f"{raw_text}_{color}"
                    
                    if status_key != last_status:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        color_display = Fore.GREEN if color == "emerald" else (Fore.RED if color in ["rose", "red"] else Fore.BLUE)
                        print(f"\r[{timestamp}] 倒计时: {color_display}{raw_text}{Style.RESET_ALL} | 颜色: {color_display}{color}{Style.RESET_ALL}          ", 
                              end="", flush=True)
                        last_status = status_key
                    
                    # 调试：当秒数等于触发秒数时，打印详细信息
                    if seconds == Config.COUNTDOWN_SECONDS:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        is_trigger = color in Config.TRIGGER_COLORS
                        print(f"\n{Fore.YELLOW}[DEBUG {timestamp}] 秒数={seconds}, 颜色={color}, 触发={is_trigger}{Style.RESET_ALL}")
                    
                    # 检查是否满足触发条件
                    if self._should_trigger(seconds, color):
                        print(f"{Fore.CYAN}[DEBUG] 触发条件满足，正在获取 round 信息...{Style.RESET_ALL}")
                        # ⚡ 性能优化：并行获取round信息和C10数据
                        round_info = await self.get_current_round()
                        current_round = round_info.get("round", {}).get("roundNumber") if round_info else None
                        
                        print(f"{Fore.CYAN}[DEBUG] current_round={current_round}, last_triggered_round={self.last_triggered_round}{Style.RESET_ALL}")
                        
                        if current_round and current_round != self.last_triggered_round:
                            print()  # 换行
                            
                            # 🚀 移除截图功能以减少延迟（原需要100-300ms）
                            # 如需调试可临时启用：
                            # try:
                            #     screenshot_path = os.path.join(os.path.dirname(__file__), f"trigger_screenshot_{current_round}.png")
                            #     await self.page.screenshot(path=screenshot_path)
                            # except: pass
                            
                            self.current_round = current_round
                            await self.trigger_order(round_info)
                            self.last_triggered_round = current_round
                        elif not current_round:
                            print(f"{Fore.RED}[DEBUG] 无法获取 current_round，跳过触发{Style.RESET_ALL}")
                        elif current_round == self.last_triggered_round:
                            print(f"{Fore.YELLOW}[DEBUG] 重复轮次 #{current_round}，跳过触发{Style.RESET_ALL}")
                
                # 引入随机抖动 (Jitter)，模拟真人不规则操作频率
                # 基础间隔 + 0-50ms 随机波动
                jitter = random.uniform(0, 0.05)
                await asyncio.sleep(Config.POLL_INTERVAL_MS / 1000 + jitter)
                
            except Exception as e:
                self.stats["errors"] += 1
                print(f"\n{Fore.RED}错误: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    def _should_trigger(self, seconds: int, color: str) -> bool:
        """检查是否满足触发条件（单一模式，最低延迟优化）"""
        # 单一判断：秒数匹配 AND 颜色在触发列表中
        return seconds == Config.COUNTDOWN_SECONDS and color in Config.TRIGGER_COLORS
    
    async def get_countdown_info(self) -> dict:
        """获取倒计时信息（秒数和颜色）- 性能优化版本"""
        try:
            # 优化1：优先查询最可能触发的颜色（emerald/rose），减少查询次数
            # 优化2：合并查询逻辑，减少代码路径
            
            # 按概率顺序尝试：emerald > rose > red > unknown（跳过blue因为不触发）
            color_checks = [
                (".text-emerald-400", "emerald"),
                (".text-rose-400", "rose"),
                (".text-red-400", "red")
            ]
            
            for suffix, color_name in color_checks:
                element = await self.page.query_selector(Config.COUNTDOWN_CONTAINER_SELECTOR + suffix)
                if element:
                    text = await element.text_content()
                    seconds = self._parse_countdown(text)
                    if seconds is not None:
                        return {"seconds": seconds, "color": color_name, "raw_text": text}
            
            # 备用：获取基础选择器并从class推断颜色
            element = await self.page.query_selector(Config.COUNTDOWN_CONTAINER_SELECTOR)
            if element:
                text = await element.text_content()
                class_attr = await element.get_attribute("class") or ""
                
                # 快速颜色识别
                if "text-emerald" in class_attr:
                    color = "emerald"
                elif "text-rose" in class_attr:
                    color = "rose"
                elif "text-red" in class_attr:
                    color = "red"
                elif "text-blue" in class_attr:
                    color = "blue"  # 不触发，但仍记录
                else:
                    color = "unknown"  # 可能触发
                
                seconds = self._parse_countdown(text)
                if seconds is not None:
                    return {"seconds": seconds, "color": color, "raw_text": text}
            
            return None
        except Exception as e:
            return None
    
    def _parse_countdown(self, text: str) -> int:
        """解析倒计时文本，返回秒数"""
        if not text:
            return None
        
        text = text.strip()
        
        # 格式: "00:03" -> 3秒
        if ":" in text and len(text) == 5:
            try:
                parts = text.split(":")
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            except:
                return None
        
        return None
    
    async def get_c10_open_from_page(self) -> float:
        """从网页 DOM 读取 C10 开盘价"""
        try:
            element = await self.page.query_selector(Config.C10_OPEN_SELECTOR)
            if element:
                text = await element.text_content()
                if text:
                    # 清理文本（去除空格、逗号等）
                    text = text.strip().replace(",", "").replace(" ", "")
                    try:
                        value = float(text)
                        return value
                    except ValueError:
                        print(f"{Fore.YELLOW}[!] 无法解析开盘价文本: {text}{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.YELLOW}[!] 读取页面开盘价失败: {e}{Style.RESET_ALL}")
            return None
    
    async def get_current_round(self) -> dict:
        """获取当前轮次信息 - 使用浏览器内 API"""
        try:
            data = await self.api_client.get_current_round()
            
            # 检查数据有效性
            if data:
                round_info = data.get("round", {})
                round_number = round_info.get("roundNumber")
                
                # 验证关键字段
                if round_number is not None and round_number > 0:
                    print(f"{Fore.CYAN}[DEBUG] 浏览器 API 返回 roundNumber: {round_number}{Style.RESET_ALL}")
                    return data
                else:
                    print(f"{Fore.YELLOW}[!] Round 数据无效 (roundNumber={round_number}){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[!] current-round API 返回空数据{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}[!] current-round API 请求异常: {e}{Style.RESET_ALL}")
        
        return {}
    

    async def trigger_order(self, round_info: dict):
        """触发下单：查询C10 API并批量下单"""
        self.stats["triggers"] += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"{Fore.MAGENTA}🎯 [{timestamp}] 触发条件满足! (倒计时={Config.COUNTDOWN_SECONDS}s){Style.RESET_ALL}")
        
        # ⚡ 性能优化：并行获取网页开盘价和API C10数据（节省约50%时间）
        c10_open_from_page, c10_data = await asyncio.gather(
            self.get_c10_open_from_page(),
            self.fetch_c10_data(),
            return_exceptions=True
        )
        
        # 处理异常情况
        if isinstance(c10_data, Exception) or not c10_data:
            print(f"{Fore.RED}[!] 无法获取C10数据，跳过下单{Style.RESET_ALL}")
            return
        
        if isinstance(c10_open_from_page, Exception):
            c10_open_from_page = None
        
        # 安全获取 C10 当前价,确保不是 None
        c10_curr = c10_data.get("c10Index") or 0
        if c10_curr is None:
            c10_curr = 0
        
        # 确定开盘价优先级:页面 > API > 当前价
        if c10_open_from_page and c10_open_from_page > 0:
            c10_open = c10_open_from_page
            print(f"{Fore.CYAN}[✓] 开盘价来源: 网页 DOM{Style.RESET_ALL}")
        else:
            c10_open = c10_data.get("c10IndexBefore") or c10_curr
            if c10_open is None or c10_open == 0:
                c10_open = c10_curr
            print(f"{Fore.YELLOW}[!] 开盘价来源: API (备用){Style.RESET_ALL}")
        
        # 确保两个值都是有效数字
        if c10_curr == 0 or c10_open == 0:
            print(f"{Fore.RED}[!] C10 数据无效 (当前={c10_curr}, 开盘={c10_open}), 跳过下单{Style.RESET_ALL}")
            return
        
        diff = c10_curr - c10_open
        pct_change = (diff / c10_open * 100) if c10_open > 0 else 0
        color = Fore.GREEN if diff >= 0 else Fore.RED
        pred = "UP" if diff >= 0 else "DOWN"
        
        # 显示C10快照
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔔 Round #{self.current_round} 趋势: {color}{pred}{Style.RESET_ALL}")
        print(f"   C10 开盘: {Fore.WHITE}{c10_open:.4f}{Style.RESET_ALL}")
        print(f"   C10 当前: {color}{c10_curr:.4f}{Style.RESET_ALL}")
        print(f"   涨跌幅:   {color}{diff:+.4f} ({pct_change:+.4f}%){Style.RESET_ALL}")
        
        # 批量下单
        print(f"{Fore.CYAN}[DEBUG] AUTO_BET_ENABLED={Config.AUTO_BET_ENABLED}, 账号数={len(Config.ACCOUNTS)}{Style.RESET_ALL}")
        if Config.AUTO_BET_ENABLED:
            print(f"  [▶] 正在批量下单...")
            success_count = await self.order_manager.place_batch_bets(pred, self.current_round)
            print(f"{Fore.CYAN}[DEBUG] place_batch_bets 返回: success_count={success_count}{Style.RESET_ALL}")
            self.stats["bets"] += success_count
            print(f"  [✓] 下单完成: {success_count}/{len(Config.ACCOUNTS)} 成功")
        else:
            print(f"  [⏸] 自动下单已关闭，仅显示信号")
        
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    async def fetch_c10_data(self) -> dict:
        """获取C10价格数据 - 使用浏览器内 API"""
        self.stats["api_calls"] += 1
        
        try:
            data = await self.api_client.get_c10_composition()
            
            # 检查数据有效性
            if data:
                c10_index = data.get("c10Index")
                
                # 验证关键字段是否存在且有效
                if c10_index is not None and c10_index > 0:
                    return data
                else:
                    print(f"{Fore.YELLOW}[!] C10 数据无效 (c10Index={c10_index}){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[!] C10 API 返回空数据{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}[!] C10 API 请求异常: {e}{Style.RESET_ALL}")
        
        return None
    

    def print_banner(self):
        """打印启动横幅"""
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║   AIX Browser Batch Monitor - 浏览器监控 + 批量下单       ║
║       https://hub.aixcrypto.ai/#prediction-market         ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    async def cleanup(self):
        """清理资源"""
        # 浏览器 API 客户端无需特殊清理
        if self.http_session:
            await self.http_session.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        print(f"\n{Fore.CYAN}═══ 运行统计 ═══{Style.RESET_ALL}")
        print(f"  触发次数: {self.stats['triggers']}")
        print(f"  API调用: {self.stats['api_calls']}")
        print(f"  下单成功: {self.stats['bets']}")
        print(f"  错误次数: {self.stats['errors']}")


# ==================== 入口 ====================

if __name__ == "__main__":
    asyncio.run(AIXBrowserBatchMonitor().start())
