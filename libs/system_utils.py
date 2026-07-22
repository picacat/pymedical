# 元件設定 2017.09.26

# -*- coding: UTF-8 -*-
import base64
import configparser
import datetime
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
from os import listdir
from pathlib import Path

import requests
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QDate, QEvent, QObject, QSettings, QStandardPaths
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)

if sys.platform == "win32":
    os.environ["PYTHON_VLC_MODULE_PATH"] = "./vlc"

import json
import logging
from io import BytesIO

from libs import dialog_utils, nhi_utils, number_utils, ui_utils

PY_MEDICAL_JSON_FILE = "pymedical.json"
COMPLICATED_TREATMENT_DISEASE_FILE = "complicated_treatment_disease.json"


class CalendarPopupFixer(QObject):
    """QDateEdit 值為哨兵日期(1900/1/1)時，月曆彈窗改顯示今天的月份"""

    def __init__(self, date_edit, empty_date=QDate(1900, 1, 1)):
        super().__init__(date_edit)  # parent 設為 date_edit，生命週期跟著它
        self.date_edit = date_edit
        self.empty_date = empty_date
        date_edit.calendarWidget().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:
            if self.date_edit.date() == self.empty_date:
                today = QDate.currentDate()
                calendar = self.date_edit.calendarWidget()
                calendar.setCurrentPage(today.year(), today.month())
        return False  # 事件照常傳遞，只是順手撥頁面


def install_pycaw():
    try:
        # 嘗試導入 pycaw，如果未安裝則安裝
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    except ImportError:
        print("未找到 pycaw 套件，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pycaw"])
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume  # 安裝後重新導入
    return AudioUtilities, ISimpleAudioVolume


# 取得醫療系統版本資訊
def get_system_version():
    version_file = "version.txt"
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    try:
        file_date = get_file_date("pymedical.zip")
    except FileNotFoundError:
        file_date = get_file_date("pymedical.py")

    version = f"PyMed{file_date}"

    return version


def get_file_date(filename, created_date=None):
    if created_date:
        time_stamp = os.stat(filename).st_ctime
    else:
        time_stamp = os.stat(filename).st_mtime

    file_date = datetime.datetime.fromtimestamp(time_stamp).strftime("%Y%m%d")

    return file_date


def get_mariadb_version(database):
    rows = database.select_record("SELECT VERSION() AS version")
    version = rows[0]["version"]
    if "MariaDB" in version:
        version = "MariaDB"
    else:
        version = "MySQL"

    return version


def get_mariadb_dump(version):
    if sys.platform == "win32":
        if version == "MariaDB":
            backup_cmd = "mysqldump.exe"
        else:
            backup_cmd = "mysqldump50.exe"
    else:
        backup_cmd = "mysqldump"

    return backup_cmd


def get_mysql_dump():
    if sys.platform == "win32":
        backup_cmd = "mysqldump50.exe"
    else:
        backup_cmd = "mysqldump"

    return backup_cmd


def get_restore_cmd():
    if sys.platform == "win32":
        restore_cmd = "mysql.exe"
    else:
        restore_cmd = "mysql"

    return restore_cmd


def dump_database(database, backup_path, dump_filename=None, exclude_tables=None):
    config = configparser.ConfigParser()
    config.read(database.CONFIG_FILE)

    host_name = config["db"]["host"]
    user_name = config["db"]["user"]
    password = config["db"]["password"]
    database_name = config["db"]["database"]

    if dump_filename is None:
        dump_filename = os.path.join(backup_path, f"{database_name}.sql")

    # 確保備份路徑存在
    os.makedirs(backup_path, exist_ok=True)

    # 構建 mysqldump 指令
    version = get_mariadb_version(database)
    mariadb_dump_cmd = [
        get_mariadb_dump(version),
        f"--host={host_name}",
        f"--user={user_name}",
        f"--password={password}",
        "--skip-lock-tables",
        "--complete-insert",
        database_name,
    ]

    # 如果有排除的表格，加入 --ignore-table 參數
    if exclude_tables:
        for table in exclude_tables:
            mariadb_dump_cmd.append(f"--ignore-table={database_name}.{table}")

    try:
        with open(dump_filename, "w") as f:
            subprocess.run(
                mariadb_dump_cmd, stdout=f, stderr=subprocess.PIPE, check=True
            )

        print(f"✅ 資料庫 {database_name} 備份完成: {dump_filename}")
        zip_filename = dump_filename.replace(".sql", ".zip")
        zip_file(zip_filename, dump_filename, backup_path)

        return 0  # 成功時返回 0

    except subprocess.CalledProcessError as e:
        print(f"❌ 資料庫備份失敗: {e.stderr.decode()}")
        return e.returncode  # 返回錯誤代碼


def import_database(database, restore_filename):
    config = configparser.ConfigParser()
    config.read(database.CONFIG_FILE)

    host = config["db"]["host"]
    user_name = config["db"]["user"]
    password = config["db"]["password"]
    database = config["db"]["database"]
    charset = "--default-character-set=utf8"

    restore_cmd = get_restore_cmd()
    dump_cmd = f"""
        {restore_cmd} {charset} --host={host} --user={user_name} --password={password} {database} < {restore_filename}
    """

    err_no = os.system(dump_cmd)

    return err_no


