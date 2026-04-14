"""
古吉設備介接技術文件 V 1.0.2
2019-04-09

環境要求file:///home/john/azuredatastudio-linux-x64
    1. 硬體需求
    a. 內    存：2Gb以上
    b. 硬    碟：500Mb
    2. 軟體需求
    a. 操作系統：Windows系統
    b. .net framework 4.0以上

安裝和設備配置軟體
    1. 安裝包解壓至軟體或其他指定目錄(軟體跟設備交互需要訪問該文件)
使用說明
    一、 軟體啟動
        1. 軟體判斷status.txt、in.txt、out.txt是否存在，存在則刪除然後打開接口程式coinsys.exe
        2. 啟動後該界面會自動隱藏至左下角，可以點擊打開設定可收幣值
        3. 啟動完後軟體需等待并判斷coinsys.exe同級目錄下是否有status.txt文件
            a. 如果有則收鈔系統已啟動
            b. 獲取文件裡面字符串（"Hopper|YES,NV|YES,ND|YES"）
                Hopper:代表是零錢箱後面的YES代表已連接（如果未連接則是NO）
                NV:代表是收鈔機後面的YES代表已連接（如果未連接則是NO）
                ND:代表是找鈔機後面的YES代表已連接（如果未連接則是NO）

    二、 收錢指令說明（具體指令指令表）
        1. 操作需要向coinsys.exe同級目錄下生成in.txt並寫入指令（除設定存量外）
        2. in.txt裡面個是為一串14位字符串前面4為代表指令後面10為指令需要操作的內容
            如：00010000000123（0001代表指令開始收錢，後面則是需要收的金額123元不足10為前面補0）

        3. 在發送收鈔指令後需要定時獲取out.txt文件的值並讀解析裡面字符串獲取當前收到的金額
        4. 獲取到找零和退幣訊息時也需要定時獲取找零狀態和退幣狀態
        5. 設定零錢箱存量則同級目錄下生成set.txt並寫入指令("1|100,5|100,10|100,20|100,50|100")
        6. 設定收鈔機和找鈔機存量則軟體自行寫入coinsys.exe同級目錄下config.xml節點分別是
            a. 收鈔機100對應節點TNV100，500對應節點TNV500，1000對應節點TNV1000
            b. 找鈔機對應是ND100count
        7. 獲取到設定零錢箱時也需要定時獲取設定結果

    三、 送出指令表
        In.txt說明
            指令代碼    指令名稱    指令格式 (長度必須是14為)   指令說明
            0001       開始收鈔    00010000000123           前4位0001代表收鈔 後面10位代表收鈔金額123元不足前面補0
            0002       停止收鈔    00020000000000           在收鈔執行中使用 以0002開頭
            0003       清空錢箱    00030000000000           空閒時操作清空錢箱操作

        set.txt說明
            文件內字符串為"1|100,5|100,10|100,20|100,50|100"
            用英文半角','隔開分別是1元、5元、10元、20元、50元硬幣用英文半角'|'隔開是分別是對應幣值的數量

    四、 接收指令說明
        指令代碼   指令名稱         指令格式 (長度爲11，前三位為狀態碼)   指令說明
        000       操作成功         00000000000                       1. 收鈔找鈔整個流程完成 2. 設定存量成功 3. 零錢箱清空成功
        002       參數出錯         00200000000                       in.txt裡面的指令錯誤
        003       取消付款參數錯誤  00300000000                       in.txt裡面的指令錯誤0
        004       零錢不足         00400000000                       當前設備裡面無法找出該金額（不會找所以不需要判斷找出了多少）
        005       找零失敗         00500000050                       設備出錯等原因出現的找零錯誤或者退幣錯誤，後面8位爲當前已經找出多少不足補0
        006       取消付款         00600000000                       機器停止收錢，等待計算是否找零
        007       設定存量         00700000000                       開始設定零錢箱存量
        008       設定存量失敗      00800000000                       設定存量機器返回失敗
        095       清空失敗         09500000001                       清空失敗最後一位1時為零錢箱設備沒連接、2為清空過程失敗
        096       清空零錢箱中      09600000000                       零錢箱清空中
        097       取消付款並開始退幣 09700000123                       停止收鈔後退幣，後面8位爲退幣金額不足補0
        098       取消付款退幣成功   09800000000                       退幣成功
        099       開始找零         09900000123                       開始找零，後面8位爲當前收到的金額不足補0
        100       收錢中           10000000123                       收錢狀態中，後面8位爲當前收到的金額不足補0

    五、 接讀取存量
        讀取config.xml對應值

        節點名稱     節點說明
        hopper1     零錢箱1元數量（不能自行修改）
        hopper5     零錢箱5元數量（不能自行修改）
        hopper10    零錢箱10元數量（不能自行修改）
        hopper20    零錢箱20元數量（不能自行修改）
        hopper50    零錢箱50元數量（不能自行修改）
        TNV100      收鈔機100元數量（需自行修改數量）
        TNV500      收鈔機500元數量（需自行修改數量）
        TNV1000     收鈔機1000元數量（需自行修改數量）
        ND100count  找鈔機100元數量（需自行修改數量）
"""

