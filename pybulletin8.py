import configparser
import datetime
import json
import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDesktopWidget

from libs import (
    class_utils,
    date_utils,
    notification_utils,
    number_utils,
    registration_utils,
    string_utils,
    ui_utils,
    voice_utils,
)


class ClockOverlay(QtWidgets.QWidget):
    """
    透明疊層上的時鐘：顯示在 parent 的 (x, y)，格式預設 %H:%M（24H）。
    不加入任何 layout，使用 move() 定位，並用 raise_() 置頂。
    """

    def __init__(self, parent, x=0, y=0, fmt="%H:%M"):
        super().__init__(parent)
        self._x, self._y = int(x), int(y)
        self._fmt = fmt

        # 這個 QWidget 本身就是 overlay 視窗
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        # 內部真正顯示時間的 QLabel
        self.label = QtWidgets.QLabel(self)
        self.label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;
                font-size: 72px;
                font-weight: bold;        
            }
        """)

        # 初始顯示與定位
        self.label.adjustSize()
        self.setFixedSize(self.label.size())
        self.move(self._x, self._y)
        self.show()
        self.raise_()  # 🔼 疊到最上層

        # 先顯示一次，記住目前分鐘
        self._set_now()
        self._last_minute = datetime.datetime.now().minute

        # ✅ 穩定計時器：每 1000ms 檢查一次是否「分鐘變了」
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.CoarseTimer)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_second)
        self._timer.start()

    def _set_now(self):
        now = datetime.datetime.now()
        self.label.setText(now.strftime(self._fmt))
        self.label.adjustSize()
        self.setFixedSize(self.label.size())

    def _tick_second(self):
        now = datetime.datetime.now()
        if now.minute != self._last_minute:  # 只在跨分鐘時更新
            self._last_minute = now.minute
            self._set_now()

    # 提供 API 調整位置 / 置頂 / 格式
    def set_position(self, x, y):
        self._x, self._y = int(x), int(y)
        self.move(self._x, self._y)

    def bring_to_front(self):
        self.raise_()

    def set_format(self, fmt="%H:%M"):
        self._fmt = fmt
        self._set_now()


class Marquee(QtWidgets.QWidget):
    """
    文字在 [x1, x2] 的可視區內「從右側長出 → 向左移動 → 到左側逐漸縮回 → 消失 → 從右側再長出」。
    一次讀取 DB 到 self._messages，之後無限循環，不重讀資料庫。
    """

    def __init__(
        self, parent, database, system_settings, *, x1=0, x2=800, y=0, speed=150
    ):
        super().__init__(parent)
        self.db = database
        self.system_settings = system_settings
        self.x1 = int(x1)
        self.x2 = int(x2)
        self.y = int(y)
        self.speed = float(speed)  # 像素/秒

        # ── 建立「可視區」本體（自己就是 viewport）：放在 (x1, y)，寬度 = x2-x1，高度用字高
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")
        self._font = self.font()
        fm = QtWidgets.QApplication.fontMetrics()  # 或 QtGui.QFontMetrics(self._font)
        self._line_h = fm.height() + 70
        self.setGeometry(self.x1, self.y, max(10, self.x2 - self.x1), self._line_h)
        self.show()

        # ── 內部真正顯示文字的 QLabel（在 viewport 內左右滑動）
        self._label = QtWidgets.QLabel(self)
        self._label.setStyleSheet("""
            QLabel {
              background: transparent;
              color: white;
              font-size: 72px;
              font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;
              font-weight: bold;
            }
        """)

        self._label.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._label.move(self.width(), 0)  # 先擺在最右邊之外（只露出一點會逐步長出）

        # 狀態
        self._messages = []
        self._idx = 0
        self._x = float(self.width())  # label 的左上角 x（相對於 viewport）
        self._text_w = 0
        self._running = False
        self._last_t = None

        # 計時器（~60FPS）
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        # 一次性載入 DB
        self._load_messages_once()

    # ---------- 一次性讀 DB ----------
    def _load_messages_once(self):
        sql = """
            SELECT * FROM system_settings
            WHERE Field LIKE "跑馬燈訊息-%"
            ORDER BY Field
        """
        rows = self.db.select_record(sql)
        msgs = []
        if rows:
            for row in rows:
                text = str(row.get("Value", "")).strip()
                if text:
                    msgs.append(text)
        if not msgs:
            name = self.system_settings.field("院所名稱") or "本院"
            msgs = [f"{name} 關心您的健康"]

        self._messages = msgs
        self._idx = 0
        self._apply_text(self._messages[self._idx])

    # ---------- 公開 API ----------
    def play(self):
        if not self._messages:
            self._load_messages_once()
        self._running = True
        self._last_t = time.perf_counter()
        # 從可視區右邊（完全在外）開始，會「逐步長出」
        self._x = float(self.width())
        self._label.move(int(self._x), 0)
        self._label.show()
        self.raise_()
        self._timer.start()

    def stop(self):
        self._running = False
        self._timer.stop()

    def set_bounds(self, x1, x2):
        """視窗大小改變時呼叫：更新 [x1,x2] 可視區。"""
        self.x1, self.x2 = int(x1), int(x2)
        self.setGeometry(self.x1, self.y, max(10, self.x2 - self.x1), self._line_h)

    def set_speed(self, px_per_sec):
        self.speed = float(px_per_sec)

    # ---------- 內部 ----------
    def _apply_text(self, text):
        self._label.setText(text)
        self._label.adjustSize()
        self._text_w = self._label.width()
        self._label.move(int(self._x), 0)

    def _tick(self):
        if not self._running:
            return
        t = time.perf_counter()
        dt = t - self._last_t if self._last_t is not None else 0.016
        if dt > 0.2:  # 防止休眠/卡頓後一次跳太遠
            dt = 0.016
        self._last_t = t

        # 向左移動 label：因為 label 在 viewport 裡，超出的部分會被裁掉
        self._x -= self.speed * dt
        self._label.move(int(self._x), 0)

        # 當「整段文字的尾端」也離開了左邊界（= 完全不可見）
        # 條件：label.x + text_width <= 0
        if self._x + self._text_w <= 0:
            # 換下一條 & 從右側外面再「長出」
            self._idx = (self._idx + 1) % len(self._messages)
            self._apply_text(self._messages[self._idx])
            self._x = float(self.width())
            self._label.move(int(self._x), 0)
            self.raise_()


class WaitingRoom(QtCore.QObject):
    """
    候診名單顯示器：一次讀取資料庫，顯示診號與姓名，每次顯示 N 筆，定時換頁循環播放。
    呼叫 refresh() 可重新抓取資料。
    """

    def __init__(
        self,
        parent,
        database,
        system_settings,
        room,
        doctor,
        x=100,
        y_list=None,
        items_per_page=5,
        interval_sec=5,
    ):
        super().__init__(parent)
        self.parent = parent
        self.database = database
        self.system_settings = system_settings
        self.room = room
        self.doctor = doctor
        self.regist_no = "0"

        # 顯示位置設定
        self.x = int(x)
        self.y_list = y_list or [400, 500, 600, 700, 800]
        self.items_per_page = int(items_per_page)
        self.interval_ms = int(interval_sec * 1000)

        # 狀態
        self._labels: list[QtWidgets.QLabel] = []
        self._items: list[str] = []
        self._page_index = 0
        self._running = False

        # 計時器
        self._timer = QtCore.QTimer(self.parent)
        self._timer.timeout.connect(self._next_page)
        self._timer.setInterval(self.interval_ms)

        # 建立 QLabel 元件
        self._build_doctor_labels()
        self._build_regist_no_labels()
        self._build_waiting_list_labels()

    # -----------------------------
    # 建立 UI 元件k
    # -----------------------------
    def _get_doctor_text(self):
        if self.doctor is None:
            doctor_text = ""
        else:
            doctor_text = f"{self.room}診 {self.doctor}醫師"

        return doctor_text

    def _build_doctor_labels(self):
        self.label_doctor = QtWidgets.QLabel(self.parent)
        self.label_doctor.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;            
                font-size: 64px;
                font-weight: bold;
            }
        """)

        y = 100
        self.label_doctor.move(self.x - 30, y)
        self.label_doctor.adjustSize()
        self.label_doctor.show()
        self.label_doctor.raise_()

    def _build_regist_no_labels(self):
        self.label_regist_no_header = QtWidgets.QLabel(self.parent)
        self.label_regist_no_header.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;            
                font-size: 48px;
                font-weight: bold;
            }
        """)

        x1 = self.x - 10
        y = 260

        self.label_regist_no_header.move(x1, y)
        self.label_regist_no_header.adjustSize()
        self.label_regist_no_header.show()
        self.label_regist_no_header.raise_()

        self.label_regist_no = QtWidgets.QLabel(self.parent)
        self.label_regist_no.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;            
                font-size: 120px;
                font-weight: bold;
            }
        """)

        x1 = self.x + 150
        y = 240

        self.label_regist_no.move(x1, y)
        self.label_regist_no.adjustSize()
        self.label_regist_no.show()
        self.label_regist_no.raise_()

    def _build_waiting_list_labels(self):
        for lbl in self._labels:
            lbl.deleteLater()
        self._labels.clear()

        for i in range(self.items_per_page):
            lbl = QtWidgets.QLabel(self.parent)

            lbl.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: white;
                    font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;        
                    font-size: 64px;
                    font-weight: bold;
                }
            """)
            lbl.move(
                self.x,
                self.y_list[i]
                if i < len(self.y_list)
                else self.y_list[-1] + (i - len(self.y_list) + 1) * 80,
            )
            lbl.show()
            lbl.raise_()
            self._labels.append(lbl)

    # -----------------------------
    # 資料讀取
    # -----------------------------
    def _load_from_db(self):
        """從資料庫讀取候診名單"""
        current_period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
            SELECT RegistNo, Name FROM wait
            WHERE
                Doctor = "{self.doctor}" AND
                Period = "{current_period}" AND
                DoctorDone = "False"
            ORDER BY RegistNo
        '''
        rows = self.database.select_record(sql)

        self._items = [f"{r['RegistNo']} {r['Name']}" for r in rows]

    # -----------------------------
    # 公開控制方法
    # -----------------------------
    def start(self):
        """若資料超過一頁才啟動輪播"""
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def stop(self):
        """停止循環"""
        self._running = False
        self._timer.stop()

    def refresh(self):
        self._refresh_doctor()
        self._refresh_waiting_list()

    def show_regist_no(self, regist_no):
        self.regist_no = string_utils.xstr(regist_no)
        text = f"""
            <table width="500">
              <tr>
                <td align="center" width="100"><b>{self.regist_no}</b></td>
              </tr>
            </table>
        """

        self.label_regist_no.setText(text)
        self.label_regist_no.adjustSize()

    def _refresh_doctor(self):
        doctor_text = self._get_doctor_text()
        self.label_doctor.setText(doctor_text)
        self.label_doctor.adjustSize()
        self._refresh_header()

    def _refresh_header(self):
        if self.doctor is None:
            regist_no_header = ""
        else:
            regist_no_header = "目前\n診號"

        self.label_regist_no_header.setText(regist_no_header)
        self.label_regist_no_header.adjustSize()

    def _refresh_waiting_list(self):
        """重新讀取資料並回到第一頁"""
        self._load_from_db()
        self._page_index = 0
        self._apply_page(0)
        # 自動判斷是否需要輪播
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def bring_to_front(self):
        """將所有 QLabel 疊到最上層"""
        for lbl in self._labels:
            lbl.raise_()

    # -----------------------------
    # 顯示邏輯
    # -----------------------------
    def _mask_name(self, name):
        mask_name = name[0] + "〇" + name[2:6]

        return mask_name

    def _apply_page(self, page_idx: int):
        n = len(self._items)
        total_pages = max(1, (n + self.items_per_page - 1) // self.items_per_page)
        page_idx %= total_pages

        start = page_idx * self.items_per_page
        end = min(start + self.items_per_page, n)
        items = self._items[start:end]

        for i, lbl in enumerate(self._labels):
            if i < len(items):
                # 分割診號與姓名
                seq, name = (
                    items[i].split(maxsplit=1) if " " in items[i] else (items[i], "")
                )

                # 用 HTML table 控制對齊與中間距離
                text = f"""
                    <table width="600">
                      <tr>
                        <td align="right" width="100"><b>{seq}</b></td>
                        <td width="20"></td>  <!-- 👈 中間空白區 -->
                        <td align="left"><b>{self._mask_name(name[:4])}</b></td>
                      </tr>
                    </table>
                """

                lbl.setText(text)
                lbl.setTextFormat(QtCore.Qt.RichText)
                lbl.adjustSize()
                lbl.show()
            else:
                lbl.setText("")
                lbl.hide()

    def _next_page(self):
        if not self._items:
            return
        total_pages = max(
            1, (len(self._items) + self.items_per_page - 1) // self.items_per_page
        )
        self._page_index = (self._page_index + 1) % total_pages
        self._apply_page(self._page_index)


class Pharmacy(QtCore.QObject):
    """
    候診名單顯示器：一次讀取資料庫，顯示診號與姓名，每次顯示 N 筆，定時換頁循環播放。
    呼叫 refresh() 可重新抓取資料。
    """

    def __init__(
        self,
        parent,
        database,
        system_settings,
        x=100,
        y_list=None,
        items_per_page=6,
        interval_sec=5,
    ):
        super().__init__(parent)
        self.parent = parent
        self.database = database
        self.system_settings = system_settings

        # 顯示位置設定
        self.x = int(x)
        self.y_list = y_list or [400, 500, 600, 700, 800]
        self.items_per_page = int(items_per_page)
        self.interval_ms = int(interval_sec * 1000)

        # 狀態
        self._labels: list[QtWidgets.QLabel] = []
        self._items: list[str] = []
        self._page_index = 0
        self._running = False

        # 計時器
        self._timer = QtCore.QTimer(self.parent)
        self._timer.timeout.connect(self._next_page)
        self._timer.setInterval(self.interval_ms)

        # 建立 QLabel 元件
        self._build_pharmacy_labels()
        self._build_pharmacy_list_labels()

    # -----------------------------
    # 建立 UI 元件k
    # -----------------------------
    def _build_pharmacy_labels(self):
        self.label_pharmacy = QtWidgets.QLabel(self.parent)
        self.label_pharmacy.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;            
                font-size: 64px;
                font-weight: bold;
            }
        """)

        y = 100
        self.label_pharmacy.move(self.x - 30, y)
        self.label_pharmacy.setText("可領藥")
        self.label_pharmacy.adjustSize()
        self.label_pharmacy.show()
        self.label_pharmacy.raise_()

    def _build_pharmacy_list_labels(self):
        for lbl in self._labels:
            lbl.deleteLater()
        self._labels.clear()

        for i in range(self.items_per_page):
            lbl = QtWidgets.QLabel(self.parent)

            lbl.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: white;
                    font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif;        
                    font-size: 96px;
                    font-weight: bold;
                }
            """)
            lbl.move(
                self.x,
                self.y_list[i]
                if i < len(self.y_list)
                else self.y_list[-1] + (i - len(self.y_list) + 1) * 80,
            )
            lbl.show()
            lbl.raise_()
            self._labels.append(lbl)

    # -----------------------------
    # 資料讀取
    # -----------------------------
    def _load_from_db(self):
        """從資料庫讀取候診名單"""
        sql = """
            SELECT wait.Name, cases.DrugNo FROM wait
                LEFT JOIN cases ON cases.CaseKey = wait.CaseKey
            WHERE
                cases.DrugDone = "True" AND
                cases.DrugPickupDone = "False"
            ORDER BY DrugNo
        """
        rows = self.database.select_record(sql)

        self._items = [f"{r['DrugNo']} {r['Name']}" for r in rows]

    # -----------------------------
    # 公開控制方法
    # -----------------------------
    def start(self):
        """若資料超過一頁才啟動輪播"""
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def stop(self):
        """停止循環"""
        self._running = False
        self._timer.stop()

    def refresh(self):
        self._refresh_pharmacy_list()

    def _refresh_pharmacy_list(self):
        """重新讀取資料並回到第一頁"""
        self._load_from_db()
        self._page_index = 0
        self._apply_page(0)
        # 自動判斷是否需要輪播
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def bring_to_front(self):
        """將所有 QLabel 疊到最上層"""
        for lbl in self._labels:
            lbl.raise_()

    # -----------------------------
    # 顯示邏輯
    # -----------------------------
    def _apply_page(self, page_idx: int):
        n = len(self._items)
        total_pages = max(1, (n + self.items_per_page - 1) // self.items_per_page)
        page_idx %= total_pages

        start = page_idx * self.items_per_page
        end = min(start + self.items_per_page, n)
        items = self._items[start:end]

        for i, lbl in enumerate(self._labels):
            if i < len(items):
                # 分割診號與姓名
                seq, name = (
                    items[i].split(maxsplit=1) if " " in items[i] else (items[i], "")
                )

                # 用 HTML table 控制對齊與中間距離
                text = f"""
                    <table width="600">
                      <tr>
                        <td align="center" width="200"><b>{seq}</b></td>
                      </tr>
                    </table>
                """

                lbl.setText(text)
                lbl.setTextFormat(QtCore.Qt.RichText)
                lbl.adjustSize()
                lbl.show()
            else:
                lbl.setText("")
                lbl.hide()

    def _next_page(self):
        if not self._items:
            return
        total_pages = max(
            1, (len(self._items) + self.items_per_page - 1) // self.items_per_page
        )
        self._page_index = (self._page_index + 1) % total_pages
        self._apply_page(self._page_index)


class PyBulletin8(QtWidgets.QMainWindow):
    """候診資訊系統 三診間及藥局版."""

    def __init__(self, parent=None, *args):
        """初始化."""
        super().__init__(parent)
        self.args = args

        self._set_db()
        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )
        self.ui = None

        self._set_ui()
        self._set_notification_server()
        self._set_signal()

        monitor_number = self.get_monitor_number()
        monitor = QDesktopWidget().screenGeometry(monitor_number)
        self.move(monitor.left(), monitor.top())
        self.showFullScreen()

    def show_bulletin(self):
        """顯示候診看板."""
        self.marquee = Marquee(
            parent=self,
            database=self.database,
            system_settings=self.system_settings,
            y=self.marquee_y,
            speed=100,
        )
        self.marquee.play()

        self.clock = ClockOverlay(self)

        self.refresh_waiting_room_info()

        if sys.platform == "win32":
            y_list = [415, 515, 615, 715, 805]
        else:
            y_list = [400, 500, 600, 700, 792]

        self.waiting_room = [None, None, None]
        for i in range(len(self.waiting_room)):
            self.waiting_room[i] = WaitingRoom(
                parent=self.ui,
                database=self.database,
                system_settings=self.system_settings,
                room=self.waiting_room_info[i][0],
                doctor=self.waiting_room_info[i][1],
                x=self.waiting_room_info[i][2],
                y_list=y_list,
                items_per_page=5,
                interval_sec=5,
            )
            self.waiting_room[i].start()

        self.pharmacy = Pharmacy(
            parent=self.ui,
            database=self.database,
            system_settings=self.system_settings,
            x=1630,
            y_list=[240, 350, 457, 565, 674, 777],
            items_per_page=6,
            interval_sec=5,
        )
        self.pharmacy.start()

        self._show_waiting_list()

    def refresh_waiting_room_info(self):
        self.waiting_room_info = [
            [None, None, 90],
            [None, None, 600],
            [None, None, 1100],
        ]

        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        current_period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
           SELECT Room, {weekday} AS Doctor FROM doctor_schedule
           WHERE
              Period = "{current_period}" AND
              {weekday} IS NOT NULL
           ORDER BY Room LIMIT 3
        '''
        rows = self.database.select_record(sql)
        for row_no, row in enumerate(rows):
            self.waiting_room_info[row_no][0] = row["Room"]
            self.waiting_room_info[row_no][1] = row["Doctor"]

    def _show_waiting_list(self):
        self.refresh_waiting_room_info()

        for i in range(len(self.waiting_room)):
            self.waiting_room[i].room = self.waiting_room_info[i][0]
            self.waiting_room[i].doctor = self.waiting_room_info[i][1]
            self.waiting_room[i].refresh()

        self.pharmacy.refresh()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.clock_x = self.width() - 300
        self.marquee_x = self.width() - 400
        self.marquee_y = 936

        if hasattr(self, "clock"):
            self.clock.set_position(self.clock_x, self.marquee_y)

        if getattr(self, "marquee_auto_bounds", True) and hasattr(self, "marquee"):
            self.marquee.set_bounds(52, self.marquee_x)

    def _set_notification_server(self):
        channels = [
            notification_utils.CHANNEL_WAITING_LIST,  # 原 8880
            notification_utils.CHANNEL_BULLETIN,  # 原 9990 的 refresh_wait
            notification_utils.CHANNEL_CALL_NUMBER,  # UDP 下線後才打開，否則會念兩次
        ]
        self.notification_server = notification_utils.NotificationServer(
            self,
            database=self.database,
            station="pybulletin",
            channels=channels,
        )
        self.notification_server.update_signal.connect(self._on_notification)

    def _on_notification(self, channel, message):
        if channel == notification_utils.CHANNEL_WAITING_LIST:
            self._show_waiting_list()  # 原本 8880 就是忽略內容直接刷新
        elif channel == notification_utils.CHANNEL_BULLETIN:
            self._broadcast_speech(message)  # 內容是 refresh_wait，它自己會分辨
        elif channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_speech(message)

    def get_monitor_number(self):
        """取得候診系統顯示器編號."""
        return number_utils.get_integer(
            self.system_settings.field("候診系統顯示器編號")
        )

    def _set_db(self):
        self.host = None
        try:
            config_file = self.args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict["host"]
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict["user"],
                database=config_dict["database"],
                password=config_dict["password"],
                charset=config_dict["charset"],
                buffered=config_dict["buffered"],
            )
            self.server_ip = config_dict["host"]
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

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

    def __del__(self):
        """解構."""

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN, self)
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        self.setCursor(Qt.BlankCursor)

        # 設定背景圖片
        background = QtGui.QPixmap("./images/bulletin_background1.png")
        palette = QtGui.QPalette()
        palette.setBrush(QtGui.QPalette.Window, QtGui.QBrush(background))
        self.setPalette(palette)

    # 設定信號
    def _set_signal(self):
        pass

    def _close(self):
        self.close()

    # 廣播叫號
    def _broadcast_speech(self, json_data):
        try:
            voice_dict = json.loads(json_data)
        except Exception:
            return

        room = number_utils.get_integer(voice_dict["room"])
        regist_no = voice_dict["regist_no"]

        for i in range(len(self.waiting_room)):
            if self.waiting_room[i].room == room:
                self.waiting_room[i].room = self.waiting_room_info[i][0]
                self.waiting_room[i].doctor = self.waiting_room_info[i][1]
                self.waiting_room[i].show_regist_no(regist_no)
                break

        sentence = voice_dict["sentence"]
        QtWidgets.qApp.processEvents()
        voice_utils.speak(sentence, threading=True)


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin8(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()
