#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт сборки SL Bot в .exe файл
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("🔨 Сборка SL Bot в .exe файл...")
    
    # Проверяем наличие основного файла
    if not Path("sl_bot.py").exists():
        print("❌ Файл sl_bot.py не найден!")
        return
    
    # Простая команда PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--clean",
        "--name", "SL_Bot",
        "sl_bot.py"
    ]
    
    try:
        print("Запуск PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Сборка завершена успешно!")
        print("📁 Готовый файл: dist/SL_Bot.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сборки:")
        print(f"Код возврата: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        
    except FileNotFoundError:
        print("❌ PyInstaller не найден!")
        print("Установите его командой: pip install pyinstaller")

if __name__ == "__main__":
    main()
    input("Нажмите Enter для выхода...") 