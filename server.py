#!/usr/bin/env python3
"""
A股风格轮动盯盘仪表盘 — 本地服务器
功能:
  - 一键启动: python server.py
  - 自动打开浏览器
  - 静态文件服务 (dashboard.html, dashboard_data.js 等)
  - /api/refresh -> 重新抓取数据并生成仪表盘
  - /api/data -> 读取最新 dashboard_data.json
  - /api/status -> 数据新鲜度检查
"""
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8765


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def log_message(self, format, *args):
        # 简化日志
        sys.stdout.write(f"  [{self.command}] {args[0]}\n")

    def end_headers(self):
        # CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/refresh':
            self.handle_refresh()
        elif path == '/api/data':
            self.handle_api_data()
        elif path == '/api/status':
            self.handle_status()
        elif path == '/api/fetch':
            self.handle_fetch()
        else:
            # 静态文件服务
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/refresh':
            self.handle_refresh()
        else:
            self.send_error(404)

    def handle_refresh(self):
        """运行完整的数据刷新流程（同步执行，一次性返回结果）"""
        result = {'success': True, 'steps': []}

        try:
            # Step 1: fetch_data.py
            r = subprocess.run(
                [sys.executable, os.path.join(BASE, 'fetch_data.py')],
                capture_output=True, text=True, timeout=300, cwd=BASE,
                env={**os.environ, 'PYTHONPATH': os.path.join(BASE, 'lib')}
            )
            result['steps'].append({
                'step': 'fetch_data.py',
                'status': 'ok' if r.returncode == 0 else 'failed',
                'output': r.stdout[-500:] if r.stdout else '',
                'error': r.stderr[-500:] if r.returncode != 0 and r.stderr else ''
            })

            # Step 2: gen_data.py
            r2 = subprocess.run(
                [sys.executable, os.path.join(BASE, 'gen_data.py')],
                capture_output=True, text=True, timeout=60, cwd=BASE
            )
            result['steps'].append({
                'step': 'gen_data.py',
                'status': 'ok' if r2.returncode == 0 else 'failed',
                'output': r2.stdout[-500:] if r2.stdout else '',
                'error': r2.stderr[-500:] if r2.returncode != 0 and r2.stderr else ''
            })

            # Step 3: build_html.py
            r3 = subprocess.run(
                [sys.executable, os.path.join(BASE, 'build_html.py')],
                capture_output=True, text=True, timeout=60, cwd=BASE
            )
            result['steps'].append({
                'step': 'build_html.py',
                'status': 'ok' if r3.returncode == 0 else 'failed',
                'output': r3.stdout[-500:] if r3.stdout else '',
                'error': r3.stderr[-500:] if r3.returncode != 0 and r3.stderr else ''
            })

            all_ok = all(s['status'] == 'ok' for s in result['steps'])
            result['success'] = all_ok

            if all_ok:
                with open(os.path.join(BASE, 'dashboard_data.json'), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                result['data_date'] = data.get('date', '')
                result['sh_index'] = data.get('sh_index', 0)
                result['overall'] = data.get('overall', '')
                result['overall_label'] = data.get('overall_label', '')
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['error'] = '刷新超时（>5分钟），请检查网络连接'
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

    def handle_api_data(self):
        """返回最新的 dashboard_data.json"""
        data_path = os.path.join(BASE, 'dashboard_data.json')
        if os.path.exists(data_path):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            with open(data_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, '数据文件不存在，请先运行 refresh_dashboard.bat')

    def handle_status(self):
        """返回数据新鲜度状态"""
        data_path = os.path.join(BASE, 'dashboard_data.json')
        status = {
            'data_exists': os.path.exists(data_path),
            'last_modified': None,
            'data_date': None,
            'hours_since_update': None
        }
        if status['data_exists']:
            mtime = os.path.getmtime(data_path)
            status['last_modified'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            status['data_date'] = data.get('date', '')
            hours = (time.time() - mtime) / 3600
            status['hours_since_update'] = round(hours, 1)
            status['is_stale'] = hours > 24

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(status, ensure_ascii=False).encode())

    def handle_fetch(self):
        """仅运行 fetch_data.py（快速更新）"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        result = {'success': True}
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(BASE, 'fetch_data.py')],
                capture_output=True, text=True, timeout=300, cwd=BASE,
                env={**os.environ, 'PYTHONPATH': os.path.join(BASE, 'lib')}
            )
            result['success'] = r.returncode == 0
            result['output'] = r.stdout[-1000:] if r.stdout else ''
            if not result['success']:
                result['error'] = r.stderr[-500:] if r.stderr else ''
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['error'] = '抓取超时'
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)

        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())


def main():
    print(f"""
╔══════════════════════════════════════════════════════╗
║     📊 A股风格轮动盯盘仪表盘 — 本地服务器             ║
╠══════════════════════════════════════════════════════╣
║  地址: http://localhost:{PORT}                         ║
║  刷新: http://localhost:{PORT}/api/refresh (POST/GET)  ║
║  数据: http://localhost:{PORT}/api/data                ║
║  状态: http://localhost:{PORT}/api/status              ║
║  按 Ctrl+C 停止服务器                                  ║
╚══════════════════════════════════════════════════════╝
""")

    server = http.server.HTTPServer(('127.0.0.1', PORT), DashboardHandler)

    # 1秒后自动打开浏览器
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{PORT}/dashboard.html')

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        print(f"  服务器已启动，正在监听 http://127.0.0.1:{PORT}")
        print(f"  按 Ctrl+C 停止\n")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务器已停止。")
        server.shutdown()


if __name__ == '__main__':
    main()
