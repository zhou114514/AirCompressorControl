import snap7
from snap7 import client, util
from functools import wraps
import time
import glob
import os
import pandas as pd

get_data = {
    'bool' : util.get_bool,
    'int' : util.get_int,
    'dword' : util.get_dword,
    'dint' : util.get_dint,
    'word' : util.get_word,
    'byte' : util.get_byte,
    'real' : util.get_real,
    'string' : util.get_string,
    'time' : util.get_time,
    'date' : util.get_date
}

class S7_1200():
    def __init__(self):
        self.protocol = {}
        self.protocol = self.initFormate()
        self.state = {}
        self.commands = {}
        self.initState()
        self.plc = client.Client()

    def connect_device(self, ip:str, rack:int, slot:int):
        self.plc.connect(ip, rack, slot)
        if self.plc.get_connected():
            print('Connected to PLC')
            return True
        else:
            print('Failed to connect to PLC')
            return False

    def disconnect_device(self):
        self.plc.disconnect()
        print('Disconnected from PLC')

    def _get_state(self):
        protocol = self.protocol['读地址']
        for key, value in protocol.items():
            if value['数据类型'] == 'bool':
                # 位索引优先从独立的"位"列读取，其次从地址小数部分解析（如 470.1 → bit 1）
                if value.get('位') is not None:
                    bit_index = int(value['位'])
                else:
                    addr_str = str(value['地址'])
                    bit_index = int(addr_str.split('.')[1]) if '.' in addr_str else 0
                byte_addr = int(str(value['地址']).split('.')[0])
                v = get_data[value['数据类型']](self.plc.db_read(int(value["DB区域"]), byte_addr, int(value['长度'])), 0, bit_index)
            else:
                v = get_data[value['数据类型']](self.plc.db_read(int(value["DB区域"]), int(value['地址']), int(value['长度'])), 0)
            strValue = None
            if value['定义'] is not None:
                strValue = value['定义'][str(v)]
            if value['系数'] is not None:
                v = v * float(value['系数'])
            self.state[key] = strValue if strValue is not None else v
                
    def initFormate(self):
        fileptah = 'Confiles/协议'
        if not os.path.exists(fileptah):
            print('协议文件不存在')
            print('请将协议文件放入Confiles文件夹中并重启程序')
            return
        
        files = glob.glob(os.path.join(fileptah, '*.xlsx'))
        if files == []:
            print('协议文件不存在')
            print('请将协议文件放入Confiles文件夹中并重启程序')
            return

        protocol = {}
        for file in files:
            frame = {}

            if not os.path.exists(file):
                continue
            df = pd.read_excel(file, header=0, index_col=None, dtype=str)
            df.fillna('', inplace=True)
            for row in df.itertuples(index=False):
                info = {}
                for key, value in row._asdict().items():
                    if key == '定义' and value != '':
                        valueParts = value.split(';')
                        d = {}
                        for valuePart in valueParts:
                            if ':' in valuePart:
                                keyValue = valuePart.split(':')
                                d[keyValue[0]] = keyValue[1]
                        value = d
                    info[key] = value if value != '' else None
                frame[row.数据名称] = info
            protocol[os.path.basename(file)[:-5]] = frame
            
        print(f'协议加载成功')
        return protocol
    
    def initState(self):
        self.state = {}
        self.commands = {}
        if self.protocol == None:
            print(f'协议不存在')
            return
        if '读地址' in self.protocol.keys():
            for key in self.protocol['读地址'].keys():
                self.state[key] = None
        if '写地址' in self.protocol.keys():
            for key, value in self.protocol['写地址'].items():
                self.commands[key] = value

    def get_state(self):
        return self.state

    def get_state_by_category(self, category: str) -> dict:
        """返回 读地址 协议中 分类==category 的所有字段当前值"""
        if not self.protocol or '读地址' not in self.protocol:
            return {}
        return {
            name: self.state.get(name)
            for name, info in self.protocol['读地址'].items()
            if info.get('分类') == category
        }

    def get_categories(self) -> list:
        """返回 读地址 协议中所有已定义的分类名称（去重，排除 None）"""
        if not self.protocol or '读地址' not in self.protocol:
            return []
        return list({
            info.get('分类')
            for info in self.protocol['读地址'].values()
            if info.get('分类')
        })

    def get_commands(self):
        return self.commands
    

if __name__ == '__main__':
    a = S7_1200()
    a.type = '大空压机'
    a.connect_device("192.168.0.1", 0, 1)
    x = a.plc.db_read(15, 540, 4)
    print(util.get_bool(x, 0, 0))
    # a._get_state()
    # print(a.get_state())


