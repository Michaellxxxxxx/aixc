"""
批量登录脚本 - DataImpulse 动态代理模式
每个账号自动根据索引分配独立 IP（端口递增）
"""
import asyncio
import aiohttp
import csv
import os
import json
from colorama import Fore, Style, init
from eth_account import Account
from order_manager import OrderManager

init()

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

class SimpleConfig:
    def __init__(self, accounts):
        self.ACCOUNTS = accounts
        self.AUTO_BET_ENABLED = False

def load_accounts():
    """从 accounts.csv 加载账号"""
    accounts = []
    csv_path = os.path.join(os.path.dirname(__file__), 'accounts.csv')
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                enabled = str(row.get('enabled', 'TRUE')).upper() == 'TRUE'
                accounts.append({
                    'label': row.get('label', f'Account_{len(accounts)+1}'),
                    'private_key': row.get('private_key', ''),
                    'enabled': enabled
                })
    except FileNotFoundError:
        print(f"{Fore.RED}[✗] 找不到 accounts.csv{Style.RESET_ALL}")
    
    return accounts


async def login_single_account(manager, account, index, total):
    """登录单个账号的辅助函数"""
    label = account.get('label', f'Account_{index}')
    pk = account.get('private_key')
    
    result = {
        'label': label,
        'status': 'failed',
        'message': '',
        'credits': 'N/A',
        'bet_count': 0,
        'bet_limit': 100
    }
    
    try:
        sid = await manager.get_session_id(pk)
        if sid and sid != "FINISHED":
            addr = Account.from_key(pk).address
            status = manager.user_status_cache.get(addr, {})
            result['status'] = 'success'
            result['credits'] = status.get('credits', 'N/A')
            result['bet_count'] = status.get('dailyBetCount', 0)
            result['bet_limit'] = status.get('dailyBetLimit', 100)
            result['message'] = f"PTS:{result['credits']} 下单:{result['bet_count']}/{result['bet_limit']}"
        elif sid == "FINISHED":
            result['status'] = 'finished'
            result['message'] = '已完成今日任务'
        else:
            result['status'] = 'failed'
            result['message'] = '登录失败'
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
    
    return result


