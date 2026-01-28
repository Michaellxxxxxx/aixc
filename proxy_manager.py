"""
DataImpulse 动态代理管理模块
为每个账号按索引分配独立 IP（端口递增）
支持故障检测和自动切换
"""
import time
from typing import Dict, Set, Optional
from colorama import Fore, Style


class ProxyPortPool:
    """代理端口池管理器 - 支持故障检测和自动切换"""
    
    def __init__(self, proxy_config: dict, total_accounts: int):
        """
        初始化代理端口池
        
        Args:
            proxy_config: 代理配置字典
            total_accounts: 总账户数量
        """
        self.proxy_config = proxy_config
        self.total_accounts = total_accounts
        self.start_port = proxy_config.get('start_port', 10000)
        
        # 账户地址 -> 当前使用的端口偏移量
        self._account_port_map: Dict[str, int] = {}
        
        # 故障端口集合 (端口偏移量)
        self._failed_ports: Set[int] = set()
        
        # 端口故障时间记录 (用于自动恢复)
        self._port_failure_time: Dict[int, float] = {}
        
        # 故障恢复时间 (秒) - 端口故障后多久可以重新尝试
        self.recovery_time = 300  # 5分钟
        
        # 最大端口偏移量 (基于账户数量 * 2,留出备用空间)
        self.max_port_offset = total_accounts * 2
        
    def get_port_for_account(self, account_addr: str, account_index: int) -> int:
        """
        获取账户对应的端口偏移量
        
        Args:
            account_addr: 账户地址
            account_index: 账户索引
            
        Returns:
            端口偏移量
        """
        # 如果账户已有分配的端口,返回该端口
        if account_addr in self._account_port_map:
            port_offset = self._account_port_map[account_addr]
            # 检查该端口是否已恢复
            if port_offset in self._failed_ports:
                if self._can_recover_port(port_offset):
                    # 端口已恢复,移除故障标记
                    self._failed_ports.discard(port_offset)
                    del self._port_failure_time[port_offset]
                    print(f"{Fore.GREEN}[✓] 端口 {self.start_port + port_offset} 已恢复{Style.RESET_ALL}")
                    return port_offset
                else:
                    # 端口仍在故障期,分配新端口
                    return self._allocate_new_port(account_addr, account_index)
            return port_offset
        
        # 新账户,分配初始端口
        self._account_port_map[account_addr] = account_index
        return account_index
    
    def _can_recover_port(self, port_offset: int) -> bool:
        """检查端口是否可以恢复"""
        if port_offset not in self._port_failure_time:
            return True
        
        elapsed = time.time() - self._port_failure_time[port_offset]
        return elapsed >= self.recovery_time
    
    def _allocate_new_port(self, account_addr: str, fallback_index: int) -> int:
        """
        为账户分配新的可用端口
        
        Args:
            account_addr: 账户地址
            fallback_index: 备用索引
            
        Returns:
            新的端口偏移量
        """
        # 尝试找到一个未被使用且未故障的端口
        used_ports = set(self._account_port_map.values())
        
        for offset in range(self.max_port_offset):
            if offset not in used_ports and offset not in self._failed_ports:
                self._account_port_map[account_addr] = offset
                return offset
        
        # 如果所有端口都被占用,尝试使用已恢复的故障端口
        for offset in range(self.max_port_offset):
            if offset in self._failed_ports and self._can_recover_port(offset):
                self._failed_ports.discard(offset)
                del self._port_failure_time[offset]
                self._account_port_map[account_addr] = offset
                return offset
        
        # 实在没办法,返回备用索引
        print(f"{Fore.YELLOW}[!] 警告: 所有端口都不可用,使用备用端口{Style.RESET_ALL}")
        return fallback_index
    
    def mark_port_failed(self, account_addr: str, account_index: int):
        """
        标记账户当前使用的端口为故障状态,并分配新端口
        
        Args:
            account_addr: 账户地址
            account_index: 账户索引
        """
        current_port = self._account_port_map.get(account_addr, account_index)
        
        if current_port not in self._failed_ports:
            self._failed_ports.add(current_port)
            self._port_failure_time[current_port] = time.time()
            print(f"{Fore.YELLOW}[!] 端口 {self.start_port + current_port} 已标记为故障{Style.RESET_ALL}")
        
        # 分配新端口
        new_port = self._allocate_new_port(account_addr, account_index)
        print(f"{Fore.CYAN}[→] {account_addr[:10]}... 切换到新端口: {self.start_port + new_port}{Style.RESET_ALL}")
        
        return new_port
    
    def get_stats(self) -> dict:
        """获取端口池统计信息"""
        return {
            "total_ports": self.max_port_offset,
            "failed_ports": len(self._failed_ports),
            "active_accounts": len(self._account_port_map),
            "failed_port_list": [self.start_port + p for p in self._failed_ports]
        }


# 全局端口池实例 (由 OrderManager 初始化)
_global_port_pool: Optional[ProxyPortPool] = None


def initialize_port_pool(proxy_config: dict, total_accounts: int):
    """初始化全局端口池"""
    global _global_port_pool
    _global_port_pool = ProxyPortPool(proxy_config, total_accounts)
    return _global_port_pool


def get_port_pool() -> Optional[ProxyPortPool]:
    """获取全局端口池实例"""
    return _global_port_pool


def build_proxy_url(proxy_config: dict, account_index: int, account_addr: str = None) -> str | None:
    """
    根据账户索引构建动态代理 URL (DataImpulse 格式)
    
    Args:
        proxy_config: 代理配置字典，包含 username, password, host, start_port, countries
        account_index: 账户索引（从 0 开始）
        account_addr: 账户地址 (可选,用于端口池管理)
        
    Returns:
        代理 URL 字符串，配置不完整时返回 None
    """
    if not proxy_config:
        return None
    
    username = proxy_config.get('username', '')
    password = proxy_config.get('password', '')
    host = proxy_config.get('host', 'gw.dataimpulse.com')
    start_port = proxy_config.get('start_port', 10000)
    # 国家代码，支持多国轮换
    countries = proxy_config.get('countries', 'us')
    
    if not username or not password:
        return None
    
    # 如果启用了端口池且提供了账户地址,使用端口池分配
    port_offset = account_index
    if _global_port_pool and account_addr:
        port_offset = _global_port_pool.get_port_for_account(account_addr, account_index)
    
    # 端口从起始端口开始，每个账户递增
    port = start_port + port_offset
    
    # DataImpulse 格式: username__cr.国家代码:password@host:port
    # 支持多国家如: us,sg,gb,hk,jp
    return f"http://{username}__cr.{countries}:{password}@{host}:{port}"


def mark_proxy_failed(account_addr: str, account_index: int):
    """
    标记账户的代理端口为故障状态
    
    Args:
        account_addr: 账户地址
        account_index: 账户索引
    """
    if _global_port_pool:
        _global_port_pool.mark_port_failed(account_addr, account_index)


def get_proxy_session_kwargs(proxy_config: dict, account_index: int, account_addr: str = None) -> dict:
    """
    获取 aiohttp 请求的代理参数
    
    Args:
        proxy_config: 代理配置字典
        account_index: 账户索引
        account_addr: 账户地址 (可选)
        
    Returns:
        可直接传给 aiohttp.ClientSession.request 的 proxy 参数字典
    """
    proxy_url = build_proxy_url(proxy_config, account_index, account_addr)
    if proxy_url:
        return {"proxy": proxy_url}
    return {}
