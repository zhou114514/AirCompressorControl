import sys
import socket
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import threading

from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import socket
import time
import pandas as pd
import os
import datetime


import json

VERSION = "Unknown" if not os.path.exists("Confiles\\更新内容.csv") or \
    pd.read_csv("Confiles\\更新内容.csv", header=None, index_col=None).iloc[-1, 0] is None \
    else pd.read_csv("Confiles\\更新内容.csv", header=None, index_col=None).iloc[-1, 0]

# log_path = "C:\\Logs\\starer_sever"

class TCPServer(QThread):
    """TCP服务器"""
    tcpSignal = pyqtSignal([str, dict])

    def __init__(self, host='127.0.0.1', port=10007, callback=None):
        super(TCPServer, self).__init__()
        # 本机IP地址
        self.host = host
        self.port = int(port)
        self.client_socket = None
        self.callback = callback
        self._running = False
        self._server_socket = None

    def handle_client_connection(self, client_socket):
        """处理客户端连接"""
        try:
            buffer = ""
            self.client_socket = client_socket
            while True:
                data = client_socket.recv(1024).decode('gbk')
                print(f"接收到来自{client_socket.getpeername()}的数据: {data}")
                if not data:
                    break
                buffer += data
                if "\n" in buffer:
                    messages = buffer.split("\n")
                    for message in messages[:-1]:
                        try:
                            message = json.loads(message)
                            self.callback(message)
                        except Exception as e:
                            print("命令格式错误")
                            self.returnpacket_callback([False, "", "Format error"])
                    buffer = messages[-1]
            if buffer:
                try:
                    message = json.loads(buffer)
                    self.callback(message)
                except Exception as e:
                    print("命令格式错误")
                    self.returnpacket_callback([False, "", "Format error"])
        except Exception as e:
            print(f"{client_socket.getpeername()}:客户端连接异常: {e}")
        finally:
            print(f"关闭来自{client_socket.getpeername()}的连接")
            # self.client_threads.pop(client_socket.getpeername())  # 删除客户端线程
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()

    def run(self):
        """启动TCP服务器"""
        print("启动TCP服务器")
        print(f"本机IP地址: {self.host}")
        print(f"端口号: {self.port}")

        # 检查链接是否使用
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex((self.host, self.port))
            if result == 0:
                print(f"端口{self.port}已被占用，请更换端口")
                return

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(('', self.port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)
        self._running = True
        print(f"服务器正在{self.host}:{self.port}上监听...")

        try:
            while self._running:
                try:
                    client_socket, addr = self._server_socket.accept()
                    print(f"接受到来自{addr}的连接")
                    client_thread = threading.Thread(
                        target=self.handle_client_connection,
                        args=(client_socket,),
                        daemon=True,
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"连接异常: {e}")
        finally:
            self._server_socket.close()
            self._server_socket = None
            print("TCP服务器已关闭")

    def send(self, client_socket, data):
        """向客户端发送数据"""
        data = data + "\n"
        try:
            client_socket.sendall(data.encode('gbk'))
        except Exception as e:
            print(f"向{client_socket.getpeername()}发送数据异常: {e}")

    def close_tcp_server(self):
        """关闭TCP服务器"""
        self._running = False
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except Exception:
                pass
        
    def returnpacket_callback(self, data):
        """返回包回调"""
        if self.client_socket is not None:
            print(f"返回包回调: {data}")
            pack = self.make_backpack(data[0], data[1], data[2])
            self.send(self.client_socket, pack)

    def make_backpack(self, isSuccess:bool, value:dict|str, msg:str):
        """返回包"""
        backpack = {
            "IsSuccessful": isSuccess,
            "Value": value,
            "ErrorMessage": msg
        }
        return json.dumps(backpack)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    server = TCPServer()
    server.start()
    sys.exit(app.exec_())