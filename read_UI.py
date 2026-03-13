import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                             QTableWidgetItem, QVBoxLayout, QWidget, QSizePolicy)
from PyQt5.QtCore import pyqtSignal, QObject, QTimer

class DictionaryTableModel(QObject):
    """数据模型类，负责管理字典数据"""
    dataChanged = pyqtSignal(dict)  # 数据变化信号
    
    def __init__(self, initial_data=None):
        super().__init__()
        self._data = initial_data if initial_data is not None else {}
    
    @property
    def data(self):
        """获取当前字典数据的副本"""
        return self._data.copy()
    
    @data.setter
    def data(self, new_data):
        """设置新数据并发出变化信号"""
        if new_data != self._data:
            self._data = new_data.copy()
            self.dataChanged.emit(self._data)
    
    def update_value(self, key, value):
        """更新单个键值"""
        if key in self._data:
            self._data[key] = value
            self.dataChanged.emit(self._data)
        else:
            print(f"警告: 键 '{key}' 不存在于字典中")

class DictionaryTableWidget(QWidget):
    """可嵌入的字典表格控件"""
    def __init__(self, initial_data=None, parent=None):
        super().__init__(parent)
        # 创建数据模型
        self.model = DictionaryTableModel(initial_data)
        # 连接数据变化信号
        self.model.dataChanged.connect(self.update_table)
        
        self.initUI()
        self.update_table(self.model.data)  # 初始更新
    
    def initUI(self):
        # 创建主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # 去除边距
        
        # 创建表格部件
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['键', '值'])
        
        # 设置表格大小策略 - 可扩展
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置表头拉伸模式
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        
        # 将表格添加到布局
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def update_table(self, new_data):
        """根据新数据更新表格"""
        # 检查是否需要重建表格结构
        if set(new_data.keys()) != {self.table.item(row, 0).text() for row in range(self.table.rowCount())}:
            self.rebuild_table(new_data)
        else:
            self.update_values(new_data)
    
    def rebuild_table(self, data):
        """完全重建表格（当键发生变化时）"""
        self.table.setRowCount(len(data))
        
        for row, (key, value) in enumerate(data.items()):
            # 设置键单元格（不可编辑）
            key_item = QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() ^ 0x0002)  # 使单元格不可编辑
            self.table.setItem(row, 0, key_item)
            
            # 设置值单元格
            value_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 1, value_item)
        
        # 调整列宽
        self.table.resizeColumnsToContents()
    
    def update_values(self, data: dict):
        """只更新值（当键不变时）"""
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            if key_item:
                key = key_item.text()
                value_item = self.table.item(row, 1)
                if value_item and key in data:
                    new_value = str(data[key])
                    if value_item.text() != new_value:
                        value_item.setText(new_value)
        # 强制刷新表格以立即显示更改
        self.table.viewport().update()
    
    def set_data(self, new_data):
        """设置新字典数据（完全替换）"""
        self.model.data = new_data
    
    def update_value(self, key, value):
        """更新单个键值"""
        self.model.update_value(key, value)
    
    def sizeHint(self):
        """提供合适的大小建议"""
        return self.table.sizeHint()
