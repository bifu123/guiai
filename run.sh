#!/bin/bash

# 自动获取脚本所在目录
SERVER_DIR=$(cd $(dirname $0); pwd)
VENV_PATH="$SERVER_DIR/.guiai/bin/activate"
PYTHON_SCRIPT="gui_server.py"
LOG_FILE="$SERVER_DIR/server.log"

get_pid() {
    # 改进：通过检查监听 5002 端口的进程来获取 PID (最准确)
    # 如果没装 lsof，则回退到 ps 过滤
    pid=$(lsof -t -i:5002 2>/dev/null)
    if [ -z "$pid" ]; then
        pid=$(ps -ef | grep "$PYTHON_SCRIPT" | grep -v grep | awk '{print $2}' | head -n 1)
    fi
    echo "$pid"
}

start() {
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "服务已在运行，PID: $pid"
    else
        echo "正在从 $SERVER_DIR 启动服务..."
        cd "$SERVER_DIR" || exit
        if [ -f "$VENV_PATH" ]; then
            source "$VENV_PATH"
            # 启动命令
            nohup python "$PYTHON_SCRIPT" > /dev/null 2>&1 &
            
            # 延长等待时间，给 Uvicorn 启动留出空间
            echo -n "检测服务启动状态..."
            for i in {1..5}; do
                sleep 1
                pid=$(get_pid)
                if [ -n "$pid" ]; then
                    echo -e "\n✅ 服务已启动，PID: $pid"
                    return 0
                fi
                echo -n "."
            done
            echo -e "\n❌ 启动检测超时，请执行 'lsof -i:5002' 手动确认。"
        else
            echo "错误: 未找到虚拟环境 $VENV_PATH"
        fi
    fi
}

stop() {
    pid=$(get_pid)
    if [ -z "$pid" ]; then
        echo "未发现正在运行的服务。"
    else
        echo "正在停止 PID 为 $pid 的服务..."
        kill "$pid"
        sleep 2
        # 如果还没关掉，强制关闭
        new_pid=$(get_pid)
        if [ -n "$new_pid" ]; then
            kill -9 "$new_pid"
        fi
        echo "服务已停止。"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status)
        pid=$(get_pid)
        [ -n "$pid" ] && echo "运行中 PID: $pid" || echo "已停止"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac