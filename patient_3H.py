# -*- coding: UTF-8 -*-


import json

from PyQt5 import QtWidgets

from libs import string_utils, system_utils, ui_utils


# 三高加強照護 202
class Patient3H(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Patient3H, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None
        self.assessment_key = None

        self._set_ui()
        self._set_dict()
        self._set_signal()

        self._read_3H_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_3H, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        system_utils.set_date_edit(self.ui.dateEdit_case_date, "未收案")
        system_utils.set_date_edit(self.ui.dateEdit_visit_date, "尚未結案")
        system_utils.set_date_edit(self.ui.dateEdit_close_date, "尚未結案")

        system_utils.CalendarPopupFixer(self.ui.dateEdit_case_date)
        system_utils.CalendarPopupFixer(self.ui.dateEdit_close_date)
        system_utils.CalendarPopupFixer(self.ui.dateEdit_visit_date)

        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QSpinBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QDateTimeEdit)

    def _set_dict(self):
        self.close_reason_radio_dict = {
            self.ui.radioButton_close1: "1",  # 死亡
            self.ui.radioButton_close2: "2",  # 遷徙
            self.ui.radioButton_close3: "3",  # 不同意收案
            self.ui.radioButton_close4: "X",  # 其他
        }

        self.job_radio_dict = {
            self.ui.radioButton_job1: "1",  # 退休
            self.ui.radioButton_job2: "2",  # 農
            self.ui.radioButton_job3: "3",  # 軍公教
            self.ui.radioButton_job4: "4",  # 工
            self.ui.radioButton_job5: "5",  # 商
            self.ui.radioButton_job6: "6",  # 服務業
            self.ui.radioButton_job7: "7",  # 家管
            self.ui.radioButton_job9: "9",  # 其他
        }
        self.family_check_dict = {
            self.ui.checkBox_family1: "01",  # 新婚夫婦
            self.ui.checkBox_family2: "02",  # 第一個小孩誕生
            self.ui.checkBox_family3: "03",  # 有學齡兒童
            self.ui.checkBox_family4: "04",  # 有青少年子女
            self.ui.checkBox_family5: "05",  # 子女外出創業
            self.ui.checkBox_family6: "06",  # 空巢
            self.ui.checkBox_family7: "07",  # 老化的家庭
            self.ui.checkBox_family99: "99",  # 其他
        }

        self.social_check_dict = {
            self.ui.checkBox_social1: "1",  # 生活有目標
            self.ui.checkBox_social2: "2",  # 靈性宗教活動
            self.ui.checkBox_social3: "3",  # 團體聚會活動
            self.ui.checkBox_social4: "4",  # 家人朋友相聚
            self.ui.checkBox_social5: "5",  # 待在大自然
        }

        self.smoking_radio_dict = {
            self.ui.radioButton_smoking1: "1",  # 無
            self.ui.radioButton_smoking2: "2",  # 偶爾交際應酬
            self.ui.radioButton_smoking3: "3",  # 平均一天約吸10支菸以下
            self.ui.radioButton_smoking4: "4",  # 平均一天約吸10支菸(含)以上
        }
        self.drinking_radio_dict = {
            self.ui.radioButton_drinking1: "1",  # 無
            self.ui.radioButton_drinking2: "2",  # 偶爾交際應酬(每週1-2天)
            self.ui.radioButton_drinking3: "3",  # 經常喝(每週>2天)
        }
        self.betel_nut_radio_dict = {
            self.ui.radioButton_betel_nut1: "1",  # 無
            self.ui.radioButton_betel_nut2: "2",  # 偶爾交際應酬(每週1-2天)
            self.ui.radioButton_betel_nut3: "3",  # 經常嚼或習慣在嚼(每週>2天)
        }

        self.chronic_check_dict = {
            self.ui.checkBox_chronic1: "01",  # 高血壓
            self.ui.checkBox_chronic2: "02",  # 糖尿病
            self.ui.checkBox_chronic3: "03",  # 腎臟病
            self.ui.checkBox_chronic4: "04",  # 缺血性心臟病
            self.ui.checkBox_chronic5: "05",  # 心律不整
            self.ui.checkBox_chronic6: "06",  # 心臟衰竭
            self.ui.checkBox_chronic7: "07",  # 腦血管疾病
            self.ui.checkBox_chronic8: "08",  # 腫瘤
            self.ui.checkBox_chronic9: "09",  # 貧血
            self.ui.checkBox_chronic10: "10",  # 關節炎
            self.ui.checkBox_chronic11: "11",  # 高膽固醇血症
            self.ui.checkBox_chronic12: "12",  # 痛風或高尿酸血症
            self.ui.checkBox_chronic13: "13",  # 過敏性鼻炎
            self.ui.checkBox_chronic14: "14",  # 氣喘
            self.ui.checkBox_chronic15: "15",  # 慢性肺疾病
            self.ui.checkBox_chronic16: "16",  # 消化性潰瘍
            self.ui.checkBox_chronic17: "17",  # 功能性腸胃問題
            self.ui.checkBox_chronic99: "99",  # 其他
        }

        # 家族病史：h欄位 -> {checkBox: 家屬代碼}
        # objectName 規則假設為 checkBox_family_history_{h編號}_{代碼小寫}
        self.family_history_dict = {}
        family_history_items = [
            ("h020", "dm"),  # 糖尿病
            ("h021", "hbp"),  # 高血壓
            ("h022", "heart"),  # 心臟病
            ("h023", "stroke"),  # 腦血管病變
            ("h024", "lipid"),  # 高血脂
            ("h025", "kidney"),  # 腎臟病或尿毒症
            ("h026", "cancer"),  # 惡性腫瘤
            ("h027", "hereditary"),  # 遺傳性腎臟疾病
            ("h028", "polycystic"),  # 多囊腎
            ("h029", "gout"),  # 痛風
            ("h030", "autoimmune"),  # 自體免疫性疾病
            ("h032", "other"),  # 其他(家屬代碼)
        ]
        for h_code, name in family_history_items:
            self.family_history_dict[h_code] = {
                getattr(self.ui, f"checkBox_{name}_a"): "A",  # 父
                getattr(self.ui, f"checkBox_{name}_b"): "B",  # 母
                getattr(self.ui, f"checkBox_{name}_c"): "C",  # 兒女
                getattr(self.ui, f"checkBox_{name}_d"): "D",  # 兄弟姊妹
                getattr(self.ui, f"checkBox_{name}_e"): "E",  # 父系親戚
                getattr(self.ui, f"checkBox_{name}_f"): "F",  # 母系親戚
                getattr(self.ui, f"checkBox_{name}_g"): "G",  # 其他
            }
        self.medicine_check_dict = {
            self.ui.checkBox_medicine1: "01",  # 降血壓藥
            self.ui.checkBox_medicine2: "02",  # 胰島素
            self.ui.checkBox_medicine3: "03",  # 降血糖藥
            self.ui.checkBox_medicine4: "04",  # 降血脂藥
            self.ui.checkBox_medicine5: "05",  # 降尿酸藥
            self.ui.checkBox_medicine6: "06",  # NSAID
            self.ui.checkBox_medicine7: "07",  # 中草藥
            self.ui.checkBox_medicine99: "99",  # 其他
        }

    # 設定信號
    def _set_signal(self):
        pass

    def _read_3H_data(self):
        self._read_patient_data()
        self._read_assessment_data()

    def _read_patient_data(self):
        sql = """
            SELECT * FROM patient
            WHERE
                PatientKey = %s
        """
        params = (self.patient_key,)
        rows = self.database.select_record(sql, params)
        if not rows:
            return

        row = rows[0]

        self.ui.label_name.setText(
            f"姓名: {string_utils.xstr(row['Name'])} ({string_utils.xstr(row['Gender'])})"
        )
        self.ui.label_birthday.setText(f"生日: {row['Birthday'].strftime('%Y-%m-%d')}")
        self.ui.label_ID.setText(f"身份證: {string_utils.xstr(row['ID'])}")
        phone = string_utils.xstr(row["Cellphone"]) or string_utils.xstr(
            row["Telephone"]
        )
        self.ui.label_telephone.setText(f"電話: {phone}")
        self.ui.label_address.setText(f"地址: {string_utils.xstr(row['Address'])}")

    def _read_assessment_data(self):
        sql = """
            SELECT * FROM patient_assessment
            WHERE
                PatientKey = %s AND AssessmentType = 'FB'
            ORDER BY AssessmentKey DESC
            LIMIT 1
        """
        params = (self.patient_key,)
        rows = self.database.select_record(sql, params)
        if not rows:
            return

        row = rows[0]

        self.assessment_key = row["AssessmentKey"]

        system_utils.db_to_date_edit(self.ui.dateEdit_case_date, row["CaseDate"])
        system_utils.db_to_date_edit(self.ui.dateEdit_visit_date, row["VisitDate"])
        system_utils.db_to_date_edit(self.ui.dateEdit_close_date, row["CloseDate"])

        self.ui.lineEdit_doctor_id.setText(string_utils.xstr(row["Doctor"]))
        self._set_close_reason(row["CloseReason"])
        self._read_content(row["Content"])

    def _set_close_reason(self, close_reason):
        reverse_dict = {v: k for k, v in self.close_reason_radio_dict.items()}
        radio_button = reverse_dict.get(string_utils.xstr(close_reason))
        if radio_button is not None:
            radio_button.setChecked(True)

    def _read_content(self, content_json):
        if not content_json:
            return  # 新個案或舊資料沒有明細

        content = json.loads(content_json)

        self._set_basic(content)
        self._set_lifestyle(content)
        self._set_habit(content)
        self._set_chronic(content)
        self._set_family(content)
        self._set_medicine(content)
        self._set_allergy(content)
        self._set_vital(content)

    def _set_basic(self, content):
        self.ui.lineEdit_caregiver.setText(string_utils.xstr(content.get("h003")))
        system_utils.set_radio_value(self.job_radio_dict, content.get("h004"))
        self.ui.lineEdit_job_other.setText(string_utils.xstr(content.get("h005")))
        self.ui.lineEdit_zip_code.setText(string_utils.xstr(content.get("h006")))
        system_utils.set_check_values(self.family_check_dict, content.get("h007"))
        self.ui.lineEdit_family_other.setText(string_utils.xstr(content.get("h008")))

    def _set_lifestyle(self, content):
        system_utils.set_check_values(self.social_check_dict, content.get("h009_items"))
        self.ui.spinBox_ls13.setValue(content.get("ls13") or 0)
        system_utils.set_combo_box_text(self.ui.comboBox_ls19, content.get("ls19"))
        system_utils.set_combo_box_text(self.ui.comboBox_ls22, content.get("ls22"))

        self.ui.checkBox_ls06.setChecked(content.get("ls06") == 1)
        self.ui.checkBox_ls11.setChecked(content.get("ls11") == 1)
        system_utils.set_combo_box_text(self.ui.comboBox_ls15, content.get("ls15"))
        system_utils.set_combo_box_text(self.ui.comboBox_ls16, content.get("ls16"))

        self.ui.checkBox_ls04.setChecked(content.get("ls04") == 1)
        self.ui.checkBox_ls08.setChecked(content.get("ls08") == 1)
        self.ui.checkBox_ls10.setChecked(content.get("ls10") == 1)
        system_utils.set_combo_box_text(self.ui.comboBox_ls17, content.get("ls17"))

        self.ui.checkBox_ls02.setChecked(content.get("ls02") == 1)
        self.ui.checkBox_ls12.setChecked(content.get("ls12") == 1)
        system_utils.set_combo_box_text(self.ui.comboBox_ls14, content.get("ls14"))
        system_utils.set_combo_box_text(self.ui.comboBox_ls18, content.get("ls18"))
        system_utils.set_combo_box_text(self.ui.comboBox_ls20, content.get("ls20"))
        system_utils.set_combo_box_text(self.ui.comboBox_ls21, content.get("ls21"))

    def _set_habit(self, content):
        system_utils.set_radio_value(self.smoking_radio_dict, content.get("h014"))
        system_utils.set_radio_value(self.drinking_radio_dict, content.get("h015"))
        system_utils.set_radio_value(self.betel_nut_radio_dict, content.get("h016"))

    def _set_chronic(self, content):
        system_utils.set_check_values(self.chronic_check_dict, content.get("h017"))
        self.ui.lineEdit_chronic_other.setText(string_utils.xstr(content.get("h018")))

    def _set_family(self, content):
        for h_code, check_dict in self.family_history_dict.items():
            codes = content.get(h_code) or ""
            for check_box, code in check_dict.items():
                check_box.setChecked(code in codes)

        self.ui.lineEdit_family_history_other.setText(
            string_utils.xstr(content.get("h031"))
        )
        self.ui.checkBox_family_history_unknown.setChecked(content.get("h033") == "Y")
        # h019 是推導值，不需回填

    def _set_medicine(self, content):
        system_utils.set_check_values(self.medicine_check_dict, content.get("h034"))
        self.ui.lineEdit_medicine_other.setText(string_utils.xstr(content.get("h035")))

    def _set_allergy(self, content):
        self.ui.lineEdit_food_allergy.setText(string_utils.xstr(content.get("h036")))
        self.ui.lineEdit_drug_allergy.setText(string_utils.xstr(content.get("h037")))

    def _set_vital(self, content):
        self.ui.spinBox_height.setValue(content.get("h038") or 0)
        self.ui.spinBox_weight.setValue(content.get("h039") or 0)
        self.ui.spinBox_waist.setValue(content.get("h040") or 0)
        self.ui.spinBox_systolic.setValue(content.get("h041") or 0)
        self.ui.spinBox_diastolic.setValue(content.get("h042") or 0)
        self.ui.spinBox_pulse.setValue(content.get("h043") or 0)

    def save_assessment(self, patient_key):
        case_date = system_utils.date_edit_to_db(self.ui.dateEdit_case_date)
        if case_date is None:
            return

        close_date = system_utils.date_edit_to_db(self.ui.dateEdit_close_date)
        visit_date = system_utils.date_edit_to_db(self.ui.dateEdit_visit_date)  # c003
        doctor_id = self.ui.lineEdit_doctor_id.text() or None  # d007
        case_type = "A"  # d008
        close_reason = (
            system_utils.get_radio_value(self.close_reason_radio_dict)
            if close_date is not None
            else None
        )

        if self.assessment_key is None:
            sql = """
                INSERT INTO patient_assessment
                    (PatientKey, AssessmentType, FormVersion,
                    Doctor, CaseType, CaseDate,
                    VisitDate, CloseDate, CloseReason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                patient_key,
                "FB",
                "1.0",
                doctor_id,
                case_type,
                case_date,
                visit_date,
                close_date,
                close_reason,
            )
            self.assessment_key = self.database.exec_sql(sql, params)
        else:
            sql = """
                UPDATE patient_assessment SET
                    Doctor = %s, CaseType = %s, CaseDate = %s,
                    VisitDate = %s, CloseDate = %s, CloseReason = %s
                WHERE AssessmentKey = %s
            """
            params = (
                doctor_id,
                case_type,
                case_date,
                visit_date,
                close_date,
                close_reason,
                self.assessment_key,
            )
            self.database.exec_sql(sql, params)

        self.save_content()  # 主檔存完接著存明細

    def save_content(self):
        content = {}
        content.update(self._collect_basic())  # h003~h008 照顧者/職業/家庭週期
        content.update(self._collect_lifestyle())  # h009~h013 生活型態量表
        content.update(self._collect_habit())  # h014~h016 菸酒檳榔
        content.update(self._collect_chronic())  # h017~h018 慢性病史
        content.update(self._collect_family())  # h019~h033 家族病史
        content.update(self._collect_medicine())  # h034~h035 長期藥物
        content.update(self._collect_allergy())  # h036~h037 過敏史
        content.update(self._collect_vital())  # h038~h043 身高體重血壓

        sql = """
            UPDATE patient_assessment SET
                Content = %s
            WHERE AssessmentKey = %s
        """
        params = (
            json.dumps(content, ensure_ascii=False),
            self.assessment_key,
        )
        self.database.exec_sql(sql, params)

    def _collect_basic(self):
        job = system_utils.get_radio_value(self.job_radio_dict)
        family_cycle = system_utils.get_check_values(self.family_check_dict)

        return {
            "h003": self.ui.lineEdit_caregiver.text(),  # 主要照顧者
            "h004": job,  # 職業別
            "h005": self.ui.lineEdit_job_other.text(),  # 職業別其他
            "h006": self.ui.lineEdit_zip_code.text(),  # 郵遞區號
            "h007": family_cycle,  # 家庭生命週期
            "h008": self.ui.lineEdit_family_other.text(),  # 家庭週期其他
        }

    def _collect_lifestyle(self):
        social_items = system_utils.get_check_values(self.social_check_dict)

        return {
            "h009_items": social_items,
            # 身體活動
            "ls13": self.ui.spinBox_ls13.value(),
            "ls19": self.ui.comboBox_ls19.currentText(),
            "ls22": self.ui.comboBox_ls22.currentText(),
            # 避免危害物質
            "ls06": int(self.ui.checkBox_ls06.isChecked()),  # 抽菸/電子煙
            "ls11": int(self.ui.checkBox_ls11.isChecked()),  # 嚼檳榔
            "ls15": self.ui.comboBox_ls15.currentText(),  # 單日最多酒精單位
            "ls16": self.ui.comboBox_ls16.currentText(),  # 平均每天酒精單位
            # 睡眠與壓力管理
            "ls04": int(self.ui.checkBox_ls04.isChecked()),  # 能處理生活壓力
            "ls08": int(self.ui.checkBox_ls08.isChecked()),  # 睡醒精神好
            "ls10": int(self.ui.checkBox_ls10.isChecked()),  # 有時間照顧自己
            "ls17": self.ui.comboBox_ls17.currentText(),  # 每晚睡眠小時
            # 營養
            "ls02": int(self.ui.checkBox_ls02.isChecked()),  # 避免油炸
            "ls12": int(self.ui.checkBox_ls12.isChecked()),  # 原型食物為主
            "ls14": self.ui.comboBox_ls14.currentText(),  # 含糖飲料杯數
            "ls18": self.ui.comboBox_ls18.currentText(),  # 水果份數
            "ls20": self.ui.comboBox_ls20.currentText(),  # 包裝零食包數
            "ls21": self.ui.comboBox_ls21.currentText(),  # 蔬菜份數
        }

    def _collect_habit(self):
        return {
            "h014": system_utils.get_radio_value(self.smoking_radio_dict),  # 抽菸
            "h015": system_utils.get_radio_value(self.drinking_radio_dict),  # 喝酒
            "h016": system_utils.get_radio_value(self.betel_nut_radio_dict),  # 嚼檳榔
        }

    def _collect_chronic(self):
        return {
            # h017 全沒勾存 None，產 XML 時轉為 'N'(無)
            "h017": system_utils.get_check_values(self.chronic_check_dict),
            "h018": self.ui.lineEdit_chronic_other.text(),  # 含99時必填
        }

    def _collect_family(self):
        content = {
            "h031": self.ui.lineEdit_family_history_other.text(),  # 其他-病名
            "h033": "Y" if self.ui.checkBox_family_history_unknown.isChecked() else "N",
        }
        any_checked = False
        for h_code, check_dict in self.family_history_dict.items():
            codes = "".join(
                code for check_box, code in check_dict.items() if check_box.isChecked()
            )
            content[h_code] = codes or None
            if codes:
                any_checked = True

        # h019: Y=無家族病史。UI 沒有「無」的勾選，以「全部沒勾且未勾不知」推導
        if any_checked or content["h033"] == "Y":
            content["h019"] = "N"
        else:
            content["h019"] = "Y"

        return content

    def _collect_medicine(self):
        return {
            # h034 全沒勾存 None，產 XML 時轉為 'N'(無)，同 h017 約定
            "h034": system_utils.get_check_values(self.medicine_check_dict),
            "h035": self.ui.lineEdit_medicine_other.text(),  # 含99時必填
        }

    def _collect_allergy(self):
        return {
            # h036/h037 空白存原樣，產 XML 時空值轉 'N'(無)，同 h017/h034 約定
            "h036": self.ui.lineEdit_food_allergy.text(),  # 食物過敏史
            "h037": self.ui.lineEdit_drug_allergy.text(),  # 藥物過敏史
        }

    def _collect_vital(self):
        return {
            "h038": self.ui.spinBox_height.value(),  # 身高 80~250
            "h039": self.ui.spinBox_weight.value(),  # 體重 20~300
            "h040": self.ui.spinBox_waist.value(),  # 腰圍 20~200
            "h041": self.ui.spinBox_systolic.value(),  # 收縮壓 50~300
            "h042": self.ui.spinBox_diastolic.value(),  # 舒張壓 20~250
            "h043": self.ui.spinBox_pulse.value(),  # 脈搏
        }
