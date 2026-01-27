
import asyncio
import aiohttp
from colorama import init
from eth_account import Account
from aix_monitor import Config
from order_manager import OrderManager

# Initialize colorama
init()

async def main():
    print("正在检查所有账号的每日任务状态...")
    async with aiohttp.ClientSession() as session:
        # Initialize OrderManager
        om = OrderManager(session, Config)
        
        # Iterate over all accounts in Config
        if not Config.ACCOUNTS:
            print("未找到账号配置。")
            return

        for i, acc in enumerate(Config.ACCOUNTS):
            pk = acc.get('private_key')
            if not pk:
                continue
                
            try:
                addr = Account.from_key(pk).address
                print(f"[{i+1}/{len(Config.ACCOUNTS)}] 正在检查 {addr[:10]}...")
                
                # Login to get session ID
                # Note: get_session_id handles caching and limit checks internally
                # asking it might return "FINISHED" if limit reached, but we want SID.
                # If "FINISHED", we still want to try claiming tasks if not done.
                # However, get_session_id in OrderManager returns "FINISHED" string if limit reached.
                # We need the actual SID to claim tasks.
                
                # To bypass the "FINISHED" check in get_session_id, we might need to access session_cache directly
                # or rely on logic that if it's FINISHED, it might have already triggered tasks?
                
                # Actually, let's look at get_session_id implementation in order_manager.py
                # It returns "FINISHED" if limit reached.
                # If so, we can't easily get SID unless we force it or if it cached it?
                # The latest edit to order_manager parses Login response, caches SID, THEN checks limit.
                # So if we call it, it might return FINISHED but `om.session_cache` might have it?
                
                sid = await om.get_session_id(pk)
                
                if sid == "FINISHED":
                    # Try to retrieve from cache
                    sid = om.session_cache.get(addr)
                
                if sid:
                    await om.claim_daily_tasks(addr, sid)
                else:
                    print(f"  无法获取会话ID，跳过。")
                    
            except Exception as e:
                print(f"  检查账号出错: {e}")
            
            # Rate limit slightly
            await asyncio.sleep(0.5)

    print("\n所有账号检查完毕。")

if __name__ == "__main__":
    asyncio.run(main())
