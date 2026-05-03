@echo off
SETLOCAL EnableDelayedExpansion

:: 1. 配置业务变量
SET "UNC_PATH=\\192.168.66.41\root\root\guiai"
SET "PROXY_URL=http://192.168.66.24:65532"

echo [INFO] 正在进入工作目录...
:: 使用 pushd 进入网络路径
pushd "%UNC_PATH%" || (
    echo [ERROR] 无法映射路径，请检查网络连接。
    pause
    exit /b
)

:: 2. 检查并清理残留的 Git 锁文件
if exist ".git\index.lock" (
    echo [WARN] 检测到残留的 index.lock，正在尝试清理...
    del /f /q ".git\index.lock"
)

:: 3. 仓库检查
if not exist ".git" (
    echo [ERROR] 找不到 .git 目录，请确认路径: %CD%
    goto :SCRIPT_END
)

:: 4. 处理时间字符串
set "cur_date=%date%"
set "cur_time=%time: =0%"
set "commit_msg=Auto-update %cur_date% %cur_time%"

echo [INFO] 提交信息: "%commit_msg%"

echo [INFO] 正在同步...
:: 使用 call 调用 git，防止脚本意外提前退出
call git status --porcelain | findstr /R "^" >nul
if !errorlevel! neq 0 (
    echo [INFO] 没有检测到变更，跳过同步。
    goto :SCRIPT_END
)

call git add .
call git commit -m "%commit_msg%"

:: 5. 推送逻辑
echo [INFO] 正在推送至 GitHub...
:: 在执行关键 git push 时务必使用 call
call git -c http.proxy=%PROXY_URL% -c https.proxy=%PROXY_URL% push origin main

if !errorlevel! eq 0 (
    echo.
    echo [SUCCESS] 任务圆满完成！
) else (
    echo.
    echo [ERROR] 推送过程中出现问题，请检查代理或网络。
)

:SCRIPT_END
:: 6. 先退出目录堆栈，再显示结束信息
popd
echo.
echo ========================================
echo   所有职责处理完毕。
echo   当前时间: %date% %time%
echo ========================================

:: 这里的 pause 建议配合一个输入判断，防止 cmd 环境异常忽略它
echo 按任意键确认退出...
pause >nul