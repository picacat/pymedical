# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    export_utils,
    nhi_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 醫師業績統計 2023-02-28 太初
class StatisticsDoctorAchievement(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.doctor = args[5]
        self.option = args[6]
        self.weekday_list = args[7]
        self.ui = None

        self.diag_with_nurse_fee = charge_utils.get_ins_diag_fee(
            self.database,
            self.system_settings,
            diag_code="A01",
        )
        self.diag_fee = charge_utils.get_ins_diag_fee(
            self.database,
            self.system_settings,
            diag_code="A02",
        )

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_ACHIEVEMENT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_summary = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_summary, self.database
        )
        self.table_widget_doctor_summary.set_column_hidden([0])
        self._set_table_width()

        self.ui.spinBox_ins_diag_rate.setValue(
            number_utils.get_integer(self.system_settings.field("診察費抽成率"))
        )
        self.ui.spinBox_ins_treat_rate.setValue(
            number_utils.get_integer(self.system_settings.field("診療費抽成率"))
        )
        self.ui.spinBox_self_drug_rate.setValue(
            number_utils.get_integer(self.system_settings.field("自費藥品抽成率"))
        )
        self.ui.spinBox_self_treat_rate.setValue(
            number_utils.get_integer(self.system_settings.field("自費針傷抽成率"))
        )

        self.ui.label_ins_diag_rate_type.setText(
            string_utils.xstr(self.system_settings.field("診察費抽成類別"))
        )
        self.ui.label_ins_treat_rate_type.setText(
            string_utils.xstr(self.system_settings.field("診療費抽成類別"))
        )
        self.ui.label_self_drug_rate_type.setText(
            string_utils.xstr(self.system_settings.field("自費藥品抽成類別"))
        )
        self.ui.label_self_treat_rate_type.setText(
            string_utils.xstr(self.system_settings.field("自費針傷抽成類別"))
        )

    def _set_table_width(self):
        width = [
            100,
            130,
            60,
            70,
            100,
            60,
            70,
            70,
            70,
            70,
            70,
            70,
            70,
            70,
            70,
            90,
            70,
            70,
            70,
            70,
            70,
            90,
            100,
        ]
        self.table_widget_doctor_summary.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_doctor_summary.doubleClicked.connect(
            self._open_medical_record
        )
        self.ui.spinBox_ins_diag_rate.valueChanged.connect(self.spin_box_value_changed)
        self.ui.spinBox_ins_treat_rate.valueChanged.connect(self.spin_box_value_changed)
        self.ui.spinBox_self_drug_rate.valueChanged.connect(self.spin_box_value_changed)
        self.ui.spinBox_self_treat_rate.valueChanged.connect(
            self.spin_box_value_changed
        )

    def spin_box_value_changed(self):
        if self.sender().objectName() == "spinBox_ins_diag_rate":
            self.system_settings.post(
                "診察費抽成率", self.ui.spinBox_ins_diag_rate.value()
            )
        elif self.sender().objectName() == "spinBox_ins_treat_rate":
            self.system_settings.post(
                "診療費抽成率", self.ui.spinBox_ins_treat_rate.value()
            )
        elif self.sender().objectName() == "spinBox_self_drug_rate":
            self.system_settings.post(
                "自費藥品抽成率", self.ui.spinBox_self_drug_rate.value()
            )
        elif self.sender().objectName() == "spinBox_self_treat_rate":
            self.system_settings.post(
                "自費針傷抽成率", self.ui.spinBox_self_treat_rate.value()
            )

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_summary.setRowCount(0)
        self._read_data()
        self._calculate_total()

    def _read_data(self):
        period_condition = ""

        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'
        else:
            doctor_condition = (
                " AND cases.Doctor IS NOT NULL AND LENGTH(cases.Doctor) > 0 "
            )

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(CaseDate) IN({','.join(self.weekday_list)})"
            )

        period_list = str(nhi_utils.PERIOD)[1:-1]
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {period_condition}
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY DATE(CaseDate), FIELD(Period, {period_list}), Room, Doctor, RegistNo
        '''
        self.table_widget_doctor_summary.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])

        diag_with_nurse_fee = charge_utils.get_ins_diag_fee(
            self.database,
            self.system_settings,
            diag_code="A01",
        )
        diag_fee = number_utils.get_integer(row["DiagFee"])
        if diag_fee == diag_with_nurse_fee:
            diag_fee = self.diag_fee

        diag_fee_rate = self.ui.spinBox_ins_diag_rate.value()
        if self.ui.label_ins_diag_rate_type.text() == "$":
            if diag_fee > 0:
                diag_fee_commission = diag_fee_rate
            else:
                diag_fee_commission = 0
        else:
            diag_fee_commission = number_utils.round_up_ex(
                diag_fee * diag_fee_rate / 100, ".1"
            )

        ins_treat_fee = (
            number_utils.get_integer(row["AcupunctureFee"])
            + number_utils.get_integer(row["MassageFee"])
            + number_utils.get_integer(row["DislocateFee"])
            + number_utils.get_integer(row["ExamFee"])
        )
        ins_treat_fee_rate = self.ui.spinBox_ins_treat_rate.value()
        if self.ui.label_ins_treat_rate_type.text() == "$":
            if ins_treat_fee > 0:
                ins_treat_fee_commission = ins_treat_fee_rate
            else:
                ins_treat_fee_commission = 0
        else:
            ins_treat_fee_commission = number_utils.round_up_ex(
                ins_treat_fee * ins_treat_fee_rate / 100, ".1"
            )

        self_drug_fee = self._get_self_treat_fee(case_key, treat_type="藥品")
        self_drug_fee_rate = self.ui.spinBox_self_drug_rate.value()

        self_treat_fee = self._get_self_treat_fee(case_key)
        self_treat_fee_rate = self.ui.spinBox_self_treat_rate.value()

        beauty_fee = self._get_self_treat_fee(case_key, beauty_type=True)
        beauty_rate = 40
        beauty_commission = number_utils.round_up_ex(
            beauty_fee * beauty_rate / 100, ".1"
        )

        total_fee = number_utils.get_integer(row["TotalFee"])
        if self_treat_fee > 0 and self_drug_fee == 0 and self_treat_fee != total_fee:
            self_treat_fee = total_fee

        if (
            self_drug_fee > 0
            and self_treat_fee == 0
            and beauty_fee == 0
            and self_drug_fee != total_fee
        ):
            self_drug_fee = total_fee

        if self.ui.label_self_drug_rate_type.text() == "$":
            if self_drug_fee > 0:
                self_drug_fee_commission = self_drug_fee_rate
            else:
                self_drug_fee_commission = 0
        else:
            self_drug_fee_commission = number_utils.round_up_ex(
                self_drug_fee * self_drug_fee_rate / 100, ".1"
            )

        if self.ui.label_self_treat_rate_type.text() == "$":
            if self_treat_fee > 0:
                self_treat_fee_commission = self_treat_fee_rate
            else:
                self_treat_fee_commission = 0
        else:
            self_treat_fee_commission = number_utils.round_up_ex(
                self_treat_fee * self_treat_fee_rate / 100, ".1"
            )

        total_commission = (
            diag_fee_commission
            + ins_treat_fee_commission
            + self_drug_fee_commission
            + self_treat_fee_commission
            + beauty_commission
        )

        medical_record_row = [
            case_key,
            row["CaseDate"].date().strftime("%Y-%m-%d"),
            string_utils.xstr(row["RegistNo"]),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["InsType"]),
            diag_fee,
            f"{diag_fee_rate}{self.ui.label_ins_diag_rate_type.text()}",
            number_utils.get_float(diag_fee_commission),
            ins_treat_fee,
            f"{ins_treat_fee_rate}{self.ui.label_ins_treat_rate_type.text()}",
            number_utils.get_float(ins_treat_fee_commission),
            self_drug_fee,
            f"{self_drug_fee_rate}{self.ui.label_self_drug_rate_type.text()}",
            number_utils.get_float(self_drug_fee_commission),
            self_treat_fee,
            f"{self_treat_fee_rate}{self.ui.label_self_treat_rate_type.text()}",
            number_utils.get_float(self_treat_fee_commission),
            number_utils.get_float(beauty_fee),
            f"{beauty_rate}%",
            number_utils.get_float(beauty_commission),
            number_utils.get_float(total_commission),
            string_utils.xstr(row["Doctor"]),
        ]

        for col_no in range(len(medical_record_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record_row[col_no])
            self.ui.tableWidget_doctor_summary.setItem(row_no, col_no, item)

            if col_no in [2, 3] or (col_no >= 6 and col_no <= 21):
                self.ui.tableWidget_doctor_summary.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [5, 19]:
                self.ui.tableWidget_doctor_summary.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

            if (
                row["InsType"] == "自費"
                or number_utils.get_integer(row["TotalFee"]) > 0
            ):
                self.ui.tableWidget_doctor_summary.item(row_no, col_no).setForeground(
                    QtGui.QColor("blue")
                )

            if col_no in [8, 11, 14, 17, 20, 21]:
                font = QtGui.QFont()
                font.setBold(True)
                self.ui.tableWidget_doctor_summary.item(row_no, col_no).setFont(font)

    def _get_self_treat_fee(self, case_key, treat_type="處置", beauty_type=False):
        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                MedicineSet != 11 AND
                Price > 0
            GROUP BY MedicineSet ORDER BY MedicineSet
        """
        rows = self.database.select_record(sql)

        if beauty_type:
            medicine_type_script = 'prescript.MedicineName LIKE "%美顏針%"'
        elif treat_type == "處置":
            medicine_type_script = """
                prescript.MedicineType IN ("穴道", "處置") AND
                prescript.MedicineName NOT LIKE "%美顏針%"
            """
        else:
            medicine_type_script = """
                prescript.MedicineType NOT IN ("穴道", "處置") AND
                prescript.MedicineName NOT LIKE "%美顏針%"
            """

        self_treat_fee = 0
        for row in rows:
            medicine_set = row["MedicineSet"]
            sql = f"""
                SELECT MedicineSet FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = {medicine_set} AND
                    Price > 0 AND
                    {medicine_type_script}
                GROUP BY CaseKey LIMIT 1
            """
            prescript_rows = self.database.select_record(sql)

            if len(prescript_rows) <= 0:
                continue

            total_fee = case_utils.get_total_fee(self.database, case_key, medicine_set)
            self_treat_fee += number_utils.get_integer(total_fee)

        return self_treat_fee

    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            f"{start_date}至{end_date}{self.doctor}門診收入一覽表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_summary,
            [0],
            [2, 3, 6, 8, 9, 11, 12, 14, 15, 17, 18],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>門診收入一覽檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _calculate_total(self):
        total_diag_fee = 0
        total_diag_fee_commission = 0
        total_ins_treat_fee = 0
        total_ins_treat_fee_commission = 0
        total_drug_fee = 0
        total_drug_fee_commission = 0
        total_self_treat_fee = 0
        total_self_treat_fee_commission = 0
        total_beauty_fee = 0
        total_beauty_commission = 0

        total_commission = 0

        row_count = self.ui.tableWidget_doctor_summary.rowCount()
        for row_no in range(row_count):
            item = self.ui.tableWidget_doctor_summary.item(row_no, 6)
            if item is not None:
                total_diag_fee += number_utils.get_integer(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 8)
            if item is not None:
                total_diag_fee_commission += number_utils.get_float(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 9)
            if item is not None:
                total_ins_treat_fee += number_utils.get_integer(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 11)
            if item is not None:
                total_ins_treat_fee_commission += number_utils.get_float(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 12)
            if item is not None:
                total_drug_fee += number_utils.get_integer(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 14)
            if item is not None:
                total_drug_fee_commission += number_utils.get_float(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 15)
            if item is not None:
                total_self_treat_fee += number_utils.get_integer(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 17)
            if item is not None:
                total_self_treat_fee_commission += number_utils.get_float(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 18)
            if item is not None:
                total_beauty_fee += number_utils.get_integer(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 20)
            if item is not None:
                total_beauty_commission += number_utils.get_float(item.text())

            item = self.ui.tableWidget_doctor_summary.item(row_no, 21)
            if item is not None:
                total_commission += number_utils.get_float(item.text())

        total_amount_row = [
            None,
            None,
            "總計",
            None,
            None,
            None,
            total_diag_fee,
            None,
            total_diag_fee_commission,
            total_ins_treat_fee,
            None,
            total_ins_treat_fee_commission,
            total_drug_fee,
            None,
            total_drug_fee_commission,
            total_self_treat_fee,
            None,
            total_self_treat_fee_commission,
            total_beauty_fee,
            None,
            total_beauty_commission,
            total_commission,
        ]
        self.ui.tableWidget_doctor_summary.insertRow(row_count)
        for col_no in range(len(total_amount_row)):
            item = total_amount_row[col_no]
            if item is None:
                continue

            if col_no != 1:
                item = number_utils.get_integer(item)

            self.ui.tableWidget_doctor_summary.setItem(
                row_count, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(item))
            )
            if col_no >= 6:
                self.ui.tableWidget_doctor_summary.item(
                    row_count, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            if col_no in [8, 11, 14, 17, 20, 21]:
                font = QtGui.QFont()
                font.setBold(True)
                self.ui.tableWidget_doctor_summary.item(row_count, col_no).setFont(font)

    def _open_medical_record(self):
        case_key = self.table_widget_doctor_summary.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)
