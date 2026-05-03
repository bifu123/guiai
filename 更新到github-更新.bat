@echo off
SETLOCAL EnableDelayedExpansion

:: 1. 配置业务变量
SET "UNC_PATH=\\192.168.66.41\root\root\guiai"
SET "PROXY_URL=http://192.168.66.24:65532"

echo [INFO] 正在进入工作目录...
pushd "%UNC_PATH%" || (
    echo [ERROR] 无法映射路径，请检查网络连接。
    pause
    exit /b
)

:: 2. 检查并清理残留的 Git 锁文件 (关键修复)
if exist ".git\index.lock" (
    echo [WARN] 检测到残留的 index.lock，正在尝试清理...
    del /f /q ".git\index.lock"
)

:: 3. 仓库检查
if not exist ".git" (
    echo [ERROR] 找不到 .git 目录，请确认路径: %CD%
    popd
    pause
    exit /b
)

:: 4. 处理时间字符串
set "cur_date=%date%"
set "cur_time=%time: =0%"
set "commit_msg=Auto-update %cur_date% %cur_time%"

echo [INFO] 提交信息: "%commit_msg%"

echo [INFO] 正在同步...
:: 检查是否有文件变更，避免产生空的 commit 报错
git status --porcelain | findstr /R "^" >nul
if !errorlevel! neq 0 (
    echo [INFO] 没有检测到变更，跳过同步。
    goto :FINISH
)

git add .
git commit -m "%commit_msg%"

:: 5. 推送逻辑
echo [INFO] 正在推送至 GitHub...
git -c http.proxy=%PROXY_URL% -c https.proxy=%PROXY_URL% push origin main

if !errorlevel! eq 0 (
    echo.
    echo [SUCCESS] 任务圆满完成！
) else (
    echo.
    echo [ERROR] 推送过程中出现问题。
)

:FINISH
:: 6. 清理并退出
popd
echo [INFO] 脚本运行完毕。
timeout /t 5