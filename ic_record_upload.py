# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QPushButton

from libs import (case_utils, class_utils, cshis_utils, date_utils,
                  dialog_utils, nhi_utils, number_utils, personnel_utils,
                  string_utils, system_utils, ui_utils)


# 主視窗
class ICRecordUpload(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(ICRecordUpload, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "period": None,
            "upload_option": 0,
        }
        self.ui = None
        self.upload_type = '1'  # 預設-正常上傳

        self.sql = None

        self._set_ui()
        self._set_signal()
        self._check_upload_button()

        self.clinic_id = self.system_settings.field('院所代號')
        self.cshis_version = self.system_settings.field('讀卡機控制軟體版本')

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_medical_record_list(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_IC_RECORD_UPLOAD, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_ic_record, self.database)
        self.table_widget_medical_record.set_column_hidden([0])
        # database._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_medical_record_list)
        self.ui.action_open_record.triggered.connect(self.open_medical_record)
        self.ui.action_set_remark.triggered.connect(self._remark_all_records)
        self.ui.action_section_remark.triggered.connect(self._section_remark)
        self.ui.action_clear_remark.triggered.connect(self._clear_remark)
        self.ui.action_correct_errors.triggered.connect(self._correct_errors)

        self.ui.action_upload_file.triggered.connect(self.upload_xml_file)
        self.ui.action_create_ic_upload_xml_2.triggered.connect(
            lambda: self._upload_xml_file_2_0('A2', clear_record=False, show_message=True))

        self.ui.action_edit_upload_type.triggered.connect(self._edit_upload_type)
        self.ui.action_set_unupload_mode.triggered.connect(self._set_unupload_mode)
        self.ui.tableWidget_ic_record.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_ic_record.horizontalHeader().sectionClicked.connect(self._header_clicked)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [70, 10, 80, 80, 160, 50, 80, 80, 40, 120, 50, 80, 80, 70, 40, 40, 80, 200, 120, 500]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_ic_record_upload(
            self, self.database, self.system_settings, 'ic_record_upload')
        check_box_list = {
            0: dialog.ui.radioButton_normal,
            1: dialog.ui.radioButton_correct,
            2: dialog.ui.radioButton_correct_updated,
        }

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting['period'])
            check_box_list[self.dialog_setting['upload_option']].setChecked(True)

        result = dialog.exec_()
        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['period'] = dialog.comboBox_period.currentText()

        if dialog.ui.radioButton_correct.isChecked():
            self.upload_type = '2'
            self.dialog_setting['upload_option'] = 1
        elif dialog.ui.radioButton_correct_updated.isChecked():
            self.upload_type = '2'
            self.dialog_setting['upload_option'] = 2
        else:
            self.upload_type = '1'
            self.dialog_setting['upload_option'] = 0

        self.sql = dialog.get_sql()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self.read_data(self.sql, show_warning=True)

    def read_data(self, sql, show_warning=False):
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)
        self._check_upload_button()
        if self.ui.tableWidget_ic_record.rowCount() <= 0 and show_warning:
            system_utils.show_message_box(
                QMessageBox.Information,
                '資料查詢',
                '''
                    <h3>這段期間查無需要上傳的資料!</h3>
                ''',
                '請檢查日期是否設定正確',
            )

    def _check_upload_button(self):
        self._set_upload_button(False)
        if self.ui.tableWidget_ic_record.rowCount() <= 0:
            self._set_edit_tool_buttons(False)
            return

        self._set_edit_tool_buttons(True)
        record_count = self.get_upload_record_count()
        if record_count > 0:
            self._set_upload_button(True)

    def _set_upload_button(self, enabled):
        self.ui.action_upload_file.setEnabled(enabled)

    def _set_edit_tool_buttons(self, enabled):
        self.ui.action_open_record.setEnabled(enabled)
        self.ui.action_set_remark.setEnabled(enabled)
        self.ui.action_section_remark.setEnabled(enabled)
        self.ui.action_clear_remark.setEnabled(enabled)

        self.ui.action_correct_errors.setEnabled(enabled)
        self.ui.action_edit_upload_type.setEnabled(enabled)
        self.ui.action_set_unupload_mode.setEnabled(enabled)

    def _set_table_data(self, row_no, row):
        case_key = row['CaseKey']
        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            pres_days = rows[0]['Days']
        else:
            pres_days = None

        security_row = case_utils.get_treat_data_xml_dict(string_utils.get_str(row['Security'], 'utf-8'))
        if security_row is None:
            return

        try:
            upload_type = case_utils.extract_security_xml(row['Security'], '資料格式')
        except Exception:
            upload_type = None

        try:
            treat_after_check = case_utils.extract_security_xml(row['Security'], '補卡註記')
        except Exception:
            treat_after_check = None

        try:
            upload_time = case_utils.extract_security_xml(row['Security'], '上傳時間')
        except Exception:
            upload_time = None

        try:
            clinic_id = case_utils.extract_security_xml(row['Security'], '院所代號')
        except Exception:
            clinic_id = None

        error_message = self._check_error(row, security_row)

        try:
            identification = case_utils.extract_security_xml(row['Security'], '就醫識別碼')
        except Exception:
            identification = None

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            None,
            cshis_utils.UPLOAD_TYPE_DICT[upload_type],
            cshis_utils.TREAT_AFTER_CHECK_DICT[treat_after_check],
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['CaseInsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.int_to_str(row['Continuance']).strip('0'),
            string_utils.int_to_str(pres_days),
            string_utils.xstr(row['Doctor']),
            error_message,
            upload_time,
            clinic_id,
            identification,
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_ic_record.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [6, 15]:
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [1, 3, 5, 8, 10, 14]:
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if error_message != '':
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setForeground(
                    QtGui.QColor('red')
                )

        if error_message != '' or self.upload_type == '2':  # 補正上傳預設不註記
            set_check = False
        else:
            set_check = True

        self._set_check_box(row_no, set_check)

    def _set_check_box(self, row_no, check):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet('padding-left: 20px')
        check_box.setChecked(check)
        check_box.clicked.connect(self._check_upload_button)
        col_no = 1

        self.ui.tableWidget_ic_record.setCellWidget(
            row_no, col_no, check_box)
        self.ui.tableWidget_ic_record.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _check_error(self, row, security_row):
        if string_utils.xstr(row['DoctorDone']) == 'False':
            return '尚未就診, 請登錄完成後再上傳'

        error_message = []

        case_key = row['CaseKey']
        patient_key = row['PatientKey']
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        try:
            patient_record = self.database.select_record(sql)[0]
        except Exception:
            patient_record = None
            error_message.append('無此病患資料')
            

        sam_clinic_id = string_utils.xstr(security_row['clinic_id'])
        if security_row['upload_type'] == '1':
            if security_row['registered_date'] == '':
                error_message.append('無IC卡掛號時間')
            if security_row['security_signature'] == '':
                error_message.append('無安全簽章')
            if security_row['sam_id'] == '':
                error_message.append('無安全模組代碼')
            if sam_clinic_id == '':
                error_message.append('無院所代碼')
            # if string_utils.xstr(patient_record['CardNo']) == '':
            #     error_message.append('病患資料無卡片號碼')

        if patient_record is not None and string_utils.xstr(patient_record['ID']) == '':
            error_message.append('病患資料無身份證號碼')
        if patient_record is not None and string_utils.xstr(patient_record['Birthday']) == '':
            error_message.append('病患資料無生日')
        if security_row['upload_type'] == '':
            error_message.append('無上傳格式')
        if security_row['treat_after_check'] == '':
            error_message.append('無補卡註記')
        if security_row['identification'] in ['', None]:
            error_message.append('無就醫識別碼')
        if string_utils.xstr(row['Card']) == '':
            error_message.append('無卡序')
        if row['CardNo'] is not None and len(row['CardNo']) >= 1 and len(row['CardNo']) != 12:
            error_message.append('健保卡片號碼有誤')
        if sam_clinic_id != '' and sam_clinic_id != self.clinic_id:
            error_message.append('院所代碼錯誤')

        doctor_id = personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(row['Doctor']), 'ID')
        position_list = personnel_utils.get_person(self.database, '醫師')

        if doctor_id == '':
            error_message.append('無醫師身份證號')
        elif string_utils.xstr(row['Doctor']) not in position_list:
            error_message.append('醫師欄位非醫師')
        if string_utils.xstr(row['DiseaseCode1']) == '':
            error_message.append('無主診斷碼')
        if number_utils.get_integer(row['InsApplyFee']) <= 0:
            error_message.append('無申報費用')

        for i in range(1, 4):
            disease_code = string_utils.xstr(row[f'DiseaseCode{i}'])
            if disease_code == '':
                continue

            if not case_utils.is_disease_code_neat(self.database, disease_code):
                disease_code = case_utils.correct_neat_disease(self.database, case_key, i)
                if disease_code is None:
                    error_message.append(f'病名{i}非最細碼')
                else:
                    if not case_utils.is_disease_code_neat(self.database, disease_code):
                        error_message.append(f'病名{i}非最細碼')

        return ', '.join(error_message)

    def open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        self.parent.open_medical_record(case_key, '病歷查詢')

    def _remark_all_records(self):
        self._header_clicked(col_no=1)

    # 取得上傳筆數
    def get_upload_record_count(self):
        record_count = 0

        for row_no in range(self.ui.tableWidget_ic_record.rowCount()):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is not None and check_box.isChecked():
                record_count += 1

        return record_count

    # 上傳資料
    def upload_xml_file(self):
        self._upload_xml_file_2_0('A1', clear_record=True, show_message=True)        

        # if self.system_settings.field('健保IC卡資料上傳格式') == '2.0':
        #     self._upload_xml_file_2_0('A1', clear_record=True, show_message=True)
        # else:
        #     if self.upload_type == '1':
        #         self._upload_xml_file_2_0('A2', clear_record=False, show_message=False)

        #     self._upload_xml_file_1_0()

    def _upload_xml_file_1_0(self):
        ic_upload_xml = class_utils.get_ic_upload_xml1(
            self.parent, self.database, self.system_settings, self.ui.tableWidget_ic_record, self.upload_type)

        ic_upload_xml.create_xml_file()

        if not ic_upload_xml.is_file_created():
            system_utils.show_message_box(
                QMessageBox.Critical,
                '上傳失敗',
                '''
                    <font color="red">
                        <h3>無法建立上傳XML檔案, 請檢查是否全部註記或資料路徑是否正確!</h3>
                    </font>
                ''',
                '請檢查是否設定正確',
            )
            return

        record_count = self.get_upload_record_count()

        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        if ic_card.upload_data(ic_upload_xml.xml_file_name(), record_count):
            self._set_uploaded_records()

            system_utils.show_message_box(
                QMessageBox.Information,
                '上傳成功',
                f'''
                    <h3>健保IC卡資料上傳成功, 回傳結果如下:</h3>
                    安全模組: {ic_card.xml_feedback_data['sam_id']}<br>
                    院所代號: {ic_card.xml_feedback_data['clinic_id']}<br>
                    上傳時間: {ic_card.xml_feedback_data['upload_time']}<br>
                    接收時間: {ic_card.xml_feedback_data['receive_time']}<br>
                    上傳筆數: {record_count}
                ''',
                '上傳結果請於2小時後再查詢'
            )
            self.read_data(self.sql)

    # 更新健保上傳時間
    def _set_uploaded_records(self):
        upload_time = date_utils.now_to_str()

        for row_no in range(self.ui.tableWidget_ic_record.rowCount()):
            self.ui.tableWidget_ic_record.setCurrentCell(row_no, 0)
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is None or not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_ic_record.item(row_no, 0).text()
            case_utils.update_xml(
                self.database, 'cases', 'Security', 'upload_time',
                upload_time, 'CaseKey', case_key,
            )

    def _correct_errors(self):
        for row_no in range(self.ui.tableWidget_ic_record.rowCount()):
            case_key = self.ui.tableWidget_ic_record.item(row_no, 0).text()
            card_item = self.ui.tableWidget_ic_record.item(row_no, 13)
            case_utils.update_xml(
                self.database, 'cases', 'Security', 'clinic_id',
                self.clinic_id, 'CaseKey', case_key,
            )  # 更新院所代號

            if card_item is None:
                continue

            card = card_item.text()

            if card not in nhi_utils.ABNORMAL_CARD:  # 正常卡序不調整
                continue

            identification_item = self.ui.tableWidget_ic_record.item(row_no, 20)
            if identification_item is None or identification_item.text() == '':
                cshis_utils.set_identification(self, self.database, self.system_settings, case_key)
                
            upload_type = '2'
            treat_after_check = '1'

            case_utils.update_xml(
                self.database, 'cases', 'Security', 'upload_type',
                upload_type, 'CaseKey', case_key,
            )  # 更新健保寫卡資料
            case_utils.update_xml(
                self.database, 'cases', 'Security', 'treat_after_check',
                treat_after_check, 'CaseKey', case_key,
            )  # 更新健保寫卡資料

        self.table_widget_medical_record.set_db_data(self.sql, self._set_table_data)

    def _edit_upload_type(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        items = ('1 正常上傳', '2 異常上傳')
        upload_type, ok = input_dialog.getItem(
            self, '更改上傳格式', '請選擇上傳格式', items, 0, False)
        if not ok or not upload_type:
            return

        upload_type = upload_type.split(' ')[0]
        for row_no in range(self.ui.tableWidget_ic_record.rowCount()):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is None or not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_ic_record.item(row_no, 0).text()

            case_utils.update_xml(
                self.database, 'cases', 'Security', 'upload_type',
                upload_type, 'CaseKey', case_key,
            )  # 更新健保寫卡資料

        self.table_widget_medical_record.set_db_data(self.sql, self._set_table_data)

    def _set_unupload_mode(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('更改未上傳狀態')
        msg_box.setText(
            "<font size='4' color='red'><b>確定將選取的病歷更改為未上傳狀態?</b></font>"
        )
        msg_box.setInformativeText("注意！資料更改後，請執行上傳資料作業")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        apply_change = msg_box.exec_()
        if not apply_change:
            return

        for row_no in range(self.ui.tableWidget_ic_record.rowCount()):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is None or not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_ic_record.item(row_no, 0).text()

            case_utils.update_xml(
                self.database, 'cases', 'Security', 'upload_time', '', 'CaseKey', case_key,
            )  # 更新健保寫卡資料

        self.table_widget_medical_record.set_db_data(self.sql, self._set_table_data)

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_ic_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, col_no)
            if check_box is None:
                continue

            check_box.setChecked(not check_box.isChecked())

        self._check_upload_button()

    def _section_remark(self):
        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')

        row_count = self.ui.tableWidget_ic_record.rowCount()
        start_no, ok = input_dialog.getInt(
            self, '區段註記', '請輸入區段註記起始號', 1, 1, row_count, 1)
        if not ok:
            return

        end_no, ok = input_dialog.getInt(
            self, '區段註記', '請輸入區段註記結束號', row_count, 1, row_count, 1)
        if not ok:
            return

        for row_no in range(row_count):
            if row_no+1 < start_no or row_no+1 > end_no:
                continue

            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is None:
                continue

            check_box.setChecked(True)

    def _clear_remark(self):
        row_count = self.ui.tableWidget_ic_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, 1)
            if check_box is None:
                continue

            check_box.setChecked(False)

    def _upload_by_cshis6(self, upload_type, xml, case_count, prescript_count, show_message):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        api_status = ic_card.get_api_status()
        sam_mode = api_status['sam']['status']
        if sam_mode != 2:  # 未完成sam認證
            ic_card.verify_sam(show_message=False)

        print('--------------------------xml-------------------------------')
        print(xml)
        print('------------------------------------------------------------')
        error_code, json = ic_card.upload_data(upload_type, xml, case_count)
        if error_code != 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                'XML2.0上傳失敗',
                f'''
                    <font color="red">
                        <h3>IC就醫資料2.0上傳失敗!</h3>
                    </font>
                    <h3>上傳結果: {error_code}</h3>
                ''',
                '上傳結果不正確, 請查明原因後重新上傳',
            )
            return False

        if show_message:
            system_utils.show_message_box(
                QMessageBox.Information,
                'XML2.0上傳成功',
                f'''
                    <font color="red">
                        <h2>IC就醫資料2.0上傳完成!</h2>
                    </font>
                    <h3>上傳結果:</h3>
                    上傳日期時間: {json["uploadDateTime"]}<br>
                    接收日期時間: {json["receiveDateTime"]}<br>
                    醫事機構代碼: {json["hospitalId"]}<br>
                    安全模組編號: {json["samId"]}<br>
                ''',
                '若上傳結果不正確, 請查明原因後重新上傳',
            )
            
        return True

    def _upload_by_cshis5(self, upload_type, xml, case_count, prescript_count, show_message):
        cshis_x = class_utils.get_cshisx(self.database, self.system_settings)
        rtn_code, op_code = cshis_x.VNHI_Upload(upload_type, xml, case_count, prescript_count)

        if rtn_code == -1:
            system_utils.show_message_box(
                QMessageBox.Critical,
                'XML2.0上傳失敗',
                f'''
                    <font color="red">
                        <h3>IC就醫資料2.0上傳失敗!</h3>
                    </font>
                    <h3>上傳結果: {op_code}</h3>
                ''',
                '上傳結果不正確, 請查明原因後重新上傳',
            )
            return False

        if show_message:
            system_utils.show_message_box(
                QMessageBox.Information,
                'XML2.0上傳成功',
                f'''
                    <font color="red">
                        <h3>IC就醫資料2.0上傳完成!</h3>
                    </font>
                    <h3>上傳結果: {cshis_x.RTN_CODE_DICT[rtn_code]}</h3>
                ''',
                '若上傳結果不正確, 請查明原因後重新上傳',
            )
            
        return True

    # 健保IC卡資料上傳格式2.0  預設為預檢上傳
    def _upload_xml_file_2_0(self, upload_type, clear_record=True, show_message=True):
        ic_upload_xml = class_utils.get_ic_upload_xml2(
            self.parent, self.database, self.system_settings, self.ui.tableWidget_ic_record, self.upload_type)

        xml = ic_upload_xml.get_xml(encoding='Big5')

        case_count = ic_upload_xml.get_case_count()
        if case_count <= 0:
            return

        prescript_count = ic_upload_xml.get_prescript_count()

        if self.cshis_version == 'cshis6':
            # self._upload_by_cshis6(xml, case_count, show_message)
            upload_ok = self._upload_by_cshis6(upload_type, xml, case_count, prescript_count, show_message)
        else:
            upload_ok = self._upload_by_cshis5(upload_type, xml, case_count, prescript_count, show_message)

        if clear_record and upload_ok:
            self._set_uploaded_records()
            self.read_data(self.sql)