def dump_table(
    database, version, backup_path, in_filename, where_script=None, use_docker=False
):
    config = configparser.ConfigParser()
    config.read(database.CONFIG_FILE)

    host_name = config["db"]["host"]
    user_name = config["db"]["user"]
    password = config["db"]["password"]
    database_name = config["db"]["database"]

    dump_file = os.path.join(backup_path, in_filename)
    table_name = in_filename.split(".")[0]

    # 判斷是否使用 WHERE 限制
    if where_script:
        where_clause = f'--where="{where_script}"'
        extra_opts = ["--no-create-info"]  # 只導出資料
    else:
        where_clause = ""
        extra_opts = []

    # ✅ 查詢這張表的 ENGINE 類型（InnoDB 或 MyISAM）
    engine_sql = f"""
        SELECT ENGINE FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{database_name}' AND TABLE_NAME = '{table_name}'
    """
    engine_rows = database.select_record(engine_sql)
    engine_type = engine_rows[0]["ENGINE"] if engine_rows else ""

    # ✅ 若是 InnoDB，加入 --single-transaction，避免鎖表且確保一致性
    extra_flags = []
    if engine_type.upper() == "INNODB":
        extra_flags.extend(["--single-transaction", "--skip-lock-tables"])

    # ✅ 組裝 mysqldump 指令
    if use_docker:
        mariadb_dump_cmd = [
            "docker",
            "exec",
            "-it",
            "mariadb-db-service",
            "mariadb-dump",
            f"--host={host_name}",
            f"--user={user_name}",
            f"--password={password}",
            where_clause,
            "--skip-extended-insert",
            "--compress",
            *extra_opts,
            *extra_flags,
            database_name,
            table_name,
        ]
    else:
        mariadb_dump_cmd = [
            get_mariadb_dump(version),
            f"--host={host_name}",
            f"--user={user_name}",
            f"--password={password}",
            where_clause,
            "--skip-extended-insert",
            "--compress",
            *extra_opts,
            *extra_flags,
            database_name,
            table_name,
        ]

    args = [arg for arg in mariadb_dump_cmd if arg]  # 過濾空白參數

    # ✅ 執行備份
    with open(dump_file, "w") as f:
        try:
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                subprocess.run(
                    args,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    check=True,
                )
            else:
                subprocess.run(args, stdout=f, stderr=subprocess.PIPE, check=True)

            print(f"✅ 資料表 {table_name} 備份完成: {dump_file}")

        except subprocess.CalledProcessError as e:
            print("❌ 備份失敗，指令如下：")
            print(" ".join(args))
            print("🔴 stderr 錯誤訊息：", e.stderr.decode("utf-8"))
            raise RuntimeError(f"資料表 {table_name} 備份失敗，錯誤: {e}")


def pip3_install(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except Exception as e:
        print(f"【警告】自動安裝套件 {package} 失敗：{e}")
        return False


def pip3_uninstall(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", package])
    except Exception:
        pass


if sys.platform == "win32":
    import win32api
    import win32gui
    from win32con import WM_INPUTLANGCHANGEREQUEST


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))
CSS_PATH = "css"


def center_window(window):
    frame_geometry = window.frameGeometry()
    center_point = QtWidgets.QDesktopWidget().availableGeometry().center()
    frame_geometry.moveCenter(center_point)
    window.move(frame_geometry.topLeft())


def get_ip():
    ip = "無網路連線"
    try:
        # 嘗試從所有網路介面中獲取 IP 地址
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # 這個 IP 地址是無效的，但會觸發系統選擇合適的本地 IP 地址
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
        except Exception:
            pass
        finally:
            s.close()
    except Exception as e:
        print(f"Error getting IP: {e}")

    return ip


def get_font(system_settings=None):
    if sys.platform == "win32":
        font = "Microsoft JhengHei"
        if system_settings is not None:
            print_font = system_settings.field("列印預設字體")
            if print_font not in ["", None]:
                font = print_font
    else:
        font = "Noto Sans"

    return font


def set_login_image(widget, system_settings):
    image_file = "login_blue.jpg"

    if system_settings.field("外觀顏色") == "紅色":
        image_file = "login_red.jpg"
    elif system_settings.field("外觀顏色") == "綠色":
        image_file = "login_green.jpg"
    elif system_settings.field("外觀顏色") == "藍色":
        image_file = "login_blue.jpg"
    elif system_settings.field("外觀顏色") == "灰色":
        image_file = "login_gray.jpg"
    else:
        image_file = "login_gray.jpg"

    style = f"""
        QDialog#Dialog_login
        {{background-image: url(./images/{image_file});}}
    """
    widget.setStyleSheet(style)


