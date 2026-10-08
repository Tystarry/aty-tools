#!/usr/bin/env python3
"""
AI_TY 插件面板 — 局域网服务器

用法:
    python server.py              # 默认端口 8080
    python server.py 9000         # 自定义端口

启动后：
  本机访问:   http://localhost:8080/插件面板.html
  其他电脑:   http://你的IP:8080/插件面板.html

留言板数据存在 server_msgs.json，重启不丢。
"""

import os, json, time, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
HOST = '0.0.0.0'  # 监听所有网卡，允许局域网访问
MSG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_msgs.json')


def load_msgs():
    try:
        with open(MSG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_msgs(msgs):
    with open(MSG_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/msgs'):
            msgs = load_msgs()
            self.send_json(msgs[-100:])  # 最近 100 条
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/msgs'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
                name = data.get('name', '匿名').strip() or '匿名'
                text = data.get('text', '').strip()
                if not text:
                    self.send_json({'error': '内容不能为空'}, 400)
                    return
                msgs = load_msgs()
                msgs.append({
                    'name': name,
                    'text': text,
                    'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                })
                save_msgs(msgs)
                self.send_json({'ok': True})
            except json.JSONDecodeError:
                self.send_json({'error': 'JSON 格式错误'}, 400)
        else:
            self.send_error(404)

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"  {args[0]}")


def get_ip():
    """获取本机局域网 IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ip = get_ip()
    print(f"""
╔══════════════════════════════════════╗
║     AI_TY 插件面板 — 局域网模式       ║
╠══════════════════════════════════════╣
║  本机: http://localhost:{PORT}/插件面板.html
║  分享: http://{ip}:{PORT}/插件面板.html
║                                      ║
║  留言板已开启共享模式                  ║
║  按 Ctrl+C 停止服务器                  ║
╚══════════════════════════════════════╝
""")

    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()
