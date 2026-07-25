# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import os

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import system_utils

try:
    # os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    import cv2

    import_cv2 = True
except ImportError:
    import_cv2 = False

from libs import class_utils, string_utils, ui_utils


# 主視窗
class DialogCaptureImage(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCaptureImage, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.patient_key = args[3]
        self.capture_type = args[4]

        self.ui = None
        self.camera = None
        self.image_list = []

        self._set_ui()
        self._set_signal()
        if not import_cv2:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "模組未安裝",
                '<font size="5" color="red"><b>找不到OpenCV模組, 無法執行照相功能.</b></font>',
                "請聯絡軟體工程師安裝OpenCV模組.",
            )
            return

        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        # self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW, (cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY))
        # self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        if not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "相機模組未安裝",
                    '<font size="5" color="red"><b>找不到相機模組, 無法執行照相功能.</b></font>',
                    "請選購並安裝相機模組.",
                )
                return

        self.image_file_path = self.system_settings.field("影像檔路徑")
        self.WIDTH, self.HEIGHT = self._get_camera_max_resolution(self.camera)

        # if self.WIDTH == 1920:
        #     self.PREVIEW_WIDTH = int(self.WIDTH / 3)
        #     self.PREVIEW_HEIGHT = int(self.HEIGHT / 3)
        # else:
        #     self.PREVIEW_WIDTH = int(self.WIDTH)
        #     self.PREVIEW_HEIGHT = int(self.HEIGHT)

        self.PREVIEW_WIDTH = 720
        self.PREVIEW_HEIGHT = 480

        try:
            self._set_slider()
        except Exception:
            pass

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(30)
        self._timer.start()
        self._timer.timeout.connect(self._query_frame)

        if self.capture_type == "病歷影像":
            self.read_images()

    def _get_camera_max_resolution(self, camera):
        # 2K
        # camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        # camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)

        # 4K
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        # 2024-05-20 增加預覽速度
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))
        # 2024-05-20 開啟自動對焦
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        max_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        max_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)

        return max_width, max_height

    # 解構
    def __del__(self):
        self.close_all()

    def close_all(self):
        if self.camera is not None:
            if self._timer.isActive():
                self._timer.stop()
            self.camera.release()
            self.camera = None  # 確保設為 None
        cv2.destroyAllWindows()

    def closeEvent(self, event):
        self.close_all()
        event.accept()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CAPTURE_IMAGE, self)
        # self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("關閉")
        self.table_widget_capture_images = class_utils.get_table_widget(
            self.ui.tableWidget_capture_images, self.database
        )
        self._set_table_width()

        if self.capture_type == "病患照片":
            self.ui.tableWidget_capture_images.setVisible(False)
            self.resize(QtCore.QSize(800, 600))

    def _set_table_width(self):
        width = [330 for _ in range(self.ui.tableWidget_capture_images.columnCount())]
        self.table_widget_capture_images.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_capture.clicked.connect(self._capture_image)
        self.ui.buttonBox.accepted.connect(self._accepted_button_clicked)
        self.ui.keyPressEvent = self._key_pressed
        self.ui.slider_brightness.valueChanged.connect(self._set_brightness)
        self.ui.slider_contrast.valueChanged.connect(self._set_contrast)
        self.ui.slider_saturation.valueChanged.connect(self._set_saturation)
        self.ui.slider_hue.valueChanged.connect(self._set_hue)
        self.ui.slider_gain.valueChanged.connect(self._set_gain)
        self.ui.slider_exposure.valueChanged.connect(self._set_exposure)

    # override key press event
    def _key_pressed(self, event):
        key = event.key()

        if key in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Escape]:
            return

        return QtWidgets.QDialog.keyPressEvent(self.ui, event)

    def _accepted_button_clicked(self):
        self.close()

    def _query_frame(self):
        ret, frame = self.camera.read()

        # 檢查影像是否成功讀取
        if not ret or frame is None:
            print("警告：無法讀取相機影像")
            return  # 直接跳出函式，避免執行後續的 .shape

        self.frame = frame  # 確保 self.frame 是有效的

        if self.ui.checkBox_flip_image.isChecked():
            self.frame = cv2.flip(self.frame, 1)

        img_rows, img_cols, channels = self.frame.shape
        bytes_per_line = channels * img_cols

        cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB, self.frame)
        image = QtGui.QImage(
            self.frame.data,
            img_cols,
            img_rows,
            bytes_per_line,
            QtGui.QImage.Format_RGB888,
        )

        self.ui.label_camera.setPixmap(
            QtGui.QPixmap.fromImage(image).scaled(
                self.PREVIEW_WIDTH,
                self.PREVIEW_HEIGHT,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        )

    def _capture_image(self):
        if self.capture_type == "病患照片":
            self._capture_personal_photo()
        else:
            self._capture_medical_record_images()

    def _capture_personal_photo(self):
        if not hasattr(self, "frame") or self.frame is None:
            QtWidgets.QMessageBox.warning(self, "錯誤", "目前沒有影像可供拍攝")
            return

        filename = f"patient_{self.patient_key:0>6}.jpg"
        full_filename = os.path.join(self.image_file_path, filename)

        frame = self.frame
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, frame)
        cv2.imwrite(filename=full_filename, img=frame)

        self.close()

    def _capture_medical_record_images(self):
        # 確保 self.frame 真的有東西
        if not hasattr(self, "frame") or self.frame is None:
            return

        filename, full_filename = self._get_filename()

        frame = self.frame
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, frame)
        cv2.imwrite(filename=full_filename, img=frame)

        self._insert_record(filename)
        self.read_images()

    def _insert_record(self, filename):
        fields = ["CaseKey", "PatientKey", "Filename"]
        data = [self.case_key, self.patient_key, filename]
        self.database.insert_record("images", fields, data)

    def _insert_table_widget(self, frame):
        img_rows, img_cols, channels = frame.shape
        bytes_per_line = channels * img_cols
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, frame)
        image = QtGui.QImage(
            frame.data, img_cols, img_rows, bytes_per_line, QtGui.QImage.Format_RGB888
        )
        image_size = QtCore.QSize(self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT)

        self.ui.tableWidget_capture_images.setRowCount(
            self.ui.tableWidget_capture_images.rowCount() + 1
        )
        row_no = self.ui.tableWidget_capture_images.rowCount() - 1

        image_label = QtWidgets.QLabel(self.ui.tableWidget_capture_images)
        image_label.setPixmap(
            QtGui.QPixmap.fromImage(image).scaled(
                self.PREVIEW_WIDTH,
                self.PREVIEW_HEIGHT,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        )
        image_label.resize(image_size)
        self.ui.tableWidget_capture_images.setCellWidget(row_no, 1, image_label)
        self.ui.tableWidget_capture_images.resizeRowsToContents()

    def _get_filename(self):
        sql = f"""
            SELECT ImageKey FROM images
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)
        sequence = len(rows) + 1
        filename = f"{self.case_key}-{sequence}.jpg"
        full_filename = os.path.join(self.system_settings.field("影像檔路徑"), filename)

        return filename, full_filename

    def read_images(self):
        self.image_list = []

        sql = f"""
            SELECT * FROM images
            WHERE
                images.CaseKey = {self.case_key}
            ORDER BY TimeStamp
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._fit_images_to_table_widget(rows)

    def _fit_images_to_table_widget(self, rows):
        image_count = len(rows)
        column_count = self.ui.tableWidget_capture_images.columnCount()

        row_count = int(image_count / column_count)
        if image_count % column_count > 0:
            row_count += 1

        self.ui.tableWidget_capture_images.setRowCount(row_count)
        for row_no in range(row_count):
            for col_no in range(column_count):
                index = (row_no * column_count) + col_no
                if index >= image_count:
                    break

                image_date = rows[index]["TimeStamp"]
                filename = string_utils.xstr(rows[index]["Filename"])
                full_filename = os.path.join(self.image_file_path, filename)
                image_label = QtWidgets.QLabel(self.ui.tableWidget_capture_images)
                image_label.setTextFormat(QtCore.Qt.RichText)
                image_label.setText(f'''
                    {image_date}<br>
                    <img src="{full_filename}" width="320" height="180" align=middle><br>
                ''')
                self.ui.tableWidget_capture_images.setCellWidget(
                    row_no, col_no, image_label
                )
                self.image_list.append(filename)

        self.ui.tableWidget_capture_images.resizeRowsToContents()
        self.ui.tableWidget_capture_images.setCurrentCell(0, 0)

    def _remove_image(self):
        index = self._get_image_index()
        if index is None:
            return

        filename = self.image_list[index]
        full_filename = os.path.join(self.system_settings.field("影像檔路徑"), filename)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除影像檔")
        msg_box.setText(f'''
            <font size='4' color='red'>
                <b>確定刪除此筆影像資料?</b>
            </font><br>
            <img src="{full_filename}" width="320" height="180" align=middle>
        ''')
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        filename = self.image_list[index]
        full_filename = os.path.join(self.system_settings.field("影像檔路徑"), filename)
        sql = f'''
            DELETE FROM images
            WHERE
                Filename = "{filename}"
        '''
        self.database.exec_sql(sql)

        os.remove(full_filename)

        self.read_images()

    def _get_image_index(self):
        column_count = self.ui.tableWidget_capture_images.columnCount()
        row_no = self.ui.tableWidget_capture_images.currentRow()
        col_no = self.ui.tableWidget_capture_images.currentColumn()

        if row_no is None or col_no is None:
            return None

        index = (row_no * column_count) + col_no
        if index >= len(self.image_list):
            return None

        return index

    def _set_slider(self):
        self.ui.slider_brightness.setMinimum(0)
        self.ui.slider_brightness.setMaximum(255)
        self.ui.slider_brightness.setValue(self.camera.get(cv2.CAP_PROP_BRIGHTNESS))

        self.ui.slider_contrast.setMinimum(0)
        self.ui.slider_contrast.setMaximum(255)
        self.ui.slider_contrast.setValue(self.camera.get(cv2.CAP_PROP_CONTRAST))

        self.ui.slider_saturation.setMinimum(0)
        self.ui.slider_saturation.setMaximum(255)
        self.ui.slider_saturation.setValue(self.camera.get(cv2.CAP_PROP_SATURATION))

        self.ui.slider_hue.setMinimum(0)
        self.ui.slider_hue.setMaximum(255)
        self.ui.slider_hue.setValue(self.camera.get(cv2.CAP_PROP_HUE))

        self.ui.slider_gain.setMinimum(0)
        self.ui.slider_gain.setMaximum(255)
        self.ui.slider_gain.setValue(self.camera.get(cv2.CAP_PROP_GAIN))

        self.ui.slider_exposure.setMinimum(0)
        self.ui.slider_exposure.setMaximum(255)
        self.ui.slider_exposure.setValue(self.camera.get(cv2.CAP_PROP_EXPOSURE))

    def _set_brightness(self):
        self.camera.set(cv2.CAP_PROP_BRIGHTNESS, self.ui.slider_brightness.value())

    def _set_contrast(self):
        self.camera.set(cv2.CAP_PROP_CONTRAST, self.ui.slider_contrast.value())

    def _set_saturation(self):
        self.camera.set(cv2.CAP_PROP_SATURATION, self.ui.slider_saturation.value())

    def _set_hue(self):
        self.camera.set(cv2.CAP_PROP_HUE, self.ui.slider_hue.value())

    def _set_gain(self):
        self.camera.set(cv2.CAP_PROP_GAIN, self.ui.slider_gain.value())

    def _set_exposure(self):
        self.camera.set(cv2.CAP_PROP_EXPOSURE, self.ui.slider_exposure.value())