def set_background_image(widget, system_settings):
    image_file = "home_blue.jpg"

    if system_settings.field("外觀顏色") == "紅色":
        image_file = "home_red.jpg"
    elif system_settings.field("外觀顏色") == "綠色":
        image_file = "home_green.jpg"
    elif system_settings.field("外觀顏色") == "藍色":
        image_file = "home_blue.jpg"
    elif system_settings.field("外觀顏色") == "灰色":
        image_file = "home_gray.jpg"

    style = f"""
        QWidget#tab_home
        {{background-image: url(./images/{image_file});}}
    """
    widget.setStyleSheet(style)


def set_css(widget, system_settings):
    css_file = os.path.join(BASE_DIR, CSS_PATH, get_css_file(system_settings))

    widget.setStyleSheet(open(css_file, "r", encoding="utf-8").read())


def get_css_file(system_settings):
    css_file = "style"

    if system_settings.field("外觀顏色") == "紅色":
        css_file += ".red"
    elif system_settings.field("外觀顏色") == "綠色":
        css_file += ".green"
    elif system_settings.field("外觀顏色") == "藍色":
        css_file += ".blue"
    elif system_settings.field("外觀顏色") == "灰色":
        css_file += ".gray"
    elif system_settings.field("外觀顏色") == "自訂1":
        css_file += ".custom1"

    if sys.platform == "win32":
        css_file += ".win32"

    css_file += ".css"

    return css_file


# 設定主題
def set_theme(ui, system_settings):
    style = system_settings.field("外觀主題")
    if style is None:
        style = "Fusion"

    ui.setStyle(QtWidgets.QStyleFactory.create(style))


def show_message_box(message_icon, title, text, informative, button_text="確定"):
    msg_box = QMessageBox()
    msg_box.setWindowFlags(QtCore.Qt.Dialog)
    msg_box.setIcon(message_icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setInformativeText(informative)
    msg_box.addButton(QPushButton(button_text), QMessageBox.YesRole)
    msg_box.exec_()


def show_message(text):
    msg_box = QMessageBox()
    msg_box.setWindowFlags(QtCore.Qt.Dialog)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("系統測試")
    msg_box.setText(text)
    msg_box.setInformativeText("系統測試")
    msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
    msg_box.exec_()


def set_keyboard_layout(lang):
    if sys.platform != "win32":
        return

    chinese = 0x0404
    english = 0x0409

    if lang == "中文":
        keyboard = chinese
    else:
        keyboard = english

    hwnd = win32gui.GetForegroundWindow()

    win32api.SendMessage(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, keyboard)


def unzip_file(zip_file, output_directory):
    if sys.platform == "darwin":
        cmd = f"unzip {zip_file} -d {output_directory}"
        os.system(cmd)
    else:
        cmd = ["7z", "x", zip_file, f"-o{output_directory}"]
        sp = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        sp.communicate()


def zip_file(zip_file, source_file, output_directory):
    source_file = os.path.join(output_directory, source_file)
    zip_file = os.path.join(output_directory, zip_file)

    cmd = ["7z", "a", "-tzip", zip_file, source_file, f"-o{output_directory}"]

    if platform.system() == "Windows":
        # 隱藏 CMD 視窗的方法
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE  # 隱藏 CMD 視窗
        sp = subprocess.Popen(
            cmd,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            startupinfo=startupinfo,
        )
    else:
        sp = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sp.communicate()

    os.remove(source_file)


def get_host_ip():
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


def set_widget_image(widget, image_file):
    style_sheet = f"""
        QWidget {{
            background-image: url({image_file});
            background-repeat: none;
            background-position: center;
        }}
        QPushButton {{
            color: rgb(255, 0, 0);
            font: 10pt;
        }}
    """
    widget.setStyleSheet(style_sheet)


def set_combo_box_item(combo_box, item_text):
    item_exists = False
    for i in range(combo_box.count()):
        if combo_box.itemText(i) == item_text:
            item_exists = True
            break

    if not item_exists:
        combo_box.insertItem(1, item_text)

    combo_box.setCurrentText(item_text)


def loggin_error(filename, error_message):
    if os.path.exists(filename):
        file_mode = "a"
    else:
        file_mode = "w"

    logging.basicConfig(
        level=logging.INFO,
        filename=filename,
        filemode=file_mode,
        format="[%(asctime)s %(levelname)s]\n%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.error(error_message)


def send_telegram_alert(json_data, mail_content):
    # --- 步驟 1: 配置您的 Token 和 Chat ID ---
    BOT_TOKEN = "8235563099:AAFBSEhk0BgQFRUjsH87iO38Gn70ZGo1GMI"
    CHAT_ID = "7646915984"

    # --- 步驟 2: 組織訊息內容 ---

    # 建立 Markdown 格式的訊息，更清晰
    subject = f"{json_data['院所名稱']} - {json_data['使用者']} pymedical 錯誤"

    # 使用 Markdown 格式加粗標題和換行
    text_message = (
        f"🚨 **PyMedical 系統警報** 🚨\n\n"
        f"**主旨：** {subject}\n"
        f"**詳細錯誤：**\n"
        f"```\n{mail_content}\n```"  # 使用三引號讓錯誤訊息格式化
    )

    # URL 編碼訊息內容，確保特殊字符不會破壞 URL
    encoded_text = urllib.parse.quote_plus(text_message)

    # Telegram API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # --- 步驟 3: 發送 HTTP 請求 ---
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": text_message,
            "parse_mode": "Markdown",  # 告訴 Telegram 啟用 Markdown 格式
        }

        response = requests.post(url, data=payload)
        response.raise_for_status()  # 檢查是否有 HTTP 錯誤 (例如 404, 500)

        # 檢查 Telegram API 是否回傳成功
        if response.json().get("ok"):
            print("Telegram 訊息發送成功。")
        else:
            print(f"Telegram API 錯誤: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"發送 Telegram 訊息時發生連線或 HTTP 錯誤: {e}")


def write_loggin_info(clinic_name, user_name, position):
    clinic_info = {
        "院所名稱": clinic_name,
        "使用者": user_name,
        "職稱": position,
    }
    with open(PY_MEDICAL_JSON_FILE, "w") as f:
        json.dump(clinic_info, f)


def read_loggin_info(field):
    json_file = open(PY_MEDICAL_JSON_FILE)
    json_data = json.load(json_file)
    json_file.close()

    return json_data[field]


def write_user_info(clinic_name, station_no, user_name):
    clinic_info = {
        "院所名稱": clinic_name,
        "使用者": user_name,
    }
    filename = f"{clinic_name}{station_no}.json"
    with open(filename, "w") as f:
        json.dump(clinic_info, f)


def get_user_name(system_settings):
    json_file = (
        f"{system_settings.field('院所名稱')}{system_settings.field('工作站編號')}.json"
    )

    try:
        json_file = open(json_file)
    except FileNotFoundError:
        return system_settings.field("使用者")

    json_data = json.load(json_file)
    json_file.close()

    user_name = json_data["使用者"]

    return user_name


def remove_user_info(system_settings):
    # try:
    #     json_file = f"{system_settings.field('院所名稱')}{system_settings.field('工作站編號')}.json"
    #     os.remove(json_file)
    # except Exception:
    #     pass

    source_dir = os.getcwd()
    source_files = [
        f for f in listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))
    ]
    for file in source_files:
        if "衝突的複本" in file:
            try:
                os.remove(file)
            except Exception:
                pass

        if "中醫診所" in file:
            try:
                os.remove(file)
            except Exception:
                pass

        if "conflicted copy" in file:
            try:
                os.remove(file)
            except Exception:
                pass

    icon_dir = os.path.join(source_dir, "icons")
    icon_files = [
        f for f in listdir(icon_dir) if os.path.isfile(os.path.join(icon_dir, f))
    ]
    for file in icon_files:
        if "衝突的複本" in file:
            try:
                os.remove(os.path.join(icon_dir, file))
            except Exception:
                pass


