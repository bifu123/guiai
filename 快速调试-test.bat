@echo off
REM 设置窗口标题
title test 快速调试
REM 1. 激活环境
call conda activate guiai
REM 2.运行 Python 脚本
python test.py

pause