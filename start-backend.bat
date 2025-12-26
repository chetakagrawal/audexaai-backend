@echo off
echo Starting AudexaAI Backend...
cd /d C:\Projects\audexaai-backend
powershell -ExecutionPolicy Bypass -Command "cd 'C:\Projects\audexaai-backend'; poetry run uvicorn main:app --reload"
pause
