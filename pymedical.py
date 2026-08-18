"""Pymedical主程式 2026-08-19"""

# -*- coding: utf-8 -*-

import configparser
import ctypes
import datetime
import json
import os
import sys
import time

if sys.platform == "linux":
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    os.environ["QT_IM_MODULE"] = "fcitx"
    os.environ["XMODIFIERS"] = "@im=fcitx"
    os.environ["SDL_IM_MODULE"] = "fcitx"  # 如果你有用到 SDL 相關庫

    os.environ["QT_FONT_DPI"] = "96"  # 避免 DPI 混亂
    os.environ["QT_DEFAULT_FONT"] = "Noto Sans"
    os.environ["QT_FONT_FAMILY"] = "Noto Sans"


import traceback
from ctypes import wintypes
from queue import Queue
from threading import Thread

import pygame
from pygame import mixer
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QCoreApplication, QDir, QLockFile, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QStyleFactory,
)

from libs import (
    class_utils,
    date_utils,
    db_utils,
    dialog_utils,
    log_utils,
    module_utils,
    nhi_utils,
    notification_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
    voice_utils,
    web_utils,
)

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)


# 導入 Windows 平台相關模塊
if sys.platform == "win32":
    import pythoncom
    from win32 import win32gui, win32print
    from win32.lib import win32con
    from win32com.client import Dispatch

    try:
        import pyuac
    except Exception:
        system_utils.pip3_install("pyuac")


class FLASHWINFO(ctypes.Structure):
    """閃爍工作列."""

    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("dwFlags", wintypes.DWORD),
        ("uCount", wintypes.UINT),
        ("dwTimeout", wintypes.DWORD),
    ]


FLASHW_STOP = 0
FLASHW_CAPTION = 0x00000001
FLASHW_TRAY = 0x00000002
FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMER = 0x00000004
FLASHW_TIMERNOFG = 0x0000000C  # 只在視窗不在前景時閃爍


def flash_window(hwnd, count=5, timeout=300):
    fw = FLASHWINFO()
    fw.cbSize = ctypes.sizeof(FLASHWINFO)
    fw.hwnd = hwnd
    fw.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
    fw.uCount = count
    fw.dwTimeout = timeout  # 自訂閃爍速度（毫秒）
    ctypes.windll.user32.FlashWindowEx(ctypes.byref(fw))


# 錯誤訊息攔截, 並通知自己
def collect_traceback(exctype, value, tb):
    # 1. 安全讀取 JSON 數據
    try:
        with open(system_utils.PY_MEDICAL_JSON_FILE, "r") as json_file:
            json_data = json.load(json_file)
    except Exception:
        json_data = {"院所名稱": "未知院所", "使用者": "未知使用者"}

    # 取得目前版本 (加 try 保險, 避免錯誤處理器本身又出錯)
    try:
        version = system_utils.get_system_version()
    except Exception:
        version = "未知版本"

    # 2. 格式化堆疊追蹤
    tb_list = traceback.extract_tb(tb)
    stack = "".join(traceback.format_list(tb_list))

    # 3. 組合通知內容
    mail_content = (
        f"**程式版本:** {version}\n"
        f"**異常類型:** {exctype.__name__}\n"
        f"**異常值:** {value}\n"
        f"**追蹤:**\n{stack}"
    )

    # 4. 記錄到本地日誌 (Logging)
    system_utils.loggin_error("tracebacks.log", mail_content)

    # 5. 發送 Telegram 警報
    system_utils.send_telegram_alert(json_data, mail_content)

    # 6. 顯示給使用者看的 GUI 訊息框 (假設使用 PyQt/PySide 的 QMessageBox)
    # 注意：這裡使用 HTML 格式來美化訊息框
    system_utils.show_message_box(
        QMessageBox.Critical,
        "系統錯誤",
        f"""
            <font color="red"><h3>錯誤訊息: {value}</h3></font><br>
            程式中斷點:<br>
            {stack}
        """,
        "錯誤訊息已通知本公司，我們將努力找到問題點，盡速排除",
    )


BEEP_COOLDOWN_SECONDS = 3


