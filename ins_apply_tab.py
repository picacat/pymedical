# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import module_utils, nhi_utils, string_utils, system_utils, ui_utils


# 健保申報資料 2018.01.31
class InsApplyTab(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.period = args[4]
        self.apply_type = args[5]
        self.clinic_id = args[6]
        self.months = args[7]
        self.ins_list = args[8]
        self.ui = None

        if self.ins_list is None:
            self.apply_date = nhi_utils.get_apply_date(
                self.apply_year, self.apply_month
            )
            self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

        self.show_warning = False

        self._set_ui()
        self._set_signal()
        self._add_ins_apply_list()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_TAB, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        pass

    def _get_judge_sql(self):
        sql_condition = []
        for row in self.ins_list:
            apply_date = row[2]
            apply_date = str(int(apply_date[:4]) - 1911) + apply_date[4:6]
            case_type = row[5]
            sequence = row[6]
            sql_condition.append(
                f'(ApplyDate = "{apply_date}" AND CaseType = "{case_type}" AND Sequence = {sequence})'
            )

        sql = f"""
            SELECT * FROM insapply
            WHERE
                {" OR ".join(sql_condition)}
        """
        return sql

    def _add_ins_apply_list(self):
        if self.ins_list is not None:
            sql = self._get_judge_sql()
            sql += " GROUP BY CaseType"
        else:
            sql = f'''
                SELECT * FROM insapply
                WHERE
                    ApplyDate = "{self.apply_date}" AND
                    ApplyType = "{self.apply_type_code}" AND
                    ApplyPeriod = "{self.period}" AND
                    ClinicID = "{self.clinic_id}"
                GROUP BY CaseType
            '''

        rows = self.database.select_record(sql)
        for row in rows:
            case_type = string_utils.xstr(row["CaseType"])
            tab_ins_apply_list = module_utils.get_ins_apply_list(
                self,
                self.database,
                self.system_settings,
                self.apply_year,
                self.apply_month,
                self.period,
                self.apply_type,
                self.clinic_id,
                case_type,
                self.months,
                ins_list=self.ins_list,
            )
            self.ui.tabWidget_ins_apply.addTab(
                tab_ins_apply_list, f"案件分類-{case_type}"
            )

        self._set_tab_icon()

        if self.show_warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("申報檔有誤")
            msg_box.setText(
                "<font size='4' color='red'><b>申報檔有錯誤, 請至申報檢查完成錯誤檢查流程.</b></font>"
            )
            msg_box.setInformativeText("錯誤未全部更正前, 請勿申報上傳, 以免遭到退件.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()

        self._add_ins_judge_list()

    def _add_ins_judge_list(self):
        if self.ins_list is not None:
            sql = self._get_judge_sql()
            sql += " GROUP BY CaseType, Sequence"
        else:
            sql = f'''
                SELECT * FROM insapply
                WHERE
                    ApplyDate = "{self.apply_date}" AND
                    ApplyType = "{self.apply_type_code}" AND
                    ApplyPeriod = "{self.period}" AND
                    ClinicID = "{self.clinic_id}" AND
                    Note = "*"
                GROUP BY CaseType, Sequence
            '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        tab_ins_judge_list = module_utils.get_ins_apply_list(
            self,
            self.database,
            self.system_settings,
            self.apply_year,
            self.apply_month,
            self.period,
            self.apply_type,
            self.clinic_id,
            "抽審",
            self.months,
            ins_list=self.ins_list,
        )
        self.ui.tabWidget_ins_apply.addTab(tab_ins_judge_list, "註記名單")

        i = self.ui.tabWidget_ins_apply.count() - 1
        self.ui.tabWidget_ins_apply.setTabIcon(i, ui_utils.ICON_EYE)

    def _set_tab_icon(self):
        tab_icon_list = [
            ui_utils.ICON_OK for i in range(self.ui.tabWidget_ins_apply.count())
        ]

        for i in range(self.ui.tabWidget_ins_apply.count()):
            tab = self.ui.tabWidget_ins_apply.widget(i)

            if tab.error_count > 0:
                tab_icon_list[i] = ui_utils.ICON_NO
                self.show_warning = True

        for i, icon in enumerate(tab_icon_list):
            self.ui.tabWidget_ins_apply.setTabIcon(i, icon)

    def open_medical_record(self, case_key):
        self.parent.open_medical_record(case_key)

    def export_ins_order(self):
        tab = self.ui.tabWidget_ins_apply.currentWidget()
        tab.print_order(print_type="pdf_by_dialog")

    def export_medical_record(self):
        tab = self.ui.tabWidget_ins_apply.currentWidget()
        tab.print_medical_records(print_type="pdf_by_dialog")

    def export_medical_chart(self):
        tab = self.ui.tabWidget_ins_apply.currentWidget()
        tab.print_medical_chart(print_type="pdf_by_dialog")
