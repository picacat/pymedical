"""候診資訊系統 四診間版（固定全螢幕 1920x1080）.

與 pybulletin8 的差異：
  1. 取消跑馬燈（Marquee）
  2. 診間由 3 個擴充為 4 個
  3. 領藥號由右側直式改為下方橫式（一次 6 格，超過自動輪播換頁）
  4. 時鐘格位置照舊（右下角）
  5. 所有 QLabel 改用「固定 geometry + 對齊」定位，不再用 move() + adjustSize()，
     文字才能穩定落在背景圖的格線內

背景圖：images/bulletin_background9.png（由 make_background9.py 產生，座標須與
下方 Layout 常數完全一致）
"""

import configparser
import datetime
import json
import sys

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

# 版面設計基準解析度（所有寫死的座標都以此為準）
DESIGN_WIDTH = 1920
DESIGN_HEIGHT = 1080

FONT_FAMILIES = [
    "Microsoft JhengHei",
    "Noto Sans TC",
    "PingFang TC",
    "Microsoft YaHei",
]


class Layout:
    """版面座標（1920x1080 基準），必須與 make_background9.py 一致."""

    # 診間格
    ROOM_X_LIST = [40, 508, 976, 1444]
    ROOM_W = 436
    ROOM_TOP = 24
    ROOM_BOTTOM = 800
    ROOM_HEADER_Y = 160  # 醫師名稱列下方分隔線
    ROOM_BRIGHT_Y = 330  # 目前診號區下方亮黃線
    ROOM_ROW_TOPS = [330, 424, 518, 612, 706]  # 5 列候診名單
    ROOM_ROW_H = 94
    ROOM_INSET = 40  # 內容左右留白（對齊背景線段）

    # 下方橫式領藥號長條
    PHARM_X1, PHARM_Y1 = 40, 832
    PHARM_X2, PHARM_Y2 = 1530, 1056
    PHARM_TITLE_X2 = 300
    PHARM_CELLS = 6
    PHARM_CELL_W = (PHARM_X2 - PHARM_TITLE_X2) // PHARM_CELLS  # 205

    # 時鐘格
    CLOCK_X1, CLOCK_Y1 = 1562, 832
    CLOCK_X2, CLOCK_Y2 = 1880, 1056


def make_font(pixel_size):
    """看板專用字型（粗體、指定像素大小）."""
    font = QtGui.QFont()
    try:
        font.setFamilies(FONT_FAMILIES)  # Qt 5.13+
    except AttributeError:  # 舊版 Qt 退回單一字型
        font.setFamily(FONT_FAMILIES[0])
    font.setPixelSize(int(pixel_size))
    font.setBold(True)
    return font


def make_label(
    parent,
    rect,
    font_size,
    align=QtCore.Qt.AlignCenter,
    color="white",
    min_font_size=None,
):
    """建立一個固定位置、固定大小的透明 QLabel.

    位置與大小完全由 rect 決定（不用 adjustSize），文字用對齊方式擺放，
    所以一定會落在背景圖的格線內。
    """
    label = QtWidgets.QLabel(parent)
    label.setStyleSheet(f"QLabel {{ background: transparent; color: {color}; }}")
    label.setTextFormat(QtCore.Qt.PlainText)  # 支援 \n 換行
    label.setAlignment(align)
    label.setGeometry(*rect)
    label.setFont(make_font(font_size))
    label.setProperty("base_font_size", int(font_size))
    label.setProperty(
        "min_font_size",
        int(min_font_size if min_font_size is not None else max(20, font_size * 0.6)),
    )
    label.show()
    label.raise_()
    return label


def set_label_text(label, text):
    """設定文字，並在過長時自動縮小字級，避免溢出格線."""
    text = "" if text is None else str(text)
    label.setText(text)
    if not text:
        return

    base = label.property("base_font_size")
    minimum = label.property("min_font_size")
    available = max(10, label.width() - 12)
    lines = text.split("\n")

    font = label.font()
    size = base
    while size > minimum:
        font.setPixelSize(size)
        metrics = QtGui.QFontMetrics(font)
        widest = max(metrics.horizontalAdvance(line) for line in lines)
        if widest <= available:
            break
        size -= 2

    font.setPixelSize(size)
    label.setFont(font)


