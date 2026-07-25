#!/usr/bin/env python3
#coding: utf-8

import sys

from PyQt5 import QtWidgets, QtGui

from libs import ui_utils
from libs import patient_utils
from libs import date_utils


# 樣板 2018.01.31
class FirstVisitRegistration(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(FirstVisitRegistration, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_FIRST_VISIT_REGISTRATION, self)
        style = '''
            QMainWindow#WindowFirstVisitRegistration 
            {background-image: url(./images/home.jpg);}
        '''
        self.ui.setStyleSheet(style)
        self.ui.label_message.setStyleSheet("QLabel {color : white; }")

        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setBlurRadius(0)
        effect.setColor(QtGui.QColor('black'))
        effect.setOffset(1, 2)
        self.ui.label_message.setGraphicsEffect(effect)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_save_file.clicked.connect(self._save_file)
        self.ui.toolButton_back.clicked.connect(self._back_registration_insert_card)
        self.ui.toolButton_back_home.clicked.connect(self._back_home)

    def set_registration_data(self, basic_data):
        self.basic_data = basic_data
        share_type =  basic_data['insured_mark']
        if share_type == '基層醫療':
            share_type = '一般健保'

        self.ui.label_message.setText(
            '''
                {name} 您好<br>
                您之前並未在本院就診過，<br>
                以下是您的基本資料:<br>
                姓名: {name}<br>
                生日: {birthday}<br>
                身分證: {id}<br>
                健保身分: {share_type}<br><br>
                請問以上是否正確?
            '''.format(
                name=self.basic_data['name'],
                birthday=self.basic_data['birthday'],
                id=self.basic_data['patient_id'],
                share_type=share_type,
            )
        )

    def _save_file(self):
        gender_code = self.basic_data['patient_id'][1]
        gender = patient_utils.get_gender(gender_code)
        nationality = patient_utils.get_nationality(gender_code)

        fields = [
            'CardNo', 'Name', 'Birthday', 'ID', 'Gender', 'Nationality', 'InsType', 'InitDate',
        ]
        data = [
            self.basic_data['card_no'],
            self.basic_data['name'],
            self.basic_data['birthday'],
            self.basic_data['patient_id'],
            gender,
            nationality,
            self.basic_data['insured_mark'],
            date_utils.date_to_str(),
        ]
        self.database.insert_record('patient', fields, data)
        self.parent.open_registration(self.basic_data, '初診', None, None)

    def _back_registration_insert_card(self):
        self.parent.open_registration_insert_card()

    def _back_home(self):
        self.parent.open_home()
        # 自動連續療程 - 30天內

