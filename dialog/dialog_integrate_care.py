
# 複雜性針灸選取視窗 2021.02.24
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
import datetime
from libs import system_utils
from libs import ui_utils
from libs import web_utils
from libs import case_utils
from libs import date_utils
from libs import dialog_utils


# 主視窗
class DialogIntegrateCare(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogIntegrateCare, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]

        self.ui = None
        self.select_integrate_care = False
        self.symptom_list = []
        self.case_date, self.patient_key = self._get_case_data()

        self._set_ui()
        self._set_signal()

        self.check_box_list = [
            self.ui.checkBox_1, self.ui.checkBox_2, self.ui.checkBox_3,
            self.ui.checkBox_4, self.ui.checkBox_5, self.ui.checkBox_6,
            self.ui.checkBox_7, self.ui.checkBox_8, self.ui.checkBox_9, self.ui.checkBox_10,
            self.ui.checkBox_11, self.ui.checkBox_12, self.ui.checkBox_13,
            self.ui.checkBox_14, self.ui.checkBox_15, self.ui.checkBox_16,
            self.ui.checkBox_17, self.ui.checkBox_18, self.ui.checkBox_19, self.ui.checkBox_20,
            self.ui.checkBox_21, self.ui.checkBox_22, self.ui.checkBox_23,
            self.ui.checkBox_24, self.ui.checkBox_25, self.ui.checkBox_26,
            self.ui.checkBox_27, self.ui.checkBox_28, self.ui.checkBox_29,
        ]

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _get_case_data(self):
        sql = f'''
            SELECT CaseDate, DoctorDate, PatientKey FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None

        row = rows[0]

        try:
            doctor_date = case_utils.get_case_extend(self.database, self.case_key, '病歷登錄時間')
            if doctor_date not in ['', None]:
                doctor_date = date_utils.str_to_datetime(doctor_date)
            else:
                doctor_date = datetime.datetime.now()
        except Exception:
            doctor_date = datetime.datetime.now()

        return doctor_date, row['PatientKey']

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INTEGRATE_CARE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)

        self.ui.setWindowTitle('中醫整合醫療照護')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        minutes = 10
        self.ui.spinBox_time.setMinimum(minutes)
        self.ui.spinBox_time.setValue(minutes)

        case_time = self.case_date + datetime.timedelta(minutes=5)
        self.ui.timeEdit_start_time.setTime(case_time.time())
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(minutes * 60)
        )
        self.ui.timeEdit_start_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)
        self.ui.timeEdit_end_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)
        self._set_evaluate()

    def _set_evaluate(self):
        sql = f'''
            SELECT cases.CaseDate, caseextend.* FROM cases
                LEFT JOIN caseextend ON caseextend.CaseKey = cases.CaseKey
            WHERE
                DATE(cases.CaseDate) < "{self.case_date.strftime('%Y-%m-%d')}" AND
                cases.PatientKey = {self.patient_key} AND
                caseextend.ExtendType = "整合醫療照護" AND
                caseextend.Content = "Y"
            ORDER BY cases.CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            self.ui.label_evaluate.setText(f'評估內容: (上次整合醫療照護日期: {row["CaseDate"].strftime("%Y-%m-%d")})')
            self.ui.textEdit_evaluate.setPlaceholderText('必填欄位, 請在此輸入評估內容')
        else:
            self.ui.label_evaluate.setText('評估內容:')
            self.ui.textEdit_evaluate.setPlaceholderText('首次執行整合醫療照護, 非必填欄位')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_dict.clicked.connect(self._open_symptom_dialog)

        self.ui.checkBox_tv.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_talk.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_paper.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_prescription.clicked.connect(self._set_check_box_color)
        self.ui.textEdit_evaluate.textChanged.connect(self._set_integrate_care_ok)

        self.ui.checkBox_1.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_2.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_3.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_4.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_5.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_6.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_7.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_8.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_9.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_10.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_11.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_12.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_13.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_14.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_15.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_16.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_17.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_18.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_19.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_20.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_21.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_22.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_23.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_24.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_25.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_26.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_27.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_28.clicked.connect(self._check_box_clicked)
        self.ui.checkBox_29.clicked.connect(self._check_box_clicked)

        self.ui.timeEdit_start_time.timeChanged.connect(self._set_treat_time)
        self.ui.timeEdit_end_time.timeChanged.connect(self._set_treat_time)
        self.ui.spinBox_time.valueChanged.connect(self._set_treat_time)

    def _set_treat_time(self):
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(self.ui.spinBox_time.value() * 60)
        )

    def _set_integrate_care_ok(self):
        check_box1_ok = False
        check_box2_ok = False

        check_box_list1 = [
            self.ui.checkBox_tv, self.ui.checkBox_talk,
            self.ui.checkBox_paper, self.ui.checkBox_prescription,
        ]
        for check_box in check_box_list1:
            if check_box.isChecked():
                check_box1_ok = True
                break

        for check_box in self.check_box_list:
            if check_box.isChecked():
                check_box2_ok = True
                break

        if check_box1_ok and check_box2_ok:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
            if '上次整合醫療照護' in self.ui.label_evaluate.text() and self.ui.textEdit_evaluate.toPlainText() == '':
                self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def accepted_button_clicked(self):
        self.select_integrate_care = True

    def is_select_integrate_care(self):
        return self.select_integrate_care

    def get_symptom(self):
        start_time = self.ui.timeEdit_start_time.time().toString("hh:mm")
        end_time = self.ui.timeEdit_end_time.time().toString("hh:mm")
        self.symptom_list.append(
            f'診療及衛教時間: 從{start_time}至{end_time}, 共{self.ui.spinBox_time.value()}分鐘')

        description_list = []
        if self.ui.checkBox_tv.isChecked():
            description_list.append(self.ui.checkBox_tv.text())
        if self.ui.checkBox_talk.isChecked():
            description_list.append(self.ui.checkBox_talk.text())
        if self.ui.checkBox_paper.isChecked():
            description_list.append(self.ui.checkBox_paper.text())
        if self.ui.checkBox_prescription.isChecked():
            description_list.append(self.ui.checkBox_prescription.text())

        if len(description_list) > 0:
            self.symptom_list.append(f'衛教方式: 透過{", ".join(description_list)}')

        education_list = []
        for check_box in self.check_box_list:
            if check_box.isChecked():
                education_list.append(check_box.text())

        if len(education_list) > 0:
            self.symptom_list.append(f'衛教內容: {", ".join(education_list)}')

        evaluate = self.ui.textEdit_evaluate.toPlainText()
        if evaluate != '':
            self.symptom_list.append(f'評估內容: {evaluate}')

        if len(self.symptom_list) <= 0:
            symptom = None
        else:
            symptom = '\n'.join(self.symptom_list)

        if not self.select_integrate_care:
            return None
        else:
            return symptom

    def _set_check_box_color(self):
        check_box = self.sender()

        if check_box.isChecked():
            check_box.setStyleSheet('color: red; font-weight: bold')
        else:
            check_box.setStyleSheet(None)

        self._set_integrate_care_ok()

    def _check_box_clicked(self):
        check_box = self.sender()
        self._set_integrate_care_ok()

        if not check_box.isChecked():
            check_box.setStyleSheet(None)
            return

        check_box.setStyleSheet('color: red; font-weight: bold')
        url_list = {
            'checkBox_1': 'http://www.twtm.tw/educate.php?cat=88&id=3253',
            'checkBox_2': 'http://www.twtm.tw/educate.php?cat=88&id=3118',
            'checkBox_3': 'http://www.twtm.tw/educate.php?cat=88&id=3353',
            'checkBox_4': 'http://www.twtm.tw/educate.php?cat=88&id=3116',
            'checkBox_5': 'http://www.twtm.tw/educate.php?cat=88&id=3113',
            'checkBox_6': 'http://www.twtm.tw/educate.php?cat=88&id=3115',
            'checkBox_7': 'http://www.twtm.tw/educate.php?cat=88&id=3212',
            'checkBox_8': 'http://www.twtm.tw/educate.php?cat=88&id=3196',
            'checkBox_9': 'http://www.twtm.tw/educate.php?cat=88&id=3180',
            'checkBox_10': 'http://www.twtm.tw/educate.php?cat=88&id=3201',
            'checkBox_11': 'http://www.twtm.tw/educate.php?cat=88&id=3300',
            'checkBox_12': 'http://www.twtm.tw/educate.php?cat=88&id=3238',
            'checkBox_13': 'http://www.twtm.tw/educate.php?cat=88&id=3336',
            'checkBox_14': 'http://www.twtm.tw/educate.php?cat=88&id=3332',
            'checkBox_15': 'http://www.twtm.tw/educate.php?cat=88&id=3313',
            'checkBox_16': 'http://www.twtm.tw/educate.php?cat=88&id=3265',
            'checkBox_17': 'http://www.twtm.tw/educate.php?cat=88&id=3264',
            'checkBox_18': 'http://www.twtm.tw/educate.php?cat=88&id=3254',
            'checkBox_19': 'http://www.twtm.tw/educate.php?cat=88&id=3255',
            'checkBox_20': 'http://www.twtm.tw/educate.php?cat=88&id=3237',
            'checkBox_21': 'http://www.twtm.tw/educate.php?cat=88&id=3236',
            'checkBox_22': 'http://www.twtm.tw/educate.php?cat=88&id=3235',
            'checkBox_23': 'http://www.twtm.tw/educate.php?cat=88&id=3234',
            'checkBox_24': 'http://www.twtm.tw/educate.php?cat=88&id=3233',
            'checkBox_25': 'http://www.twtm.tw/educate.php?cat=88&id=3230',
            'checkBox_26': 'http://www.twtm.tw/educate.php?cat=88&id=3229',
            'checkBox_27': 'http://www.twtm.tw/educate.php?cat=88&id=3228',
        }

        if self.ui.checkBox_open_url.isChecked():
            try:
                url = url_list[check_box.objectName()]
            except Exception:
                url = None

            if url is not None:
                web_utils.open_address(url)


    def _open_symptom_dialog(self):
        dialog = dialog_utils.get_dialog_inquiry(
            self, self.database, self.system_settings, '主訴', self.ui.textEdit_evaluate)
        dialog.exec_()
        dialog.deleteLater()

    def insert_text(self, text_edit, text, input_code, insert_comma=True):
        system_utils.insert_text(text_edit, text, input_code, insert_comma)
