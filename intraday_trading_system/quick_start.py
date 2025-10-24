"""
快速启动脚本
检查环境配置，引导用户快速开始使用日内交易分析系统
"""

import os
import sys
import json
from pathlib import Path


def check_dependencies():
    """检查依赖库是否已安装"""
    print("📦 检查依赖库...")
    
    required_packages = {
        'akshare': 'akshare',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'openai': 'openai'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - 未安装")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖库: {', '.join(missing_packages)}")
        print("\n💡 请运行以下命令安装:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖库已安装\n")
    return True


def check_config_files():
    """检查配置文件"""
    print("📝 检查配置文件...")
    
    config_file = Path('intraday_trading_config.json')
    keys_file_local = Path('keys.json')  # 当前目录
    keys_file_parent = Path('../keys.json')  # 父目录
    example_keys_file = Path('intraday_trading_example_keys.json')
    
    all_ok = True
    
    # 检查主配置文件
    if config_file.exists():
        print(f"  ✅ {config_file}")
    else:
        print(f"  ❌ {config_file} - 未找到")
        all_ok = False
    
    # 检查API密钥文件（优先当前目录，其次父目录）
    keys_file = None
    if keys_file_local.exists():
        keys_file = keys_file_local
    elif keys_file_parent.exists():
        keys_file = keys_file_parent
    
    if keys_file:
        print(f"  ✅ {keys_file}")
        
        # 验证API密钥是否已配置
        try:
            with open(keys_file, 'r', encoding='utf-8') as f:
                keys = json.load(f)
            
            api_key = keys.get('api_key', '')
            if not api_key or api_key.startswith('sk-xxxx'):
                print(f"  ⚠️ API密钥尚未配置，请编辑 {keys_file} 填入真实密钥")
                all_ok = False
        except Exception as e:
            print(f"  ⚠️ 读取 {keys_file} 失败: {e}")
            all_ok = False
    else:
        print(f"  ❌ keys.json - 未找到（当前目录或父目录）")
        
        if example_keys_file.exists():
            print(f"\n  💡 请复制 {example_keys_file} 为 keys.json，并填入真实API密钥")
        else:
            print(f"\n  💡 请创建 keys.json 文件，参考以下格式:")
            print('  {')
            print('    "api_key": "您的API密钥",')
            print('    "email_sender": "your_email@example.com",')
            print('    "email_password": "邮箱密码或授权码",')
            print('    "email_receivers": ["receiver@example.com"]')
            print('  }')
        
        all_ok = False
    
    if all_ok:
        print("✅ 所有配置文件就绪\n")
    else:
        print("\n⚠️ 配置文件检查未通过\n")
    
    return all_ok


def check_modules():
    """检查自定义模块"""
    print("🔧 检查系统模块...")
    
    required_modules = [
        'intraday_data_fetcher.py',
        'intraday_indicators.py',
        'intraday_prompt_builder.py',
        'intraday_trading_main.py'
    ]
    
    all_ok = True
    
    for module in required_modules:
        module_path = Path(module)
        if module_path.exists():
            print(f"  ✅ {module}")
        else:
            print(f"  ❌ {module} - 未找到")
            all_ok = False
    
    if all_ok:
        print("✅ 所有系统模块就绪\n")
    else:
        print("\n⚠️ 系统模块检查未通过\n")
    
    return all_ok


def show_usage():
    """显示使用说明"""
    print("="*60)
    print("📖 使用说明")
    print("="*60)
    print("\n1️⃣ 测试数据获取（不调用大模型）:")
    print("   python test_intraday_data.py 600000")
    print("\n2️⃣ 完整分析单只股票:")
    print("   python intraday_trading_main.py 600000")
    print("\n3️⃣ 批量分析多只股票:")
    print("   python intraday_trading_main.py 600000 000001 300750")
    print("\n4️⃣ 查看详细文档:")
    print("   打开 INTRADAY_TRADING_README.md")
    print("\n" + "="*60 + "\n")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 A股日内交易分析系统 - 环境检查")
    print("="*60 + "\n")
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    # 检查配置文件
    config_ok = check_config_files()
    
    # 检查模块
    modules_ok = check_modules()
    
    # 总结
    print("="*60)
    print("📊 环境检查总结")
    print("="*60)
    
    if deps_ok and config_ok and modules_ok:
        print("✅ 所有检查通过，系统就绪！")
        print("\n")
        show_usage()
        
        # 询问是否立即测试
        response = input("是否立即进行数据获取测试？(y/n): ")
        if response.lower() == 'y':
            stock_code = input("请输入股票代码（如600000）: ")
            if stock_code:
                print("\n" + "="*60)
                os.system(f"python test_intraday_data.py {stock_code}")
    else:
        print("❌ 环境检查未通过，请根据上述提示进行配置")
        print("\n💡 配置步骤:")
        
        if not deps_ok:
            print("  1. 安装缺失的依赖库")
        
        if not config_ok:
            print("  2. 配置API密钥文件 (keys.json)")
        
        if not modules_ok:
            print("  3. 确保所有系统模块文件存在")
        
        print("\n详细配置说明请查看 INTRADAY_TRADING_README.md")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()

