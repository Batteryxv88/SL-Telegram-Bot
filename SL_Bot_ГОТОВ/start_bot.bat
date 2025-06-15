@echo off
echo ======================================
echo  ЗАПУСК SL TELEGRAM BOT
echo  Используется исправленная версия
echo ======================================
echo.
echo Проверяем что другие боты остановлены...
timeout /t 5 /nobreak >nul
echo.
echo Запуск бота...
SL_Bot_NoDeps.exe
pause 