def get_qrcode_from_file(parent):
    import cv2

    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    filename, _ = QFileDialog.getOpenFileName(
        parent, "讀取QRCode檔", "../", "圖形檔 (*.png *.jpg)", options=options
    )
    if not filename:
        return

    image = cv2.imread(filename)
    detector = cv2.QRCodeDetector()
    qrcode, vertices_array, binary_qrcode = detector.detectAndDecode(image)

    if vertices_array is None:
        return None
    else:
        return qrcode


# 'baud=9600 parity=n data=8 stop=1';
def send_to_com_port(com_port, regist_no):

    import serial

    com = serial.Serial()
    com.port = f"COM{com_port}"
    com.baudrate = 9600
    com.parity = serial.PARITY_NONE
    com.bytesize = serial.EIGHTBITS
    com.stopbits = serial.STOPBITS_ONE

    com.timeout = 0.5  # non-block read 0.5s
    com.writeTimeout = 0.5  # timeout for write 0.5s
    com.xonxoff = False  # disable software flow control
    com.rtscts = False  # disable hardware (RTS/CTS) flow control
    com.dsrdtr = False  # disable hardware (DSR/DTR) flow control

    try:
        com.open()
    except Exception:
        return

    if not com.isOpen():
        return

    head = [0x02, 0x31, 0x41, 0x03]
    tail = [0x03]

    regist_no = number_utils.get_integer(regist_no)
    if number_utils.get_integer(regist_no) == 0:
        regist_no_hex = [0x20, 0x20, 0x20, 0xD5]  # 關掉led燈
        data_list = head + regist_no_hex + tail
    else:
        regist_no_str = f"{regist_no: >3}"
        regist_no_str = regist_no_str[::-1]
        regist_no_hex = []
        for i in regist_no_str:
            if i == " ":
                regist_no_hex.append(0x3F)
            else:
                regist_no_hex.append(0x30 + int(i))

        checksum_list = get_checksum_list()
        data_list = head + regist_no_hex + [checksum_list[regist_no]] + tail

    try:
        com.flushInput()
        com.flushOutput()
        com.write(serial.to_bytes(data_list))
        time.sleep(0.5)
        com.close()
    except Exception:
        pass


