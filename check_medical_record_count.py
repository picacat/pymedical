import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    date_utils,
    log_utils,
    nhi_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 申報檢查 門診次數檢查 2018.01.31
class CheckMedicalRecordCount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = int(args[2])
        self.apply_month = int(args[3])
        self.apply_type = args[4]
        self.treat_limit = args[5]
        self.diag_limit = args[6]
        self.moderate_acupuncture_limit = args[7]
        self.highly_acupuncture_limit = args[8]
        self.moderate_massage_limit = args[9]
        self.highly_massage_limit = args[10]
        self.merge_limit = args[11]
        self.treat_drug_limit = args[12]

        self._error_count = 0

        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self.start_date = date_utils.get_start_date_by_year_month(
            self.apply_year, self.apply_month
        )
        self.end_date = date_utils.get_end_date_by_year_month(
            self.apply_year, self.apply_month
        )
        self.apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)
        self.long_term_care = (
            "(" + ",".join(f"'{x}'" for x in nhi_utils.LONG_TERM_CARE) + ")"
        )

        self._set_ui()
        self._set_signal()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHECK_MEDICAL_RECORD_COUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.tabWidget_medical_record_count.setCurrentIndex(0)
        self._set_table_widget()
        self.ui.label_treat_limit.setText(f"針傷次數限制: {self.treat_limit}次")
        self.ui.label_diag_limit.setText(f"首次次數限制: {self.diag_limit}次")
        self.ui.label_moderate_acupuncture_limit.setText(
            f"中度複雜性針灸限量: {self.moderate_acupuncture_limit}次"
        )
        self.ui.label_highly_acupuncture_limit.setText(
            f"高度複雜性針灸限量: {self.highly_acupuncture_limit}次"
        )
        self.ui.label_moderate_massage_limit.setText(
            f"中度複雜性傷科限量: {self.moderate_massage_limit}次"
        )
        self.ui.label_highly_massage_limit.setText(
            f"高度複雜性傷科限量: {self.highly_massage_limit}次"
        )
        self.ui.label_merge_limit.setText(f"針傷合併限量: {self.merge_limit}次")
        self.ui.label_treat_drug_limit.setText(
            f"針傷給藥限量: {self.treat_drug_limit}次"
        )
        start_date = date_utils.str_to_date(self.start_date)
        last_month = (start_date - datetime.timedelta(days=1)).replace(
            day=1
        )  # 上個月1日
        self.ui.dateEdit_start_date.setDate(last_month)
        self.ui.dateEdit_end_date.setDate(date_utils.str_to_date(self.end_date))

    def _set_table_widget(self):
        self.table_widget_patient_treat = class_utils.get_table_widget(
            self.ui.tableWidget_patient_treat, self.database
        )
        self.table_widget_medical_record_treat = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record_treat, self.database
        )
        self.table_widget_patient_diag = class_utils.get_table_widget(
            self.ui.tableWidget_patient_diag, self.database
        )
        self.table_widget_medical_record_diag = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record_diag, self.database
        )
        self.table_widget_moderate_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_moderate_doctor, self.database
        )
        self.table_widget_moderate_case = class_utils.get_table_widget(
            self.ui.tableWidget_moderate_case, self.database
        )
        self.table_widget_highly_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_highly_doctor, self.database
        )
        self.table_widget_highly_case = class_utils.get_table_widget(
            self.ui.tableWidget_highly_case, self.database
        )
        self.table_widget_moderate_massage_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_moderate_massage_doctor, self.database
        )
        self.table_widget_moderate_massage_case = class_utils.get_table_widget(
            self.ui.tableWidget_moderate_massage_case, self.database
        )
        self.table_widget_highly_massage_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_highly_massage_doctor, self.database
        )
        self.table_widget_highly_massage_case = class_utils.get_table_widget(
            self.ui.tableWidget_highly_massage_case, self.database
        )
        self.table_widget_merge_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_merge_doctor, self.database
        )
        self.table_widget_merge_case = class_utils.get_table_widget(
            self.ui.tableWidget_merge_case, self.database
        )
        self.table_widget_treat_drug_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_treat_drug_doctor, self.database
        )
        self.table_widget_treat_drug_case = class_utils.get_table_widget(
            self.ui.tableWidget_treat_drug_case, self.database
        )

        self.table_widget_medical_record_treat.set_column_hidden([0])
        self.table_widget_medical_record_diag.set_column_hidden([0])
        self.table_widget_moderate_case.set_column_hidden([0])
        self.table_widget_highly_case.set_column_hidden([0])
        self.table_widget_moderate_massage_case.set_column_hidden([0])
        self.table_widget_highly_massage_case.set_column_hidden([0])
        self.table_widget_merge_case.set_column_hidden([0])
        self.table_widget_treat_drug_case.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [90, 100, 90, 90]
        self.table_widget_patient_treat.set_table_heading_width(width)
        self.table_widget_patient_diag.set_table_heading_width(width)

        width = [90, 100, 90]
        self.table_widget_moderate_doctor.set_table_heading_width(width)
        self.table_widget_highly_doctor.set_table_heading_width(width)
        self.table_widget_moderate_massage_doctor.set_table_heading_width(width)
        self.table_widget_highly_massage_doctor.set_table_heading_width(width)
        self.table_widget_merge_doctor.set_table_heading_width(width)
        self.table_widget_treat_drug_doctor.set_table_heading_width(width)

        width = [100, 90, 130, 90, 100, 90, 70, 50, 100, 200, 120, 100, 100, 100]
        self.table_widget_medical_record_treat.set_table_heading_width(width)
        self.table_widget_medical_record_diag.set_table_heading_width(width)
        self.table_widget_moderate_case.set_table_heading_width(width)
        self.table_widget_highly_case.set_table_heading_width(width)
        self.table_widget_moderate_massage_case.set_table_heading_width(width)
        self.table_widget_highly_massage_case.set_table_heading_width(width)
        self.table_widget_merge_case.set_table_heading_width(width)
        self.table_widget_treat_drug_case.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record_treat.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.tableWidget_medical_record_diag.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.tableWidget_moderate_case.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.tableWidget_highly_case.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_moderate_massage_case.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.tableWidget_highly_massage_case.doubleClicked.connect(
            self.open_medical_record
        )
        self.ui.tableWidget_merge_case.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_treat_drug_case.doubleClicked.connect(
            self.open_medical_record
        )

        self.ui.tableWidget_patient_treat.itemSelectionChanged.connect(
            self._patient_treat_changed
        )
        self.ui.tableWidget_patient_diag.itemSelectionChanged.connect(
            self._patient_diag_changed
        )
        self.ui.tableWidget_moderate_doctor.itemSelectionChanged.connect(
            self._moderate_doctor_changed
        )
        self.ui.tableWidget_highly_doctor.itemSelectionChanged.connect(
            self._highly_doctor_changed
        )
        self.ui.tableWidget_moderate_massage_doctor.itemSelectionChanged.connect(
            self._moderate_massage_doctor_changed
        )
        self.ui.tableWidget_highly_massage_doctor.itemSelectionChanged.connect(
            self._highly_massage_doctor_changed
        )
        self.ui.tableWidget_merge_doctor.itemSelectionChanged.connect(
            self._merge_doctor_changed
        )
        self.ui.tableWidget_treat_drug_doctor.itemSelectionChanged.connect(
            self._treat_drug_doctor_changed
        )

        self.ui.tableWidget_patient_treat.keyPressEvent = self._patient_treat_key_press
        self.ui.tableWidget_medical_record_treat.keyPressEvent = (
            self._medical_record_treat_key_press
        )

        self.ui.dateEdit_start_date.dateChanged.connect(
            self._read_medical_record_treat_by_patient
        )
        self.ui.dateEdit_end_date.dateChanged.connect(
            self._read_medical_record_treat_by_patient
        )

        self.ui.toolButton_treat_unapply.clicked.connect(self._set_treat_apply)
        self.ui.toolButton_treat_apply.clicked.connect(self._set_treat_apply)
        self.ui.toolButton_diag_unapply.clicked.connect(self._set_diag_apply)
        self.ui.toolButton_diag_apply.clicked.connect(self._set_diag_apply)

        self.ui.toolButton_acupuncture1.clicked.connect(
            lambda: self._set_acupuncture("中度複雜性針灸")
        )
        self.ui.toolButton_acupuncture2.clicked.connect(
            lambda: self._set_acupuncture("高度複雜性針灸")
        )
        self.ui.toolButton_massage1.clicked.connect(
            lambda: self._set_massage("中度複雜性傷科")
        )  # 2025-04-27
        self.ui.toolButton_massage2.clicked.connect(
            lambda: self._set_massage("高度複雜性傷科")
        )  # 2025-04-27
        self.ui.toolButton_cancel_merge.clicked.connect(self._cancel_merge)

        self.ui.toolButton_complicated1.clicked.connect(
            lambda: self._set_complicated_acupuncture("中度複雜性針灸")
        )  # 恢復中度複雜性針灸
        self.ui.toolButton_complicated2.clicked.connect(
            lambda: self._set_complicated_acupuncture("高度複雜性針灸")
        )  # 恢復高度複雜性針灸
        self.ui.toolButton_complicated3.clicked.connect(
            lambda: self._set_complicated_massage("中度複雜性傷科")
        )  # 恢復中度複雜性傷科 2025-04-27
        self.ui.toolButton_complicated4.clicked.connect(
            lambda: self._set_complicated_massage("高度複雜性傷科")
        )  # 恢復高度複雜性傷科 2025-04-27
        self.ui.toolButton_merge.clicked.connect(self._merge_treat)  # 恢復針傷合併

    def _medical_record_treat_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            self.ui.tableWidget_patient_treat.setFocus()

        return QtWidgets.QTableWidget.keyPressEvent(
            self.ui.tableWidget_medical_record_treat, event
        )

    def _patient_treat_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Right:
            self.ui.tableWidget_medical_record_treat.setFocus()

        return QtWidgets.QTableWidget.keyPressEvent(
            self.ui.tableWidget_patient_treat, event
        )

    def _get_case_key(self, table_widget_name):
        if table_widget_name == "tableWidget_medical_record_treat":
            case_key = self.table_widget_medical_record_treat.field_value(0)
        elif table_widget_name == "tableWidget_medical_record_diag":
            case_key = self.table_widget_medical_record_diag.field_value(0)
        elif table_widget_name == "tableWidget_moderate_case":
            case_key = self.table_widget_moderate_case.field_value(0)
        elif table_widget_name == "tableWidget_highly_case":
            case_key = self.table_widget_highly_case.field_value(0)
        elif table_widget_name == "tableWidget_moderate_massage_case":
            case_key = self.table_widget_moderate_massage_case.field_value(0)
        elif table_widget_name == "tableWidget_highly_massage_case":
            case_key = self.table_widget_highly_massage_case.field_value(0)
        elif table_widget_name == "tableWidget_merge_case":
            case_key = self.table_widget_merge_case.field_value(0)
        elif table_widget_name == "tableWidget_treat_drug_case":
            case_key = self.table_widget_treat_drug_case.field_value(0)

        elif table_widget_name == "toolButton_acupuncture1":
            case_key = self.table_widget_moderate_case.field_value(0)
        elif table_widget_name == "toolButton_acupuncture2":
            case_key = self.table_widget_highly_case.field_value(0)
        elif table_widget_name == "toolButton_massage1":
            case_key = self.table_widget_moderate_massage_case.field_value(0)
        elif table_widget_name == "toolButton_massage2":
            case_key = self.table_widget_highly_massage_case.field_value(0)
        else:
            case_key = None

        return case_key

    def _get_table_widget(self, table_widget_name):
        if table_widget_name == "toolButton_acupuncture1":
            table_widget_case = self.table_widget_moderate_case
        elif table_widget_name == "toolButton_acupuncture2":
            table_widget_case = self.table_widget_highly_case
        elif table_widget_name == "toolButton_acupuncture3":
            table_widget_case = self.table_widget_merge_case

        elif table_widget_name == "toolButton_massage1":
            table_widget_case = self.table_widget_moderate_massage_case
        elif table_widget_name == "toolButton_massage2":
            table_widget_case = self.table_widget_highly_massage_case

        elif table_widget_name == "toolButton_complicated1":
            table_widget_case = self.table_widget_moderate_case
        elif table_widget_name == "toolButton_complicated2":
            table_widget_case = self.table_widget_highly_case
        elif table_widget_name == "toolButton_complicated3":
            table_widget_case = self.table_widget_moderate_massage_case
        elif table_widget_name == "toolButton_complicated4":
            table_widget_case = self.table_widget_highly_massage_case
        elif table_widget_name == "toolButton_merge":
            table_widget_case = self.table_widget_merge_case
        else:
            table_widget_case = None

        return table_widget_case

    def open_medical_record(self):
        case_key = self._get_case_key(self.sender().objectName())
        self.parent.open_medical_record(case_key)

    def start_check(self):
        max_progress = 9
        progress_dialog = QtWidgets.QProgressDialog(
            "正在統計針傷人次資料中, 請稍後...", "取消", 0, max_progress, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self._read_medical_record_treat(self.start_date, self.end_date, 0)
        self._set_total_treat_count()
        progress_dialog.setValue(1)

        self._read_medical_record_diag(0)
        progress_dialog.setValue(2)

        self._read_moderate_acupuncture()
        progress_dialog.setValue(3)

        self._read_highly_acupuncture()
        progress_dialog.setValue(4)

        self._read_moderate_massage()
        progress_dialog.setValue(5)

        self._read_highly_massage()
        progress_dialog.setValue(6)

        self._read_merge()
        progress_dialog.setValue(7)

        self._read_treat_drug()
        progress_dialog.setValue(8)

        self._calculate_avg_count()
        progress_dialog.setValue(9)

        self.ui.tableWidget_medical_record_treat.resizeColumnsToContents()
        self.ui.tableWidget_medical_record_diag.resizeColumnsToContents()
        self.ui.tableWidget_moderate_case.resizeColumnsToContents()
        self.ui.tableWidget_highly_case.resizeColumnsToContents()
        self.ui.tableWidget_moderate_massage_case.resizeColumnsToContents()
        self.ui.tableWidget_highly_massage_case.resizeColumnsToContents()
        self.ui.tableWidget_merge_case.resizeColumnsToContents()
        self.ui.tableWidget_treat_drug_case.resizeColumnsToContents()

        self._set_icon()

    def _calculate_avg_count(self):
        self.label_moderate_acupuncture.setVisible(False)
        self.label_highly_acupuncture.setVisible(False)

        if self.ui.tableWidget_moderate_doctor.rowCount() > 0:
            self._calculate_avg_moderate_acupuncture()

        if self.ui.tableWidget_highly_doctor.rowCount() > 0:
            self._calculate_avg_highly_acupuncture()

        if self.ui.tableWidget_moderate_massage_doctor.rowCount() > 0:
            self._calculate_avg_moderate_massage()

        if self.ui.tableWidget_highly_massage_doctor.rowCount() > 0:
            self._calculate_avg_highly_massage()

        if self.ui.tableWidget_merge_doctor.rowCount() > 0:
            self._calculate_avg_merge()

        if self.ui.tableWidget_treat_drug_doctor.rowCount() > 0:
            self._calculate_avg_treat_drug()

    def _get_doctor_count_sql(self):
        sql = f'''
            SELECT
               Doctor, person.Position
            FROM cases
                LEFT JOIN person ON person.Name = cases.Doctor
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (NOT POSITION(',' IN cases.Doctor) > 0) AND
                ({self.apply_type_sql})
            GROUP BY Doctor
        '''
        return sql

    def _get_doctor_count(self, table_widget_acupuncture):
        doctor_count = 0
        for row_no in range(table_widget_acupuncture.rowCount()):
            position = table_widget_acupuncture.item(row_no, 0).text()
            if position == "支援醫師":
                continue

            doctor_count += 1

        if doctor_count == 0:
            doctor_count = 1

        return doctor_count

    def _get_avg_count(self, table_widget_acupuncture):
        doctor_count = self._get_doctor_count(table_widget_acupuncture)
        person_count = self._get_person_count(table_widget_acupuncture)

        avg_count = person_count / doctor_count

        return doctor_count, person_count, avg_count

    def _calculate_avg_moderate_acupuncture(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_moderate_doctor
        )

        self.label_moderate_acupuncture.setVisible(True)
        self.label_moderate_acupuncture.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _calculate_avg_highly_acupuncture(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_highly_doctor
        )

        self.label_highly_acupuncture.setVisible(True)
        self.label_highly_acupuncture.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _calculate_avg_moderate_massage(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_moderate_massage_doctor
        )

        self.label_moderate_massage.setVisible(True)
        self.label_moderate_massage.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _calculate_avg_highly_massage(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_highly_massage_doctor
        )

        self.label_highly_massage.setVisible(True)
        self.label_highly_massage.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _calculate_avg_merge(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_merge_doctor
        )

        self.label_merge.setVisible(True)
        self.label_merge.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _calculate_avg_treat_drug(self):
        doctor_count, person_count, avg_count = self._get_avg_count(
            self.ui.tableWidget_treat_drug_doctor
        )

        self.label_treat_drug.setVisible(True)
        self.label_treat_drug.setText(
            f"平均人數: {person_count} / {doctor_count} = {avg_count:.1f}"
        )

    def _get_person_count(self, table_widget_doctor):
        person_count = 0

        for row_no in range(table_widget_doctor.rowCount()):
            item = table_widget_doctor.item(row_no, 2)
            if item is None:
                continue

            person_count += number_utils.get_integer(item.text())

        return person_count

    def error_count(self):
        return self._error_count

    def _read_medical_record_treat(self, start_date, end_date, treat_limit):
        sql = f'''
            SELECT
               PatientKey, Name, Count(PatientKey) AS Count
            FROM cases
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IS NOT NULL) AND (LENGTH(Treatment) > 0) AND (Continuance >= 1) AND
                ({self.apply_type_sql})
            GROUP BY PatientKey
            HAVING COUNT(PatientKey) > {treat_limit}
        '''
        self.table_widget_patient_treat.set_db_data(sql, self._set_patient_treat_data)

    def _set_patient_treat_data(self, row_no, row):
        if number_utils.get_integer(row["Count"]) > self.treat_limit:
            exceed_count = number_utils.get_integer(row["Count"]) - self.treat_limit
        else:
            exceed_count = 0

        patient_row = [
            row["PatientKey"],
            string_utils.xstr(row["Name"]),
            row["Count"],
            exceed_count,
        ]

        for col_no in range(len(patient_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, patient_row[col_no])
            self.ui.tableWidget_patient_treat.setItem(row_no, col_no, item)
            if exceed_count > 0:
                self.ui.tableWidget_patient_treat.item(row_no, col_no).setForeground(
                    QtGui.QColor("red")
                )

            if col_no in [0, 2, 3]:
                self.ui.tableWidget_patient_treat.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_medical_record_diag(self, diag_limit):
        sql = f'''
            SELECT
               PatientKey, Name, Count(PatientKey) AS Count
            FROM cases
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                ((Continuance IS NULL) OR (Continuance <= 1)) AND
                ({self.apply_type_sql})
            GROUP BY PatientKey
            HAVING COUNT(PatientKey) > {diag_limit}
        '''
        self.table_widget_patient_diag.set_db_data(sql, self._set_patient_diag_data)

    def _set_patient_diag_data(self, row_no, row):
        if number_utils.get_integer(row["Count"]) > self.diag_limit:
            exceed_count = number_utils.get_integer(row["Count"]) - self.diag_limit
        else:
            exceed_count = 0

        patient_row = [
            row["PatientKey"],
            string_utils.xstr(row["Name"]),
            row["Count"],
            exceed_count,
        ]

        for col_no in range(len(patient_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, patient_row[col_no])
            self.ui.tableWidget_patient_diag.setItem(row_no, col_no, item)
            if exceed_count > 0:
                self.ui.tableWidget_patient_diag.item(row_no, col_no).setForeground(
                    QtGui.QColor("red")
                )

            if col_no in [0, 2, 3]:
                self.ui.tableWidget_patient_diag.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _patient_treat_changed(self):
        self._read_medical_record_treat_by_patient()

    def _read_medical_record_treat_by_patient(self):
        patient_key = self.table_widget_patient_treat.field_value(0)
        if patient_key is None:
            return

        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")

        sql = f'''
            SELECT * FROM cases
            WHERE
                (PatientKey = {patient_key}) AND
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IS NOT NULL) AND (LENGTH(Treatment) > 0) AND (cases.Continuance >= 1)
            ORDER BY CaseDate
        '''

        self.table_widget_medical_record_treat.set_db_data(
            sql, self._set_medical_record_treat_data, resize_rows=False
        )

        self._set_medical_record_treat_color()
        self.ui.tableWidget_medical_record_treat.setCurrentCell(0, 1)
        self.ui.tableWidget_patient_treat.setFocus(True)

    def _set_medical_record_treat_data(self, row_no, row):
        case_key = row["CaseKey"]

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        medical_record_treat = [
            string_utils.xstr(case_key),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for col_no in range(len(medical_record_treat)):
            self.ui.tableWidget_medical_record_treat.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(medical_record_treat[col_no])
            )
            if col_no in [3, 12, 13]:
                self.ui.tableWidget_medical_record_treat.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [7]:
                self.ui.tableWidget_medical_record_treat.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _patient_diag_changed(self):
        patient_key = self.table_widget_patient_diag.field_value(0)

        sql = f'''
            SELECT * FROM cases
            WHERE
                (PatientKey = {patient_key}) AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                ((Continuance IS NULL) OR (Continuance <= 1))
            ORDER BY CaseDate
        '''

        self.table_widget_medical_record_diag.set_db_data(
            sql, self._set_medical_record_diag_data, resize_rows=False
        )
        self._set_medical_record_diag_color()
        self.ui.tableWidget_medical_record_diag.setCurrentCell(0, 1)
        self.ui.tableWidget_patient_diag.setFocus(True)

    def _set_medical_record_diag_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        medical_record_diag = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for column in range(len(medical_record_diag)):
            self.ui.tableWidget_medical_record_diag.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(medical_record_diag[column])
            )
            if column in [3, 8, 13, 14]:
                self.ui.tableWidget_medical_record_diag.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [7]:
                self.ui.tableWidget_medical_record_diag.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _set_medical_record_treat_color(self):
        record_count = 0
        for row_no in range(self.ui.tableWidget_medical_record_treat.rowCount()):
            case_date = self.ui.tableWidget_medical_record_treat.item(row_no, 2).text()
            case_date = datetime.datetime.strptime(case_date, "%Y-%m-%d")
            month = case_date.month
            if case_date < datetime.datetime.strptime(
                self.start_date, "%Y-%m-%d %H:%M:%S"
            ):
                self.table_widget_medical_record_treat.set_row_color(
                    row_no, QtGui.QColor("darkGray")
                )
            else:
                record_count += 1

            self.table_widget_medical_record_treat.set_row_color(
                row_no, QtGui.QColor("black")
            )
            if record_count > self.treat_limit:
                self.table_widget_medical_record_treat.set_row_color(
                    row_no, QtGui.QColor("red")
                )

            apply_type = self.ui.tableWidget_medical_record_treat.item(row_no, 1).text()
            if apply_type == "不申報":
                self.table_widget_medical_record_treat.set_row_color(
                    row_no, QtGui.QColor("darkGray")
                )
            elif month != self.apply_month:
                self.table_widget_medical_record_treat.set_row_color(
                    row_no, QtGui.QColor("lightSlateGrey")
                )

    def _set_medical_record_diag_color(self):
        for row in range(
            self.diag_limit, self.ui.tableWidget_medical_record_diag.rowCount()
        ):
            self.ui.tableWidget_medical_record_diag.setCurrentCell(row, 1)
            self.table_widget_medical_record_diag.set_row_color(
                row, QtGui.QColor("red")
            )
            if self.table_widget_medical_record_diag.field_value(1) == "不申報":
                self.table_widget_medical_record_diag.set_row_color(
                    row, QtGui.QColor("darkGray")
                )

    def _set_treat_apply(self):
        table_widget_name = "tableWidget_medical_record_treat"
        row_no = self.ui.tableWidget_medical_record_treat.currentRow()
        if self.sender().objectName() == "toolButton_treat_unapply":
            apply_type = "不申報"
        else:
            apply_type = "申報"

        case_key = self._get_case_key(table_widget_name)
        self.database.exec_sql(f'''
            UPDATE cases
            SET
                ApplyType = "{apply_type}"
            WHERE
                CaseKey = {case_key}
        ''')
        self.ui.tableWidget_medical_record_treat.setItem(
            self.ui.tableWidget_medical_record_treat.currentRow(),
            1,
            QtWidgets.QTableWidgetItem(apply_type),
        )

        self._set_medical_record_treat_color()
        self.ui.tableWidget_medical_record_treat.setCurrentCell(row_no, 1)
        self.ui.tableWidget_medical_record_treat.setFocus()
        self._set_treat_count()
        self._set_total_treat_count()

    def _set_treat_count(self):
        treat_count = 0
        for row_no in range(self.ui.tableWidget_medical_record_treat.rowCount()):
            case_date = self.ui.tableWidget_medical_record_treat.item(row_no, 2).text()
            case_date = datetime.datetime.strptime(case_date, "%Y-%m-%d")
            month = case_date.month
            if month != self.apply_month:
                continue

            apply_type = self.ui.tableWidget_medical_record_treat.item(row_no, 1).text()
            if apply_type == "申報":
                treat_count += 1

        row_no = self.ui.tableWidget_patient_treat.currentRow()
        self._set_patient_treat_value(row_no, 2, treat_count)

        if treat_count <= self.treat_limit:
            treat_limit = 0
        else:
            treat_limit = treat_count - self.treat_limit

        self._set_patient_treat_value(row_no, 3, treat_limit)

    def _set_total_treat_count(self):
        treat_count = 0
        for row_no in range(self.ui.tableWidget_patient_treat.rowCount()):
            treat_count += number_utils.get_integer(
                self.ui.tableWidget_patient_treat.item(row_no, 2).text()
            )

        self.ui.label_treat_limit.setText(
            f"針傷次數限制: {self.treat_limit}次, 目前針傷總人次: {treat_count}"
        )

    def _set_patient_treat_value(self, row_no, col_no, value):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_patient_treat.setItem(row_no, col_no, item)
        self.ui.tableWidget_patient_treat.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _set_diag_apply(self):
        table_widget_name = "tableWidget_medical_record_diag"
        row_no = self.ui.tableWidget_medical_record_diag.currentRow()
        if self.sender().objectName() == "toolButton_diag_unapply":
            apply_type = "不申報"
        else:
            apply_type = "申報"

        case_key = self._get_case_key(table_widget_name)
        self.database.exec_sql(f'''
            UPDATE cases
            SET
                ApplyType = "{apply_type}"
            WHERE
                CaseKey = {case_key}
        ''')
        self.ui.tableWidget_medical_record_diag.setItem(
            self.ui.tableWidget_medical_record_diag.currentRow(),
            1,
            QtWidgets.QTableWidgetItem(apply_type),
        )

        self._set_medical_record_diag_color()
        self.ui.tableWidget_medical_record_diag.setCurrentCell(row_no, 1)
        self.ui.tableWidget_medical_record_diag.setFocus()

    def _read_moderate_acupuncture(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_moderate_doctor.set_db_data(
            sql, self._set_moderate_doctor_data
        )

    def _read_moderate_acupuncture_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND

                {self._get_case_type_29_condition()} AND

                (Treatment IN {tuple(nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _set_moderate_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_moderate_acupuncture_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_moderate_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_moderate_doctor.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _read_highly_acupuncture(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_highly_doctor.set_db_data(sql, self._set_highly_doctor_data)

    def _read_highly_acupuncture_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND

                {self._get_case_type_29_condition()} AND

                (Treatment IN {tuple(nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _set_highly_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_highly_acupuncture_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_highly_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_highly_doctor.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_merge(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_merge_doctor.set_db_data(sql, self._set_merge_doctor_data)

    def _read_merge_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.MERGE_TREAT_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)
        # count = 0
        # for row in rows:
        #     pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
        #     if pres_days <= 0:
        #         count += 1

        # return count

    def _set_merge_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_merge_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_merge_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_merge_doctor.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_treat_drug(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_treat_drug_doctor.set_db_data(
            sql, self._set_treat_drug_doctor_data
        )

    def _read_treat_drug_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
                LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IS NOT NULL) AND (LENGTH(Treatment) > 0) AND
                (dosage.MedicineSet = 1 AND dosage.Days > 0) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _set_treat_drug_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_treat_drug_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_treat_drug_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_treat_drug_doctor.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _moderate_doctor_changed(self, doctor=None):
        if doctor is None:
            doctor = self.table_widget_moderate_doctor.field_value(1)

        limit = nhi_utils.MAX_MODERATE_COMPLICATED_ACUPUNCTURE

        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                        
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''

        self.table_widget_moderate_case.set_db_data(
            sql, self._set_moderate_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_moderate_case, limit)
        self.ui.tableWidget_moderate_case.setCurrentCell(0, 1)
        self.ui.tableWidget_moderate_case.setFocus(True)
        self.ui.tableWidget_moderate_case.resizeColumnsToContents()

    def _set_moderate_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)

        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        moderate_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for column in range(len(moderate_case_data)):
            self.ui.tableWidget_moderate_case.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(moderate_case_data[column])
            )
            if column in [3, 8, 13, 14]:
                self.ui.tableWidget_moderate_case.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [7]:
                self.ui.tableWidget_moderate_case.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _highly_doctor_changed(self):
        doctor = self.table_widget_highly_doctor.field_value(1)
        limit = nhi_utils.MAX_HIGHLY_COMPLICATED_ACUPUNCTURE

        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''

        self.table_widget_highly_case.set_db_data(
            sql, self._set_highly_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_highly_case, limit)
        self.ui.tableWidget_highly_case.setCurrentCell(0, 1)
        self.ui.tableWidget_highly_case.setFocus(True)
        self.ui.tableWidget_highly_case.resizeColumnsToContents()

    def _merge_doctor_changed(self):
        doctor = self.table_widget_merge_doctor.field_value(1)
        limit = nhi_utils.MAX_MERGE_TREAT

        # 把開藥的醫師排除
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.MERGE_TREAT_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseKey
        '''
        # rows = self.database.select_record(sql)
        # case_key_list = []
        # for row in rows:
        #     pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
        #     if pres_days <= 0:
        #         case_key_list.append(row['CaseKey'])

        # if len(case_key_list) <= 0:
        #     self.ui.tableWidget_merge_case.setRowCount(0)
        #     return

        # sql = f'''
        #     SELECT * FROM cases
        #     WHERE
        #         (cases.CaseKey IN {tuple(case_key_list)})
        #     ORDER BY CaseDate
        # '''

        self.table_widget_merge_case.set_db_data(
            sql, self._set_merge_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_merge_case, limit)
        self.ui.tableWidget_merge_case.setCurrentCell(0, 1)
        self.ui.tableWidget_merge_case.setFocus(True)
        self.ui.tableWidget_merge_case.resizeColumnsToContents()

    def _treat_drug_doctor_changed(self):
        doctor = self.table_widget_treat_drug_doctor.field_value(1)
        limit = nhi_utils.MAX_TREAT_DRUG

        sql = f'''
            SELECT * FROM cases
                LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IS NOT NULL AND LENGTH(Treatment) > 0) AND
                (dosage.MedicineSet = 1 AND dosage.Days > 0) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        self.table_widget_treat_drug_case.set_db_data(
            sql, self._set_treat_drug_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_treat_drug_case, limit)
        self.ui.tableWidget_treat_drug_case.setCurrentCell(0, 1)
        self.ui.tableWidget_treat_drug_case.setFocus(True)

    def _set_highly_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        highly_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for column in range(len(highly_case_data)):
            self.ui.tableWidget_highly_case.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(highly_case_data[column])
            )
            if column in [3, 8, 13, 14]:
                self.ui.tableWidget_highly_case.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [7]:
                self.ui.tableWidget_highly_case.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _set_merge_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        merge_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
        ]

        for col_no in range(len(merge_case_data)):
            self.ui.tableWidget_merge_case.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(merge_case_data[col_no])
            )
            if col_no in [3, 8]:
                self.ui.tableWidget_merge_case.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [7]:
                self.ui.tableWidget_merge_case.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _set_treat_drug_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        treat_drug_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
        ]

        for col_no in range(len(treat_drug_case_data)):
            self.ui.tableWidget_treat_drug_case.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(treat_drug_case_data[col_no])
            )
            if col_no in [3, 8]:
                self.ui.tableWidget_treat_drug_case.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [7]:
                self.ui.tableWidget_treat_drug_case.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    @staticmethod
    def _set_case_color(table_widget_case, limit):
        for row in range(limit, table_widget_case.row_count()):
            table_widget_case.set_current_cell(row, 1)
            table_widget_case.set_row_color(row, QtGui.QColor("red"))

    def _set_icon(self):
        self._set_treat_count_icon()
        self._set_diag_count_icon()
        self._set_moderate_acupuncture_count_icon()
        self._set_highly_acupuncture_count_icon()
        self._set_moderate_massage_count_icon()
        self._set_highly_massage_count_icon()
        self._set_merge_count_icon()
        self._set_treat_drug_count_icon()

        # self.tab_icon_list = []

        # table_widget_list = [
        #     self.ui.tableWidget_patient_treat,
        #     self.ui.tableWidget_patient_diag,
        #     self.ui.tableWidget_moderate_doctor,
        #     self.ui.tableWidget_highly_doctor,
        # ]

        # self.error_count_list = []
        # for i, table in enumerate(table_widget_list):
        #     icon = ui_utils.ICON_OK
        #     if table.rowCount() > 0:
        #         self.error_count_list.append(table.rowCount())
        #         icon = ui_utils.ICON_NO

        #     self.ui.tabWidget_medical_record_count.setTabIcon(i, icon)

    def _set_treat_count_icon(self):
        icon = ui_utils.ICON_OK

        for row_no in range(self.ui.tableWidget_patient_treat.rowCount()):
            exceed_count = number_utils.get_integer(
                self.ui.tableWidget_patient_treat.item(row_no, 3).text()
            )
            if exceed_count > 0:
                self._error_count += 1
                icon = ui_utils.ICON_NO
                break

        self.ui.tabWidget_medical_record_count.setTabIcon(0, icon)

    def _set_diag_count_icon(self):
        icon = ui_utils.ICON_OK

        for row_no in range(self.ui.tableWidget_patient_diag.rowCount()):
            exceed_count = number_utils.get_integer(
                self.ui.tableWidget_patient_diag.item(row_no, 3).text()
            )
            if exceed_count > 0:
                self._error_count += 1
                icon = ui_utils.ICON_NO
                break

        self.ui.tabWidget_medical_record_count.setTabIcon(1, icon)

    def _set_moderate_acupuncture_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(self.ui.tableWidget_moderate_doctor)
        if avg_count > self.moderate_acupuncture_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(2, icon)

    def _set_highly_acupuncture_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(self.ui.tableWidget_highly_doctor)
        if avg_count > self.highly_acupuncture_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(3, icon)

    def _set_moderate_massage_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(
            self.ui.tableWidget_moderate_massage_doctor
        )
        if avg_count > self.moderate_massage_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(4, icon)

    def _set_highly_massage_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(self.ui.tableWidget_highly_massage_doctor)
        if avg_count > self.highly_massage_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(5, icon)

    def _set_merge_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(self.ui.tableWidget_merge_doctor)
        if avg_count > self.merge_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(6, icon)

    def _set_treat_drug_count_icon(self):
        icon = ui_utils.ICON_OK

        _, _, avg_count = self._get_avg_count(self.ui.tableWidget_treat_drug_doctor)
        if avg_count > self.treat_drug_limit:
            self._error_count += 1
            icon = ui_utils.ICON_NO

        self.ui.tabWidget_medical_record_count.setTabIcon(7, icon)

    def _set_acupuncture(self, origin_treat_type):
        table_widget_case = self._get_table_widget(self.sender().objectName())
        case_key = table_widget_case.field_value(0)
        case_date = table_widget_case.field_value(2)
        patient_key = table_widget_case.field_value(3)
        name = table_widget_case.field_value(4)
        treatment = "一般針灸"

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treatment}",
                TreatType = "{treatment}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"轉換病歷號{patient_key}{name} {case_date}的{origin_treat_type}為{treatment}",
        )

        row_no = table_widget_case.current_row()
        table_widget_case.set_item_text(row_no, 5, treatment, align=QtCore.Qt.AlignLeft)
        table_widget_case.set_item_text(
            row_no, 11, treatment, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_row_color(row_no, QtGui.QColor("blue"))
        table_widget_case.set_focus()

    def _set_massage(self, origin_treat_type):
        table_widget_case = self._get_table_widget(self.sender().objectName())
        case_key = table_widget_case.field_value(0)
        case_date = table_widget_case.field_value(2)
        patient_key = table_widget_case.field_value(3)
        name = table_widget_case.field_value(4)
        treatment = "一般傷科"

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treatment}",
                TreatType = "{treatment}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"轉換病歷號{patient_key}{name} {case_date}的{origin_treat_type}為{treatment}",
        )

        row_no = table_widget_case.current_row()
        table_widget_case.set_item_text(row_no, 5, treatment, align=QtCore.Qt.AlignLeft)
        table_widget_case.set_item_text(
            row_no, 11, treatment, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_row_color(row_no, QtGui.QColor("blue"))
        table_widget_case.set_focus()

    def _cancel_merge(self):
        table_widget_merge_case = self.table_widget_merge_case
        origin_treat_type = table_widget_merge_case.field_value(5)
        if "合併" not in origin_treat_type:
            return

        case_key = table_widget_merge_case.field_value(0)
        case_date = table_widget_merge_case.field_value(2)
        patient_key = table_widget_merge_case.field_value(3)
        name = table_widget_merge_case.field_value(4)

        if "中度針灸" in origin_treat_type:
            treatment = "中度複雜性針灸"
        elif "高度針灸" in origin_treat_type:
            treatment = "高度複雜性針灸"
        else:
            treatment = "一般針灸"

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treatment}",
                TreatType = "{treatment}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"取消病歷號{patient_key}{name} {case_date}的{origin_treat_type}為{treatment}",
        )

        row_no = table_widget_merge_case.current_row()
        table_widget_merge_case.set_item_text(
            row_no, 5, treatment, align=QtCore.Qt.AlignLeft
        )
        table_widget_merge_case.set_item_text(
            row_no, 11, treatment, align=QtCore.Qt.AlignLeft
        )
        table_widget_merge_case.set_row_color(row_no, QtGui.QColor("blue"))
        table_widget_merge_case.set_focus()

    def _set_complicated_acupuncture(self, treat_type):
        table_widget_case = self._get_table_widget(self.sender().objectName())
        case_key = table_widget_case.field_value(0)
        case_date = table_widget_case.field_value(2)
        patient_key = table_widget_case.field_value(3)
        name = table_widget_case.field_value(4)
        # treat_type = table_widget_case.field_value(5)

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treat_type}",
                TreatType = "{treat_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"轉換病歷號{patient_key}{name} {case_date}的一般針灸為{treat_type}",
        )

        row_no = table_widget_case.current_row()
        table_widget_case.set_item_text(
            row_no, 5, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_item_text(
            row_no, 11, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_row_color(row_no, QtGui.QColor("red"))
        table_widget_case.set_focus()

    def _set_complicated_massage(self, treat_type):
        table_widget_case = self._get_table_widget(self.sender().objectName())
        case_key = table_widget_case.field_value(0)
        if case_key is None:
            return

        case_date = table_widget_case.field_value(2)
        patient_key = table_widget_case.field_value(3)
        name = table_widget_case.field_value(4)

        sql = """
            UPDATE cases
            SET
                Treatment = %s, TreatType = %s
            WHERE
                CaseKey = %s
        """
        params = (treat_type, treat_type, case_key)
        self.database.exec_sql(sql, params=params)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"轉換病歷號{patient_key}{name} {case_date}的一般傷科為{treat_type}",
        )

        row_no = table_widget_case.current_row()
        table_widget_case.set_item_text(
            row_no, 5, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_item_text(
            row_no, 11, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_row_color(row_no, QtGui.QColor("red"))
        table_widget_case.set_focus()

    def _merge_treat(self):
        table_widget_case = self._get_table_widget(self.sender().objectName())
        original_treat_type = table_widget_case.field_value(5)
        if original_treat_type is not None and "合併" in original_treat_type:
            return

        case_key = table_widget_case.field_value(0)
        case_date = table_widget_case.field_value(2)
        patient_key = table_widget_case.field_value(3)
        name = table_widget_case.field_value(4)
        if "中度複雜性針灸" in original_treat_type:
            treat_type = "中度針灸合併一般傷科"
        elif "高度複雜性針灸" in original_treat_type:
            treat_type = "高度針灸合併一般傷科"
        else:
            treat_type = "一般針灸合併一般傷科"

        sql = f'''
            UPDATE cases
            SET
                Treatment = "{treat_type}",
                TreatType = "{treat_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

        charge_utils.calculate_ins_fee(self.database, self.system_settings, case_key)
        log_utils.write_event_log(
            self.database,
            self.user_name,
            "病歷修正",
            "申報檢查-門診次數檢查",
            f"{self.user_name}於{date_utils.now_to_str()}"
            f"轉換病歷號{patient_key}{name} {case_date}的{original_treat_type}為{treat_type}",
        )

        row_no = table_widget_case.current_row()
        table_widget_case.set_item_text(
            row_no, 5, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_item_text(
            row_no, 11, treat_type, align=QtCore.Qt.AlignLeft
        )
        table_widget_case.set_row_color(row_no, QtGui.QColor("red"))
        table_widget_case.set_focus()

    ###################################################################################################################
    # 2025-04-27 新增中度傷科, 高度傷科次數檢查 2025-05-01 生效
    ###################################################################################################################
    def _read_moderate_massage(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_moderate_massage_doctor.set_db_data(
            sql, self._set_moderate_massage_doctor_data
        )

    def _read_moderate_massage_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND

                {self._get_case_type_29_condition()} AND

                (Treatment IN {tuple(nhi_utils.MODERATE_COMPLICATED_MASSAGE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _set_moderate_massage_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_moderate_massage_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_moderate_massage_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_moderate_massage_doctor.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _read_highly_massage(self):
        sql = self._get_doctor_count_sql()
        self.table_widget_highly_massage_doctor.set_db_data(
            sql, self._set_highly_massage_doctor_data
        )

    def _read_highly_massage_count(self, doctor):
        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND

                {self._get_case_type_29_condition()} AND

                (Treatment IN {tuple(nhi_utils.HIGHLY_COMPLICATED_MASSAGE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _set_highly_massage_doctor_data(self, row_no, row):
        doctor = string_utils.xstr(row["Doctor"])
        count = self._read_highly_massage_count(doctor)

        doctor_row = [
            string_utils.xstr(row["Position"]),
            doctor,
            count,
        ]

        for col_no in range(len(doctor_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, doctor_row[col_no])
            self.ui.tableWidget_highly_massage_doctor.setItem(row_no, col_no, item)
            if col_no in [2]:
                self.ui.tableWidget_highly_massage_doctor.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _moderate_massage_doctor_changed(self, doctor=None):
        if doctor is None:
            doctor = self.table_widget_moderate_massage_doctor.field_value(1)

        limit = nhi_utils.MAX_MODERATE_COMPLICATED_MASSAGE

        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                        
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.MODERATE_COMPLICATED_MASSAGE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''

        self.table_widget_moderate_massage_case.set_db_data(
            sql, self._set_moderate_massage_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_moderate_case, limit)
        self.ui.tableWidget_moderate_massage_case.setCurrentCell(0, 1)
        self.ui.tableWidget_moderate_massage_case.setFocus(True)
        self.ui.tableWidget_moderate_massage_case.resizeColumnsToContents()

    def _set_moderate_massage_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)

        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        moderate_massage_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for column in range(len(moderate_massage_case_data)):
            self.ui.tableWidget_moderate_massage_case.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(moderate_massage_case_data[column]),
            )
            if column in [3, 8, 13, 14]:
                self.ui.tableWidget_moderate_massage_case.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [7]:
                self.ui.tableWidget_moderate_massage_case.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _highly_massage_doctor_changed(self):
        doctor = self.table_widget_highly_massage_doctor.field_value(1)
        limit = nhi_utils.MAX_HIGHLY_COMPLICATED_MASSAGE

        sql = f'''
            SELECT * FROM cases
            WHERE
                (Doctor = "{doctor}") AND
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
                (cases.RegistType NOT IN {self.long_term_care}) AND                
                (cases.Share NOT IN ("山地離島")) AND
                (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
                (Treatment IN {tuple(nhi_utils.HIGHLY_COMPLICATED_MASSAGE_LIST)}) AND
                ({self.apply_type_sql})
            ORDER BY CaseDate
        '''

        self.table_widget_highly_massage_case.set_db_data(
            sql, self._set_highly_massage_case_data, resize_rows=False
        )
        self._set_case_color(self.table_widget_highly_massage_case, limit)
        self.ui.tableWidget_highly_massage_case.setCurrentCell(0, 1)
        self.ui.tableWidget_highly_massage_case.setFocus(True)
        self.ui.tableWidget_highly_massage_case.resizeColumnsToContents()

    def _set_highly_massage_case_data(self, row_no, row):
        case_key = row["CaseKey"]
        pres_days = case_utils.get_pres_days(self.database, case_key)
        if pres_days <= 0:
            pres_days = ""

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        disease_name = case_utils.get_disease_name_all(row)
        highly_massage_case_data = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["ApplyType"]),
            f"{year}-{month:0>2}-{day:0>2}",
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Card"]),
            string_utils.xstr(row["Continuance"]),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["DiseaseCode1"]),
            disease_name,
            string_utils.xstr(row["Treatment"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiagFee"]),
            string_utils.xstr(
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
            ),
        ]

        for column in range(len(highly_massage_case_data)):
            self.ui.tableWidget_highly_massage_case.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(highly_massage_case_data[column]),
            )
            if column in [3, 8, 13, 14]:
                self.ui.tableWidget_highly_massage_case.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [7]:
                self.ui.tableWidget_highly_massage_case.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _get_case_type_29_condition(self):
        """
        建立對應案件分類 29 (一般針傷脫臼處置) 的共用篩選條件
        比照 nhi_utils.get_case_type() 的判斷邏輯
        """
        return f"""
            (cases.Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
            (cases.Injury != "法定傳染病通報隔離") AND
            (cases.TreatType NOT IN {tuple(nhi_utils.ALL_CARE_TREAT)}) AND
            (cases.RegistType NOT IN {self.long_term_care}) AND
            (cases.RegistType NOT IN {tuple(nhi_utils.TOUR_TYPE)}) AND
            (cases.RegistType != "資源不足開業") AND
            (cases.Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡") AND
            (cases.Continuance >= 1)
        """
