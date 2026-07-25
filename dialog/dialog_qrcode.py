import cv2
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

from libs import system_utils

try:
    from pyzbar.pyzbar import decode
except ModuleNotFoundError:
    system_utils.pip3_install('pyzbar')
    from pyzbar.pyzbar import decode


class DialogQRCode(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("掃描 QRCode")
        self.setFixedSize(640, 480)

        self.qr_data = None

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_frame)
        self.timer.start(30)

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            self.qr_data = obj.data.decode("utf-8")
            self.accept()  # 關閉對話框並回傳成功
            return

        # 顯示畫面
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qt_image))

    def accept(self):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        super().accept()

    def reject(self):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        super().reject()

    @staticmethod
    def get_qr_code(parent=None):
        dialog = DialogQRCode(parent)
        result = dialog.exec_()
        return (result == QDialog.Accepted, dialog.qr_data)

