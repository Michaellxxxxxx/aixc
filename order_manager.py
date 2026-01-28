import aiohttp
import asyncio
import json
import os
import time
from eth_account import Account
from eth_account.messages import encode_defunct
from colorama import Fore, Style
from proxy_manager import build_proxy_url, initialize_port_pool, mark_proxy_failed

# Session 缓存文件路径
SESSION_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'session_cache.json')

class OrderManager:
    """批量自动登录与下单管理模块 (私钥模式版) - DataImpulse 动态代理"""
    
    def __init__(self, session: aiohttp.ClientSession, config_obj):
        self.session = session
        self.config = config_obj
        # 从文件加载缓存的 Session
        self.session_cache, self.user_status_cache = self._load_session_cache()
        # 记录已完成的账号 (达到100次上限)
        self.finished_accounts = set()
        # 记录已尝试领取每日任务的账号
        self.tasks_claimed_accounts = set()
        # AIX 配置
        self.BASE_URL = "https://hub.aixcrypto.ai/api"
        
        # 并发配置
        self.concurrency = getattr(self.config, 'CONCURRENCY', 4)
        self.all_accounts = self.config.ACCOUNTS
        self.current_account_index = 0  # 当前轮询到的账号索引
        
        # 预计算地址以用于快速状态检查 (PK -> Address)
        self._address_map = {} 
        for acc in self.all_accounts:
            pk = acc.get('private_key')
            if pk:
                try:
                    self._address_map[pk] = Account.from_key(pk).address
                except:
                    pass
        
        # 账号索引映射 (address -> account_index)
        self._account_index_map = {}
        for idx, acc in enumerate(self.all_accounts):
            pk = acc.get('private_key')
            if pk:
                addr = self._address_map.get(pk)
                if addr:
                    self._account_index_map[addr] = idx
        
        # DataImpulse 代理配置
        self._proxy_config = self._load_proxy_config()
        self._proxy_enabled = bool(self._proxy_config and self._proxy_config.get('enabled', True) 
                                   and self._proxy_config.get('username') 
                                   and self._proxy_config.get('password'))
        
        if self._proxy_enabled:
            print(f"{Fore.GREEN}[✓] DataImpulse 代理已启用: {self._proxy_config.get('host')}:{self._proxy_config.get('start_port')}{Style.RESET_ALL}")
            # 添加代理测试提示
            print(f"{Fore.CYAN}[i] 代理将在首次使用时自动测试连接{Style.RESET_ALL}")
            # 初始化代理端口池
            initialize_port_pool(self._proxy_config, len(self.all_accounts))
            print(f"{Fore.GREEN}[✓] 代理端口池已初始化 (支持故障自动切换){Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}[!] 代理未配置或已禁用，将直连{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}[i] 并发数: {self.concurrency}{Style.RESET_ALL}")
        
        # 代理测试标记
        self._proxy_tested = False
        


    def _load_session_cache(self) -> tuple[dict, dict]:
        """从文件加载 Session 缓存"""
        try:
            if os.path.exists(SESSION_CACHE_FILE):
                with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查缓存是否过期（超过 12 小时）
                    cache_time = data.get('timestamp', 0)
                    if time.time() - cache_time > 12 * 3600:
                        print(f"{Fore.YELLOW}[!] Session 缓存已过期，需要重新登录{Style.RESET_ALL}")
                        return {}, {}
                    
                    session_cache = data.get('sessions', {})
                    status_cache = data.get('status', {})
                    if session_cache:
                        print(f"{Fore.GREEN}[✓] 已加载 {len(session_cache)} 个账号的 Session 缓存{Style.RESET_ALL}")
                    return session_cache, status_cache
        except Exception as e:
            print(f"{Fore.YELLOW}[!] 加载 Session 缓存失败: {e}{Style.RESET_ALL}")
        return {}, {}
    
    def _save_session_cache(self):
        """保存 Session 缓存到文件"""
        try:
            data = {
                'timestamp': time.time(),
                'sessions': self.session_cache,
                'status': self.user_status_cache
            }
            with open(SESSION_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"{Fore.YELLOW}[!] 保存 Session 缓存失败: {e}{Style.RESET_ALL}")
    
    def _invalidate_session(self, addr: str):
        """使某个账号的 Session 失效"""
        if addr in self.session_cache:
            del self.session_cache[addr]
            self._save_session_cache()
            print(f"{Fore.YELLOW}[!] {addr[:10]} Session 已失效，将重新登录{Style.RESET_ALL}")

    def _load_proxy_config(self) -> dict:
        """加载代理配置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('proxy', {})
        except:
            return {}

    def _get_proxy_for_account(self, addr: str) -> str | None:
        """获取账号对应的代理 URL"""
        if not self._proxy_enabled:
            return None
        account_index = self._account_index_map.get(addr, 0)
        return build_proxy_url(self._proxy_config, account_index, addr)
    
    async def _test_proxy_connection(self):
        """测试代理连接是否可用"""
        test_url = "https://hub.aixcrypto.ai/api/game/current-round"
        proxy_url = build_proxy_url(self._proxy_config, 0)
        
        print(f"{Fore.CYAN}[⌛] 正在测试代理连接...{Style.RESET_ALL}")
        
        try:
            async with self.session.get(
                test_url, 
                proxy=proxy_url, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 401, 403]:  # 能连接即可,不要求成功
                    print(f"{Fore.GREEN}[✓] 代理连接正常 (状态码: {resp.status}){Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.YELLOW}[!] 代理响应异常 (状态码: {resp.status}){Style.RESET_ALL}")
                    return False
        except asyncio.TimeoutError:
            print(f"{Fore.RED}[✗] 代理连接超时 - 请检查代理配置{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[i] 代理地址: {self._proxy_config.get('host')}:{self._proxy_config.get('start_port')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}[✗] 代理测试失败: {type(e).__name__} - {str(e)[:100]}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[i] 将尝试继续运行,但可能会遇到连接问题{Style.RESET_ALL}")
            return False

    async def warmup_sessions(self, count: int = 10):
        """预热前N个账号的Session,减少首次下单延迟"""
        print(f"{Fore.CYAN}[⚡ 预热] 正在预热 {count} 个账号的 Session...{Style.RESET_ALL}")
        
        warmup_accounts = [
            acc for acc in self.all_accounts 
            if acc.get("enabled", True) and acc.get("private_key")
        ][:count]
        
        if not warmup_accounts:
            print(f"{Fore.YELLOW}[!] 没有可预热的账号{Style.RESET_ALL}")
            return
        
        start_time = time.time()
        tasks = [
            self.get_session_id(acc["private_key"]) 
            for acc in warmup_accounts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if r and r != "FINISHED" and not isinstance(r, Exception))
        elapsed = time.time() - start_time
        
        print(f"{Fore.GREEN}[✓] 预热完成: {success}/{len(warmup_accounts)} 成功 (耗时: {elapsed:.1f}s){Style.RESET_ALL}")


    async def get_session_id(self, private_key: str, max_retries: int = 3):
        """核心:通过私钥执行登录逻辑,使用独立代理"""
        try:
            addr = Account.from_key(private_key).address
        except:
            return None
        
        # 首次使用时测试代理连接
        if self._proxy_enabled and not self._proxy_tested:
            await self._test_proxy_connection()
            self._proxy_tested = True
        
        # 1. 检查是否达到上限
        if addr in self.finished_accounts:
            return "FINISHED"
            
        # 2. 如果已有 Session，直接返回（无需重新登录）
        if addr in self.session_cache:
            status = self.user_status_cache.get(addr)
            if status and status["dailyBetCount"] >= status["dailyBetLimit"]:
                self.finished_accounts.add(addr)
                self._trigger_daily_tasks_if_needed(addr)
                return "FINISHED"
            # 使用缓存，无需重新登录
            return self.session_cache[addr]

        # 获取账号代理
        proxy_url = self._get_proxy_for_account(addr)
        account_index = self._account_index_map.get(addr, 0)
        
        if proxy_url:
            port = self._proxy_config.get('start_port', 10000) + account_index
            print(f"  {Fore.CYAN}[⌛] {addr[:10]}... 正在登录 (端口 {port})...{Style.RESET_ALL}")
        else:
            print(f"  {Fore.CYAN}[⌛] {addr[:10]}... 正在登录...{Style.RESET_ALL}")
        
        # 完整的浏览器模拟请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/json',
            'Origin': 'https://hub.aixcrypto.ai',
            'Referer': 'https://hub.aixcrypto.ai/',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Priority': 'u=1, i'
        }

        for attempt in range(max_retries + 1):
            try:
                # 步骤 A: 获取挑战
                challenge_url = f"{self.BASE_URL}/users/auth/challenge?address={addr}"
                async with self.session.get(challenge_url, headers=headers, proxy=proxy_url) as resp:
                    if resp.status == 403:
                        raise Exception("403")
                    challenge_data = await resp.json()
                    message = challenge_data.get("message")
                
                # 步骤 B: 签名
                signable = encode_defunct(text=message)
                signed = Account.sign_message(signable, private_key=private_key)
                signature = "0x" + signed.signature.hex()
            
                # 步骤 C: 登录
                login_url = f"{self.BASE_URL}/login"
                payload = {"address": addr, "signature": signature, "message": message}
                async with self.session.post(login_url, json=payload, headers=headers, proxy=proxy_url) as resp:
                    if resp.status == 403:
                        raise Exception("403")
                    if resp.status not in [200, 201]:
                        raise Exception(f"Login failed: {resp.status}")
                    
                    res = await resp.json()
                    sid = res.get("sessionId")
                    
                    # 更新状态缓存
                    self.user_status_cache[addr] = {
                        "credits": res.get("credits", "0"),
                        "dailyBetCount": res.get("dailyBetCount", 0),
                        "dailyBetLimit": res.get("dailyBetLimit", 100)
                    }
                    
                    self.session_cache[addr] = sid
                    
                    # 保存缓存到文件
                    self._save_session_cache()
                    
                    pts = self.user_status_cache[addr]["credits"]
                    port_info = f" (端口 {self._proxy_config.get('start_port', 10000) + account_index})" if proxy_url else ""
                    print(f"  {Fore.GREEN}[✓] {addr[:10]} 登录成功 [PTS: {pts}]{port_info}{Style.RESET_ALL}")
                    
                    if res.get("dailyBetCount", 0) >= res.get("dailyBetLimit", 100):
                        self.finished_accounts.add(addr)
                        self._trigger_daily_tasks_if_needed(addr)
                        return "FINISHED"
                    return sid
                    
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    print(f"  {Fore.YELLOW}[!] {addr[:10]} 登录超时，重试 ({attempt + 1}/{max_retries}){Style.RESET_ALL}")
                    await asyncio.sleep(1)
                    continue
                print(f"  {Fore.RED}[✗] {addr[:10]} 登录超时 (网络延迟过高或代理无法连接){Style.RESET_ALL}")
                return None
            except aiohttp.ClientError as e:
                error_msg = f"{type(e).__name__}: {str(e)[:80]}"
                
                # 检测特定网络错误,标记代理端口故障
                error_type = type(e).__name__
                if error_type in ['ClientHttpProxyError', 'ServerDisconnectedError', 'ClientProxyConnectionError']:
                    if self._proxy_enabled:
                        account_index = self._account_index_map.get(addr, 0)
                        print(f"  {Fore.YELLOW}[!] {addr[:10]} 检测到代理故障: {error_type}{Style.RESET_ALL}")
                        mark_proxy_failed(addr, account_index)
                        # 重新获取代理URL (已切换到新端口)
                        proxy_url = self._get_proxy_for_account(addr)
                
                if attempt < max_retries:
                    print(f"  {Fore.YELLOW}[!] {addr[:10]} 网络错误，重试 ({attempt + 1}/{max_retries}): {error_msg}{Style.RESET_ALL}")
                    await asyncio.sleep(1)
                    continue
                print(f"  {Fore.RED}[✗] {addr[:10]} 网络错误: {error_msg}{Style.RESET_ALL}")
                return None
            except Exception as e:
                import traceback
                error_msg = str(e)
                is_403 = "403" in error_msg
                
                if attempt < max_retries:
                    if is_403:
                        print(f"  {Fore.YELLOW}[!] {addr[:10]} 403 错误，重试 ({attempt + 1}/{max_retries}){Style.RESET_ALL}")
                    else:
                        print(f"  {Fore.YELLOW}[!] {addr[:10]} 请求失败，重试 ({attempt + 1}/{max_retries}): {error_msg[:50]}{Style.RESET_ALL}")
                    await asyncio.sleep(1)
                    continue
                
                error_detail = traceback.format_exc()
                print(f"  {Fore.RED}[✗] {addr[:10]} 登录出错: {type(e).__name__} - {error_msg[:100]}{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}[DEBUG] 详细错误:\n{error_detail[:500]}{Style.RESET_ALL}")
                return None
        
        return None

    async def _place_single_bet(self, account, prediction: str, round_num: int):
        """单账号下单与状态更新逻辑"""
        pk = account.get("private_key")
        label = account.get("label", "Unknown")
        if not pk or not account.get("enabled", True): return False

        sid = await self.get_session_id(pk)
        addr = Account.from_key(pk).address
        
        # 获取状态信息
        status = self.user_status_cache.get(addr, {"credits": "N/A", "dailyBetCount": 0, "dailyBetLimit": 100})
        pts = status["credits"]
        count_val = status["dailyBetCount"]
        limit_val = status["dailyBetLimit"]

        if sid == "FINISHED":
            return False
        if not sid: return False
        
        # 获取账号代理
        proxy_url = self._get_proxy_for_account(addr)
        
        url = f"{self.BASE_URL}/game/bet"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://hub.aixcrypto.ai',
            'Referer': 'https://hub.aixcrypto.ai/',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        payload = {"prediction": prediction.upper(), "sessionId": sid}

        try:
            start_time = time.time()
            async with self.session.post(url, json=payload, headers=headers, timeout=10, proxy=proxy_url) as resp:
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status in [200, 201]:
                    # === 本地状态更新 ===
                    self.user_status_cache[addr]["dailyBetCount"] += 1
                    current_count = self.user_status_cache[addr]["dailyBetCount"]
                    
                    # 保存状态到缓存
                    self._save_session_cache()
                    
                    # 检查是否达标
                    if current_count >= limit_val:
                        self.finished_accounts.add(addr)
                        self._trigger_daily_tasks_if_needed(addr)
                    
                    account_index = self._account_index_map.get(addr, 0)
                    port_info = f" (端口 {self._proxy_config.get('start_port', 10000) + account_index})" if proxy_url else ""
                    print(f"  {Fore.GREEN}[✓] {label} 下单成功 {current_count}/{limit_val} [PTS: {pts}] [延迟: {latency_ms}ms]{port_info}{Style.RESET_ALL}")
                    return True
                elif resp.status in [401, 403]:
                    # Session 失效，清除缓存并重试
                    self._invalidate_session(addr)
                    # 重新获取 Session 并下单
                    new_sid = await self.get_session_id(pk)
                    if new_sid and new_sid != "FINISHED":
                        payload["sessionId"] = new_sid
                        retry_start = time.time()
                        async with self.session.post(url, json=payload, headers=headers, timeout=10, proxy=proxy_url) as retry_resp:
                            retry_latency_ms = int((time.time() - retry_start) * 1000)
                            if retry_resp.status in [200, 201]:
                                self.user_status_cache[addr]["dailyBetCount"] += 1
                                current_count = self.user_status_cache[addr]["dailyBetCount"]
                                self._save_session_cache()
                                print(f"  {Fore.GREEN}[✓] {label} 重试成功 {current_count}/{limit_val} [PTS: {pts}] [延迟: {retry_latency_ms}ms]{Style.RESET_ALL}")
                                return True
                    print(f"  {Fore.RED}[✗] {label} Session 失效，重新登录后仍失败 [延迟: {latency_ms}ms]{Style.RESET_ALL}")
                    return False
                else:
                    text = await resp.text()
                    if "limit" in text.lower():
                        self.finished_accounts.add(addr)
                        self._trigger_daily_tasks_if_needed(addr)
                    error_msg = text[:80] if len(text) > 80 else text
                    print(f"  {Fore.RED}[✗] {label} 下单失败: {resp.status} - {error_msg} [延迟: {latency_ms}ms]{Style.RESET_ALL}")
                    return False
        except asyncio.TimeoutError:
            print(f"  {Fore.RED}[!] {label} 下单超时 (网络延迟过高){Style.RESET_ALL}")
            return False
        except aiohttp.ClientError as e:
            error_type = type(e).__name__
            print(f"  {Fore.RED}[!] {label} 网络错误: {error_type} - {str(e)[:100]}{Style.RESET_ALL}")
            
            # 检测特定网络错误,标记代理端口故障
            if error_type in ['ClientHttpProxyError', 'ServerDisconnectedError', 'ClientProxyConnectionError']:
                if self._proxy_enabled:
                    account_index = self._account_index_map.get(addr, 0)
                    print(f"  {Fore.YELLOW}[!] {label} 检测到代理故障,自动切换端口...{Style.RESET_ALL}")
                    mark_proxy_failed(addr, account_index)
            
            return False
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"  {Fore.RED}[!] {label} 异常: {type(e).__name__} - {str(e)[:100]}{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}[DEBUG] 详细错误:\n{error_detail[:500]}{Style.RESET_ALL}")
            return False

    def _get_current_batch_accounts(self):
        """获取当前批次的账号（动态替补模式）"""
        # 如果还没有当前批次，初始化批次
        if not hasattr(self, '_current_batch') or self._current_batch is None:
            self._current_batch = self._fetch_next_batch()
            if self._current_batch:
                batch_labels = [acc.get("label", "?")[:8] for acc in self._current_batch]
                print(f"{Fore.CYAN}[→] 初始化批次 ({len(self._current_batch)}/{self.concurrency}): {', '.join(batch_labels)}{Style.RESET_ALL}")
        
        # ⚡ 动态替补：检查当前批次，移除已完成的账户并补充新账户
        if self._current_batch:
            self._refill_batch()
        
        return self._current_batch if self._current_batch else []
    
    def _refill_batch(self):
        """动态替补：移除已完成账户，补充新账户，保持并发数"""
        if not self._current_batch:
            return
        
        # 1. 移除已完成的账户
        finished_in_batch = []
        remaining_in_batch = []
        
        for acc in self._current_batch:
            pk = acc.get("private_key")
            addr = self._address_map.get(pk)
            if addr and addr in self.finished_accounts:
                finished_in_batch.append(acc)
            else:
                remaining_in_batch.append(acc)
        
        # 2. 如果有账户完成，进行替补
        if finished_in_batch:
            for acc in finished_in_batch:
                label = acc.get("label", "?")[:10]
                print(f"{Fore.YELLOW}[✓] {label} 已完成100次，移出批次{Style.RESET_ALL}")
        
        # 3. 补充新账户至目标并发数
        needed = self.concurrency - len(remaining_in_batch)
        
        if needed > 0:
            # 从未使用的账户池中补充
            added_accounts = []
            total = len(self.all_accounts)
            checked = 0
            
            while len(added_accounts) < needed and checked < total:
                acc = self.all_accounts[self.current_account_index]
                self.current_account_index = (self.current_account_index + 1) % total
                checked += 1
                
                # 跳过禁用的账户
                if not acc.get("enabled", True):
                    continue
                
                pk = acc.get("private_key")
                addr = self._address_map.get(pk)
                
                # 跳过已完成的账户
                if addr and addr in self.finished_accounts:
                    continue
                
                # 跳过已在当前批次的账户
                if acc in remaining_in_batch:
                    continue
                
                added_accounts.append(acc)
            
            # 输出补充信息
            if added_accounts:
                added_labels = [acc.get("label", "?")[:10] for acc in added_accounts]
                print(f"{Fore.GREEN}[+] 补充账户 ({len(added_accounts)}): {', '.join(added_labels)}{Style.RESET_ALL}")
                remaining_in_batch.extend(added_accounts)
            elif needed > 0:
                # 没有更多可用账户了
                active_count = sum(1 for acc in self.all_accounts 
                                 if acc.get("enabled", True) and 
                                 self._address_map.get(acc.get("private_key")) not in self.finished_accounts)
                if active_count == 0:
                    print(f"{Fore.YELLOW}[!] 所有账户已完成，无法补充{Style.RESET_ALL}")
        
        # 4. 更新当前批次
        self._current_batch = remaining_in_batch
        
        # 5. 如果批次为空，说明所有账户都已完成
        if not self._current_batch:
            print(f"{Fore.GREEN}[✓] 所有账户均已完成今日任务!{Style.RESET_ALL}")
    
    def _fetch_next_batch(self):
        """获取下一批未完成的账号"""
        batch = []
        total = len(self.all_accounts)
        checked = 0
        
        while len(batch) < self.concurrency and checked < total:
            acc = self.all_accounts[self.current_account_index]
            self.current_account_index = (self.current_account_index + 1) % total
            checked += 1
            
            if not acc.get("enabled", True):
                continue
            pk = acc.get("private_key")
            addr = self._address_map.get(pk)
            if addr and addr in self.finished_accounts:
                continue
            batch.append(acc)
        
        return batch if batch else None

    async def place_batch_bets(self, prediction: str, round_num: int):
        """批量下单 - 动态替补模式：账户完成100次后自动替换，保持满额并发"""
        print(f"{Fore.MAGENTA}[DEBUG] place_batch_bets 被调用: prediction={prediction}, round={round_num}{Style.RESET_ALL}")
        
        if not self.config.AUTO_BET_ENABLED: 
            return 0
        if not self.all_accounts: 
            return 0
        
        # ⚡ 优化：直接获取批次，由 _get_current_batch_accounts 内部处理所有逻辑
        # 避免重复遍历所有账号计算 active_count（节省时间）
        batch = self._get_current_batch_accounts()
        
        # 如果批次为空，说明所有账号都已完成
        if not batch:
            # 只在首次检测到全部完成时输出提示
            if not hasattr(self, '_all_finished_logged'):
                print(f"{Fore.YELLOW}[i] 所有账号均已完成今日任务。{Style.RESET_ALL}")
                self._all_finished_logged = True
            return 0
        
        print(f"{Fore.BLUE}[▶] 并发下单中 ({len(batch)}/{self.concurrency} 账号)...{Style.RESET_ALL}")

        # 并发下单
        tasks = [self._place_single_bet(acc, prediction, round_num) for acc in batch]
        results = await asyncio.gather(*tasks)
        return sum(1 for r in results if r)

    def _trigger_daily_tasks_if_needed(self, addr):
        """检查并触发每日任务（后台执行，不阻塞下单）"""
        if addr in self.finished_accounts and addr not in self.tasks_claimed_accounts:
            sid = self.session_cache.get(addr)
            if sid:
                self.tasks_claimed_accounts.add(addr)
                # 创建后台任务，不阻塞下单流程
                task = asyncio.create_task(self.claim_daily_tasks(addr, sid))
                # 保存任务引用，防止被垃圾回收
                if not hasattr(self, '_background_tasks'):
                    self._background_tasks = set()
                self._background_tasks.add(task)
                # 任务完成后自动清理
                task.add_done_callback(self._background_tasks.discard)

    async def claim_daily_tasks(self, addr, sid):
        """执行每日任务自动签到"""
        proxy_url = self._get_proxy_for_account(addr)
        
        status_url = f"{self.BASE_URL}/tasks/daily?address={addr}"
        claim_url = f"{self.BASE_URL}/tasks/claim"
        
        headers = {
            'Authorization': f'Bearer {sid}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://hub.aixcrypto.ai/'
        }
        
        total_tasks = 3
        completed_count = 0
        
        try:
            async with self.session.get(status_url, headers=headers, proxy=proxy_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    tasks_list = []
                    if isinstance(data, list):
                        tasks_list = data
                    elif isinstance(data, dict):
                         if "data" in data and isinstance(data["data"], list):
                             tasks_list = data["data"]
                         elif "tasks" in data and isinstance(data["tasks"], list):
                             tasks_list = data["tasks"]
                    
                    if tasks_list:
                        total_tasks = len(tasks_list)
                        completed_count = 0
                        
                        claim_headers = headers.copy()
                        claim_headers['Content-Type'] = 'application/json'
                        claim_headers['Origin'] = 'https://hub.aixcrypto.ai'
                        
                        for t in tasks_list:
                            tid = t.get("id") or t.get("taskId")
                            is_done = t.get("completedAt") or t.get("isCompleted") or t.get("isClaimed")
                            
                            if is_done:
                                completed_count += 1
                            else:
                                try:
                                    payload = {"taskId": tid, "sessionId": sid}
                                    async with self.session.post(claim_url, json=payload, headers=claim_headers, proxy=proxy_url) as c_resp:
                                        if c_resp.status in [200, 201]:
                                            completed_count += 1
                                        else:
                                            text = await c_resp.text()
                                            if "claimed" in text.lower() or "completed" in text.lower():
                                                completed_count += 1
                                except:
                                    pass
        except Exception:
            pass
        
        print(f"  {Fore.MAGENTA}[★] {addr[:10]} 每日任务已经完成【{completed_count}/{total_tasks}】{Style.RESET_ALL}")