def get_checksum_list():
    checksum_list = [None]
    for i in range(0, 9):  # 1-9 start: 0x24
        checksum_list.append(0x24 + i)

    for i in range(1, 10):  # 10-99 start: 0x15
        for j in range(0, 10):
            checksum_list.append(0x15 + (j - 1) + i)

    for i in range(0, 10):  # 100-109 start: 0x06
        checksum_list.append(0x06 + i)

    for i in range(1, 37):  # 110-469 start: 0x07
        for j in range(0, 10):
            checksum_list.append(0x07 + ((i - 1) % 9) + j)

    for i in range(1, 4):  # 470-499 start: 0x10
        for j in range(0, 10):
            checksum_list.append(0x10 + ((i - 1) % 9) + j)

    for i in range(1, 28):  # 500-769 start: 0x0a
        for j in range(0, 10):
            checksum_list.append(0x10 + ((i - 1) % 9) + j)

    for i in range(1, 4):  # 770-799 start: 0x13
        for j in range(0, 10):
            checksum_list.append(0x13 + ((i - 1) % 9) + j)

    for i in range(1, 10):  # 800-889 start: 0x0d
        for j in range(0, 10):
            checksum_list.append(0x0D + ((i - 1) % 9) + j)

    for i in range(0, 10):  # 890-899 start: 0x16
        checksum_list.append(0x16 + i)

    for i in range(1, 10):  # 900-989 start: 0x0e
        for j in range(0, 10):
            checksum_list.append(0x0E + ((i - 1) % 9) + j)

    for i in range(0, 10):  # 990-999 start: 0x17
        checksum_list.append(0x17 + i)

    return checksum_list


# 傳送資料到tcpip
def send_to_tcpip(target_ip, target_port, data):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((target_ip, target_port))
    client_socket.sendall(data)


def set_combo_box_treat_type(combobox_treat_type, start_date=None):
    treat_type_list = nhi_utils.get_treat_type_list(start_date)
    color_list = []
    for treat_type in treat_type_list:
        if treat_type in nhi_utils.ACUPUNCTURE_TREAT:
            color = QtGui.QBrush(QtCore.Qt.darkMagenta)
        elif treat_type in nhi_utils.MASSAGE_TREAT:
            color = QtGui.QBrush(QtCore.Qt.darkGreen)
        elif treat_type in nhi_utils.DISLOCATE_TREAT:
            color = QtGui.QBrush(QtCore.Qt.darkBlue)
        elif treat_type in nhi_utils.AUXILIARY_CARE_TREAT:
            color = QtGui.QBrush(QtCore.Qt.red)
        elif treat_type in nhi_utils.IMPROVE_CARE_TREAT:
            color = QtGui.QBrush(QtCore.Qt.darkRed)
        elif treat_type in nhi_utils.HOME_CARE:
            color = QtGui.QBrush(QtCore.Qt.blue)
        elif treat_type in nhi_utils.TRADITIONAL_TREAT:
            color = QtGui.QBrush(QtCore.Qt.darkYellow)
        else:
            color = None

        color_list.append(color)

    ui_utils.set_combo_box(combobox_treat_type, treat_type_list)
    ui_utils.set_combo_box_item_color(combobox_treat_type, color_list)


def verify_confirm_code():
    random_number = f"{str(random.randint(0000, 9999)):0>4}"
    input_dialog = dialog_utils.get_dialog(
        "掛號刪除雙重確認",
        f"請輸入刪除確認碼 {random_number}",
        None,
        QInputDialog.TextInput,
        320,
        200,
    )
    ok = input_dialog.exec_()
    if not ok:
        return False

    confirm_code = input_dialog.textValue()
    if confirm_code != random_number:
        show_message_box(
            QMessageBox.Critical,
            "認證錯誤",
            '<font size="5" color="red"><b>刪除認證碼輸入錯誤, 無法刪除資料.</b></font>',
            "請重新執行刪除作業並輸入正確的確認碼.",
        )
        return False
    else:
        return True


def get_blood_measure_data(parent, system_settings, patient_id):
    blood_measure_path = system_settings.field("血壓計路徑")
    filename = os.path.join(blood_measure_path, patient_id + "*.femet")

    options = QFileDialog.Options()
    json_filename, _ = QFileDialog.getOpenFileName(
        parent,
        "血壓計檔案",
        filename,
        f"femet檔案 ({patient_id}*.femet)",
        options=options,
    )
    if not json_filename:
        return

    json_file = open(json_filename, "r")
    json_data = json.load(json_file)
    json_file.close()
    measure_time = json_data[0]["MeasureTime"]

    measure_data = []
    for data in json_data[0]["data"]:
        measure_line = f"{data['Type']}: {data['Value']}"
        measure_data.append(measure_line)

    measure_data = "\n".join(measure_data)

    script = f"測量時間: {measure_time}\n{measure_data}\n"

    history_dir = os.path.join(blood_measure_path, "history")
    if not os.path.exists(history_dir):
        os.mkdir(history_dir)

    shutil.move(
        json_filename, os.path.join(history_dir, os.path.basename(json_filename))
    )

    return script


