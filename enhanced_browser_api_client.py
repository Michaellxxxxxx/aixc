"""
增强版浏览器内 API 客户端 - 完全模拟真实浏览器请求
=======================================================

基于真实浏览器请求头/响应头标准构建
完全模拟 Chrome 144 的请求特征

核心特性:
1. 精确复制真实浏览器的所有请求头
2. 自动继承浏览器的 Cookie 和认证状态
3. 完整的 Sec-Fetch-* 头部
4. 正确的 Accept-Encoding 和 Accept-Language
5. 真实的 Referer 和 Origin
"""

from typing import Optional, Dict, Any
from playwright.async_api import Page
from colorama import init, Fore, Style
from datetime import datetime
import time
import json

init()


class EnhancedBrowserAPIClient:
    """增强版浏览器 API 客户端 - 完全模拟真实浏览器"""
    
    BASE_URL = "https://hub.aixcrypto.ai/api/game"
    CURRENT_ROUND_URL = f"{BASE_URL}/current-round"
    C10_COMPOSITION_URL = f"{BASE_URL}/c10-composition"
    
    # 真实浏览器请求头模板 (基于你提供的截图)
    REAL_HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Priority": "u=1, i",
        "Referer": "https://hub.aixcrypto.ai/",
        "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    }
    
    def __init__(
        self,
        page: Page,
        timeout: int = 10,
        max_retries: int = 3,
        verbose: bool = False
    ):
        """
        初始化增强版浏览器 API 客户端
        
        Args:
            page: Playwright 页面对象
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            verbose: 是否显示详细日志
        """
        self.page = page
        self.timeout = timeout * 1000  # 转换为毫秒
        self.max_retries = max_retries
        self.verbose = verbose
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "status_codes": {}
        }
    
    def _log(self, message: str, level: str = "INFO"):
        """内部日志方法"""
        if self.verbose:
            color = {
                "INFO": Fore.CYAN,
                "SUCCESS": Fore.GREEN,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED
            }.get(level, Fore.WHITE)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"{color}[{level} {timestamp}] {message}{Style.RESET_ALL}")
    
    async def _fetch_api(self, url: str, method: str = "GET") -> Optional[Dict[str, Any]]:
        """
        在浏览器内执行完全模拟真实浏览器的 fetch 请求
        
        Args:
            url: API URL
            method: HTTP 方法
            
        Returns:
            成功返回 JSON 数据,失败返回 None
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                self.stats["total_requests"] += 1
                
                self._log(f"尝试 {attempt}/{self.max_retries}: {method} {url}", "INFO")
                
                # 构建完全模拟真实浏览器的 fetch 请求
                # 注意: 这里使用 JavaScript 模板字符串来避免转义问题
                headers_json = json.dumps(self.REAL_HEADERS)
                
                result = await self.page.evaluate(f"""async () => {{
                    try {{
                        // 使用真实浏览器的完整请求头
                        const headers = {headers_json};
                        
                        const response = await fetch("{url}", {{
                            method: '{method}',
                            headers: headers,
                            credentials: 'include',  // 自动携带 Cookie
                            cache: 'no-cache',       // 禁用缓存,获取最新数据
                            mode: 'cors',            // CORS 模式
                            redirect: 'follow'       // 跟随重定向
                        }});
                        
                        // 记录响应状态
                        const status = response.status;
                        const statusText = response.statusText;
                        const contentType = response.headers.get('content-type');
                        
                        // 检查响应状态
                        if (!response.ok) {{
                            // 尝试读取错误响应体
                            let errorBody = '';
                            try {{
                                errorBody = await response.text();
                            }} catch (e) {{
                                errorBody = 'Unable to read error body';
                            }}
                            
                            return {{ 
                                error: true, 
                                status: status,
                                statusText: statusText,
                                contentType: contentType,
                                body: errorBody
                            }};
                        }}
                        
                        // 解析 JSON 响应
                        const data = await response.json();
                        
                        return {{ 
                            success: true, 
                            data: data,
                            status: status,
                            contentType: contentType
                        }};
                        
                    }} catch (e) {{
                        return {{ 
                            error: true, 
                            message: e.toString(),
                            stack: e.stack 
                        }};
                    }}
                }}""")
                
                elapsed = time.time() - start_time
                self.stats["total_time"] += elapsed
                
                # 记录状态码
                status = result.get("status", 0)
                if status:
                    self.stats["status_codes"][status] = self.stats["status_codes"].get(status, 0) + 1
                
                # 检查结果
                if result.get("success"):
                    self.stats["success_requests"] += 1
                    self.stats["avg_time"] = self.stats["total_time"] / self.stats["success_requests"]
                    self._log(f"请求成功 (状态: {status}, 耗时: {elapsed*1000:.0f}ms)", "SUCCESS")
                    return result.get("data")
                
                elif result.get("error"):
                    error_msg = result.get("message", "")
                    status = result.get("status", 0)
                    status_text = result.get("statusText", "")
                    content_type = result.get("contentType", "")
                    body = result.get("body", "")
                    
                    # 详细的错误日志
                    if status == 403:
                        self._log(f"CloudFlare 拦截 (403) - 可能需要重新验证", "ERROR")
                        if "text/html" in content_type:
                            self._log("响应为 HTML 页面,确认为 CloudFlare 验证页", "WARNING")
                    elif status == 429:
                        self._log(f"请求过于频繁 (429) - 触发速率限制", "ERROR")
                    elif status:
                        self._log(f"HTTP {status}: {status_text}", "ERROR")
                    else:
                        self._log(f"请求异常: {error_msg}", "ERROR")
                    
                    # 如果不是最后一次尝试,则重试
                    if attempt < self.max_retries:
                        import asyncio
                        retry_delay = min(2 ** attempt, 5)  # 指数退避,最多5秒
                        self._log(f"等待 {retry_delay}s 后重试...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                
            except Exception as e:
                self._log(f"异常: {e}", "ERROR")
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(1)
                    continue
        
        # 所有重试都失败
        self.stats["failed_requests"] += 1
        return None
    
    async def get_current_round(self) -> Optional[Dict[str, Any]]:
        """
        获取当前 Round 数据
        
        Returns:
            成功返回 JSON 数据,失败返回 None
            
        示例响应:
        {
            "round": {
                "roundNumber": 12345,
                "startTime": "2026-01-27T05:00:00.000Z",
                "endTime": "2026-01-27T05:05:00.000Z",
                "status": "ACTIVE"
            }
        }
        """
        return await self._fetch_api(self.CURRENT_ROUND_URL)
    
    async def get_c10_composition(self) -> Optional[Dict[str, Any]]:
        """
        获取 C10 组成数据
        
        Returns:
            成功返回 JSON 数据,失败返回 None
            
        示例响应:
        {
            "c10Index": 1234.5678,
            "c10IndexBefore": 1230.0000,
            "composition": [...]
        }
        """
        return await self._fetch_api(self.C10_COMPOSITION_URL)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印性能统计"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 增强版浏览器 API 性能统计{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"  总请求数: {self.stats['total_requests']}")
        print(f"  成功: {Fore.GREEN}{self.stats['success_requests']}{Style.RESET_ALL}")
        print(f"  失败: {Fore.RED}{self.stats['failed_requests']}{Style.RESET_ALL}")
        
        if self.stats['success_requests'] > 0:
            print(f"  平均耗时: {self.stats['avg_time']*1000:.0f}ms")
            success_rate = (self.stats['success_requests'] / self.stats['total_requests']) * 100
            print(f"  成功率: {success_rate:.1f}%")
        
        if self.stats['status_codes']:
            print(f"\n  状态码分布:")
            for code, count in sorted(self.stats['status_codes'].items()):
                color = Fore.GREEN if code == 200 else Fore.RED
                print(f"    {color}{code}{Style.RESET_ALL}: {count}")


# ============ 示例用法 ============

async def demo():
    """演示如何使用增强版浏览器 API 客户端"""
    from playwright.async_api import async_playwright
    
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 增强版浏览器 API 客户端演示{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    playwright = await async_playwright().start()
    
    # 使用真实的浏览器配置
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080'
        ]
    )
    
    # 创建上下文,模拟真实浏览器环境
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        locale='zh-CN',
        timezone_id='Asia/Shanghai'
    )
    
    page = await context.new_page()
    
    # 注入反检测脚本
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
    """)
    
    try:
        # 打开页面并等待加载
        print(f"{Fore.YELLOW}[1] 打开页面...{Style.RESET_ALL}")
        await page.goto("https://hub.aixcrypto.ai/#prediction-market", wait_until="domcontentloaded")
        
        # 等待 CloudFlare 验证
        print(f"{Fore.YELLOW}[2] 等待 CloudFlare 验证 (10秒)...{Style.RESET_ALL}")
        import asyncio
        await asyncio.sleep(10)
        
        # 创建增强版 API 客户端
        client = EnhancedBrowserAPIClient(page, verbose=True)
        
        # 获取当前 Round
        print(f"\n{Fore.YELLOW}[3] 获取当前 Round...{Style.RESET_ALL}")
        round_data = await client.get_current_round()
        
        if round_data:
            round_info = round_data.get("round", {})
            print(f"{Fore.GREEN}[✓] 成功!{Style.RESET_ALL}")
            print(f"    Round 编号: {round_info.get('roundNumber')}")
            print(f"    结束时间: {round_info.get('endTime')}")
            print(f"    状态: {round_info.get('status')}")
        else:
            print(f"{Fore.RED}[✗] 获取 Round 数据失败{Style.RESET_ALL}")
        
        # 获取 C10 组成
        print(f"\n{Fore.YELLOW}[4] 获取 C10 组成数据...{Style.RESET_ALL}")
        c10_data = await client.get_c10_composition()
        
        if c10_data:
            c10_index = c10_data.get("c10Index")
            c10_prev = c10_data.get("c10IndexBefore")
            print(f"{Fore.GREEN}[✓] 成功!{Style.RESET_ALL}")
            print(f"    当前 C10: {c10_index}")
            print(f"    之前 C10: {c10_prev}")
            if c10_index and c10_prev:
                diff = c10_index - c10_prev
                percent = (diff / c10_prev) * 100 if c10_prev != 0 else 0
                color = Fore.GREEN if diff >= 0 else Fore.RED
                print(f"    涨跌: {color}{diff:+.4f} ({percent:+.2f}%){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[✗] 获取 C10 数据失败{Style.RESET_ALL}")
        
        # 打印性能统计
        client.print_stats()
        
    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
