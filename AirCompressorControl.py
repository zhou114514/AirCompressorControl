import sys
import os
import threading
import time
import socket

# 添加snap7.dll路径处理
def setup_snap7():
    """设置snap7.dll路径"""
    # 获取当前执行文件的目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是python脚本
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # 将snap7.dll添加到系统路径
    snap7_dll_path = os.path.join(application_path, 'snap7.dll')
    if os.path.exists(snap7_dll_path):
        # 如果在应用程序目录找到snap7.dll，则将其路径添加到系统路径
        os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')
        print("协议加载成功")
    else:
        print("警告：未找到snap7.dll文件")

# 在导入snap7之前调用设置函数
setup_snap7()

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QVBoxLayout, QWidget
from Ui_AirCompressorUI import Ui_MainWindow
from read_UI import DictionaryTableWidget
from S7_1200 import S7_1200
from TCPServer import TCPServer

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_server_host(config):
    """从配置获取服务端监听IP：有配置值则用配置，否则用本机IP"""
    value = config.value("server_ip")
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return get_local_ip()
    return value if isinstance(value, str) else str(value).strip() or "127.0.0.1"

def get_server_port(config):
    """从配置获取服务端监听端口，默认10007"""
    value = config.value("server_port")
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 10007
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10007

class AirCompressorControl(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(AirCompressorControl, self).__init__(parent)
        self.setupUi(self)
        self.S7_1200 = S7_1200()  # 实例化空压机控制类
        self.readZone = None
        self.writeZone = None
        self.stopFlag = False
        self.config = QSettings('config.ini', QSettings.IniFormat)
        self.server = TCPServer(
            host=get_server_host(self.config),
            port=get_server_port(self.config),
            callback=self.callback,
        )
        self.server.start()
        self.initUI()  # 初始化界面
        self.init_btn()  # 初始化按钮

    def init_btn(self):
        self.connectPLC.clicked.connect(self.connect_device)  # 连接设备
        self.disconnectPLC.clicked.connect(self.disconnect_device)  # 断开设备
        self.start.clicked.connect(self.startCallback) # 开始读取数据
        self.stop.clicked.connect(self.stopCallback) # 停止读取数据
        self.connectPLC.setEnabled(True)
        self.disconnectPLC.setEnabled(False)
        self.start.setEnabled(False)
        self.stop.setEnabled(False)

    def connect_device(self):
        if self.IPaddress.text() != '' and self.setSlot.text() != '' and self.setRack.text() != '':
            ip = self.IPaddress.text()
            rack = int(self.setRack.text())
            slot = int(self.setSlot.text())
        else:
            ip, rack, slot = self.config.value("ip"), int(self.config.value("rack")), int(self.config.value("slot"))
        if self.S7_1200.connect_device(ip, rack, slot):  # 连接设备
            self.start.setEnabled(True)
            self.stop.setEnabled(False)
            self.disconnectPLC.setEnabled(True)
            self.connectPLC.setEnabled(False)

    def disconnect_device(self):
        self.stopFlag = True
        self.S7_1200.disconnect_device()
        self.connectPLC.setEnabled(True)
        self.disconnectPLC.setEnabled(False)
        self.start.setEnabled(False)
        self.stop.setEnabled(False)


    def initUI(self):
        self.S7_1200.initState()  # 初始化状态
        self.clear_tab_layout(0)  # 清空读取区
        self.clear_tab_layout(1)  # 清空写入区
        self.readZone = DictionaryTableWidget(initial_data=self.S7_1200.get_state())  # 实例化读取区
        self.readPLC.layout().addWidget(self.readZone)  # 加入读取区
        self.writeZone = DictionaryTableWidget(initial_data=self.S7_1200.get_commands())  # 实例化写入区
        self.writePLC.layout().addWidget(self.writeZone)  # 加入写入区
        if self.config.value("ip", None) == None:
            self.config.setValue("ip", "192.168.0.1")
        if self.config.value("rack", None) == None:
            self.config.setValue("rack", 0)
        if self.config.value("slot", None) == None:
            self.config.setValue("slot", 1)
        if self.config.value("server_ip", None) is None:
            self.config.setValue("server_ip", "")
        if self.config.value("server_port", None) is None:
            self.config.setValue("server_port", 10007)
        self.IPaddress.setPlaceholderText(self.config.value("ip"))
        self.setRack.setPlaceholderText(str(self.config.value("rack")))
        self.setSlot.setPlaceholderText(str(self.config.value("slot")))

    def clear_tab_layout(self, tab_index):
        # 获取指定标签页的 widget
        tab_widget = self.IOtab.widget(tab_index)
        
        # 清空现有 layout
        old_layout = tab_widget.layout()
        if old_layout:
            # 删除所有控件
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # 可选：删除并重新设置 layout
            tab_widget.setLayout(None)  # 删除旧 layout
            new_layout = QVBoxLayout()  # 或其他类型的 layout
            tab_widget.setLayout(new_layout)

    def readThread(self):
        while not self.stopFlag:
            self.S7_1200._get_state()
            self.readZone.update_values(self.S7_1200.get_state())
            time.sleep(1)

    def startCallback(self):
        self.stopFlag = False
        thread = threading.Thread(target=self.readThread)
        thread.start()
        self.stop.setEnabled(True)
        self.start.setEnabled(False)

    def stopCallback(self):
        self.stopFlag = True
        self.start.setEnabled(True)
        self.stop.setEnabled(False)

    def callback(self, message: dict):
        if message['opcode'] == 'get_temp':
            tempList = ["热沉当前设定温度", "热沉控温点温度", "冷板当前设定温度", "冷板控温点温度"]
            state = self.S7_1200.get_state()
            value = {name: state[name] for name in tempList}
            self.server.returnpacket_callback([True, value, 'success'])
        elif message['opcode'] == 'get_state':
            stateList = ["一体机上电标志", "温控状态"]
            state = self.S7_1200.get_state()
            value = {name: state[name] for name in stateList}
            self.server.returnpacket_callback([True, value, 'success'])
        else:
            self.server.returnpacket_callback([False, None, 'No command'])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AirCompressorControl()
    window.show()
    sys.exit(app.exec_())