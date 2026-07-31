# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    export_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 執行業務所得統計 2024.07.19
class StatisticsBusinessIncomeList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
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
        self.program_name = "自費印花稅統計"
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.clinic_name = self.system_settings.field("院所名稱")

        self._set_ui()
        self._set_signal()

        self.item_list = [
            "科中藥品",
            "水藥",
            "丸散",
            "保健食品",
            "三伏貼",
            "三九貼",
            "推拿",
            "整復",
            "拔罐",
            "針灸",
            "護具",
            "膏藥",
            "藥膏",
            "貼布",
            "噴劑",
            "減肥",
            "診斷證明書",
        ]

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            ui_utils.UI_STATISTICS_BUSINESS_INCOME_LIST, self
        )
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_case_amount = class_utils.get_table_widget(
            self.ui.tableWidget_case_amount, self.database
        )
        self._set_table_width()
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.toolButton_export_excel.setEnabled(False)

    def _set_table_width(self):
        width = [
            180,
            100,
            120,
            100,
        ]
        self.table_widget_case_amount.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_case_amount.setRowCount(0)
        self._calculate_data()

    def _calculate_data(self):
        self._set_items()
        self._calculate_case_amount()
        self._calculate_table_widget_total(self.ui.tableWidget_case_amount)

    def _set_items(self):
        self.ui.tableWidget_case_amount.setRowCount(len(self.item_list) + 1)
        for row_no, item_name in enumerate(self.item_list):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, item_name)
            self.ui.tableWidget_case_amount.setItem(row_no, 0, item)

    def _get_row_no(self, item_type):
        for row_no, item_name in enumerate(self.item_list):
            if item_name == item_type:
                return row_no

    def _get_medicine_sets(self, case_key):
        sql = f'''
            SELECT
                MedicineSet
            FROM
                prescript
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet >= 2
            GROUP BY MedicineSet
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_dosage_total_fee(self, case_key, medicine_set):
        sql = f'''
            SELECT
                SUM(TotalFee) AS TotalFee
            FROM
                dosage
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet = {medicine_set}
        '''
        rows = self.database.select_record(sql)
        if rows and rows[0]["TotalFee"] is not None:
            return number_utils.get_integer(rows[0]["TotalFee"])

        return 0

    # 修正: 折讓為 set 層級, 各 set 扣自己的 dosage.DiscountFee
    #
    # set 實收 = 登錄金額 - 該 set 的 DiscountFee
    #   登錄金額: dosage.TotalFee 有值優先, 否則加總 prescript.Amount
    #
    # 注意 (口徑確認點):
    #   此寫法假設 dosage.TotalFee 是「折讓前」的登錄金額。
    #   如果實際上 dosage.TotalFee 已經是折讓後實收, 則第一層不可再扣
    #   DiscountFee (會扣兩次), 只有 fallback 到 prescript.Amount 時才需要扣。

    def _get_set_total_fee(self, case_key, medicine_set):
        sql = f'''
            SELECT
                SUM(TotalFee) AS TotalFee,
                SUM(DiscountFee) AS DiscountFee
            FROM
                dosage
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet = {medicine_set}
        '''
        rows = self.database.select_record(sql)

        dosage_total = 0
        discount_fee = 0
        if rows:
            dosage_total = number_utils.get_integer(rows[0]["TotalFee"])
            discount_fee = number_utils.get_integer(rows[0]["DiscountFee"])

        if dosage_total > 0:
            base = dosage_total
        else:
            # 處置類等沒有 dosage 金額的 set: 用 prescript 明細加總
            sql = f'''
                SELECT
                    SUM(Amount) AS Amount
                FROM
                    prescript
                WHERE
                    CaseKey = "{case_key}" AND
                    MedicineSet = {medicine_set}
            '''
            prescript_rows = self.database.select_record(sql)
            base = 0
            if prescript_rows and prescript_rows[0]["Amount"] is not None:
                base = number_utils.get_integer(prescript_rows[0]["Amount"])

        net = base - discount_fee
        net = max(net, 0)  # 折讓大於登錄金額屬資料異常, 不讓負數污染統計

        return net

    # _calculate_case_amount 簡化: 各 set 金額已是最終實收, 不再分攤縮放

    def _calculate_case_amount(self):
        FALLBACK_ITEM = "保健食品"

        rows = self._get_case_rows()
        grand_total_case = 0  # cases.TotalFee 加總, 供驗算

        for row in rows:
            case_key = row["CaseKey"]
            case_total_fee = number_utils.get_integer(row["TotalFee"])
            grand_total_case += case_total_fee

            medicine_sets = self._get_medicine_sets(case_key)
            counted_items = set()
            set_total = 0

            for medicine_set in medicine_sets:
                ms = number_utils.get_integer(medicine_set["MedicineSet"])
                amount = self._get_set_total_fee(case_key, ms)

                item_type = self._get_item_type(case_key, ms)
                row_no = self._get_row_no(item_type)
                if row_no is None:
                    item_type = FALLBACK_ITEM
                    row_no = self._get_row_no(FALLBACK_ITEM)

                add_person = item_type not in counted_items
                counted_items.add(item_type)

                self._set_data(row_no, amount, add_person)
                set_total += amount

            # 偷懶病歷: 各 set 都算不出金額但 TotalFee 有值
            # -> 差額歸給第一個 set 的項目 (只有一個 set 時即整筆歸該項)
            diff = case_total_fee - set_total
            if diff != 0 and medicine_sets:
                if set_total == 0:
                    # 偷懶病歷: 全部 set 都沒金額, 整筆歸第一個 set 的項目
                    ms = number_utils.get_integer(medicine_sets[0]["MedicineSet"])
                    item_type = self._get_item_type(case_key, ms)
                    row_no = self._get_row_no(item_type)
                    if row_no is None:
                        row_no = self._get_row_no(FALLBACK_ITEM)
                    self._set_data(row_no, diff, add_person=False)
                else:
                    # 明細合計與 TotalFee 有差額: 差額歸科中藥品
                    row_no = self._get_row_no("科中藥品")
                    self._set_data(row_no, diff, add_person=False)

        return grand_total_case

    def _allocate_case_fee(self, case_total_fee, dosage_totals):
        # 將 case_total_fee 分攤到各 medicine_set
        # 回傳 [(medicine_set, 分攤金額), ...], 分攤金額加總必等於 case_total_fee
        priced = [(ms, amount) for ms, amount in dosage_totals if amount > 0]
        unpriced = [ms for ms, amount in dosage_totals if amount <= 0]
        priced_sum = sum(amount for _, amount in priced)

        allocations = []

        if not priced:
            # 情境 C: 全部沒填價, 平均分攤
            remaining = case_total_fee
            for i, ms in enumerate(unpriced):
                if i == len(unpriced) - 1:
                    amount = remaining
                else:
                    amount = round(case_total_fee / len(unpriced))
                    remaining -= amount
                allocations.append((ms, amount))
        elif unpriced and case_total_fee >= priced_sum:
            # 情境 B: 有價的照登錄金額, 差額平均分給沒填價的 set
            for ms, amount in priced:
                allocations.append((ms, amount))

            diff = case_total_fee - priced_sum
            remaining = diff
            for i, ms in enumerate(unpriced):
                if i == len(unpriced) - 1:
                    amount = remaining
                else:
                    amount = round(diff / len(unpriced))
                    remaining -= amount
                allocations.append((ms, amount))
        else:
            # 情境 A: 全部有價 (或整單折讓致 TotalFee < 有價合計),
            # 依比例分攤, 最後一個吸收進位誤差
            remaining = case_total_fee
            for i, (ms, amount) in enumerate(priced):
                if i == len(priced) - 1:
                    adjusted = remaining
                else:
                    adjusted = round(amount * case_total_fee / priced_sum)
                    remaining -= adjusted
                allocations.append((ms, adjusted))

            # 折讓情境下沒填價的 set 分不到錢, 但仍回傳 0 額以利除錯
            for ms in unpriced:
                allocations.append((ms, 0))

        return allocations

    def _set_data(self, row_no, total_fee, add_person=True):
        person_item = self.ui.tableWidget_case_amount.item(row_no, 1)
        if person_item is None:
            person_count = 0
        else:
            person_count = number_utils.get_integer(person_item.text())

        total_fee_item = self.ui.tableWidget_case_amount.item(row_no, 2)
        if total_fee_item is None:
            total_fee_sum = 0
        else:
            total_fee_sum = number_utils.get_integer(total_fee_item.text())

        if add_person:
            person_count += 1

        self._set_item_data(self.ui.tableWidget_case_amount, row_no, 1, person_count)
        self._set_item_data(
            self.ui.tableWidget_case_amount, row_no, 2, total_fee_sum + total_fee
        )

    def _get_case_rows(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        ins_type_condition = ""
        if self.ins_type != "全部":
            ins_type_condition = f' AND InsType = "{self.ins_type}"'

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(CaseDate) IN({','.join(self.weekday_list)})"
            )

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT
                CaseKey, TotalFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                TotalFee > 0
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    # 修正版 _get_item_type
    # 1. 第二迴圈內重新取得每一列的 medicine_type / medicine_name（原本用到最後一列的舊值）
    # 2. "埋線減肥" 改回傳 "減肥"（item_list 內的名稱），金額才不會被 _get_row_no 丟掉
    # 3. 改為逐列判斷、比到就 return；全部比不到才歸 "保健食品"
    def _get_item_type(self, case_key, medicine_set):
        sql = f'''
            SELECT
                MedicineName, MedicineType
            FROM
                prescript
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet = {medicine_set} AND
                Amount > 0
        '''
        rows = self.database.select_record(sql)

        # 第一優先: 名稱或類別直接含有 item_list 的關鍵字
        for row in rows:
            medicine_type = string_utils.xstr(row["MedicineType"])
            medicine_name = string_utils.xstr(row["MedicineName"])
            for item_name in self.item_list:
                if item_name in medicine_name or item_name in medicine_type:
                    return item_name

        # 第二優先: 依 MedicineType 推斷 (每列都要重新取值)
        for row in rows:
            medicine_type = string_utils.xstr(row["MedicineType"])
            medicine_name = string_utils.xstr(row["MedicineName"])

            if medicine_type == "穴道" or "針灸" in medicine_name:
                return "針灸"

            if "埋線" in medicine_type or "埋線" in medicine_name:
                return "減肥"  # 原本回傳 "埋線減肥"，不在 item_list 內，金額會消失

            if "丸" in medicine_type and "丸" in medicine_name:
                return "丸散"

            if "散" in medicine_type and "散" in medicine_name:
                return "丸散"

            if "OTC" in medicine_type:
                return "保健食品"

            if medicine_type == "器材":
                return "護具"

            if medicine_type == "外用":
                return "膏藥"

            if medicine_type == "處置":
                return "推拿"

            if medicine_type in ["單方", "複方"]:
                return "科中藥品"

        # 全部比不到才歸為保健食品; 沒有任何處方列則回 None
        if rows:
            return "保健食品"

        return None

    def _calculate_table_widget_total(self, tableWidget):
        row_count = tableWidget.rowCount()
        total_person, total_fee, total_avg = 0, 0, 0
        for row_no in range(row_count - 1):
            person_item = tableWidget.item(row_no, 1)
            if person_item is None:
                continue

            person_count = number_utils.get_integer(person_item.text())
            total_person += person_count

            total_fee_item = tableWidget.item(row_no, 2)
            if total_fee_item is None:
                continue

            total_fee_count = number_utils.get_integer(total_fee_item.text())
            total_fee += total_fee_count

            avg_fee = round(total_fee_count / person_count)
            total_avg += avg_fee
            self._set_item_data(self.ui.tableWidget_case_amount, row_no, 3, avg_fee)

        self._set_item_data(self.ui.tableWidget_case_amount, row_count - 1, 0, "合計")
        self._set_item_data(
            self.ui.tableWidget_case_amount, row_count - 1, 1, total_person
        )
        self._set_item_data(
            self.ui.tableWidget_case_amount, row_count - 1, 2, total_fee
        )
        self._set_item_data(
            self.ui.tableWidget_case_amount, row_count - 1, 3, total_avg
        )

    def _set_item_data(self, tableWidget, row_no, col_no, data):
        tableWidget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(data))
        )
        tableWidget.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f"{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}執行業務所得統計表.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_case_amount,
            [],
            [1, 2, 3],
            title=None,
            column_width=[15],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )
