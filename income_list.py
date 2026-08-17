# -*- coding: UTF-8 -*-
# 掛號櫃台結帳 2018.11.15

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    dialog_utils,
    export_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 掛號櫃台結帳 - 收費一覽表
class IncomeList(QtWidgets.QMainWindow):
    program_name = "掛號櫃台結帳"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.regist_type = args[5]
        self.doctor = args[6]
        self.room = args[7]
        self.tableWidget_registration = args[8]
        self.tableWidget_charge = args[9]
        self.income_source = args[10]
        self.columns = args[11]
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.start_calculate()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_income(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INCOME_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_income = class_utils.get_table_widget(
            self.ui.tableWidget_income, self.database
        )
        self.table_widget_income.set_column_hidden([0])
        self.ui.tableWidget_income.setSortingEnabled(False)
        self._set_table_width()

        self._set_table_widget_total()

    def _set_table_widget_total(self):
        self.ui.tableWidget_total.clear()
        self.ui.tableWidget_total.setSpan(0, 0, 2, 1)
        self.ui.tableWidget_total.setItem(0, 0, QtWidgets.QTableWidgetItem("健保"))
        self.ui.tableWidget_total.setSpan(2, 0, 2, 1)
        self.ui.tableWidget_total.setItem(2, 0, QtWidgets.QTableWidgetItem("自費"))
        self.ui.tableWidget_total.setSpan(1, 8, 3, 1)
        self.ui.tableWidget_total.setSpan(1, 9, 3, 1)

        ins_heading = [
            "健保",
            "掛號費",
            "門診負擔",
            "藥品負擔",
            "欠卡費",
            "還卡費",
            "掛號欠款",
            "健保合計",
            "民俗調理",
            "現金總計",
        ]
        for col_no, heading in enumerate(ins_heading):
            self.ui.tableWidget_total.setItem(
                0, col_no, QtWidgets.QTableWidgetItem(heading)
            )
            self.ui.tableWidget_total.item(0, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )
            self.ui.tableWidget_total.item(0, col_no).setBackground(
                QtGui.QColor("lightGray")
            )

        self_heading = [
            "自費",
            "掛號費",
            "自費金額",
            "應收合計",
            "欠款",
            "實收合計",
            "還款",
            "自費合計",
            "民俗調理",
            "現金總計",
        ]
        for col_no, heading in enumerate(self_heading):
            self.ui.tableWidget_total.setItem(
                2, col_no, QtWidgets.QTableWidgetItem(heading)
            )
            self.ui.tableWidget_total.item(2, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )
            self.ui.tableWidget_total.item(2, col_no).setBackground(
                QtGui.QColor("lightGray")
            )

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_income.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_income.horizontalHeader().sectionClicked.connect(
            self._header_clicked
        )
        self.ui.toolButton_set_traditional_health_case.clicked.connect(
            lambda: self._set_traditional_health_case(case_key=None)
        )
        self.ui.toolButton_set_batch_traditional_health_case.clicked.connect(
            self._set_batch_traditional_health_case
        )

    def _header_clicked(self, col_no):
        if col_no != self.columns["remark"]:
            return

        row_count = self.ui.tableWidget_income.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_income.cellWidget(row_no, col_no)
            if check_box is None:
                continue

            check_box.setChecked(not check_box.isChecked())

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100,
            50,
            180,
            50,
            75,
            90,
            50,
            90,
            90,
            90,
            80,
            50,
            70,
            70,
            70,
            70,
            70,
            70,
            70,
            70,
            50,
            70,
            80,
            80,
            80,
            60,
        ]
        self.table_widget_income.set_table_heading_width(width)

    def open_medical_record(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "進入病歷", self.user_name
            )
            != "Y"
        ):
            return

        case_key = self.table_widget_income.field_value(self.columns["case_key"])
        if case_key in ["", None]:
            return

        self.parent.open_medical_record(case_key, "掛號櫃台結帳")

    def start_calculate(self):
        self._merge_table_widgets()
        self._merge_traditional_health_care()
        try:
            self._read_return_goods()
        except Exception:
            pass

        self._set_check_box()
        self._calculate_total_income()
        self._set_table_widget_total_value()

    def _set_check_box(self):
        for row_no in range(self.ui.tableWidget_income.rowCount()):
            check_box_remark = QtWidgets.QCheckBox()
            check_box_remark.setChecked(False)
            check_box_remark.setStyleSheet("padding-left: 20px")
            col_no = self.columns["remark"]

            self.ui.tableWidget_income.setCellWidget(row_no, col_no, check_box_remark)

    def _set_table_widget_total_value(self):
        row_no = self.ui.tableWidget_income.rowCount() - 1

        ins_regist_fee = self._get_regist_fee_from_table_widget("健保")
        diag_share_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(
                row_no, self.columns["diag_share_fee"]
            ).text()
        )
        drug_share_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(
                row_no, self.columns["drug_share_fee"]
            ).text()
        )
        deposit_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["deposit_fee"]).text()
        )
        refund_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["refund_fee"]).text()
        )
        regist_debt = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["regist_debt"]).text()
        )
        ins_total = (
            ins_regist_fee
            + diag_share_fee
            + drug_share_fee
            + deposit_fee
            + refund_fee
            + regist_debt
        )
        ins_fee_list = [
            ins_regist_fee,
            diag_share_fee,
            drug_share_fee,
            deposit_fee,
            refund_fee,
            regist_debt,
            ins_total,
        ]

        self_regist_fee = self._get_regist_fee_from_table_widget("自費")
        self_total_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(
                row_no, self.columns["self_total_fee"]
            ).text()
        )
        massage_fee = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["massage_fee"]).text()
        )
        debt = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["debt"]).text()
        )
        repayment = number_utils.get_integer(
            self.ui.tableWidget_income.item(row_no, self.columns["repayment"]).text()
        )

        return_goods_fee = self._get_return_goods_fee()

        total_fee = self_regist_fee + self_total_fee
        receipt_fee = total_fee + debt
        self_total = receipt_fee + repayment
        cash_total = ins_total + self_total + massage_fee
        self_fee_list = [
            self_regist_fee,
            self_total_fee,
            total_fee,
            debt,
            receipt_fee,
            repayment,
            self_total,
        ]

        for col_no, ins_fee in enumerate(ins_fee_list):
            self.ui.tableWidget_total.setItem(
                1, col_no + 1, QtWidgets.QTableWidgetItem(string_utils.xstr(ins_fee))
            )
            self.ui.tableWidget_total.item(1, col_no + 1).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

        for col_no, self_fee in enumerate(self_fee_list):
            self.ui.tableWidget_total.setItem(
                3, col_no + 1, QtWidgets.QTableWidgetItem(string_utils.xstr(self_fee))
            )
            self.ui.tableWidget_total.item(3, col_no + 1).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

        self.ui.tableWidget_total.setItem(
            1, 8, QtWidgets.QTableWidgetItem(string_utils.xstr(massage_fee))
        )
        self.ui.tableWidget_total.item(1, 8).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_total.setItem(
            1, 9, QtWidgets.QTableWidgetItem(string_utils.xstr(cash_total))
        )
        self.ui.tableWidget_total.item(1, 9).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    def _get_return_goods_fee(self):
        sql = f'''
            SELECT SUM(Amount) AS TotalAmount FROM returngoods
            WHERE
                DATE(ReturnGoodsDate) = "{self.start_date[:10]}"
        '''
        try:
            rows = self.database.select_record(sql)
        except Exception:
            return 0

        if len(rows) <= 0:
            return 0

        row = rows[0]

        return -number_utils.get_integer(row["TotalAmount"])

    def _get_regist_fee_from_table_widget(self, in_ins_type):
        regist_fee = 0
        for row_no in range(self.ui.tableWidget_income.rowCount() - 1):
            ins_type = self.ui.tableWidget_income.item(row_no, self.columns["ins_type"])
            if ins_type is None:
                continue

            ins_type = ins_type.text()
            if (
                in_ins_type == "健保"
                and ins_type != in_ins_type
                or in_ins_type == "自費"
                and ins_type == "健保"
            ):
                continue

            regist_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["regist_fee"]
                ).text()
            )

        return regist_fee

    def _merge_table_widgets(self):
        self.ui.tableWidget_income.setRowCount(0)

        self._merge_table_registration()
        self._merge_table_charge()

    def _table_widget_income_patient_key_exists(self, patient_key, name, ins_type):
        row_no_exists = None
        for row_no in range(self.ui.tableWidget_income.rowCount()):
            patient_key_item = self.ui.tableWidget_income.item(
                row_no, self.columns["patient_key"]
            )
            name_item = self.ui.tableWidget_income.item(row_no, self.columns["name"])
            ins_type_item = self.ui.tableWidget_income.item(
                row_no, self.columns["ins_type"]
            )
            if (
                patient_key_item is not None
                and patient_key_item.text() == patient_key
                and name_item is not None
                and name_item.text() == name
            ):
                row_no_exists = row_no
                break
            # if (patient_key_item is not None and patient_key_item.text() == patient_key and
            #         name_item is not None and name_item.text() == name and
            #         ins_type_item is not None and ins_type_item.text() == ins_type):
            #     row_no_exists = row_no
            #     break

        return row_no_exists

    def _merge_table_registration(self):
        for row_no in range(self.tableWidget_registration.rowCount()):
            patient_key = self.tableWidget_registration.item(row_no, 3).text()
            name = self.tableWidget_registration.item(row_no, 4).text()
            ins_type = self.tableWidget_registration.item(row_no, 5).text()
            if patient_key in ["", None]:  # at end
                break

            row_no_exists = self._table_widget_income_patient_key_exists(
                patient_key, name, ins_type
            )
            if row_no_exists is None:  # 不存在
                self._append_registration_item(row_no)
            else:
                self._insert_registration_item(row_no_exists, row_no)

    def _get_registration_item(self, registration_row_no):
        cell_data = [
            [
                self.columns["case_key"],
                self.tableWidget_registration.item(registration_row_no, 0),
            ],
            [
                self.columns["case_date"],
                self.tableWidget_registration.item(registration_row_no, 1),
            ],
            [
                self.columns["period"],
                self.tableWidget_registration.item(registration_row_no, 2),
            ],
            [
                self.columns["patient_key"],
                self.tableWidget_registration.item(registration_row_no, 3),
            ],
            [
                self.columns["name"],
                self.tableWidget_registration.item(registration_row_no, 4),
            ],
            [
                self.columns["ins_type"],
                self.tableWidget_registration.item(registration_row_no, 5),
            ],
            [
                self.columns["share_type"],
                self.tableWidget_registration.item(registration_row_no, 6),
            ],
            [
                self.columns["treat_type"],
                self.tableWidget_registration.item(registration_row_no, 7),
            ],  # 負擔類別
            [
                self.columns["discount_type"],
                self.tableWidget_registration.item(registration_row_no, 8),
            ],  # 優待類別
            [
                self.columns["card"],
                self.tableWidget_registration.item(registration_row_no, 9),
            ],  # 卡序
            [
                self.columns["regist_fee"],
                self.tableWidget_registration.item(registration_row_no, 10),
            ],  # 掛號費
            [
                self.columns["diag_share_fee"],
                self.tableWidget_registration.item(registration_row_no, 11),
            ],  # 門診負擔
            [
                self.columns["deposit_fee"],
                self.tableWidget_registration.item(registration_row_no, 12),
            ],  # 欠卡費
            [
                self.columns["refund_fee"],
                self.tableWidget_registration.item(registration_row_no, 13),
            ],  # 還卡費
            [
                self.columns["repayment"],
                self.tableWidget_registration.item(registration_row_no, 15),
            ],  # 自費還款
            [
                self.columns["regist_debt"],
                self.tableWidget_registration.item(registration_row_no, 14),
            ],  # 掛號欠款
            [
                self.columns["registrar"],
                self.tableWidget_registration.item(registration_row_no, 17),
            ],  # 掛號者
            [
                self.columns["regist_no"],
                self.tableWidget_registration.item(registration_row_no, 19),
            ],  # 診號
        ]

        return cell_data

    def _append_registration_item(self, registration_row_no):
        cell_data = self._get_registration_item(registration_row_no)

        row_no = self.ui.tableWidget_income.rowCount()
        self.ui.tableWidget_income.setRowCount(row_no + 1)
        for cell in cell_data:
            self.ui.tableWidget_income.setItem(
                row_no, cell[0], QtWidgets.QTableWidgetItem(cell[1])
            )

    # def _insert_registration_item(self, income_row_no, registration_row_no):
    #     cell_data = self._get_registration_item(registration_row_no)

    #     for cell in cell_data:
    #         if self.ui.tableWidget_income.item(income_row_no, cell[0]).text() != "0":
    #             continue

    #         if cell[0] in [
    #             self.columns["refund_fee"],
    #             self.columns["repayment"],
    #         ]:  # 還卡費,還款另外計算 (當天可能還兩筆)
    #             continue

    #         self.ui.tableWidget_income.setItem(
    #             income_row_no, cell[0], QtWidgets.QTableWidgetItem(cell[1])
    #         )

    #     total_regist_fee = number_utils.get_integer(
    #         self.ui.tableWidget_income.item(
    #             income_row_no, self.columns["regist_fee"]
    #         ).text()
    #     )
    #     regist_fee = number_utils.get_integer(
    #         self.tableWidget_registration.item(registration_row_no, 10).text()
    #     )  # 櫃台結帳分析表

    #     total_refund_fee = number_utils.get_integer(
    #         self.ui.tableWidget_income.item(
    #             income_row_no, self.columns["refund_fee"]
    #         ).text()
    #     )
    #     refund_fee = number_utils.get_integer(
    #         self.tableWidget_registration.item(registration_row_no, 13).text()
    #     )  # 櫃台結帳分析表

    #     total_regist_fee += regist_fee
    #     total_refund_fee += refund_fee

    #     self.ui.tableWidget_income.setItem(
    #         income_row_no,
    #         self.columns["regist_fee"],
    #         QtWidgets.QTableWidgetItem(string_utils.xstr(total_regist_fee)),
    #     )
    #     self.ui.tableWidget_income.setItem(
    #         income_row_no,
    #         self.columns["refund_fee"],
    #         QtWidgets.QTableWidgetItem(string_utils.xstr(total_refund_fee)),
    #     )

    #     total_repayment = number_utils.get_integer(
    #         self.ui.tableWidget_income.item(
    #             income_row_no, self.columns["repayment"]
    #         ).text()
    #     )
    #     repayment = number_utils.get_integer(
    #         self.tableWidget_registration.item(registration_row_no, 15).text()
    #     )  # 櫃台結帳分析表

    #     total_repayment += repayment
    #     self.ui.tableWidget_income.setItem(
    #         income_row_no,
    #         self.columns["repayment"],
    #         QtWidgets.QTableWidgetItem(string_utils.xstr(total_repayment)),
    #     )
    def _insert_registration_item(self, income_row_no, registration_row_no):
        # 費用欄位一律累加 (同一人當天可能有多筆掛號 / 還卡 / 還款)
        # key = income 欄號, value = tableWidget_registration 來源欄號
        fee_columns = {
            self.columns["regist_fee"]: 10,  # 掛號費
            self.columns["diag_share_fee"]: 11,  # 門診負擔
            self.columns["deposit_fee"]: 12,  # 欠卡費
            self.columns["refund_fee"]: 13,  # 還卡費
            self.columns["regist_debt"]: 14,  # 掛號欠款
            self.columns["repayment"]: 15,  # 自費還款
        }

        # 非費用欄位: 原本是空的或 0 才補上
        for cell in self._get_registration_item(registration_row_no):
            col_no = cell[0]
            if col_no in fee_columns:
                continue
            item = self.ui.tableWidget_income.item(income_row_no, col_no)
            if item is not None and item.text() not in ["", "0"]:
                continue
            self.ui.tableWidget_income.setItem(
                income_row_no, col_no, QtWidgets.QTableWidgetItem(cell[1])
            )

        # 費用欄位: 累加
        for col_no, source_col in fee_columns.items():
            item = self.ui.tableWidget_income.item(income_row_no, col_no)
            total = number_utils.get_integer(item.text()) if item is not None else 0
            source_item = self.tableWidget_registration.item(
                registration_row_no, source_col
            )
            if source_item is not None:
                total += number_utils.get_integer(source_item.text())
            self.ui.tableWidget_income.setItem(
                income_row_no,
                col_no,
                QtWidgets.QTableWidgetItem(string_utils.xstr(total)),
            )

    def _merge_table_charge(self):
        for row_no in range(self.tableWidget_charge.rowCount()):
            treat_type = self.tableWidget_charge.item(row_no, 7).text()
            patient_key = self.tableWidget_charge.item(row_no, 3).text()
            name = self.tableWidget_charge.item(row_no, 4).text()
            ins_type = self.tableWidget_charge.item(row_no, 5).text()
            if patient_key == "":  # at end
                break

            row_no_exists = self._table_widget_income_patient_key_exists(
                patient_key, name, ins_type
            )
            # if row_no_exists is None or treat_type == '民俗調理':
            if row_no_exists is None:
                self._append_charge_item(row_no)
            else:
                self._insert_charge_item(row_no_exists, row_no)

    def _get_charge_item(self, charge_row_no, ins_type=None, treat_type=None):
        total_fee_item = self.tableWidget_charge.item(charge_row_no, 13)
        massage_fee_item = QtWidgets.QTableWidgetItem()
        massage_fee_item.setData(QtCore.Qt.EditRole, 0)
        if ins_type == "自費" and treat_type in ["民俗調理", "自費健保"]:
            total_fee_item = QtWidgets.QTableWidgetItem()
            total_fee_item.setData(QtCore.Qt.EditRole, 0)
            massage_fee_item = self.tableWidget_charge.item(charge_row_no, 13)

        cell_data = [
            [self.columns["case_key"], self.tableWidget_charge.item(charge_row_no, 0)],
            [self.columns["case_date"], self.tableWidget_charge.item(charge_row_no, 1)],
            [self.columns["period"], self.tableWidget_charge.item(charge_row_no, 2)],
            [
                self.columns["patient_key"],
                self.tableWidget_charge.item(charge_row_no, 3),
            ],
            [self.columns["name"], self.tableWidget_charge.item(charge_row_no, 4)],
            [self.columns["ins_type"], self.tableWidget_charge.item(charge_row_no, 5)],
            [
                self.columns["share_type"],
                self.tableWidget_charge.item(charge_row_no, 6),
            ],
            [
                self.columns["treat_type"],
                self.tableWidget_charge.item(charge_row_no, 7),
            ],
            [
                self.columns["discount_type"],
                self.tableWidget_charge.item(charge_row_no, 8),
            ],  # 優待類別
            [
                self.columns["card"],
                self.tableWidget_charge.item(charge_row_no, 9),
            ],  # 卡序
            [
                self.columns["pres_days"],
                self.tableWidget_charge.item(charge_row_no, 10),
            ],  # 藥日
            [
                self.columns["drug_share_fee"],
                self.tableWidget_charge.item(charge_row_no, 12),
            ],  # 藥品負擔
            [self.columns["self_total_fee"], total_fee_item],  # 自費應收
            [
                self.columns["debt"],
                self.tableWidget_charge.item(charge_row_no, 15),
            ],  # 自費欠款
            [
                self.columns["receipt_fee"],
                self.tableWidget_charge.item(charge_row_no, 16),
            ],  # 實收現金
            [
                self.columns["cashier"],
                self.tableWidget_charge.item(charge_row_no, 17),
            ],  # 醫師
            [
                self.columns["regist_no"],
                self.tableWidget_charge.item(charge_row_no, 19),
            ],  # 診號
            [self.columns["massage_fee"], massage_fee_item],  # 民俗調理
        ]

        return cell_data

    def _append_charge_item(self, charge_row_no):
        cell_data = self._get_charge_item(charge_row_no)

        row_no = self.ui.tableWidget_income.rowCount()
        self.ui.tableWidget_income.setRowCount(row_no + 1)
        for cell in cell_data:
            self.ui.tableWidget_income.setItem(
                row_no, cell[0], QtWidgets.QTableWidgetItem(cell[1])
            )

    def _insert_charge_item(self, income_row_no, charge_row_no):
        ins_type = self.tableWidget_charge.item(charge_row_no, 5).text()
        treat_type = self.tableWidget_charge.item(charge_row_no, 7).text()
        cell_data = self._get_charge_item(
            charge_row_no, ins_type=ins_type, treat_type=treat_type
        )

        for cell in cell_data:
            col_no = cell[0]
            if (
                self.ui.tableWidget_income.item(income_row_no, col_no) is not None
                and self.ui.tableWidget_income.item(income_row_no, col_no).text() != ""
            ):
                if col_no in [
                    self.columns["regist_fee"],
                    self.columns["diag_share_fee"],
                    self.columns["drug_share_fee"],
                    self.columns["deposit_fee"],
                    self.columns["refund_fee"],
                    self.columns["repayment"],
                    self.columns["self_total_fee"],
                    self.columns["debt"],
                    self.columns["regist_debt"],
                    self.columns["massage_fee"],
                ]:
                    fee = number_utils.get_integer(
                        self.ui.tableWidget_income.item(income_row_no, col_no).text()
                    )
                    fee += number_utils.get_integer(cell[1].text())
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, fee)
                    self.ui.tableWidget_income.setItem(income_row_no, col_no, item)
                continue

            if cell[1] is None or cell[1].text() == "0":
                continue

            self.ui.tableWidget_income.setItem(
                income_row_no, col_no, QtWidgets.QTableWidgetItem(cell[1])
            )

    def _calculate_total_income(self):
        self._calculate_subtotal()
        self._separate_massage_fee()
        self._calculate_total()

    def _get_massage_fee(self, case_key):
        sql = f"""
            SELECT SMassageFee FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        row = rows[0]

        return number_utils.get_integer(row["SMassageFee"])

    def _separate_massage_fee(self):
        row_count = self.ui.tableWidget_income.rowCount()
        for row_no in range(row_count):
            item = self.ui.tableWidget_income.item(row_no, self.columns["treat_type"])
            if item is None or (item is not None and item.text() not in ["民俗調理"]):
                continue

            ins_type_item = self.ui.tableWidget_income.item(
                row_no, self.columns["ins_type"]
            )
            if (
                ins_type_item is None or ins_type_item.text() == "健保"
            ):  # 只統計自費民俗調理
                continue

            self_total_fee = number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["self_total_fee"]
                ).text()
            )

            if self_total_fee <= 0:
                continue

            case_key = self.ui.tableWidget_income.item(
                row_no, self.columns["case_key"]
            ).text()
            massage_fee = self._get_massage_fee(case_key)

            self_total_fee -= massage_fee

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, self_total_fee)
            self.ui.tableWidget_income.setItem(
                row_no, self.columns["self_total_fee"], item
            )
            self.ui.tableWidget_income.item(
                row_no, self.columns["self_total_fee"]
            ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, massage_fee)
            self.ui.tableWidget_income.setItem(
                row_no, self.columns["massage_fee"], item
            )
            self.ui.tableWidget_income.item(
                row_no, self.columns["massage_fee"]
            ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _calculate_subtotal(self):
        row_count = self.ui.tableWidget_income.rowCount()
        for row_no in range(row_count):
            subtotal = 0
            for col_no in range(
                self.columns["regist_fee"], self.columns["massage_fee"] + 1
            ):  # regist_fee...massage_fee
                cell = self.ui.tableWidget_income.item(row_no, col_no)
                if cell is None or cell.text() == "":
                    self.ui.tableWidget_income.setItem(
                        row_no, col_no, QtWidgets.QTableWidgetItem("0")
                    )
                else:
                    subtotal += number_utils.get_integer(cell.text())
                self.ui.tableWidget_income.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            self.ui.tableWidget_income.setItem(
                row_no,
                self.columns["receipt_fee"],
                QtWidgets.QTableWidgetItem(string_utils.xstr(subtotal)),
            )
            self.ui.tableWidget_income.item(
                row_no, self.columns["receipt_fee"]
            ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _calculate_total(self):
        row_count = self.ui.tableWidget_income.rowCount()
        regist_fee, diag_share_fee, drug_share_fee, deposit_fee, refund_fee = (
            0,
            0,
            0,
            0,
            0,
        )
        repayment, self_total_fee, debt, regist_debt, receipt_fee = 0, 0, 0, 0, 0
        massage_fee = 0

        for row_no in range(row_count):
            treat_type = self.ui.tableWidget_income.item(
                row_no, self.columns["treat_type"]
            ).text()

            regist_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["regist_fee"]
                ).text()
            )
            diag_share_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["diag_share_fee"]
                ).text()
            )
            drug_share_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["drug_share_fee"]
                ).text()
            )
            deposit_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["deposit_fee"]
                ).text()
            )
            refund_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["refund_fee"]
                ).text()
            )
            repayment += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["repayment"]
                ).text()
            )
            self_total_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["self_total_fee"]
                ).text()
            )

            debt += number_utils.get_integer(
                self.ui.tableWidget_income.item(row_no, self.columns["debt"]).text()
            )
            regist_debt += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["regist_debt"]
                ).text()
            )
            massage_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["massage_fee"]
                ).text()
            )
            receipt_fee += number_utils.get_integer(
                self.ui.tableWidget_income.item(
                    row_no, self.columns["receipt_fee"]
                ).text()
            )

        total_record = [
            None,  # case_key
            None,  # remark
            None,
            None,
            None,
            "合計",
            None,
            None,
            None,
            None,
            None,
            None,
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(deposit_fee),
            string_utils.xstr(refund_fee),
            string_utils.xstr(repayment),
            string_utils.xstr(self_total_fee),
            string_utils.xstr(debt),
            string_utils.xstr(regist_debt),
            string_utils.xstr(massage_fee),
            string_utils.xstr(receipt_fee),  # 多扣了欠款，把欠款加回去
        ]

        self.ui.tableWidget_income.setRowCount(row_count + 1)

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_income.setItem(
                row_count, col_no, QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [
                self.columns["regist_fee"],
                self.columns["diag_share_fee"],
                self.columns["drug_share_fee"],
                self.columns["deposit_fee"],
                self.columns["refund_fee"],
                self.columns["repayment"],
                self.columns["self_total_fee"],
                self.columns["debt"],
                self.columns["regist_debt"],
                self.columns["massage_fee"],
                self.columns["receipt_fee"],
            ]:
                self.ui.tableWidget_income.item(row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_income.item(row_count, col_no).setFont(font)

    # 合併民俗調理
    def _merge_traditional_health_care(self):
        for row_no in range(self.ui.tableWidget_income.rowCount(), -1, -1):
            item = self.ui.tableWidget_income.item(row_no, self.columns["treat_type"])
            if item is None:
                continue

            treat_type = item.text()
            if treat_type in ["民俗調理", "自費健保"]:
                case_key = self.ui.tableWidget_income.item(
                    row_no, self.columns["case_key"]
                ).text()
                patient_key = self.ui.tableWidget_income.item(
                    row_no, self.columns["patient_key"]
                ).text()
                replace_row_no = self._get_merge_row_no(patient_key, row_no)
                if replace_row_no is not None:
                    regist_fee = self._get_regist_fee(case_key)
                    if regist_fee > 0:
                        continue

                    massage_fee = self.ui.tableWidget_income.item(
                        row_no, self.columns["receipt_fee"]
                    )
                    if massage_fee is not None:
                        massage_fee = massage_fee.text()
                    else:
                        massage_fee = 0

                    self._merge_fee(
                        replace_row_no, self.columns["massage_fee"], massage_fee
                    )

                    self.ui.tableWidget_income.removeRow(row_no)

    def _read_return_goods(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f'AND Period = "{self.period}"'

        sql = f'''
            SELECT * FROM returngoods
            WHERE
                DATE(ReturnGoodsDate) = "{self.start_date[:10]}"
                {period_condition}
            ORDER BY ReturnGoodsKey
        '''
        rows = self.database.select_record(sql)

        row_count = self.ui.tableWidget_income.rowCount()
        for row in rows:
            cells = [
                None,
                None,
                row["ReturnGoodsDate"].strftime("%Y-%m-%d"),
                string_utils.xstr(row["Period"]),
                row["PatientKey"],
                string_utils.xstr(row["Name"]),
                "自費",
                None,
                "退貨",
                None,
                None,
                None,
                0,
                0,
                0,
                0,
                0,
                0,
                -number_utils.get_integer(row["Amount"]),
                0,
                0,
                0,
                -number_utils.get_integer(row["Amount"]),
            ]
            row_count += 1
            self.ui.tableWidget_income.setRowCount(row_count)
            for col_no, cell in enumerate(cells):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, cell)
                self.ui.tableWidget_income.setItem(row_count - 1, col_no, item)
                if col_no in [3]:
                    self.ui.tableWidget_income.item(
                        row_count - 1, col_no
                    ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                elif col_no in [4]:
                    self.ui.tableWidget_income.item(
                        row_count - 1, col_no
                    ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _get_regist_fee(self, case_key):
        sql = f"SELECT RegistFee FROM cases WHERE CaseKey = {case_key}"
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        return number_utils.get_integer(rows[0]["RegistFee"])

    def _merge_fee(self, row_no, col_no, fee):
        item = self.ui.tableWidget_income.item(row_no, col_no)
        if item is not None:
            origin_fee = number_utils.get_integer(item.text())
        else:
            origin_fee = 0

        self.ui.tableWidget_income.setItem(
            row_no,
            col_no,
            QtWidgets.QTableWidgetItem(
                string_utils.xstr(origin_fee + number_utils.get_integer(fee))
            ),
        )
        self.ui.tableWidget_income.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_income.item(row_no, col_no).setForeground(
            QtGui.QColor("blue")
        )

    def _get_merge_row_no(self, in_patient_key, last_row_no):
        for row_no in range(last_row_no):
            item = self.ui.tableWidget_income.item(row_no, self.columns["patient_key"])
            if item is None:
                continue

            patient_key = item.text()
            if patient_key == in_patient_key:
                return row_no

        return None

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出交帳明細一覽表",
            f"{self.start_date[:10]}至{self.end_date[:10]}交帳明細一覽表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_income_list(
            self.system_settings,
            excel_file_name,
            self.ui.tableWidget_income,
            self.columns,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _set_batch_traditional_health_case(self):
        input_dialog = dialog_utils.get_dialog(
            "設定費用", "請設定民俗調理費", "0", QInputDialog.IntInput, 320, 200
        )
        if not input_dialog.exec_():
            return

        traditional_health_care_fee = input_dialog.textValue()
        if traditional_health_care_fee == "0":
            return

        row_count = self.ui.tableWidget_income.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            "正在設定民俗調理費中, 請稍後...", "取消", 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no in range(row_count):
            progress_dialog.setValue(row_no + 1)

            check_box = self.ui.tableWidget_income.cellWidget(
                row_no, self.columns["remark"]
            )
            if check_box is None or not check_box.isChecked():
                continue

            case_key_item = self.ui.tableWidget_income.item(
                row_no, self.columns["case_key"]
            )
            if case_key_item is None:
                continue

            case_key = case_key_item.text()
            ins_type = self.ui.tableWidget_income.item(
                row_no, self.columns["ins_type"]
            ).text()
            treat_type = self.ui.tableWidget_income.item(
                row_no, self.columns["treat_type"]
            ).text()
            self._set_traditional_health_case(
                case_key=case_key,
                ins_type=ins_type,
                treat_type=treat_type,
                traditional_health_care_fee=traditional_health_care_fee,
                set_massager=False,
                refresh_record=False,
            )

        progress_dialog.setValue(row_count)

        self.parent.start_calculate()
        self.parent.tabWidget_income.setCurrentIndex(1)

    def _set_traditional_health_case(
        self,
        case_key=None,
        ins_type=None,
        treat_type=None,
        set_massager=True,
        traditional_health_care_fee=None,
        refresh_record=True,
    ):
        if case_key is None:
            case_key = self.table_widget_income.field_value(self.columns["case_key"])
            ins_type = self.table_widget_income.field_value(self.columns["ins_type"])
            treat_type = self.table_widget_income.field_value(
                self.columns["treat_type"]
            )

        if case_key in [None, ""]:
            return

        sql = f"""
            SELECT Massager FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        case_massager = string_utils.xstr(row["Massager"])
        if case_massager != "":
            massager = case_massager
        else:
            massager = None

        if massager is None and set_massager:
            massager_list = personnel_utils.get_person(self.database, "推拿師父")
            massager_list = [None] + massager_list
            input_dialog = dialog_utils.get_dialog(
                "推拿師選擇",
                "請選擇民俗調理的推拿師父",
                None,
                QInputDialog.TextInput,
                320,
                200,
            )
            input_dialog.setComboBoxItems(massager_list)
            if not input_dialog.exec_():
                return

            massager = input_dialog.textValue()

        if traditional_health_care_fee is None:
            fee = charge_utils.get_traditional_health_care_fee(
                self.database, self.system_settings, "健保", 1, massager
            )
            input_dialog = dialog_utils.get_dialog(
                "設定費用",
                "請設定民俗調理費",
                string_utils.xstr(fee),
                QInputDialog.IntInput,
                320,
                200,
            )
            if not input_dialog.exec_():
                return

            traditional_health_care_fee = input_dialog.textValue()

        if ins_type == "健保" or (ins_type == "自費" and treat_type != "民俗調理"):
            case_utils.write_traditional_health_care(
                self.database,
                self.system_settings,
                case_key,
                traditional_health_care_fee=traditional_health_care_fee,
                massager=massager,
            )
        else:
            case_utils.update_traditional_health_care(
                self.database,
                self.system_settings,
                case_key,
                traditional_health_care_fee=traditional_health_care_fee,
            )

        if refresh_record:
            self.parent.start_calculate()
            self.parent.tabWidget_income.setCurrentIndex(1)
