import argparse
import requests
import json
import sys

def search_causal_cli():
    parser = argparse.ArgumentParser(
        description="ylbot Causal AI: 基于关键字的因果事件搜索工具",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 定义命令行参数
    parser.add_argument("keyword", help="搜索关键词，支持逻辑与（&）操作符，例如: '商王&祭祀'")
    parser.add_argument("--owner", "-o", help="事件拥有者ID (owner_id)", default="815669761")
    parser.add_argument("--limit", "-l", type=int, help="返回结果数量限制 (默认 100)", default=100)
    parser.add_argument("--json", action="store_true", help="以原始 JSON 格式输出结果")

    args = parser.parse_args()

    url = "http://192.168.66.39:8094/api/v1/causal/search/keyword"
    
    # 构造请求载荷
    payload = {"keyword": args.keyword}
    if args.owner:
        payload["owner_id"] = args.owner
    if args.limit:
        payload["limit"] = args.limit

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        if result.get('status') == 'success':
            data = result.get('data', [])
            count = result.get('count', 0)
            print(f"✅ 搜索成功: 找到 {count} 个相关事件 (V5 算法排序)\n")
            print(f"{'事件 ID (Node ID)':<20} | {'相关度':<10}")
            print("-" * 35)
            for item in data:
                print(f"{item.get('node_id', 'N/A'):<20} | {item.get('relevance_score', 0):.4f}")
        else:
            print(f"❌ 搜索失败: {result.get('message')}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"🔌 网络连接失败 (检查 192.168.66.39 服务状态): {e}")
        sys.exit(1)

if __name__ == "__main__":
    search_causal_cli()