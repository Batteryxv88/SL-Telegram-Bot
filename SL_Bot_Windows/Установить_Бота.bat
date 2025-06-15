@echo off
title Установка SL Telegram Bot
echo ═══════════════════════════════════════════════════════════════
echo                    УСТАНОВКА SL TELEGRAM BOT
echo ═══════════════════════════════════════════════════════════════
echo.
echo 🛠️  Мастер установки бота для мониторинга склада
echo.

REM Переход в папку с файлами
cd /d "%~dp0"

echo 📋 Проверка файлов...
if exist "SL_Bot.exe" (
    echo ✅ SL_Bot.exe найден
) else (
    echo ❌ SL_Bot.exe не найден!
    pause
    exit /b 1
)

if exist ".env" (
    echo ✅ .env найден
) else (
    echo ❌ .env не найден!
    pause
    exit /b 1
)

echo.
echo 📝 СЛЕДУЮЩИЕ ШАГИ:
echo.
echo 1️⃣  Откройте файл ".env" в блокноте
echo 2️⃣  Замените "your_telegram_bot_token_here" на ваш токен от @BotFather
echo 3️⃣  Замените Firebase JSON на ваш ключ из Firebase Console
echo 4️⃣  Сохраните файл .env
echo 5️⃣  Запустите "Запустить_Бота.bat"
echo.
echo 🔑 ПОЛУЧЕНИЕ ТОКЕНОВ:
echo.
echo 📱 Telegram Bot:
echo    - Найдите @BotFather в Telegram
echo    - Отправьте /newbot
echo    - Следуйте инструкциям
echo.
echo 🔥 Firebase:
echo    - Откройте Firebase Console
echo    - Настройки проекта → Service accounts
echo    - Generate new private key
echo    - Скопируйте весь JSON в одну строку
echo.
echo 📖 Подробная инструкция в файле "УСТАНОВКА.txt"
echo.

choice /C YN /M "Открыть файл .env для редактирования?"
if %ERRORLEVEL%==1 (
    echo 📝 Открываю .env для редактирования...
    notepad .env
)

echo.
echo ✅ Установка завершена!
echo 🚀 Настройте .env и запустите "Запустить_Бота.bat"
echo.
pause 