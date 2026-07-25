
# -*- coding: UTF-8 -*-

import os
import sys
import shutil

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QPushButton, QFileDialog
import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import personnel_utils
from libs import system_utils


# 病歷資料 2018.01.31
class MedicalRecordImage(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordImage, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.patient_key = args[3]

        self._set_ui()
        self._set_signal()  # 先讀完資料才設定信號

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.image_list = []

        self._set_permission()
        self.read_images()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_IMAGE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_image_history = class_utils.get_table_widget(
            self.ui.tableWidget_image_history, self.database
        )
        self._set_table_width()
        self.ui.toolButton_remove_image.setEnabled(False)

    def _set_table_width(self):
        width = [330, 330, 330, 330, 330]
        self.table_widget_image_history.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_remove_image.clicked.connect(self._remove_image)
        self.ui.toolButton_capture_image.clicked.connect(self._capture_image)
        self.ui.toolButton_load_image.clicked.connect(self._load_image)
        self.ui.toolButton_load_image_from_clipboard.clicked.connect(self._load_image_from_clipboard)
        self.ui.tableWidget_image_history.doubleClicked.connect(self._open_image_file)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

    def get_image_count(self):
        sql = f'''
            SELECT * FROM images
            WHERE
                images.PatientKey = {self.patient_key}
            ORDER BY TimeStamp
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def read_images(self):
        self.ui.toolButton_remove_image.setEnabled(False)
        self.ui.tableWidget_image_history.setRowCount(0)
        self.image_list = []

        sql = f'''
            SELECT images.*, cases.CaseDate FROM images
                LEFT JOIN cases ON cases.CaseKey = images.CaseKey
            WHERE
                images.PatientKey = {self.patient_key}
            ORDER BY CaseKey DESC
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._fit_images_to_table_widget(rows)

    def _fit_images_to_table_widget(self, rows):
        self.ui.toolButton_remove_image.setEnabled(True)
        image_file_path = self.system_settings.field('影像檔路徑')

        self.ui.label_heading.setText('病歷影像資料')
        if image_file_path in ['', None]:
            self.ui.label_heading.setText(
                '<font color="red"><b>系統設定未設定影像資料檔路徑, 無法顯示影像資料, 請設定完成後再檢視病歷影像.</b></font>'
            )
            return

        image_count = len(rows)
        column_count = self.ui.tableWidget_image_history.columnCount()

        row_count = int(image_count / column_count)
        if image_count % column_count > 0:
            row_count += 1

        self.ui.tableWidget_image_history.setRowCount(row_count)
        for row_no in range(row_count):
            for col_no in range(column_count):
                index = (row_no * column_count) + col_no
                if index >= image_count:
                    break

                filename = string_utils.xstr(rows[index]['Filename'])
                full_filename = os.path.join(image_file_path, filename)
                try:
                    image_date = rows[index]['CaseDate'].date()
                except Exception:
                    image_date = rows[index]['TimeStamp'].date()

                image_file = full_filename
                filename = os.path.basename(full_filename)
                image_label = QtWidgets.QLabel(self.ui.tableWidget_image_history)
                image_label.setTextFormat(QtCore.Qt.RichText)
                image_label.setText(f'''
                    {image_date} {filename}<br>
                    <img src="{image_file}" width="320" height="180" align=middle><br>
                ''')
                self.ui.tableWidget_image_history.setCellWidget(row_no, col_no, image_label)
                self.image_list.append(filename)

        self.ui.tableWidget_image_history.resizeRowsToContents()
        self.ui.tableWidget_image_history.setCurrentCell(0, 0)

    def _capture_image(self):
        self.parent.capture_image()

    def _load_image(self):
        options = QFileDialog.Options()
        source_file, _ = QFileDialog.getOpenFileName(
            self, '開啟影像檔',
            '*.jpg', 'jpg 檔 (*.jpg);;All Files (*.*)',
            options=options
        )
        if not source_file:
            return

        image_file_path = self.system_settings.field('影像檔路徑')
        filename = os.path.basename(source_file)
        image_file = os.path.join(image_file_path, filename)

        if source_file != image_file:
            shutil.copy2(source_file, image_file)

        self._insert_record(filename)
        self.read_images()

    def _load_image_from_clipboard(self):
        import sys
        if sys.platform == 'linux':
            img = self._load_image_from_linux_clipboard()
        else:
            img = self._load_image_from_win32_macos_clipboard()

        if img is None:
            return

        image_file_path = self.system_settings.field('影像檔路徑')
        source_file = datetime.datetime.today().strftime('%Y%m%d%H%M%S') + '.png'

        filename = os.path.basename(source_file)
        image_file = os.path.join(image_file_path, filename)
        img.save(image_file, 'PNG')

        self._insert_record(filename)
        self.read_images()

    @staticmethod
    def _load_image_from_linux_clipboard():
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()

        return img

    @staticmethod
    def _load_image_from_win32_macos_clipboard():
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()

        return img

    def _insert_record(self, filename):
        fields = ['CaseKey', 'PatientKey', 'Filename']
        data = [self.case_key, self.patient_key, filename]
        self.database.insert_record('images', fields, data)

    def _remove_image(self):
        index = self._get_image_index()
        if index is None:
            return

        filename = self.image_list[index]
        full_filename = os.path.join(self.system_settings.field('影像檔路徑'), filename)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除影像檔')
        msg_box.setText(f"""
            <font size='4' color='red'><b>確定刪除此筆影像資料?</b></font><br>
            <img src="{full_filename}" width="320" height="180" align=middle>
        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        filename = self.image_list[index]
        full_filename = os.path.join(self.system_settings.field('影像檔路徑'), filename)
        sql = f'''
            DELETE FROM images
            WHERE
                Filename = "{filename}"
        '''
        self.database.exec_sql(sql)

        try:
            os.remove(full_filename)
        except FileNotFoundError:
            pass

        self.read_images()

    def _get_image_index(self):
        column_count = self.ui.tableWidget_image_history.columnCount()
        row_no = self.ui.tableWidget_image_history.currentRow()
        col_no = self.ui.tableWidget_image_history.currentColumn()

        if row_no is None or col_no is None:
            return None

        index = (row_no * column_count) + col_no
        if index >= len(self.image_list):
            return None

        return index

    def _open_image_file(self):
        index = self._get_image_index()
        if index is None:
            return

        filename = self.image_list[index]
        full_filename = os.path.join(self.system_settings.field('影像檔路徑'), filename)

        if sys.platform == 'win32':
            os.system(f'start "" "{full_filename}"')
        else:
            desktop_session = os.environ.get("DESKTOP_SESSION")
            if desktop_session is not None:
                desktop_session = desktop_session.lower()

            if desktop_session == 'plasma':  # kde
                os.system(f'gwenview {full_filename}')
            else:
                os.system(f'viewnior {full_filename}')

            # os.system(f'viewnior {full_filename}')