def get_qrcode_b64png(data):
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_colo="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer)
    png = buffer.getvalue()

    b64png = base64.b64encode(png).decode("utf-8")

    return b64png


def play_youtube(parent, database, system_settings, url):
    dialog = dialog_utils.get_dialog_youtube(parent, database, system_settings)
    dialog.play_youtube(url)


def disable_mouse_wheel(parent, object):
    for widget in parent.findChildren(object):
        widget.wheelEvent = lambda event: None


def set_image(parent, png_filename, x, y, width=None, height=None, center=False):
    pixmap = QPixmap(png_filename)
    label_image = QtWidgets.QLabel(parent)

    label_image.setPixmap(pixmap)

    if width is None and height is None:
        label_image.setFixedSize(pixmap.size())
    else:
        label_image.setScaledContents(True)
        label_image.resize(width, height)

    if center:
        parent_width = parent.width()
        pixmap_width = label_image.pixmap().width()

        x = (parent_width - pixmap_width) // 2

    label_image.move(x, y)

    return label_image


def set_label(
    parent,
    text,
    x,
    y,
    font_name,
    font_size,
    font_color,
    center=False,
    font_weight="normal",
    shadow=False,
):
    label_text = QtWidgets.QLabel(parent)
    label_text.setText(text)
    label_text.setStyleSheet(
        f'font: 75 {font_size}pt "{font_name}"; color: {font_color}; font-weight: {font_weight};'
    )
    label_text.adjustSize()

    if center:
        parent_width = parent.width()
        label_width = label_text.width()
        x = (parent_width - label_width) // 2

    if shadow:
        shadow_widget(parent, label_text)

    label_text.move(x, y)

    return label_text


def set_button(
    parent,
    text,
    text_color,
    x,
    y,
    font_name,
    font_color,
    font_size,
    width,
    height,
    event,
    center=False,
    font_weight="normal",
    shadow=False,
):
    push_button = QtWidgets.QPushButton(parent)
    push_button.resize(width, height)
    push_button.setText(text)
    push_button.setStyleSheet(f"""
        QPushButton {{
            background-color: {font_color};  /* 正常狀態背景顏色 */
            border: 2px solid {font_color};  /* 邊框顏色 */
            border-radius: 10px;        /* 圓角 */
            color: {text_color};               /* 字體顏色 */
            font: 75 {font_size}pt "{font_name}";
            font-weight: {font_weight};
        }}
    """)

    if center:
        parent_width = parent.width()
        button_width = push_button.width()
        x = (parent_width - button_width) // 2

    if shadow:
        shadow_widget(parent, push_button)

    push_button.move(x, y)
    push_button.clicked.connect(event)

    return push_button


