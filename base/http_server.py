"""
HTTP server for StrangeCat Monitor.
Serves metrics in the exact format required.
"""
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

_http_server = None
_http_thread = None
_data_lock = threading.Lock()
_collector = None


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics."""
    
    store = None
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/performance":
            try:
                if self.store:
                    body = json.dumps(self.store.http_payload()).encode()
                else:
                    body = json.dumps({"timestamp": time.time(), "psutil": {}, "hwinfo": []}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def start_http(port, collector):
    """Start the HTTP server."""
    global _http_server, _http_thread, _collector
    
    stop_http()
    
    try:
        _collector = collector
        class _H(MetricsHandler):
            store = _collector
        _http_server = HTTPServer(("127.0.0.1", port), _H)
        threading.Thread(
            target=_http_server.serve_forever,
            name="SCat-http", daemon=True).start()
        return True
    except Exception:
        return False


def stop_http():
    """Stop the HTTP server."""
    global _http_server, _http_thread
    
    if _http_server:
        try:
            _http_server.shutdown()
        except Exception:
            pass
        _http_server = None
