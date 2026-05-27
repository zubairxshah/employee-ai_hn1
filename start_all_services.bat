@echo off
echo ============================================================
echo   AI Employee - Start All Services
echo ============================================================
echo.
echo This will start:
echo   1. All MCP Servers (Email, Approval, WhatsApp, etc.)
echo   2. Workflow Executor (processes approvals)
echo.
echo IMPORTANT: Only ONE instance of each service will run.
echo DO NOT run this script multiple times.
echo ============================================================
echo.

REM Check if already running
if exist "%TEMP%\ai_employee_services.pid" (
    echo [WARN] Services may already be running.
    echo        PID file: %TEMP%\ai_employee_services.pid
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b
)

REM Store PID
echo %DATE% %TIME% > "%TEMP%\ai_employee_services.pid"

echo [1/3] Starting MCP Servers...
start "MCP Servers" cmd /k "cd /d %~dp0 && python start_mcp_servers.py"

timeout /t 5 /nobreak >nul

echo [2/3] Starting Workflow Executor...
start "Workflow Executor" cmd /k "cd /d %~dp0 && python approval_workflow_executor.py"

echo.
echo ============================================================
echo [OK] Services started!
echo.
echo Windows opened:
echo   - MCP Servers (all servers on ports 8000-8004)
echo   - Workflow Executor (processing approvals)
echo.
echo To stop:
echo   - Close the terminal windows
echo   - Or press Ctrl+C in each window
echo ============================================================
echo.
echo Press any key to exit this window...
pause >nul