def shadow_widget(parent, widget):
    shadow = QtWidgets.QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(15)
    shadow.setOffset(4, 4)
    shadow.setColor(QtGui.QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(shadow)


def get_last_directory(program_name):
    settings = QSettings("pymedical", program_name)
    return settings.value(
        "lastDirectory",
        QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
    )


def set_last_directory(program_name, filename):
    directory = os.path.dirname(filename)
    settings = QSettings("pymedical", program_name)
    settings.setValue("lastDirectory", directory)


# 你已經有的工具：get_mariadb_dump()、dump_table()、delete_old_folders()
# 這裡直接呼叫即可


def backup_mariadb(parent, database, backup_path, db_dir=None, use_docker=False):
    """
    混合式備份（自動判斷引擎）：
        - MyISAM → 複製 .MYD/.MYI/.frm
        - InnoDB / 其他 → mysqldump --single-transaction
    """
    # ───────────────────────── 讀取 config ─────────────────────────
    cfg = configparser.ConfigParser()
    cfg.read(database.CONFIG_FILE)
    db_name = cfg["db"]["database"]
    host = cfg["db"]["host"]
    user = cfg["db"]["user"]
    pwd = cfg["db"]["password"]

    # ───────────────────────── 找出資料目錄 ─────────────────────────
    if not use_docker:
        if db_dir is None:
            rows = database.select_record("SHOW VARIABLES LIKE 'datadir'")
            if not rows:
                print("⚠️ 取不到 data_dir")
                return
            db_dir = os.path.join(rows[0]["Value"], db_name)

        if not os.path.isdir(db_dir):
            print(f"❌ 無法存取資料目錄: {db_dir}")
            return

    # ───────────────────────── 查表與分類 ─────────────────────────
    sql = f"""
        SELECT TABLE_NAME, ENGINE
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{db_name}'
    """
    rows = database.select_record(sql)
    myisam_tables = [
        r["TABLE_NAME"] for r in rows if (r["ENGINE"] or "").upper() == "MYISAM"
    ]
    dump_tables = [
        r["TABLE_NAME"] for r in rows if r["TABLE_NAME"] not in myisam_tables
    ]

    # ───────────────────────── 進度條 ─────────────────────────
    steps = len(myisam_tables) * 3 + len(dump_tables)  # MYD+MYI+frm = 3 檔，dump=1 步
    progress = QProgressDialog("正在備份資料庫...", "取消", 0, steps, parent)
    progress.setWindowModality(True)
    progress.setWindowTitle("資料庫備份")
    progress.show()

    step = 0

    def _update():
        nonlocal step
        step += 1
        progress.setValue(step)
        if progress.wasCanceled():
            raise KeyboardInterrupt

    # ───────────────────────── 備份 MyISAM 原始檔 ─────────────────────────
    database.exec_sql("FLUSH TABLES WITH READ LOCK")
    for tbl in myisam_tables:
        for ext in (".MYD", ".MYI", ".frm"):
            try:
                if use_docker:
                    table_name = f"{tbl}{ext}"
                    mariadb_dump_cmd = [
                        "docker",
                        "cp",
                        f"mariadb-db-service:/var/lib/mysql/pymedical/{table_name}",
                        backup_path,
                    ]
                    args = [arg for arg in mariadb_dump_cmd if arg]  # 過濾空白參數

                    dump_file = os.path.join(backup_path, table_name)
                    with open(dump_file, "w") as f:
                        try:
                            run_command(args, out_file=f)
                            print(f"✅ 複製docker: {tbl}{ext}")
                        except subprocess.CalledProcessError as e:
                            print("❌ 備份失敗，指令如下：")
                            print(" ".join(args))
                            print("🔴 stderr 錯誤訊息：", e.stderr.decode("utf-8"))
                            raise RuntimeError(
                                f"資料表 {table_name} 備份失敗，錯誤: {e}"
                            )
                else:
                    src = os.path.join(db_dir, f"{tbl}{ext}")
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(backup_path, f"{tbl}{ext}"))
                        print(f"✅ 複製 {tbl}{ext}")
            except Exception as e:
                print(f"❌ 複製 {tbl}{ext} 失敗: {e}")
            _update()

    database.exec_sql("UNLOCK TABLES")
    # ───────────────────────── 備份 InnoDB / 其他引擎 ─────────────────────────
    if dump_tables:
        version = "MariaDB"  # 若你已有偵測函式可自行替換
        for tbl in dump_tables:
            try:
                dump_table(database, version, backup_path, f"{tbl}.sql")
            except Exception as e:
                print(f"❌ dump {tbl} 失敗: {e}")
            _update()

    progress.setValue(steps)
    delete_old_folders(backup_path)
    print("🎉 備份完成！")


def run_command(command_args, out_file=None):
    """
    通用命令執行器：
    根據 out_file 參數，自動決定 stdout 是否導向檔案。

    參數:
    - command_args: 包含命令及其參數的列表，例如 ['docker', 'stop', 'mariadb-db-service']。
    - out_file: 可選的檔案物件。如果提供，stdout 將寫入此檔案。
                如果為 None，則 stdout 將被捕獲到 PIPE (用於錯誤訊息)。
    """
    is_windows = sys.platform == "win32"
    startupinfo = None

    # 處理 Windows 隱藏視窗設定
    if is_windows:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    # 決定 stdout 的行為：
    if out_file:
        # 情況一：有 out_file，將 stdout 導向檔案
        stdout_target = out_file
    else:
        # 情況二：無 out_file，將 stdout 導向 PIPE (這樣可以捕獲所有輸出，有利於除錯和錯誤報告)
        stdout_target = subprocess.PIPE

    try:
        result = subprocess.run(
            command_args,
            stdout=stdout_target,  # 根據 out_file 決定 stdout 目標
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            check=True,  # 確保命令返回非零碼時拋出 CalledProcessError
            text=True,  # 確保 stdout 和 stderr 的輸出是文本 (string)
            # ⚠️ 注意：由於 command_args 是列表，預設 shell=False，這在 Docker 環境下通常更安全。
        )
        return result

    except subprocess.CalledProcessError as e:
        # 當 check=True 拋出錯誤時，提供清晰的錯誤報告
        error_msg = (
            f"指令失敗: {' '.join(command_args)}\n🔴 錯誤訊息:\n{e.stderr.strip()}"
        )
        # 由於 stdout 已經被導向或捕獲，這裡只報告 stderr
        raise RuntimeError(error_msg)

    except FileNotFoundError:
        raise RuntimeError(
            f"❌ 錯誤: 無法找到執行檔 ({command_args[0]})。請確認執行檔在系統 PATH 中。"
        )
    except Exception as e:
        raise RuntimeError(f"執行命令時發生未預期錯誤: {e}")


