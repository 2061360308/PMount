@echo off
:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 已经以管理员身份运行
) else (
    echo 请求管理员权限
    powershell -Command "Start-Process cmd -ArgumentList '/c %~dp0%~nx0' -Verb RunAs"
    exit /b
)

:: 进入虚拟环境
cd /d E:\AlistPanBaidu
call .venv\Scripts\activate

:: 运行 Python 脚本
python run.py