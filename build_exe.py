#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт сборки SL Bot в исполняемый .exe файл
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_requirements():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Зависимости установлены успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def build_exe():
    """Сборка exe файла"""
    print("🔨 Сборка исполняемого файла...")
    
    # Команда PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",                    # Один файл
        "--windowed",                   # Без консоли (можно убрать для отладки)
        "--clean",                      # Очистить кэш
        "--distpath", "dist",           # Папка с результатом
        "--workpath", "build",          # Временная папка
        "--specpath", ".",              # Папка для .spec файла
        "--name", "SL_Bot",             # Имя файла
        "--icon", "generated-icon.png", # Иконка (если есть)
        "sl_bot.py"                     # Основной файл
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✅ Сборка завершена успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сборки: {e}")
        return False
    except FileNotFoundError:
        print("❌ PyInstaller не найден. Установите его: pip install pyinstaller")
        return False

def create_release_package():
    """Создание пакета для распространения"""
    print("📦 Создание пакета для распространения...")
    
    release_dir = Path("SL_Bot_Release")
    
    # Удаляем старую папку если есть
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    # Создаем структуру папок
    release_dir.mkdir()
    
    # Копируем файлы
    files_to_copy = [
        ("dist/SL_Bot.exe", "SL_Bot.exe"),
        ("config_example.env", ".env"),
        ("README-PYTHON.md", "README.md"),
    ]
    
    for src, dst in files_to_copy:
        src_path = Path(src)
        dst_path = release_dir / dst
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"✅ Скопирован: {src} -> {dst}")
        else:
            print(f"⚠️  Файл не найден: {src}")
    
    print(f"📦 Пакет готов в папке: {release_dir.absolute()}")

def main():
    """Главная функция"""
    print("=" * 60)
    print("    SL Bot - Сборка в исполняемый файл (.exe)")
    print("=" * 60)
    
    # Проверяем наличие основного файла
    if not Path("sl_bot.py").exists():
        print("❌ Файл sl_bot.py не найден!")
        return False
    
    # Установка зависимостей
    if not install_requirements():
        return False
    
    # Сборка exe
    if not build_exe():
        return False
    
    # Создание пакета
    create_release_package()
    
    print("\n🎉 Сборка завершена!")
    print("\n📁 Готовые файлы:")
    print("   - SL_Bot_Release/SL_Bot.exe - исполняемый файл")
    print("   - SL_Bot_Release/.env - файл конфигурации (настройте его)")
    print("   - SL_Bot_Release/README.md - инструкция")
    
    print("\n📋 Следующие шаги:")
    print("   1. Настройте файл .env с вашими токенами")
    print("   2. Запустите SL_Bot.exe двойным кликом")
    print("   3. Бот будет работать в фоне")
    
    return True

if __name__ == "__main__":
    success = main()
    input(f"\n{'✅ Успех!' if success else '❌ Ошибка!'} Нажмите Enter для выхода...") 