@echo off
chcp 65001 >nul
title AmoSight

echo.
echo  מפעיל AmoSight...
echo.

:: עצור תהליכים קודמים על הפורטים
echo  מנקה פורטים קודמים...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000"') do taskkill /PID %%a /F >nul 2>&1

:: הפעל שרת Python בחלון נפרד
echo  מפעיל שרת...
start "AmoSight - Server" cmd /k "cd /d %~dp0 && python -m src.api.app"

:: הפעל פרונטאנד בחלון נפרד
echo  מפעיל פרונטאנד...
start "AmoSight - Frontend" cmd /k "cd /d %~dp0\frontend\web && npm start"

:: המתן ופתח דפדפן
echo  ממתין שהכל יעלה...
timeout /t 10 /nobreak >nul
start http://localhost:3000

echo.
echo  AmoSight פועל!
echo    שרת:      http://localhost:8000
echo    אפליקציה: http://localhost:3000
echo.
echo  ניתן לסגור חלון זה. לעצירה — סגור את חלונות השרת והפרונטאנד.
echo.
pause