class ClockOverlay(QtWidgets.QWidget):
    """時鐘：置中顯示於右下角的時鐘格內，格式預設 %H:%M（24H）."""

    def __init__(self, parent, fmt="%H:%M"):
        super().__init__(parent)
        self._fmt = fmt

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        x = Layout.CLOCK_X1
        y = Layout.CLOCK_Y1
        w = Layout.CLOCK_X2 - Layout.CLOCK_X1
        h = Layout.CLOCK_Y2 - Layout.CLOCK_Y1
        self.setGeometry(x, y, w, h)

        self.label = make_label(self, (0, 0, w, h), 88)

        self.show()
        self.raise_()

        # 先顯示一次，記住目前分鐘
        self._set_now()
        self._last_minute = datetime.datetime.now().minute

        # 每 1000ms 檢查一次是否「分鐘變了」
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.CoarseTimer)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_second)
        self._timer.start()

    def _set_now(self):
        set_label_text(self.label, datetime.datetime.now().strftime(self._fmt))

    def _tick_second(self):
        now = datetime.datetime.now()
        if now.minute != self._last_minute:  # 只在跨分鐘時更新
            self._last_minute = now.minute
            self._set_now()

    def bring_to_front(self):
        self.raise_()

    def set_format(self, fmt="%H:%M"):
        self._fmt = fmt
        self._set_now()