async def batch_login():
    """批量登录 - 每个账号使用独立端口的代理(顺序登录)"""
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}     批量登录 - DataImpulse 动态代理模式{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    # 加载账号
    accounts = load_accounts()
    enabled_accounts = [a for a in accounts if a.get('enabled', True) and a.get('private_key')]
    
    if not enabled_accounts:
        print(f"{Fore.RED}[✗] 没有可用的账号{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}[i] 发现 {len(enabled_accounts)} 个账号{Style.RESET_ALL}")
    
    # 加载配置检查代理状态
    config_dict = load_config()
    proxy_config = config_dict.get("proxy", {})
    
    if proxy_config.get("enabled", True) and proxy_config.get("username") and proxy_config.get("password"):
        start_port = proxy_config.get("start_port", 10000)
        host = proxy_config.get("host", "gw.dataimpulse.com")
        print(f"{Fore.GREEN}[✓] DataImpulse 代理已配置{Style.RESET_ALL}")
        print(f"    主机: {host}")
        print(f"    端口范围: {start_port} - {start_port + len(enabled_accounts) - 1}")
    else:
        print(f"{Fore.YELLOW}[!] 代理未配置，将直连{Style.RESET_ALL}")
    
    # 创建登录会话
    async with aiohttp.ClientSession() as session:
        config = SimpleConfig(enabled_accounts)
        manager = OrderManager(session, config)
        
        total_success = 0
        total_finished = 0
        total_failed = 0
        
        # 逐个登录
        for i, account in enumerate(enabled_accounts, 1):
            label = account.get('label', f'Account_{i}')
            pk = account.get('private_key')
            
            print(f"\n{Fore.BLUE}[{i}/{len(enabled_accounts)}] {label}{Style.RESET_ALL}")
            
            try:
                sid = await manager.get_session_id(pk)
                if sid and sid != "FINISHED":
                    addr = Account.from_key(pk).address
                    status = manager.user_status_cache.get(addr, {})
                    print(f"    {Fore.GREEN}✓ 登录成功{Style.RESET_ALL} PTS:{status.get('credits', 'N/A')} 下单:{status.get('dailyBetCount', 0)}/{status.get('dailyBetLimit', 100)}")
                    total_success += 1
                elif sid == "FINISHED":
                    print(f"    {Fore.YELLOW}ℹ 已完成今日任务{Style.RESET_ALL}")
                    total_finished += 1
                else:
                    print(f"    {Fore.RED}✗ 登录失败{Style.RESET_ALL}")
                    total_failed += 1
            except Exception as e:
                print(f"    {Fore.RED}✗ 异常: {e}{Style.RESET_ALL}")
                total_failed += 1
    
    # 汇总
    print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  批量登录完成{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"  成功登录: {Fore.GREEN}{total_success}{Style.RESET_ALL}")
    print(f"  已完成:   {Fore.YELLOW}{total_finished}{Style.RESET_ALL}")
    print(f"  失败:     {Fore.RED}{total_failed}{Style.RESET_ALL}")


async def concurrent_batch_login(concurrency=5):
    """并发批量登录 - 同时登录多个账号"""
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}     并发批量登录 - DataImpulse 动态代理模式{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    # 加载账号
    accounts = load_accounts()
    enabled_accounts = [a for a in accounts if a.get('enabled', True) and a.get('private_key')]
    
    if not enabled_accounts:
        print(f"{Fore.RED}[✗] 没有可用的账号{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}[i] 发现 {len(enabled_accounts)} 个账号{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[i] 并发数: {concurrency}{Style.RESET_ALL}")
    
    # 加载配置检查代理状态
    config_dict = load_config()
    proxy_config = config_dict.get("proxy", {})
    
    if proxy_config.get("enabled", True) and proxy_config.get("username") and proxy_config.get("password"):
        start_port = proxy_config.get("start_port", 10000)
        host = proxy_config.get("host", "gw.dataimpulse.com")
        print(f"{Fore.GREEN}[✓] DataImpulse 代理已配置{Style.RESET_ALL}")
        print(f"    主机: {host}")
        print(f"    端口范围: {start_port} - {start_port + len(enabled_accounts) - 1}")
    else:
        print(f"{Fore.YELLOW}[!] 代理未配置，将直连{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}开始并发登录...{Style.RESET_ALL}\n")
    
    # 创建登录会话
    async with aiohttp.ClientSession() as session:
        config = SimpleConfig(enabled_accounts)
        manager = OrderManager(session, config)
        
        total_success = 0
        total_finished = 0
        total_failed = 0
        
        # 分批并发登录
        for batch_start in range(0, len(enabled_accounts), concurrency):
            batch_end = min(batch_start + concurrency, len(enabled_accounts))
            batch = enabled_accounts[batch_start:batch_end]
            
            print(f"{Fore.CYAN}[批次 {batch_start//concurrency + 1}] 正在登录账号 {batch_start+1}-{batch_end}...{Style.RESET_ALL}")
            
            # 并发执行当前批次
            tasks = [
                login_single_account(manager, account, batch_start + i + 1, len(enabled_accounts))
                for i, account in enumerate(batch)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 显示结果
            for i, result in enumerate(results):
                account_index = batch_start + i + 1
                if isinstance(result, Exception):
                    print(f"  [{account_index}/{len(enabled_accounts)}] {batch[i].get('label', f'Account_{account_index}')} {Fore.RED}✗ 异常: {result}{Style.RESET_ALL}")
                    total_failed += 1
                else:
                    label = result['label']
                    if result['status'] == 'success':
                        print(f"  [{account_index}/{len(enabled_accounts)}] {label} {Fore.GREEN}✓ 登录成功{Style.RESET_ALL} {result['message']}")
                        total_success += 1
                    elif result['status'] == 'finished':
                        print(f"  [{account_index}/{len(enabled_accounts)}] {label} {Fore.YELLOW}ℹ {result['message']}{Style.RESET_ALL}")
                        total_finished += 1
                    else:
                        print(f"  [{account_index}/{len(enabled_accounts)}] {label} {Fore.RED}✗ {result['message']}{Style.RESET_ALL}")
                        total_failed += 1
            
            # 批次间短暂延迟
            if batch_end < len(enabled_accounts):
                await asyncio.sleep(0.5)
    
    # 汇总
    print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  并发批量登录完成{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"  成功登录: {Fore.GREEN}{total_success}{Style.RESET_ALL}")
    print(f"  已完成:   {Fore.YELLOW}{total_finished}{Style.RESET_ALL}")
    print(f"  失败:     {Fore.RED}{total_failed}{Style.RESET_ALL}")


def main():
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}         批量登录管理 (DataImpulse 代理){Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"\n请选择操作:\n")
    print(f"  {Fore.WHITE}1.{Style.RESET_ALL} 批量登录所有账号 (顺序登录)")
    print(f"  {Fore.WHITE}2.{Style.RESET_ALL} 并发批量登录 (同时登录多个账号)")
    print(f"  {Fore.WHITE}0.{Style.RESET_ALL} 退出")
    
    choice = input("\n请选择 (0-2): ").strip()
    
    if choice == '1':
        asyncio.run(batch_login())
    elif choice == '2':
        # 获取账号总数
        accounts = load_accounts()
        enabled_accounts = [a for a in accounts if a.get('enabled', True) and a.get('private_key')]
        total_accounts = len(enabled_accounts)
        
        if total_accounts == 0:
            print(f"{Fore.RED}[✗] 没有可用的账号{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}[i] 共有 {total_accounts} 个可用账号{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[提示] 建议并发数: 5-20 (根据网络和代理情况调整){Style.RESET_ALL}")
        
        # 获取并发数
        while True:
            try:
                concurrency_input = input(f"\n请输入并发登录数量 (1-{total_accounts}): ").strip()
                concurrency = int(concurrency_input)
                
                if 1 <= concurrency <= total_accounts:
                    break
                else:
                    print(f"{Fore.RED}[✗] 请输入 1 到 {total_accounts} 之间的数字{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}[✗] 请输入有效的数字{Style.RESET_ALL}")
        
        asyncio.run(concurrent_batch_login(concurrency))
    else:
        print("退出")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")

