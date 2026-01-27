
import asyncio
import aiohttp
from colorama import init, Fore, Style
from eth_account import Account
from aix_monitor import Config
from order_manager import OrderManager

# Initialize colorama
init()

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
                     print(f"  {Fore.YELLOW}[i] {addr[:10]} 已经在战队中或加入失败: {text}{Style.RESET_ALL}")
                else:
                     print(f"  {Fore.RED}[✗] {addr[:10]} 加入战队失败: {status} - {text}{Style.RESET_ALL}")
                return False
    except Exception as e:
        print(f"  {Fore.RED}[!] Error joining team: {e}{Style.RESET_ALL}")
        return False

async def main():
    print(f"{Fore.CYAN}=== 批量加入战队脚本 ==={Style.RESET_ALL}")
    
    INVITE_CODE = "C7KUWZ"
    print(f"目标邀请码: {INVITE_CODE}\n")

    async with aiohttp.ClientSession() as session:
        # Initialize OrderManager to reuse login logic
        om = OrderManager(session, Config)
        
        if not Config.ACCOUNTS:
            print("未找到账号配置。")
            return

        for i, acc in enumerate(Config.ACCOUNTS):
            pk = acc.get('private_key')
            if not pk:
                continue
                
            try:
                addr = Account.from_key(pk).address
                print(f"[{i+1}/{len(Config.ACCOUNTS)}] 正在处理 {addr[:10]}...")
                
                # Login to get session ID
                sid = await om.get_session_id(pk)
                
                if sid == "FINISHED":
                     # Even if finished daily bet limit, we might want to join team?
                     # Try to retrieve from cache or just proceed if we have it?
                     # In OrderManager, if it returns FINISHED, it likely cached the SID in om.session_cache before returning.
                     sid = om.session_cache.get(addr)

                if sid:
                    await join_team(session, addr, sid, INVITE_CODE)
                else:
                    print(f"  {Fore.RED}无法获取Session ID，跳过。{Style.RESET_ALL}")

            except Exception as e:
                print(f"  {Fore.RED}账号处理出错: {e}{Style.RESET_ALL}")
            
            # Small delay
            await asyncio.sleep(1)

    print("\n所有账号处理完毕。")

if __name__ == "__main__":
    asyncio.run(main())
