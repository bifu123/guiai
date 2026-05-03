@echo off
REM 设置窗口标题
title server 快速调试
REM 激活环境
call conda activate guiai
REM 运行 Python 脚本
python gui_server.py
