# -*- coding: UTF-8 -*-

import datetime
import json
import os
import re
import subprocess

from lxml import etree as ET
from PyQt5 import QtCore, QtWidgets

from libs import (
    case_utils,
    charge_utils,
    date_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    prescript_utils,
    string_utils,
    xml_utils,
)


# 健保申報格式xml 2023.10.31
class InsApplyXML(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.start_date = args[4]
        self.end_date = args[5]
        self.period = args[6]
        self.apply_type = args[7]
        self.clinic_id = args[8]
        self.ins_total_fee = args[9]
        self.pre_ins_apply = args[10]

        self.ui = None
        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]
        self.start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        self.end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")

        try:
            with open("2023_ICD_MAP.json", "r", encoding="utf-8") as f:
                self.dict_icd_map = json.load(f)
        except Exception:
            self.dict_icd_map = None

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
        pass

    # 設定信號
    def _set_signal(self):
        pass

    def create_xml_file(self):
        xml_dir = nhi_utils.get_dir(self.system_settings, "申報路徑")
        if not os.path.exists(xml_dir):
            os.mkdir(xml_dir)

        xml_file_name = nhi_utils.get_ins_xml_file_name(
            self.system_settings,
            self.ins_total_fee["apply_type"],
            self.ins_total_fee["apply_date"],
        )

        self._write_xml_file(xml_file_name)
        self._zip_xml_file(xml_file_name)

    def _write_xml_file(self, xml_file_name):
        rows = self._get_ins_rows()
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生申報XML檔中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        root = ET.Element("outpatient")
        self._add_tdata(root)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                return

            self._add_ddata(root, row)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

        xml_utils.write_big5_xml(root, xml_file_name)

    def _add_tdata(self, root):
        ins_year = self.ins_total_fee["ins_generate_date"].year() - 1911
        ins_month = self.ins_total_fee["ins_generate_date"].month()
        ins_day = self.ins_total_fee["ins_generate_date"].day()
        generate_date = f"{ins_year:0>3}{ins_month:0>2}{ins_day:0>2}"

        start_year = self.ins_total_fee["start_date"].year() - 1911
        start_month = self.ins_total_fee["start_date"].month()
        start_day = self.ins_total_fee["start_date"].day()
        start_date = f"{start_year:0>3}{start_month:0>2}{start_day:0>2}"

        end_year = self.ins_total_fee["end_date"].year() - 1911
        end_month = self.ins_total_fee["end_date"].month()
        end_day = self.ins_total_fee["end_date"].day()
        end_date = f"{end_year:0>3}{end_month:0>2}{end_day:0>2}"

        tdata = ET.SubElement(root, "tdata")
        t1 = ET.SubElement(tdata, "t1")
        t1.text = "10"
        t2 = ET.SubElement(tdata, "t2")
        t2.text = self.ins_total_fee["clinic_id"]  # 院所代號
        t3 = ET.SubElement(tdata, "t3")
        t3.text = self.ins_total_fee["apply_date"]  # 費用年月
        t4 = ET.SubElement(tdata, "t4")
        t4.text = "3"  # 申報方式: 3=網路
        t5 = ET.SubElement(tdata, "t5")
        t5.text = self.ins_total_fee["apply_type"]  # 申報類別: 1=送核, 2=補報
        t6 = ET.SubElement(tdata, "t6")
        t6.text = generate_date  # 申報日期
        t25 = ET.SubElement(tdata, "t25")
        t25.text = string_utils.xstr(
            self.ins_total_fee["general_count"]
        )  # 一般案案件件數
        t26 = ET.SubElement(tdata, "t26")
        t26.text = string_utils.xstr(
            self.ins_total_fee["general_amount"]
        )  # 一般案件點數
        t27 = ET.SubElement(tdata, "t27")
        t27.text = string_utils.xstr(
            self.ins_total_fee["special_count"]
        )  # 專案案件件數
        t28 = ET.SubElement(tdata, "t28")
        t28.text = string_utils.xstr(
            self.ins_total_fee["special_amount"]
        )  # 專案案件點數
        t29 = ET.SubElement(tdata, "t29")
        t29.text = string_utils.xstr(
            self.ins_total_fee["tcm_count"]
        )  # 中醫案件件數小計
        t30 = ET.SubElement(tdata, "t30")
        t30.text = string_utils.xstr(
            self.ins_total_fee["tcm_amount"]
        )  # 中醫案件點數小計

        t33 = ET.SubElement(tdata, "t33")
        t33.text = string_utils.xstr(
            self.ins_total_fee["chronical_count"]
        )  # 慢箋件數小計
        t34 = ET.SubElement(tdata, "t34")
        t34.text = string_utils.xstr(
            self.ins_total_fee["chronical_amount"]
        )  # 慢箋點數小計

        t37 = ET.SubElement(tdata, "t37")
        t37.text = string_utils.xstr(self.ins_total_fee["total_count"])  # 案件件數總計
        t38 = ET.SubElement(tdata, "t38")
        t38.text = string_utils.xstr(self.ins_total_fee["total_amount"])  # 案件點數總計
        t39 = ET.SubElement(tdata, "t39")
        t39.text = string_utils.xstr(
            self.ins_total_fee["share_count"]
        )  # 部份負擔件數總計
        t40 = ET.SubElement(tdata, "t40")
        t40.text = string_utils.xstr(
            self.ins_total_fee["share_amount"]
        )  # 部份負擔點數總計
        t41 = ET.SubElement(tdata, "t41")
        t41.text = start_date  # 連線申報起日期
        t42 = ET.SubElement(tdata, "t42")
        t42.text = end_date  # 連線申報迄日期

    def _add_ddata(self, root, row):
        ddata = ET.SubElement(root, "ddata")

        self._add_dhead(ddata, row)
        self._add_dbody(ddata, row)

    def _add_dhead(self, ddata, row):
        dhead = ET.SubElement(ddata, "dhead")
        d1 = ET.SubElement(dhead, "d1")
        d1.text = string_utils.xstr(row["CaseType"])
        d2 = ET.SubElement(dhead, "d2")
        d2.text = string_utils.xstr(row["Sequence"])

    def _add_dbody(self, ddata, row):
        dbody = ET.SubElement(ddata, "dbody")
        case_type = string_utils.xstr(row["CaseType"])

        d3 = ET.SubElement(dbody, "d3")
        d3.text = string_utils.xstr(row["ID"])

        is_cancer_extend_care = False
        for i in range(1, 5):
            special_code = string_utils.xstr(row[f"SpecialCode{i}"])
            if special_code == "JH":  # 癌症中醫門診延長照護
                is_cancer_extend_care = True

            if special_code != "":
                dx = ET.SubElement(dbody, f"d{i + 3}")
                dx.text = string_utils.xstr(special_code)

        d8 = ET.SubElement(dbody, "d8")
        d8.text = string_utils.xstr(row["Class"])
        d9 = ET.SubElement(dbody, "d9")
        d9.text = date_utils.west_date_to_nhi_date(row["CaseDate"])

        d10 = ET.SubElement(dbody, "d10")
        d10.text = date_utils.west_date_to_nhi_date(row["StopDate"])

        birthday = row["Birthday"]
        if birthday is not None:
            d11 = ET.SubElement(dbody, "d11")
            d11.text = date_utils.west_date_to_nhi_date(birthday)

        if string_utils.xstr(row["ApplyType"]) == "2":  # 補報
            for course in range(1, nhi_utils.MAX_COURSE + 1):
                case_key = number_utils.get_integer(row[f"CaseKey{course}"])
                if case_key <= 0:
                    continue

                case_row = self._get_case_rows(case_key)[0]
                apply_type = string_utils.xstr(case_row["ApplyType"])
                if apply_type not in nhi_utils.REMEDY_TYPE:
                    continue

                remedy_type_code = nhi_utils.REMEDY_TYPE_CODE[apply_type]
                d12 = ET.SubElement(dbody, "d12")
                d12.text = string_utils.xstr(remedy_type_code)
                break

        d14 = ET.SubElement(dbody, "d14")
        d14.text = string_utils.xstr(row["Injury"])

        share_code = string_utils.xstr(row["ShareCode"])
        d15 = ET.SubElement(dbody, "d15")
        d15.text = string_utils.xstr(share_code)

        if case_type in ["28"]:
            pharmacy_note = "2"  # 慢性病處方箋調劑註記
            d16 = ET.SubElement(dbody, "d16")
            d16.text = string_utils.xstr(pharmacy_note)
            d17 = ET.SubElement(dbody, "d17")
            d17.text = self.clinic_id
        else:
            d17 = ET.SubElement(dbody, "d17")
            d17.text = "N"  # 轉診院所代號

        d18 = ET.SubElement(dbody, "d18")
        d18.text = "N"  # 是否轉診

        # if row['StopDate'] not in ['', None]:
        #     case_date = row['StopDate']
        # else:
        #     case_date = row['CaseDate']

        case_date = row["CaseDate"]  # 2024-11-22 2014 ICD10舊碼轉換已就醫日期為主

        for i in range(1, nhi_utils.MAX_DISEASE_CODE + 1):
            disease_code = string_utils.xstr(row[f"DiseaseCode{i}"]).upper()
            if disease_code != "":
                if (
                    not self.pre_ins_apply
                    and case_date.year <= 2024
                    and self.dict_icd_map is not None
                ):  # 2024以舊版申報
                    try:
                        disease_code = self.dict_icd_map[
                            disease_code
                        ]  # 申報月份2025年以前只能申報2014年版本ICD-10
                    except Exception:
                        pass

                if case_date.year <= 2024:  # 2024以舊版申報
                    if disease_code == "H814":
                        disease_code = "H8149"

                dx = ET.SubElement(dbody, f"d{i + 18}")
                dx.text = string_utils.xstr(disease_code.upper())

        if number_utils.get_integer(row["PresDays"]) > 0:
            d27 = ET.SubElement(dbody, "d27")
            d27.text = string_utils.xstr(row["PresDays"])

        d28 = ET.SubElement(dbody, "d28")
        d28.text = string_utils.xstr(row["PresType"])

        d29 = ET.SubElement(dbody, "d29")
        card = string_utils.xstr(row["Card"])[:4]
        d29.text = card

        d30 = ET.SubElement(dbody, "d30")
        d30.text = string_utils.xstr(row["DoctorID"])

        if string_utils.xstr(row["PharmacistID"]) != "":
            d31 = ET.SubElement(dbody, "d31")
            d31.text = string_utils.xstr(
                row["PharmacistID"]
            )  # 如果沒藥師，就是醫師調劑

        drug_fee = number_utils.get_integer(row["DrugFee"])
        if drug_fee > 0:
            d32 = ET.SubElement(dbody, "d32")
            d32.text = string_utils.xstr(row["DrugFee"])

        if number_utils.get_integer(row["TreatFee"]) > 0:
            d33 = ET.SubElement(dbody, "d33")
            d33.text = string_utils.xstr(row["TreatFee"])

        if string_utils.xstr(row["DiagCode"]) != "":
            d35 = ET.SubElement(dbody, "d35")
            d35.text = string_utils.xstr(row["DiagCode"])

        if number_utils.get_integer(row["DiagFee"]) > 0:
            d36 = ET.SubElement(dbody, "d36")
            d36.text = string_utils.xstr(row["DiagFee"])

        pharmacy_code = nhi_utils.extract_pharmacy_code(
            string_utils.xstr(row["PharmacyCode"])
        )
        pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])

        if string_utils.xstr(row["CaseType"]) == "30":  # 腦血管疾病
            default_pharmacy_fee = charge_utils.get_ins_pharmacy_fee(
                self.database,
                self.system_settings,
                drug_fee,
                "申報",
            )
            if number_utils.get_integer(row["PharmacyFee"]) > default_pharmacy_fee:
                pharmacy_code = ""
            elif (
                number_utils.get_integer(row["PharmacyFee"]) > 0
                and pharmacy_code.strip() == ""
            ):
                pharmacist = self.system_settings.field("藥師人數")
                if int(pharmacist) > 0:
                    default_pharmacy_code = "100000"
                else:
                    default_pharmacy_code = "200000"

                pharmacy_code = nhi_utils.extract_pharmacy_code(default_pharmacy_code)
                sql = f'''
                    UPDATE insapply
                    SET
                        PharmacyCode = "{default_pharmacy_code}"
                    WHERE
                        InsApplyKey = {row["InsApplyKey"]}
                '''
                self.database.exec_sql(sql)

        elif string_utils.xstr(row["CaseType"]) == "C5":
            if pharmacy_fee <= 0:
                pharmacy_code = ""
        elif is_cancer_extend_care and drug_fee > 0:
            pharmacy_code = charge_utils.get_ins_code_from_charge_settings(
                self.database, "照護費", "中醫門診延長照護藥品調劑費"
            )

        if string_utils.xstr(pharmacy_code) != "":
            d37 = ET.SubElement(dbody, "d37")
            d37.text = string_utils.xstr(pharmacy_code)

        if pharmacy_fee > 0:
            d38 = ET.SubElement(dbody, "d38")
            d38.text = string_utils.xstr(pharmacy_fee)

        d39 = ET.SubElement(dbody, "d39")
        d39.text = string_utils.xstr(number_utils.get_integer(row["InsTotalFee"]))
        d40 = ET.SubElement(dbody, "d40")
        d40.text = string_utils.xstr(number_utils.get_integer(row["ShareFee"]))
        d41 = ET.SubElement(dbody, "d41")
        d41.text = string_utils.xstr(number_utils.get_integer(row["InsApplyFee"]))

        # if row['AgentFee'] is not None:
        #     d43 = ET.SubElement(dbody, 'd43')
        #     d43.text = string_utils.xstr(row['AgentFee'])

        # 2023-08-01
        diag_share_fee = number_utils.get_integer(row["DiagShareFee"])
        drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
        exam_share_fee = number_utils.get_integer(row["ExamShareFee"])

        if share_code in ["003", "004"]:
            agent_fee = diag_share_fee + drug_share_fee
            d43 = ET.SubElement(dbody, "d43")
            d43.text = string_utils.xstr(agent_fee)

        special_code = string_utils.xstr(row["SpecialCode1"])
        if case_type in ["24", "28"] and special_code in ["CC", "CD", "CE", "CF", "CG"]:
            total_pres_days = case_utils.get_pres_days(self.database, row["CaseKey1"])
            d44 = ET.SubElement(dbody, "d44")
            d44.text = string_utils.xstr(total_pres_days)

        d49 = ET.SubElement(dbody, "d49")

        name = string_utils.xstr(row["Name"])
        d49.text = self._get_name(name)

        case_key = row["CaseKey1"]
        regist_type = None
        treat_type = None
        tour_area = None
        if case_key is not None:
            rows = self._get_case_rows(case_key)
            if len(rows) > 0:
                case_row = rows[0]
                regist_type = string_utils.xstr(case_row["RegistType"])
                treat_type = string_utils.xstr(case_row["TreatType"])
                tour_area = string_utils.xstr(case_row["TourArea"])
            else:
                case_row = None

        if tour_area is not None:
            correction_area_code = nhi_utils.get_correction_area_code(
                self.system_settings, tour_area
            )  # 矯正機關代號
            if correction_area_code is not None:
                d50 = ET.SubElement(dbody, "d50")
                d50.text = correction_area_code

        if (
            self.system_settings.field("資源類別") in nhi_utils.AT_LACK_AREA
            or regist_type in nhi_utils.AT_LACK_AREA
        ):
            lack_area = "01"
            d52 = ET.SubElement(dbody, "d52")
            d52.text = self._get_name(lack_area)
        elif (
            self.system_settings.field("資源類別") in nhi_utils.GOTO_LACK_AREA
            or regist_type in nhi_utils.GOTO_LACK_AREA
        ):
            lack_area = "02"
            d52 = ET.SubElement(dbody, "d52")
            d52.text = self._get_name(lack_area)
            try:
                lack_area_code = nhi_utils.TOUR_AREA_CODE[tour_area]
                d53 = ET.SubElement(dbody, "d53")
                d53.text = self._get_name(lack_area_code)
            except Exception:
                pass
        elif (
            regist_type in nhi_utils.TOUR_MOUNTAIN_ISLAND
            and treat_type in nhi_utils.HOME_CARE
        ):  # 山地離島居家醫療訪視費 2022.09.09 龍潭安聲
            lack_area = "04"
            d52 = ET.SubElement(dbody, "d52")
            d52.text = self._get_name(lack_area)
            try:
                lack_area_code = nhi_utils.TOUR_AREA_CODE[tour_area]
                d53 = ET.SubElement(dbody, "d53")
                d53.text = self._get_name(lack_area_code)
            except Exception:
                pass

        if case_type in ["28"]:
            if case_row is not None:
                card = string_utils.xstr(case_row["Card"])
                d56 = ET.SubElement(dbody, "d56")
                d56.text = string_utils.xstr(card)

        # 2023.07.01 實施
        d57 = ET.SubElement(dbody, "d57")
        d57.text = string_utils.xstr(diag_share_fee)

        d58 = ET.SubElement(dbody, "d58")
        d58.text = string_utils.xstr(drug_share_fee)

        if exam_share_fee > 0:
            d59 = ET.SubElement(dbody, "d59")
            d59.text = string_utils.xstr(exam_share_fee)

        identifier = string_utils.xstr(row["Identifier"])
        if identifier not in ["", None]:
            d60 = ET.SubElement(dbody, "d60")
            d60.text = string_utils.xstr(identifier)

        actual_identifier = string_utils.xstr(row["ActualIdentifier"])
        if actual_identifier not in ["", None]:
            d61 = ET.SubElement(dbody, "d61")
            d61.text = string_utils.xstr(actual_identifier)

        original_identifier = string_utils.xstr(row["OriginalIdentifier"])
        if original_identifier not in ["", None]:
            d62 = ET.SubElement(dbody, "d62")
            d62.text = string_utils.xstr(original_identifier)

        self._add_pdata(dbody, row)

    def _add_pdata(self, dbody, row):
        if string_utils.xstr(row["CaseType"]) == "30":  # 腦血管疾病, 小兒氣喘, 小兒腦麻
            self._add_auxiliary_case(dbody, row)
            return
        elif string_utils.xstr(row["CaseType"]) == "31":  # 居家醫療
            self._add_home_care_case(dbody, row)
            return
        elif string_utils.xstr(row["CaseType"]) == "C5":  # 法定傳染病通報隔離
            self._add_infectious_case(dbody, row)
            return

        self.sequence = 0
        for course in range(1, nhi_utils.MAX_COURSE + 1):
            case_key = number_utils.get_integer(row[f"CaseKey{course}"])
            if case_key <= 0:
                continue

            rows = self._get_case_rows(case_key)
            if len(rows) <= 0:
                continue

            case_row = rows[0]
            identifier = case_utils.get_identifier(
                self.database, case_key, "就醫識別碼"
            )

            if course == 1:  # 設定診察費
                self._set_diagnosis(dbody, row, identifier)
                if string_utils.xstr(row["Visit"]) == "初診照護":
                    self._set_first_visit(dbody, row, identifier)

            case_type = string_utils.xstr(row["CaseType"])
            if (
                case_type not in ["28"]
                and case_utils.get_case_extend(self.database, case_key, "整合醫療照護")
                == "Y"
            ):  # 慢箋不能報
                self._set_integrate_care(dbody, row, case_row, identifier)

            # infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
            # if infectious_drug in ['台灣清冠一號及科學中藥', '台灣清冠一號']:  # 台灣清冠一號藥品補助費
            if case_type == "C5":  # 法定傳染病通報隔離
                self._add_infectious_drug(dbody, row, identifier)

            try:
                age_year, _ = date_utils.get_age(row["Birthday"], case_row["CaseDate"])
                if (
                    case_row["CaseDate"].strftime("%Y-%m-%d") >= "2023-03-01"
                    and age_year < 7
                    and course == 1
                    and string_utils.xstr(case_row["Treatment"])
                    in nhi_utils.MASSAGE_TREAT
                ):
                    self._set_child_extra_massage_fee(dbody, row, identifier)
            except Exception:
                pass

            regist_type = string_utils.xstr(case_row["RegistType"])
            treat_type = string_utils.xstr(case_row["TreatType"])
            if treat_type in nhi_utils.CARE_TREAT:
                self._set_special_care(dbody, row, case_row, identifier)

            treat_code = string_utils.xstr(row[f"TreatCode{course}"])

            if (
                treat_type in nhi_utils.PREGNANT_CARE_TREAT
            ):  # 孕產照護不放針傷處置代碼  2024-12-18 陳立德 岐伯齋
                pass
            elif case_type not in ["28"] and treat_code != "":
                if (
                    string_utils.xstr(row["CaseType"]) == "22"
                ):  # 特定照護: 孕產照護，肝乳癌照護, 癌症中醫門診延長照護
                    if (
                        treat_code in ["P59041", "P59042"]
                        or regist_type in nhi_utils.LONG_TERM_CARE
                    ):  # 癌症中醫門診延長照護
                        order_type = "2"
                    else:
                        order_type = "4"
                else:
                    order_type = "2"

                self._set_treatment(
                    dbody, row, case_row, course, treat_code, order_type, identifier
                )

            # 山地離島居家醫療訪視費
            if case_type == "25" and string_utils.xstr(row["SpecialCode1"]) == "EC":
                diag_code = nhi_utils.get_diag_code(
                    self.database,
                    self.system_settings,
                    string_utils.xstr(case_row["Doctor"]),
                    string_utils.xstr(case_row["RegistType"]),
                    string_utils.xstr(case_row["TreatType"]),
                    number_utils.get_integer(case_row["DiagFee"]),
                )
                self._set_treatment(
                    dbody, row, case_row, course, diag_code, "居家醫療", identifier
                )

            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                self._set_prescript(
                    dbody, row, case_row, prescript_rows, case_key, course, identifier
                )

    def _set_diagnosis(self, dbody, row, identifier):
        diag_code = string_utils.xstr(row["DiagCode"])
        # case_type = string_utils.xstr(row['CaseType'])

        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, diag_code, case_date=row["CaseDate"]
            )
        )
        if unit_price <= 0:
            return

        amount = number_utils.get_integer(row["DiagFee"])

        self.sequence += 1
        pdata = ET.SubElement(dbody, "pdata")
        p3 = ET.SubElement(pdata, "p3")
        p3.text = "0"  # 0=診察費
        p4 = ET.SubElement(pdata, "p4")
        p4.text = diag_code

        if string_utils.xstr(row["ShareCode"]) == "007":
            percent = 100
        else:
            percent = amount / unit_price * 100

        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量

        if string_utils.xstr(row["ShareCode"]) == "007":
            price = amount
        else:
            price = unit_price

        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(price)  # 單價

        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"])  # 中醫時間補0000
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_first_visit(self, dbody, row, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        ins_code = "A90"
        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, ins_code, case_date=row["CaseDate"]
            )
        )
        unit_price = amount

        p3 = ET.SubElement(pdata, "p3")
        p3.text = "2"  # 2=診療明細
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = amount / unit_price * 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_child_extra_massage_fee(self, dbody, row, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        ins_code = "E90"
        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, ins_code, case_date=row["CaseDate"]
            )
        )
        unit_price = amount

        p3 = ET.SubElement(pdata, "p3")
        p3.text = "2"  # 2=診療明細
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = amount / unit_price * 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_integrate_care(self, dbody, row, case_row, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        ins_code = "A91"
        amount = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, ins_code, case_date=row["CaseDate"]
            )
        )
        unit_price = amount

        p3 = ET.SubElement(pdata, "p3")
        p3.text = "2"  # 2=診療明細
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = amount / unit_price * 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_key = case_row["CaseKey"]
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"])
        try:
            start_time, end_time = case_utils.get_integrate_case_time(
                self.database, case_key
            )
        except Exception:
            start_time = "0000"
            end_time = "0000"

        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}{start_time}"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}{end_time}"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _get_treat_datetime(self, case_key, case_row):
        start_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        end_date = start_date

        try:
            start_time = prescript_utils.get_treat_time(
                self.database, case_key, "治療開始:"
            )
            end_time = prescript_utils.get_treat_time(
                self.database, case_key, "治療結束:"
            )
        except Exception:
            start_time = "0000"
            end_time = "0000"

        if end_time < start_time:
            end_date = date_utils.west_date_to_nhi_date(
                case_row["CaseDate"].date() + datetime.timedelta(days=1)
            )

        return start_date, end_date, start_time, end_time

    def _set_treatment(
        self, dbody, row, case_row, course, treat_code, order_type, identifier
    ):
        pdata = ET.SubElement(dbody, "pdata")
        p17_code = "2"  # 同一療程
        p19_code = ""  # 事前審查受理編號
        total_dosage = 1  # 總量

        self.sequence += 1

        case_key = case_row["CaseKey"]
        case_date = case_row["CaseDate"]

        try:
            if order_type == "居家醫療":  # redefine
                order_type = "2"
                amount = number_utils.get_integer(case_row["DiagFee"])
                percent = 100
                unit_price = amount
            elif order_type == "台灣清冠一號藥品補助費":  # redefine
                order_type = "2"
                unit_price = charge_utils.get_ins_fee_from_ins_code(
                    self.database, "E5012C", case_date=case_date
                )  # 台灣清冠一號補助費
                total_dosage = case_utils.get_pres_days(
                    self.database, case_row["CaseKey"]
                )
                amount = unit_price * total_dosage
                percent = 100
                p17_code = "4"
                infectious_drug_code = prescript_utils.get_infectious_drug_code(
                    self.database, case_key
                )
                if infectious_drug_code not in ["", None]:
                    p19_code = infectious_drug_code
                else:
                    p19_code = charge_utils.get_ins_code_from_infectious_drug(
                        self.database, "清冠一號"
                    )
            elif order_type == "遠距診療費":  # redefine
                order_type = "2"
                amount = charge_utils.get_ins_fee_from_ins_code(
                    self.database, "E5204C", case_date=case_date
                )  # 遠距診療費
                percent = 100
                unit_price = amount
                p17_code = "4"
            else:
                amount = number_utils.get_integer(row[f"TreatFee{course}"])
                percent = number_utils.get_integer(row[f"Percent{course}"])
                treat_code = string_utils.xstr(row[f"TreatCode{course}"])
                unit_price = number_utils.get_integer(
                    charge_utils.get_ins_fee_from_ins_code(
                        self.database, treat_code, case_date=case_date
                    )
                )
                if (
                    string_utils.xstr(case_row["TreatType"])
                    in nhi_utils.MISC_CARE_TREAT
                    + nhi_utils.PREGNANT_CARE_TREAT
                    + nhi_utils.CANCER_CARE_TREAT
                    + nhi_utils.KIDNEY_CARE_TREAT
                ):
                    total_dosage = 0
                    amount = 0
        except KeyError:
            amount = 0
            unit_price = 0
            percent = 100

        # unit_price = number_utils.round_up(amount / percent * 100)

        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑或物理治療
        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type  # 2=診療明細
        p4 = ET.SubElement(pdata, "p4")
        p4.text = treat_code

        if treat_code in nhi_utils.COMPLICATED_TREAT_CODE:
            # if row["CaseType"] == "22":
            #     print(row["Sequence"], row["Name"], treat_code)

            treat_position_code = prescript_utils.get_treat_position_code(
                self.database, case_key, "治療部位:"
            )
            if treat_position_code != "":
                p6 = ET.SubElement(pdata, "p6")
                p6.text = treat_position_code[:18]  # p6 最多18bytes

        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"

        p10 = ET.SubElement(pdata, "p10")
        p10.text = f"{total_dosage:05.1f}"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = f"{unit_price:05.2f}"  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date, end_date, start_time, end_time = self._get_treat_datetime(
            case_key, case_row
        )

        # if treat_code in ['F01', 'F02', 'F18', 'F19']:  # 2024.01.04 一般針灸合併一般傷科不需要放治療時間
        #     start_time = '0000'
        #     end_time = '0000'

        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}{start_time}"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{end_date}{end_time}"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        if p17_code != "":
            p17 = ET.SubElement(pdata, "p17")
            p17.text = p17_code  # 同一療程

        if p19_code != "":
            p19 = ET.SubElement(pdata, "p19")
            p19.text = p19_code

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if self.apply_date >= "11504":
            diag_code = row["DiagCode"]
            if diag_code in [
                "A01",
                "A03",
                "A05",
                "A09",
            ]:  # 有護理人員 2026-04-14  護理人員跟診獎勵
                p21 = ET.SubElement(pdata, "p21")
                p21.text = "CNP"

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

        if treat_code in nhi_utils.COMPLICATED_TREAT_CODE:
            self._set_auxiliary_treat(dbody, row, case_row, "輔助治療:", identifier)

    # 複雜針灸傷科輔助治療
    def _set_auxiliary_treat(self, dbody, row, case_row, field_value, identifier):
        case_key = case_row["CaseKey"]
        start_date, end_date, start_time, end_time = self._get_treat_datetime(
            case_key, case_row
        )

        start_date += start_time
        end_date += end_time

        sql = f'''
            SELECT MedicineName FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineName LIKE "{field_value}%"
            ORDER BY PrescriptKey
        '''
        prescript_rows = self.database.select_record(sql)

        for prescript_row in prescript_rows:
            auxiliary_treat = string_utils.xstr(prescript_row["MedicineName"])
            try:
                auxiliary_treat = auxiliary_treat.split(field_value)[1].strip()
            except Exception:
                continue

            try:
                ins_code = nhi_utils.AUXILIARY_TREAT_DICT[auxiliary_treat]
            except Exception:
                continue

            self._set_auxiliary_treat_row(
                dbody, row, case_row, ins_code, start_date, end_date, identifier
            )

    def _set_auxiliary_treat_row(
        self, dbody, row, case_row, ins_code, start_date, end_date, identifier
    ):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1

        order_type = "4"  # 藥品代號為 R001~R007 專案支付參考數值填G
        total_dosage = 1
        unit_price = 0
        amount = 0

        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type  # 4=不另計價
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = string_utils.xstr(total_dosage)  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        p14 = ET.SubElement(pdata, "p14")
        p14.text = start_date

        p15 = ET.SubElement(pdata, "p15")
        p15.text = end_date

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_prescript(
        self,
        dbody,
        row,
        case_row,
        prescript_rows,
        case_key,
        course,
        identifier,
        set_A21=True,
    ):
        pres_days = case_utils.get_pres_days(self.database, case_key)
        packages = case_utils.get_packages(self.database, case_key)
        instruction = case_utils.get_instruction(self.database, case_key)
        if pres_days <= 0:
            return

        case_type = string_utils.xstr(row["CaseType"])
        if case_type in ["24", "29"] and pres_days > 30:
            if pres_days == 60:
                pres_days = 30  # 拆成兩筆
            elif pres_days == 56:
                pres_days = 28  # 拆成兩筆
            else:
                pres_days = 30
        elif case_type in ["28"]:
            if pres_days == 60:
                pres_days -= 30
            elif pres_days == 56:
                pres_days -= 28
            else:
                pres_days -= 30

        # 新特約院所新增虛擬碼 R005 2019.08.10
        if row["Card"] is not None and string_utils.xstr(row["Card"][:4]) == "G000":
            self._set_virtual_order(dbody, row, case_row, "R005", pres_days, identifier)

        if (
            row["Card"] is not None
            and string_utils.xstr(row["Card"][0]) == "W"  # 控制軟體6.0產生卡序 W***
            and case_utils.get_case_extend(self.database, case_key, "健保卡種類")
            == "虛擬健保卡"
        ):
            self._set_virtual_order(dbody, row, case_row, "W00V", 0, identifier)

        if string_utils.xstr(case_row["RegistType"]) in nhi_utils.TELECOM_TYPE:
            self._set_covid19(dbody, row, case_row, pres_days, identifier)

        if number_utils.get_integer(row["DrugFee"]) > 0:
            order_type = "1"  # 1=用藥明細
        else:
            order_type = "4"  # 4=不另計價

        if set_A21:
            self._set_A21(dbody, row, case_row, order_type, pres_days, identifier)

        if number_utils.get_integer(row["PharmacyFee"]) > 0:
            if string_utils.xstr(row["CaseType"]) in [
                "30",
                "31",
            ]:  # 腦血管疾病加強照護, 居家照護
                self._set_auxiliary_pharmacy(
                    dbody, row, case_row, pres_days, course, identifier
                )
            else:
                self._set_pharmacy(dbody, row, case_row, pres_days, course, identifier)

        for prescript_row in prescript_rows:
            self._set_medicine(
                dbody,
                row,
                case_row,
                prescript_row,
                pres_days,
                packages,
                instruction,
                identifier,
            )

    def _set_virtual_order(self, dbody, row, case_row, ins_code, pres_days, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1

        order_type = "G"  # 藥品代號為 R001~R007 專案支付參考數值填G
        total_dosage = 0
        unit_price = 0
        amount = 0

        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type  # 1=用藥明細 4=不另計價 G-專案支付參考
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = string_utils.xstr(total_dosage)  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}0000"

        if pres_days > 0:
            end_date = date_utils.west_date_to_nhi_date(
                case_row["CaseDate"].date() + datetime.timedelta(days=pres_days - 1)
            )
            p15 = ET.SubElement(pdata, "p15")
            p15.text = f"{end_date}0000"
        else:
            p15 = ET.SubElement(pdata, "p15")
            p15.text = f"{start_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_covid19(self, dbody, row, case_row, pres_days, identifier, ins_code=None):
        if ins_code is None:
            if string_utils.xstr(case_row["RegistType"]) in "視訊門診":
                ins_code = "ViT-COVID19"  # 新特約院所
            elif string_utils.xstr(case_row["RegistType"]) in "電話門診":
                ins_code = "PhT-COVID19"  # 新特約院所
            else:
                return

        pdata = ET.SubElement(dbody, "pdata")
        self.sequence += 1
        order_type = "G"  # 藥品代號為 R001~R007 專案支付參考數值填G
        total_dosage = 0
        unit_price = 0
        amount = 0

        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type  # 1=用藥明細 4=不另計價 G-專案支付參考
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code

        percent = 000
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = string_utils.xstr(total_dosage)  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}0000"

        end_date = start_date
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{end_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_infectious_virtual_code(self, dbody, row, case_row, identifier):
        infectious_date = case_utils.get_case_extend(
            self.database, case_row["CaseKey"], "確診日期"
        )
        if infectious_date is not None:
            try:
                infectious_date = date_utils.str_to_date(infectious_date[:10])
            except ValueError:
                infectious_date = infectious_date.split(" ")[0] + " 00:00:00"
                infectious_date = date_utils.str_to_datetime(infectious_date)
        else:
            infectious_date = case_row["CaseDate"].date()

        pdata = ET.SubElement(dbody, "pdata")
        self.sequence += 1
        total_dosage = 0
        unit_price = 0
        amount = 0

        p3 = ET.SubElement(pdata, "p3")
        p3.text = "G"  # 1=用藥明細 4=不另計價 G-虛擬醫令
        p4 = ET.SubElement(pdata, "p4")
        p4.text = "NND000"

        percent = 000
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = string_utils.xstr(total_dosage)  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date = date_utils.west_date_to_nhi_date(infectious_date)
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}0000"

        end_date = start_date
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{end_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_A21(self, dbody, row, case_row, order_type, pres_days, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1

        ins_code = "A21"
        if string_utils.xstr(case_row["TreatType"]) == "癌症中醫門診延長照護":
            ins_code = "P59021"

        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, ins_code, case_date=case_row["CaseDate"]
            )
        )
        amount = unit_price * pres_days

        p1 = ET.SubElement(pdata, "p1")
        p1.text = f"{pres_days}"  # 給藥日數
        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑
        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type  # 1=用藥明細 4=不另計價
        p4 = ET.SubElement(pdata, "p4")
        p4.text = ins_code
        p5 = ET.SubElement(pdata, "p5")
        p5.text = f"{pres_days:07.2f}"  # 用量
        p7 = ET.SubElement(pdata, "p7")
        p7.text = "QD"

        percent = 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p9 = ET.SubElement(pdata, "p9")
        p9.text = "PO"  # 口服
        p10 = ET.SubElement(pdata, "p10")
        p10.text = f"{pres_days:07.1f}"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}0000"

        end_date = date_utils.west_date_to_nhi_date(
            case_row["CaseDate"].date() + datetime.timedelta(days=pres_days - 1)
        )
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{end_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_auxiliary_pharmacy(
        self, dbody, row, case_row, pres_days, course, identifier
    ):
        if pres_days <= 0:
            return

        if string_utils.xstr(case_row["PharmacyType"]) == "不申報":
            return

        on_duty, pharmacist = nhi_utils.pharmacist_schedule_on_duty(
            self.database, case_row["CaseKey"]
        )
        if on_duty:
            item_name = "藥師調劑"
        else:
            item_name = "醫師調劑"

        pharmacy_code = charge_utils.get_ins_code_from_charge_settings(
            self.database, "調劑費", item_name
        )

        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, pharmacy_code, case_date=case_row["CaseDate"]
            )
        )
        amount = charge_utils.get_extra_pharmacy_fee(
            string_utils.xstr(case_row["RegistType"]), unit_price
        )

        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑
        p3 = ET.SubElement(pdata, "p3")
        p3.text = "9"  # 9=調劑費
        p4 = ET.SubElement(pdata, "p4")
        p4.text = pharmacy_code

        percent = amount / unit_price * 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        if pharmacist is not None:
            p16.text = personnel_utils.get_person_field_value(
                self.database, pharmacist, "ID"
            )
        else:
            p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_pharmacy(self, dbody, row, case_row, pres_days, course, identifier):
        if pres_days <= 0:
            return

        pharmacy_byte = string_utils.xstr(row["PharmacyCode"])[course - 1]
        if pharmacy_byte in ["1", "2"]:
            pharmacy_code = f"A3{pharmacy_byte}"
            if string_utils.xstr(case_row["TreatType"]) == "癌症中醫門診延長照護":
                pharmacy_code = "P59031"
        else:
            return

        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, pharmacy_code, case_date=case_row["CaseDate"]
            )
        )
        amount = charge_utils.get_extra_pharmacy_fee(
            string_utils.xstr(case_row["RegistType"]), unit_price
        )

        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑
        p3 = ET.SubElement(pdata, "p3")
        p3.text = "9"  # 9=調劑費
        p4 = ET.SubElement(pdata, "p4")
        p4.text = pharmacy_code

        percent = amount / unit_price * 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        if pharmacy_code == "A31":
            _, pharmacist = nhi_utils.pharmacist_schedule_on_duty(
                self.database, case_row["CaseKey"]
            )
            p16.text = personnel_utils.get_person_field_value(
                self.database, pharmacist, "ID"
            )
        else:
            p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_medicine(
        self,
        dbody,
        row,
        case_row,
        prescript_row,
        pres_days,
        packages,
        instruction,
        identifier,
    ):
        if pres_days <= 0 or packages <= 0:
            return

        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        unit_price = 0
        amount = unit_price

        p1 = ET.SubElement(pdata, "p1")
        p1.text = string_utils.xstr(pres_days)  # 給藥天數
        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑
        p3 = ET.SubElement(pdata, "p3")
        p3.text = "4"  # 4=不另計價藥品
        p4 = ET.SubElement(pdata, "p4")
        p4.text = string_utils.xstr(prescript_row["InsCode"])

        dosage = prescript_row["Dosage"]  # 用量

        dosage_mode = prescript_row["DosageMode"]  # 劑量模式
        if dosage_mode == "次劑量":
            dosage *= packages

        p5 = ET.SubElement(pdata, "p5")
        p5.text = f"{dosage:07.2f}"  # 用量

        frequency = nhi_utils.FREQUENCY[packages]
        usage = nhi_utils.get_usage(instruction)
        p7 = ET.SubElement(pdata, "p7")
        p7.text = f"{frequency}{usage}"

        percent = 100
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"  # 成數

        p9 = ET.SubElement(pdata, "p9")
        p9.text = "PO"  # 使用途徑

        total_dosage = prescript_row["Dosage"] * pres_days  # 總量
        if dosage_mode == "次劑量":
            total_dosage *= packages
            # total_dosage = round(float(str(total_dosage)), 1)

        total_dosage = number_utils.round_up_ex(total_dosage, ".1")  # 小數點1位

        p10 = ET.SubElement(pdata, "p10")
        p10.text = f"{total_dosage:07.1f}"  # 總量

        # if case_row['Name'] == '袁巧倪':
        #     print(prescript_row['Dosage'], pres_days, packages, total_dosage, p10.text)

        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        start_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{start_date}0000"

        end_date = date_utils.west_date_to_nhi_date(
            case_row["CaseDate"].date() + datetime.timedelta(days=pres_days - 1)
        )
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{end_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = string_utils.xstr(case_row["DoctorID"])

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "4"  # 非慢性病 非同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    # 小兒氣喘，小兒腦性麻痺不能申報藥費及調劑費，也不能申報針灸治療
    def _add_auxiliary_case(self, dbody, row):
        set_A21 = True
        apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)
        case_key = row["CaseKey1"]

        if string_utils.xstr(row["TreatCode1"]) in [
            "C01",
            "C02",
            "C03",
            "C04",
        ]:  # 小兒氣喘, 小兒腦性麻痺
            set_A21 = False
            sql = f"""
                SELECT cases.*, person.ID AS DoctorID FROM cases
                    LEFT JOIN person ON cases.Doctor = person.Name
                WHERE
                    CaseKey = {case_key} AND
                    person.Position IN ("醫師", "支援醫師")
            """
        else:
            patient_key = row["PatientKey"]
            auxiliary_treat = tuple(nhi_utils.AUXILIARY_CARE_TREAT)
            sql = f'''
                SELECT cases.*, person.ID AS DoctorID FROM cases
                    LEFT JOIN person ON cases.Doctor = person.Name
                WHERE
                    (person.Position IN ("醫師", "支援醫師")) AND
                    (InsType = "健保") AND
                    (Card != "欠卡") AND
                    (TreatType IN {auxiliary_treat}) AND
                    (PatientKey = {patient_key}) AND
                    (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                    ({apply_type_sql})
                ORDER BY CaseDate
            '''

        rows = self.database.select_record(sql)

        self.sequence = 0
        identifier = case_utils.get_identifier(self.database, case_key, "就醫識別碼")
        self._set_auxiliary_case(
            dbody, row, rows[0], "2", identifier
        )  # order_type = 2 診療明細, 4 = 不另計價

        # 2026-05-09 增加虛擬健保卡虛擬醫令 (申報指標獎勵金)
        for case_row in rows:
            case_key = case_row["CaseKey"]
            identifier = case_utils.get_identifier(
                self.database, case_key, "就醫識別碼"
            )

            self._set_auxiliary_case(dbody, row, case_row, "4", identifier)  # 不另計價
            # treat_code = nhi_utils.get_treat_code(self.database, case_row['CaseKey'])
            # self.set_treatment(dbody, row, case_row, None, treat_code, '4')
            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                self._set_prescript(
                    dbody,
                    row,
                    case_row,
                    prescript_rows,
                    case_key,
                    number_utils.get_integer(case_row["Continuance"]),
                    identifier,
                    set_A21=set_A21,
                )

    def _set_auxiliary_case(self, dbody, row, case_row, order_type, identifier):
        pdata = ET.SubElement(dbody, "pdata")

        self.sequence += 1
        treat_code = string_utils.xstr(row["TreatCode1"])
        amount = number_utils.get_integer(row["TreatFee1"])
        percent = number_utils.get_integer(row["Percent1"])
        unit_price = number_utils.get_integer(
            charge_utils.get_ins_fee_from_ins_code(
                self.database, treat_code, case_date=case_row["CaseDate"]
            )
        )
        # unit_price = number_utils.round_up(amount / percent * 100)
        doctor_id = personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(case_row["Doctor"]), "ID"
        )

        p2 = ET.SubElement(pdata, "p2")
        p2.text = "0"  # 0=自行調劑或物理治療

        p3 = ET.SubElement(pdata, "p3")
        p3.text = order_type

        p4 = ET.SubElement(pdata, "p4")
        p4.text = treat_code
        p8 = ET.SubElement(pdata, "p8")
        p8.text = f"{percent:06.2f}"
        p10 = ET.SubElement(pdata, "p10")
        p10.text = "1"  # 總量
        p11 = ET.SubElement(pdata, "p11")
        p11.text = string_utils.xstr(unit_price)  # 單價
        p12 = ET.SubElement(pdata, "p12")
        p12.text = string_utils.xstr(amount)  # 點數
        p13 = ET.SubElement(pdata, "p13")
        p13.text = string_utils.xstr(self.sequence)  # 序號

        case_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
        p14 = ET.SubElement(pdata, "p14")
        p14.text = f"{case_date}0000"
        p15 = ET.SubElement(pdata, "p15")
        p15.text = f"{case_date}0000"

        p16 = ET.SubElement(pdata, "p16")
        p16.text = doctor_id

        p17 = ET.SubElement(pdata, "p17")
        p17.text = "2"  # 同一療程

        p20 = ET.SubElement(pdata, "p20")
        p20.text = string_utils.xstr(row["Class"])

        if identifier not in [None, ""]:
            p26 = ET.SubElement(pdata, "p26")
            p26.text = identifier

    def _set_special_care(self, dbody, row, case_row, identifier):
        case_key = case_row["CaseKey"]
        sql = f"""
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 11 AND
                MedicineType = "照護"
            ORDER BY PrescriptKey
        """
        rows = self.database.select_record(sql)

        for care_row in rows:
            pdata = ET.SubElement(dbody, "pdata")

            self.sequence += 1
            amount = number_utils.get_integer(care_row["Price"])
            percent = 100
            unit_price = number_utils.round_up(amount / percent * 100)

            p2 = ET.SubElement(pdata, "p2")
            p2.text = "0"  # 0=自行調劑或物理治療
            p3 = ET.SubElement(pdata, "p3")
            p3.text = "2"  # 2=診療明細
            p4 = ET.SubElement(pdata, "p4")
            p4.text = string_utils.xstr(care_row["InsCode"])
            p8 = ET.SubElement(pdata, "p8")
            p8.text = f"{percent:06.2f}"
            p10 = ET.SubElement(pdata, "p10")
            p10.text = "1"  # 總量
            p11 = ET.SubElement(pdata, "p11")
            p11.text = string_utils.xstr(unit_price)  # 單價
            p12 = ET.SubElement(pdata, "p12")
            p12.text = string_utils.xstr(amount)  # 點數
            p13 = ET.SubElement(pdata, "p13")
            p13.text = string_utils.xstr(self.sequence)  # 序號

            case_date = date_utils.west_date_to_nhi_date(case_row["CaseDate"])
            p14 = ET.SubElement(pdata, "p14")
            p14.text = f"{case_date}0000"
            p15 = ET.SubElement(pdata, "p15")
            p15.text = f"{case_date}0000"

            p16 = ET.SubElement(pdata, "p16")
            p16.text = string_utils.xstr(case_row["DoctorID"])

            p17 = ET.SubElement(pdata, "p17")
            p17.text = "2"  # 同一療程

            p20 = ET.SubElement(pdata, "p20")
            p20.text = string_utils.xstr(row["Class"])

            if identifier not in [None, ""]:
                p26 = ET.SubElement(pdata, "p26")
                p26.text = identifier

    def _get_name(self, in_name):
        in_name = re.sub(r"[\x00-\x1F\x7F]", "", in_name)

        name = ""
        for ch in in_name:
            try:
                name += str(ch).encode("big5").decode("big5")
            except Exception:
                name += "◇"

        return name[:20]  # 只上傳20bytes

    def _get_ins_rows(self):
        sql = f'''
            SELECT * FROM insapply
            WHERE
                (ClinicID = "{self.clinic_id}") AND
                (ApplyDate = "{self.apply_date}") AND
                (ApplyPeriod = "{self.period}") AND
                (ApplyType = "{self.apply_type_code}")
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_case_rows(self, case_key):
        sql = f'''
            SELECT cases.*, person.ID AS DoctorID FROM cases
                LEFT JOIN person ON cases.Doctor = person.Name
            WHERE
                CaseKey = "{case_key}" AND
                person.Position IN ("醫師", "支援醫師")
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_prescript_rows(self, case_key):
        sql = f'''
            SELECT *
            FROM prescript
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet = 1 AND
                InsCode IS NOT NULL AND
                MedicineName NOT LIKE "%清冠一號%" AND
                MedicineType NOT IN ("處置", "穴道") AND
                LENGTH(InsCode) > 0
            ORDER BY PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        return rows

    def _zip_xml_file(self, xml_file):
        xml_dir = nhi_utils.get_dir(self.system_settings, "申報路徑")
        zip_file_name = self.ins_total_fee["apply_date"]
        zip_file = f"{xml_dir}/{zip_file_name}-{self.apply_type_code}.zip"

        cmd = ["7z", "a", "-tzip", zip_file, xml_file, f"-o{xml_dir}"]
        sp = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        sp.communicate()

    def _add_home_care_case(self, dbody, row):
        self.sequence = 0
        for course in range(1, nhi_utils.MAX_HOME_CARE + 1):
            case_key = number_utils.get_integer(row[f"CaseKey{course}"])
            if case_key <= 0:
                continue

            rows = self._get_case_rows(case_key)
            if len(rows) <= 0:
                continue

            case_row = rows[0]

            # self._set_diagnosis(dbody, row)

            diag_code = nhi_utils.get_diag_code(
                self.database,
                self.system_settings,
                string_utils.xstr(case_row["Doctor"]),
                string_utils.xstr(case_row["RegistType"]),
                string_utils.xstr(case_row["TreatType"]),
                number_utils.get_integer(case_row["DiagFee"]),
            )

            identifier = case_utils.get_identifier(
                self.database, case_key, "就醫識別碼"
            )
            self._set_treatment(
                dbody, row, case_row, course, diag_code, "居家醫療", identifier
            )

            treat_code = string_utils.xstr(row[f"TreatCode{course}"])
            if treat_code != "":
                order_type = "2"
                self._set_treatment(
                    dbody, row, case_row, course, treat_code, order_type, identifier
                )

            prescript_rows = self._get_prescript_rows(case_key)
            if len(prescript_rows) > 0:
                self._set_prescript(
                    dbody, row, case_row, prescript_rows, case_key, course, identifier
                )

    def _add_infectious_case(self, dbody, row):
        self.sequence = 0
        course = 1

        case_key = number_utils.get_integer(row[f"CaseKey{course}"])
        if case_key <= 0:
            return

        rows = self._get_case_rows(case_key)
        if len(rows) <= 0:
            return

        case_row = rows[0]

        identifier = case_utils.get_identifier(self.database, case_key, "就醫識別碼")
        ins_total_fee = number_utils.get_integer(row["InsTotalFee"])
        diag_fee = number_utils.get_integer(row["DiagFee"])
        treat_fee = number_utils.get_integer(row["TreatFee"])

        infectious_drug_fee = charge_utils.get_ins_fee_from_ins_code(
            self.database, "E5012C", case_date=case_row["CaseDate"]
        )  # 台灣清冠一號補助費
        pres_days = case_utils.get_pres_days(self.database, case_row["CaseKey"])

        if ins_total_fee == (infectious_drug_fee * pres_days):
            self._set_treatment(
                dbody,
                row,
                case_row,
                course,
                "E5012C",
                "台灣清冠一號藥品補助費",
                identifier,
            )
            # self._set_infectious_virtual_code(dbody, row, case_row)  # 以下這兩行會造成申報檢核錯誤 2023-06-05 澄美
            # self._set_covid19(dbody, row, case_row, pres_days, ins_code='ViT-COVID19')
        else:
            if diag_fee > 0:
                self._set_diagnosis(dbody, row, identifier)

            if treat_fee > 0:
                self._set_treatment(
                    dbody, row, case_row, course, "E5204C", "遠距診療費", identifier
                )

            self._set_infectious_virtual_code(dbody, row, case_row, identifier)
            self._set_covid19(
                dbody, row, case_row, pres_days, identifier, ins_code="ViT-COVID19"
            )

            infectious_drug = prescript_utils.get_infectious_drug(
                self.database, case_key
            )
            if infectious_drug in ["台灣清冠一號及科學中藥", "科學中藥"]:
                prescript_rows = self._get_prescript_rows(case_key)
                if len(prescript_rows) > 0:
                    self._set_prescript(
                        dbody,
                        row,
                        case_row,
                        prescript_rows,
                        case_key,
                        course,
                        identifier,
                    )

    def _add_infectious_drug(self, dbody, row, identifier):
        self.sequence = 0
        course = 1

        case_key = number_utils.get_integer(row[f"CaseKey{course}"])
        if case_key <= 0:
            return

        rows = self._get_case_rows(case_key)
        if len(rows) <= 0:
            return

        case_row = rows[0]

        pres_days = case_utils.get_pres_days(self.database, case_row["CaseKey"])
        self._set_treatment(
            dbody, row, case_row, course, "E5012C", "台灣清冠一號藥品補助費", identifier
        )
        # self._set_infectious_virtual_code(dbody, row, case_row)
        # self._set_covid19(dbody, row, case_row, pres_days, ins_code='ViT-COVID19')
