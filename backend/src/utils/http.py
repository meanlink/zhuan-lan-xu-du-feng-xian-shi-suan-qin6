import json, urllib.request, urllib.error
def call(method, url, body=None, token='', timeout=5):
    """最小 HTTP 客户端:返回 (状态码, JSON响应, 网络错误)。非 2xx 不抛异常,网络异常不抛出。"""
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'Content-Type': 'application/json', 'X-Inbox-Token': token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}, None
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return e.code, payload, None
    except Exception as e:
        return None, None, str(e)[:200]
