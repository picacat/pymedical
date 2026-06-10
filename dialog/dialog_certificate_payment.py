# 開立醫療費用證明書 2026.06.10
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    certificate_utils,
    charge_utils,
    class_utils,
    date_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 醫療費用證明
class DialogCertificatePayment(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCertificatePayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.auto_create_list = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()

        if self.auto_create_list is not None:
            self._auto_create_certificate_payment()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CERTIFICATE_PAYMENT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self._set_group_box(False)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

        certificate_Fee = charge_utils.get_charge_settings_fee(
            self.database, "證明書費", "自費", "醫療費用證明書費"
        )
        if certificate_Fee in [None, 0]:
            certificate_Fee = 100

        self.ui.spinBox_certificate_fee.setValue(certificate_Fee)
        self.ui.lineEdit_certificate_fee.setText(string_utils.xstr(certificate_Fee))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.lineEdit_patient_key.returnPressed.connect(self._get_patient)
        self.ui.lineEdit_patient_key.textChanged.connect(self._patient_key_changed)
        self.ui.toolButton_select_patient.clicked.connect(self._select_patient)
        self.ui.toolButton_modify_patient.clicked.connect(self._modify_patient)

        self.ui.dateEdit_start_date.dateChanged.connect(self._read_medical_record)
        self.ui.dateEdit_end_date.dateChanged.connect(self._read_medical_record)
        self.ui.comboBox_ins_type.currentTextChanged.connect(self._read_medical_record)
        self.ui.comboBox_treat_type.currentTextChanged.connect(
            self._read_medical_record
        )
        self.ui.spinBox_certificate_fee.valueChanged.connect(
            self._calculate_certificate_fee
        )
        self.ui.spinBox_certificate_quantity.valueChanged.connect(
            self._calculate_certificate_fee
        )
        self.ui.checkBox_accept.clicked.connect(self._set_accepted)

    def _set_table_width(self):
        width = [100, 10, 130, 60, 100, 90, 90, 90, 90, 90, 90]
        self.table_widget_medical_record.set_table_heading_width(width)

    def _set_group_box(self, enabled):
        self.ui.lineEdit_name.setEnabled(enabled)
        self.ui.lineEdit_id.setEnabled(enabled)
        self.ui.lineEdit_birthday.setEnabled(enabled)
        self.ui.lineEdit_gender.setEnabled(enabled)
        self.ui.lineEdit_telephone.setEnabled(enabled)
        self.ui.lineEdit_address.setEnabled(enabled)

        self.ui.label_name.setEnabled(enabled)
        self.ui.label_id.setEnabled(enabled)
        self.ui.label_birthday.setEnabled(enabled)
        self.ui.label_gender.setEnabled(enabled)
        self.ui.label_telephone.setEnabled(enabled)
        self.ui.label_address.setEnabled(enabled)

        self.ui.groupBox_medical_record.setEnabled(enabled)
        self.ui.groupBox_diagnosis.setEnabled(enabled)

        self.ui.toolButton_modify_patient.setEnabled(enabled)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(
            self.ui.comboBox_ins_type,
            nhi_utils.INS_TYPE + ["自費(含健保內的自費)"],
            "全部",
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_treat_type, ["針傷科", "針灸科", "傷骨科", "內科"], "全部"
        )

    def accepted_button_clicked(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        start_date = self.ui.tableWidget_medical_record.item(0, 2).text()
        end_date = self.ui.tableWidget_medical_record.item(
            self.ui.tableWidget_medical_record.rowCount() - 1, 2
        ).text()

        if certificate_utils.check_certificate_duplicate(
            self.database, "收費證明", patient_key, start_date, end_date
        ):
            msg_box = dialog_utils.get_message_box(
                "重複開立證明",
                QMessageBox.Warning,
                '<font color="red"><h3>在此期間已有開立證明書, 是否繼續重複開立?</h3></font>',
                "請確認開立證明的開始與結束日期, 若需要重複開立，請選擇「確定」按鈕.",
            )
            continue_save = msg_box.exec_()
            if not continue_save:
                return

        self._save_files()

    def _clear_patient_data(self):
        self.ui.lineEdit_name.setText("")
        self.ui.lineEdit_id.setText("")
        self.ui.lineEdit_birthday.setText("")
        self.ui.lineEdit_gender.setText("")
        self.ui.lineEdit_telephone.setText("")
        self.ui.lineEdit_address.setText("")

        self.ui.tableWidget_medical_record.setRowCount(0)

    def _set_patient_data(self, row):
        telephone = string_utils.xstr(row["Telephone"])
        if telephone == "":
            telephone = string_utils.xstr(row["Cellphone"])

        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))
        self.ui.lineEdit_id.setText(string_utils.xstr(row["ID"]))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row["Birthday"]))
        self.ui.lineEdit_gender.setText(string_utils.xstr(row["Gender"]))
        self.ui.lineEdit_telephone.setText(telephone)
        self.ui.lineEdit_address.setText(string_utils.xstr(row["Address"]))

    def _set_date_edit_index(self, date_edit):
        if self.table_widget_medical_record.row_count() <= 0:
            return

        index = date_edit.currentSectionIndex()
        if index <= 1:
            date_edit.setFocus()
            date_edit.setCurrentSectionIndex(index + 1)
        else:
            self.ui.dateEdit_end_date.setFocus()
            self.ui.dateEdit_end_date.setCurrentSectionIndex(0)

    def _read_medical_record(self):
        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")
        patient_key = self.ui.lineEdit_patient_key.text()

        treat_type_dict = {
            "針傷科": nhi_utils.INS_TREAT,
            "針灸科": nhi_utils.ACUPUNCTURE_TREAT,
            "傷骨科": nhi_utils.MASSAGE_TREAT,
        }

        condition = ""
        ins_type = self.ui.comboBox_ins_type.currentText()
        treat_type = self.ui.comboBox_treat_type.currentText()
        # doctor = self.ui.comboBox_doctor.currentText()

        if ins_type == "全部":
            condition = ""
        elif ins_type in ["健保", "自費"]:
            condition = f' AND InsType = "{ins_type}" '
        else:
            condition = " AND TotalFee > 0"

        if treat_type == "內科":
            condition += ' AND TreatType = "內科" '
        elif treat_type != "全部":
            treat_type_list = tuple(treat_type_dict[treat_type])
            condition += f" AND TreatType IN {treat_type_list} "

        if self.system_settings.field("開立費用證明不要列出民俗調理") == "Y":
            condition += ' AND InsType != "自費" AND TreatType != "民俗調理"'

        sql = f'''
            SELECT
                CaseKey, CaseDate, InsType, TreatType, Doctor,
                RegistFee, SDiagShareFee, SDrugShareFee, InsApplyFee, TotalFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key}
                {condition}
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(
            sql, self._set_table_data, set_focus=False
        )

        if (
            self.table_widget_medical_record.row_count() > 0
            and self.ui.checkBox_accept.isChecked()
        ):
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self._set_doctor()
        self.sender().setFocus()

    def _set_accepted(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        if (
            self.table_widget_medical_record.row_count() > 0
            and self.ui.checkBox_accept.isChecked()
        ):
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _set_doctor(self):
        doctor_list = []
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            doctor_item = self.ui.tableWidget_medical_record.item(row_no, 10)
            if doctor_item is None:
                continue

            doctor = doctor_item.text()
            if doctor == "":
                continue

            if doctor not in doctor_list:
                doctor_list.append(doctor)

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)

    def _set_table_data(self, row_no, row):
        medical_record = [
            string_utils.xstr(row["CaseKey"]),
            None,
            string_utils.xstr(row["CaseDate"].date()),
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(number_utils.get_integer(row["RegistFee"])),
            string_utils.xstr(number_utils.get_integer(row["SDiagShareFee"])),
            string_utils.xstr(number_utils.get_integer(row["SDrugShareFee"])),
            string_utils.xstr(number_utils.get_integer(row["InsApplyFee"])),
            string_utils.xstr(number_utils.get_integer(row["TotalFee"])),
            string_utils.xstr(row["Doctor"]),
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [5, 6, 7, 8, 9]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [1]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        check_box = QtWidgets.QCheckBox(self.ui.tableWidget_medical_record)
        check_box.setChecked(True)
        self.ui.tableWidget_medical_record.setCellWidget(row_no, 1, check_box)

    def _save_files(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        start_date = self.ui.tableWidget_medical_record.item(0, 2).text()
        end_date = self.ui.tableWidget_medical_record.item(
            self.ui.tableWidget_medical_record.rowCount() - 1, 2
        ).text()

        # if certificate_utils.check_certificate_duplicate(
        #     self.database, '收費證明', patient_key, start_date, end_date): # 已經dialog 問過了
        #     return

        if (
            self.ui.checkBox_create_medical_record.isChecked()
            or self.ui.checkBox_print_cert_fee_only.isChecked()
        ):
            certificate_fee = self.ui.lineEdit_certificate_fee.text()
        else:
            certificate_fee = None

        name = self.ui.lineEdit_name.text()
        ins_type = self.ui.comboBox_ins_type.currentText()
        if ins_type not in ["健保", "自費", "全部"]:
            ins_type = "自費"

        certificate_key = certificate_utils.insert_certificate(
            self.database,
            certificate_type="收費證明",
            patient_key=patient_key,
            name=name,
            start_date=start_date,
            end_date=end_date,
            ins_type=ins_type,
            doctor=self.ui.comboBox_doctor.currentText(),
            certificate_fee=certificate_fee,
        )
        self._write_certificate_items(certificate_key)

        if self.system_settings.field("開立費用證明不要列出民俗調理") == "Y":
            pass
        else:
            self._merge_cases(certificate_key)

        if self.ui.checkBox_create_medical_record.isChecked():
            unit_price = self.ui.spinBox_certificate_fee.value()
            quantity = self.ui.spinBox_certificate_quantity.value()
            certificate_fee = self.ui.lineEdit_certificate_fee.text()

            case_key = certificate_utils.insert_medical_record(
                self.database, self.system_settings, patient_key, name, certificate_fee
            )
            certificate_utils.insert_prescript(
                self.database, case_key, unit_price, quantity
            )
            certificate_utils.insert_wait(
                self.database, self.system_settings, case_key, patient_key, name
            )
            certificate_utils.insert_certificate_items(
                self.database, certificate_key, case_key
            )

    def _write_certificate_items(self, certificate_key):
        row_count = self.ui.tableWidget_medical_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_medical_record.item(row_no, 0).text()
            certificate_utils.insert_certificate_items(
                self.database, certificate_key, case_key
            )

    def _merge_cases(self, certificate_key):
        sql = f"""
            SELECT *, cases.TreatType FROM certificate_items
                LEFT JOIN cases ON cases.CaseKey = certificate_items.CaseKey
            WHERE
                CertificateKey = {certificate_key} AND
                cases.TreatType = "民俗調理"
        """
        rows = self.database.select_record(sql)
        for row in rows:
            certificate_items_key = row["CertificateItemsKey"]
            if self._is_merge_case(row, certificate_key):
                self.database.exec_sql(f"""
                    DELETE FROM certificate_items
                    WHERE
                        CertificateItemsKey = {certificate_items_key}
                """)

    def _is_merge_case(self, row, certificate_key):
        case_date = row["CaseDate"].date()
        sql = f'''
            SELECT * FROM certificate_items
            WHERE
                CertificateKey = {certificate_key} AND
                InsType = "健保" AND
                Date(CaseDate) = "{case_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return False

        certificate_items_row = rows[0]
        s_massage_fee = number_utils.get_integer(row["SMassageFee"])
        certificate_items_key = certificate_items_row["CertificateItemsKey"]
        cert_massage_fee = (
            number_utils.get_integer(certificate_items_row["SMassageFee"])
            + s_massage_fee
        )
        self_total_fee = (
            number_utils.get_integer(certificate_items_row["SelfTotalFee"])
            + s_massage_fee
        )
        total_fee = (
            number_utils.get_integer(certificate_items_row["TotalFee"]) + s_massage_fee
        )
        receipt_fee = (
            number_utils.get_integer(certificate_items_row["ReceiptFee"])
            + s_massage_fee
        )
        sql = f"""
            UPDATE certificate_items
            SET
                SMassageFee = {cert_massage_fee},
                SelfTotalFee = {self_total_fee},
                TotalFee = {total_fee},
                ReceiptFee = {receipt_fee}
            WHERE
                CertificateItemsKey = {certificate_items_key}
        """
        self.database.exec_sql(sql)

        return True

    def _auto_create_certificate_payment(self):
        try:
            start_date = date_utils.str_to_date(self.auto_create_list[4])
            end_date = date_utils.str_to_date(self.auto_create_list[5])
        except Exception:
            start_date = date_utils.str_to_date(
                date_utils.date_to_west_date(self.auto_create_list[4])
            )
            end_date = date_utils.str_to_date(
                date_utils.date_to_west_date(self.auto_create_list[5])
            )

        self.ui.lineEdit_patient_key.setText(self.auto_create_list[0])
        self.ui.dateEdit_start_date.setDate(start_date)
        self.ui.dateEdit_end_date.setDate(end_date)
        self.ui.comboBox_ins_type.setCurrentText(self.auto_create_list[2])
        self.ui.comboBox_treat_type.setCurrentText(self.auto_create_list[3])
        self.ui.comboBox_doctor.setCurrentText(self.auto_create_list[6])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def _modify_patient(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        fields = ["Telephone", "Address"]
        data = [
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_address.text(),
        ]
        self.database.update_record("patient", fields, "PatientKey", patient_key, data)
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料存檔完成",
            "<h3>病患電話及地址存檔完成.</h3>",
            "只開放修改電話及地址",
        )

    def _select_patient(self):
        patient_key = patient_utils.select_patient(
            self, self.database, self.system_settings, "patient", "PatientKey", ""
        )
        if patient_key in ["", None]:
            return

        self._set_line_edit_patient_data(patient_key)

    def _patient_key_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text()

        if patient_key == "":
            self._clear_patient_data()
            self._set_group_box(False)
            return

        if patient_key.isdigit() and len(patient_key) <= 6:
            self._set_line_edit_patient_data(patient_key)
        else:
            self._clear_patient_data()

    def _get_patient(self):
        keyword = self.ui.lineEdit_patient_key.text()

        patient_key = patient_utils.get_patient_by_keyword(
            self, self.database, self.system_settings, "patient", "PatientKey", keyword
        )
        if patient_key in ["", None]:
            return

        self._set_line_edit_patient_data(patient_key)

    def _set_line_edit_patient_data(self, patient_key):
        self.ui.checkBox_accept.setChecked(False)
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._clear_patient_data()
            return

        row = rows[0]
        self._set_patient_data(row)
        self._set_group_box(True)
        self._read_medical_record()
        if self.table_widget_medical_record.row_count() <= 0:
            self.ui.checkBox_accept.setChecked(True)

        self.ui.lineEdit_patient_key.setFocus()

    def _calculate_certificate_fee(self):
        certificate_fee = (
            self.ui.spinBox_certificate_fee.value()
            * self.ui.spinBox_certificate_quantity.value()
        )
        self.ui.lineEdit_certificate_fee.setText(string_utils.xstr(certificate_fee))
