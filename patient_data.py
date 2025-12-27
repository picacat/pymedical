
# -*- coding: utf-8 -*-

import os

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (date_utils, dialog_utils, nhi_utils, patient_utils,
                  personnel_utils, string_utils, system_utils, ui_utils,
                  validator_utils)


# 病患基本資料 2018.01.31
class PatientData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PatientData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.call_from = args[3]
        self.ic_card = args[4]
        self.patient = None
        self.ui = None
        self.name_warning = False
        self.quit_save = False

        self.image_file_path = self.system_settings.field('影像檔路徑')
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.auto_chart_no = self.system_settings.field('自動產生病歷號')

        self._set_ui()
        self._set_validator()
        self._set_signal()

        if self.ic_card:
            self._set_patient_by_ic_card()
        elif self.patient_key is not None:
            self._read_patient()

        # self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_DATA, self)

        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_combobox()
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(
            self.database.get_last_auto_increment_key('patient'))
        )
        self.ui.lineEdit_init_date.setText(date_utils.now_to_str())
        if personnel_utils.get_permission(self.database, '病患資料', '遮蔽電話地址', self.user_name) == 'Y':
            self.ui.lineEdit_telephone.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_cellphone.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_address.setEchoMode(QtWidgets.QLineEdit.Password)

            self.ui.lineEdit_emergency_contact.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_emergency_contact_phone.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.lineEdit_emergency_relevant.setEchoMode(QtWidgets.QLineEdit.Password)

        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QSpinBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QDateTimeEdit)
        self._get_check_box_list(self.ui.groupBox_trace)

    def _set_validator(self):
        self.ui.lineEdit_birthday.setValidator(validator_utils.set_validator('日期格式'))
        # self.ui.lineEdit_id.setValidator(validator_utils.set_validator('身分證格式'))
        self.ui.lineEdit_nursing_home_in_date.setValidator(validator_utils.set_validator('日期格式'))

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_address.clicked.connect(self._open_address_dict)
        self.ui.lineEdit_birthday.editingFinished.connect(self._validate_birthday)
        self.ui.lineEdit_name.editingFinished.connect(self._validate_name)
        self.ui.lineEdit_id.editingFinished.connect(self._check_id)
        self.ui.lineEdit_id.textEdited.connect(self._id_edited)
        self.ui.lineEdit_telephone.editingFinished.connect(self._phone_editing_finished)
        self.ui.lineEdit_cellphone.editingFinished.connect(self._phone_editing_finished)
        self.ui.comboBox_nursing_home.currentIndexChanged.connect(self._set_nursing_home_id)
        self.ui.lineEdit_id.textChanged.connect(self._set_auto_chart_no)

        self.ui.toolButton_history.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.toolButton_remark.clicked.connect(self._tool_button_dictionary_clicked)
        self.ui.checkBox_vegetarian.clicked.connect(self._set_vegetarian_color)

    def _check_id(self):
        if self.ui.comboBox_nationality.currentText() == '外國':
            return
        
        self._set_gender()
        self._set_nationality()

    def _set_auto_chart_no(self):
        if self.auto_chart_no in [None, '無']:
            return

        if self.ui.lineEdit_chart_no.text() != '':
            return

        patient_id = self.ui.lineEdit_id.text()
        if self.auto_chart_no == '身份證後四碼' and patient_id == '':
            return

        patient_id = patient_id[-4:]
        self.ui.lineEdit_chart_no.setText(patient_id)

    def _id_edited(self, arg):
        self.ui.lineEdit_id.setText(arg.upper())

    def _set_nursing_home_id(self):
        nursing_home = self.ui.comboBox_nursing_home.currentText()
        if nursing_home == '':
            self.ui.lineEdit_nursing_home_id.setText(None)
            return

        sql = f'''
            SELECT NursingHomeID FROM patient
            WHERE
                NursingHome = "{nursing_home}" AND
                NursingHomeID IS NOT NULL AND LENGTH(NursingHomeID) > 0
            LIMIT 1
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_nursing_home_id.setText(string_utils.xstr(row['NursingHomeID']))

    def _set_combobox(self):
        ui_utils.set_combo_box(self.ui.comboBox_gender, nhi_utils.GENDER, None)
        ui_utils.set_combo_box(self.ui.comboBox_blood_type, nhi_utils.BLOOD_TYPE, None)
        ui_utils.set_combo_box(self.ui.comboBox_nationality, nhi_utils.NATIONALITY, None)
        ui_utils.set_combo_box(self.ui.comboBox_ins_type, nhi_utils.INSURED_TYPE)
        ui_utils.set_combo_box(self.ui.comboBox_marriage, nhi_utils.MARRIAGE, None)
        ui_utils.set_combo_box(self.ui.comboBox_education, nhi_utils.EDUCATION, None)
        ui_utils.set_combo_box(self.ui.comboBox_occupation, nhi_utils.OCCUPATION, None)
        ui_utils.set_combo_box(self.ui.comboBox_discount, '掛號優待', self.database)

        sql = '''
            SELECT NursingHome FROM patient
            WHERE
                NursingHome IS NOT NULL AND LENGTH(NursingHome) > 0
            GROUP BY NursingHome
        '''
        rows = self.database.select_record(sql)
        nursing_home_list = []
        for row in rows:
            nursing_home_list.append(row['NursingHome'])

        ui_utils.set_combo_box(self.ui.comboBox_nursing_home, nursing_home_list, None)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '病患資料', '病患修正', self.user_name) == 'Y':
            return

        self.ui.toolButton_address.setEnabled(False)

        self.ui.action_save.setEnabled(False)
        self.ui.lineEdit_chart_no.setReadOnly(True)
        self.ui.lineEdit_card_no.setReadOnly(True)
        self.ui.lineEdit_name.setReadOnly(True)
        self.ui.lineEdit_birthday.setReadOnly(True)
        self.ui.lineEdit_id.setReadOnly(True)
        self.ui.lineEdit_init_date.setReadOnly(True)

        self.ui.comboBox_gender.setEnabled(False)
        self.ui.comboBox_nationality.setEnabled(False)
        self.ui.comboBox_ins_type.setEnabled(False)

        self.ui.lineEdit_telephone.setReadOnly(True)
        self.ui.lineEdit_cellphone.setReadOnly(True)
        self.ui.lineEdit_email.setReadOnly(True)
        self.ui.lineEdit_address.setReadOnly(True)

        self.ui.lineEdit_emergency_contact.setReadOnly(True)
        self.ui.lineEdit_emergency_contact_phone.setReadOnly(True)
        self.ui.lineEdit_emergency_relevant.setReadOnly(True)

        self.ui.comboBox_marriage.setEnabled(False)
        self.ui.comboBox_education.setEnabled(False)
        self.ui.comboBox_occupation.setEnabled(False)
        self.ui.comboBox_discount.setEnabled(False)

        self.ui.lineEdit_family.setReadOnly(True)
        self.ui.lineEdit_family_telephone.setReadOnly(True)

        self.ui.textEdit_description.setReadOnly(True)
        self.ui.textEdit_allergy.setReadOnly(True)
        self.ui.textEdit_history.setReadOnly(True)
        self.ui.textEdit_remark.setReadOnly(True)

    def _validate_birthday(self):
        if self.ic_card:
            return

        west_date = date_utils.date_to_west_date(self.ui.lineEdit_birthday.text())
        self.ui.lineEdit_birthday.setText(west_date)

    def _validate_name(self):
        if self.ic_card:
            return

        if self.patient_key is not None:  # 此人已存在
            return

        name = self.ui.lineEdit_name.text()
        if name == '':
            return

        sql = f'''
            SELECT * FROM patient
            WHERE
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        if self.name_warning:
            return

        self.name_warning = True

        row = rows[0]
        patient_key = row['PatientKey']
        name = string_utils.xstr(row['Name'])
        birthday = row['Birthday']
        patient_id = row['ID']

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('相同姓名病患已存在')
        msg_box.setText(f'''
            <font size='4' color='red'>
            <b>相同姓名的病患已存在！以下是相同病患的資料:<br>
            </font>
            <font size='4' color='blue'>
               病歷號碼: {patient_key}<br>
               病患姓名: {name}<br>
               出生日期: {birthday}<br>
               身分證號: {patient_id}
            </b>
            </font>
        ''')
        msg_box.setInformativeText("如果確定不同人，請繼續編輯病患資料.")
        msg_box.addButton(QPushButton("不同病患, 繼續編輯"), QMessageBox.NoRole)  # 0
        msg_box.addButton(QPushButton("此人為相同病患, 確定離開編輯"), QMessageBox.AcceptRole)  # 1
        quit_patient = msg_box.exec_()
        if quit_patient:
            self.quit_save = True
            self.parent.close_patient()
        else:
            self.ui.lineEdit_birthday.setFocus()

    def _check_patient_id(self):
        if self.ic_card:
            return True

        patient_id = self.ui.lineEdit_id.text()
        if patient_id == '':
            return True

        if not validator_utils.verify_id(self.ui.lineEdit_id.text()):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('身分證檢查錯誤')
            msg_box.setText("<font size='4' color='red'><b>身分證可能有誤，請確認身分證號碼是否輸入正確!</b></font>")
            msg_box.setInformativeText("如果確定輸入正確，可以忽略此項警告.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消存檔, 繼續編輯"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                return False

        return True

    def _set_gender(self):
        patient_id = self.ui.lineEdit_id.text()
        if patient_id == '':
            return

        gender = patient_utils.get_gender(patient_id[1])
        if gender is not None:
            self.ui.comboBox_gender.setCurrentText(gender)

    def _set_nationality(self):
        patient_id = self.ui.lineEdit_id.text()
        if patient_id == '':
            return

        self.ui.comboBox_nationality.setCurrentText(patient_utils.get_nationality(patient_id[1]))

    def _read_patient(self):
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {self.patient_key}
        '''
        self.patient = self.database.select_record(sql)[0]
        self._set_patient()
        self._set_photo()
        self._set_trace()

    def _set_patient_by_ic_card(self):
        self.ui.lineEdit_card_no.setText(self.ic_card.basic_data['card_no'])
        self.ui.lineEdit_name.setText(self.ic_card.basic_data['name'])
        self.ui.lineEdit_id.setText(self.ic_card.basic_data['patient_id'])
        self.ui.lineEdit_birthday.setText(self.ic_card.basic_data['birthday'])
        self.ui.comboBox_ins_type.setCurrentText(self.ic_card.basic_data['insured_mark'])
        self.ui.comboBox_gender.setCurrentText(self.ic_card.basic_data['gender'])
        self._set_nationality()

    def _set_patient(self):
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(self.patient['PatientKey']))
        self.ui.lineEdit_chart_no.setText(string_utils.xstr(self.patient['ChartNo']))
        self.ui.lineEdit_card_no.setText(string_utils.xstr(self.patient['CardNo']))
        self.ui.lineEdit_name.setText(string_utils.xstr(self.patient['Name']))
        self.ui.lineEdit_id.setText(string_utils.xstr(self.patient['ID']))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(self.patient['Birthday']))
        self.ui.lineEdit_init_date.setText(string_utils.xstr(self.patient['InitDate']))
        self.ui.lineEdit_telephone.setText(string_utils.xstr(self.patient['Telephone']))
        self.ui.lineEdit_cellphone.setText(string_utils.xstr(self.patient['Cellphone']))
        self.ui.lineEdit_email.setText(string_utils.xstr(self.patient['Email']))
        self.ui.lineEdit_address.setText(string_utils.xstr(self.patient['Address']))

        self.ui.lineEdit_emergency_contact.setText(string_utils.xstr(self.patient['EmergencyContact']))
        self.ui.lineEdit_emergency_contact_phone.setText(string_utils.xstr(self.patient['EmergencyContactPhone']))
        self.ui.lineEdit_emergency_relevant.setText(string_utils.xstr(self.patient['EmergencyRelevant']))

        self.ui.lineEdit_family.setText(string_utils.xstr(self.patient['FamilyPatientKey']))
        self.ui.lineEdit_family_telephone.setText(string_utils.xstr(self.patient['Reference']))
        self.ui.comboBox_gender.setCurrentText(self.patient['Gender'])
        self.ui.comboBox_blood_type.setCurrentText(self.patient['BloodType'])
        self.ui.comboBox_ins_type.setCurrentText(self.patient['InsType'])
        self.ui.comboBox_nationality.setCurrentText(self.patient['Nationality'])
        self.ui.comboBox_marriage.setCurrentText(self.patient['Marriage'])
        self.ui.comboBox_education.setCurrentText(self.patient['Education'])
        self.ui.comboBox_occupation.setCurrentText(self.patient['Occupation'])
        self.ui.comboBox_discount.setCurrentText(self.patient['DiscountType'])

        self.ui.comboBox_nursing_home.setCurrentText(self.patient['NursingHome'])
        self.ui.lineEdit_nursing_home_id.setText(self.patient['NursingHomeID'])
        self.ui.lineEdit_nursing_home_in_date.setText(self.patient['NursingHomeInDate'])
        self._set_patient_text_fields()
        if self.patient_key is not None:
            vegetarian = patient_utils.get_patient_extension_settings(
                self.database, self.patient_key, '吃素')
            if vegetarian == 'Y':
                self.ui.checkBox_vegetarian.setChecked(True)

        self._set_vegetarian_color()

    def _set_vegetarian_color(self):
        check_box = self.ui.checkBox_vegetarian
        if check_box.isChecked():
            check_box.setStyleSheet('color:red; font-weight:bold')
        else:
            check_box.setStyleSheet(None)

    def _set_patient_text_fields(self):
        try:
            self.ui.textEdit_allergy.setText(string_utils.get_str(self.patient['Allergy'], 'utf8'))
        except TypeError:
            pass

        try:
            self.ui.textEdit_history.setText(string_utils.get_str(self.patient['History'], 'utf8'))
        except TypeError:
            pass

        try:
            self.ui.textEdit_remark.setText(string_utils.get_str(self.patient['Remark'], 'utf8'))
        except TypeError:
            pass

        try:
            self.ui.textEdit_description.setText(string_utils.get_str(self.patient['Description'], 'utf8'))
        except TypeError:
            pass

    def _set_photo(self):
        self.ui.label_photo.setText('病患照片')
        filename = personnel_utils.get_personal_photo_filename(
            self.image_file_path, self.ui.lineEdit_patient_key.text()
        )
        if filename is None:
            return

        self.ui.label_photo.setText(f'<img src="{filename}" width="384" height="216" align="middle">')

    def remove_photo(self):
        filename = personnel_utils.get_personal_photo_filename(
            self.image_file_path, self.ui.lineEdit_patient_key.text()
        )
        if filename is None:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除個人照片')
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定刪除此人的照片?</b>
            </font><br>
           <img src="{filename}" width="320" height="180" align=middle>

        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        os.remove(filename)
        self.ui.label_photo.setText('病患照片')

    def _check_patient_ok(self):
        if self.ui.lineEdit_birthday.text() == '':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '生日空白',
                '''
                    <font color="red">
                        <h3>病患資料未輸入生日, 請輸入正確的生日後再存檔</h3>
                    </font>
                ''',
                '生日為必要欄位',
            )
            return False

        return True

    def save_patient(self):
        self.ui.lineEdit_patient_key.setFocus(True)

        if self.system_settings.field('行動電話必填') == 'Y' and self.ui.lineEdit_cellphone.text().strip() == '':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '行動電話未輸入',
                '<font color="red"><h3>行動電話為必填欄位, 請輸入行動電話!</h3></font>',
                '若無行動電話資料，請填「無」.'
            )
            return None

        if self.quit_save:
            return None

        if not self._check_patient_ok():
            return None

        if not self._check_patient_id():
            return None

        name = self.ui.lineEdit_name.text()
        name = string_utils.remove_illegal_characters(name)

        address = self.ui.lineEdit_address.text()
        address = string_utils.remove_illegal_characters(address)

        fields = [
            'ChartNo', 'CardNo', 'Name', 'ID', 'Birthday', 'InitDate', 'Telephone', 'Cellphone', 'Email',
            'Address', 'EmergencyContact', 'EmergencyContactPhone', 'EmergencyRelevant',
            'FamilyPatientKey', 'Reference', 'Gender', 'BloodType', 'InsType', 'Nationality', 'Marriage',
            'Education', 'Occupation', 'DiscountType', 'Allergy', 'History', 'Remark', 'Description',
            'NursingHome', 'NursingHomeID', 'NursingHomeInDate',
        ]
        data = [
            self.ui.lineEdit_chart_no.text(),
            self.ui.lineEdit_card_no.text(),
            name,
            self.ui.lineEdit_id.text(),
            self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_init_date.text(),
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_cellphone.text(),
            self.ui.lineEdit_email.text(),
            address,
            self.ui.lineEdit_emergency_contact.text(),
            self.ui.lineEdit_emergency_contact_phone.text(),
            self.ui.lineEdit_emergency_relevant.text(),
            self.ui.lineEdit_family.text(),
            self.ui.lineEdit_family_telephone.text(),
            self.ui.comboBox_gender.currentText(),
            self.ui.comboBox_blood_type.currentText(),
            self.ui.comboBox_ins_type.currentText(),
            self.ui.comboBox_nationality.currentText(),
            self.ui.comboBox_marriage.currentText(),
            self.ui.comboBox_education.currentText(),
            self.ui.comboBox_occupation.currentText(),
            self.ui.comboBox_discount.currentText(),
            self.ui.textEdit_allergy.toPlainText(),
            self.ui.textEdit_history.toPlainText(),
            self.ui.textEdit_remark.toPlainText(),
            self.ui.textEdit_description.toPlainText(),
            self.ui.comboBox_nursing_home.currentText(),
            self.ui.lineEdit_nursing_home_id.text(),
            self.ui.lineEdit_nursing_home_in_date.text(),
        ]
        if self.patient is None:
            last_row_id = self.database.insert_record('patient', fields, data)
            patient_key = last_row_id
            self.parent.parent.set_new_patient(last_row_id)
        else:
            self.database.update_record('patient', fields, 'PatientKey', self.patient_key, data)
            patient_key = self.patient_key
            self._rewrite_wait(patient_key, name)

        try:
            self._check_vegetarian(patient_key)
        except Exception:
            pass

        try:
            self._save_trace(patient_key)
        except Exception:
            pass

        return patient_key

    def _check_vegetarian(self, patient_key):
        vegetarian = patient_utils.get_patient_extension_settings(
            self.database, patient_key, '吃素')
        if self.ui.checkBox_vegetarian.isChecked() and string_utils.xstr(vegetarian) != 'Y':
            patient_utils.set_patient_extension_settings(
                self.database, patient_key, '吃素', 'Y')
        elif not self.ui.checkBox_vegetarian.isChecked() and string_utils.xstr(vegetarian) == 'Y':
            patient_utils.set_patient_extension_settings(
                self.database, patient_key, '吃素', None)

    def _rewrite_wait(self, patient_key, patient_name):
        sql = f'''
            SELECT CaseKey, Name FROM wait
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        if patient_name == string_utils.xstr(row['Name']):
            return

        self.database.exec_sql(
            f'UPDATE wait SET Name = "{patient_name}" WHERE PatientKey = {patient_key}'
        )

        case_key = string_utils.xstr(row['CaseKey'])
        self._rewrite_cases(case_key, patient_name)

    def _rewrite_cases(self, case_key, patient_name):
        if case_key in [None, '']:
            return

        sql = f'''
            SELECT Name FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        if patient_name == string_utils.xstr(row['Name']):
            return

        self.database.exec_sql(
            f'UPDATE cases SET Name = "{patient_name}" WHERE CaseKey = {case_key}'
        )

    def _open_address_dict(self):
        dialog = dialog_utils.get_dialog_address(
            self, self.database, self.system_settings, self.ui.lineEdit_address,
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _phone_editing_finished(self):
        if self.ui.lineEdit_address.text().strip() != '':  # 已經輸入過就不要自動帶入
            return

        sender_name = self.sender().objectName()
        if sender_name == 'lineEdit_telephone':
            line_edit_phone = self.ui.lineEdit_telephone
            field = 'Telephone'
        else:
            line_edit_phone = self.ui.lineEdit_cellphone
            field = 'Cellphone'

        phone_no = line_edit_phone.text().strip()
        if phone_no in ['', '無']:
            return

        sql = f'''
            SELECT Address FROM patient
            WHERE
                {field} = "{phone_no}"
            LIMIT 1
        '''
        try:
            rows = self.database.select_record(sql)
        except Exception:
            return

        if len(rows) > 0:
            self.ui.lineEdit_address.setText(string_utils.xstr(rows[0]['Address']))

    # 拷貝分院病患基本資料
    def copy_remote_patient(self):
        dialog = dialog_utils.get_dialog_select_remote_patient(
            self, self.database, self.system_settings,
        )
        if dialog.exec_():
            remote_patient = dialog.get_remote_patient()
            self.ui.lineEdit_name.setText(remote_patient['Name'])
            self.ui.lineEdit_birthday.setText(remote_patient['Birthday'])
            self.ui.comboBox_gender.setCurrentText(remote_patient['Gender'])
            self.ui.lineEdit_id.setText(remote_patient['ID'])
            self.ui.comboBox_ins_type.setCurrentText(remote_patient['InsType'])
            self.ui.lineEdit_telephone.setText(remote_patient['Telephone'])
            self.ui.lineEdit_cellphone.setText(remote_patient['Cellphone'])
            self.ui.lineEdit_address.setText(remote_patient['Address'])
            self._set_nationality()

        del dialog

    def capture_image(self):
        if self.system_settings.field('影像檔路徑') in ['', None]:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '路徑未設定',
                '<font size="5" color="red"><b>系統設定內的影像資料檔路徑未設定, 無法執行及讀取影像資料功能.</b></font>',
                '請至系統設定->其他->設定影像資料檔路徑.'
            )
            return

        dialog = dialog_utils.get_dialog_capture_image(
            self, self.database, self.system_settings, None, self.ui.lineEdit_patient_key.text(), '病患照片',
        )
        if dialog.camera is not None and dialog.camera.isOpened():
            dialog.exec_()

        dialog.deleteLater()

        self._set_photo()

    def _tool_button_dictionary_clicked(self):
        sender_name = self.sender().objectName()
        tool_button_dict = {
            'toolButton_history': '病史',
            'toolButton_remark': '備註',
        }

        self.open_dictionary(tool_button_dict[sender_name])

    def open_dictionary(self, dialog_type=None):
        text_edit = {
            '病史': self.ui.textEdit_history,
            '備註': self.ui.textEdit_remark,
        }
        dialog = None
        if dialog_type in ['病史', '備註']:
            dialog = dialog_utils.get_dialog_inquiry(
                self, self.database, self.system_settings, dialog_type, text_edit[dialog_type])

        if dialog is None:
            return

        dialog.exec_()
        dialog.deleteLater()

    def insert_text(self, text_edit, text, input_code, insert_comma=True):
        system_utils.insert_text(text_edit, text, input_code, insert_comma)

    def _set_trace(self):
        sql = f'''
            SELECT * FROM patient_extension
            WHERE
                PatientKey = {self.patient_key} AND
                ExtensionType = "從何處得知本診所"
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            trace = string_utils.xstr(row['Content'])
            self._set_check_box_trace(trace)

        sql = f'''
            SELECT * FROM patient_extension
            WHERE
                PatientKey = {self.patient_key} AND
                ExtensionType = "從何處得知本診所備註"
        '''
        rows = self.database.select_record(sql)
        if rows:
            row = rows[0]
            self.ui.lineEdit_trace_remark.setText(string_utils.xstr(row['Content']))

    def _set_check_box_trace(self, trace):
        check_box_list = self._get_check_box_list(self.ui.groupBox_trace)

        for check_box in check_box_list:
            if check_box.text() == trace:
                check_box.setChecked(True)
                check_box.setStyleSheet('color:darkred; font-weight:bold')
                break

    def _save_trace(self, patient_key):
        check_box_list = self._get_check_box_list(self.ui.groupBox_trace)
        sql = f'''
            DELETE FROM patient_extension
            WHERE
                PatientKey = {patient_key} AND
                ExtensionType IN ("從何處得知本診所", "從何處得知本診所備註")
        '''
        self.database.exec_sql(sql)

        for check_box in check_box_list:
            if check_box.isChecked():
                trace = check_box.text()
                sql = f'''
                    INSERT INTO patient_extension (PatientKey, ExtensionType, Content)
                    VALUES ({patient_key}, "從何處得知本診所", "{trace}")
                '''
                self.database.exec_sql(sql)

        trace_remark = self.ui.lineEdit_trace_remark.text().strip()
        if trace_remark != '':
            sql = f'''
                INSERT INTO patient_extension (PatientKey, ExtensionType, Content)
                VALUES ({patient_key}, "從何處得知本診所備註", "{trace_remark}")
            '''
            self.database.exec_sql(sql)

    def _get_check_box_list(self, group_box):
        check_box_list = []
        check_boxes = group_box.findChildren(QtWidgets.QCheckBox)
        for check_box in check_boxes:
            check_box_list.append(check_box)
            check_box.clicked.connect(self._set_check_box_color)

        return check_box_list

    def _set_check_box_color(self):
        sender = self.sender()
        if sender.isChecked():
            sender.setStyleSheet('color:darkred; font-weight:bold')
        else:
            sender.setStyleSheet(None)
