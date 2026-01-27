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

def main():
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