def delete_old_folders(backup_path, days_to_keep=30):
    """刪除 `backup_path` 內超過 `days_to_keep` 天的資料夾"""

    now = datetime.datetime.now()
    cutoff_time = now - datetime.timedelta(days=days_to_keep)

    backup_path = os.path.dirname(backup_path)

    # 遍歷 `backup_path` 內的所有目錄
    for folder in Path(backup_path).iterdir():
        if folder.is_dir():  # 確保是資料夾
            folder_mtime = datetime.datetime.fromtimestamp(
                folder.stat().st_mtime
            )  # 取得修改時間
            if folder_mtime < cutoff_time:  # 超過 30 天
                try:
                    shutil.rmtree(folder)
                    # 把 print 移進來，如果 print 失敗，會被下方的 except 捕捉，不會讓程式崩潰
                    print(
                        f"✅ 已刪除過期備份資料夾: {folder}（最後修改: {folder_mtime.strftime('%Y-%m-%d %H:%M:%S')}）"
                    )
                except Exception as e:
                    # 這裡也要防禦一下，萬一連這個 print 也因為管道斷開而失敗
                    try:
                        print(f"❌ 刪除失敗或輸出失敗 {folder}: {e}")
                    except OSError:
                        pass  # 管道真的斷了就直接放手，反正程式都要關了


def is_maintain_expired(clinic_name):
    expired_clinic = [
        "中醫診所",
    ]

    if clinic_name in expired_clinic:
        return True
    else:
        return False


def insert_text(text_edit, text, input_code, insert_comma=True):
    cursor = text_edit.textCursor()

    if insert_comma:
        if len(text_edit.toPlainText()) > len(input_code) and not cursor.atStart():
            text = ", " + text

    cursor.movePosition(
        QtGui.QTextCursor.Left, QtGui.QTextCursor.MoveAnchor, len(input_code)
    )
    text_edit.setTextCursor(cursor)
    text_edit.insertPlainText(text)

    cursor.movePosition(
        QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor, len(input_code)
    )
    cursor.removeSelectedText()


def delete_old_backup_folders(root_path, keep_days=30):
    now = datetime.datetime.today()
    threshold = now - datetime.timedelta(days=keep_days)

    for folder in os.listdir(root_path):
        folder_path = os.path.join(root_path, folder)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.datetime.strptime(folder, "%Y-%m-%d")
                if folder_date < threshold:
                    shutil.rmtree(folder_path)
                    print(f"🗑 已刪除過期備份資料夾：{folder_path}")
            except ValueError:
                continue  # 忽略非日期格式的資料夾


# 測試ip是否有通 2025-05-17
def ping_ip(ip):
    is_windows = platform.system().lower() == "windows"

    if is_windows:
        command = f"ping -n 1 -w 500 {ip}"  # 等待最多 500ms
    else:
        command = f"ping -c 1 -W 1 {ip}"  # Linux 下，-W 1 是 1 秒 timeout

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            timeout=3,
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        return False


def download_file_from_github(url, local_filename):
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "pymedical"},
        )
        response.raise_for_status()
        with open(local_filename, "wb") as f:
            f.write(response.content)
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def set_date_edit(date_edit, text):
    date_edit.setMinimumDate(QDate(1900, 1, 1))  # 定一個「哨兵值」
    date_edit.setSpecialValueText(text)  # 等於最小日期時顯示這個
    date_edit.setDate(QDate(1900, 1, 1))  # 預設顯示「未收案」


def date_edit_to_db(date_edit):
    """QDateEdit -> 'yyyy-MM-dd' 字串或 None（1900/1/1 視為空值）"""
    qdate = date_edit.date()
    if qdate == QDate(1900, 1, 1):
        return None

    return qdate.toString("yyyy-MM-dd")


def db_to_date_edit(date_edit, value):
    """DB 的 date/None -> QDateEdit（None 顯示為 1900/1/1）"""
    if value is None:
        date_edit.setDate(QDate(1900, 1, 1))
    else:
        # value 可能是 datetime.date 或字串，看你們 db 層回傳什麼
        date_edit.setDate(QDate(value.year, value.month, value.day))


def get_radio_value(radio_dict):
    """掃 radio 群組，回傳選中的代碼，都沒選回傳 None"""
    for radio_button, value in radio_dict.items():
        if radio_button.isChecked():
            return value

    return None


def set_radio_value(radio_dict, value):
    """依代碼設定 radioButton 群組（get_radio_value 的反向）"""
    if value is None:
        return
    for radio_button, code in radio_dict.items():
        if code == str(value):
            radio_button.setChecked(True)
            return


def get_check_values(check_dict):
    """掃 checkbox 群組，回傳底線分隔字串如 '01_11'，都沒勾回傳 None"""
    values = [value for check_box, value in check_dict.items() if check_box.isChecked()]
    return "_".join(values) if values else None


def set_check_values(check_dict, value):
    """依底線分隔字串勾選 checkBox 群組（get_check_values 的反向）"""
    codes = str(value).split("_") if value else []
    for check_box, code in check_dict.items():
        check_box.setChecked(code in codes)


def set_combo_box_text(combo_box, value):
    """依顯示文字設定 comboBox，找不到或 None 則回到第一個選項"""
    if value is None:
        combo_box.setCurrentIndex(0)
        return

    index = combo_box.findText(str(value))
    combo_box.setCurrentIndex(index if index >= 0 else 0)
