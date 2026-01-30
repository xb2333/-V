import sys
import os
from PyInstaller.__main__ import run

# 解决深度递归报错
sys.setrecursionlimit(10000)

def build_exe():
    print("🚀 开始强力打包...")
    opts = [
        'manga_gui.py',
        '--name=漫画翻译神器',
        '--onefile',
        '--noconsole',
        '--clean',
        '--collect-all=easyocr',
        '--collect-all=translators',
        '--collect-all=pyclipper',
        '--collect-all=numpy',
    ]
    try:
        run(opts)
        print("\n✅ 打包完成！")
    except Exception as e:
        print(f"\n❌ 打包出错: {e}")

if __name__ == '__main__':
    build_exe()