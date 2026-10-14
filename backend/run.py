import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOST = '127.0.0.1'
PORT = 9090
URL = f'http://{HOST}:{PORT}/'


def open_browser_when_ready(timeout: float = 60.0) -> None:
    """Open the frontend in the default browser once the server accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                webbrowser.open(URL)
                return
        except OSError:
            time.sleep(0.5)
    print(f'Server did not respond in time. Open {URL} manually.')


if __name__ == '__main__':
    print('Dental AI Platform, port 9090')
    print('Swagger: http://localhost:9090/docs')
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print('Frontend: ' + URL)
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    uvicorn.run('main:app', host=HOST, port=PORT)
