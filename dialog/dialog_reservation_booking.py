# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime
import re

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QDialogButtonBox, QMessageBox, QPushButton

from libs import (
    alleypin_utils,
    date_utils,
    dialog_utils,
    hainachuan_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    validator_utils,
)


# 新增預約掛號視窗
class DialogReservationBooking(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReservationBooking, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.reservation_date = args[2]
        self.period = args[3]
        self.doctor = args[4]
        self.reserve_no = args[5]
        self.patient_key = args[6]
        self.ui = None

        self._set_ui()
        self._set_validator()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RESERVATION_BOOKING, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setText(
            "存檔列印預約單"
        )
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("存檔")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.ui.lineEdit_reservation_date.setText(self.reservation_date)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)
        self.ui.comboBox_period.setCurrentText(self.period)

        self._set_combobox_doctor()

        self.ui.lineEdit_reserve_no.setText(self.reserve_no)
        ui_utils.set_completer(
            self.database,
            "SELECT Name FROM patient GROUP BY Name ORDER BY Name",
            "Name",
            self.ui.lineEdit_query,
        )
        self._set_reserve_type()
        self._clear_patient_data()
        self._set_patient_read_only(True)

        if self.patient_key is not None:
            self.ui.lineEdit_query.setText(string_utils.xstr(self.patient_key))
            self._query_patient()
            self.ui.label_query.setVisible(False)
            self.ui.lineEdit_query.setVisible(False)
            self.ui.pushButton_query.setVisible(False)
            self.ui.comboBox_source.setEnabled(False)

    def _set_reserve_type(self):
        reserve_type_list = [
            "現場預約",
            "初診預約",
            "視訊預約",
            "視訊初診預約",
            "特殊預約",
        ]
        try:
            reserve_type = self._get_reserve_type()
            if reserve_type == "複診":
                reserve_type_list = ["現場預約", "視訊預約", "特殊預約"]
        except Exception:
            pass

        ui_utils.set_combo_box(self.ui.comboBox_source, reserve_type_list)

    def _set_combobox_doctor(self):
        doctor_list = personnel_utils.get_person(self.database, "醫師")
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)
        self.ui.comboBox_doctor.setCurrentText(self.doctor)

    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            return

    # 設定信號
    def _set_signal(self):
        # self.ui.buttonBox.accepted.connect(self._dialog_button_clicked)
        self.ui.buttonBox.clicked.connect(self._dialog_button_clicked)
        self.ui.pushButton_query.clicked.connect(self._query_patient)
        self.ui.lineEdit_query.returnPressed.connect(self._query_patient)
        self.ui.comboBox_source.currentTextChanged.connect(self._source_changed)
        self.ui.lineEdit_name.textChanged.connect(self.check_validation)
        self.ui.lineEdit_id.textChanged.connect(self.check_validation)
        self.ui.lineEdit_birthday.editingFinished.connect(self._validate_birthday)

    def _cancel_button_clicked(self):
        self.close()

    def _validate_birthday(self):
        west_date = date_utils.date_to_west_date(self.ui.lineEdit_birthday.text())
        self.ui.lineEdit_birthday.setText(west_date)

    def _set_validator(self):
        self.ui.lineEdit_birthday.setValidator(
            validator_utils.set_validator("日期格式")
        )

    def check_validation(self):
        patient_id = self.ui.lineEdit_id.text()
        if patient_id.strip() != "" and self.ui.lineEdit_name.text().strip() != "":
            button_enabled = True
        else:
            button_enabled = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setEnabled(
            button_enabled
        )
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
            button_enabled
        )

    def _clear_patient_data(self):
        self.ui.lineEdit_patient_key.setText(None)
        self.ui.lineEdit_name.setText(None)
        self.ui.lineEdit_birthday.setText(None)
        self.ui.lineEdit_id.setText(None)
        self.ui.lineEdit_telephone.setText(None)
        self.ui.lineEdit_cellphone.setText(None)
        self.ui.lineEdit_address.setText(None)

    def _set_patient_read_only(self, set_read_only):
        self.ui.lineEdit_query.setEnabled(set_read_only)
        self.ui.pushButton_query.setEnabled(set_read_only)

        self.ui.lineEdit_patient_key.setReadOnly(True)
        self.ui.lineEdit_name.setReadOnly(set_read_only)
        self.ui.lineEdit_birthday.setReadOnly(set_read_only)
        self.ui.lineEdit_id.setReadOnly(set_read_only)
        self.ui.lineEdit_telephone.setReadOnly(set_read_only)
        self.ui.lineEdit_cellphone.setReadOnly(set_read_only)
        self.ui.lineEdit_address.setReadOnly(set_read_only)

        if set_read_only:
            self.ui.lineEdit_query.setFocus()
        else:
            self.ui.lineEdit_name.setFocus()

    def _dialog_button_clicked(self, sender):
        if sender == self.ui.buttonBox.button(QDialogButtonBox.Cancel):
            self.close()
            return

        reserve_key = self._save_reserve_record()

        if sender == self.ui.buttonBox.button(QDialogButtonBox.Yes):
            self._print_reservation_form(reserve_key)

        if self.system_settings.field("alleypin") == "Y":
            alleypin_utils.add_reservation_alleypin_appointments(
                self.database, self.system_settings, reserve_key
            )
        if self.system_settings.field("hainachuan") == "Y":
            hainachuan_utils.add_reservation(
                self.database, self.system_settings, reserve_key
            )

    def _print_reservation_form(self, reserve_key):
        printer_utils.print_reservation(
            self, self.database, self.system_settings, reserve_key, "系統設定"
        )

    def _get_last_regist_no(self, start_date, end_date, period):
        sql = f'''
            SELECT RegistNo FROM wait
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Period = "{period}"
            ORDER BY RegistNo DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0
        else:
            return rows[0]["RegistNo"]

    def _get_last_reservation_no(self, start_date, end_date, period):
        sql = f'''
            SELECT ReserveNo FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Period = "{period}"
            ORDER BY ReserveNo DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0
        else:
            return rows[0]["ReserveNo"]

    def _auto_get_reservation_no(self):
        start_date = f"{self.reservation_date[:10]} 00:00:00"
        end_date = f"{self.reservation_date[:10]} 23:59:59"

        period = self.ui.comboBox_period.currentText()
        last_regist_no = self._get_last_regist_no(start_date, end_date, period)
        last_reservation_no = self._get_last_reservation_no(
            start_date, end_date, period
        )
        start_no = number_utils.get_integer(
            self.system_settings.field(f"{period}起始號")
        )

        if last_regist_no > last_reservation_no:
            reservation_no = last_regist_no
        else:
            reservation_no = last_reservation_no

        if reservation_no == 0:
            reservation_no = start_no
        else:
            reservation_no += 1

        return reservation_no

    def _save_reserve_record(self):
        reservation_date = self.ui.lineEdit_reservation_date.text().strip()
        weekday = date_utils.str_to_date(reservation_date).weekday()
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_doctor.currentText()
        room = registration_utils.get_room(
            self.database, period, doctor, weekday=weekday
        )
        reserve_no = self.ui.lineEdit_reserve_no.text()
        if reserve_no == "":
            reserve_no = self._auto_get_reservation_no()

        if registration_utils.is_reservation_full(
            self.database, reservation_date, period, reserve_no, doctor
        ):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "預約已滿",
                '<font size="5" color="red"><b>在剛剛此時段已被網路預約者預約, 請選擇其他時段.</b></font>',
                "很不巧, 有網路的預約者已搶先預約.",
            )
            return

        fields = [
            "PatientKey",
            "Name",
            "ReserveDate",
            "Period",
            "Room",
            "Doctor",
            "ReserveNo",
            "Source",
            "Registrar",
            "CreateTime",
            "Remark",
        ]

        source = self.ui.comboBox_source.currentText()
        if source in ["初診預約", "視訊初診預約"]:
            self._write_temp_patient()

        patient_key = self.ui.lineEdit_patient_key.text()
        name = self.ui.lineEdit_name.text()
        registrar = self.system_settings.field("使用者")
        create_time = date_utils.now_to_str()
        remark = self.ui.comboBox_remark.currentText()

        data = [
            patient_key,
            name,
            reservation_date,
            period,
            room,
            doctor,
            reserve_no,
            source,
            registrar,
            create_time,
            remark,
        ]

        reserve_key = self.database.insert_record("reserve", fields, data)

        return reserve_key

    # 寫入初診病患暫存檔
    def _write_temp_patient(self):
        fields = [
            "Name",
            "ID",
            "Birthday",
            "PhoneNo",
            "Cellphone",
            "Address",
        ]

        data = [
            self.ui.lineEdit_name.text(),
            self.ui.lineEdit_id.text(),
            self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_cellphone.text(),
            self.ui.lineEdit_address.text(),
        ]

        last_row_id = self.database.insert_record("temp_patient", fields, data)
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(last_row_id))

    # 開始查詢病患資料
    def _query_patient(self):
        keyword = string_utils.xstr(self.ui.lineEdit_query.text())
        if keyword == "":
            return

        pattern = re.compile(validator_utils.DATE_REGEXP)
        if pattern.match(keyword):
            keyword = date_utils.date_to_west_date(keyword)
        else:
            keyword = validator_utils.get_exp_date(keyword)

        self._get_patient(keyword)

    def _get_patient(self, keyword, ic_card=None):
        rows = patient_utils.search_patient(
            self.ui, self.database, self.system_settings, keyword
        )
        if rows is None:  # 找不到資料
            dialog = dialog_utils.get_dialog_select_patient(
                self,
                self.database,
                self.system_settings,
                "patient",
                "PatientKey",
                keyword,
            )
            if dialog.table_widget_patient_list.row_count() <= 0:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "查無資料",
                    '<font size="5" color="red"><b>找不到有關的病患資料, 請檢查關鍵字是否有誤.</b></font>',
                    "請確定輸入資料的正確性, 生日請輸入YYYY-MM-DD.",
                )
                self.ui.lineEdit_query.setFocus()
                return

            if dialog.exec_():
                patient_key = dialog.get_primary_key()
                rows = patient_utils.get_patient_row(self.database, patient_key)
                self._set_patient_data(rows)

            del dialog
        elif rows == -1:  # 取消查詢
            self.ui.lineEdit_query.setFocus()
        else:  # 已選取病患
            self._set_patient_data(rows)

        self.ui.lineEdit_query.clear()

    def _set_patient_data(self, rows):
        try:
            row = rows[0]
        except Exception:
            row = rows

        patient_key = row["PatientKey"]

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if (
            self.reservation_date[:10] == today
            and registration_utils.is_today_already_visited(self.database, patient_key)
            and self.system_settings.field("同日預約兩次") != "Y"
        ):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("已就診提醒")
            msg_box.setText("此人今日已經門診過了, 無法再次預約掛號.")
            msg_box.setInformativeText("請確認是否正確.")
            msg_box.addButton(QPushButton("知道了"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        name = string_utils.xstr(row["Name"])  # 病歷號可能會跟網路初診病歷號重複
        telephone = string_utils.xstr(row["Telephone"])
        cellphone = string_utils.xstr(row["Cellphone"])
        address = string_utils.xstr(row["Address"])

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))
        self.ui.lineEdit_name.setText(name)
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row["Birthday"]))
        self.ui.lineEdit_id.setText(string_utils.xstr(row["ID"]))
        self.ui.lineEdit_telephone.setText(telephone)
        self.ui.lineEdit_cellphone.setText(cellphone)
        self.ui.lineEdit_address.setText(address)
        self.ui.comboBox_remark.clear()

        if registration_utils.is_in_permission_list(
            self.database,
            patient_key,
            "黑名單",
            self.ui.lineEdit_reservation_date.text()[:10],
        ):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("黑名單管控中")
            msg_box.setText("此人在預約黑名單中, 無法預約掛號.")
            msg_box.setInformativeText("請確認黑名單的狀態.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()

        if not self._check_reservation_status(patient_key, name):
            if self.patient_key is not None:
                self.ui.buttonBox.button(
                    QtWidgets.QDialogButtonBox.Cancel
                ).animateClick()

        self._add_remark(patient_key)

    def _add_remark(self, patient_key):
        self.ui.comboBox_remark.addItem(None)
        sql = f"""
            SELECT Remark FROM reserve
            WHERE
                PatientKey = {patient_key} AND
                Remark IS NOT NULL AND LENGTH(Remark) > 0
            GROUP BY Remark
            ORDER BY ReserveDate DESC
        """
        rows = self.database.select_record(sql)
        for row in rows:
            self.ui.comboBox_remark.addItem(string_utils.xstr(row["Remark"]))

    def _check_reservation_status(self, patient_key, name):
        if not self._check_reservation_duplicated(patient_key, name):
            return False

        if not self._check_reservation_limit(patient_key, name):
            return False

        if not self._check_reservation_missing_appointment(patient_key, name):
            return False

        # try:
        #     reservation_date = datetime.datetime.strptime(self.ui.lineEdit_reservation_date.text(), "%Y-%m-%d %H:%M")
        # except Exception:
        #     reservation_date = datetime.datetime.strptime(self.ui.lineEdit_reservation_date.text(), "%Y-%m-%d")

        text = self.ui.lineEdit_reservation_date.text().strip()

        reservation_date = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                reservation_date = datetime.datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

        if reservation_date is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "日期格式錯誤",
                f'<b><font size="5" color="red">預約日期格式無法辨識: {text}</font></b>',
                "請確認預約日期欄位的內容.",
            )
            return False

        message = registration_utils.check_prescription_finished(  # 檢查上次健保給藥是否服藥完畢
            self.database,
            self.system_settings,
            None,
            patient_key,
            in_date=reservation_date,
        )
        if message is not None:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "掛號檢查結果提醒",
                f'<b><font size="5" color="red">{message}</font></b>',
                "請注意! 以上的狀況提示並非資料發生錯誤, 若有疑問, 請至 [病歷查詢] 檢查該筆資料的內容.",
            )

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setEnabled(True)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

        return True

    # 檢查重複預約
    def _check_reservation_duplicated(self, patient_key, name):
        is_ok = True
        if name == "休診":
            return is_ok

        start_date = f"{self.reservation_date[:10]} 00:00:00"
        end_date = f"{self.reservation_date[:10]} 23:59:59"

        twice_condition = ""
        if self.system_settings.field("同日預約兩次") == "Y":
            doctor = self.ui.comboBox_doctor.currentText()
            twice_condition = f'AND Doctor = "{doctor}"'

        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key} AND
                Name = "{name}"
                {twice_condition}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            is_ok = False

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("已有預約")
            msg_box.setText("此人該日已有預約, 無法再次預約掛號.")
            msg_box.setInformativeText("無法重複預約掛號.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            self.ui.lineEdit_patient_key.setText(None)
            self.ui.lineEdit_name.setText(None)
            self.ui.lineEdit_birthday.setText(None)
            self.ui.lineEdit_id.setText(None)

        return is_ok

    def _get_reservation_list(self, patient_key, name, doctor=None):
        start_date = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")

        doctor_condition = ""
        if doctor is not None:
            doctor_condition = f'Doctor = "{doctor}" AND'

        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate >= "{start_date}" AND
                Arrival = "False" AND
                PatientKey = {patient_key} AND
                Name = "{name}" AND
                Doctor NOT IN ("三伏貼", "三九貼") AND
                {doctor_condition}
                Source NOT IN ("網路初診預約", "視訊初診預約")
        '''
        rows = self.database.select_record(sql)

        reservation_list = []
        for row in rows:
            reservation_date = string_utils.xstr(row["ReserveDate"].date())
            period = string_utils.xstr(row["Period"])
            doctor = string_utils.xstr(row["Doctor"])
            reservation_no = string_utils.xstr(row["ReserveNo"])
            reservation_list.append(
                f"{reservation_date} {period} 預約醫師: {doctor} 預約診號: {reservation_no}"
            )

        return reservation_list

    # 檢查預約次數限制
    def _check_reservation_limit(self, patient_key, name):
        is_ok = True
        if name == "休診":
            return is_ok

        if registration_utils.is_in_permission_list(
            self.database,
            patient_key,
            "白名單",
            self.ui.lineEdit_reservation_date.text()[:10],
        ):
            return is_ok

        reservation_limit = number_utils.get_integer(
            self.system_settings.field("預約次數限制")
        )

        if self.system_settings.field("預約次數不同醫師分別計算") == "Y":
            reservation_list = self._get_reservation_list(
                patient_key, name, self.doctor
            )
        else:
            reservation_list = self._get_reservation_list(
                patient_key, name
            )  # 2023-09-11 馥林: 所有醫師一起統計

        if self.doctor in ["三伏貼", "三九貼"]:  # 三伏貼不要限制次數  2025-06-13 安聲
            pass
        elif len(reservation_list) >= reservation_limit:
            is_ok = False
            reservation_list = "\n".join(reservation_list)

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("預約次數超過上限")
            msg_box.setText(
                f"<h3>此人預約已超過預約次數{reservation_limit}次的限制, 無法再次預約掛號.</h4>"
            )
            msg_box.setInformativeText(f"預約記錄:\n{reservation_list}")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            self.ui.lineEdit_patient_key.setText(None)
            self.ui.lineEdit_name.setText(None)
            self.ui.lineEdit_birthday.setText(None)
            self.ui.lineEdit_id.setText(None)

        return is_ok

    # 檢查爽約次數
    def _check_reservation_missing_appointment(self, patient_key, name):
        is_ok = True
        if name == "休診":
            return is_ok

        if registration_utils.is_in_permission_list(
            self.database,
            patient_key,
            "白名單",
            self.ui.lineEdit_reservation_date.text()[:10],
        ):
            return is_ok

        duration = number_utils.get_integer(self.system_settings.field("爽約期間"))
        missing_count = number_utils.get_integer(self.system_settings.field("爽約次數"))

        today = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate >= "{today}" AND
                Arrival = "False" AND
                PatientKey = {patient_key} AND
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        reservation_count = len(rows)

        reservation_date = date_utils.str_to_date(self.reservation_date[:10])
        start_date = reservation_date - datetime.timedelta(days=duration)
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate >= "{start_date}" AND
                Arrival = "False" AND
                PatientKey = {patient_key} AND
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        total_absent = len(rows)
        absent = total_absent - reservation_count

        if absent >= missing_count:
            is_ok = False

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("爽約警告")
            msg_box.setText(
                f"此人預約已超過系統設定內, {duration}天內爽約超過{missing_count}次的限制, 無法再次預約掛號."
            )
            msg_box.setInformativeText("爽約超過次數, 無法預約掛號.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            self._clear_patient_data()

        return is_ok

    def _source_changed(self):
        current_text = self.ui.comboBox_source.currentText()
        self._clear_patient_data()
        if current_text in ["初診預約", "視訊初診預約"]:
            set_read_only = False
            last_temp_patient_key = self.database.get_last_auto_increment_key(
                "temp_patient"
            )
            self.ui.lineEdit_patient_key.setText(
                string_utils.xstr(last_temp_patient_key)
            )
            self.ui.label_patient_key.setText("虛擬號碼")
        else:
            set_read_only = True
            self.ui.label_patient_key.setText("病歷號碼")

        self._set_patient_read_only(set_read_only)

    def _get_reserve_type(self):
        reserve_type = None

        weekday_name = self._get_week_day_name()

        sql = f'''
            SELECT * FROM reservation_table
            WHERE
                (Doctor="{self.doctor}") AND
                (Period = "{s限制elf.period}") AND
                (Weekday = "{weekday_name}") AND
                (ReserveNo IS NOT NULL) AND
                (ReserveNo = {self.reserve_no})
            ORDER BY RowNo, ColumnNo
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            sql = f'''
                SELECT * FROM reservation_table
                WHERE
                    (Doctor="{self.doctor}") AND
                    (Period = "{self.period}") AND
                    (ReserveNo IS NOT NULL) AND
                    (ReserveNo = {self.reserve_no}) AND
                    (Weekday IS NULL)
                ORDER BY RowNo, ColumnNo
            '''
            rows = self.database.select_record(sql)

        try:
            if len(rows) > 0:
                reserve_type = string_utils.xstr(rows[0]["ReserveType"])
        except Exception:
            pass

        return reserve_type

    def _get_week_day_name(self, region="zh_TW"):
        date_obj = datetime.datetime.strptime(
            self.reservation_date[:10], "%Y-%m-%d"
        ).date()
        week_day_name = date_utils.get_weekday_name(date_obj.weekday(), region)

        return week_day_name
