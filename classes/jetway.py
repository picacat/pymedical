import time
import serial
import json
import os

# Configuration for machines
MACHINE_CONFIGS = {
    'BILL_IN_MACHINE': {
        'port': 'COM1',
        'baudrate': 9600,
        'parity': serial.PARITY_EVEN,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'COIN_IN_MACHINE': {
        'port': 'COM2',
        'baudrate': 9600,
        'parity': serial.PARITY_NONE,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'BILL_OUT_100_MACHINE': {
        'port': 'COM3',
        'baudrate': 9600,
        'parity': serial.PARITY_NONE,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'COIN_OUT_50_MACHINE': {
        'port': 'COM4',
        'baudrate': 9600,
        'parity': serial.PARITY_EVEN,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'COIN_OUT_10_MACHINE': {
        'port': 'COM5',
        'baudrate': 9600,
        'parity': serial.PARITY_EVEN,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'COIN_OUT_5_MACHINE': {
        'port': 'COM6',
        'baudrate': 9600,
        'parity': serial.PARITY_EVEN,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'COIN_OUT_1_MACHINE': {
        'port': 'COM7',
        'baudrate': 9600,
        'parity': serial.PARITY_EVEN,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
    'KIOSK_PC': {
        'port': 'COM2',
        'baudrate': 9600,
        'parity': serial.PARITY_NONE,
        'bytesize': serial.EIGHTBITS,
        'stopbits': serial.STOPBITS_ONE,
    },
}


class Jetway:
    COUNT_FILE = 'kiosk_count_data.json'

    def __init__(self, system_settings):
        self.system_settings = system_settings
        self.serial_connection = self._setup_serial('KIOSK_PC')

        if self.serial_connection:
            self._disable_cash_in_machine()
            self.connected = True
        else:
            self.connected = False

    def __del__(self):
        try:
            self.close_serial()
        except Exception:
            pass

    def _disable_cash_in_machine(self):
        self.open_cash_in_machine()
        self.close_cash_in_machine()

    def is_connected(self):
        return self.connected

    def _get_checksum(self, data):
        """Calculate the checksum for a list of data bytes."""
        return (sum(data) & 0xFF) ^ 0x5A

    def _setup_serial(self, machine_name):
        """動態設定設備序列連接"""
        if machine_name not in MACHINE_CONFIGS:
            print(f'無效的設備名稱：{machine_name}')
            return None

        config = MACHINE_CONFIGS[machine_name]
        try:
            ser = serial.Serial(
                port=config['port'],
                baudrate=config['baudrate'],
                parity=config['parity'],
                bytesize=config['bytesize'],
                stopbits=config['stopbits'],
                timeout=1
            )
            return ser
        except serial.SerialException as e:
            print(f'無法開啟 {machine_name} 的序列端口: {e}')
            return None

    def close_serial(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def open_cash_in_machine(self):
        return self._toggle_cash_in_machine(0x11)

    def close_cash_in_machine(self):
        return self._toggle_cash_in_machine(0x00)

    def _toggle_cash_in_machine(self, command):
        ser = self.serial_connection
        if not ser:
            print("Serial connection not established.")
            return False

        data = [0xA5, 0x03, 0xF4, command]
        checksum = self._get_checksum(data)
        data.append(checksum)
        send_data = bytearray(data)

        try:
            ser.write(send_data)
            received_data = ser.read(5)
            if received_data:
                return received_data[3] == 0x00
        except serial.SerialException as e:
            print(f'Error sending data: {e}')

        return False

    def reset_coin_out_machine(self, coin_type):
        coin_types = {50: 0x01, 10: 0x02, 5: 0x03, 1: 0x04}
        if coin_type not in coin_types:
            return False

        ser = self.serial_connection
        if not ser:
            print("Serial connection not established.")
            return False

        data = [0xA5, 0x03, 0xF5, coin_types[coin_type]]
        checksum = self._get_checksum(data)
        data.append(checksum)
        send_data = bytearray(data)

        try:
            ser.write(send_data)
            received_data = ser.read(5)
            if received_data:
                return received_data[3] == 0x00
        except serial.SerialException as e:
            print(f'Error sending data: {e}')

        return False

    def clear_coin_out_machine(self, coin_type):
        coin_types = {50: 0x01, 10: 0x02, 5: 0x03, 1: 0x04}
        if coin_type not in coin_types:
            return False

        ser = self.serial_connection
        if not ser:
            print("Serial connection not established.")
            return False

        data = [0xA5, 0x03, 0xF2, coin_types[coin_type]]
        checksum = self._get_checksum(data)
        data.append(checksum)
        send_data = bytearray(data)

        try:
            ser.write(send_data)
            received_data = ser.read(5)
            if received_data:
                return received_data[3] == 0x00
        except serial.SerialException as e:
            print(f'Error sending data: {e}')

        return False

    def charge_cash(self, total_amount, update_display, stop_event):
        if not self.open_cash_in_machine():
            print("Failed to open cash-in machine.")
            return

        ser = self.serial_connection
        if not ser:
            print("Serial connection not established.")
            return

        data = [0xA5, 0x02, 0xF0]
        checksum = self._get_checksum(data)
        data.append(checksum)
        send_data = bytearray(data)
        receipt_total = 0

        try:
            while not stop_event.is_set():
                ser.write(send_data)
                if ser.in_waiting > 0:
                    received_data = ser.read(10)
                    if received_data:
                        s1 = received_data[3]
                        if s1 == 0x01:
                            receipt_total += 1
                        elif s1 == 0x02:
                            receipt_total += 5
                        elif s1 == 0x03:
                            receipt_total += 10
                        elif s1 == 0x04:
                            receipt_total += 50
                        elif s1 == 0x40:
                            receipt_total += 100
                        elif s1 == 0x41:
                            receipt_total += 200
                        elif s1 == 0x42:
                            receipt_total += 500
                        elif s1 == 0x43:
                            receipt_total += 1000

                time.sleep(0.2)
                current_total = int(receipt_total)
                update_display.emit(current_total)  # 發送信號更新金額

                if current_total >= int(total_amount):
                    break
        except Exception as e:
            print(f'Exception occurred: {e}')
        # finally:
        #     self.close_cash_in_machine()

    def calculate_change(self, amount):
        bill_100 = amount // 100
        amount %= 100

        coin_50 = amount // 50
        amount %= 50

        coin_10 = amount // 10
        amount %= 10

        coin_5 = amount // 5
        amount %= 5

        coin_1 = amount
        self.give_change(coin_50=coin_50, coin_10=coin_10, coin_5=coin_5, coin_1=coin_1, bill_100=bill_100)

    def give_change(self, coin_50=0, coin_10=0, coin_5=0, coin_1=0, bill_100=0):
        if not self.open_cash_in_machine():
            print("Failed to open cash-in machine.")
            return ['Failed to open serial port']

        ser = self.serial_connection
        if not ser:
            print("Serial connection not established.")
            return ['Failed to open serial port']

        data = [0xA5, 0x07, 0xF1, coin_50, coin_10, coin_5, coin_1, bill_100]
        checksum = self._get_checksum(data)
        data.append(checksum)
        send_data = bytearray(data)

        try:
            ser.write(send_data)
            received_data = ser.read(5)
            if received_data:
                s1 = received_data[3]
                errors = []
                if coin_50 and s1 & 0x01:
                    errors.append('Coin 50 eject failed')
                if coin_10 and s1 & 0x02:
                    errors.append('Coin 10 eject failed')
                if coin_5 and s1 & 0x04:
                    errors.append('Coin 5 eject failed')
                if coin_1 and s1 & 0x08:
                    errors.append('Coin 1 eject failed')
                if bill_100 and s1 & 0x10:
                    errors.append('Bill 100 eject failed')

                # 重點：如果沒有錯誤，或者你想只要發送了指令就扣庫存，在這裡呼叫
                if not errors:
                    self._update_inventory(bill_100, coin_50, coin_10, coin_5, coin_1)

                return errors
        except serial.SerialException as e:
            return [f'Serial exception occurred: {e}']
        finally:
            self.close_cash_in_machine()

    def _update_inventory(self, bill_100, coin_50, coin_10, coin_5, coin_1):
        """讀取 JSON，扣除找出的數量，並寫回檔案"""
        if not os.path.exists(self.COUNT_FILE):
            return  # 如果檔案不存在，無法扣除

        try:
            # 1. 讀取現有庫存
            with open(self.COUNT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 2. 扣除數量 (確保不低於 0，或者允許負數作為異常記錄，這裡設為允許負數以便追蹤誤差)
            if "100_bill" in data:
                data["100_bill"] -= bill_100
            if "50_coin" in data:
                data["50_coin"] -= coin_50
            if "10_coin" in data:
                data["10_coin"] -= coin_10
            # 如果你的 JSON 之後有擴充 5元和1元，也可以在這裡扣除
            # if "5_coin" in data: data["5_coin"] -= coin_5
            # if "1_coin" in data: data["1_coin"] -= coin_1

            # 3. 寫回檔案
            with open(self.COUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"更新庫存失敗: {e}")

    def eject_cash(self, amount):
        self.calculate_change(amount)
