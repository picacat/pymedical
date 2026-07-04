# -*- coding: UTF-8 -*-
# libs/qrcode_scanner_utils.py

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtWidgets import QLineEdit


def read_vhc_basic_data(ic_card, qr_data):
    """設定虛擬健保卡並讀取基本資料, 成功回傳 True"""
    if not qr_data:
        return False

    ic_card.ic_card_type = "虛擬健保卡"
    ic_card.qrcode = qr_data

    return ic_card.read_register_basic_data(show_warning=False)


class QrCodeScanner(QObject):
    """
    虛擬健保卡 QR Code 掃描器。
    在指定視窗上建立隱藏輸入框接收掃描槍(鍵盤模擬)輸入。

    用法:
        scanner = QrCodeScanner(self)
        scanner.start(
            dialog=self.parent.show_vhc_in_progress(),
            on_scanned=self._on_scanned,      # 收到 qr_data 時呼叫: on_scanned(qr_data)
            on_cancelled=self._back_to_home,  # 取消或逾時呼叫
            timeout_ms=30000,
        )
    """

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._qr_input = None
        self._waiting = False
        self._timer = None
        self._dialog = None
        self._on_scanned = None
        self._on_cancelled = None

    def start(self, dialog, on_scanned, on_cancelled, timeout_ms=30000):
        self._dialog = dialog
        self._on_scanned = on_scanned
        self._on_cancelled = on_cancelled

        # 每次重新建立, 避免被 clear_all_widgets 之類的清除後變成殭屍物件
        self._qr_input = QLineEdit(self.window)
        self._qr_input.setGeometry(0, 0, 1, 1)
        self._qr_input.returnPressed.connect(self._scanned)
        self._qr_input.show()

        # 確保主視窗為作用中視窗, 焦點才拿得到掃描槍輸入
        self.window.activateWindow()
        self.window.raise_()
        self._qr_input.setFocus()
        self._waiting = True

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._timeout)
        self._timer.start(timeout_ms)

        # dialog 被關閉(取消)時
        dialog.finished.connect(self._cancelled)

    # ------------------------------------------------------------
    def _cleanup(self):
        self._waiting = False
        if self._timer is not None:
            self._timer.stop()
        if self._qr_input is not None:
            self._qr_input.hide()
            self._qr_input.deleteLater()
            self._qr_input = None

    def _scanned(self):
        if not self._waiting:
            return

        qr_data = self._qr_input.text().strip()
        self._cleanup()
        self._dialog.close()
        self._on_scanned(qr_data)

    def _timeout(self):
        if not self._waiting:
            return

        self._cleanup()
        self._dialog.close()
        self._on_cancelled()

    def _cancelled(self):
        if not self._waiting:
            return

        self._cleanup()
        self._on_cancelled()
