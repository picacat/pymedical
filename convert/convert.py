
# 資料轉檔 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton, QFileDialog
import datetime

try:
    import pyodbc
except Exception:
    pass

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils

from convert import cvt_utec
from convert import cvt_kthis
from convert import cvt_tm
from convert import cvt_cm
from convert import cvt_gp
from convert import cvt_vis
from convert import cvt_cm2

import check_database


# 主視窗
class DialogConvert(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogConvert, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.source_db = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CONVERT, self)
        # self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setText('開始轉檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.No).setText('關閉')
        self._set_combo_box()
        self.ui.tabWidget_convert.setCurrentIndex(0)

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_dosage_mode, ['日劑量', '次劑量'])
        ui_utils.set_combo_box(self.ui.comboBox_utec_product, ['Medical', 'Med2000'])
        ui_utils.set_combo_box(
            self.ui.comboBox_tour_area,
            nhi_utils.TOUR_AREA_LEVEL['山地鄉'] +
            nhi_utils.TOUR_AREA_LEVEL['一級離島'] +
            nhi_utils.TOUR_AREA_LEVEL['二級離島'] +
            nhi_utils.TOUR_AREA_LEVEL['三級離島'],
            None
        )
        ui_utils.set_combo_box(self.ui.comboBox_lack_area, nhi_utils.TOUR_AREA_LEVEL['資源不足'], None)
        ui_utils.set_combo_box(
            self.ui.comboBox_correction_area,
            nhi_utils.CORRECTION_AREA_DICT[self.system_settings.field('健保業務')], None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.pushButton_test_connection.clicked.connect(self.test_connection)  # 友杏
        
        self.ui.pushButton_change_encoding.clicked.connect(self.change_encoding)
        self.ui.pushButton_convert_images.clicked.connect(self.convert_images)

        self.ui.pushButton_test_connection_kt.clicked.connect(self.test_connection_kt)
        self.ui.pushButton_test_connection_tm.clicked.connect(self.test_connection_tm)
        self.ui.pushButton_test_connection_cm.clicked.connect(self.test_connection_cm)
        self.ui.pushButton_test_connection_gp.clicked.connect(self.test_connection_gp)
        self.ui.pushButton_test_connection_cm2.clicked.connect(self.test_connection_cm2)

        self.ui.toolButton_set_vis_path.clicked.connect(self.set_vis_path)
        self.ui.pushButton_sqlite3.clicked.connect(self.create_sqlite3)

    def set_vis_path(self):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self, "選擇展望資料庫路徑",
            self.ui.lineEdit_vis_db_path.text(), options=options
        )
        if directory:
            self.ui.lineEdit_vis_db_path.setText(directory)

    def create_sqlite3(self):
        cvt = cvt_vis.CvtVIS(self)
        cvt.create_sqlite3()

        del cvt

    # 開始轉檔
    def accepted_button_clicked(self):
        tab_name = self.ui.tabWidget_convert.tabText(self.ui.tabWidget_convert.currentIndex())
        if tab_name == '友杏':
            cvt = cvt_utec.CvtUtec(self)
            check_box_database = self.ui.checkBox_database
        elif tab_name == '國泰':
            cvt = cvt_kthis.CvtKThis(self)
            check_box_database = self.ui.checkBox_database_kt
        elif tab_name == '天明':
            cvt = cvt_tm.CvtTM(self)
            check_box_database = self.ui.checkBox_database_tm
        elif tab_name == '精典':
            cvt = cvt_cm.CvtCM(self)
            check_box_database = self.ui.checkBox_database_cm
        elif tab_name == '巨騰':
            cvt = cvt_gp.CvtGP(self)
            check_box_database = self.ui.checkBox_database_gp
        elif tab_name == '展望':
            cvt = cvt_vis.CvtVIS(self)
        elif tab_name == '中醫智庫':
            cvt = cvt_cm2.CvtCM2(self)
            check_box_database = self.ui.checkBox_database_cm2
        else:
            return

        if tab_name != '展望' and check_box_database.isChecked():  # 展望使用foxpro
            self.ui.progressBar.setMaximum(100)
            self.ui.progressBar.setValue(0)
            check_db = check_database.CheckDatabase(
                self, self.database, self.system_settings, 'convert')
            check_db.check_database()
            del check_db

            self.ui.progressBar.setValue(100)

        cvt.convert()

    # 關閉
    def rejected_button_clicked(self):
        self.close()

    def test_connection(self):
        if string_utils.xstr(self.ui.lineEdit_database.text()) == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! 資料庫名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入資料庫名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self.source_db = class_utils.get_db(
            host=self.ui.lineEdit_host.text(),
            user=self.ui.lineEdit_user.text(),
            password=self.ui.lineEdit_password.text(),
            charset=self.ui.lineEdit_charset.text(),
            database=self.ui.lineEdit_database.text(),
        )
        if not self.source_db.connected():
            return

        self.ui.label_connection_status.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        self.utec_db = None
        if string_utils.xstr(self.ui.lineEdit_old_database.text()) != '':
            self.utec_db = class_utils.get_db(
                host=self.ui.lineEdit_host.text(),
                user=self.ui.lineEdit_user.text(),
                password=self.ui.lineEdit_password.text(),
                charset=self.ui.lineEdit_charset.text(),
                database=self.ui.lineEdit_old_database.text(),
            )
            if self.utec_db.connected():
                self.ui.label_connection_status.setText('已連線')
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle('連線成功')
                msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至友杏資料庫主機成功.</b></font>")
                msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()

    def test_connection_kt(self):
        if string_utils.xstr(self.ui.lineEdit_database_kt.text()) == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! 資料庫名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入資料庫名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return
        
        self.source_db = class_utils.get_db(
            host=self.ui.lineEdit_host_kt.text(),
            user=self.ui.lineEdit_user_kt.text(),
            password=self.ui.lineEdit_password_kt.text(),
            charset=self.ui.lineEdit_charset_kt.text(),
            database=self.ui.lineEdit_database_kt.text(),
        )
        if not self.source_db.connected():
            return

        self.ui.label_connection_status_kt.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        self.utec_db = None
        if string_utils.xstr(self.ui.lineEdit_old_database.text()) != '':
            self.utec_db = class_utils.get_db(
                host=self.ui.lineEdit_host.text(),
                user=self.ui.lineEdit_user.text(),
                password=self.ui.lineEdit_password.text(),
                charset=self.ui.lineEdit_charset.text(),
                database=self.ui.lineEdit_old_database.text(),
            )
            if self.utec_db.connected():
                self.ui.label_connection_status.setText('已連線')
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle('連線成功')
                msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至友杏資料庫主機成功.</b></font>")
                msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
                msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
                msg_box.exec_()

    def test_connection_tm(self):
        dsn = self.ui.lineEdit_dsn_tm.text()
        if dsn == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! dsn名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入ODBC名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        try:
            conn = pyodbc.connect(f'DSN={dsn};UID="";PWD=""')
            _ = conn.cursor()
        except Exception:
            self.ui.label_connection_status_tm.setText('連線失敗')
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='red'><b>連線至資料庫主機失敗.</b></font>")
            msg_box.setInformativeText("連線失敗, 請檢查ODBC設定.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self.ui.label_connection_status_tm.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def test_connection_cm2(self):
        dsn = self.ui.lineEdit_dsn_cm2.text()
        if dsn == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! dsn名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入ODBC名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        try:
            conn = pyodbc.connect(f'DSN={dsn};UID="";PWD=""')
            _ = conn.cursor()
        except Exception:
            self.ui.label_connection_status_tm.setText('連線失敗')
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='red'><b>連線至資料庫主機失敗.</b></font>")
            msg_box.setInformativeText("連線失敗, 請檢查ODBC設定.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self.ui.label_connection_status_cm2.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def test_connection_gp(self):
        dsn = self.ui.lineEdit_dsn_gp.text()
        if dsn == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! dsn名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入ODBC名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        try:
            conn = pyodbc.connect(f'DSN={dsn};UID="";PWD=""')
            _ = conn.cursor()
        except Exception:
            self.ui.label_connection_status_gp.setText('連線失敗')
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='red'><b>連線至資料庫主機失敗.</b></font>")
            msg_box.setInformativeText("連線失敗, 請檢查ODBC設定.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self.ui.label_connection_status_gp.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def test_connection_cm(self):
        if string_utils.xstr(self.ui.lineEdit_database_cm.text()) == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('連線失敗')
            msg_box.setText("<font size='4' color='Red'><b>連線至資料庫主機失敗! 資料庫名稱空白.</b></font>")
            msg_box.setInformativeText("請輸入資料庫名稱.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        if self.ui.radioButton_windows_auth_cm.isChecked():
            auth_type = 'windows'
        else:
            auth_type = 'sql'

        self.source_db = class_utils.get_mssql_db(
            host=self.ui.lineEdit_host_cm.text(),
            user=self.ui.lineEdit_user_cm.text(),
            password=self.ui.lineEdit_password_cm.text(),
            charset=self.ui.lineEdit_charset_cm.text(),
            database=self.ui.lineEdit_database_cm.text(),
            auth=auth_type,
        )
        if not self.source_db.connected():
            return

        self.ui.label_connection_status_cm.setText('已連線')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('連線成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 連線至資料庫主機成功.</b></font>")
        msg_box.setInformativeText("連線成功, 可以執行轉檔作業.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def convert_images(self):
        cvt = cvt_utec.CvtUtec(self)
        cvt.convert_images()

    def change_encoding(self):
        charset = self.ui.lineEdit_charset.text()
        database_name = self.ui.lineEdit_database.text()
        sql = f'''
            SELECT
                CONCAT('ALTER TABLE ', tbl.TABLE_NAME, ' CONVERT TO CHARACTER SET {charset};') AS exec_script
            FROM
                information_schema.TABLES tbl
            WHERE
                tbl.TABLE_SCHEMA = '{database_name}'
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self.progressBar.setMaximum(row_count)
        self.progressBar.setValue(0)
        for row_no, row in enumerate(rows):
            self.progressBar.setValue(row_no)

            exec_script = row['exec_script']
            try:
                self.database.exec_sql(exec_script)
            except Exception:
                print(exec_script)

        self.progressBar.setValue(row_count)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('更改成功')
        msg_box.setText("<font size='4' color='Blue'><b>恭喜您! 資料庫編碼更改成功.</b></font>")
        msg_box.setInformativeText("編碼更改成功, 可以儲存更新後的編碼.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()
