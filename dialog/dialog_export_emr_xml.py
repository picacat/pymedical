# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime
import os
import re

from lxml import etree as ET
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    case_utils,
    class_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 匯出電子病歷交換檔 xml
class DialogExportEMRXml(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExportEMRXml, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        if self.system_settings.field("匯出電子病歷包含自費病歷") == "Y":
            self.export_self_case = True
        else:
            self.export_self_case = False

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXPORT_EMR_XML, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("匯出")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )

        self.table_widget_medical_record.set_column_hidden([0])
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, "全部")

        doctor_list = personnel_utils.get_person(self.database, "醫師", "全部")
        doctor_list.insert(0, "全部")
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)
        self.ui.pushButton_read_medical_record.clicked.connect(
            self._read_medical_record
        )
        self.ui.toolButton_set_bookmark.clicked.connect(self._set_bookmark)
        self.ui.dateEdit_start_date.dateChanged.connect(self._set_date_edit)
        self.ui.tableWidget_medical_record.horizontalHeader().sectionClicked.connect(
            self._header_clicked
        )

    def _set_date_edit(self):
        self.ui.dateEdit_end_date.setDate(self.ui.dateEdit_start_date.date())

    def button_accepted(self):
        self._export_xml_files()

    def button_rejected(self):
        pass

    def _read_medical_record(self):
        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")

        period = self.ui.comboBox_period.currentText()
        if period != "全部":
            period_condition = f' AND Period = "{period}"'
        else:
            period_condition = ""

        doctor = self.ui.comboBox_doctor.currentText()
        if doctor != "全部":
            doctor_condition = f' AND doctor = "{doctor}"'
        else:
            doctor_condition = ""

        patient_key = self.ui.lineEdit_patient_key.text().strip()
        if patient_key != "":
            patient_key_condition = f" AND PatientKey = {patient_key}"
        else:
            patient_key_condition = ""

        if self.export_self_case:
            ins_type_condition = ""
        else:
            ins_type_condition = 'InsType = "健保" AND '

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                {ins_type_condition}
                DoctorDone = "True"
                {period_condition}
                {doctor_condition}
                {patient_key_condition}
            ORDER BY CaseKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        if row["InsType"] == "健保":
            medicine_set = 1
        else:
            medicine_set = 2

        case_key = string_utils.xstr(row["CaseKey"])
        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)

        full_card = case_utils.get_full_card(row["Card"], row["Continuance"])

        export_date = None
        sql = f"""
            SELECT * FROM caseextend
            WHERE
                CaseKey = {case_key} AND
                ExtendType = "EMRDate"
        """
        extend_rows = self.database.select_record(sql)
        if len(extend_rows) > 0:
            export_date = string_utils.xstr(extend_rows[0]["Content"])

        medical_record = [
            string_utils.xstr(row["CaseKey"]),
            None,
            string_utils.xstr(row["CaseDate"]),
            string_utils.xstr(row["Period"]),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["TreatType"]),
            full_card,
            string_utils.int_to_str(pres_days),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["DiseaseName1"]),
            export_date,
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [4, 11]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [1, 3, 6]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        if export_date is None:
            checked = True
        else:
            checked = False

        self._set_check_box(row_no, checked)

    def _set_check_box(self, row_no, checked):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet("padding-left: 20px")
        check_box.setChecked(checked)
        check_box.clicked.connect(
            lambda: self._set_row_color(row_no, check_box.isChecked())
        )
        col_no = 1

        self.ui.tableWidget_medical_record.setCellWidget(row_no, col_no, check_box)
        self.ui.tableWidget_medical_record.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self._set_row_color(row_no, checked)

    def _set_row_color(self, row_no, checked):
        if checked:
            color = "black"
        else:
            color = "darkGray"

        for col_no in range(self.ui.tableWidget_medical_record.columnCount()):
            self.ui.tableWidget_medical_record.item(row_no, col_no).setForeground(
                QtGui.QColor(color)
            )

    def _export_xml_files(self):
        xml_file_path = self.system_settings.field("電子病歷交換檔輸出路徑")
        if xml_file_path is None or xml_file_path == "":
            system_utils.show_message_box(
                QMessageBox.Critical,
                "查無電子病歷檔路徑",
                '<font color="red"><h3>系統設定內的「電子病歷檔路徑尚未設定」, 請設定後再執行!</h3></font>',
                "請至系統設定->其他->設定電子病歷檔路徑.",
            )
            return

        row_count = self.ui.tableWidget_medical_record.rowCount()

        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生電子病歷交換檔中, 請稍後...", "取消", 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(row_count):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if not check_box.isChecked():
                continue

            self.ui.tableWidget_medical_record.setCurrentCell(row_no, 1)
            case_key = self.table_widget_medical_record.field_value(0)
            write_ok = self._export_emr_file(xml_file_path, case_key)
            if write_ok:
                self._set_emr_date(case_key)

        progress_dialog.setValue(row_count)

        system_utils.show_message_box(
            QMessageBox.Information,
            "匯出完成",
            "<h4>電子病歷交換檔匯出完成 !</h4>",
            "請繼續完成電子病歷簽章作業",
        )

    def _set_emr_date(self, case_key):
        self.database.exec_sql(f"""
            DELETE FROM caseextend
            WHERE
                CaseKey = {case_key} AND
                ExtendType = "EMRDate"
        """)

        fields = ["CaseKey", "ExtendType", "Content"]
        data = [
            case_key,
            "EMRDate",
            datetime.datetime.now(),
        ]
        self.database.insert_record("caseextend", fields, data)

    def _get_xml_file_name(self, xml_file_path, row):
        foxconn_id = "TW.Foxconn.Clinic.ChineseMedicine.1"

        doctor_name = string_utils.xstr(row["Doctor"])
        cert_card_no = personnel_utils.get_person_field_value(
            self.database, doctor_name, "CertCardNo"
        )
        doctor_id = personnel_utils.get_person_field_value(
            self.database, doctor_name, "ID"
        )
        patient_key = string_utils.xstr(row["PatientKey"])

        year = row["CaseDate"].year
        month = row["CaseDate"].month
        day = row["CaseDate"].day
        hour = row["CaseDate"].hour
        minute = row["CaseDate"].minute
        case_date = f"{year}{month:0>2}{day:0>2}{hour:0>2}{minute:0>2}"

        regist_no = number_utils.get_integer(row["RegistNo"])
        name = string_utils.xstr(row["Name"])
        name = string_utils.remove_illegal_characters(name.strip())

        doctor_part = f"{cert_card_no}-{doctor_id}-{doctor_name}"
        patient_part = f"{patient_key}-{case_date}-{regist_no}-{name}"

        xml_file_name = (
            f"{doctor_part}-{foxconn_id}- {nhi_utils.INS_CLASS}-{patient_part}.xml"
        )

        return os.path.join(xml_file_path, xml_file_name)

    def _export_emr_file(self, xml_file_path, case_key):
        sql = f"""
            SELECT * FROM cases
            WHERE 
                CaseKEy = {case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        xml_file_name = self._get_xml_file_name(xml_file_path, row)
        if xml_file_name is None:
            return

        xsi = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {"xsi": xsi}

        attrib = {
            "{"
            + xsi
            + "}noNamespaceSchemaLocation": "TW.Foxconn.Clinic.ChineseMedicine.1.1.xsd"
        }
        root = ET.Element("EMR", nsmap=nsmap, attrib=attrib)

        patient_key = string_utils.xstr(row["PatientKey"])
        self._add_document_info(root, row)
        self._add_patient_info(root, row, patient_key)
        self._add_encounter(root, row)
        self._add_drugs(root, row)

        tree = ET.ElementTree(root)
        write_ok = True
        try:
            tree.write(
                xml_file_name, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
        except OSError:
            write_ok = False

        return write_ok

    def _add_document_info(self, root, row):
        document_info = ET.SubElement(root, "DocumentInfo")

        his_doc_pk = ET.SubElement(document_info, "HISDocPK")
        his_doc_pk.text = string_utils.xstr(row["CaseKey"])

        hospital_id = ET.SubElement(document_info, "HospitalID")
        hospital_id.text = self.system_settings.field("院所代號")

        hospital_name = ET.SubElement(document_info, "HospitalName")
        hospital_name.text = self.system_settings.field("院所名稱")

        sheet = ET.SubElement(document_info, "Sheet")

        patient_id = ET.SubElement(sheet, "ID")
        patient_id.text = "TW.Foxconn.Clinic.ChineseMedicine.1"

        name = ET.SubElement(sheet, "Name")
        name.text = "中醫門診單"

        version = ET.SubElement(sheet, "Version")
        version.text = "1"

        doc = ET.SubElement(document_info, "Doc")

        doc_confidentiality_code = ET.SubElement(doc, "DocConfidentialityCode")
        doc_confidentiality_code.text = "N"

        now = datetime.datetime.now()
        present = f"{now.year}{now.month:0>2}{now.day:0>2}{now.hour:0>2}{now.minute:0>2}{now.second:0>2}"
        create_time = ET.SubElement(doc, "CreateTime")
        create_time.text = present

    def _add_patient_info(self, root, case_row, patient_key):
        sql = f"""
            SELECT * FROM patient
            WHERE 
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        patient_info = ET.SubElement(root, "PatientInfo")

        chart_no = ET.SubElement(patient_info, "ChartNo")
        chart_no.text = patient_key

        patient_name = ET.SubElement(patient_info, "PatientName")
        patient_name.text = string_utils.xstr(row["Name"])

        patient_birthday = row["Birthday"]
        birthday = ET.SubElement(patient_info, "Birthday")
        if patient_birthday is not None:
            year = patient_birthday.year
            month = patient_birthday.month
            day = patient_birthday.day
            birthday.text = f"{year}{month:0>2}{day:0>2}"
        else:
            birthday.text = "19000101"

        identity = ET.SubElement(patient_info, "Identity")
        identity.text = string_utils.xstr(case_row["InsType"])

        gender = ET.SubElement(patient_info, "Gender")
        gender.text = patient_utils.get_gender_code(string_utils.xstr(row["Gender"]))

        patient_id = ET.SubElement(patient_info, "PatientID")
        patient_id.text = string_utils.xstr(row["ID"])

        telephone = string_utils.xstr(row["Telephone"])
        office_phone = string_utils.xstr(row["Officephone"])
        cellphone = string_utils.xstr(row["Cellphone"])

        if telephone != "" or office_phone != "" or cellphone != "":
            tel = ET.SubElement(patient_info, "TEL")
            if telephone != "":
                home = ET.SubElement(tel, "Home")
                home.text = telephone

            if office_phone != "":
                office = ET.SubElement(tel, "Office")
                office.text = office_phone

            if cellphone != "":
                mobile = ET.SubElement(tel, "Mobile")
                mobile.text = cellphone

        marriage = ET.SubElement(patient_info, "MarriageStatus")
        marriage.text = patient_utils.get_marriage_code(
            string_utils.xstr(row["Marriage"])
        )

        patient_occupation = string_utils.xstr(row["Occupation"])
        if patient_occupation != "":
            occupation = ET.SubElement(patient_info, "Occupation")
            occupation.text = patient_occupation

        patient_address = string_utils.xstr(row["Address"])
        if patient_address != "":
            address = ET.SubElement(patient_info, "Address")
            contact = ET.SubElement(address, "Contact")

            zip_area_code = patient_utils.get_zip_code(self.database, patient_address)

            zip_code = ET.SubElement(contact, "ZipCode")
            zip_code.text = zip_area_code

            location = ET.SubElement(contact, "Location")
            location.text = patient_address

        patient_email = string_utils.xstr(row["Email"])
        if patient_email != "":
            email = ET.SubElement(patient_info, "Email")
            email.text = patient_email

        patient_history = string_utils.get_str(row["History"], "utf-8")
        if patient_history != "":
            history = ET.SubElement(patient_info, "History")
            history.text = patient_history

        patient_allergy = string_utils.get_str(row["Allergy"], "utf-8")
        if patient_allergy != "":
            allergy = ET.SubElement(patient_info, "Allergy")
            allergy.text = patient_allergy

        patient_init_date = row["InitDate"]
        if patient_init_date is not None:
            first_visit_date = ET.SubElement(patient_info, "FirstVisitDate")
            year = patient_init_date.year
            month = patient_init_date.month
            day = patient_init_date.day
            first_visit_date.text = f"{year}{month:0>2}{day:0>2}"

        patient_education = string_utils.xstr(row["Education"])
        if patient_education != "":
            education = ET.SubElement(patient_info, "Education")
            education.text = patient_education

    def _add_encounter(self, root, row):
        encounter = ET.SubElement(root, "Encounter")

        self._add_registration_data(encounter, row)
        self._add_diagnosis_data(encounter, row)
        self._add_disease_data(encounter, row)
        self._add_major_injuries(encounter, row)
        self._add_treatment(encounter, row)

    def _add_registration_data(self, encounter, row):
        case_date = row["CaseDate"]
        visit_date = ET.SubElement(encounter, "VisitDate")
        year = case_date.year
        month = case_date.month
        day = case_date.day
        hour = case_date.hour
        minute = case_date.minute
        visit_date.text = f"{year}{month:0>2}{day:0>2}{hour:0>2}{minute:0>2}"

        visit_seq = ET.SubElement(encounter, "VisitSeq")
        visit_seq.text = string_utils.xstr(number_utils.get_integer(row["RegistNo"]))

        department = ET.SubElement(encounter, "Department")
        department.text = "60"

        doc_name = string_utils.xstr(row["Doctor"])
        if doc_name != "":
            doc_id = personnel_utils.get_person_field_value(
                self.database, doc_name, "ID"
            )
            doctor_id = ET.SubElement(encounter, "DoctorID")
            doctor_id.text = doc_id

            doctor_name = ET.SubElement(encounter, "DoctorName")
            doctor_name.text = doc_name

    def _add_diagnosis_data(self, encounter, row):
        symptom = string_utils.get_str(row["Symptom"], "utf-8")

        chief_complain = ET.SubElement(encounter, "ChiefComplain")
        if chief_complain in [None, ""]:
            chief_complain = "N/A"

        if symptom is not None and symptom != "":
            try:
                chief_complain.text = symptom
            except ValueError:
                symptom = string_utils.remove_control_characters(symptom)
                chief_complain.text = symptom
        else:
            chief_complain.text = "　"

        tongue = string_utils.get_str(row["Tongue"], "utf-8")
        if tongue in [None, ""]:
            tongue = "N/A"

        if tongue is not None and tongue != "":
            tongue_condition = ET.SubElement(encounter, "TongueCondition")
            try:
                tongue_condition.text = tongue
            except ValueError:
                tongue = string_utils.remove_control_characters(tongue)
                tongue_condition.text = tongue

        pulse = string_utils.get_str(row["Pulse"], "utf-8")
        if pulse in [None, ""]:
            pulse = "N/A"

        if pulse is not None and pulse != "":
            pulse_condition = ET.SubElement(encounter, "PulseCondition")
            try:
                pulse_condition.text = pulse
            except ValueError:
                pulse = string_utils.remove_control_characters(pulse)
                pulse_condition.text = pulse

        distinct = string_utils.get_str(row["Distincts"], "utf-8")
        if distinct in [None, ""]:
            distinct = "N/A"

        if distinct is not None and distinct != "":
            manifestation = ET.SubElement(encounter, "Manifestation")
            try:
                manifestation.text = distinct
            except ValueError:
                distinct = string_utils.remove_control_characters(distinct)
                manifestation.text = distinct

        cure = string_utils.get_str(row["Cure"], "utf-8")
        if cure in [None, ""]:
            cure = "N/A"

        if cure is not None and cure != "":
            therapeutic_discipline = ET.SubElement(encounter, "TherapeuticDiscipline")
            try:
                therapeutic_discipline.text = cure
            except ValueError:
                cure = string_utils.remove_control_characters(cure)
                therapeutic_discipline.text = cure

    @staticmethod
    def _add_disease_data(encounter, row):
        if string_utils.xstr(row["DiseaseCode1"]) == "":
            diagnosis = ET.SubElement(encounter, "Diagnosis")
            code = ET.SubElement(diagnosis, "Code")
            code.text = "N/A"
            name = ET.SubElement(diagnosis, "Name")
            name.text = "N/A"
        else:
            for i in range(1, 4):
                code_field = f"DiseaseCode{i}"
                disease_code = string_utils.xstr(row[code_field])
                if disease_code == "":
                    continue

                name_field = f"DiseaseName{i}"
                disease_name = string_utils.xstr(row[name_field])

                diagnosis = ET.SubElement(encounter, "Diagnosis")
                code = ET.SubElement(diagnosis, "Code")
                code.text = disease_code
                name = ET.SubElement(diagnosis, "Name")
                name.text = disease_name

    @staticmethod
    def _add_major_injuries(encounter, row):
        major_injuries = ET.SubElement(encounter, "MajorInjuries")

        major_injury_flag = ET.SubElement(major_injuries, "MajorInjuryFlag")
        if string_utils.xstr(row["SpecialCode"]) != "":
            major_injury_flag.text = "是"

            major_injury = ET.SubElement(major_injuries, "MajorInjury")

            major_injury_code = ET.SubElement(major_injury, "MajorInjuryCode")
            major_injury_code.text = string_utils.xstr(row["DiseaseCode1"])

            major_injury_name = ET.SubElement(major_injury, "MajorInjuryName")
            major_injury_name.text = string_utils.xstr(row["DiseaseName1"])
        else:
            major_injury_flag.text = "否"

    def _add_treatment(self, encounter, row):
        medical_record_treatment = string_utils.xstr(row["Treatment"])
        if medical_record_treatment == "":
            return

        treatment = ET.SubElement(encounter, "Treatment")

        treatment_nhi_code = ET.SubElement(treatment, "TreatmentNHICode")
        treatment_nhi_code.text = nhi_utils.TREAT_DICT[medical_record_treatment]

        treatment_description = ET.SubElement(treatment, "TreatmentDescription")
        treatment_description.text = medical_record_treatment

        self._add_treatment_prescript(treatment, medical_record_treatment, row)

    def _add_treatment_prescript(self, treatment, medical_record_treatment, row):
        case_key = string_utils.xstr(row["CaseKey"])
        medicine_type = "處置"
        treatment_region = None

        if medical_record_treatment in nhi_utils.ACUPUNCTURE_TREAT:
            medicine_type = "穴道"
            treatment_region_field = "AcupunctureRegion"
            treatment_region = ET.SubElement(treatment, treatment_region_field)
        elif medical_record_treatment in nhi_utils.MASSAGE_TREAT:
            treatment_region_field = "ContusionRegion"
        elif medical_record_treatment in nhi_utils.DISLOCATE_DICT:
            treatment_region_field = "DislocateRegion"
        else:
            return

        sql = f'''
            SELECT * FROM prescript
            WHERE
                MedicineSet = 1 AND
                CaseKey = {case_key} AND
                MedicineType = "{medicine_type}" AND
                MedicineName IS NOT NULL AND
                LENGTH(MedicineName) > 0
            ORDER BY PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        if medical_record_treatment in nhi_utils.ACUPUNCTURE_TREAT:
            node_name = "AcupunctureRegionNHICode"
            treatment_nhi_code = ET.SubElement(treatment_region, node_name)
            treatment_nhi_code.text = "9"

        electric_acupuncture = ""
        for prescript_row in rows:
            medicine_name = string_utils.xstr(prescript_row["MedicineName"]).replace(
                " ", ""
            )
            if (
                "波形" in medicine_name
                or "頻率" in medicine_name
                or "時間" in medicine_name
            ):  # 電針處置暫不處理
                if electric_acupuncture == "":
                    electric_acupuncture += medicine_name
                else:
                    electric_acupuncture += "," + medicine_name

                continue

            if medical_record_treatment in nhi_utils.ACUPUNCTURE_TREAT:
                point = ET.SubElement(treatment_region, "Point")
                point_name = ET.SubElement(point, "PointName")
                point_name.text = medicine_name

                if medical_record_treatment == "電針治療":
                    point_comment = ET.SubElement(point, "PointComment")
                    point_comment.text = electric_acupuncture
            else:
                treatment_region = ET.SubElement(treatment, treatment_region_field)

                treatment_nhi_code = ET.SubElement(
                    treatment_region, "ContusionRegionNHICode"
                )
                treatment_nhi_code.text = "9"

                contusion_technique = ET.SubElement(
                    treatment_region, "ContusionTechnique"
                )
                contusion_technique.text = medicine_name

    def _add_drugs(self, root, row):
        case_key = string_utils.xstr(row["CaseKey"])

        if self.export_self_case:
            medicine_set_condition = " MedicineSet >= 1"
        else:
            medicine_set_condition = " MedicineSet = 1"

        sql = f"""
            SELECT * FROM prescript
            WHERE
                {medicine_set_condition} AND
                CaseKey = {case_key} AND
                MedicineName IS NOT NULL AND
                MedicineType NOT IN ("穴道", "處置", "檢驗", "成方") AND
                LENGTH(MedicineName) > 0
            ORDER BY PrescriptNo, PrescriptKey
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        drugs = ET.SubElement(root, "Drugs")

        for prescript_row in rows:
            medicine_set = prescript_row["MedicineSet"]
            packages = case_utils.get_packages(
                self.database, case_key, medicine_set=medicine_set
            )

            try:
                if packages == 0:
                    dosage = 1
                else:
                    dosage = prescript_row["Dosage"] / packages  # 用量
            except Exception:
                continue

            drug = ET.SubElement(drugs, "Drug")

            pres_days = case_utils.get_pres_days(
                self.database, row["CaseKey"], medicine_set=medicine_set
            )
            instruction = case_utils.get_instruction(
                self.database, case_key, medicine_set=medicine_set
            )

            ins_code = string_utils.xstr(prescript_row["InsCode"])
            if ins_code != "":
                drug_nhi_code = ET.SubElement(drug, "DrugNHICode")
                drug_nhi_code.text = ins_code

            medicine_key = string_utils.xstr(prescript_row["MedicineKey"])
            medicine_code = self._get_drug_code(medicine_key)
            if medicine_code == "":
                medicine_code = "0000"

            drug_code = ET.SubElement(drug, "DrugCode")
            drug_code.text = medicine_code

            drug_name = ET.SubElement(drug, "DrugName")
            drug_name.text = string_utils.xstr(prescript_row["MedicineName"])

            dose = ET.SubElement(drug, "Dose")
            dose.text = f"{dosage:01.2f}"  # 用量

            unit = string_utils.xstr(prescript_row["Unit"])
            if unit == "":
                unit = "克"

            unit = unit.strip()
            pattern = r'[\t &"<]'  # 注意空白在 [] 裡面也會被當作字元
            unit = re.sub(pattern, "", unit)

            dose_unit = ET.SubElement(drug, "DoseUnit")
            dose_unit.text = unit

            start_date = row["CaseDate"]
            end_date = start_date + datetime.timedelta(days=90)

            drug_start_date = ET.SubElement(drug, "DrugStartDate")
            drug_start_date.text = (
                f"{start_date.year}{start_date.month:0>2}{start_date.day:0>2}"
            )
            drug_end_date = ET.SubElement(drug, "DrugEndDate")
            drug_end_date.text = (
                f"{end_date.year}{end_date.month:0>2}{end_date.day:0>2}"
            )

            try:
                amount = prescript_row["Dosage"] * pres_days  # 用量
                total_amount = ET.SubElement(drug, "TotalAmount")
                total_amount.text = f"{amount:01.2f}"  # 用量
            except TypeError:
                pass

            if packages <= 0:
                packages = 1

            if pres_days <= 0:
                pres_days = 1

            package_number = ET.SubElement(drug, "PackageNumber")
            package_number.text = string_utils.xstr(packages)

            days = ET.SubElement(drug, "Days")
            days.text = string_utils.xstr(pres_days)

            frequency = ET.SubElement(drug, "Frequency")
            frequency.text = self._get_frequency(packages, instruction)

            prescription_method = ET.SubElement(drug, "PrescriptionMethod")
            prescription_method.text = self._get_prescript_method(
                string_utils.xstr(prescript_row)
            )

    def _get_drug_code(self, medicine_key):
        drug_code = "0000"

        if medicine_key in ["", None]:
            return drug_code

        rows = self.database.select_record(f"""
            SELECT * FROM medicine 
            WHERE 
                MedicineKey = {medicine_key}
        """)
        if len(rows) > 0:
            drug_code = string_utils.xstr(rows[0]["MedicineCode"])

        return drug_code

    @staticmethod
    def _get_frequency(packages, instruction):
        try:
            frequency = nhi_utils.FREQUENCY[packages]
        except Exception:
            frequency = "TID"

        try:
            usage = nhi_utils.USAGE[instruction]
        except Exception:
            usage = "PC"

        return f"{frequency},{usage}"

    @staticmethod
    def _get_prescript_method(medicine_type):
        prescript_method = "成藥"

        if medicine_type in ["單方", "複方"]:
            prescript_method = "磨粉"
        elif medicine_type in ["水藥"]:
            prescript_method = "先煎"
        elif medicine_type in ["外用"]:
            prescript_method = "外敷"

        return prescript_method

    def _set_bookmark(self):
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            self._header_clicked(1)

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_medical_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, col_no)
            check_box.setChecked(not check_box.isChecked())
            self._set_row_color(row_no, check_box.isChecked())
