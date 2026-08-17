"""
收鈔機作業
清除狀態
0.{"command":"machine-clear","parmeter":{"fee":0}}
  {"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},
  "parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1","incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1","outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-clear"}

偵測收鈔狀態
1.{"command":"machine-state","parmeter":{"fee":0}}
  {
      "status": {"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK",
              "outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},
      "parmeter": {"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1",
                "incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1",
                "outcoin4": "1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},
      "command": "machine-state"
   }

提供應付金額
2.{"command":"machine-deduct","parmeter":{"fee":100}}
  {"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},
  "parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1",
  "incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1",
  "outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-deduct"}

交易取消
3.{"command":"machine-stop-deduct","parmeter":{"fee":0}}
  {"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},"parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1","incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1","outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-stop-deduct"}

RESET
4.{"command":"machine-reset","parmeter":{"fee":0}}
  {"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},"parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1","incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1","outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-reset"}

inbillstatus:收鈔機狀態
outbillstatus:吐鈔機狀態
incoinstatus:投幣器狀態
outcoin1status:打幣錢筒1狀態
outcoin2status:打幣錢筒2狀態
outcoin3status:打幣錢筒3狀態
outcoin4status:打幣錢筒4狀態
inbill1000:此次收鈔1000累積數量
inbill500:此次收鈔500累積數量
inbill200:此次收鈔200累積數量
inbill100:此次收鈔100累積數量
outbillA:此次吐鈔機累積數量
incoin50:此次吃幣50元累積數量
incoin10:此次吃幣10元累積數量
incoin5:此次吃幣5元累積數量
incoin1:此次吃幣1元累積數量
outcoin1-4:此次吐幣累積數量
needpay:應付金額
paid:已付金額
needchange:須找零金額
notchange:未找零金額
emsg:doing/finish--代表目前是否正在交易/完成動作

操作流程----
開機時請先開啟程式使此程式常駐
程式開啟時會自行RESET
RESET結束之後會開啟Socket開始並開始監聽Client端的請求
Socket預設IP為127.0.0.1  Port為6389 可於CPAY底下的SETTING.XML修改

client端請先連上之後，

下達指令:
{"command":"machine-clear","parmeter":{"fee":0}}

接著會收到:
{"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},"parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1","incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1","outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-clear"}

收到回應之後請再下指令:
{"command":"machine-reset","parmeter":{"fee":0}}

並收到:
{"status":{"inbillstatus":"OK","outbillstatus":"OK","incoinstatus":"OK","outcoin1status":"OK","outcoin2status":"OK","outcoin3status":"OK","outcoin4status":"OK"},"parmeter":{"inbill1000":"1","inbill500":"1","inbill200":"1","inbill100":"1","outbillA":"1","incoin50":"1","incoin10":"1","incoin5":"1","incoin1":"1","outcoin1":"1","outcoin2":"1","outcoin3":"1","outcoin4":"1","needpay":"100","paid":"100","needchange":"100","notchange":"100","emsg":"ffff"},"command":"machine-reset"}

如果狀態不是 "OK" 或 "N/A" ， 請重新下RESET指令檢查設備是否異常。

正常狀態即可下達指令進行交易:
    順序為 1.清除狀態 2.提供應付金額
    當收到2的回應碼時，即代表開始交易
    交易中可下達 偵測收鈔狀態 指令，以查詢目前收/找鈔狀態
    交易中可下達 交易取消 指令，讓使用者可以取消交易
    當偵測收鈔狀態的emsg由doing變finish 即完成交易

    請查看回應字串是否有未找零金額:
    有未找零金額: 請下 清除狀態 跟 RESET 指令 (在下筆交易前須做此動作否則會有資料不正確的情況發生)

"""

import json
import socket

command = {
    "machine-clear": {  # 清除狀態
        "command": "machine-clear",
        "parmeter": {"fee": 0},
    },
    "machine-state": {  # 偵測收鈔狀態
        "command": "machine-state",
        "parmeter": {"fee": 0},
    },
    "machine-deduct": {  # 提供應付金額
        "command": "machine-deduct",
        "parmeter": {"fee": 0},
    },
    "machine-stop-deduct": {  # 交易取消
        "command": "machine-stop-deduct",
        "parmeter": {"fee": 0},
    },
    "machine-reset": {  # RESET
        "command": "machine-reset",
        "parmeter": {"fee": 0},
    },
}


class CPay:
    def __init__(self, system_settings):
        self.system_settings = system_settings
        self.connected = False
        self._init_socket()

        if not self._connect_socket():
            return

        self._close_socket()

        self.connected = True
        self.machine_clear()
        self.machine_reset()

    def _init_socket(self):
        host = "127.0.0.1"
        port = 6389
        self.server_address = (host, port)

    def _connect_socket(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect(self.server_address)
            connected = True
        except ConnectionRefusedError:
            connected = False

        connected = True
        return connected

    def _close_socket(self):
        self.client.close()

    def set_fee(self, fee):
        self.machine_clear()
        self.machine_deduct(fee)

    def machine_clear(self):
        json_data = json.dumps(command["machine-clear"], ensure_ascii=True)
        self.send_data(json_data, recv_data=True)

    def machine_reset(self):
        json_data = json.dumps(command["machine-reset"], ensure_ascii=True)
        self.send_data(json_data, recv_data=True)

    def machine_state(self):
        json_data = json.dumps(command["machine-state"], ensure_ascii=True)
        status = self.send_data(json_data, recv_data=True)

        return status

    def machine_deduct(self, fee):
        command["machine-deduct"]["parmeter"]["fee"] = fee
        json_data = json.dumps(command["machine-deduct"], ensure_ascii=True)
        self.send_data(json_data, recv_data=True)

    def machine_stop_deduct(self):
        json_data = json.dumps(command["machine-stop-deduct"], ensure_ascii=True)
        self.send_data(json_data, recv_data=False)

    def eject_coin(self):
        command["machine-stop-deduct"]["parmeter"]["needchange"] = 5000
        json_data = json.dumps(command["machine-clear"], ensure_ascii=True)
        self.send_data(json_data, recv_data=True)

    def get_paid(self):
        state = self.machine_state()
        parameter = json.loads(state)["parmeter"]
        paid = parameter["paid"]

        return paid

    def send_data(self, json_data, recv_data=True):
        buffer_size = 1024

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(self.server_address)
        cmd = bytes(json_data, "ascii")
        self.client.sendto(cmd, self.server_address)

        if recv_data:
            received_data, received_address = self.client.recvfrom(buffer_size)
            received_data = str(received_data, "ascii")

            return received_data

    def start_payment(self, total_fee):
        self.set_fee(total_fee)

    def cancel_payment(self):
        self.machine_stop_deduct()

    def is_payment_done(self, total_fee):
        payment_done = False

        try:
            paid = self.get_paid()

            if int(paid) == int(total_fee):
                payment_done = True
        except Exception:
            pass

        return payment_done

    def get_payment(self):
        try:
            paid = self.get_paid()
        except Exception:
            paid = 0

        return int(paid)