class WaitingRoom(QtCore.QObject):
    """單一診間：顯示醫師、目前診號與候診名單，超過一頁定時輪播換頁."""

    def __init__(
        self,
        parent,
        database,
        system_settings,
        room,
        doctor,
        box_x,
        box_w=None,
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

        self.box_x = int(box_x)
        self.box_w = int(box_w if box_w is not None else Layout.ROOM_W)
        self.items_per_page = int(items_per_page)
        self.interval_ms = int(interval_sec * 1000)

        # 狀態
        self._seq_labels: list[QtWidgets.QLabel] = []
        self._name_labels: list[QtWidgets.QLabel] = []
        self._items: list[str] = []
        self._page_index = 0
        self._running = False

        # 計時器
        self._timer = QtCore.QTimer(self.parent)
        self._timer.timeout.connect(self._next_page)
        self._timer.setInterval(self.interval_ms)

        self._build_labels()

    # -----------------------------
    # 建立 UI 元件
    # -----------------------------
    def _build_labels(self):
        x, w = self.box_x, self.box_w
        inset = Layout.ROOM_INSET

        # 醫師名稱（診間標題列）
        self.label_doctor = make_label(
            self.parent,
            (
                x + 16,
                Layout.ROOM_TOP + 20,
                w - 32,
                Layout.ROOM_HEADER_Y - Layout.ROOM_TOP - 30,
            ),
            46,
            min_font_size=30,
        )

        # 目前診號
        self.label_regist_no_header = make_label(
            self.parent, (x + 20, 180, 110, 130), 38
        )
        self.label_regist_no = make_label(
            self.parent, (x + 140, 176, w - 160, 140), 104
        )

        # 候診名單（診號右對齊、姓名左對齊）
        for i in range(self.items_per_page):
            row_top = self._y_of(i)
            seq = make_label(
                self.parent,
                (x + inset, row_top + 8, 120, Layout.ROOM_ROW_H - 18),
                50,
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            )
            name = make_label(
                self.parent,
                (
                    x + inset + 140,
                    row_top + 8,
                    w - inset * 2 - 140,
                    Layout.ROOM_ROW_H - 18,
                ),
                50,
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            )
            self._seq_labels.append(seq)
            self._name_labels.append(name)

    def _y_of(self, i):
        if i < len(Layout.ROOM_ROW_TOPS):
            return Layout.ROOM_ROW_TOPS[i]
        return (
            Layout.ROOM_ROW_TOPS[-1]
            + (i - len(Layout.ROOM_ROW_TOPS) + 1) * Layout.ROOM_ROW_H
        )

    # -----------------------------
    # 資料讀取
    # -----------------------------
    def _load_from_db(self):
        """從資料庫讀取候診名單."""
        if self.doctor is None:
            self._items = []
            return

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
        """若資料超過一頁才啟動輪播."""
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def stop(self):
        self._running = False
        self._timer.stop()

    def refresh(self):
        self._refresh_doctor()
        self._refresh_waiting_list()

    def show_regist_no(self, regist_no):
        if self.doctor is None:  # 該診間今日無醫師看診，不顯示診號
            return

        self.regist_no = string_utils.xstr(regist_no)
        set_label_text(self.label_regist_no, self.regist_no)

    def _refresh_doctor(self):
        if self.doctor is None:
            set_label_text(self.label_doctor, "")
        else:
            set_label_text(self.label_doctor, f"{self.room}診 {self.doctor}醫師")
        self._refresh_header()

    def _refresh_header(self):
        if self.doctor is None:
            set_label_text(self.label_regist_no_header, "")
            set_label_text(self.label_regist_no, "")
        else:
            set_label_text(self.label_regist_no_header, "目前\n診號")

    def _refresh_waiting_list(self):
        """重新讀取資料並回到第一頁."""
        self._load_from_db()
        self._page_index = 0
        self._apply_page(0)

        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def bring_to_front(self):
        self.label_doctor.raise_()
        self.label_regist_no_header.raise_()
        self.label_regist_no.raise_()
        for label in self._seq_labels + self._name_labels:
            label.raise_()

    # -----------------------------
    # 顯示邏輯
    # -----------------------------
    @staticmethod
    def _mask_name(name):
        if len(name) < 2:
            return name
        return name[0] + "〇" + name[2:6]

    def _apply_page(self, page_idx):
        n = len(self._items)
        total_pages = max(1, (n + self.items_per_page - 1) // self.items_per_page)
        page_idx %= total_pages

        start = page_idx * self.items_per_page
        end = min(start + self.items_per_page, n)
        items = self._items[start:end]

        for i in range(self.items_per_page):
            if i < len(items):
                seq, name = (
                    items[i].split(maxsplit=1) if " " in items[i] else (items[i], "")
                )
                set_label_text(self._seq_labels[i], seq)
                set_label_text(self._name_labels[i], self._mask_name(name[:4]))
            else:
                set_label_text(self._seq_labels[i], "")
                set_label_text(self._name_labels[i], "")

    def _next_page(self):
        if not self._items:
            return
        total_pages = max(
            1, (len(self._items) + self.items_per_page - 1) // self.items_per_page
        )
        self._page_index = (self._page_index + 1) % total_pages
        self._apply_page(self._page_index)


class PharmacyBar(QtCore.QObject):
    """下方橫式可領藥號：一列 6 格，超過 6 筆定時輪播換頁."""

    def __init__(
        self,
        parent,
        database,
        system_settings,
        items_per_page=None,
        interval_sec=5,
    ):
        super().__init__(parent)
        self.parent = parent
        self.database = database
        self.system_settings = system_settings

        self.items_per_page = int(
            items_per_page if items_per_page is not None else Layout.PHARM_CELLS
        )
        self.interval_ms = int(interval_sec * 1000)

        self._labels: list[QtWidgets.QLabel] = []
        self._items: list[str] = []
        self._page_index = 0
        self._running = False

        self._timer = QtCore.QTimer(self.parent)
        self._timer.timeout.connect(self._next_page)
        self._timer.setInterval(self.interval_ms)

        self._build_labels()

    # -----------------------------
    # 建立 UI 元件
    # -----------------------------
    def _build_labels(self):
        h = Layout.PHARM_Y2 - Layout.PHARM_Y1

        # 標題格
        self.label_title = make_label(
            self.parent,
            (
                Layout.PHARM_X1,
                Layout.PHARM_Y1,
                Layout.PHARM_TITLE_X2 - Layout.PHARM_X1,
                h,
            ),
            52,
        )
        set_label_text(self.label_title, "可領藥號")

        # 6 個號碼格
        for i in range(self.items_per_page):
            x = Layout.PHARM_TITLE_X2 + i * Layout.PHARM_CELL_W
            label = make_label(
                self.parent,
                (x, Layout.PHARM_Y1, Layout.PHARM_CELL_W, h),
                88,
                min_font_size=46,
            )
            self._labels.append(label)

    # -----------------------------
    # 資料讀取
    # -----------------------------
    def _load_from_db(self):
        """從資料庫讀取可領藥名單."""
        sql = """
            SELECT wait.Name, cases.DrugNo FROM wait
                LEFT JOIN cases ON cases.CaseKey = wait.CaseKey
            WHERE
                cases.DrugDone = "True" AND
                cases.DrugPickupDone = "False"
            ORDER BY DrugNo
        """
        rows = self.database.select_record(sql)
        self._items = [string_utils.xstr(r["DrugNo"]) for r in rows]

    # -----------------------------
    # 公開控制方法
    # -----------------------------
    def start(self):
        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def stop(self):
        self._running = False
        self._timer.stop()

    def refresh(self):
        self._load_from_db()
        self._page_index = 0
        self._apply_page(0)

        if len(self._items) > self.items_per_page:
            if not self._running:
                self._running = True
                self._timer.start()
        else:
            self._running = False
            self._timer.stop()

    def bring_to_front(self):
        self.label_title.raise_()
        for label in self._labels:
            label.raise_()

    # -----------------------------
    # 顯示邏輯
    # -----------------------------
    def _apply_page(self, page_idx):
        n = len(self._items)
        total_pages = max(1, (n + self.items_per_page - 1) // self.items_per_page)
        page_idx %= total_pages

        start = page_idx * self.items_per_page
        end = min(start + self.items_per_page, n)
        items = self._items[start:end]

        for i, label in enumerate(self._labels):
            set_label_text(label, items[i] if i < len(items) else "")

    def _next_page(self):
        if not self._items:
            return
        total_pages = max(
            1, (len(self._items) + self.items_per_page - 1) // self.items_per_page
        )
        self._page_index = (self._page_index + 1) % total_pages
        self._apply_page(self._page_index)


class PyBulletin9(QtWidgets.QMainWindow):
    """候診資訊系統 四診間版（固定全螢幕）."""

    ROOM_COUNT = len(Layout.ROOM_X_LIST)
    BACKGROUND_IMAGE = "./images/bulletin_background2.png"

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
        self._check_screen_resolution(monitor)

        # 先 move 再 show()，讓 windowHandle 綁到正確的螢幕，最後才全螢幕
        self.move(monitor.left(), monitor.top())
        self.show()
        self.showFullScreen()

    @staticmethod
    def _check_screen_resolution(monitor):
        """版面以 1920x1080 設計，解析度不符時提出警告（不中斷執行）."""
        if (monitor.width(), monitor.height()) == (DESIGN_WIDTH, DESIGN_HEIGHT):
            return

        print(
            f"警告：候診看板螢幕解析度為 {monitor.width()}x{monitor.height()}，"
            f"版面以 {DESIGN_WIDTH}x{DESIGN_HEIGHT} 設計，顯示位置可能偏移"
        )

    def _canvas(self):
        """所有 overlay 一律掛在同一個 widget 上，避免座標基準不一致."""
        return self.ui if self.ui is not None else self

    def show_bulletin(self):
        """顯示候診看板."""
        canvas = self._canvas()

        self.clock = ClockOverlay(canvas)

        self.refresh_waiting_room_info()

        self.waiting_room = []
        for i in range(self.ROOM_COUNT):
            self.waiting_room.append(
                WaitingRoom(
                    parent=canvas,
                    database=self.database,
                    system_settings=self.system_settings,
                    room=self.waiting_room_info[i][0],
                    doctor=self.waiting_room_info[i][1],
                    box_x=self.waiting_room_info[i][2],
                    box_w=Layout.ROOM_W,
                    items_per_page=len(Layout.ROOM_ROW_TOPS),
                    interval_sec=5,
                )
            )
            self.waiting_room[i].start()

        self.pharmacy = PharmacyBar(
            parent=canvas,
            database=self.database,
            system_settings=self.system_settings,
            items_per_page=Layout.PHARM_CELLS,
            interval_sec=5,
        )
        self.pharmacy.start()

        self._show_waiting_list()

    def refresh_waiting_room_info(self):
        self.waiting_room_info = [[None, None, x] for x in Layout.ROOM_X_LIST]

        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        current_period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
           SELECT Room, {weekday} AS Doctor FROM doctor_schedule
           WHERE
              Period = "{current_period}" AND
              {weekday} IS NOT NULL
           ORDER BY Room LIMIT {self.ROOM_COUNT}
        '''
        rows = self.database.select_record(sql)
        for row_no, row in enumerate(rows):
            if row_no >= self.ROOM_COUNT:
                break
            self.waiting_room_info[row_no][0] = row["Room"]
            self.waiting_room_info[row_no][1] = row["Doctor"]

    def _show_waiting_list(self):
        self.refresh_waiting_room_info()
        for i in range(len(self.waiting_room)):
            self.waiting_room[i].room = self.waiting_room_info[i][0]
            self.waiting_room[i].doctor = self.waiting_room_info[i][1]
            self.waiting_room[i].refresh()

        self.pharmacy.refresh()

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
        background = QtGui.QPixmap(self.BACKGROUND_IMAGE)
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
    # 看板座標全部寫死為實體像素，關掉 High DPI 縮放才不會整片偏移
    # （必須在建立 QApplication 之前設定）
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, True)

    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin9(None, sys.argv)
    py_bulletin.show_bulletin()
    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()
