@echo off
:: ============================================================
:: Trading Agent — Bot Listener Startup Setup
:: Starts bot_listener.py silently on Windows login
:: Run this script ONCE as Administrator
:: ============================================================

set TASK_NAME=TradingAgentBotListener
set SCRIPT_DIR=%~dp0
set PYTHONW=pythonw

schtasks /delete /tn "%TASK_NAME%" /f 2>nul

:: Start bot listener at login, run silently (pythonw = no console window)
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHONW%\" \"%SCRIPT_DIR%bot_listener.py\"" ^
  /sc ONLOGON ^
  /rl HIGHEST ^
  /f

echo.
echo Bot listener task "%TASK_NAME%" created.
echo bot_listener.py will start automatically at Windows login.
echo Send /brief or /status to your Telegram bot to test.
echo.
pause
