# -*- coding: utf-8 -*-

from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


class StatisticsDoctorMedicinePercent(QtWidgets.QMainWindow):
    """醫師處方類別抽成統計 2025.08.04 仁聿."""

    def __init__(self, parent=None, *args):
        super(StatisticsDoctorMedicinePercent, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
        self.option = args[7]
        self.weekday_list = args[8]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._set_medicine_type_rate()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            ui_utils.UI_STATISTICS_DOCTOR_MEDICINE_PERCENT, self
        )
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_doctor, self.database
        )
        self.table_widget_commission = class_utils.get_table_widget(
            self.ui.tableWidget_commission, self.database
        )
        self.table_widget_doctor.set_column_hidden([0, 1])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            100,
            120,
            60,
            90,
            80,
            60,
            200,
            60,
            70,
            60,
            90,
            90,
            60,
            60,
            90,
        ]
        self.table_widget_doctor.set_table_heading_width(width)
        self.table_widget_commission.set_table_heading_width([150, 60, 90, 60, 60])

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_doctor_excel.clicked.connect(
            self._export_to_doctor_excel
        )
        self.ui.tableWidget_doctor.doubleClicked.connect(self.open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_medical_record(self):
        row_no = self.ui.tableWidget_doctor.currentRow()
        case_key_item = self.ui.tableWidget_doctor.item(row_no, 0)
        if case_key_item is None:
            return

        self.parent.parent.open_medical_record(case_key_item.text())

    def _set_medicine_type_rate(self):
        self.medicine_type_dict = {}

        sql = """
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "藥品類別" AND
                DictGroupsLevel2 IS NOT NULL AND
                LENGTH(DictGroupsLevel2) > 0
            ORDER BY DictOrderNo
        """
        rows = self.database.select_record(sql)
        for row in rows:
            item = row["DictGroupsName"]
            self.medicine_type_dict[item] = row["DictGroupsLevel2"]

    def start_calculate(self):
        self.ui.tableWidget_doctor.setRowCount(0)
        self._calculate_data()
        self._calculate_total()
        self._calculate_medicine_name_total()
        self.ui.tableWidget_doctor.setCurrentCell(0, 0)

        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)

    def _calculate_data(self):
        self._reset_data()
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            "門診收入統計中, 請稍後...", "取消", 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)

        self.ui.tableWidget_doctor.setRowCount(row_count)
        for row_no, row in enumerate(rows):
            self.progress_dialog.setValue(row_no)

            case_key = row["CaseKey"]
            prescript_key = row["PrescriptKey"]
            doctor = string_utils.xstr(row["Doctor"])
            medicine_name = string_utils.xstr(row["MedicineName"])

            medicine_set = number_utils.get_integer(row["MedicineSet"])
            dosage = number_utils.get_float(row["Dosage"])
            price = number_utils.get_integer(row["Price"])
            pres_days = case_utils.get_pres_days(
                self.database, case_key, medicine_set=medicine_set
            )
            if pres_days <= 0:
                pres_days = 1

            amount = dosage * price * pres_days

            medicine_type = string_utils.xstr(row["MedicineType"])
            combo_box_medicine_type = QtWidgets.QComboBox(self.ui.tableWidget_doctor)
            combo_box_medicine_type.currentTextChanged.connect(
                partial(self._set_commission, combo_box_medicine_type)
            )
            combo_box_medicine_type.blockSignals(True)
            ui_utils.set_combo_box(
                combo_box_medicine_type, list(self.medicine_type_dict.keys()), None
            )
            if medicine_type in self.medicine_type_dict:
                combo_box_medicine_type.setCurrentText(medicine_type)
                commission_rate = number_utils.get_integer(
                    self.medicine_type_dict[medicine_type]
                )
                commission = round(amount * (commission_rate / 100))
            else:
                medicine_type = self._get_medicine_type(medicine_name)
                if medicine_type is None:
                    commission_rate = None
                    commission = None
                else:
                    combo_box_medicine_type.setCurrentText(medicine_type)
                    commission_rate = number_utils.get_integer(
                        self.medicine_type_dict[medicine_type]
                    )
                    commission = round(amount * (commission_rate / 100))

            combo_box_medicine_type.blockSignals(False)

            self._set_item_data(row_no, 0, case_key)
            self._set_item_data(row_no, 1, prescript_key)
            self._set_item_data(row_no, 2, row["CaseDate"].date().strftime("%Y-%m-%d"))
            self._set_item_data(row_no, 3, row["Period"], align="center")
            self._set_item_data(row_no, 4, row["Name"], align="center")
            self._set_item_data(row_no, 5, row["PatientKey"], align="right")
            self._set_item_data(row_no, 6, f"{medicine_set - 1}", align="center")
            self._set_item_data(row_no, 7, medicine_name)
            self._set_item_data(row_no, 8, dosage, align="right")
            self._set_item_data(row_no, 9, price, align="right")
            self._set_item_data(row_no, 10, pres_days, align="right")
            self._set_item_data(row_no, 11, amount, align="right")
            # self._set_item_data(row_no, 12, medicine_type, align='center')
            self.ui.tableWidget_doctor.setCellWidget(
                row_no, 12, combo_box_medicine_type
            )
            self._set_item_data(row_no, 13, commission_rate, align="right")
            self._set_item_data(row_no, 14, commission, align="right")
            self._set_item_data(row_no, 15, doctor, align="center")

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _get_medicine_type(self, medicine_name):
        medicine_type = None
        sql = f'''
            SELECT MedicineType FROM medicine
            WHERE
                MedicineType IN {tuple(self.medicine_type_dict.keys())} AND
                MedicineName LIKE "{medicine_name}%"
            LIMIT 1
        
        '''
        rows = self.database.select_record(sql)
        if rows:
            row = rows[0]
            medicine_type = string_utils.xstr(row["MedicineType"])

        return medicine_type

    def _set_commission(self, combo_box_medicine_type, medicine_type):
        row_no = self.ui.tableWidget_doctor.currentRow()

        commission_rate = number_utils.get_integer(
            self.medicine_type_dict[medicine_type]
        )
        amount = number_utils.get_integer(
            self.ui.tableWidget_doctor.item(row_no, 11).text()
        )
        commission = round(amount * (commission_rate / 100))

        self._set_item_data(row_no, 13, commission_rate, align="right")
        self._set_item_data(row_no, 14, commission, align="right")

        prescript_key = self.ui.tableWidget_doctor.item(row_no, 1).text()
        sql = f'UPDATE prescript SET MedicineType = "{medicine_type}" WHERE PrescriptKey = {prescript_key}'
        self.database.exec_sql(sql)

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                self.ui.tableWidget_doctor.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("0")
                )
                self.ui.tableWidget_doctor.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ""
        if self.ins_type != "全部":
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        if self.doctor != "全部":
            doctor_condition = ' AND Doctor = "{0}"'.format(self.doctor)
        else:
            doctor_condition = " AND Doctor IS NOT NULL AND LENGTH(Doctor) > 0"

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(CaseDate) IN({','.join(self.weekday_list)})"
            )

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT prescript.MedicineSet, prescript.MedicineName, prescript.MedicineType,
                prescript.MedicineKey, prescript.PrescriptKey,
                prescript.Dosage, prescript.Price,
                cases.CaseKey, cases.PatientKey, cases.CaseDate, cases.Name, cases.Period,
                cases.Doctor
            FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                MedicineName NOT LIKE ("代煎%") AND
                MedicineSet >= 2 AND Amount > 0
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY prescript.CaseDate, prescript.MedicineSet, prescript.PrescriptKey
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_commission_cell_value(self, row_no, col_no):
        cell = self.ui.tableWidget_commission.item(row_no, col_no)

        if cell is None:
            value = 0
        else:
            value = number_utils.get_integer(cell.text())

        return value

    def _set_item_data(
        self, row_no, col_no, data, align="left", table_widget_commission=False
    ):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, data)
        if item is None:
            return

        if table_widget_commission:
            tableWidget = self.ui.tableWidget_commission
        else:
            tableWidget = self.ui.tableWidget_doctor

        tableWidget.setItem(row_no, col_no, QtWidgets.QTableWidgetItem(item))
        if align == "right":
            tableWidget.item(row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
        elif align == "center":
            tableWidget.item(row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            tableWidget.item(row_no, col_no).setForeground(QtGui.QColor("red"))

    def _calculate_total(self):
        total_fee, total_commission = 0, 0
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            total_commission += number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 14).text()
            )

            total_fee += number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 11).text()
            )

        row_count = self.ui.tableWidget_doctor.rowCount()
        self.ui.tableWidget_doctor.setRowCount(row_count + 1)
        self._set_item_data(row_count, 10, "合計")
        self._set_item_data(row_count, 11, total_fee, align="right")
        self._set_item_data(row_count, 14, total_commission, align="right")

    def _calculate_commission_total(self):
        total_fee, total_commission = 0, 0
        for row_no in range(self.ui.tableWidget_commission.rowCount()):
            total_commission += number_utils.get_integer(
                self.ui.tableWidget_commission.item(row_no, 3).text()
            )

            total_fee += number_utils.get_integer(
                self.ui.tableWidget_commission.item(row_no, 1).text()
            )

        row_count = self.ui.tableWidget_commission.rowCount()
        self.ui.tableWidget_commission.setRowCount(row_count + 1)
        self._set_item_data(row_count, 0, "合計", table_widget_commission=True)
        self._set_item_data(
            row_count, 1, total_fee, align="right", table_widget_commission=True
        )
        self._set_item_data(
            row_count, 3, total_commission, align="right", table_widget_commission=True
        )

    def _calculate_medicine_name_total(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            combox_box = self.ui.tableWidget_doctor.cellWidget(row_no, 12)
            if combox_box is None:
                continue

            medicine_type = combox_box.currentText()
            medicine_name = self.ui.tableWidget_doctor.item(row_no, 7).text().strip()
            amount = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 11).text()
            )
            quantity = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 8).text()
            )
            pres_days = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 10).text()
            )
            # total_quantity = quantity * pres_days
            total_quantity = 1

            if medicine_type not in list(self.medicine_type_dict.keys()):
                medicine_name = "自費產品"
            elif "療程" in medicine_type:
                pass
            elif medicine_type in ["單方", "複方"]:
                if medicine_name == "自費粉藥":
                    total_quantity = 1
                else:
                    medicine_name = "自費粉藥"
                    total_quantity = 0
            elif medicine_type in ["水藥"]:
                if medicine_name == "自費水藥":
                    total_quantity = 1
                else:
                    medicine_name = "自費水藥"
                    total_quantity = 0
            else:
                medicine_name = "自費產品"

            commission_row_no = self._get_commission_row_no(medicine_name)
            if commission_row_no is None:
                commission_row_no = self.ui.tableWidget_commission.rowCount()
                self.ui.tableWidget_commission.setRowCount(commission_row_no + 1)

            self._set_item_data(
                commission_row_no, 0, medicine_name, table_widget_commission=True
            )

            last_quantity = self._get_commission_cell_value(commission_row_no, 1)
            self._set_item_data(
                commission_row_no,
                1,
                string_utils.xstr(total_quantity + last_quantity),
                align="right",
                table_widget_commission=True,
            )

            last_amount = self._get_commission_cell_value(commission_row_no, 2)
            self._set_item_data(
                commission_row_no,
                2,
                string_utils.xstr(amount + last_amount),
                align="right",
                table_widget_commission=True,
            )

        # self._calculate_commission_total()

    def _get_commission_row_no(self, medicine_name):
        for row_no in range(self.ui.tableWidget_commission.rowCount()):
            try:
                currnet_medicine_name = self.ui.tableWidget_commission.item(
                    row_no, 0
                ).text()
            except Exception:
                continue

            if currnet_medicine_name == medicine_name:
                return row_no

        return None

    def _calculate_medicine_type(self, medicine_type):
        total_fee, total_commission = 0, 0

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            combox_box = self.ui.tableWidget_doctor.cellWidget(row_no, 12)
            if combox_box is None or medicine_type != combox_box.currentText():
                continue

            total_fee += number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 11).text()
            )
            total_commission += number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 14).text()
            )

        commission_rate = number_utils.get_integer(
            self.medicine_type_dict[medicine_type]
        )
        row_count = self.ui.tableWidget_commission.rowCount()
        self.ui.tableWidget_commission.setRowCount(row_count + 1)
        self._set_item_data(row_count, 0, medicine_type, table_widget_commission=True)
        self._set_item_data(
            row_count, 1, total_fee, align="right", table_widget_commission=True
        )
        self._set_item_data(
            row_count, 2, commission_rate, align="right", table_widget_commission=True
        )
        self._set_item_data(
            row_count, 3, total_commission, align="right", table_widget_commission=True
        )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{self.start_date[:10]}至{self.end_date[:10]}醫師金額統計表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor,
            title=f"{self.system_settings.field('院所名稱')} 醫師金額統計表",
            numeric_cell=[
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
            ],
            calc_total=False,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>個別醫師收入統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )
