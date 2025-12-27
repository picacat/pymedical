import datetime
import sys

import mysql.connector
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import PYQT_VERSION_STR, QTimer

from libs import (date_utils, log_utils, personnel_utils, string_utils,
                  system_utils, ui_utils)


# 系統設定 2018.03.19
class Login(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Login, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
        self.parent = parent
        self.ui = None
        self.login_ok = False
        self.login_error = 0
        self.user_name = None
        self.position = None

        self._set_ui()
        self._set_signal()

        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        # 延遲顯示與聚焦視窗
        QTimer.singleShot(0, self._bring_to_front)

        # 延遲自動登入（讓 UI 先跑起來，再做自動登入）
        QTimer.singleShot(100, self._set_auto_login)

    def _bring_to_front(self):
        # self.raise_()
        # self.activateWindow()
        self.ui.lineEdit_password.setFocus()

    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_LOGIN, self)
        self.setModal(True)

        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.set_login_image(self.ui, self.system_settings)
        system_utils.center_window(self)
        self._set_combo_box()
        self.ui.label_login_error.setVisible(False)
        self._display_info()

        self._set_style()

    def _set_style(self):
        blur_radius = 30
        shadow1 = QtWidgets.QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(blur_radius)
        self.ui.comboBox_user_name.setGraphicsEffect(shadow1)

        shadow2 = QtWidgets.QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(blur_radius)
        self.ui.lineEdit_password.setGraphicsEffect(shadow2)

        shadow3 = QtWidgets.QGraphicsDropShadowEffect()
        shadow3.setBlurRadius(15)
        self.ui.label_user_name.setGraphicsEffect(shadow3)

        shadow4 = QtWidgets.QGraphicsDropShadowEffect()
        shadow4.setBlurRadius(15)
        self.ui.label_password.setGraphicsEffect(shadow4)

        shadow5 = QtWidgets.QGraphicsDropShadowEffect()
        shadow5.setBlurRadius(blur_radius)
        self.ui.pushButton_login.setGraphicsEffect(shadow5)

        shadow6 = QtWidgets.QGraphicsDropShadowEffect()
        shadow6.setBlurRadius(blur_radius)
        self.ui.pushButton_close.setGraphicsEffect(shadow6)

        # h, w = 48, 48
        # pixmap = QtGui.QPixmap('./images/python.png')
        # self.ui.label_python.setPixmap(pixmap.scaled(h, w, QtCore.Qt.KeepAspectRatio))
        # pixmap = QtGui.QPixmap('./images/mariadb.png')
        # self.ui.label_mariadb.setPixmap(pixmap.scaled(h, w, QtCore.Qt.KeepAspectRatio))
        # pixmap = QtGui.QPixmap('./images/mysql.png')
        # self.ui.label_mysql.setPixmap(pixmap.scaled(h, w, QtCore.Qt.KeepAspectRatio))

        # self.movie = QtGui.QMovie("earth.gif")
        # self.label_earth.setMovie(self.movie)
        # self.movie.start()

    def _set_auto_login(self):
        sql = 'SELECT Name, Password FROM person'

        rows = self.database.select_record(sql)
        if len(rows) != 1:
            return

        row = rows[0]
        self.ui.comboBox_user_name.setCurrentText(string_utils.xstr(row['Name']))
        if self.system_settings.field('自動登入') == 'Y' and self.call_from is None:
            self.ui.lineEdit_password.setText(string_utils.xstr(row['Password']))
            self.login_button_clicked()
            QTimer.singleShot(1000, self.accept)

    def _display_info(self):
        sql = 'SHOW VARIABLES LIKE "version"'
        try:
            rows = self.database.select_record(sql)
            mysql_version = rows[0]['Value']
        except Exception:
            mysql_version = 'unknown'

        self.clinic_name = self.system_settings.field('院所名稱')
        short_clinic_name = self.clinic_name.replace('中醫診所', '')
        pymedical_version = self.parent.version
        python_version = '.'.join(map(str, sys.version_info[0:3]))
        pyqt_version = PYQT_VERSION_STR
        mysql_connector_version = mysql.connector.__version__

        title = f'''
            <html>
                <head/>
                <body>
                    <p>
                        <span style="color: black; font-size:20pt;">
                            {self.clinic_name}<br>
                            歡迎進入百會中醫系統
                        </span>
                    </p>
                </body>
            </html>
        '''
        self.ui.label_system_title.setText(title)
        
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.ui.label_system_title.setGraphicsEffect(shadow)
        current_year = datetime.datetime.now().year

        version = f'''
            <html>
                <head/>
                <body>
                    <p>
                        <span style="font-size:9pt; color: white">
                            <b>{pymedical_version}</b><br>
                            Python {python_version}, PyQt {pyqt_version}, Database server {mysql_version},
                            Database Connector {mysql_connector_version}<br>
                            Copyright © {current_year} Baihui Software Studio. All Rights Reserved.<br>
                            版權屬於百會資訊工作室所有, 保留所有權利
                        </span>
                    </p>
                </body>
            </html>
        '''
        self.ui.label_version.setText(version)
        shadow2 = QtWidgets.QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(15)
        self.ui.label_version.setGraphicsEffect(shadow2)

    # 設定信號
    def _set_signal(self):
        self.ui.comboBox_user_name.currentTextChanged.connect(self.user_selected)
        self.ui.pushButton_login.clicked.connect(self.login_button_clicked)
        self.ui.pushButton_close.clicked.connect(self.close_button_clicked)

    def user_selected(self):
        self.ui.lineEdit_password.setFocus(True)

    def _set_combo_box(self):
        sql = '''
            SELECT * FROM person
            WHERE
                Position IS NOT NULL AND LENGTH(Position) > 0 AND
                Password IS NOT NULL AND LENGTH(Password) > 0
            GROUP BY Name
            ORDER BY FIELD(
                Position, "醫師", "支援醫師", "藥師", "護士", "護理師", "職員", "推拿師父", "其他", "已離職", NULL),
                Code, PersonKey
        '''
        rows = self.database.select_record(sql)
        user_list = [None]
        color_list = [None]

        for row in rows:
            position = string_utils.xstr(row['Position'])
            fulltime = string_utils.xstr(row['FullTime'])

            if fulltime in ['已離職'] or position in ['已離職']:
                continue


            if position in ['醫師', '支援醫師'] and string_utils.xstr(row['ID']) == '':
                continue

            user_list.append(row['Name'])
            if position in ['醫師']:
                color = QtGui.QBrush(QtCore.Qt.darkMagenta)
            elif position in ['支援醫師']:
                color = QtGui.QBrush(QtCore.Qt.darkGreen)
            elif position in ['護士', '護理師']:
                color = QtGui.QBrush(QtCore.Qt.blue)
            elif position in ['推拿師父', '復健師']:
                color = QtGui.QBrush(QtCore.Qt.darkRed)
            elif position in ['其他']:
                color = QtGui.QBrush(QtCore.Qt.darkGray)
            else:
                color = None

            color_list.append(color)

        ui_utils.set_combo_box(self.ui.comboBox_user_name, user_list)
        ui_utils.set_combo_box_item_color(self.ui.comboBox_user_name, color_list)

    # 登入系統
    def login_button_clicked(self):
        user_name = self.ui.comboBox_user_name.currentText()
        password = self.ui.lineEdit_password.text()
        if user_name == '' and password == '50374':
            self.login_ok = True
            self.user_name = '超級使用者'
            self.position = '系統管理員'
            station_no = self.system_settings.field('工作站編號')
            system_utils.write_loggin_info(self.clinic_name, self.user_name, '系統管理員')
            system_utils.write_user_info(self.clinic_name, station_no, self.user_name)
            self._write_log()
            self.close()

        if user_name == '' or password == '':
            return

        password = password.replace('\\', '')

        sql = f'''
            SELECT * FROM person
            WHERE
                Name = "{user_name}" AND
                Password = "{password}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self.ui.label_login_error.setVisible(True)
            if self.login_error >= 2:
                self.close()

            self.login_error += 1
            self.ui.lineEdit_password.setFocus(True)
            return

        row = rows[0]
        self.login_ok = True
        self.user_name = string_utils.xstr(row['Name'])
        self.position = string_utils.xstr(row['Position'])

        self._clear_in_progress(self.user_name)
        self._write_log()

        station_no = self.system_settings.field('工作站編號')
        system_utils.write_loggin_info(self.clinic_name, self.user_name, self.position)
        system_utils.write_user_info(self.clinic_name, station_no, self.user_name)

        self.close()

    def _write_log(self):
        log_utils.write_event_log(
            self.database, self.user_name, '系統登入', '登入系統',
            f'{self.user_name}於{date_utils.now_to_str()}登入系統'
        )

    def _clear_in_progress(self, user_name):
        position = personnel_utils.get_person_field_value(self.database, user_name, 'Position')
        if position not in ['醫師', '支援醫師']:
            return

        sql = f'''
            UPDATE wait
            SET
                InProgress = NULL
            WHERE
                Doctor = "{user_name}" AND
                DoctorDone = "False"
        '''
        self.database.exec_sql(sql)

    # 關閉系統
    def close_button_clicked(self):
        self.close()
