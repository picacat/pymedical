# 叫號燈 2026.09
import socket
import time

from libs import number_utils, system_utils

# ── TCP/IP 叫號燈通訊協定 ──
TCP_OFF_COMMAND = b"\xed\xed\x0f\x0f\x0f\x0f\x7f\x00\x00"
TCP_TIMEOUT = 1  # 秒，避免對方沒開機時卡住畫面

# ── RS-232 叫號燈通訊協定 ──
COM_BAUDRATE = 9600
COM_HEAD = [0x02, 0x31, 0x41, 0x03]
COM_TAIL = [0x03]
COM_OFF_DATA = [0x20, 0x20, 0x20, 0xD5]  # 關掉叫號燈

# (名稱, COM埠欄位, IP欄位, TCP埠欄位, 響鈴欄位)
LED_SETTING_FIELDS = (
    ("叫號燈", "叫號燈連接埠", "叫號燈ip", "叫號燈port", "叫號燈響鈴"),
    ("叫號燈2", "叫號燈連接埠2", "叫號燈ip2", "叫號燈port2", "叫號燈響鈴2"),
)

_checksum_list = None  # 第一次用到才建，之後重複使用


class ComLedDevice:
    """RS-232 介面的叫號燈"""

    def __init__(self, name, com_port):
        self.name = f"{name}(COM{com_port})"
        self.com_port = com_port

    def call(self, regist_no):
        _send_com_port(self.com_port, regist_no)

    def turn_off(self):
        _send_com_port(self.com_port, 0)


class TcpLedDevice:
    """TCP/IP 介面的叫號燈"""

    def __init__(self, name, ip, tcp_port, ring_bell):
        self.name = f"{name}({ip})"
        self.ip = ip
        self.tcp_port = number_utils.get_integer(tcp_port)
        self.ring_bell = ring_bell == "Y"

    def call(self, regist_no):
        _send_tcpip(self.ip, self.tcp_port, self._call_command(regist_no))

    def turn_off(self):
        _send_tcpip(self.ip, self.tcp_port, TCP_OFF_COMMAND)

    def _call_command(self, regist_no):
        digits = f"{number_utils.get_integer(regist_no):0>3}"[-3:]
        head = [0x6D, 0x6D, 0x00]
        tail = [0x01, 0x01 if self.ring_bell else 0x00, 0x00]
        return bytes(head + [int(d) for d in digits] + tail)


def get_led_devices(system_settings):
    """讀取系統設定，每個有設定的介面各算一台叫號燈"""
    devices = []
    for name, com_field, ip_field, port_field, bell_field in LED_SETTING_FIELDS:
        com_port = system_settings.field(com_field)
        if number_utils.get_integer(com_port) > 0:
            devices.append(ComLedDevice(name, com_port))

        ip = system_settings.field(ip_field)
        if ip not in [None, ""]:
            devices.append(
                TcpLedDevice(
                    name,
                    ip,
                    system_settings.field(port_field),
                    system_settings.field(bell_field),
                )
            )
    return devices


def call_all(devices, regist_no):
    for device in devices:
        try:
            device.call(regist_no)
        except Exception as e:
            system_utils.loggin_error(
                "system_errors.log", f"{device.name}叫號失敗: {e}"
            )


def turn_off_all(devices):
    for device in devices:
        try:
            device.turn_off()
        except Exception as e:
            system_utils.loggin_error(
                "system_errors.log", f"關閉{device.name}失敗: {e}"
            )


# ── 以下為底層傳送，原本放在 system_utils ──
def _send_tcpip(ip, tcp_port, data):
    with socket.create_connection((ip, tcp_port), timeout=TCP_TIMEOUT) as client:
        client.sendall(data)


def _send_com_port(com_port, regist_no):
    # baud=9600 parity=n data=8 stop=1
    import serial

    com = serial.Serial()
    com.port = f"COM{com_port}"
    com.baudrate = COM_BAUDRATE
    com.parity = serial.PARITY_NONE
    com.bytesize = serial.EIGHTBITS
    com.stopbits = serial.STOPBITS_ONE
    com.timeout = 0.5  # non-block read 0.5s
    com.writeTimeout = 0.5  # timeout for write 0.5s
    com.xonxoff = False  # disable software flow control
    com.rtscts = False  # disable hardware (RTS/CTS) flow control
    com.dsrdtr = False  # disable hardware (DSR/DTR) flow control

    com.open()  # 開不起來就讓例外往外拋，由 call_all 寫進 log
    try:
        com.flushInput()
        com.flushOutput()
        com.write(serial.to_bytes(_get_com_data(regist_no)))
        time.sleep(0.5)
    finally:
        com.close()


def _get_com_data(regist_no):
    regist_no = number_utils.get_integer(regist_no)
    if regist_no == 0:
        return COM_HEAD + COM_OFF_DATA + COM_TAIL

    regist_no_hex = []
    for i in f"{regist_no: >3}"[::-1]:
        if i == " ":
            regist_no_hex.append(0x3F)
        else:
            regist_no_hex.append(0x30 + int(i))

    return COM_HEAD + regist_no_hex + [_get_checksum(regist_no)] + COM_TAIL


def _get_checksum(regist_no):
    global _checksum_list

    if _checksum_list is None:
        _checksum_list = _build_checksum_list()

    return _checksum_list[regist_no]


def _build_checksum_list():
    checksum_list = [None]
    for i in range(9):  # 1-9 start: 0x24
        checksum_list.append(0x24 + i)
    for i in range(1, 10):  # 10-99 start: 0x15
        for j in range(10):
            checksum_list.append(0x15 + (j - 1) + i)
    for i in range(10):  # 100-109 start: 0x06
        checksum_list.append(0x06 + i)
    for i in range(1, 37):  # 110-469 start: 0x07
        for j in range(10):
            checksum_list.append(0x07 + ((i - 1) % 9) + j)
    for i in range(1, 4):  # 470-499 start: 0x10
        for j in range(10):
            checksum_list.append(0x10 + ((i - 1) % 9) + j)
    for i in range(1, 28):  # 500-769 start: 0x0a
        for j in range(10):
            checksum_list.append(0x10 + ((i - 1) % 9) + j)
    for i in range(1, 4):  # 770-799 start: 0x13
        for j in range(10):
            checksum_list.append(0x13 + ((i - 1) % 9) + j)
    for i in range(1, 10):  # 800-889 start: 0x0d
        for j in range(10):
            checksum_list.append(0x0D + ((i - 1) % 9) + j)
    for i in range(10):  # 890-899 start: 0x16
        checksum_list.append(0x16 + i)
    for i in range(1, 10):  # 900-989 start: 0x0e
        for j in range(10):
            checksum_list.append(0x0E + ((i - 1) % 9) + j)
    for i in range(10):  # 990-999 start: 0x17
        checksum_list.append(0x17 + i)

    return checksum_list
