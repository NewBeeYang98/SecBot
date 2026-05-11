@echo off
chcp 65001 >nul 2>&1
title SecBot - 安全工具箱

:: ============================================================
::  SecBot 一键启动器 v2.0
::  内网优化版：静默失败 → 明确提示
:: ============================================================

setlocal

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || goto :error

:: ── 阶段1：检查Python ───────────────────────────────────
echo.
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 goto :no_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if %errorlevel% neq 0 goto :old_python
echo   [OK] Python OK
goto :check_deps

:no_python
echo.
echo [错误] 未找到Python！
echo.
echo 请先下载安装 Python 3.8+：
echo   https://www.python.org/downloads/
echo.
echo 安装时务必勾选：Add Python to PATH
echo.
pause
exit /b 1

:old_python
echo.
echo [错误] Python版本过低，需要3.8以上
pause
exit /b 1

:: ── 阶段2：安装依赖 ─────────────────────────────────────
:check_deps
echo.
echo [2/5] 检查依赖包（内网自动跳过）...

set "NEED_PIP=0"

python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo   - Streamlit: 缺失
    set "NEED_PIP=1"
)

python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo   - Requests: 缺失
    set "NEED_PIP=1"
)

python -c "import bs4" >nul 2>&1
if %errorlevel% neq 0 (
    echo   - BeautifulSoup4: 缺失
    set "NEED_PIP=1"
)

if "%NEED_PIP%"=="0" (
    echo   [OK] 依赖完整
    goto :check_webapp
)

echo.
echo [3/5] 尝试自动安装依赖...
echo.

:: 先测试网络
python -c "import urllib.request; urllib.request.urlopen('https://pypi.org', timeout=5)" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [注意] 无法连接PyPI，内网环境
    echo   尝试从本地离线包安装...
    echo.

    :: 尝试离线安装
    if exist "offline" (
        for %%f in (streamlit requests bs4 lxml colorama) do (
            for %%x in (whl tar.gz) do (
                if exist "offline\*.%%x" (
                    echo   安装 %%f...
                    python -m pip install "offline\*.%%x" --quiet --no-index --find-links=offline >nul 2>&1
                )
            )
        )
    )

    :: 检查是否安装成功
    python -c "import streamlit" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [错误] 离线安装失败，请手动安装依赖：
        echo.
        python -m pip install streamlit requests beautifulsoup4 lxml colorama
        echo.
        pause
        exit /b 1
    )
) else (
    :: 有网，直接pip install
    echo   正在安装（需要网络）...
    python -m pip install streamlit requests beautifulsoup4 lxml colorama --quiet --user
    if %errorlevel% neq 0 (
        echo   pip安装失败，尝试--break-system-packages...
        python -m pip install streamlit requests beautifulsoup4 lxml colorama --break-system-packages --quiet
    )
)

echo   [OK] 依赖安装完成

:: ── 阶段3：检查Web UI文件 ────────────────────────────────
:check_webapp
echo.
echo [4/5] 检查Web界面文件...
if not exist "web_app.py" (
    echo.
    echo [错误] web_app.py 未找到！
    echo 请确保 SecBot 目录完整。
    echo.
    pause
    exit /b 1
)
echo   [OK] web_app.py 就绪

:: ── 阶段4：网络检测 ────────────────────────────────────
echo.
echo [5/5] 检测网络环境...
python -c "import urllib.request; urllib.request.urlopen('https://www.baidu.com', timeout=5)" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] 互联网模式
) else (
    echo   [注意] 内网/隔离模式（AI功能需本地模型）
)

:: ── 阶段5：启动 ─────────────────────────────────────────
echo.
echo ============================================================
echo.
echo   启动 SecBot Web UI ...
echo   浏览器将自动打开：http://localhost:8501
echo   首次启动需要10-30秒，请耐心等待...
echo.
echo ============================================================
echo.

:: 等待Streamlit启动完成再打开浏览器
start /b cmd /c "timeout /t 8 /nobreak >nul && start http://localhost:8501"

:: 启动Streamlit（不等待）
python -m streamlit run web_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false

goto :end

:error
echo [错误] 无法进入目录
pause

:end
endlocal
