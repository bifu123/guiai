import argparse
import requests
import json
import sys

def click_causal_cli():
    parser = argparse.ArgumentParser(
        description="ylbot Causal AI: 节点点击业务 - 获取完整节点事件描述与多因多果前后事件关系",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("serial_id", type=int, help="节点的物理 ID (serial_id)")
    parser.add_argument("--actor_id", "-a", help="事件观察者ID，用于个性化权重更新", default=None)
    parser.add_argument("--owner_id", "-o", help="事件拥有者ID，因果链的创建者", default=None)
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")

    args = parser.parse_args()
    url = "http://192.168.66.39:8094/api/v1/causal/click"
    
    payload = {
        "serial_id": args.serial_id,
        "owner_id": args.owner_id
    }
    if args.actor_id:
        payload["actor_id"] = args.actor_id

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        if result.get('status') == 'success':
            event = result.get('data', {})
            
            # 处理多因多果逻辑，兼容可能返回的字段名（如 parent_ids 或 parent_id 实际为列表）
            parents = event.get('parent_ids') or event.get('parent_id') or []
            children = event.get('child_ids') or event.get('child_id') or []
            
            # 确保即使 API 返回单个元素或 None，也能安全转为列表呈现
            if not isinstance(parents, list): parents = [parents] if parents else []
            if not isinstance(children, list): children = [children] if children else []
            
            print(f"点击业务处理成功: {event.get('node_id', '未知节点')}")
            print("-" * 50)
            
            print(f"▶ 核心元组 (event_tuple): {event.get('event_tuple')}")
            # 以数组格式输出，明确表示多因多果
            print(f"▶ 父节点列表 (Parents)  : {parents}")
            print(f"▶ 子节点列表 (Children) : {children}")
            
            print("-" * 50)
            print(f"权重提升到: {event.get('survival_weight', 0):.2%}")
            print(f"更新节点数: {result.get('updated_count', 0)}")
            
            if args.actor_id:
                print("用户个性化权重已更新")
                print(f"观察者用户: {event.get('actor_id')}")
                print(f"事件拥有者: {event.get('owner_id')}")

        else:
            print(f"点击业务处理失败: {result.get('message')}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"网络请求异常 (192.168.66.39): {e}")
        sys.exit(1)

if __name__ == "__main__":
    click_causal_cli()