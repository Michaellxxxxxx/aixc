import os
import sys
import subprocess
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("=" * 50)
    print("       AIX 自动化脚本启动菜单")
    print("=" * 50)

def check_and_init_files():
    """检查并初始化必要的配置文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 检查 config.json
    config_path = os.path.join(base_dir, 'config.json')
    config_example_path = os.path.join(base_dir, 'config.example.json')
    if not os.path.exists(config_path) and os.path.exists(config_example_path):
        try:
            import shutil
            shutil.copy2(config_example_path, config_path)
            print(f"[✓] 已自动创建默认配置文件: config.json")
            print(f"    请记得编辑它以配置您的参数！")
        except Exception as e:
            print(f"[!] 创建 config.json 失败: {e}")

    # 2. 检查 accounts.csv
    accounts_path = os.path.join(base_dir, 'accounts.csv')
    accounts_example_path = os.path.join(base_dir, 'accounts.example.csv')
    if not os.path.exists(accounts_path) and os.path.exists(accounts_example_path):
        try:
            import shutil
            shutil.copy2(accounts_example_path, accounts_path)
            print(f"[✓] 已自动创建默认账号文件: accounts.csv")
            print(f"    请务必编辑它并填入您的私钥！")
        except Exception as e:
            print(f"[!] 创建 accounts.csv 失败: {e}")
    
    # 简单的视觉分隔
    if not os.path.exists(config_path) or not os.path.exists(accounts_path):
        print("-" * 50)
        time.sleep(2)  # 给用户一点时间看提示

def main():
    check_and_init_files()
    while True:
        clear_screen()
        print_header()
        print("\n请选择要启动的功能模块：\n")
        print("1. [主程序] AIX 监控 (aix_monitor.py) ★网页开盘价+API当前价")
        print("2. [管理] 订单管理 (order_manager.py)")
        print("3. [任务] 每日任务检查 (check_tasks.py)")
        print("4. [战队] 批量加入战队 (join_teams.py)")
        print("5. [登录] 批量登录 (batch_login.py)")
        print("0. 退出")
        print("-" * 50)
        
        choice = input("\n请输入数字选择 (0-5): ").strip()
        
        if choice == '0':
            print("\n感谢使用，再见！")
            time.sleep(1)
            sys.exit(0)
            
        script_map = {
            '1': 'aix_monitor.py',
            '2': 'order_manager.py',
            '3': 'check_tasks.py',
            '4': 'join_teams.py',
            '5': 'batch_login.py'
        }
        
        if choice in script_map:
            script_name = script_map[choice]
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
            
            if os.path.exists(script_path):
                print(f"\n正在启动 {script_name} ...")
                print("-" * 50)
                try:
                    # Use the same python interpreter as the current script
                    subprocess.run([sys.executable, script_path], check=False)
                except KeyboardInterrupt:
                    print("\n程序已停止")
                
                input("\n按回车键返回主菜单...")
            else:
                print(f"\n错误: 找不到文件 {script_name}")
                time.sleep(2)
        else:
            print("\n无效的选择，请重试")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
