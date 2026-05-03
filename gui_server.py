import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Union, Optional
import json

# 导入需要封装的函数
from gui_tools import execute_manual_flow, run_for_agent

app = FastAPI(title="GUI Agent Server", description="提供 GUI 自动化操作的 API 接口")

# 定义请求体模型
class ManualFlowRequest(BaseModel):
    flow_data: Union[List[Dict[str, Any]], str]
    endpoint: str = "http://192.168.68.16:8000/execute"
    time_sleep: float = 3.0
    params: Optional[Dict[str, Any]] = None

class AgentRequest(BaseModel):
    user_id: str
    intent: str
    max_attempts: int = 5
    gui_client_url: str = "http://192.168.68.16:8000/execute"
    show_img: bool = False
    history: Optional[List[Dict[str, Any]]] = None

@app.post("/api/execute_manual_flow")
def api_execute_manual_flow(req: ManualFlowRequest):
    """
    顺次执行手动定义的流程自动化列表。
    """
    try:
        result = execute_manual_flow(
            flow_data=req.flow_data,
            endpoint=req.endpoint,
            time_sleep=req.time_sleep,
            params=req.params
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run_for_agent")
def api_run_for_agent(req: AgentRequest):
    """
    执行 GUI Agent 任务，根据自然语言意图自动操作桌面。
    """
    try:
        result = run_for_agent(
            user_id=req.user_id,
            intent=req.intent,
            max_attempts=req.max_attempts,
            gui_client_url=req.gui_client_url,
            show_img=req.show_img,
            history=req.history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动 GUI Agent Server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
