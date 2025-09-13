import subprocess
import os
import sys
import time
from http.server import HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler
import threading

# --- 配置 ---
APP_PORT = 7860
MAIN_SERVICE_PORT = 8010
SECONDARY_SERVICE_PORT = 8000
CMD_TEMPLATE = "python start.py"

# --- 代理逻辑 (无需改动) ---
class Proxy(BaseHTTPRequestHandler):
    def proxy_request(self):
        target_port = MAIN_SERVICE_PORT
        try:
            url = f'http://127.0.0.1:{target_port}{self.path}'
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            req = Request(url, data=body, headers=dict(self.headers), method=self.command)
            with urlopen(req, timeout=60) as response:
                self.send_response(response.status)
                for key, value in response.getheaders(): self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, f"Proxy Error: {e}")

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "message": "Launcher proxy is running"}')
            return
        self.proxy_request()

    def do_POST(self): self.proxy_request()
    def do_PUT(self): self.proxy_request()
    def do_DELETE(self): self.proxy_request()
    def do_OPTIONS(self): self.proxy_request()
    def do_HEAD(self): self.proxy_request()

# --- 服务启动和管理 ---
def run_service(port):
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(CMD_TEMPLATE.split(), env=env, stdout=sys.stdout, stderr=sys.stderr)
    print(f"Started service on port {port} with PID {process.pid}")
    return process

# 【核心修复】添加健康检查函数
def wait_for_service(port, timeout=60):
    """主动检查服务是否启动并响应请求"""
    start_time = time.time()
    url = f"http://127.0.0.1:{port}"
    # Warp2Api 的服务在根路径返回 404，这也可以算作 "running"
    # 我们需要找到一个能返回 200 的路径，比如 /docs
    health_check_url = f"{url}/docs" 
    
    while time.time() - start_time < timeout:
        try:
            # 使用 urlopen 检查服务是否响应
            with urlopen(health_check_url, timeout=2) as response:
                if response.status >= 200 and response.status < 500:
                    print(f"Service on port {port} is ready!")
                    return True
        except (URLError, ConnectionRefusedError):
            print(f"Service on port {port} not ready yet, retrying...")
            time.sleep(2)
        except Exception as e:
            print(f"An unexpected error occurred while checking port {port}: {e}")
            time.sleep(2)
    
    print(f"Error: Service on port {port} did not start within {timeout} seconds.")
    return False

if __name__ == "__main__":
    print("--- Starting Services ---")
    
    # 首先启动依赖服务 (8000)
    process_8000 = run_service(SECONDARY_SERVICE_PORT)
    # 等待它完全准备好
    if not wait_for_service(SECONDARY_SERVICE_PORT):
        print("!!! Secondary service (8000) failed to start. Aborting.")
        process_8000.terminate()
        sys.exit(1)

    # 然后启动主服务 (8010)
    process_8010 = run_service(MAIN_SERVICE_PORT)
    # 等待它完全准备好
    if not wait_for_service(MAIN_SERVICE_PORT):
        print("!!! Main service (8010) failed to start. Aborting.")
        process_8000.terminate()
        process_8010.terminate()
        sys.exit(1)

    print(f"\n--- All services are healthy. Starting Proxy Server on port {APP_PORT} ---")
    print(f"Forwarding traffic to main service on port {MAIN_SERVICE_PORT}")
    
    httpd = HTTPServer(("", APP_PORT), Proxy)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n--- Shutting down ---")
        httpd.server_close()
        process_8000.terminate()
        process_8010.terminate()
        print("All services stopped.")
