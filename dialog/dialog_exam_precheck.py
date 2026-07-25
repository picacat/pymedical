
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
import json

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils


# 診前檢查
class DialogExamPrecheck(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExamPrecheck, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.call_from = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()

        self.data_list = [
            [self.ui.lineEdit_height, 'height', '身高'],
            [self.ui.lineEdit_weight, 'weight', '體重'],
            [self.ui.lineEdit_bmi, 'bmi', 'BMI'],
            [self.ui.lineEdit_ideal_weight, 'ideal_weight', '理想體重'],
            [self.ui.lineEdit_body_fat, 'body_fat', '體脂率'],
            [self.ui.lineEdit_visceral, 'visceral', '內臟脂肪'],
            [self.ui.lineEdit_muscle_mass, 'muscle_mass', '肌肉量'],
            [self.ui.lineEdit_muscle_quality, 'muscle_quality', '肌肉質量'],
            [self.ui.lineEdit_body_water, 'body_water', '體水分率'],
            [self.ui.lineEdit_metabolic_age, 'metabolic_age', '體內年齡'],
            [self.ui.lineEdit_bmr, 'bmr', '基礎代謝率'],
            [self.ui.lineEdit_head_circumference, 'head_circumference', '頭圍'],
            [self.ui.lineEdit_upper_chest, 'upper_chest', '上胸圍'],
            [self.ui.lineEdit_lower_chest, 'lower_chest', '下胸圍'],
            [self.ui.lineEdit_hip, 'hip', '臀圍'],
            [self.ui.lineEdit_calf, 'calf', '小腿圍'],
            [self.ui.lineEdit_waist, 'waist', '腰圍'],
            [self.ui.lineEdit_thigh, 'thigh', '大腿圍'],
            [self.ui.lineEdit_bph, 'bph', '收縮壓'],
            [self.ui.lineEdit_bpl, 'bpl', '舒張壓'],
            [self.ui.lineEdit_heartbeat, 'heartbeat', '心率'],
        ]
        self.set_case_extension()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXAM_PRECHECK, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.call_from == '病歷資料':
            self.ui.buttonBox.setVisible(False)
            self.ui.checkBox_copy_to_remark.setVisible(False)
        else:
            self.ui.pushButton_save.setVisible(False)

        self.ui.lineEdit_height.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.pushButton_save.clicked.connect(self._push_button_save_clicked)
        self.ui.lineEdit_height.textChanged.connect(self._calc_bmi)
        self.ui.lineEdit_weight.textChanged.connect(self._calc_bmi)

    def _calc_bmi(self):
        self.ui.lineEdit_ideal_weight.setText(None)
        if self.ui.lineEdit_height.text() == '' or self.ui.lineEdit_weight == '':
            return

        height = number_utils.get_float(self.ui.lineEdit_height.text())
        weight = number_utils.get_float(self.ui.lineEdit_weight.text())
        if height > 10:
            height /= 100

        try:
            bmi = weight / (height * height)
        except ZeroDivisionError:
            self.ui.lineEdit_ideal_weight.setText(None)
            return

        bmi = round(bmi, 1)  # 取小數點1位

        self.ui.lineEdit_bmi.setText(f'{bmi}')

        ideal_weight = round(height * height * 21.5, 1)
        self.ui.lineEdit_ideal_weight.setText(f'{ideal_weight}')

    def set_case_extension(self):
        sql = f'''
            SELECT * FROM case_extension
            WHERE
                CaseKey = {self.case_key} AND
                ExtensionType = "診前檢查"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        exam_precheck_dict = json.loads(string_utils.xstr(row['Content']))

        for item in self.data_list:
            line_edit = item[0]
            field = item[1]
            try:
                line_edit.setText(exam_precheck_dict[field])
            except KeyError:
                line_edit.setText(None)

    def accepted_button_clicked(self):
        self._write_case_extension()

        if self.ui.checkBox_copy_to_remark.isChecked() and self.call_from in ['掛號作業']:
            self._write_case_remark()

    def get_remark(self):
        remark = self._get_remark()

        return remark

    def _push_button_save_clicked(self):
        self._write_case_extension()
        system_utils.show_message_box(
            QMessageBox.Information,
            '存檔完成',
            '<h3>診前檢查資料存檔完成</h3>',
            '存檔成功.'
        )

    def _write_case_extension(self):
        if self.case_key is None:
            return

        line_edit = []
        field = []
        for item in self.data_list:
            line_edit.append(item[0].text())
            field.append(item[1])

        exam_precheck_dict = dict(zip(field, line_edit))
        exam_precheck_json = json.dumps(exam_precheck_dict, indent=4)

        fields = [
            'CaseKey', 'ExtensionType', 'Content',
        ]

        data = [
            self.case_key, '診前檢查', exam_precheck_json,
        ]

        self._delete_existing_exam_precheck()
        self.database.insert_record('case_extension', fields, data)

    def _get_remark(self):
        examination_list = []
        for item in self.data_list:
            value = item[0].text()
            field_name = item[2]
            if value != '':
                examination_list.append(f'{field_name}: {value}')

        examination_str = ', '.join(examination_list)

        return examination_str

    def _write_case_remark(self):
        if self.case_key is None:
            return

        remark = self._get_remark()

        sql = f'''
            UPDATE cases
                SET Remark = "{remark}"
            WHERE
                CaseKey = {self.case_key}
        '''
        self.database.exec_sql(sql)

    def _delete_existing_exam_precheck(self):
        sql = f'''
            DELETE FROM case_extension
            WHERE
                CaseKey = {self.case_key} AND
                ExtensionType = "診前檢查"
        '''
        self.database.exec_sql(sql)
