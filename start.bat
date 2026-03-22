@echo off
start "Backend" cmd /k ".venv\Scripts\python.exe -m src.api.app"
start "Frontend" cmd /k "cd frontend\web && npm start" 