@echo off
chcp 65001 >nul 2>&1
title SecBot 离线安装

echo.
echo  ==========================================
echo     SecBot 离线安装程序
echo  ==========================================
echo.

:: =============================================
::  Step 1: 检查 Python
:: =============================================
python --version >nul 2>&1
if errorlevel 1 (
    echo  [错误] 未找到 Python
    echo  请先安装 Python 3.8+: https://www.python.org/downloads/
    echo  注意: 安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER%
echo.

:: =============================================
::  Step 2: 解析 Python 版本号
:: =============================================
:: Python 3.8.0 -> 38, Python 3.11.4 -> 311
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)
set PYVER_NUM=%PYMAJOR%%PYMINOR%
echo  Python 版本: %PYVER_NUM% (目标架构: win_amd64)
echo.

:: =============================================
::  Step 3: 安装 pip (如缺失)
:: =============================================
pip --version >nul 2>&1
if errorlevel 1 (
    echo  [i] pip 未找到，尝试安装...
    :: 方式1: 用 pip wheel 安装
    python -m ensurepip --upgrade >nul 2>&1
    if errorlevel 1 (
        :: 方式2: 用离线 wheel
        for %%f in (offline\pip\pip-*.whl) do (
            if exist "%%f" (
                echo  使用离线 wheel: %%~nxf
                python "%%f" --no-warn-script-location
                goto :pip_done
            )
        )
        echo  [错误] pip 安装失败，请检查 offline\pip\ 目录
        pause
        exit /b 1
    )
)
:pip_done
pip --version
echo.

:: =============================================
::  Step 4: 从 offline/pip/ 安装所有 wheel
:: =============================================
echo  [i] 开始安装离线包...
echo.

set INSTALLED=0
set FAILED=0

for %%f in (offline\pip\*.whl) do (
    :: 跳过不兼容的 wheel
    echo %%~nxf | findstr /C:"cp27" >nul
    if not errorlevel 1 (
        echo  [跳过] %%~nxf (Python 2.7 不兼容)
    ) else (
        echo  [安装] %%~nxf
        pip install "%%f" --no-deps --force-reinstall -q >nul 2>&1
        if errorlevel 1 (
            echo         失败，尝试忽略...
            pip install "%%f" --no-deps --ignore-installed -q >nul 2>&1
            if errorlevel 1 (
                echo         [警告] %%~nxf 安装失败
                set /a FAILED+=1
            ) else (
                set /a INSTALLED+=1
            )
        ) else (
            set /a INSTALLED+=1
        )
    )
)

echo.
echo  安装完成: %INSTALLED% 个成功, %FAILED% 个失败
echo.

:: =============================================
::  Step 5: 验证核心依赖
:: =============================================
echo  验证核心依赖...
python -c "import requests; print('  [OK] requests')" 2>nul
if errorlevel 1 echo  [X] requests 安装失败

python -c "import colorama; print('  [OK] colorama')" 2>nul
if errorlevel 1 echo  [X] colorama 安装失败

python -c "import nmap; print('  [OK] python-nmap')" 2>nul
if errorlevel 1 echo  [i] python-nmap 未安装 (nmap 功能依赖系统 nmap)

python -c "import streamlit; print('  [OK] streamlit')" 2>nul
if errorlevel 1 echo  [X] streamlit 未安装 (Web UI 依赖)

python -c "import paramiko; print('  [OK] paramiko')" 2>nul
if errorlevel 1 echo  [i] paramiko 未安装 (SSH 爆破依赖)

echo.

:: =============================================
::  Step 6: 安装 nmap (如存在)
:: =============================================
if exist "offline\nmap\*.exe" (
    echo  安装 nmap 到系统目录...
    for %%f in (offline\nmap\*.exe) do (
        echo   安装 %%~nxf...
        start /wait cmd /c "%%f /S /D=C:\nmap" >nul 2>&1
    )
    echo  [OK] nmap 安装完成
) else if exist "offline\nmap\*.zip" (
    echo  [i] 检测到 nmap.zip，请手动解压并添加到 PATH
    echo    下载: https://nmap.org/dist/nmap-7.95-win32.zip
) else (
    echo  [i] 未找到 offline\nmap\，跳过 nmap
    echo    下载: https://nmap.org/dist/nmap-7.95-win32.zip
)

:: =============================================
::  Step 7: AI 配置检查
:: =============================================
echo.
findstr /C:"YOUR_API_KEY" config.py >nul 2>&1
if not errorlevel 1 (
    echo  [警告] AI API Key 未配置
    echo  请编辑 config.py 填入有效的 API Key
) else (
    echo  [OK] AI 配置已就绪
)

:: =============================================
::  完成
:: =============================================
echo.
echo  ==========================================
echo   安装完成!
echo  ==========================================
echo.
echo  运行方式:
echo   python main.py         -^> 命令行界面
echo   SecBot启动器.bat       -^> 一键启动
echo.
echo  Web UI: python web_app.py (需 streamlit)
echo  依赖检测: python main.py -^> 选 [D]
echo.
pause
