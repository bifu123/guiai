import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

class RedisContextManager:
    def __init__(self, host=None, port=None, db=None):
        self.host = host or os.getenv("REDIS_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.db = db or int(os.getenv("REDIS_DB", 13))
        self.redis_client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        
    def set_task_status(self, session_id, status):
        self.redis_client.set(f"task:{session_id}:status", status)
        
    def get_task_status(self, session_id):
        return self.redis_client.get(f"task:{session_id}:status")
        
    def add_history(self, session_id, thought, action, observation):
        record = {
            "T": thought,
            "A": action,
            "O": observation
        }
        self.redis_client.rpush(f"task:{session_id}:history", json.dumps(record, ensure_ascii=False))
        
    def get_history(self, session_id):
        records = self.redis_client.lrange(f"task:{session_id}:history", 0, -1)
        return [json.loads(r) for r in records]
        
    def set_element_coords(self, session_id, target_name, coords):
        self.redis_client.hset(f"task:{session_id}:elements", target_name, json.dumps(coords))
        
    def get_element_coords(self, session_id, target_name):
        coords_str = self.redis_client.hget(f"task:{session_id}:elements", target_name)
        if coords_str:
            return json.loads(coords_str)
        return None
        
    def set_summary(self, session_id, summary):
        self.redis_client.set(f"task:{session_id}:summary", summary)
        
    def get_summary(self, session_id):
        return self.redis_client.get(f"task:{session_id}:summary")
        
    def set_task_intent(self, session_id, intent):
        self.redis_client.set(f"task:{session_id}:current_intent", intent)
        
    def get_task_intent(self, session_id):
        return self.redis_client.get(f"task:{session_id}:current_intent")
        
    # --- 全局占用锁机制 ---
    def set_global_active_user(self, session_id):
        """设置当前占用 Agent 的用户"""
        self.redis_client.set("global:active_user", session_id)
        
    def get_global_active_user(self):
        """获取当前占用 Agent 的用户"""
        return self.redis_client.get("global:active_user")
        
    def clear_global_active_user(self, session_id):
        """
        清除全局占用锁。
        为了安全，只有当前占用者（或强制清理时）才能清除。
        """
        current_user = self.get_global_active_user()
        if current_user == session_id or current_user is None:
            self.redis_client.delete("global:active_user")
            return True
        return False

    def clear_all_tasks(self):
        """
        清空所有任务相关的键以及全局占用锁。
        """
        keys = self.redis_client.keys("task:*")
        if keys:
            self.redis_client.delete(*keys)
        self.redis_client.delete("global:active_user")

redis_manager = RedisContextManager()
