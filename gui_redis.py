import redis
import json
import os

class RedisContextManager:
    def __init__(self, host='192.168.66.24', port=6379, db=13):
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
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

redis_manager = RedisContextManager()
