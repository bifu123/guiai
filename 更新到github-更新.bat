@echo off
REM set /p commitMsg=请输入提交信息：

git add .

REM git commit -m "%commitMsg%"
git commit -m "debug"
git push origin main

pause
