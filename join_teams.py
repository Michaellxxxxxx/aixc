
import asyncio
import aiohttp
from colorama import init, Fore, Style
from eth_account import Account
from aix_monitor import Config
from order_manager import OrderManager

# Initialize colorama
init()


async def check_team_status(session: aiohttp.ClientSession, addr: str, sid: str):
    """
    检查账号是否已加入战队
    API: GET https://hub.aixcrypto.ai/api/team/my-team?sessionId=...
    
    Returns:
        tuple: (is_in_team: bool, team_info: dict or None)
    """
    url = f"https://hub.aixcrypto.ai/api/team/my-team?sessionId={sid}"
    
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "referrer": "https://hub.aixcrypto.ai/"
    }
    
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                # 如果返回的数据包含战队信息，说明已在战队中
                if data and isinstance(data, dict) and data.get('name'):
                    return True, data
            return False, None
    except Exception as e:
        print(f"  {Fore.YELLOW}[!] {addr[:10]} 检查战队状态失败: {e}{Style.RESET_ALL}")
        return False, None


async def join_team(session: aiohttp.ClientSession, addr: str, sid: str, invite_code: str):
    """
    Call the join team API.
    API: POST https://hub.aixcrypto.ai/api/team/join
    Body: {"inviteCode": "...", "sessionId": "..."}
    """
    url = "https://hub.aixcrypto.ai/api/team/join"
    
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "referrer": "https://hub.aixcrypto.ai/",
        "mode": "cors"
    }
    
    payload = {
        "inviteCode": invite_code,
        "sessionId": sid
    }
    
    try:
        async with session.post(url, json=payload, headers=headers) as resp:
            status = resp.status
            text = await resp.text()
            
            if status in [200, 201]:
                print(f"  {Fore.GREEN}[✓] {addr[:10]} 加入战队成功!{Style.RESET_ALL}")
                return True
            else:
                # If already in a team or other error
                if "already" in text.lower() or "member" in text.lower():
                     print(f"  {Fore.YELLOW}[i] {addr[:10]} 已经在战队中{Style.RESET_ALL}")
                else:
                     print(f"  {Fore.RED}[✗] {addr[:10]} 加入战队失败: {status} - {text}{Style.RESET_ALL}")
                return False
    except Exception as e:
        print(f"  {Fore.RED}[!] {addr[:10]} 加入战队出错: {e}{Style.RESET_ALL}")
        return False


async def process_single_account(session: aiohttp.ClientSession, om: OrderManager, 
                                 account: dict, index: int, total: int, 
                                 invite_code: str, stats: dict):
    """
    处理单个账号的完整流程：登录 -> 检查状态 -> 加入战队
    
    Args:
        session: aiohttp session
        om: OrderManager 实例
        account: 账号配置
        index: 账号索引
        total: 总账号数
        invite_code: 邀请码
        stats: 统计信息字典
    """
    pk = account.get('private_key')
    if not pk:
        stats['skipped'] += 1
        return
        
    try:
        addr = Account.from_key(pk).address
        print(f"[{index+1}/{total}] 正在处理 {addr[:10]}...")
        
        # 登录获取 Session ID
        sid = await om.get_session_id(pk)
        
        if sid == "FINISHED":
            sid = om.session_cache.get(addr)

        if not sid:
            print(f"  {Fore.RED}[✗] {addr[:10]} 无法获取Session ID，跳过{Style.RESET_ALL}")
            stats['failed'] += 1
            return
        
        # 检查是否已在战队中
        is_in_team, team_info = await check_team_status(session, addr, sid)
        
        if is_in_team:
            team_name = team_info.get('name', '未知') if team_info else '未知'
            print(f"  {Fore.CYAN}[→] {addr[:10]} 已在战队中: {team_name}{Style.RESET_ALL}")
            stats['already_joined'] += 1
            return
        
        # 加入战队
        success = await join_team(session, addr, sid, invite_code)
        
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1

    except Exception as e:
        print(f"  {Fore.RED}[!] {addr[:10]} 处理出错: {e}{Style.RESET_ALL}")
        stats['failed'] += 1


async def main():
    print(f"{Fore.CYAN}=== 批量加入战队脚本 ==={Style.RESET_ALL}")
    
    INVITE_CODE = "C7KUWZ"
    print(f"目标邀请码: {INVITE_CODE}\n")

    # 获取用户输入的并发数量
    try:
        concurrency_input = input(f"{Fore.YELLOW}请输入并发数量 (默认 10): {Style.RESET_ALL}").strip()
        concurrency = int(concurrency_input) if concurrency_input else 10
        
        if concurrency < 1:
            print(f"{Fore.RED}并发数量必须大于 0，使用默认值 10{Style.RESET_ALL}")
            concurrency = 10
        elif concurrency > 100:
            print(f"{Fore.YELLOW}并发数量过大，建议不超过 100，当前设置: {concurrency}{Style.RESET_ALL}")
    except ValueError:
        print(f"{Fore.RED}输入无效，使用默认并发数量 10{Style.RESET_ALL}")
        concurrency = 10
    
    print(f"{Fore.GREEN}并发数量: {concurrency}{Style.RESET_ALL}\n")

    async with aiohttp.ClientSession() as session:
        # Initialize OrderManager to reuse login logic
        om = OrderManager(session, Config)
        
        if not Config.ACCOUNTS:
            print("未找到账号配置。")
            return
        
        # 统计信息
        stats = {
            'success': 0,           # 成功加入
            'already_joined': 0,    # 已在战队中
            'failed': 0,            # 失败
            'skipped': 0            # 跳过（无私钥）
        }
        
        total_accounts = len(Config.ACCOUNTS)
        print(f"共 {total_accounts} 个账号，开始批量处理...\n")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_with_semaphore(account, index):
            async with semaphore:
                await process_single_account(
                    session, om, account, index, total_accounts, 
                    INVITE_CODE, stats
                )
        
        # 创建所有任务
        tasks = [
            process_with_semaphore(account, i) 
            for i, account in enumerate(Config.ACCOUNTS)
        ]
        
        # 并发执行所有任务
        await asyncio.gather(*tasks)
        
        # 显示统计信息
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}=== 处理完成 ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ 成功加入: {stats['success']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}→ 已在战队: {stats['already_joined']}{Style.RESET_ALL}")
        print(f"{Fore.RED}✗ 失败: {stats['failed']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}- 跳过: {stats['skipped']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}总计: {total_accounts}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    asyncio.run(main())
