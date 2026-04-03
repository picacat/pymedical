# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    alleypin_utils,
    date_utils,
    hainachuan_utils,
    nhi_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 主視窗
class DialogReservationModify(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReservationModify, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.reserve_key = args[2]
        self.patient_key = self._get_patient_key()

        self.ui = None
        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RESERVATION_MODIFY, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self._set_combo_box()

    def _get_patient_key(self):
        sql = f"SELECT PatientKey FROM reserve WHERE ReserveKey = {self.reserve_key}"
        rows = self.database.select_record(sql)
        if not rows:
            return None

        row = rows[0]
        return row["PatientKey"]

    def _set_combo_box(self):
        sql = """
            SELECT * FROM person
            WHERE
                Position IN ("醫師", "支援醫師")
        """
        rows = self.database.select_record(sql)
        doctor_list = []
        for row in rows:
            doctor_list.append(row["Name"])

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)
        ui_utils.set_combo_box(self.ui.comboBox_arrival, ["是", "否"])
        ui_utils.set_combo_box(
            self.ui.comboBox_source,
            [
                "現場預約",
                "初診預約",
                "網路預約",
                "網路初診預約",
                "視訊預約",
                "視訊初診預約",
                "特殊預約",
            ],
        )

    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            return

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_reserve_date.dateChanged.connect(
            self._set_available_reservation_dict
        )
        self.ui.comboBox_period.currentIndexChanged.connect(
            self._set_available_reservation_dict
        )
        self.ui.comboBox_doctor.currentIndexChanged.connect(
            self._set_available_reservation_dict
        )
        self.ui.comboBox_time.currentIndexChanged.connect(self._set_reserve_no)
        self.ui.comboBox_reserve_no.currentIndexChanged.connect(
            self._set_reservation_time
        )

    def _get_week_day_name(self):
        current_week_day = datetime.datetime(
            self.ui.dateEdit_reserve_date.date().year(),
            self.ui.dateEdit_reserve_date.date().month(),
            self.ui.dateEdit_reserve_date.date().day(),
        ).weekday()
        week_day_name = date_utils.get_weekday_name(current_week_day)

        return week_day_name

    def accepted_button_clicked(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        reserve_date = self.ui.dateEdit_reserve_date.date().toString("yyyy-MM-dd")
        period = self.ui.comboBox_period.currentText()
        time = self.ui.comboBox_time.currentText() + ":00"
        reserve_no = self.ui.comboBox_reserve_no.currentText()
        doctor = self.ui.comboBox_doctor.currentText()
        room = self.ui.spinBox_room.value()
        source = self.ui.comboBox_source.currentText()
        remark = self.ui.lineEdit_remark.text()

        sql = f'''
            SELECT ReserveKey FROM reserve
            WHERE
                DATE(ReserveDate) = "{reserve_date}" AND
                PatientKey != "{patient_key}" AND
                Period = "{period}" AND
                Doctor = "{doctor}" AND
                Room = {room} AND
                ReserveNo = {reserve_no}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "預約號碼重複",
                '<font size="5" color="red"><b>預約號碼重複, 請重新輸入.</b></font>',
                "請檢視正確的預約號碼.",
            )
            return

        reserve_date = f"{reserve_date} {time}"

        if self.ui.comboBox_arrival.currentText() == "是":
            arrival = "True"
        else:
            arrival = "False"

        fields = [
            "ReserveDate",
            "Period",
            "ReserveNo",
            "Room",
            "Doctor",
            "Arrival",
            "Source",
            "Remark",
        ]

        data = [
            reserve_date,
            period,
            reserve_no,
            room,
            doctor,
            arrival,
            source,
            remark,
        ]

        self.database.update_record(
            "reserve", fields, "ReserveKey", self.reserve_key, data
        )
        if self.system_settings.field("alleypin") == "Y":
            alleypin_utils.change_reservation_alleypin_appointments(
                self.database, self.system_settings, self.reserve_key
            )

        if self.system_settings.field("hainachuan") == "Y":
            hainachuan_utils.change_reservation(
                self.database, self.system_settings, self.reserve_key, patient_key
            )

    def _read_data(self):
        sql = f"""
            SELECT reserve.*, patient.Telephone, patient.Cellphone FROM reserve
                LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
            WHERE
                ReserveKey = {self.reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self._set_reservation_data(row)

    def _set_reservation_data(self, row):
        patient_key = string_utils.xstr(row["PatientKey"])
        source = string_utils.xstr(row["Source"])
        if source[:4] in ["網路初診", "視訊初診"]:
            patient_key = source[:4]

        self.ui.lineEdit_patient_key.setText(patient_key)
        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))
        self.ui.lineEdit_telephone.setText(string_utils.xstr(row["Telephone"]))
        self.ui.lineEdit_cellphone.setText(string_utils.xstr(row["Cellphone"]))
        self.ui.dateEdit_reserve_date.setDate(row["ReserveDate"].date())
        self.ui.spinBox_room.setValue(number_utils.get_integer(row["Room"]))
        self.ui.comboBox_period.setCurrentText(string_utils.xstr(row["Period"]))
        self.ui.comboBox_doctor.setCurrentText(string_utils.xstr(row["Doctor"]))
        self.ui.comboBox_source.setCurrentText(source)
        self.ui.lineEdit_remark.setText(string_utils.xstr(row["Remark"]))

        if string_utils.xstr(row["Arrival"]) == "True":
            arrival = "是"
        else:
            arrival = "否"

        self.ui.comboBox_arrival.setCurrentText(arrival)

        if source[:4] in ["網路預約", "網路初診"]:
            self.ui.comboBox_source.setEnabled(False)
        else:
            self.ui.comboBox_source.setEnabled(True)

        self._set_available_reservation_dict()
        reserve_time = row["ReserveDate"].strftime("%H:%M")
        index = self.ui.comboBox_time.findText(reserve_time)
        if index >= 0:
            self.ui.comboBox_time.setCurrentIndex(index)

    def _is_reservation_exists(self, reservation_date, reserve_no):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self.ui.comboBox_period.currentText()

        sql = f'''
            SELECT ReserveKey FROM reserve
            WHERE
                ReserveDate = "{reservation_date}" AND
                ReserveNo = {reserve_no} AND
                PatientKey != "{self.patient_key}" AND
                Doctor = "{doctor}" AND
                Period = "{period}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True
        else:
            return False

    def _set_available_reservation_dict(self):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self.ui.comboBox_period.currentText()
        weekday_name = self._get_week_day_name()

        sql = f'''
            SELECT * FROM reservation_table
            WHERE
                (Doctor="{doctor}") AND
                (Period = "{period}") AND
                (Weekday = "{weekday_name}")
            GROUP BY Time
            ORDER BY Time
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            sql = f'''
                SELECT * FROM reservation_table
                WHERE
                    (Doctor="{doctor}") AND
                    (Period = "{period}")
                ORDER BY Time
            '''
            rows = self.database.select_record(sql)

        if len(rows) <= 0:
            sql = f'''
                SELECT * FROM reservation_table
                WHERE
                    (Doctor="{doctor}") AND
                    (Period = "{period}") AND
                    (ReserveNo IS NOT NULL) AND
                    (Weekday IS NULL)
                ORDER BY Time
            '''
            rows = self.database.select_record(sql)

        self.time_dict = {}
        self.number_dict = {}
        for row in rows:
            reserve_no = string_utils.xstr(row["ReserveNo"])
            time = string_utils.xstr(row["Time"])
            reservation_date = (
                self.ui.dateEdit_reserve_date.date().toString("yyyy-MM-dd")
                + " "
                + time
                + ":00"
            )
            if self._is_reservation_exists(reservation_date, reserve_no):
                continue

            self.time_dict[time] = reserve_no
            self.number_dict[reserve_no] = time

        self.ui.comboBox_time.blockSignals(True)
        self.ui.comboBox_reserve_no.blockSignals(True)

        sorted_times = sorted(self.time_dict.keys())
        ui_utils.set_combo_box(self.ui.comboBox_time, sorted_times)

        sorted_numbers = sorted(
            self.number_dict.keys(), key=lambda x: int(x) if x.isdigit() else x
        )
        ui_utils.set_combo_box(self.ui.comboBox_reserve_no, sorted_numbers)

        if self.ui.comboBox_time.count() <= 0:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

        self.ui.comboBox_time.blockSignals(False)
        self.ui.comboBox_reserve_no.blockSignals(False)

    def _set_reservation_time(self):
        self.ui.comboBox_time.blockSignals(True)
        reserve_no = self.ui.comboBox_reserve_no.currentText()
        if reserve_no in ["", None]:
            self.ui.comboBox_reserve_no.blockSignals(False)
            return

        try:
            time = self.number_dict[reserve_no]
            self.ui.comboBox_time.setCurrentText(time)
        except Exception:
            pass

        self.ui.comboBox_time.blockSignals(False)

    def _set_reserve_no(self):
        self.ui.comboBox_reserve_no.blockSignals(True)
        time = self.ui.comboBox_time.currentText()
        if time in ["", None]:
            self.ui.comboBox_reserve_no.blockSignals(False)
            return

        reserve_no = self.time_dict[time]
        self.ui.comboBox_reserve_no.setCurrentText(reserve_no)
        self.ui.comboBox_reserve_no.blockSignals(False)
