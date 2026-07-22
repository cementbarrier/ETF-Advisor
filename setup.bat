@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   ETF Trader - 环境初始化
echo ========================================
echo.

:: ── Check Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python。请先安装 Python 3.9+ 并添加到 PATH。
    echo        下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检测 Python ...
python --version
echo.

:: ── Create venv ──
echo [2/3] 创建虚拟环境 ...
if not exist ".venv" (
    python -m venv .venv
    echo 虚拟环境已创建
) else (
    echo 虚拟环境已存在，跳过创建
)
echo.

:: ── Install dependencies ──
echo [3/3] 安装依赖 ...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo.

:: ── Done ──
echo ========================================
echo   初始化完成！
echo.
echo   运行方式：
echo     .venv\Scripts\python.exe gui.py
echo.
echo   打包 EXE：
echo     .venv\Scripts\python.exe -m PyInstaller gui.spec --clean
echo ========================================
pause
