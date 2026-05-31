@echo off
title Stopping Local LLM PDF OCR
echo Stopping Background OCR Services...

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'src.pdf_ocr.server:app' -or $_.CommandLine -match 'celery -A src.pdf_ocr.api.celery_app' } | Invoke-CimMethod -MethodName Terminate | Out-Null"

echo.
echo All OCR background services have been stopped.
timeout /t 3