import os
import subprocess
import time

from lxml import etree as ET

from libs import number_utils, string_utils

COMMAND = {
    "開始收鈔": "0001",
    "停止收鈔": "00020000000000",
    "清空錢箱": "00030000000000",
}

RESULT = {
    "000": "操作成功",
    "002": "參數錯誤",
    "003": "取消付款參數錯誤",
    "004": "零錢不足",
    "005": "找零失敗",
    "006": "取消付款",
    "007": "設定存量",
    "008": "設定存量失敗",
    "095": "清空失敗",
    "096": "清空零錢箱中",
    "097": "取消付款並開始退幣",
    "098": "取消付款退幣成功",
    "099": "開始找零",
    "100": "收錢中",
}

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))


class CoinSys:
    def __init__(self, system_settings):
        self.system_settings = system_settings
        self.set_current_path()

    def __del__(self):
        pass

    # def set_current_path(self, path=None):
    #     if path is None:
    #         path = CURRENT_DIR

    #     self.COIN_SYS_FILE = os.path.join(path, "coinsys", "coinsys.exe")
    #     self.STATUS_FILE = os.path.join(path, "coinsys", "status.txt")
    #     self.CONFIG_FILE = os.path.join(path, "coinsys", "config.xml")
    #     self.IN_FILE = os.path.join(path, "coinsys", "in.txt")
    #     self.OUT_FILE = os.path.join(path, "coinsys", "out.txt")
    #     self.SET_FILE = os.path.join(path, "coinsys", "set.txt")

    def set_current_path(self, path=None):
        if path is None:
            # 如果 CURRENT_DIR 是 D:\pymedical，
            # 我們就把基礎路徑設為 D:\pymedical\coinsys
            path = os.path.join(CURRENT_DIR, "coinsys")

        # 這裡直接用 path 組合檔名，不要再加 "coinsys" 了
        self.COIN_SYS_FILE = os.path.join(path, "coinsys.exe")
        self.STATUS_FILE = os.path.join(path, "status.txt")
        self.CONFIG_FILE = os.path.join(path, "config.xml")
        self.IN_FILE = os.path.join(path, "in.txt")
        self.OUT_FILE = os.path.join(path, "out.txt")
        self.SET_FILE = os.path.join(path, "set.txt")

    def release_coin_sys(self):
        try:
            self.coin_sys_process.kill()
        except Exception:
            pass

    def clear_parameter_files(self):
        file_list = [self.STATUS_FILE, self.IN_FILE, self.OUT_FILE, self.SET_FILE]
        for file in file_list:
            if os.path.exists(file):
                os.remove(file)

    def clear_in_file(self):
        if os.path.exists(self.IN_FILE):
            os.remove(self.IN_FILE)

    def clear_out_file(self):
        if os.path.exists(self.OUT_FILE):
            os.remove(self.OUT_FILE)

    def startup_coin_sys(self):
        self.coin_sys_process = subprocess.Popen([self.COIN_SYS_FILE])

    def reset_coin_box(self):
        with open(self.IN_FILE, "w") as in_file:
            in_file.write(COMMAND["清空錢箱"])
            in_file.flush()

    def start_payment(self, amount):
        self.clear_out_file()

        with open(self.IN_FILE, "w") as in_file:
            amount_command = (
                f"{COMMAND['開始收鈔']}{number_utils.get_integer(amount):0>10}"
            )
            in_file.write(amount_command)
            in_file.flush()

    def set_coin_amount(self, **kwargs):
        try:
            one = kwargs["one_dollar"]
        except Exception:
            one = 0

        try:
            five = kwargs["five_dollar"]
        except Exception:
            five = 0

        try:
            ten = kwargs["ten_dollar"]
        except Exception:
            ten = 0

        try:
            fifty = kwargs["fifty_dollar"]
        except Exception:
            fifty = 0

        setting_list = f"1|{one},5|{five},10|{ten},20|0,50|{fifty}"

        with open(self.SET_FILE, "w") as set_file:
            set_file.write(setting_list)
            set_file.flush()

    # def set_banknote(self, nd100, tnv100, tnv500, tnv1000):
    def set_banknote(self, nd100, tnv100, tnv1000):
        tree = ET.parse(self.CONFIG_FILE)
        root = tree.getroot()
        root.find("ND100count").text = string_utils.xstr(nd100)
        root.find("TNV100").text = string_utils.xstr(tnv100)
        # root.find('TNV500').text = string_utils.xstr(tnv500)
        root.find("TNV1000").text = string_utils.xstr(tnv1000)

        tree.write(
            self.CONFIG_FILE,
            pretty_print=True,
            xml_declaration=False,
            doctype='<?xml version="1.0" encoding="utf-8"?>',
            encoding="utf-8",
        )

    def get_coin_amount(self):
        print(f"DEBUG: 正在嘗試讀取路徑 -> {os.path.abspath(self.CONFIG_FILE)}")
        tree = ET.parse(self.CONFIG_FILE)
        root = tree.getroot()

        one = number_utils.get_integer(root.find("hopper1").text)
        five = number_utils.get_integer(root.find("hopper5").text)
        ten = number_utils.get_integer(root.find("hopper10").text)
        fifty = number_utils.get_integer(root.find("hopper50").text)

        return one, five, ten, fifty

    def get_banknote_amount(self):
        tree = ET.parse(self.CONFIG_FILE)
        root = tree.getroot()

        nd100 = number_utils.get_integer(root.find("ND100count").text)
        tnv100 = number_utils.get_integer(root.find("TNV100").text)
        # tnv500 = number_utils.get_integer(root.find('TNV500').text)
        tnv1000 = number_utils.get_integer(root.find("TNV1000").text)

        # return nd100, tnv100, tnv500, tnv1000
        return nd100, tnv100, tnv1000

    def get_payment(self):
        try:
            with open(self.OUT_FILE, "r") as out_file:
                line = out_file.readline()

            if line[:3] == "100":
                return number_utils.get_integer(line[3:])
        except Exception:
            return None

    def is_payment_done(self):
        payment_done = False

        try:
            with open(self.OUT_FILE, "r") as out_file:
                line = out_file.readline()

            if line[:3] == "000":
                payment_done = True
        except Exception:
            pass

        return payment_done

    def cancel_payment(self):
        with open(self.IN_FILE, "w") as in_file:
            in_file.write(COMMAND["停止收鈔"])
            in_file.flush()

    def _get_slot_machine_status(self):
        with open(self.STATUS_FILE, "r") as status_file:
            try:
                line = status_file.readlines()[0]
                fields = line.split(",")
                hopper = fields[0].split("|")[1]
                nv = fields[1].split("|")[1]
                # nd = fields[0].split('|')[1]
                nd = fields[2].split("|")[1]
            except Exception:
                return "NO", "NO", "NO"

        return hopper, nv, nd

    def connected(self):
        while True:
            if os.path.exists(self.STATUS_FILE):
                break

        hopper, nv, nd = self._get_slot_machine_status()
        if hopper == "YES" and nv == "YES" and nd == "YES":
            return True

        return False

    def connected(self, timeout=5):
        elapsed = 0
        while not os.path.exists(self.STATUS_FILE) and elapsed < timeout:
            time.sleep(0.1)
            elapsed += 0.1

        if not os.path.exists(self.STATUS_FILE):
            return False

        hopper, nv, nd = self._get_slot_machine_status()
        return hopper == "YES" and nv == "YES" and nd == "YES"
