@echo off
:: ============================================================
:: Trading Agent — Windows Task Scheduler Setup
:: Runs main.py every weekday at 7:00 AM Central Time
:: Run this script ONCE as Administrator
:: ============================================================

set TASK_NAME=TradingAgentDailyBrief
set SCRIPT_DIR=%~dp0
set PYTHON=python

:: Remove existing task if present
schtasks /delete /tn "%TASK_NAME%" /f 2>nul

:: Create task: weekdays (Mon-Fri) at 07:00 local time
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT_DIR%main.py\"" ^
  /sc WEEKLY ^
  /d MON,TUE,WED,THU,FRI ^
  /st 07:00 ^
  /rl HIGHEST ^
  /f

echo.
echo Task "%TASK_NAME%" created successfully.
echo Runs every weekday at 07:00 AM (your local Windows time zone).
echo Make sure Windows is set to Central Time (America/Chicago).
echo.
pause
