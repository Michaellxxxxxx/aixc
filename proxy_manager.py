"""
DataImpulse 动态代理管理模块
为每个账号按索引分配独立 IP（端口递增）
"""


def build_proxy_url(proxy_config: dict, account_index: int) -> str | None:
    """
    根据账户索引构建动态代理 URL (DataImpulse 格式)
    
    Args:
        proxy_config: 代理配置字典，包含 username, password, host, start_port, countries
        account_index: 账户索引（从 0 开始）
        
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
    
    # 端口从起始端口开始，每个账户递增
    port = start_port + account_index
    
    # DataImpulse 格式: username__cr.国家代码:password@host:port
    # 支持多国家如: us,sg,gb,hk,jp
    return f"http://{username}__cr.{countries}:{password}@{host}:{port}"


def get_proxy_session_kwargs(proxy_config: dict, account_index: int) -> dict:
    """
    获取 aiohttp 请求的代理参数
    
    Args:
        proxy_config: 代理配置字典
        account_index: 账户索引
        
    Returns:
        可直接传给 aiohttp.ClientSession.request 的 proxy 参数字典
    """
    proxy_url = build_proxy_url(proxy_config, account_index)
    if proxy_url:
        return {"proxy": proxy_url}
    return {}