class PyMedical(QtWidgets.QMainWindow):
    """主程式."""

    def __init__(self, parent=None, splash=None, *args):
        """初始化主程式."""
        super().__init__(parent)
        self.splash = splash
        self.args = args
        self.version = system_utils.get_system_version()
        self._deleted = False
        self.host = None
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self._force_close = False

        try:
            config_file = self.args[0][1]
        except IndexError:
            config_file = None

        self._set_db(config_file)
        if not self.database.connected():
            if self.splash is not None:
                self.splash.finish(self)

            if config_file is None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("連線失敗")
                msg_box.setText(
                    "<font size='4' color='red'><b>無法連線至資料庫主機, 請檢查網路設定.</b></font>"
                )
                msg_box.setInformativeText(
                    "請檢查 pymedical.conf 內的設定, 確定資料庫連線設定是否正確."
                )
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()
            else:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("連線失敗")
                msg_box.setText(
                    "<font size='4' color='red'><b>無法連線至資料庫主機, 請檢查傳遞的參數.</b></font>"
                )
                msg_box.setInformativeText("請檢查傳遞的參數是否正確.")
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()

            sys.exit(0)

        try:
            self.database.kill_sleep_connections()
        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("連線清理失敗")
            msg_box.setText(
                f"<font size='4' color='red'><b>無法清除Sleep連線:<br>{e!s}</b></font>"
            )
            msg_box.setInformativeText("請檢查傳遞的參數是否正確.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()

        self.check_system_db()
        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )

        system_utils.remove_user_info(self.system_settings)
        self.clinic_name = self.system_settings.field("院所名稱")
        instance_setting = self.system_settings.field("醫療系統執行個體")
        self.set_waiting_list = self.system_settings.field("自動切換醫師候診名單")
        self.no_beep = self.system_settings.field("醫師候診名單不要提示音")
        self.beep_anywhere = self.system_settings.field("候診名單更新發出提示音")
        self._last_beep_time = 0.0

        if instance_setting == "獨立執行" and not self._acquire_single_instance_lock():
            if sys.platform == "win32":
                self._check_single_instance()  # 保留原本「把舊視窗叫到前景」的好體驗
            sys.exit(0)

        self.ui = None

        self._init_statistics_dicts()

        self._set_ui()
        self._set_notification_server()

        self._set_signal()
        self._set_user_name()

        self.reset_wait()
        self._set_dealer()
        voice_utils.cleanup_tts_cache()

    def _acquire_single_instance_lock(self):
        # 用院所名稱當 key, 讓不同院所 / 不同資料庫仍可各自獨立執行
        lock_path = os.path.join(QDir.tempPath(), f"pymedical_{self.clinic_name}.lock")
        self._instance_lock = QLockFile(lock_path)  # 一定要存成 self 屬性!
        self._instance_lock.setStaleLockTime(30000)  # 30秒, 死鎖自動回收的保險
        return self._instance_lock.tryLock(100)  # 拿到=True, 已被佔用=False

    def _set_dealer(self):
        dealer = "百會資訊"

        dealer_file = "dealer.conf"
        if os.path.exists(dealer_file):
            config = configparser.ConfigParser()
            config.read(dealer_file)
            dealer = config["settings"]["dealer"]

        self.ui.label_system_owner.setText(f"<b>{dealer}</b>")

    def _init_statistics_dicts(self):
        self.statistics_dicts = {
            "本月健保內科人數": 0,
            "本月健保針灸人數": 0,
            "本月健保中度複針人數": 0,
            "本月健保高度複針人數": 0,
            "本月健保傷科人數": 0,
            "本月健保首次人數": 0,
            "本月健保看診日數": 0,
            "第一段診察費合理量": 0,
            "本月健保診察費人數": 0,
            "本月健保診察人數": 0,
            "本月健保針傷限量": 0,
            "本月健保針傷合計": 0,
            "本日健保內科人數": 0,
            "本日健保針灸人數": 0,
            "本日健保傷科人數": 0,
            "本日健保首次人數": 0,
            "本月健保中度複針限量": 0,
            "本月健保高度複針限量": 0,
            "本月健保針傷合併限量": 0,
            "本月健保針傷合併人數": 0,
            "本月健保中度複傷人數": 0,
            "本月健保高度複傷人數": 0,
            "本月健保脫臼整復人數": 0,
            "本月健保針傷給藥人數": 0,
        }

    def _set_db(self, config_file):
        if config_file is not None:
            BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))
            self.config_file = os.path.join(BASE_DIR, config_file)
            self.database = class_utils.get_db(self.config_file, backend="mysql")
            self.host = self.database.host
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

    def _check_single_instance(self):
        import win32con
        import win32gui

        def windowEnumerationHandler(hwnd, top_windows):
            top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

        top_windows = []
        win32gui.EnumWindows(windowEnumerationHandler, top_windows)
        for i in top_windows:
            if (
                self.clinic_name is not None
                and self.clinic_name + " 醫療資訊管理系統" in i[1]
            ):
                hwnd = i[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(hwnd)
                sys.exit()

    def set_treatment_list(self):
        """設定複雜針傷病名列表."""
        sql = """
            SELECT * FROM system_log
            WHERE
                LogType = "資料轉檔" AND
                LogName = "2023ICD10轉檔" AND
                Log = "已轉檔"
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            station_no = self.system_settings.field("工作站編號")
            sql = f'''
                SELECT * FROM system_log
                WHERE
                    LogType = "資料轉檔" AND
                    LogName = "2023ICD10轉檔" AND
                    Log = "{station_no}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:  # 還沒拷貝過complicated_treatment_data.json
                log_utils.write_system_log(
                    self.database, "資料轉檔", "2023ICD10轉檔", station_no
                )
                self.get_treatment_list_from_db()

        try:
            self.get_treatment_list_from_json()
        except FileNotFoundError:
            self.get_treatment_list_from_db()

    def get_treatment_list_from_json(self):
        """取得複雜針傷json."""
        json_file = open(system_utils.COMPLICATED_TREATMENT_DISEASE_FILE)
        json_data = json.load(json_file)

        self.moderate_complicated_acupuncture_list = json_data["moderate_acupuncture"]
        self.highly_complicated_acupuncture_list = json_data["highly_acupuncture"]
        self.moderate_complicated_massage_list = json_data["moderate_massage"]
        self.highly_complicated_massage_list = json_data["highly_massage"]
        self.special_disease_list = json_data["special_disease"]
        self.dislocate_list = json_data["dislocate"]
        self.fracture_list = json_data["fracture"]

        self.complicated_treat_list = [
            self.moderate_complicated_acupuncture_list,
            self.highly_complicated_acupuncture_list,
            self.moderate_complicated_massage_list,
            self.highly_complicated_massage_list,
            self.special_disease_list,
            self.dislocate_list,
            self.fracture_list,
        ]

    def get_treatment_list_from_db(self):
        """資料庫取得複雜針傷內容."""
        list_count = 6
        progress_dialog = QtWidgets.QProgressDialog(
            "正在讀取針傷專案診斷碼中, 請稍後...", "取消", 0, list_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.moderate_complicated_acupuncture_list = (
            nhi_utils.get_moderate_complicated_acupuncture_list(self.database)
        )
        progress_dialog.setValue(1)
        self.highly_complicated_acupuncture_list = (
            nhi_utils.get_highly_complicated_acupuncture_list(self.database)
        )
        progress_dialog.setValue(2)
        self.moderate_complicated_massage_list = (
            nhi_utils.get_moderate_complicated_massage_list(self.database)
        )
        progress_dialog.setValue(3)
        self.highly_complicated_massage_list = (
            nhi_utils.get_highly_complicated_massage_list(self.database)
        )
        progress_dialog.setValue(4)
        self.special_disease_list = (
            nhi_utils.get_moderate_complicated_massage_with_special_disease_list(
                self.database
            )
        )
        self.dislocate_list = nhi_utils.get_dislocate_list(self.database)
        progress_dialog.setValue(5)
        self.fracture_list = nhi_utils.get_fracture_list(self.database)
        progress_dialog.setValue(list_count)

        treatment_disease = {
            "moderate_acupuncture": self.moderate_complicated_acupuncture_list,
            "highly_acupuncture": self.highly_complicated_acupuncture_list,
            "moderate_massage": self.moderate_complicated_massage_list,
            "highly_massage": self.highly_complicated_massage_list,
            "special_disease": self.special_disease_list,
            "dislocate": self.dislocate_list,
            "fracture": self.fracture_list,
        }
        with open(system_utils.COMPLICATED_TREATMENT_DISEASE_FILE, "w") as f:
            json.dump(treatment_disease, f)

        progress_dialog.deleteLater()

    @staticmethod
    def _parse_config_file(config_file, db_section="db"):
        config = configparser.ConfigParser()
        config.read(config_file)

        config_dict = {
            "host": config[db_section]["host"],
            "user": config[db_section]["user"],
            "database": config[db_section]["database"],
            "password": config[db_section]["password"],
            "charset": config[db_section]["charset"],
            "buffered": True,
        }

        return config_dict

    def _set_user_name(self):
        self.user_name = system_utils.get_user_name(self.system_settings)

    def __del__(self):
        """解構主程式."""
        if self._deleted:
            return

        self._deleted = True

    def closeEvent(self, event: QtGui.QCloseEvent):
        """關閉主程式事件."""
        if self._force_close:
            self._shutdown()  # 一樣執行備份與清理,只是不問使用者
            event.accept()
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("關閉醫療系統")
        msg_box.setText(
            "<font size='5' color='red'><b>確定要關閉醫療資訊管理系統?</b></font>"
        )
        msg_box.setInformativeText(
            "<font size='4'>注意！系統結束後, 會自動執行資料備份作業，請稍後...</font>"
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("關閉醫療系統"), QMessageBox.AcceptRole)
        quit_app = msg_box.exec_()

        if not quit_app:
            event.ignore()
            return

        # IC卡未上傳檢查(只在互動關閉時檢查)
        if self.user_name != "超級使用者":
            dialog = dialog_utils.get_dialog_ic_record_upload(
                self, self.database, self.system_settings, "pymedical"
            )
            dialog.ui.dateEdit_start_date.setDate(datetime.datetime.now().date())
            dialog.ui.dateEdit_end_date.setDate(datetime.datetime.now().date())
            dialog.ui.comboBox_period.setCurrentText("全部")
            sql = dialog.get_sql()
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("IC卡資料尚有資料未上傳")
                msg_box.setText(
                    "<font size='5' color='red'><b>IC卡資料尚有資料未上傳, 確定要繼續關閉醫療資訊管理系統?</b></font>"
                )
                msg_box.setInformativeText(
                    "<font size='4'>注意！請確認IC卡資料上傳作業是否要執行</font>"
                )
                msg_box.addButton(QPushButton("不要關, 我要上傳"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("我知道了"), QMessageBox.AcceptRole)
                quit_app = msg_box.exec_()
                if not quit_app:
                    event.ignore()
                    return

        self._shutdown()
        event.accept()

    def _backup_database(self):
        if self.user_name == "超級使用者" or self.system_settings.field("資料路徑") in [
            "不備份",
        ]:
            return

        backup_process = module_utils.get_backup(
            self, self.database, self.system_settings
        )
        backup_process.start_backup()

    def _shutdown(self, run_backup=True):
        """關閉前的清理作業(備份、關資料庫等)"""
        if run_backup:
            self._backup_database()

        self._turn_off_led()
        pygame.quit()
        system_utils.remove_user_info(self.system_settings)

        if hasattr(self, "database") and self.database:
            try:
                self.database.close_database()
                print("✅ 資料庫連線已安全關閉")
            except Exception as e:
                print(f"❌ 關閉資料庫時發生錯誤: {e}")
                system_utils.loggin_error(
                    "system_errors.log", f"關閉資料庫時發生錯誤: {e}"
                )

        if hasattr(self, "archive_db") and self.archive_db:
            try:
                self.archive_db.close_database()
                print("✅ 封存資料庫連線已安全關閉")
            except Exception as e:
                print(f"❌ 關閉封存資料庫時發生錯誤: {e}")
                system_utils.loggin_error(
                    "system_errors.log", f"關閉封存資料庫時發生錯誤: {e}"
                )

        self.deactivate_ic_card_reader()

    def _turn_off_led(self):
        led_port = self.system_settings.field("叫號燈連接埠")
        if led_port not in [None, "0"]:
            system_utils.send_to_com_port(led_port, "0")

        led_ip = self.system_settings.field("叫號燈ip")
        if led_ip not in [None, ""]:
            led_port = number_utils.get_integer(
                self.system_settings.field("叫號燈port")
            )
            try:
                system_utils.send_to_tcpip(
                    led_ip, led_port, b"\xed\xed\x0f\x0f\x0f\x0f\x7f\x00\x00"
                )
            except Exception as e:
                system_utils.loggin_error(
                    "system_errors.log",
                    f"關閉叫號燈失敗 (IP={led_ip}, Port={led_port}): {e}",
                )

    def check_system_db(self):
        """檢查資料庫是否需要補充."""
        mysql_path = "./mysql"
        mysql_files = [
            f
            for f in os.listdir(mysql_path)
            if os.path.isfile(os.path.join(mysql_path, f))
        ]
        for file in mysql_files:
            table_name = file.split(".sql")[0]
            self.database.check_table_exists(table_name)

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            ui_utils.UI_PY_MEDICAL, self, native_menu_bar=True
        )

        self.setWindowIcon(QtGui.QIcon("./icons/python.ico"))
        self.ui.tabWidget_window.setTabsClosable(True)

        self._set_images()
        self._set_button_enabled()
        self.ui.setWindowTitle(f"{self.clinic_name} 醫療資訊管理系統")
        self._set_style()
        self.set_status_bar()
        self.setup_hourly_refresh()

        if self.system_settings.field("顯示側邊欄") == "Y":
            self.ui.frameSidebar.show()
            self.ui.action_show_side_bar.setChecked(True)
        else:
            self.ui.frameSidebar.hide()
            self.ui.action_show_side_bar.setChecked(False)

        try:
            self._display_bulletin()
        except Exception:
            pass

        self._set_menu_font()

    def _set_menu_font(self):
        menu_list = []
        sql = """
            SELECT Value FROM system_settings
            WHERE
                StationNo = 0 AND
                Field = "功能表醒目設定"
        """
        rows = self.database.select_record(sql)
        for row in rows:
            menu_list.append(row["Value"])

        if len(menu_list) <= 0:
            return

        font = QtGui.QFont()
        font.setBold(True)

        for action in self.findChildren(QtWidgets.QAction):
            if action.text() in menu_list:
                action.setFont(font)

    def _set_images(self):
        icon_size = 128

        self.ui.label_line_qrcode.setPixmap(QtGui.QPixmap("./images/line_qrcode.jpg"))
        self.ui.label_line_qrcode.setMaximumWidth(icon_size)
        self.ui.label_line_qrcode.setMaximumHeight(icon_size)
        self.ui.label_line_qrcode.setScaledContents(True)

    def _display_bulletin(self):
        # 1. 檢查使用者設定
        if self.system_settings.field("不要顯示最新消息") == "Y":
            self.ui.label_system_name.hide()
            self.ui.textBrowser.hide()
            return

        import ssl
        import urllib.request

        # 預設內容 (備援用)
        html = "<html><body><p>正在載入最新消息...</p></body></html>"
        url = "https://raw.githubusercontent.com/picacat/medical-announcements/refs/heads/main/bulletin.html"

        try:
            # 建立不檢查憑證的 context (對付舊系統 Win7 的關鍵)
            context = ssl._create_unverified_context()

            # 加入 timeout 確保網路不通時不會讓 HIS 啟動畫面卡死太久
            with urllib.request.urlopen(url, context=context, timeout=5) as response:
                html = response.read().decode("utf-8")
        except Exception as e:
            # --- 💡 關鍵備援邏輯 ---
            # 如果網路抓不到最新的，再改讀本地的 bulletin.html 作為保險
            print(f"公告抓取失敗: {e}")
            bulletin_path = os.path.join(self.base_path, "html", "bulletin.html")
            if os.path.exists(bulletin_path):
                with open(bulletin_path, "r", encoding="utf-8") as f:
                    html = f.read()
            else:
                html = (
                    "<html><body>目前無法連線至公告伺服器，請檢查網路。</body></html>"
                )

        # 設定 UI 效果
        shadow1 = QtWidgets.QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(40)
        self.ui.textBrowser.setStyleSheet("background: transparent;")
        self.ui.textBrowser.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.ui.textBrowser.setGraphicsEffect(shadow1)

        # 顯示最終內容
        self.ui.textBrowser.setHtml(html)

    def set_plugin(self):
        """增加外掛程式."""
        self.ui.menu_massage.menuAction().setVisible(False)

        massage_host_dict = db_utils.get_host_database_dict(self.database, "養生館")
        if len(massage_host_dict) > 0:
            self.ui.menu_massage.menuAction().setVisible(True)

    def _set_notification_server(self):
        notification_utils.ensure_table(self.database)  # ← 先確保表在
        notification_utils.purge_old_records(self.database)

        channels = [notification_utils.CHANNEL_WAITING_LIST]
        if self.system_settings.field("廣播叫號主機") == "Y":
            channels.append(notification_utils.CHANNEL_CALL_NUMBER)

        self.notification_server = notification_utils.NotificationServer(
            self,
            database=self.database,
            station="pymedical",
            channels=channels,
        )
        self.notification_server.update_signal.connect(self._on_notification)

    def _on_notification(self, channel, message):
        if channel == notification_utils.CHANNEL_WAITING_LIST:
            self._refresh_waiting_data(message)
        elif channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_speech(message)

    def add_separator(self):
        """狀態列增加分隔線."""
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.VLine)  # 垂直線
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        separator.setFixedHeight(20)

        return separator

    # 設定 status bar
    def set_status_bar(self):
        """設定狀態列."""
        self.label_version = QtWidgets.QLabel()
        self.label_version.setFixedWidth(280)
        self.ui.statusbar.addPermanentWidget(self.label_version)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_db_engine = QtWidgets.QLabel()  # 先暫時卡位 2025-04-30
        self.label_db_engine.setFixedWidth(180)
        self.ui.statusbar.addPermanentWidget(self.label_db_engine)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_record_index = QtWidgets.QLabel()
        self.label_record_index.setFixedWidth(300)
        self.ui.statusbar.addPermanentWidget(self.label_record_index)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_station_no = QtWidgets.QLabel()
        self.label_station_no.setFixedWidth(150)
        self.ui.statusbar.addPermanentWidget(self.label_station_no)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_server_ip = QtWidgets.QLabel()
        self.label_server_ip.setFixedWidth(250)
        self.ui.statusbar.addPermanentWidget(self.label_server_ip)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_ip = QtWidgets.QLabel()
        self.label_ip.setFixedWidth(250)
        self.ui.statusbar.addPermanentWidget(self.label_ip)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_user_name = QtWidgets.QLabel()
        self.label_user_name.setFixedWidth(200)
        self.ui.statusbar.addPermanentWidget(self.label_user_name)
        self.ui.statusbar.addPermanentWidget(self.add_separator())

        self.label_today = QtWidgets.QLabel()
        self.label_today.setFixedWidth(180)
        self.ui.statusbar.addPermanentWidget(self.label_today)

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_registration.clicked.connect(
            self._open_subroutine
        )  # 掛號作業
        self.ui.pushButton_reservation.clicked.connect(
            lambda: self.open_reservation(None, None, None)
        )  # 預約掛號
        self.ui.pushButton_cashier.clicked.connect(self._open_subroutine)  # 批價作業
        self.ui.pushButton_return_card.clicked.connect(
            self._open_subroutine
        )  # 健保卡欠還卡
        self.ui.pushButton_debt.clicked.connect(self._open_subroutine)  # 欠還款作業
        self.ui.pushButton_checkout.clicked.connect(
            self._open_subroutine
        )  # 掛號櫃台結帳
        self.ui.pushButton_patient_list.clicked.connect(
            self._open_subroutine
        )  # 病患查詢
        self.ui.pushButton_ic_record_upload.clicked.connect(
            self._open_subroutine
        )  # 健保IC卡資料上傳

        self.ui.toolButton_nhi_vpn.clicked.connect(self._open_hyper_link)  # 健保VPN
        self.ui.toolButton_nhi_vpn_new.clicked.connect(
            self._open_hyper_link
        )  # 健保VPN (新版)
        self.ui.toolButton_mohw.clicked.connect(self._open_hyper_link)  # 醫事入口網
        self.ui.toolButton_hca.clicked.connect(
            self._open_hyper_link
        )  # 醫事憑證管理中心
        self.ui.toolButton_nhi.clicked.connect(self._open_hyper_link)  # 中央健康保險署
        self.ui.toolButton_hpa.clicked.connect(self._open_hyper_link)  # 國民健康暑

        self.ui.toolButton_nucmda.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_tpcma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_sbcma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_klcma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_tycma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_hctcma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_hccma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_mlcma.clicked.connect(self._open_hyper_link)
        self.ui.toolButton_med_vpn.clicked.connect(self._open_hyper_link)

        self.ui.pushButton_waiting_list.clicked.connect(
            self._open_subroutine
        )  # 醫師看診作業
        self.ui.pushButton_medical_record_list.clicked.connect(
            self._open_subroutine
        )  # 病歷查詢
        self.ui.pushButton_purchase.clicked.connect(self._open_subroutine)  # 病歷統計

        self.ui.pushButton_settings.clicked.connect(self.open_settings)  # 系統設定
        self.ui.action_hosts.triggered.connect(self.open_hosts_settings)  # 分院連線設定
        self.ui.action_import_medical_record.triggered.connect(
            self.open_import_medical_record
        )  # 匯入JSON
        # self.ui.pushButton_charge.clicked.connect(self._open_subroutine)                    # 收費設定
        self.ui.pushButton_diagnostic.clicked.connect(self._open_subroutine)  # 診察資料
        self.ui.pushButton_medicine.clicked.connect(self._open_subroutine)  # 處方資料
        self.ui.pushButton_ic_card.clicked.connect(self.open_ic_card)  # 健保卡讀卡機
        # self.ui.pushButton_reconnect_database.clicked.connect(self.reconnect_database)                       # 健保卡讀卡機

        self.ui.pushButton_logout.clicked.connect(self.logout)  # 登出
        self.ui.pushButton_quit.clicked.connect(self.close)  # 離開系統

        self.ui.action_reservation.triggered.connect(
            lambda: self.open_reservation(None, None, None)
        )  # 預約掛號
        self.ui.action_logout.triggered.connect(self.logout)  # 登出
        self.ui.action_quit.triggered.connect(self.close)  # 離開系統

        self.ui.action_convert.triggered.connect(self.convert)  # 轉檔作業
        self.ui.action_export_emr_xml.triggered.connect(
            self.export_emr_xml
        )  # 匯出電子病歷
        self.ui.action_export_medical_record_json.triggered.connect(
            self.export_medical_record_json
        )  # 匯出病歷
        self.ui.action_export_all_database.triggered.connect(
            self.export_all_database
        )  # 匯出整個資料庫
        self.ui.action_import_all_database.triggered.connect(
            self.import_all_database
        )  # 匯出整個資料庫

        self.ui.action_ins_check.triggered.connect(self._open_subroutine)  # 申報檢查
        self.ui.action_ins_apply.triggered.connect(self._open_subroutine)  # 健保申報
        self.ui.action_ins_judge.triggered.connect(self._open_subroutine)  # 健保抽審
        self.ui.action_ins_appeal.triggered.connect(self._open_subroutine)  # 健保申復
        self.ui.action_statistics_ins_pregnant.triggered.connect(
            self._open_subroutine
        )  # 孕產照護報表
        self.ui.action_statistics_nursing_home.triggered.connect(
            self._open_subroutine
        )  # 照護機構院民資料報表

        self.ui.action_registration.triggered.connect(self._open_subroutine)
        self.ui.action_cashier.triggered.connect(self._open_subroutine)
        self.ui.action_pharmacy.triggered.connect(self._open_subroutine)  # 藥局作業

        self.ui.action_return_card.triggered.connect(self._open_subroutine)
        self.ui.action_purchase.triggered.connect(self._open_subroutine)
        self.ui.action_checkout.triggered.connect(self._open_subroutine)
        self.ui.action_debt.triggered.connect(self._open_subroutine)
        self.ui.action_return_goods.triggered.connect(self._open_subroutine)
        self.ui.action_patient_list.triggered.connect(self._open_subroutine)
        self.ui.action_ins_record_upload.triggered.connect(self._open_subroutine)
        self.ui.action_update.triggered.connect(self._update_files)
        self.ui.action_restore_records.triggered.connect(self._open_subroutine)
        self.ui.action_database_repair.triggered.connect(self._database_repair)

        self.ui.action_waiting_list.triggered.connect(self._open_subroutine)
        self.ui.action_medical_record_list.triggered.connect(self._open_subroutine)
        self.ui.action_medical_record_statistics.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_examination.triggered.connect(
            self._open_subroutine
        )  # 檢驗報告登錄
        self.ui.action_examination_list.triggered.connect(
            self._open_subroutine
        )  # 檢驗報告查詢
        self.ui.action_exam_result.triggered.connect(
            self.open_exam_result
        )  # 檢驗報告查詢

        self.ui.action_settings.triggered.connect(self.open_settings)
        self.ui.action_menu_setting.triggered.connect(self.open_menu_setting)
        self.ui.action_bulletin_settings.triggered.connect(
            self.open_bulletin_settings
        )  # 候診資訊系統設定
        self.ui.action_cashier_machine_settings.triggered.connect(
            self.open_cashier_machine_settings
        )  # 掛號機零錢箱設定
        self.ui.action_charge.triggered.connect(self._open_subroutine)
        self.ui.action_doctor_schedule.triggered.connect(self._open_subroutine)
        self.ui.action_pharmacist_schedule.triggered.connect(self._open_subroutine)
        self.ui.action_doctor_nurse_table.triggered.connect(self._open_subroutine)
        self.ui.action_users.triggered.connect(self._open_subroutine)
        self.ui.action_diagnostic.triggered.connect(self._open_subroutine)
        self.ui.action_medicine.triggered.connect(self._open_subroutine)
        self.ui.action_misc.triggered.connect(self._open_subroutine)
        self.ui.action_ins_drug.triggered.connect(self._open_subroutine)
        self.ui.action_ins_apply_infectious.triggered.connect(self._open_subroutine)

        self.ui.action_tutorial_videos.triggered.connect(self.open_tutorial_videos)

        self.ui.action_purchase_records.triggered.connect(self._open_subroutine)
        self.ui.action_trace.triggered.connect(self._open_subroutine)
        self.ui.action_discount_type.triggered.connect(self._open_subroutine)
        self.ui.action_patient_age_group.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_ins_apply_year.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_period_year.triggered.connect(self._open_subroutine)

        self.ui.action_statistics_daily.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_doctor.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_doctor_monthly.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_doctor_amount.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_doctor_medicine.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_return_rate.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_no_return_rate.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_medicine.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_ins_performance.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_doctor_commission.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_ins_discount.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_multiple_performance.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_growth_rate.triggered.connect(self._open_subroutine)
        self.ui.action_business_income.triggered.connect(self._open_subroutine)

        self.ui.action_statistics_massager.triggered.connect(self._open_subroutine)
        self.ui.action_statistics_period_count.triggered.connect(
            self._open_subroutine
        )  # 診數統計

        self.ui.action_statistics_branch_project.triggered.connect(
            self._open_subroutine
        )
        self.ui.action_statistics_branch_daily.triggered.connect(self._open_subroutine)

        self.ui.action_statistics_commission.triggered.connect(
            self._open_subroutine
        )  # 自費抽成統計

        self.ui.action_ic_card.triggered.connect(self.open_ic_card)
        self.ui.action_show_side_bar.triggered.connect(self.switch_side_bar)

        self.ui.action_certificate_diagnosis.triggered.connect(
            self._open_subroutine
        )  # 申請診斷證明書
        self.ui.action_certificate_payment.triggered.connect(
            self._open_subroutine
        )  # 申請醫療費用證明書

        self.ui.action_massage_registration.triggered.connect(self._open_subroutine)

        self.ui.action_event_log.triggered.connect(self._open_subroutine)

        self.ui.tabWidget_window.tabCloseRequested.connect(self.close_tab)  # 關閉分頁
        self.ui.tabWidget_window.currentChanged.connect(self.tab_changed)  # 切換分頁

        self.ui.action_case_template.triggered.connect(
            self._open_case_template
        )  # 參考病歷
        self.ui.action_commission_summary.triggered.connect(
            self._open_subroutine
        )  # 業績抽成統計
        self.ui.action_sales_summary.triggered.connect(
            self._open_subroutine
        )  # 業績金額統計

        self.ui.action_course_accomplish.triggered.connect(
            self._open_subroutine
        )  # 自費療程實現
        self.ui.action_export_table_to_json.triggered.connect(
            self._export_table_to_json
        )  # 匯出指定資料至json

        self.ui.action_statistics_correction_reg.triggered.connect(
            self._open_subroutine
        )  # 矯正機關內門診報表
        self.ui.action_import_home_care.triggered.connect(
            self._open_import_home_care
        )  # 居家藍芽資料匯入
        self.ui.action_supplier.triggered.connect(
            self._open_subroutine
        )  # 廠商資料 2022.09.08 安聲

        self.ui.action_stock_in.triggered.connect(self._open_subroutine)  # 進貨
        self.ui.action_stock_dispense.triggered.connect(self._open_subroutine)  # 進貨
        self.ui.action_stock_out.triggered.connect(self._open_subroutine)  # 出貨
        self.ui.action_stock_replenishment.triggered.connect(
            self._open_subroutine
        )  # 補貨
        self.ui.action_stock_inventory.triggered.connect(self._open_subroutine)  # 盤點
        self.ui.action_goods.triggered.connect(self._open_subroutine)  # 進貨商品資料
        self.ui.action_physiotherapy.triggered.connect(
            self._open_subroutine
        )  # 物理治療預約
        self.ui.action_stamp_duty.triggered.connect(
            self._open_subroutine
        )  # 自費印花稅統計

        self.ui.action_create_cshis6_shortcut.triggered.connect(
            self._create_shortcut
        )  # 產生讀卡機控制軟體6.0捷徑

    # 設定 css style
    def _set_style(self):
        self.ui.label_system_name.setText(f"<b>{self.clinic_name} 醫療資訊管理系統</b>")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        # self.ui.label_system_name.setGraphicsEffect(shadow)

        self.ui.label_system_owner.setText(
            "<b>百會資訊<br>統編:92551655<br>0911971800</b>"
        )
        self.ui.label_system_owner.setStyleSheet("color: yellow")
        shadow1 = QtWidgets.QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(15)
        self.ui.label_system_owner.setGraphicsEffect(shadow1)

        system_utils.set_background_image(self.ui.tab_home, self.system_settings)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        system_utils.set_theme(self.ui, self.system_settings)

        self._set_button_style()

    def _set_button_style(self):
        self._set_hyper_link_button()
        self._set_registration_button()
        self._set_doctor_button()
        self._set_settings_button()
        self._set_system_button()

    def _set_hyper_link_button(self):
        tool_button_list = [
            self.ui.toolButton_nhi_vpn,
            self.ui.toolButton_nhi_vpn_new,
            self.ui.toolButton_mohw,
            self.ui.toolButton_hca,
            self.ui.toolButton_nhi,
            self.ui.toolButton_hpa,
            self.ui.toolButton_nucmda,
            self.ui.toolButton_tpcma,
            self.ui.toolButton_sbcma,
            self.ui.toolButton_klcma,
            self.ui.toolButton_tycma,
            self.ui.toolButton_hctcma,
            self.ui.toolButton_hccma,
            self.ui.toolButton_mlcma,
            self.ui.toolButton_med_vpn,
        ]
        self._set_tool_button_shadow(tool_button_list)

    def _set_tool_button_shadow(self, tool_button_list):
        blur_radius = 30

        shadow_list = []
        for i in range(len(tool_button_list)):
            shadow_list.append(QtWidgets.QGraphicsDropShadowEffect())
            shadow_list[i].setBlurRadius(blur_radius)
            tool_button_list[i].setGraphicsEffect(shadow_list[i])

    def _set_registration_button(self):
        tool_button_list = [
            self.ui.pushButton_registration,
            self.ui.pushButton_reservation,
            self.ui.pushButton_cashier,
            self.ui.pushButton_return_card,
            self.ui.pushButton_debt,
            self.ui.pushButton_checkout,
            self.ui.pushButton_patient_list,
            self.ui.pushButton_ic_record_upload,
            self.ui.pushButton_purchase,
        ]
        self._set_tool_button_shadow(tool_button_list)

    def _set_doctor_button(self):
        tool_button_list = [
            self.ui.pushButton_waiting_list,
            self.ui.pushButton_medical_record_list,
        ]
        self._set_tool_button_shadow(tool_button_list)

    def _set_settings_button(self):
        tool_button_list = [
            self.ui.pushButton_settings,
            # self.ui.pushButton_charge,
            self.ui.pushButton_diagnostic,
            self.ui.pushButton_medicine,
            self.ui.pushButton_ic_card,
        ]
        self._set_tool_button_shadow(tool_button_list)

    def _set_system_button(self):
        tool_button_list = [
            self.ui.pushButton_logout,
            self.ui.pushButton_quit,
        ]
        self._set_tool_button_shadow(tool_button_list)

    # 候診名單歸零
    def reset_wait(self):
        # current_date = date_utils.get_time_server_date()
        current_date = datetime.datetime.today().strftime("%Y-%m-%d")
        today = f"{current_date} 00:00:00"
        tonight = f"{current_date} 23:59:59"
        sql = f'''
            DELETE FROM wait
            WHERE
                CaseDate < "{today}" OR
                CaseDate > "{tonight}"
        '''
        self.database.exec_sql(sql)

        sql = f'''
            DELETE FROM seq_number
            WHERE
                CaseDate < "{today}" OR
                CaseDate > "{tonight}"
        '''
        self.database.exec_sql(sql)

    # 設定按鈕權限
    def _set_button_enabled(self):
        if self.system_settings.field("使用讀卡機") == "Y":
            self.ui.pushButton_ic_card.setEnabled(True)
        else:
            self.ui.pushButton_ic_card.setEnabled(False)

    # tab 切換
    def tab_changed(self, i):
        for x in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(x) == "門診掛號":
                tabx = self.ui.tabWidget_window.widget(x)
                tabx.dialog_history.close()
                break

        tab_name = self.ui.tabWidget_window.tabText(i)
        tab = self.ui.tabWidget_window.currentWidget()
        if tab_name in ["門診掛號", "醫師看診作業", "批價作業"]:
            tab.read_wait()
            if tab_name in ["醫師看診作業"] and self.set_waiting_list == "Y":
                tab.reset_tab_widget()
        elif tab_name in ["藥局作業"]:
            tab.refresh_wait()
        elif tab_name == "健保卡欠還卡":
            tab.read_return_card()
        elif tab_name == "退貨":
            tab.read_return_goods()
        elif tab_name == "欠還款作業":
            tab.read_debt()
        elif tab_name == "預約掛號":
            tab.tabWidget_reservation.setCurrentIndex(0)
            tab.read_reservation(set_combo_doctor=True)

    # 按鍵驅動
    def _open_subroutine(self, action=None):
        # tab_name = self.sender().text()
        tab_name = action.text() if action else self.sender().text()

        if tab_name == "醫師看診作業":
            self._add_tab(
                tab_name, self.database, self.system_settings, self.statistics_dicts
            )
        elif tab_name == "病歷查詢":
            self._add_tab(tab_name, self.database, self.system_settings, None)
        elif tab_name == "參考病歷":
            self._add_tab(
                tab_name, self.database, self.system_settings, None, "參考病歷"
            )
        elif tab_name == "檢驗報告登錄":
            self._add_tab(
                tab_name, self.database, self.system_settings, None, None, None
            )
        elif tab_name in ["醫療費用證明書", "健保卡欠還卡"]:
            self._add_tab(tab_name, self.database, self.system_settings, None)
        elif tab_name == "清冠一號補助清冊":
            self._add_tab(
                tab_name,
                self.database,
                self.system_settings,
                None,
                None,
                None,
                None,
                None,
            )
        else:
            self._add_tab(tab_name, self.database, self.system_settings)

    # 新增tab
    def _add_tab(self, tab_name, *args):
        if self.tab_exists(tab_name):
            if "自動產生醫療費用證明" in tab_name:
                self.close_tab_by_name(tab_name)
            else:
                return

        module_class = module_utils.get_module(tab_name)
        if module_class is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "模組載入失敗",
                f'<font color="red"><h3>無法載入「{tab_name}」模組!</h3></font>',
                "程式檔案可能不完整, 請執行醫療軟體更新後重新啟動系統.",
            )
            return None

        module = module_class(self, *args)

        self.ui.tabWidget_window.addTab(module, tab_name)
        self.ui.tabWidget_window.setCurrentWidget(module)
        if tab_name == "病歷查詢" and args[2] is not None:  # args[2] = patient_key
            pass
        else:
            self._set_focus(tab_name, module)

        return module

    # 設定 focus
    @staticmethod
    def _set_focus(widget_name, widget):
        if widget_name in ["門診掛號", "自費療程實現"]:
            widget.ui.lineEdit_query.setFocus()

        if widget_name in [
            "掛號櫃台結帳",
            "病患查詢",
            "病歷查詢",
            "檢驗報告查詢",
            "病歷統計",
            "健保IC卡資料上傳",
            "申報檢查",
            "健保申報",
            "健保抽審",
            "健保申復",
            "孕產照護報表",
            "照護機構院民資料報表",
            "矯正機關內門診報表",
            "自費銷售記錄",
            "自費銷售抽成總表",
            "醫師自費銷售金額總表",
            "日報表",
            "醫師統計",
            "醫師金額統計",
            "醫師處方類別抽成統計",
            "醫師月報表",
            "回診率統計",
            "未回診統計",
            "用藥統計",
            "健保申報業績",
            "醫師銷售業績統計",
            "健保門診優惠統計",
            "綜合業績報表",
            "業績成長統計",
            "自費抽成統計",
            "推拿師統計",
            "分院專案統計",
            "分院日報表",
            "診數統計",
            "養生館櫃台結帳",
            "消費資料查詢",
            "養生館統計",
            "自費印花稅統計",
            "執行業務所得統計",
            "何處得知本診所統計",
            "病患優待身份統計",
            "健保申報分列項目表",
            "年度診次統計",
            "銷貨",
        ]:
            widget.open_dialog()
        elif widget_name == "醫師看診作業":
            widget.ui.tableWidget_waiting_list.setFocus()
        elif widget_name == "新病患資料":
            widget.ui.tab_patient_data.lineEdit_name.setFocus()
        elif "病歷資料" in widget_name:
            widget.set_focus()

    # 關閉 tab
    def close_tab(self, current_index):
        current_tab = self.ui.tabWidget_window.widget(current_index)
        tab_name = self.ui.tabWidget_window.tabText(current_index)
        if tab_name == "首頁":
            return

        if not self._tab_is_closable(tab_name, current_tab):
            return

        current_tab.close_all()
        current_tab.deleteLater()
        self.ui.tabWidget_window.removeTab(current_index)
        if (
            tab_name.find("病歷資料") != -1
            or tab_name.find("病患資料") != -1
            or tab_name.find("養生館購買商品") != -1
            or tab_name.find("購買商品") != -1
        ):
            self._set_tab(current_tab.call_from)

    # 關閉 tab
    def close_tab_by_name(self, tab_name):
        current_index = None
        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == tab_name:
                current_index = i
                break

        if current_index is None:
            return

        current_tab = self.ui.tabWidget_window.widget(current_index)
        current_tab.close_all()
        current_tab.deleteLater()
        self.ui.tabWidget_window.removeTab(current_index)

    # 關閉分頁
    @staticmethod
    def _tab_is_closable(tab_name, current_tab):
        closable = True

        if tab_name.find("病歷資料") == -1:
            return closable

        if current_tab.call_from == "離開不存檔":
            return closable

        if current_tab.call_from == "醫師看診作業":
            if not current_tab.record_saved and not current_tab.is_doctor_done():
                current_tab.update_medical_record(check_prescript=False)

            return closable

        record_modified = current_tab.record_modified()
        if not record_modified:
            return closable

        if not current_tab.record_saved:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("關閉病歷資料")
            msg_box.setText(
                "<font size='4' color='red'><b>病歷資料已被變更, 確定離開病歷資料而不存檔?</b></font>"
            )
            msg_box.setInformativeText(
                "注意！選擇不存檔而關閉病歷資料後, 之前所輸入的病歷資料將會回復原來狀態."
            )
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)  # 0
            msg_box.addButton(QPushButton("存檔"), QMessageBox.AcceptRole)  # 1
            msg_box.addButton(QPushButton("不存檔"), QMessageBox.YesRole)  # 2
            quit_medical_record = msg_box.exec_()
            if not quit_medical_record:
                closable = False
            else:
                closable = True

            if quit_medical_record == 1:  # 存檔
                current_tab.save_medical_record()

        return closable

    # 檢查是否開啟tab
    def tab_exists(self, tab_text):
        if self.ui.tabWidget_window.count() <= 0:
            return False

        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == tab_text:
                self.ui.tabWidget_window.setCurrentIndex(i)
                return True

        return False

    # 打開指定的tab
    def _set_tab(self, tab_name):
        if self.ui.tabWidget_window.count() <= 0:
            return False

        if tab_name == "醫師看診作業-查詢":
            tab_name = "醫師看診作業"

        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == tab_name:
                current_tab = self.ui.tabWidget_window.widget(i)
                self.ui.tabWidget_window.setCurrentIndex(i)
                if tab_name == "病歷查詢":
                    current_tab.ui.tableWidget_medical_record_list.setFocus(True)
                    current_tab.refresh_medical_record()
                elif tab_name == "醫師看診作業":
                    current_tab.refresh_medical_record()
                elif tab_name == "病患查詢":
                    current_tab.ui.tableWidget_patient_list.setFocus(True)
                    current_tab.refresh_patient_record()
                elif tab_name == "櫃台購藥":
                    current_tab.ui.tableWidget_purchase_list.setFocus(True)
                    case_key = current_tab.get_case_key()
                    current_tab.refresh_purchase(case_key)
                elif tab_name == "養生館購物":
                    current_tab.ui.tableWidget_purchase_list.setFocus(True)
                    current_tab.read_purchase_today()
                elif tab_name == "門診掛號":
                    current_tab.read_wait()
                elif tab_name == "消費資料查詢" or tab_name == "養生館櫃台結帳":
                    current_tab.refresh_massage_case()
                elif tab_name == "申報檢查":
                    current_tab.refresh_medical_record()
                elif tab_name == "照護機構院民資料報表":
                    current_tab.refresh_patient_record()

                return current_tab

        return None

    # 開啟病歷資料
    def open_examination(self, examination_key):
        if examination_key is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無檢驗報告資料",
                '<font color="red"><h3>檢驗檔主鍵遺失, 請重新查詢!</h3></font>',
                "請至檢驗報告查詢確認此筆資料是否存在.",
            )
            return

        sql = f"""
            SELECT Name, ExaminationDate FROM examination
            WHERE
                ExaminationKey = {examination_key}
        """
        rows = self.database.select_record(sql)
        name = string_utils.xstr(rows[0]["Name"])
        examination_date = string_utils.xstr(rows[0]["ExaminationDate"])
        tab_name = f"檢驗報告-{name}-{examination_date}"

        self._add_tab(
            tab_name, self.database, self.system_settings, examination_key, None, None
        )

    # 開啟病歷資料
    def create_certificate_payment(self, auto_create_list):
        name = auto_create_list[1]
        start_date = auto_create_list[4]
        tab_name = f"自動產生醫療費用證明書-{name}-{start_date}"

        self._add_tab(tab_name, self.database, self.system_settings, auto_create_list)

    # 開啟病歷資料
    def open_return_card(self, patient_key):
        tab_name = "健保卡欠還卡"
        self._add_tab(tab_name, self.database, self.system_settings, patient_key)

    # 查詢病歷資料
    def open_medical_record_list(self, patient_key):
        tab_name = "病歷查詢"

        self._add_tab(tab_name, self.database, self.system_settings, patient_key)
        current_tab = self._set_tab(tab_name)
        current_tab.open_medical_record_list(patient_key)

    # 開啟病歷資料
    def open_medical_record(
        self, case_key, call_from=None, current_user=None, archive_database=None
    ):
        if archive_database is not None:
            database = archive_database
        else:
            database = self.database

        if case_key is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無病歷資料",
                '<font color="red"><h3>病歷主鍵遺失, 請重新查詢!</h3></font>',
                "請至病歷查詢確認此筆資料是否存在.",
            )
            return

        sql = f"""
            SELECT
                CaseKey, CaseDate, PatientKey, Name, InsType, Doctor
            FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = database.select_record(sql)

        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無病歷資料",
                f'<font color="red"><h3>找不到病歷主鍵{case_key}的資料, 請重新查詢!</h3></font>',
                "請至病歷查詢確認此筆資料是否存在.",
            )
            return

        row = rows[0]
        # doctor = string_utils.xstr(row['Doctor'])

        position_list = personnel_utils.get_person(database, "醫師")
        if call_from == "醫師看診作業" and self.user_name not in position_list:
            if (
                personnel_utils.get_permission(
                    database, call_from, "非醫師病歷登錄", self.user_name
                )
                != "Y"
            ):
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "使用者非醫師",
                    '<font color="red"><h3>登入的使用者並非醫師, 無法進行病歷看診作業!</h3></font>',
                    "請重新以醫師身份登入系統.",
                )
                return

        # if call_from == '醫師看診作業' and current_user is not None and current_user != doctor:
        #     msg_box = dialog_utils.get_message_box(
        #         '友善提醒',
        #         QMessageBox.Question,
        #         f'<font color="blue"><h3>此病歷的主治醫師為{doctor}, 請確認是否繼續?</h3></font>',
        #         '如果繼續登錄病歷, 存檔後主治醫師將會變成您的名字.'
        #     )
        #     edit_medical_record = msg_box.exec_()
        #     if not edit_medical_record:
        #         return

        case_key = row["CaseKey"]
        name = string_utils.xstr(row["Name"])
        try:
            case_date = string_utils.xstr(row["CaseDate"].date())
        except Exception:
            case_date = None

        ins_type = string_utils.xstr(row["InsType"])

        tab_name = f"{case_key}-{name}-{ins_type}病歷資料-{case_date}"
        self._add_tab(tab_name, database, self.system_settings, case_key, call_from)

    # 新增自費病歷
    def append_self_medical_record(self, case_key, patient_key, name):
        tab_name = f"{patient_key}-{name}-自費病歷資料"
        self._add_tab(
            tab_name,
            self.database,
            self.system_settings,
            case_key,
            "新增自費病歷",
            patient_key,
        )

    # 新增加購自費病歷 2025.12.27 林胤谷
    def append_extra_medical_record(self, case_key, patient_key, name):
        tab_name = f"{patient_key}-{name}-加購病歷資料"
        self._add_tab(
            tab_name,
            self.database,
            self.system_settings,
            case_key,
            "加購自費病歷",
            patient_key,
        )

    def _open_case_template(self):
        tab_name = "參考病歷"
        self._add_tab(tab_name, self.database, self.system_settings, None, "參考病歷")

    # 開啟病患資料
    def open_patient_record(self, patient_key, call_from=None, ic_card=None):
        if patient_key is None:
            tab_name = "新病患資料"
            self._add_tab(
                tab_name,
                self.database,
                self.system_settings,
                patient_key,
                call_from,
                ic_card,
            )
            return

        script = f"""
            SELECT PatientKey, Name FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        try:
            row = self.database.select_record(script)[0]
        except IndexError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("查無病患資料")
            msg_box.setText(
                "<font size='4' color='red'><b>雖然掛號資料存在, 但是病歷資料因不明原因遺失!</b></font>"
            )
            msg_box.setInformativeText("請至掛號作業刪除此筆掛號資料並重新掛號.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        tab_name = f"{row['PatientKey']}-{row['Name']}-病患資料"
        self._add_tab(
            tab_name,
            self.database,
            self.system_settings,
            row["PatientKey"],
            call_from,
            None,
        )

    # 預約掛號
    def open_reservation(self, reserve_key, patient_key, doctor, vhc_ic_card=None):
        tab_name = "預約掛號"
        if self.tab_exists(tab_name):
            current_tab = None
            for i in range(self.ui.tabWidget_window.count()):
                if self.ui.tabWidget_window.tabText(i) == tab_name:
                    current_tab = self.ui.tabWidget_window.widget(i)
                    if doctor is not None and patient_key is not None:
                        current_tab.set_doctor_and_patient(doctor, patient_key)
                    else:
                        current_tab.set_doctor_and_patient(
                            None, None, vhc_ic_card=vhc_ic_card
                        )

                    break
        else:
            current_tab = self._add_tab(
                tab_name,
                self.database,
                self.system_settings,
                reserve_key,
                patient_key,
                doctor,
                vhc_ic_card,
            )

        if reserve_key is not None:
            current_tab.set_reservation_arrival(reserve_key, vhc_ic_card)

    # 櫃台購藥
    def open_purchase_tab(self):
        tab_name = "購買商品"
        self._add_tab(tab_name, self.database, self.system_settings, "櫃台購藥")

    # 預約掛號
    def registration_arrival(
        self, reserve_key, late=False, late_remark="預約報到過號", vhc_ic_card=None
    ):
        tab_name = "門診掛號"
        self._add_tab(tab_name, self.database, self.system_settings)

        current_tab = None
        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == tab_name:
                current_tab = self.ui.tabWidget_window.widget(i)
                break

        current_tab.reservation_arrival(
            reserve_key, late, late_remark=late_remark, vhc_ic_card=vhc_ic_card
        )

    # 初診掛號
    def set_new_patient(self, new_patient_key):
        current_tab = None
        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == "門診掛號":
                current_tab = self.ui.tabWidget_window.widget(i)
                break

        if current_tab is None:
            return

        current_tab.ui.lineEdit_query.setText(str(new_patient_key))
        current_tab.query_patient()

    # 檢驗所報告
    def open_exam_result(self):
        url = self.system_settings.field("檢驗所伺服器")
        hosp_id = self.system_settings.field("檢驗所用戶代碼")
        login_pws = self.system_settings.field("檢驗所密碼")

        if url is None or hosp_id is None or login_pws is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "參數未設定",
                '<font size="5" color="red"><b>系統設定內沒有設定醫事檢驗所連線資訊, 無法取得檢驗資料.</b></font>',
                "請至系統設定完成醫師檢驗所連線各項設定.",
            )
            return

        dialog = dialog_utils.get_dialog_exam_result(
            self, self.database, self.system_settings, None
        )
        dialog.exec_()
        dialog.deleteLater()

    # 系統設定
    def open_settings(self):
        dialog = dialog_utils.get_dialog_system_settings(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()
        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )
        self.label_station_no.setText(
            f"工作站編號: {self.system_settings.field('工作站編號')}"
        )
        self._set_button_enabled()

    # 功能表醒目設定
    def open_menu_setting(self):
        dialog = dialog_utils.get_dialog_menu_setting(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 教學影片
    def open_tutorial_videos(self):
        dialog = dialog_utils.get_dialog_tutorial_videos(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 候診系統設定
    def open_bulletin_settings(self):
        dialog = dialog_utils.get_dialog_bulletin_settings(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 掛號機零錢箱設定
    def open_cashier_machine_settings(self):
        dialog = dialog_utils.get_dialog_cashier_machine_settings(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 分院資料設定
    def open_hosts_settings(self):
        dialog = dialog_utils.get_dialog_hosts(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 匯入病歷
    def open_import_medical_record(self):
        dialog = dialog_utils.get_dialog_import_medical_record(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 匯入居家藍芽病歷
    def _open_import_home_care(self):
        dialog = dialog_utils.get_dialog_import_home_care(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 健保卡讀卡機
    def open_ic_card(self):
        dialog = dialog_utils.get_dialog_ic_card(
            self, self.database, self.system_settings
        )
        if dialog.ic_card is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "無法驅動讀卡機",
                '<font size="5" color="red"><b>無法載入健保讀卡機驅動程式, 無法執行健保卡掛號.</b></font>',
                "請確定讀卡機驅動程式是否正確.",
            )
            dialog.deleteLater()
            return

        dialog.exec_()
        dialog.deleteLater()

    # 重新連線資料庫
    def reconnect_database(self):
        self._set_db(self.config_file)
        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )

        if self.database.connected():
            system_utils.show_message_box(
                QMessageBox.Information,
                "資料庫重新連線",
                '<font size="5" color="blue"><b>資料庫連線成功, 請繼續使用系統.</b></font>',
                "網路連線正常.",
            )
        else:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "資料庫重新連線",
                '<font size="5" color="red"><b>資料庫連線失敗, 請關閉醫療系統重新進入.</b></font>',
                "網路連線失敗, 請檢查網路狀態.",
            )

    # 轉檔
    def convert(self):
        dialog = module_utils.get_convert(self, self.database, self.system_settings)
        dialog.exec_()
        dialog.deleteLater()

    def export_emr_xml(self):
        dialog = dialog_utils.get_dialog_export_emr_xml(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    def export_medical_record_json(self):
        dialog = dialog_utils.get_dialog_export_medical_record_json(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    def export_all_database(self):
        options = QFileDialog.Options()
        mysql_file_name, _ = QFileDialog.getSaveFileName(
            self, "匯出資料庫檔案", "pymedical.sql", "sql檔案 (*.sql)", options=options
        )
        if not mysql_file_name:
            return

        self.export_database(mysql_file_name)

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料庫匯出完成",
            f"<h3>資料庫{mysql_file_name}匯出完成.</h3>",
            "此為敏感性資料，請小心使用，切勿外洩.",
        )

    # 就醫診療資料寫入作業
    def export_database(self, export_filename):
        title = "匯出全部資料庫"
        message = (
            '<font size="5" color="red"><b>正在匯出全部資料庫中, 請稍後...</b></font>'
        )
        hint = "匯出的時間會依照資料庫的大小, 花費一些時間."
        msg_box = dialog_utils.message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(
            target=self._export_database_thread, args=(msg_queue, export_filename)
        )
        t.start()
        (error_code) = msg_queue.get()
        msg_box.close()

        return error_code

    def _export_database_thread(self, out_queue, export_filename):
        QtCore.QCoreApplication.processEvents()
        error_code = system_utils.dump_database(self.database, None, export_filename)

        out_queue.put(error_code)

    # 匯入全部資料庫
    def import_all_database(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("匯入全部資料庫")
        msg_box.setText(
            "<font size='4' color='red'><b>確定匯入全部資料庫, 並取代原來的資料庫?</b></font>"
        )
        msg_box.setInformativeText(
            "注意！資料匯入後, 原來的病歷資料將會全部消失, 並以新的匯入資料庫取代!"
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        import_database = msg_box.exec_()
        if not import_database:
            return

        options = QFileDialog.Options()
        restore_filename, _ = QFileDialog.getOpenFileName(
            self, "匯入資料庫檔案", "pymedical.sql", "sql檔案 (*.sql)", options=options
        )
        if not restore_filename:
            return

        self.import_database(restore_filename)

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料庫匯入完成",
            f"<h3>資料庫{restore_filename}匯入完成.</h3>",
            "請確認匯入的資料是否完整.",
        )

    # 就醫診療資料寫入作業
    def import_database(self, import_filename):
        title = "匯入全部資料庫"
        message = (
            '<font size="5" color="red"><b>正在匯入全部資料庫中, 請稍後...</b></font>'
        )
        hint = "匯入的時間會依照資料庫的大小, 花費一些時間."
        msg_box = dialog_utils.message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(
            target=self._import_database_thread, args=(msg_queue, import_filename)
        )
        t.start()
        (error_code) = msg_queue.get()
        msg_box.close()

        return error_code

    @staticmethod
    def _import_database_thread(out_queue, restore_filename):
        QtCore.QCoreApplication.processEvents()
        error_code = system_utils.import_database(restore_filename)

        out_queue.put(error_code)

    # 設定權限
    def set_root_permission(self):
        if self.user_name != "超級使用者":
            self.ui.action_convert.setEnabled(False)
        else:
            self.ui.action_convert.setEnabled(True)

    def _authorize_all_permission(self):
        action_list = [
            self.ui.pushButton_registration,
            self.ui.pushButton_reservation,
            self.ui.pushButton_cashier,
            self.ui.pushButton_return_card,
            self.ui.pushButton_settings,
            self.ui.pushButton_debt,
            self.ui.pushButton_checkout,
            self.ui.pushButton_patient_list,
            self.ui.pushButton_waiting_list,
            self.ui.pushButton_ic_record_upload,
            self.ui.pushButton_medical_record_list,
            self.ui.pushButton_purchase,
            # self.ui.pushButton_charge,
            self.ui.pushButton_diagnostic,
            self.ui.pushButton_medicine,
            self.ui.pushButton_ic_card,
            self.ui.action_registration,
            self.ui.action_reservation,
            self.ui.action_cashier,
            self.ui.action_return_card,
            self.ui.action_purchase,
            self.ui.action_checkout,
            self.ui.action_patient_list,
            self.ui.action_ins_record_upload,
            self.ui.action_waiting_list,
            self.ui.action_medical_record_list,
            self.ui.action_medical_record_statistics,
            self.ui.action_settings,
            self.ui.action_charge,
            self.ui.action_diagnostic,
            self.ui.action_medicine,
            self.ui.action_ic_card,
            self.ui.action_doctor_schedule,
            self.ui.action_pharmacist_schedule,
            self.ui.action_doctor_nurse_table,
            self.ui.action_users,
            self.ui.action_ins_drug,
            self.ui.action_export_emr_xml,
            self.ui.action_update,
            self.ui.action_restore_records,
            self.ui.action_certificate_diagnosis,
            self.ui.action_certificate_payment,
            self.ui.action_ins_check,
            self.ui.action_ins_apply,
            self.ui.action_ins_judge,
            self.ui.action_ins_appeal,
            self.ui.menu_registration,
            self.ui.menu_doctor,
            self.ui.menu_administrative,
            self.ui.menu_purchase,
            self.ui.menu_insurance,
            self.ui.menu_statistics,
            self.ui.menu_host,
            self.ui.menu_stock,
            self.ui.menu_settings,
            self.ui.menu_system,
            self.ui.action_statistics_doctor,
            self.ui.action_statistics_commission,
            self.ui.action_statistics_return_rate,
            self.ui.action_statistics_medicine,
            self.ui.action_statistics_ins_performance,
            self.ui.action_statistics_doctor_commission,
            self.ui.action_statistics_ins_performance,
            self.ui.action_statistics_multiple_performance,
            self.ui.action_statistics_ins_discount,
            self.ui.action_statistics_doctor_amount,
            self.ui.action_statistics_doctor_medicine,
            self.ui.action_convert,
            self.ui.action_export_all_database,
            self.ui.action_statistics_daily,
            self.ui.action_statistics_doctor_monthly,
            self.ui.action_statistics_period_count,
            self.ui.action_statistics_no_return_rate,
            self.ui.action_statistics_growth_rate,
            self.ui.action_statistics_massager,
            self.ui.action_business_income,
        ]

        for action in action_list:
            action.setEnabled(True)

    # 設定權限
    def set_permission(self):
        self._authorize_all_permission()
        self._set_user_name()

        if self.user_name == "超級使用者":
            return

        import copy

        # 如果不copy, 會影響到 dialog_permission
        person_list = copy.deepcopy(personnel_utils.PERMISSION_LIST)

        for item in person_list:
            if string_utils.xstr(item[1]) == "執行門診掛號":
                item.append(
                    [self.ui.pushButton_registration, self.ui.action_registration]
                )
            elif string_utils.xstr(item[1]) == "執行預約掛號":
                item.append(
                    [
                        self.ui.pushButton_reservation,
                        self.ui.action_reservation,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行批價作業":
                item.append(
                    [
                        self.ui.pushButton_cashier,
                        self.ui.action_cashier,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行健保卡欠還卡":
                item.append(
                    [
                        self.ui.pushButton_return_card,
                        self.ui.action_return_card,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行欠還款作業":
                item.append(self.ui.pushButton_debt)
            elif string_utils.xstr(item[1]) == "執行櫃台購藥":
                item.append(
                    [
                        self.ui.action_purchase,
                        self.ui.pushButton_purchase,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行退貨":
                item.append(self.ui.action_return_goods)
            elif string_utils.xstr(item[1]) == "執行掛號櫃台結帳":
                item.append(
                    [
                        self.ui.pushButton_checkout,
                        self.ui.action_checkout,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行病患查詢":
                item.append(
                    [
                        self.ui.pushButton_patient_list,
                        self.ui.action_patient_list,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行健保IC卡資料上傳":
                item.append(
                    [
                        self.ui.pushButton_ic_record_upload,
                        self.ui.action_ins_record_upload,
                    ]
                )

            elif string_utils.xstr(item[1]) == "執行醫師看診作業":
                item.append(
                    [
                        self.ui.pushButton_waiting_list,
                        self.ui.action_waiting_list,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行病歷查詢":
                item.append(
                    [
                        self.ui.pushButton_medical_record_list,
                        self.ui.action_medical_record_list,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行系統設定":
                item.append(
                    [
                        self.ui.pushButton_settings,
                        self.ui.action_settings,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行收費設定":
                item.append(
                    [
                        # self.ui.pushButton_charge,
                        self.ui.action_charge,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行診察資料":
                item.append(
                    [
                        self.ui.pushButton_diagnostic,
                        self.ui.action_diagnostic,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行處方資料":
                item.append(
                    [
                        self.ui.pushButton_medicine,
                        self.ui.action_medicine,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行健保卡讀卡機":
                item.append(
                    [
                        self.ui.pushButton_ic_card,
                        self.ui.action_ic_card,
                    ]
                )
            elif string_utils.xstr(item[1]) == "執行醫師班表":
                item.append(self.ui.action_doctor_schedule)
            elif string_utils.xstr(item[1]) == "執行藥師班表":
                item.append(self.ui.action_pharmacist_schedule)
            elif string_utils.xstr(item[1]) == "執行護士跟診表":
                item.append(self.ui.action_doctor_nurse_table)
            elif string_utils.xstr(item[1]) == "執行使用者管理":
                item.append(self.ui.action_users)
            elif string_utils.xstr(item[1]) == "執行健保藥品":
                item.append(self.ui.action_ins_drug)
            elif string_utils.xstr(item[1]) == "執行匯出電子病歷交換檔":
                item.append(self.ui.action_export_emr_xml)
            elif string_utils.xstr(item[1]) == "執行醫療軟體更新":
                item.append(self.ui.action_update)
            elif string_utils.xstr(item[1]) == "執行資料回復":
                item.append(self.ui.action_restore_records)

            elif string_utils.xstr(item[1]) == "執行診斷證明書":
                item.append(self.ui.action_certificate_diagnosis)
            elif string_utils.xstr(item[1]) == "執行醫療費用證明書":
                item.append(self.ui.action_certificate_payment)

            elif string_utils.xstr(item[1]) == "執行申報檢查":
                item.append(self.ui.action_ins_check)
            elif string_utils.xstr(item[1]) == "執行健保申報":
                item.append(self.ui.action_ins_apply)
            elif string_utils.xstr(item[1]) == "執行健保抽審":
                item.append(self.ui.action_ins_judge)
            elif string_utils.xstr(item[1]) == "執行健保申復":
                item.append(self.ui.action_ins_appeal)

            elif string_utils.xstr(item[1]) == "關閉掛號作業":
                item.append(self.ui.menu_registration)
            elif string_utils.xstr(item[1]) == "關閉診療作業":
                item.append(self.ui.menu_doctor)
            elif string_utils.xstr(item[1]) == "關閉醫務行政":
                item.append(self.ui.menu_administrative)
            elif string_utils.xstr(item[1]) == "關閉自費管理":
                item.append(self.ui.menu_purchase)
            elif string_utils.xstr(item[1]) == "關閉申報作業":
                item.append(self.ui.menu_insurance)
            elif string_utils.xstr(item[1]) == "關閉統計表":
                item.append(self.ui.menu_statistics)
            elif string_utils.xstr(item[1]) == "關閉分院統計":
                item.append(self.ui.menu_host)
            elif string_utils.xstr(item[1]) == "關閉進銷存管理":
                item.append(self.ui.menu_stock)
            elif string_utils.xstr(item[1]) == "關閉設定":
                item.append(self.ui.menu_settings)
            elif string_utils.xstr(item[1]) == "關閉系統作業":
                item.append(self.ui.menu_system)

            elif string_utils.xstr(item[1]) == "執行醫師統計":
                item.append(self.ui.action_statistics_doctor)
            elif string_utils.xstr(item[1]) == "執行醫師金額統計":
                item.append(self.ui.action_statistics_doctor_amount)
            elif string_utils.xstr(item[1]) == "執行醫師處方類別抽成統計":
                item.append(self.ui.action_statistics_doctor_medicine)
            elif string_utils.xstr(item[1]) == "執行自費抽成統計":
                item.append(self.ui.action_statistics_commission)
            elif string_utils.xstr(item[1]) == "執行回診率統計":
                item.append(self.ui.action_statistics_return_rate)
            elif string_utils.xstr(item[1]) == "執行用藥統計":
                item.append(self.ui.action_statistics_medicine)
            elif string_utils.xstr(item[1]) == "執行健保申報業績":
                item.append(self.ui.action_statistics_ins_performance)
            elif string_utils.xstr(item[1]) == "執行醫師銷售業績統計":
                item.append(self.ui.action_statistics_doctor_commission)
            elif string_utils.xstr(item[1]) == "執行健保門診優惠統計":
                item.append(self.ui.action_statistics_ins_discount)
            elif string_utils.xstr(item[1]) == "執行綜合業績統計":
                item.append(self.ui.action_statistics_multiple_performance)
            elif string_utils.xstr(item[1]) == "執行業績成長統計":
                item.append(self.ui.action_statistics_growth_rate)
            elif string_utils.xstr(item[1]) == "執行匯出全部資料庫":
                item.append(self.ui.action_export_all_database)
            elif string_utils.xstr(item[1]) == "執行匯入全部資料庫":
                item.append(self.ui.action_import_all_database)

            elif string_utils.xstr(item[1]) == "執行日報表":
                item.append(self.ui.action_statistics_daily)
            elif string_utils.xstr(item[1]) == "執行醫師月報表":
                item.append(self.ui.action_statistics_doctor_monthly)
            elif string_utils.xstr(item[1]) == "執行診數統計":
                item.append(self.ui.action_statistics_period_count)
            elif string_utils.xstr(item[1]) == "執行未回診統計":
                item.append(self.ui.action_statistics_no_return_rate)
            elif string_utils.xstr(item[1]) == "執行推拿師統計":
                item.append(self.ui.action_statistics_massager)
            elif string_utils.xstr(item[1]) == "執行執行業務所得統計":
                item.append(self.ui.action_business_income)

            else:
                item.append(None)

        for item in person_list:
            action_name = string_utils.xstr(item[1])
            action = item[2]
            if action is None:
                continue

            if action_name in [
                "關閉掛號作業",
                "關閉診療作業",
                "關閉醫務行政",
                "關閉自費管理",
                "關閉申報作業",
                "關閉統計表",
                "關閉分院統計",
                "關閉進銷存管理",
                "關閉設定",
                "關閉系統作業",
            ]:
                if (
                    personnel_utils.get_permission(
                        self.database,
                        string_utils.xstr(item[0]),
                        action_name,
                        self.user_name,
                    )
                    == "Y"
                ):
                    action.setEnabled(False)

                continue

            if (
                personnel_utils.get_permission(
                    self.database,
                    string_utils.xstr(item[0]),
                    action_name,
                    self.user_name,
                )
                != "Y"
            ):
                if type(action) is list:
                    for act in action:
                        act.setEnabled(False)
                else:
                    action.setEnabled(False)

            ############################################## 例外狀況 ############################################################
            if (
                personnel_utils.get_permission(
                    self.database,
                    string_utils.xstr(item[0]),
                    "輸入成方資料",
                    self.user_name,
                )
                == "Y"
            ):
                self.ui.pushButton_medicine.setEnabled(True)

        if self.system_settings.field("執行匯入全部資料庫") != "Y":
            self.ui.action_import_all_database.setEnabled(False)

    # 重新顯示病歷登錄候診名單
    def _refresh_waiting_data(self, data):
        fields = data.split(",")
        clinic_name = fields[0] if len(fields) > 0 else ""
        call_from = fields[1] if len(fields) > 1 else ""
        doctor = fields[2] if len(fields) > 2 else None
        room = fields[3] if len(fields) > 3 else None

        if clinic_name != self.clinic_name:  # 其他分院呼叫
            return

        index = self.ui.tabWidget_window.currentIndex()
        current_tab_text = self.ui.tabWidget_window.tabText(index)

        if (
            self.beep_anywhere == "Y"
            and call_from in ["門診掛號"]
            and doctor == self.user_name
        ):
            self._notify_wait_arrive()

        if (
            current_tab_text not in ["門診掛號", "醫師看診作業", "批價作業", "藥局作業"]
            and "病歷資料" not in current_tab_text
        ):
            return

        tab = self.ui.tabWidget_window.currentWidget()

        refresh_wait_option = self.system_settings.field("候診名單顯示診別")
        room_no = self.system_settings.field("診療室")

        if call_from in ["門診掛號"]:
            if current_tab_text in ["門診掛號"]:
                tab.refresh_wait()
            elif current_tab_text in ["醫師看診作業"]:
                if doctor is not None and room is not None:
                    if (
                        (refresh_wait_option == "醫師診別" and self.user_name == doctor)
                        or (refresh_wait_option == "指定診別" and room_no == room)
                        or (refresh_wait_option == "所有診別")
                    ):
                        tab.read_wait()
                else:
                    tab.read_wait()

                self.start_flash()
            elif "病歷資料" in current_tab_text:  # 在病歷登錄頁面顯示目前看診人數
                tab.refresh_wait()
        elif call_from in ["醫師看診作業"]:
            if current_tab_text in ["門診掛號", "批價作業", "藥局作業"]:
                tab.refresh_wait()
                if current_tab_text in ["批價作業"]:
                    self._notify_wait_arrive()
            elif current_tab_text in ["醫師看診作業"]:
                tab.read_wait()
        elif call_from in ["批價作業", "藥局作業"]:
            if current_tab_text in ["批價作業", "藥局作業"]:
                tab.refresh_wait()
                if current_tab_text in ["藥局作業"]:
                    self._notify_wait_arrive()
        else:
            pass

    def _notify_wait_arrive(self):
        if self.no_beep == "Y":
            return

        now = time.monotonic()
        if now - self._last_beep_time < BEEP_COOLDOWN_SECONDS:
            return

        self._last_beep_time = now

        try:
            mixer.init()
            mixer.music.load("./icq.mp3")
            mixer.music.play()
        except pygame.error:
            pass

    # 廣播叫號
    def _broadcast_speech(self, json_data):
        try:
            voice_dict = json.loads(json_data)
        except Exception:
            return

        clinic_name = voice_dict["clinic_name"]
        if clinic_name != self.clinic_name:  # 其他分院呼叫
            return

        voice_data = voice_dict["sentence"]
        voice_utils.speak(voice_data, threading=True)

    # 重新顯示狀態列
    def refresh_status_bar(self):
        """重新更新狀態列."""
        today = datetime.datetime.today()
        weekday = date_utils.get_weekday_name(today.weekday())
        current_date = f"{today.strftime('%Y-%m-%d')} ({weekday[-1]})"
        self.label_today.setText(current_date)

        self.label_user_name.setText(f"使用者: {self.system_settings.field('使用者')}")
        self.label_station_no.setText(
            f"工作站編號: {self.system_settings.field('工作站編號')}"
        )
        self.label_db_engine.setText(f"資料引擎: {self.database.db_engine()}")
        self.label_ip.setText(f"本機IP: {self.system_settings.field('使用者IP')}")
        self.label_version.setText(f"版本: {self.version}")
        self.label_server_ip.setText(f"伺服器IP: {self.host}")

    def setup_hourly_refresh(self):
        # 先算出距離下個整點還有多少毫秒
        now = datetime.datetime.now()
        next_hour = (now + datetime.timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        delay_ms = int((next_hour - now).total_seconds() * 1000)

        # 用單次 QTimer 等到整點
        self.initial_timer = QtCore.QTimer(self)
        self.initial_timer.setSingleShot(True)
        self.initial_timer.timeout.connect(self._start_hourly_timer)
        self.initial_timer.start(delay_ms)

        # 先更新一次
        self.refresh_status_bar()

    def _start_hourly_timer(self):
        # 每小時定時更新
        self.hourly_timer = QtCore.QTimer(self)
        self.hourly_timer.timeout.connect(self.refresh_status_bar)
        self.hourly_timer.start(3600000)  # 1 小時
        self.refresh_status_bar()  # 整點再更新一次

    def set_record_index(self, index):
        self.label_record_index.setText(index)

    # 登出
    def logout(self):
        login_dialog = module_utils.get_login(
            self, self.database, self.system_settings, "pymedical"
        )
        login_dialog.exec_()
        if not login_dialog.login_ok:
            self._force_close = True
            self.close()
            return

        user_name = login_dialog.user_name
        position = login_dialog.position
        self.system_settings.post("使用者", user_name)
        self._set_user_name()
        self.refresh_status_bar()
        self.set_permission()
        self.set_root_permission()
        self._reload_users_permission()

        self.close_all_tabs()
        if position in ["醫師", "支援醫師"]:
            self._set_login_statistics(user_name)
        else:
            self._init_statistics_dicts()

        login_dialog.deleteLater()

    def _set_login_statistics(self, user_name):
        statistics = module_utils.get_login_statistics(
            self, self.database, self.system_settings, user_name
        )
        statistics.start_statistics()
        self.statistics_dicts = statistics.statistics_dicts

        del statistics

    def close_all_tabs(self):
        for i in range(self.ui.tabWidget_window.count(), 0, -1):
            self.ui.tabWidget_window.removeTab(i)

    def _reload_users_permission(self):
        tab_name = "使用者管理"
        if not self.tab_exists(tab_name):
            return

        current_tab = None
        for i in range(self.ui.tabWidget_window.count()):
            if self.ui.tabWidget_window.tabText(i) == tab_name:
                current_tab = self.ui.tabWidget_window.widget(i)
                break

        if current_tab is None:
            return

        if not self.ui.action_users.isEnabled():
            self.close_tab_by_name(tab_name)
        else:
            current_tab.reload_permissions()

    def switch_side_bar(self):
        if self.ui.action_show_side_bar.isChecked():
            self.ui.frameSidebar.show()
        else:
            self.ui.frameSidebar.hide()

    def activate_ic_card_reader(self):
        if self.system_settings.field("使用讀卡機") == "N":
            return

        try:
            cshis = class_utils.get_cshis(self, self.database, self.system_settings)
            cshis.activate_reader_app()
            # ic_card.reset_reader(show_message=False)
        except Exception as e:
            system_utils.loggin_error("system_errors.log", f"讀卡機啟動失敗: {e}")
            system_utils.show_message_box(
                QMessageBox.Critical,
                "讀卡機啟動錯誤",
                """
                    <font size="5" color="red"><b>
                        讀卡機作業失敗, 無法開啟讀卡機驅動程式!
                    </b></font>
                """,
                "請檢查讀卡機連接埠是否連接正確或驅動程式是否正確安裝",
            )

    def deactivate_ic_card_reader(self):
        if self.system_settings.field("使用讀卡機") == "N":
            return

        try:
            cshis = class_utils.get_cshis(self, self.database, self.system_settings)
            cshis.deactivate_reader_app()
            # ic_card.reset_reader(show_message=False)
        except Exception as e:
            system_utils.loggin_error("system_errors.log", f"讀卡機關閉失敗: {e}")

    def _update_files(self):
        if system_utils.is_maintain_expired(self.clinic_name):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "維護合約過期",
                '<font color="red"><h2>貴診所維護合約已過期，恕無法提供更新下載服務</h2></font>',
                "如欲開通下載更新服務，請洽本公司業務人員",
            )
            return

        dialog = module_utils.get_system_update(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 資料庫修復
    def _database_repair(self):
        dialog = dialog_utils.get_dialog_database_repair(
            self, self.database, self.system_settings
        )
        dialog.exec_()
        dialog.deleteLater()

    # 重新啟動系統
    def restart_pymedical(self):
        if sys.platform == "win32":
            os.execv(
                sys.executable,
                [sys.executable, os.path.join(sys.path[0], __file__)] + sys.argv[1:],
            )
        else:
            os.execv(__file__, sys.argv)

    @staticmethod
    def _open_nhi_vpn():
        web_utils.open_nhi_vpn()

    @staticmethod
    def _open_mohw():
        web_utils.open_mohw()

    @staticmethod
    def _open_hca():
        web_utils.open_hca()

    def _open_hyper_link(self):
        sender_name = self.sender().objectName()

        address_list = {
            "toolButton_nhi": "https://www.nhi.gov.tw/",
            "toolButton_nhi_vpn": f"https://medvpn.nhi.gov.tw/iwse0000/IWSE0020S01.aspx?_t={int(time.time())}",
            "toolButton_nhi_vpn_new": f"https://medvpn.nhi.gov.tw/iwse5000/IWSE5020S01.aspx?_t={int(time.time())}",
            "toolButton_hpa": "https://www.hpa.gov.tw/",
            "toolButton_mohw": "https://euservice.mohw.gov.tw",
            "toolButton_hca": "https://hca.nat.gov.tw",
            "toolButton_nucmda": "http://www.twtm.tw/",
            "toolButton_tpcma": "http://www.tpcma.org.tw/",
            "toolButton_sbcma": "http://www.tcm.org.tw/",
            "toolButton_klcma": "https://www.facebook.com/KCHD0855",
            "toolButton_tycma": "http://www.tyccm.org.tw/indexmain.php",
            "toolButton_hctcma": "http://www.hccm.org.tw/index18.php",
            "toolButton_hccma": "https://www.facebook.com/035newbamboo/",
            "toolButton_mlcma": "https://www.facebook.com/MiaoliChineseMedicineAssociation/",
            "toolButton_med_vpn": "https://medcloud2.nhi.gov.tw/imu/IMUE1000/",
        }
        web_utils.open_address(address_list[sender_name])

    # 匯出指定資料至json
    def _export_table_to_json(self):
        config = configparser.ConfigParser()
        config.read(self.database.CONFIG_FILE)
        database_name = config["db"]["database"]

        sql = f'''
            SELECT table_name FROM information_schema.tables
            WHERE
                table_schema = "{database_name}"
            ORDER BY table_name
        '''
        rows = self.database.select_record(sql)

        items = []
        for row in rows:
            items.append(row["table_name"])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        table_name, ok = input_dialog.getItem(
            self, "匯出資料表", "請選擇資料表", items, 0, False
        )

        if not ok:
            return

        options = QFileDialog.Options()
        json_file_name, _ = QFileDialog.getSaveFileName(
            self,
            "匯出資料表JSON檔案",
            f"{table_name}.json",
            "json檔案 (*.json)",
            options=options,
        )
        if not json_file_name:
            return

        sql = f"SELECT * FROM {table_name}"
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding="utf8")
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            "JSON資料匯出完成",
            f"<h3>{json_file_name}匯出完成.</h3>",
            "JSON 檔案格式.",
        )

    def start_flash(self):
        try:
            hwnd = self.winId().__int__()  # 取得視窗 HWND
            flash_window(hwnd)
        except Exception:
            pass

    def _create_shortcut(self):
        self._create_cshis6_shortcut()

    def _create_cshis6_shortcut(self):
        # 1. HIS 當前目錄與 .bat 路徑
        current_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        bat_path = os.path.join(current_dir, "start_cshis6.bat")

        # 2. 外部圖示路徑
        icon_path = r"C:\Program Files (x86)\nhi\cshis6\favicon.ico"

        # 3. 建立 .bat 檔案
        content = "@echo off\nstart cshis6://console\nexit\n"
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 4. 系統目錄
        appdata = os.environ.get("APPDATA")
        userprofile = os.environ.get("USERPROFILE")
        if not appdata or not userprofile:
            raise RuntimeError("找不到必要的環境變數")

        startup_dir = os.path.join(
            appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        desktop_dir = os.path.join(userprofile, "Desktop")

        shortcut_paths = [
            os.path.join(startup_dir, "start_cshis6.lnk"),
            os.path.join(desktop_dir, "啟動讀卡機控制軟體6.0.lnk"),
        ]

        pythoncom.CoInitialize()
        shell = Dispatch("WScript.Shell")

        for shortcut_path in shortcut_paths:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)

            shortcut = shell.CreateShortcut(shortcut_path)
            shortcut.TargetPath = bat_path
            shortcut.WorkingDirectory = current_dir
            shortcut.WindowStyle = 7  # 最小化

            if os.path.exists(icon_path):
                shortcut.IconLocation = icon_path

            shortcut.Save()

        # 5. 顯示成功訊息
        system_utils.show_message_box(
            QMessageBox.Information,
            "設定成功",
            '<font size="5" color="blue"><b>桌面與啟動資料夾捷徑建立完成！</b></font>',
            "捷徑已包含專屬圖示，重開機或點選桌面捷徑即可啟動讀卡機控制軟體6.0。",
        )


def set_high_dpi_attributes():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_Use96Dpi, True)
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


def set_windows_scale_factor():
    hDC = win32gui.GetDC(0)
    real_width = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
    screen_scale_rate = "1.25" if real_width == 2560 else "1.0"
    os.environ["QT_SCALE_FACTOR"] = screen_scale_rate


def show_splash_screen():
    splash_pix = QtGui.QPixmap("images/login_green.jpg")
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    splash.setEnabled(False)
    splash.showMessage(
        "<h1><font color='darkgreen'>系統程式載入中, 請稍後...</font></h1>",
        QtCore.Qt.AlignCenter,
        QtCore.Qt.black,
    )
    splash.show()
    QtWidgets.qApp.processEvents()

    return splash


def initialize_app(splash):
    py_medical = PyMedical(None, splash, sys.argv)
    check_db = module_utils.get_check_database(
        py_medical, py_medical.database, py_medical.system_settings, "pymedical"
    )
    check_db.check_database()
    del check_db

    py_medical.set_plugin()
    splash.finish(py_medical)

    return py_medical


def handle_login(py_medical):
    login_dialog = module_utils.get_login(
        py_medical, py_medical.database, py_medical.system_settings
    )
    login_dialog.exec_()
    if not login_dialog.login_ok:
        login_dialog.deleteLater()
        py_medical.deleteLater()

        return None, None

    user_name = login_dialog.user_name
    position = login_dialog.position
    login_dialog.deleteLater()

    return user_name, position


def setup_user_environment(py_medical, user_name, position):
    current_ip_address = system_utils.get_ip()

    if user_name != "超級使用者":
        sys.excepthook = collect_traceback

    if position in ["醫師", "支援醫師"]:
        statistics = module_utils.get_login_statistics(
            py_medical, py_medical.database, py_medical.system_settings, user_name
        )
        statistics.start_statistics()
        py_medical.statistics_dicts = statistics.statistics_dicts
        del statistics

    py_medical.system_settings.post("使用者", user_name)
    py_medical.system_settings.post("使用者ip", current_ip_address)
    py_medical.system_settings.post(
        "登入日期", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    py_medical.refresh_status_bar()
    py_medical.set_permission()
    py_medical.set_root_permission()
    QtWidgets.qApp.processEvents()
    py_medical.set_treatment_list()


def configure_main_window(py_medical, config):
    try:
        full_screen = config["settings"].getboolean("full_screen")
    except Exception:
        full_screen = True

    if full_screen is None:
        full_screen = True

    if full_screen:
        # py_medical.show()  # 先show()再showMaximized()才不會被wayland忽略
        # QtCore.QTimer.singleShot(1000, py_medical.showMaximized)
        py_medical.showMaximized()
    else:
        py_medical.resize(1920, 1080)
        system_utils.center_window(py_medical)
        py_medical.show()

    if (
        py_medical.system_settings.field("自動開啟雲端安全模組主控台") == "Y"
        or py_medical.system_settings.field("讀卡機控制軟體版本") == "cshis6"
    ):
        py_medical.activate_ic_card_reader()


# 檢查港香蘭無效健保碼 2025-09-24
def check_invalid_ins_drug(py_medical):
    dialog_invalid_ins_drug = dialog_utils.get_dialog_invalid_ins_drug(
        py_medical, py_medical.database, py_medical.system_settings
    )
    dialog_invalid_ins_drug.start_check()
    del dialog_invalid_ins_drug


# 設定theme
def set_light_style(app):
    app.setStyle(QStyleFactory.create("Fusion"))

    # 設定調色盤為淺色
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))  # 背景白色
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))  # 文字黑色
    palette.setColor(QPalette.Base, QColor(255, 255, 255))  # 輸入框背景白色
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))  # 文字黑色
    palette.setColor(QPalette.Button, QColor(220, 220, 220))  # 按鈕灰色
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))  # 按鈕文字黑色
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(76, 163, 224))  # 選取顏色藍色
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    app.setPalette(palette)


def set_dark_style(app):
    app.setStyle(QStyleFactory.create("Fusion"))

    # 設定調色盤為暗色
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))  # 背景深灰
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))  # 文字白色
    palette.setColor(QPalette.Base, QColor(42, 42, 42))  # 輸入框背景深灰
    palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))  # 交替背景色
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))  # 文字白色
    palette.setColor(QPalette.Button, QColor(64, 64, 64))  # 按鈕深灰
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))  # 按鈕文字白色
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(76, 163, 224))  # 選取顏色藍色
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    app.setPalette(palette)


def check_smart_app_control():
    """檢查 Windows 11 Smart App Control 是否啟用 (0=關閉, 1=強制, 2=評估)"""
    if sys.platform != "win32":
        return

    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\CI\Policy"
        )
        state, _ = winreg.QueryValueEx(key, "VerifiedAndReputablePolicyState")
        winreg.CloseKey(key)
    except Exception:
        return  # 讀不到就當作沒有此功能 (Win10 或舊版 Win11)

    if state != 0:
        system_utils.show_message_box(
            QMessageBox.Warning,
            "系統設定提醒",
            '<font color="red"><h3>偵測到「智慧型應用程式控制」已啟用!</h3></font>',
            "此功能會封鎖醫療系統部分模組, 造成無法預期的錯誤.<br>"
            "請至 Windows 安全性 → 應用程式與瀏覽器控制 → 智慧型應用程式控制, 將其關閉後重新啟動電腦.",
        )


# 主程式
def main(config):
    set_high_dpi_attributes()
    if sys.platform == "win32":
        set_windows_scale_factor()

    app = QtWidgets.QApplication(sys.argv)
    QtGui.QFontDatabase.addApplicationFont("code128.ttf")
    translator = QtCore.QTranslator()
    translator.load("./qtbase_zh_TW.qm")
    app.installTranslator(translator)

    splash = show_splash_screen()
    check_smart_app_control()

    py_medical = initialize_app(splash)
    user_name, position = handle_login(py_medical)
    if not user_name:
        return

    setup_user_environment(py_medical, user_name, position)
    check_invalid_ins_drug(py_medical)
    configure_main_window(py_medical, config)
    py_medical.start_flash()
    sys.exit(app.exec_())


# 程式進入點
if __name__ == "__main__":
    try:
        config_file = sys.argv[1]
    except IndexError:
        config_file = "pymedical.conf"

    config = configparser.ConfigParser()
    config.read(config_file)
    try:
        run_as_admin = config["settings"].getboolean("run_as_admin")
    except KeyError:
        run_as_admin = False

    if sys.platform == "win32" and run_as_admin:
        if not pyuac.isUserAdmin():  # type: ignore
            pyuac.runAsAdmin()
        else:
            main(config)
    else:
        main(config)
