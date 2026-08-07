import os

from PyQt5 import QtCore, QtWidgets

from libs import charge_utils, date_utils, system_utils, update_utils

UPDATE_RECORD_LOG = "update_records.log"

# 允許自動清除的殘骸表（錯誤 1932：.frm 還在，但引擎裡沒有資料實體）
#
# 這種表任何讀寫都會拋 1932，備份也會失敗。麻煩的是 information_schema
# 看得到它，所以「不存在就自動建立」的判斷會被 .frm 騙過去，這個狀態會
# 永遠卡住，不會自己好。
#
# 只加入「刪掉之後由系統重建空表即可、不含需要保留的歷史資料」的表。
# 【絕對不要】加入 cases、patient、prescript、dosage、insapply 等
# 病歷與申報相關資料表——那類表出問題應該走災難復原流程
# （停機、完整備份資料目錄、嘗試 IMPORT TABLESPACE 或從備份還原），
# 不該由程式自動刪除。
ORPHAN_CHECK_TABLES = [
    "returngoods",
    "insappeal",
]


# 系統設定 2018.03.19
class CheckDatabase(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]

        self._set_ui()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_ui(self):
        system_utils.center_window(self)

    # 檢查資料庫狀態
    def check_database(self):
        self._drop_wrong_tables()
        self._alter_table()
        self._correct_records()
        self._check_additional_records()
        update_utils.update_database(self.parent, self.database)

    def _drop_wrong_tables(self):
        try:
            self.database.exec_sql("DROP TABLE IF EXISTS insreply")
        except Exception:
            print("error: DROP TABLE IF EXISTS insreply")

        try:
            self.database.exec_sql("DROP TABLE IF EXISTS `ReturnGoods`")
        except Exception:
            pass

        try:
            self.database.exec_sql("DROP TABLE IF EXISTS `checklist`")
        except Exception:
            pass

        try:
            self.database.exec_sql("DROP TABLE IF EXISTS `chargeregist`")
        except Exception:
            pass

    def _alter_table(self):
        self._check_orphan_tables()

        max_progress = 61
        self.progress = 0
        self.progress_dialog = QtWidgets.QProgressDialog(
            "正在檢查資料庫中, 請稍後...", "取消", 0, max_progress, self
        )
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)

        self._check_patient()
        self._check_cases()
        self._check_dosage()
        self._check_prescript()
        self._check_medicine()
        self._check_person()
        self._check_icd10()
        self._check_reserve()
        self._check_wait()
        self._check_deposit()
        self._check_debt()
        self._check_clinic()
        self._check_certificate()
        self._check_others()
        self._check_ins_apply()

        self.progress_dialog.deleteLater()

    def _exec_process(self, process_list):
        for _ in process_list:  # process execute here
            self.progress += 1
            self.progress_dialog.setValue(self.progress)

    def _check_patient_index(self):
        index_name = "idx_select_optimization"
        fields = (
            "Name",
            "ID",
            "Telephone",
            "Cellphone",
        )
        self.database.add_index_if_not_exists("patient", index_name, fields)

    def _check_patient(self):
        try:
            self._check_patient_index()
        except Exception:
            pass

        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "patient",
                    "add",
                    "FamilyPatientKey",
                    "varchar(10) AFTER PrivateInsurance",
                ),
                self.database.check_field_exists(
                    "patient",
                    "add",
                    "EmergencyContact",
                    "varchar(20) AFTER FamilyPatientKey",
                ),
                self.database.check_field_exists(
                    "patient",
                    "add",
                    "EmergencyContactPhone",
                    "varchar(40) AFTER EmergencyContact",
                ),
                self.database.check_field_exists(
                    "patient",
                    "add",
                    "EmergencyRelevant",
                    "varchar(100) AFTER EmergencyContactPhone",
                ),
                self.database.check_field_exists(
                    "patient", "add", "BloodType", "varchar(10) AFTER Gender"
                ),
                self.database.check_field_exists(
                    "patient_assessment",
                    "add",
                    "UploadFileName",
                    "varchar(30) AFTER UploadDate",
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "patient", "add", "Gender", "varchar(4) AFTER Nationality"
                ),
                self.database.check_field_exists(
                    "patient", "add", "Description", "text AFTER History"
                ),
                self.database.check_field_exists(
                    "patient", "add", "Allergy", "text AFTER Alergy"
                ),
                self.database.check_field_exists(
                    "patient", "change", ["EMail", "Email"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "patient", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "patient", "change", ["RegistNo", "ChartNo"], "varchar(10)"
                ),
                self.database.check_field_exists(
                    "patient", "add", "NursingHome", "varchar(50) after Allergy"
                ),
                self.database.check_field_exists(
                    "patient", "add", "NursingHomeID", "varchar(20) after NursingHome"
                ),
                self.database.check_field_exists(
                    "patient",
                    "add",
                    "NursingHomeInDate",
                    "varchar(10) after NursingHomeID",
                ),
            ]

        self._exec_process(process_list)

    def _check_cases_index(self):
        index_name = "idx_select_optimization"
        fields = (
            "Period",
            "RegistType",
            "InsType",
            "TreatType",
            "Doctor",
            "DoctorDone",
        )
        self.database.add_index_if_not_exists("cases", index_name, fields)
        self.database.add_index_if_not_exists("cases", "idx_case_date", ["CaseDate"])

    def _check_cases_thc_index(self):
        index_name = "idx_thc_position1"
        fields = (
            "TreatType",
            "Position1",
        )
        self.database.add_index_if_not_exists("cases", index_name, fields)
        self.database.add_index_if_not_exists(
            "caseextend", "idx_case_type", ["CaseKey", "ExtendType"]
        )

    def _check_cases(self):
        try:
            self._check_cases_index()
        except Exception:
            pass

        try:
            self._check_cases_thc_index()
        except Exception:
            pass

        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "cases", "add", "DebtFee", "int AFTER Debt"
                ),
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "RegistPaymentType",
                    'varchar(20) DEFAULT "現金" AFTER DebtFee',
                ),
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "ChargePaymentType",
                    'varchar(20) DEFAULT "現金" AFTER RegistPaymentType',
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiseaseCode4", "varchar(10) AFTER DiseaseName3"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiseaseName4", "varchar(40) AFTER DiseaseCode4"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiseaseCode5", "varchar(10) AFTER DiseaseName4"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiseaseName5", "varchar(40) AFTER DiseaseCode5"
                ),
                self.database.check_field_exists(
                    "cases", "add", "RegistTypex", "varchar(10) AFTER RegistType"
                ),
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "DrugPickupDone",
                    'ENUM("False", "True") NOT NULL DEFAULT "False" AFTER DrugDone',
                ),
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "IsClosed",
                    "tinyint(1) NOT NULL DEFAULT 0 AFTER Security",
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "cases", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DoctorDate", "datetime AFTER CaseDate"
                ),
                self.database.check_field_exists(
                    "cases", "add", "PharmacyType", "varchar(10) AFTER ApplyType"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DebtFee", "int AFTER Debt"
                ),
                self.database.check_field_exists(
                    "cases", "add", "SDiagShareFee", "int AFTER ReceiptShare"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiagShareFee", "int AFTER TreatShare"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DrugShareFee", "int AFTER DrugShare"
                ),
                self.database.check_field_exists(
                    "cases", "add", "Cashier", "varchar(10) AFTER Casher"
                ),
                self.database.check_field_exists(
                    "cases", "add", "RefundFee", "int AFTER Refund"
                ),
                self.database.check_field_exists(
                    "cases", "add", "SMaterialFee", "int AFTER SMaterial"
                ),
                self.database.check_field_exists(
                    "cases", "add", "ChargePeriod", "varchar(4) AFTER Period"
                ),
                self.database.check_field_exists(
                    "cases", "add", "ChargeDate", "datetime AFTER DoctorDate"
                ),
                self.database.check_field_exists(
                    "cases", "add", "DiscountRate", "int DEFAULT 100 AFTER DiscountFee"
                ),
                self.database.check_field_exists(
                    "cases", "add", "TourArea", "varchar(20) AFTER RegistType"
                ),
                self.database.check_field_exists(
                    "cases", "add", "InvoiceNo", "varchar(20) AFTER Security"
                ),
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "DesignatedDoctor",
                    'ENUM("False", "True") NOT NULL AFTER DrugDone',
                ),  # 指定醫師
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "DesignatedDoctor",
                    'ENUM("False", "True") NOT NULL AFTER DrugDone',
                ),  # 指定醫師
                self.database.check_field_exists(
                    "cases",
                    "add",
                    "DesignatedMassager",
                    'ENUM("False", "True") NOT NULL AFTER DesignatedDoctor',
                ),  # 指定醫師
                self.database.check_field_exists(
                    "cases", "add", "CurativeEffect", "int AFTER Cure"
                ),
                self.database.check_field_exists(
                    "cases", "add", "TreatType", "varchar(100) AFTER RegistType"
                ),
                self.database.check_field_exists(
                    "cases", "change", ["TreatType", "TreatType"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "cases", "change", ["Treatment", "Treatment"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "cases", "add", "NursingAssistant", "varchar(20) AFTER Cashier"
                ),
                self.database.check_field_exists(
                    "cases", "add", "MassageReferrer", "varchar(20) AFTER Cashier"
                ),
                self.database.check_field_exists(
                    "cases", "change", ["Card", "Card"], "varchar(15)"
                ),
                self.database.check_field_exists(
                    "cases", "change", ["Injury", "Injury"], "varchar(50)"
                ),
                self.database.check_field_exists(
                    "cases", "change", ["Share", "Share"], "varchar(50)"
                ),
            ]

        self._exec_process(process_list)

    def _check_dosage(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "dosage", "add", "TotalDosage", "double(6,2) AFTER Days"
                ),
                self.database.check_field_exists(
                    "dosage", "add", "TotalDosage", "double(6,2) AFTER Days"
                ),
                self.database.check_field_exists(
                    "dosage", "add", "FreeInsMedicine", "varchar(4) AFTER Amount"
                ),
                self.database.check_field_exists(
                    "dosage", "add", "NoPharmacy", "varchar(4) AFTER FreeInsMedicine"
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "dosage", "add", "SelfTotalFee", "int AFTER Instruction"
                ),
                self.database.check_field_exists(
                    "dosage",
                    "add",
                    "DiscountRate",
                    "int DEFAULT 100 AFTER SelfTotalFee",
                ),
                self.database.check_field_exists(
                    "dosage", "add", "DiscountFee", "int AFTER DiscountRate"
                ),
                self.database.check_field_exists(
                    "dosage", "add", "TotalFee", "int AFTER DiscountFee"
                ),
                self.database.check_field_exists(
                    "dosage", "add", "FreeInsMedicine", "varchar(4) AFTER Amount"
                ),
            ]

        self._exec_process(process_list)
        self.database.add_index_if_not_exists(
            "dosage", "idx_case_set", ["CaseKey", "MedicineSet"]
        )

    def _check_prescript_index(self):
        index_name = "idx_update_optimization"
        fields = ("MedicineSet", "CaseDate", "MedicineKey")
        self.database.add_index_if_not_exists("prescript", index_name, fields)

    def _check_prescript(self):
        try:
            self._check_prescript_index()
        except Exception:
            pass

        if self.call_from == "pymedical":
            process_list = []
        else:
            process_list = [
                self.database.check_field_exists(
                    "prescript", "add", "PrescriptNo", "int AFTER PrescriptKey"
                ),
                self.database.check_field_exists(
                    "prescript", "add", "DosageMode", "varchar(10) AFTER MedicineName"
                ),
                self.database.check_field_exists(
                    "prescript", "change", ["price", "Price"], "decimal(10,2)"
                ),
                self.database.check_field_exists(
                    "prescript", "change", ["amount", "Amount"], "decimal(10,2)"
                ),
                self.database.check_field_exists(
                    "prescript",
                    "change",
                    ["MedicineType", "MedicineType"],
                    "varchar(10)",
                ),
                self.database.check_field_exists(
                    "prescript", "add", "DiscountFee", "decimal(10,2) AFTER Price"
                ),
                self.database.check_field_exists(
                    "prescript", "add", "Promotion", "varchar(10) AFTER Amount"
                ),
                self.database.check_field_exists(
                    "prescript", "add", "Debt", "decimal(10,2) AFTER DiscountFee"
                ),
                self.database.check_field_exists(
                    "prescript", "add", "Dealer", "varchar(10) AFTER Amount"
                ),
                self.database.check_field_exists(
                    "prescript", "add", "Remark", "varchar(200) AFTER Promotion"
                ),
            ]

        self._exec_process(process_list)

    def _check_medicine_index(self):
        index_name = "idx_select_optimization"
        fields = ("MedicineType", "InputCode", "InsCode", "MedicineName", "DrugName")
        self.database.add_index_if_not_exists("medicine", index_name, fields)

    def _check_medicine(self):
        try:
            self._check_medicine_index()
        except Exception:
            pass

        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "medicine", "add", "Charged", "varchar(4) AFTER InPrice"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "NoDosage", "varchar(4) AFTER Charged"
                ),  # 不計算總量
                self.database.check_field_exists(
                    "medicine", "add", "NonNHI", "varchar(4) AFTER NoDosage"
                ),  # 僅用於自費
                self.database.check_field_exists(
                    "medicine", "add", "MinDosage", "decimal(10,2) AFTER Dosage"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "MaxDosage", "decimal(10,2) AFTER MinDosage"
                ),
                self.database.check_field_exists(
                    "medicine",
                    "add",
                    "AnimalDerived",
                    "TINYINT(1) NOT NULL DEFAULT 0 AFTER MedicineName",
                ),
                self.database.check_field_exists(
                    "dict_groups",
                    "add",
                    "DictGroupsLevel3",
                    "varchar(20) AFTER DictGRoupsLevel2",
                ),
                self.database.check_field_exists(
                    "medicine", "add", "DrugName", "varchar(40) AFTER MedicineName"
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "medicine", "add", "Dosage", "decimal(10,2) AFTER Unit"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "HitRate", "int DEFAULT 0 AFTER Description"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "Commission", "varchar(10) AFTER InPrice"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "Project", "varchar(50) AFTER Commission"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "DoctorProject", "varchar(50) AFTER Project"
                ),
                self.database.check_field_exists(
                    "medicine", "add", "Deactivate", "varchar(50) AFTER HitRate"
                ),
                self.database.check_field_exists(
                    "medicine", "change", ["location", "Location"], "varchar(20)"
                ),
                self.database.check_field_exists(
                    "medicine",
                    "change",
                    ["MedicineType", "MedicineType"],
                    "varchar(10)",
                ),
                self.database.check_field_exists(
                    "medicine",
                    "change",
                    ["MedicineCode", "MedicineCode"],
                    "varchar(15)",
                ),
                self.database.check_field_exists(
                    "medextend",
                    "change",
                    ["MedExtendType", "ExtendType"],
                    "varchar(10)",
                ),
                self.database.check_field_exists(
                    "drug", "change", ["Supplier", "Supplier"], "varchar(50)"
                ),
                self.database.check_field_exists(
                    "drug", "add", "MedicineType", "varchar(10) AFTER DrugName"
                ),
            ]

        self._exec_process(process_list)

    def _check_person(self):
        if self.call_from == "pymedical":
            process_list = []
        else:
            process_list = [
                self.database.check_field_exists(
                    "person", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "person", "add", "Birthday", "date AFTER Name"
                ),
                self.database.check_field_exists(
                    "person", "add", "Gender", "varchar(2) AFTER ID"
                ),
                self.database.check_field_exists(
                    "person", "add", "Email", "varchar(100) AFTER Address"
                ),
                self.database.check_field_exists(
                    "person", "add", "FullTime", "varchar(10) AFTER Position"
                ),
                self.database.check_field_exists(
                    "person", "add", "Department", "varchar(20) AFTER Email"
                ),
                self.database.check_field_exists(
                    "person", "add", "InputDate", "date AFTER Department"
                ),
                self.database.check_field_exists(
                    "person", "add", "CertCardNo", "varchar(50) AFTER Certificate"
                ),
                self.database.check_field_exists(
                    "person", "change", ["EMail", "Email"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "person", "add", "Room", "int AFTER Position"
                ),
            ]

        self._exec_process(process_list)

    def _check_icd10(self):
        if self.call_from == "pymedical":
            process_list = []
        else:
            process_list = [
                self.database.check_field_exists(
                    "icd10", "add", "Groups", "varchar(100) AFTER SpecialCode"
                ),
                self.database.check_field_exists(
                    "icd10", "add", "HitRate", "int DEFAULT 0 AFTER Groups"
                ),
            ]

        self._exec_process(process_list)

    def _check_reserve(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "reserve",
                    "add",
                    "Arrival",
                    'enum("False", "True") not null AFTER Doctor',
                ),
                self.database.check_field_exists(
                    "doctor_month_schedule",
                    "add",
                    "CanReservation",
                    'ENUM("False", "True") NOT NULL AFTER Doctor',
                ),
                self.database.check_field_exists(
                    "reservation_table",
                    "add",
                    "ReserveType",
                    "varchar(10) AFTER ReservationTableKey",
                ),
                self.database.check_field_exists(
                    "reserve", "add", "PatInitial", "varchar(200) AFTER Arrival"
                ),
                self.database.check_field_exists(
                    "reserve",
                    "add",
                    "Frozen",
                    "tinyint(1) NOT NULL DEFAULT 0 AFTER Arrival",
                ),
                self.database.check_field_exists(
                    "reservation_table",
                    "add",
                    "ReservationDate",
                    "DATE AFTER ReservationTableKey",
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "reserve", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "reserve", "add", "ReserveNo", "int AFTER Sequence"
                ),
                self.database.check_field_exists(
                    "reserve", "add", "Source", "varchar(10) AFTER Doctor"
                ),
                self.database.check_field_exists(
                    "reservation_table", "add", "Doctor", "varchar(10) AFTER Period"
                ),
                self.database.check_field_exists(
                    "reserve", "add", "CreateTime", "datetime AFTER ReserveDate"
                ),
            ]

        self._exec_process(process_list)

    def _check_wait(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "wait", "add", "VHCReqCode", "varchar(100) AFTER Remark"
                ),
                self.database.check_field_exists(
                    "wait", "change", ["Card", "Card"], "varchar(6)"
                ),
                self.database.check_field_exists(
                    "wait", "modify", "VHCReqCode", "varchar(256)"
                ),
                self.database.check_field_exists(
                    "wait",
                    "add",
                    "DrugPickupDone",
                    'ENUM("False", "True") NOT NULL DEFAULT "False" AFTER DrugDone',
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "wait", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "wait", "add", "TreatType", "varchar(10) AFTER RegistType"
                ),
                self.database.check_field_exists(
                    "wait", "change", ["Remark", "Remark"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "wait", "add", "InProgress", "varchar(10) AFTER Doctor"
                ),
                self.database.check_field_exists(
                    "wait", "change", ["TreatType", "TreatType"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "wait", "change", ["Share", "Share"], "varchar(50)"
                ),
            ]

        self._exec_process(process_list)

    def _check_deposit(self):
        if self.call_from == "pymedical":
            process_list = []
        else:
            process_list = [
                self.database.check_field_exists(
                    "deposit", "change", ["Name", "Name"], "varchar(100)"
                ),
            ]

        self._exec_process(process_list)

    def _check_debt(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "debt", "add", "PaymentType", 'varchar(20) DEFAULT "現金" AFTER Fee'
                ),
                self.database.check_field_exists(
                    "debt", "add", "PrescriptKey", "Int AFTER CaseKey"
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "debt", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "debt", "add", "DebtType", "varchar(10) AFTER PatientKey"
                ),
                self.database.check_field_exists(
                    "debt", "add", "Cashier1", "varchar(10) AFTER Casher1"
                ),
                self.database.check_field_exists(
                    "debt", "add", "Cashier2", "varchar(10) AFTER Casher2"
                ),
                self.database.check_field_exists(
                    "debt", "add", "Cashier3", "varchar(10) AFTER Casher3"
                ),
            ]

        self._exec_process(process_list)

    def _check_ins_apply(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "insapply", "add", "DiagShareFee", "int AFTER ShareFee"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "DrugShareFee", "int AFTER DiagShareFee"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "ExamShareFee", "int AFTER DrugShareFee"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Identifier", "varchar(20) AFTER Name"
                ),
                self.database.check_field_exists(
                    "insapply",
                    "add",
                    "ActualIdentifier",
                    "varchar(20) AFTER Identifier",
                ),
                self.database.check_field_exists(
                    "insapply",
                    "add",
                    "OriginalIdentifier",
                    "varchar(20) AFTER ActualIdentifier",
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "insapply", "change", ["Name", "Name"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Visit", "varchar(10) AFTER ShareCode"
                ),
                self.database.check_field_exists(
                    "insapply", "change", ["Card", "Card"], "varchar(5)"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey7", "int(11) AFTER Percent6"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode7", "varchar(12) AFTER CaseKey7"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee7", "int AFTER TreatCode7"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent7", "int AFTER TreatFee7"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey8", "int AFTER Percent7"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode8", "varchar(12) AFTER CaseKey8"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee8", "int AFTER TreatCode8"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent8", "int AFTER TreatFee8"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey9", "int AFTER Percent8"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode9", "varchar(12) AFTER CaseKey9"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee9", "int AFTER TreatCode9"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent9", "int AFTER TreatFee9"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey10", "int AFTER Percent9"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode10", "varchar(12) AFTER CaseKey10"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee10", "int AFTER TreatCode10"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent10", "int AFTER TreatFee10"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey11", "int AFTER Percent10"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode11", "varchar(12) AFTER CaseKey11"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee11", "int AFTER TreatCode11"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent11", "int AFTER TreatFee11"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey12", "int AFTER Percent11"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode12", "varchar(12) AFTER CaseKey12"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee12", "int AFTER TreatCode12"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent12", "int AFTER TreatFee12"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey13", "int AFTER Percent12"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode13", "varchar(12) AFTER CaseKey13"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee13", "int AFTER TreatCode13"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent13", "int AFTER TreatFee13"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey14", "int AFTER Percent13"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode14", "varchar(12) AFTER CaseKey14"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee14", "int AFTER TreatCode14"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent14", "int AFTER TreatFee14"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "CaseKey15", "int AFTER Percent14"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatCode15", "varchar(12) AFTER CaseKey15"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "TreatFee15", "int AFTER TreatCode15"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "Percent15", "int AFTER TreatFee15"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "DiseaseCode4", "varchar(10) AFTER DiseaseCode3"
                ),
                self.database.check_field_exists(
                    "insapply", "add", "DiseaseCode5", "varchar(10) AFTER DiseaseCode4"
                ),
            ]

        self._exec_process(process_list)

    def _check_clinic(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "clinic", "change", ["InputCode", "InputCode"], "varchar(10)"
                ),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "clinic", "change", ["groups", "Groups"], "varchar(40)"
                ),
                self.database.check_field_exists(
                    "clinic", "change", ["position", "Position"], "varchar(40)"
                ),
                self.database.check_field_exists(
                    "clinic", "add", "HitRate", "int DEFAULT 0 AFTER ClinicName"
                ),
                self.database.check_field_exists(
                    "clinic", "change", ["ClinicName", "ClinicName"], "varchar(200)"
                ),
            ]

        self._exec_process(process_list)

    def _check_certificate(self):
        if self.call_from == "pymedical":
            process_list = []
        else:
            process_list = [
                self.database.check_field_exists(
                    "certificate", "add", "Doctor", "varchar(20) AFTER Name"
                ),
                self.database.check_field_exists(
                    "certificate", "add", "TreatType", "varchar(20) AFTER InsType"
                ),
            ]

        self._exec_process(process_list)

    def _check_others(self):
        if self.call_from == "pymedical":
            process_list = [
                self.database.check_field_exists(
                    "bulletin", "add", "Title", "varchar(200) AFTER BulletinKey"
                ),
                self.database.check_field_exists(
                    "reserve_cancel", "add", "ReserveBackup", "TEXT AFTER Remark"
                ),
                self.database.check_field_exists(
                    "stockinitems",
                    "change",
                    ["UnitPrice", "UnitPrice"],
                    "decimal(10, 2)",
                ),
                self.database.check_field_exists(
                    "stockinitems", "change", ["Amount", "Amount"], "decimal(10, 2)"
                ),
                self.database.check_field_exists(
                    "stockin", "change", ["Amount", "Amount"], "decimal(10, 2)"
                ),
                self.database.check_field_exists(
                    "backup_records", "modify", "JSON", "MEDIUMTEXT"
                ),
                self.database.check_field_exists(
                    "stockinventory_items",
                    "add",
                    "Location",
                    "varchar(20) AFTER MedicineName",
                ),
                # self.database.check_field_exists('bulletin', 'modify', 'Title', 'MEDIUMTEXT'),
            ]
        else:
            process_list = [
                self.database.check_field_exists(
                    "dict_groups",
                    "add",
                    "DictOrderNo",
                    "varchar(10) AFTER DictGroupsKey",
                ),
                self.database.check_field_exists(
                    "person", "add", "Title", "varchar(20) AFTER Code"
                ),
                self.database.check_field_exists(
                    "reservation_table", "add", "Weekday", "varchar(10) AFTER Period"
                ),
                self.database.check_field_exists(
                    "hospid", "change", ["HospName", "HospName"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "hospid", "add", "Telephone", "varchar(50) AFTER HospName"
                ),
                self.database.check_field_exists(
                    "hospid", "add", "Address", "varchar(100) AFTER Telephone"
                ),
                self.database.check_field_exists(
                    "hospid", "change", ["Telephone", "Telephone"], "varchar(50)"
                ),
                self.database.check_field_exists(
                    "hospid", "change", ["Address", "Address"], "varchar(100)"
                ),
                self.database.check_field_exists(
                    "reserve", "add", "Registrar", "varchar(10) AFTER Source"
                ),
                self.database.check_field_exists(
                    "off_day_list", "add", "Doctor", "varchar(20) AFTER Period"
                ),
                self.database.check_field_exists(
                    "images", "change", ["Filename", "Filename"], "varchar(200)"
                ),
                self.database.check_field_exists(
                    "temp_patient", "add", "Address", "varchar(100) AFTER PhoneNo"
                ),
                self.database.check_field_exists(
                    "temp_patient", "add", "Symptom", "blob AFTER Address"
                ),
                self.database.check_field_exists(
                    "temp_patient", "add", "Remark", "blob AFTER Symptom"
                ),
                self.database.check_field_exists(
                    "temp_patient", "add", "Cellphone", "varchar(20) AFTER PhoneNo"
                ),
                self.database.check_field_exists(
                    "hosts", "add", "Function", "varchar(100) AFTER HISVersion"
                ),
                self.database.check_field_exists(
                    "presextend", "add", "TimeStamp", "TIMESTAMP AFTER Content"
                ),
                self.database.check_field_exists(
                    "temporary_schedule",
                    "add",
                    "ScheduleType",
                    "varchar(10) AFTER CaseDate",
                ),
                self.database.check_field_exists(
                    "backup_records", "add", "Editor", "varchar(50) AFTER Deleter"
                ),
                self.database.check_field_exists(
                    "extension_json", "change", ["KeyValue", "KeyValue"], "varchar(50)"
                ),
                self.database.check_field_exists(
                    "doctor_agent",
                    "add",
                    "OriginalDoctor",
                    "varchar(20) AFTER AgentDate",
                ),
                self.database.check_field_exists(
                    "doctor_month_schedule",
                    "add",
                    "ProgressID",
                    "varchar(100) AFTER ScheduleID",
                ),
                self.database.check_field_exists(
                    "temporary_schedule", "add", "Agent", "varchar(10) AFTER Name"
                ),
                self.database.check_field_exists(
                    "hosts", "add", "ImageDir", "varchar(100) AFTER Function"
                ),
                self.database.check_field_exists(
                    "pregnant", "change", ["OvulateDATE", "OvulateDate"], "date"
                ),
                self.database.check_field_exists(
                    "returngoods", "add", "PatientKey", "int AFTER Period"
                ),
                self.database.check_field_exists(
                    "returngoods", "add", "Name", "varchar(20) AFTER PatientKey"
                ),
            ]

        self._exec_process(process_list)

    def _correct_records(self):
        if not os.path.isfile(UPDATE_RECORD_LOG):
            file = open(UPDATE_RECORD_LOG, "w")
            file.write(f"{date_utils.now_to_str()}: create update_records.log\n")
            file.close()

        self._check_highly_complicated_treatment()
        sql = 'SELECT * FROM icd10 WHERE ChineseName = "白帶" and ICDCode = "12"'
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self.database.exec_sql(
                'UPDATE icd10 SET ICDCode = "N899" WHERE ChineseName = "白帶" and ICDCode = "12"'
            )

    def _check_highly_complicated_treatment(self):
        keyword = "update highly complicated treatment"
        if open(UPDATE_RECORD_LOG, "r").read().find(keyword) >= 0:
            return

        script_list = [
            'UPDATE cases SET Treatment = "中度針灸合併高度傷科起始次" WHERE Treatment = "中度針灸合併高度傷科" AND Continuance <= 1',
            'UPDATE cases SET Treatment = "中度針灸合併高度傷科後續治療" WHERE Treatment = "中度針灸合併高度傷科療程2-6次"',
            'UPDATE cases SET Treatment = "中度針灸合併高度傷科後續治療" WHERE Treatment = "中度針灸合併高度傷科" AND Continuance >= 2',
            'UPDATE cases SET Treatment = "高度針灸合併高度傷科起始次" WHERE Treatment = "高度針灸合併高度傷科" AND Continuance <= 1',
            'UPDATE cases SET Treatment = "高度針灸合併高度傷科後續治療" WHERE Treatment = "高度針灸合併高度傷科療程2-6次"',
            'UPDATE cases SET Treatment = "高度針灸合併高度傷科後續治療" WHERE Treatment = "高度針灸合併高度傷科" AND Continuance >= 2',
            'UPDATE cases SET TreatType = "中度針灸合併高度傷科起始次" WHERE TreatType = "中度針灸合併高度傷科" AND Continuance <= 1',
            'UPDATE cases SET TreatType = "中度針灸合併高度傷科後續治療" WHERE TreatType = "中度針灸合併高度傷科療程2-6次"',
            'UPDATE cases SET TreatType = "中度針灸合併高度傷科後續治療" WHERE TreatType = "中度針灸合併高度傷科" AND Continuance >= 2',
            'UPDATE cases SET TreatType = "高度針灸合併高度傷科起始次" WHERE TreatType = "高度針灸合併高度傷科" AND Continuance <= 1',
            'UPDATE cases SET TreatType = "高度針灸合併高度傷科後續治療" WHERE TreatType = "高度針灸合併高度傷科療程2-6次"',
            'UPDATE cases SET TreatType = "高度針灸合併高度傷科後續治療" WHERE TreatType = "高度針灸合併高度傷科" AND Continuance >= 2',
        ]
        for script in script_list:
            self.database.exec_sql(script)

        file = open(UPDATE_RECORD_LOG, "a")
        file.write(f"{date_utils.now_to_str()}: {keyword}\n")
        file.close()

    def _check_additional_records(self):
        if self.call_from == "pymedical":
            self._check_self_fees()
            self._check_value()
        else:
            self._check_covid_history()
            self._check_infectious_medicine()
            self._check_covid_icd_10()
            self._check_covid_post_icd_10()
            self._check_infectious_share()
            self._check_infectious_drug_share()
            self._check_infectious_medicine()
            self._check_infectious_ins_charge()
            self._check_infectious_treat_fee()
            self._fix_infectious_card()

    def _check_self_fees(self):
        sql = 'SELECT * FROM charge_settings WHERE ChargeType = "自費" ORDER BY ChargeSettingsKey'
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            charge_utils.set_self_fee_basic_data(self.database)

        sql = 'SELECT * FROM charge_settings WHERE ChargeType = "證明書費" ORDER BY ChargeSettingsKey'
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            charge_utils.set_self_fee_certificate_data(self.database)

        sql = 'SELECT * FROM charge_settings WHERE ItemName IN ("三伏貼", "三九貼")'
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            charge_utils.set_self_fee_tri_heat_data(self.database)

    def _check_covid_icd_10(self):
        icd_code = "U071"

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICDCode = "{icd_code}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["ICDCode", "InputCode", "ChineseName"]
        data = [icd_code, "COVID", "確認COVID-19病毒感染"]

        self.database.insert_record("icd10", fields, data)

    def _check_covid_history(self):
        icd_code = "Z8616"

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICDCode = "{icd_code}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["ICDCode", "InputCode", "ChineseName"]
        data = [icd_code, "COVID", "COVID-19之個人史"]

        self.database.insert_record("icd10", fields, data)

    def _check_covid_post_icd_10(self):
        icd_code = "U099"

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICDCode = "{icd_code}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["ICDCode", "InputCode", "ChineseName", "EnglishName"]
        data = [
            icd_code,
            "COVID",
            "COVID-19後的病況，未明示",
            "Post COVID-19 condition, unspecified",
        ]

        self.database.insert_record("icd10", fields, data)

    def _check_infectious_share(self):
        sql = """
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "門診負擔" AND
                InsType = "健保" AND
                ShareType = "法定傳染病通報隔離" AND
                TreatType = "內科" AND
                Course = "首次"
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = [
            "ChargeType",
            "InsType",
            "ItemName",
            "ShareType",
            "TreatType",
            "Course",
            "InsCode",
            "Amount",
            "Remark",
        ]

        data = [
            "門診負擔",
            "健保",
            "行政協助法定傳染病通報且隔離案件",
            "法定傳染病通報隔離",
            "內科",
            "首次",
            "914",
            0,
            "本次就醫醫療費用全部由疾管署支付",
        ]
        self.database.insert_record("charge_settings", fields, data)

    def _check_infectious_drug_share(self):
        sql = """
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "藥品負擔" AND
                InsType = "健保" AND
                ShareType = "法定傳染病通報隔離"
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = [
            "ChargeType",
            "InsType",
            "ItemName",
            "ShareType",
            "InsCode",
            "Amount",
            "Remark",
        ]

        data = [
            "藥品負擔",
            "健保",
            "行政協助法定傳染病通報且隔離案件",
            "法定傳染病通報隔離",
            "914",
            0,
            "本次就醫醫療費用全部由疾管署支付",
        ]
        self.database.insert_record("charge_settings", fields, data)

    def _check_infectious_medicine(self):
        self._check_infectious_medicine_extra(
            "(富田)台灣清冠一號濃縮顆粒", "1110022062"
        )

        sql = """
            SELECT * FROM medicine
            WHERE
                MedicineType = "複方" AND
                MedicineName = "(天明)台灣清冠一號濃縮顆粒"
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["MedicineType", "InputCode", "InsCode", "MedicineName", "Unit"]

        rows = [
            ["複方", "WJFE", "1100015686", "(順天堂)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100015903", "(莊松榮)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1101800237", "(康福)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100022217", "(勸奉堂)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100028044", "(勝昌)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100028108", "(華陀)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100030654", "(漢聖)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1100034528", "(天一)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1110019135", "(天明)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1110020553", "(科達)台灣清冠一號濃縮顆粒", "克"],
            ["複方", "WJFE", "1110022062", "(富田)台灣清冠一號濃縮顆粒", "克"],
        ]
        for row in rows:
            self.database.insert_record("medicine", fields, row)

        rows = [
            "(順)台灣清冠一號濃縮顆粒",
            "(莊)台灣清冠一號濃縮顆粒",
            "(康)台灣清冠一號濃縮顆粒",
            "(勸)台灣清冠一號濃縮顆粒",
            "(勝)台灣清冠一號濃縮顆粒",
            "(華)台灣清冠一號濃縮顆粒",
            "(漢)台灣清冠一號濃縮顆粒",
            "(天)台灣清冠一號濃縮顆粒",
        ]
        for row in rows:
            sql = f'''
                DELETE FROM medicine
                WHERE
                    MedicineType = "複方" AND
                    MedicineName = "{row}"
            '''
            self.database.exec_sql(sql)

        rows = [
            ["(順)台灣清冠一號濃縮顆粒", "(順天堂)台灣清冠一號濃縮顆粒"],
            ["(莊)台灣清冠一號濃縮顆粒", "(莊松榮)台灣清冠一號濃縮顆粒"],
            ["(康)台灣清冠一號濃縮顆粒", "(康福)台灣清冠一號濃縮顆粒"],
            ["(勸)台灣清冠一號濃縮顆粒", "(勸奉堂)台灣清冠一號濃縮顆粒"],
            ["(勝)台灣清冠一號濃縮顆粒", "(勝昌)台灣清冠一號濃縮顆粒"],
            ["(華)台灣清冠一號濃縮顆粒", "(華陀)台灣清冠一號濃縮顆粒"],
            ["(漢)台灣清冠一號濃縮顆粒", "(漢聖)台灣清冠一號濃縮顆粒"],
            ["(天)台灣清冠一號濃縮顆粒", "(天一)台灣清冠一號濃縮顆粒"],
            ["(科)台灣清冠一號濃縮顆粒", "(科達)台灣清冠一號濃縮顆粒"],
            ["(富)台灣清冠一號濃縮顆粒", "(富田)台灣清冠一號濃縮顆粒"],
        ]
        for row in rows:
            sql = f'''
                UPDATE prescript
                SET
                    MedicineName = "{row[1]}"
                WHERE
                    MedicineSet = 1 AND
                    MedicineType = "複方" AND
                    MedicineName = "{row[0]}"
            '''
            self.database.exec_sql(sql)

    def _check_infectious_medicine_extra(self, medicine_name, ins_code):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineType = "複方" AND
                MedicineName = "{medicine_name}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["MedicineType", "InputCode", "InsCode", "MedicineName", "Unit"]
        row = ["複方", "WJFE", ins_code, medicine_name, "克"]

        self.database.insert_record("medicine", fields, row)

    def _check_infectious_ins_charge(self):
        ins_code = "E5012C"
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "處置費" AND
                InsCode = "{ins_code}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) == 1:
            return

        if len(rows) >= 2:
            self.database.exec_sql(
                f'DELETE FROM charge_settings WHERE InsCode = "{ins_code}"'
            )

        fields = ["ChargeType", "ItemName", "InsCode", "Amount", "Remark"]

        data = [
            "處置費",
            "台灣清冠一號藥品補助費",
            ins_code,
            300,
            "公費臺灣清冠一號藥品補助費用採實支實付，以每位個案實際服藥天數計算費用。無論藥品廠牌，每日藥費補助金額新臺幣300元整（含藥品調劑及管理費等）。",
        ]
        self.database.insert_record("charge_settings", fields, data)

    def _check_infectious_treat_fee(self):
        sql = """
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "處置費" AND
                InsCode = "E5204C"
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return

        fields = ["ChargeType", "ItemName", "InsCode", "Amount", "Remark"]

        data = ["處置費", "遠距診療費", "E5204C", 500, "限確診居家照護對象"]
        self.database.insert_record("charge_settings", fields, data)

    def _fix_infectious_card(self):
        self.database.exec_sql('UPDATE cases SET Card = "HVIT" WHERE Card = "IC09"')

    def _check_value(self):
        if self.system_settings.field("健保IC卡資料上傳格式") != "2.0":
            self.system_settings.post("健保IC卡資料上傳格式", "2.0")

    def _find_table_name(self, table_name):
        """回傳資料庫中實際的表名，找不到則回傳 None.

        Linux/FreeBSD 的 MariaDB 表名分大小寫，實際名稱可能是
        ReturnGoods 而非 returngoods，必須拿回真正的名字才能操作。
        """
        sql = f'''
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE
                    TABLE_SCHEMA = DATABASE() AND
                    TABLE_TYPE = "BASE TABLE" AND
                    LOWER(TABLE_NAME) = LOWER("{table_name}")
                LIMIT 1
            '''
        rows = self.database.select_record(sql)
        if not rows:
            return None
        return list(rows[0].values())[0]

    def _table_is_usable(self, table_name):
        """真的去引擎開一次表；只有明確是 1932 才回報不可用.

        其他任何錯誤（連線問題、權限不足）一律當作可用，
        絕不因為不確定就刪表。
        """
        try:
            self.database.select_record(f"SELECT 1 FROM `{table_name}` LIMIT 1")
            return True
        except Exception as e:
            message = str(e)
            if "1932" in message or "doesn't exist in engine" in message:
                return False
            return True

    def _write_update_log(self, message):
        # 訊息一律用 ASCII：這個檔案在別處是用預設編碼讀取的，
        # 混入中文會讓 _check_highly_complicated_treatment 的 read() 爆掉
        try:
            with open(UPDATE_RECORD_LOG, "a") as f:
                f.write(f"{date_utils.now_to_str()}: {message}\n")
        except Exception:
            pass

    def _check_orphan_tables(self):
        """清除 ORPHAN_CHECK_TABLES 名單內的殘骸表，回傳已刪除的表名清單."""
        dropped = []

        for name in ORPHAN_CHECK_TABLES:
            try:
                actual_name = self._find_table_name(name)
                if actual_name is None:
                    continue  # 本來就不存在，交給既有的自動建表流程
                if self._table_is_usable(actual_name):
                    continue  # 正常，不動它

                self.database.exec_sql(f"DROP TABLE IF EXISTS `{actual_name}`")

                if self._find_table_name(name) is not None:
                    # DROP 回報成功但 .frm 仍在，需要停服務手動移除
                    self._write_update_log(
                        f"orphan table {actual_name} still exists after DROP"
                    )
                    continue

                dropped.append(actual_name)
                self._write_update_log(
                    f"orphan table {actual_name} dropped (error 1932)"
                )
            except Exception as e:
                self._write_update_log(f"orphan table {name} check failed: {e}")

        return dropped
