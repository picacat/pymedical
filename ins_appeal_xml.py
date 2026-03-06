# -*- coding: UTF-8 -*-

import datetime
import os
import subprocess

from lxml import etree as ET
from PyQt5 import QtCore, QtWidgets

from libs import date_utils, nhi_utils, number_utils, string_utils, xml_utils


# 上傳申復資料 2023.05.25
class InsAppealXML(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsAppealXML, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.apply_date = args[4]
        self.apply_period = args[5]
        self.apply_type_code = args[6]
        self.clinic_id = args[7]
        self.apply_upload_date = args[8]

        self.ui = None

        self.xml_file_name = nhi_utils.get_ins_appeal_xml_file_name(
            self.system_settings, self.apply_type_code, self.apply_date
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
        pass

    # 設定信號
    def _set_signal(self):
        pass

    def create_xml_file(self):
        xml_dir = nhi_utils.get_dir(self.system_settings, "申報路徑")
        if not os.path.exists(xml_dir):
            os.mkdir(xml_dir)

        self._write_xml_file(self.xml_file_name)
        self._zip_xml_file(self.xml_file_name)

    def get_xml_file_name(self):
        return self.xml_file_name

    def _zip_xml_file(self, xml_file):
        xml_dir = nhi_utils.get_dir(self.system_settings, "申報路徑")
        zip_file = self.xml_file_name.replace("xml", "zip")

        cmd = ["7z", "a", "-tzip", zip_file, xml_file, f"-o{xml_dir}"]
        sp = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        sp.communicate()

    def _get_ddata_rows(self):
        sql = f'''
            SELECT * FROM insappeal
            WHERE
                (ClinicID = "{self.clinic_id}") AND
                (ApplyDate = "{self.apply_date}") AND
                (ApplyPeriod = "{self.apply_period}") AND
                (ApplyType = "{self.apply_type_code}") AND
                (Sample != "統扣")
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_edata_rows(self):
        sql = f'''
            SELECT * FROM insappeal
            WHERE
                (ClinicID = "{self.clinic_id}") AND
                (ApplyDate = "{self.apply_date}") AND
                (ApplyPeriod = "{self.apply_period}") AND
                (ApplyType = "{self.apply_type_code}") AND
                (Sample = "統扣")
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        return rows

    def _write_xml_file(self, xml_file_name):
        rows = self._get_ddata_rows()
        record_count = len(rows)
        if record_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生申復XML檔中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        root = ET.Element("outpatient")
        self._add_tdata(root)
        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            self._add_ddata(root, row)

        self._add_edata(root)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

        tree = ET.ElementTree(root)
        tree.write(
            xml_file_name, pretty_print=True, xml_declaration=True, encoding="Big5"
        )
        xml_utils.set_xml_file_to_big5(xml_file_name)

    def _get_ins_total_points(self):
        rows = self._get_ddata_rows()
        general_case, general_point = 0, 0
        special_case, special_point = 0, 0
        for row in rows:
            ins_appeal_key = row["InsAppealKey"]
            ins_appeal_items_total_points = self._get_ins_appeal_items_total_points(
                ins_appeal_key
            )

            if string_utils.xstr(row["CaseType"]) == "21":
                general_case += 1
                general_point += ins_appeal_items_total_points
            else:
                special_case += 1
                special_point += ins_appeal_items_total_points

        return general_case, general_point, special_case, special_point

    def _get_reject_total_points(self):
        rows = self._get_edata_rows()
        reject_case, reject_point = 0, 0
        for row in rows:
            ins_appeal_key = row["InsAppealKey"]
            ins_appeal_items_reject_points = self._get_ins_appeal_items_total_points(
                ins_appeal_key
            )

            reject_case += 1
            reject_point += ins_appeal_items_reject_points

        return reject_case, reject_point

    def _get_ins_appeal_items(self, ins_appeal_key):
        sql = f"""
            SELECT insappeal_items.*, insappeal.CaseType, insappeal.Sequence
            FROM insappeal_items
                LEFT JOIN insappeal ON insappeal.InsAppealKey = insappeal_items.InsAppealKey
            WHERE
                insappeal_items.InsAppealKey = {ins_appeal_key}
        """
        rows = self.database.select_record(sql)

        return rows

    def _get_ins_appeal_items_total_points(self, ins_appeal_key):
        rows = self._get_ins_appeal_items(ins_appeal_key)

        total_points = 0
        for row in rows:
            point = number_utils.get_integer(row["Point"])
            quantity = number_utils.get_integer(row["Quantity"])
            # total_points += point * quantity
            total_points += point

        return total_points

    def _add_tdata(self, root):
        today = date_utils.west_date_to_nhi_date(datetime.datetime.now())
        upload_year = self.apply_upload_date.year() - 1911
        upload_month = self.apply_upload_date.month()
        upload_day = self.apply_upload_date.day()
        apply_upload_date = f"{upload_year:0>3}{upload_month:0>2}{upload_day:0>2}"

        general_case, general_points, special_case, special_points = (
            self._get_ins_total_points()
        )
        reject_case, reject_points = self._get_reject_total_points()

        tdata = ET.SubElement(root, "tdata")
        t1 = ET.SubElement(tdata, "t1")
        t1.text = self.clinic_id
        t2 = ET.SubElement(tdata, "t2")
        t2.text = self.apply_date
        t3 = ET.SubElement(tdata, "t3")
        t3.text = "4"  # 申復送核
        t4 = ET.SubElement(tdata, "t4")
        t4.text = apply_upload_date
        t5 = ET.SubElement(tdata, "t5")
        t5.text = today  # 申報日期
        t22 = ET.SubElement(tdata, "t22")
        t22.text = string_utils.xstr(general_case)
        t23 = ET.SubElement(tdata, "t23")
        t23.text = string_utils.xstr(general_points)
        t24 = ET.SubElement(tdata, "t24")
        t24.text = string_utils.xstr(special_case)
        t25 = ET.SubElement(tdata, "t25")
        t25.text = string_utils.xstr(special_points)
        t26 = ET.SubElement(tdata, "t26")
        t26.text = string_utils.xstr(general_case + special_case)
        t27 = ET.SubElement(tdata, "t27")
        t27.text = string_utils.xstr(general_points + special_points)

        if reject_case > 0:
            t36 = ET.SubElement(tdata, "t36")
            t36.text = string_utils.xstr(reject_case)

        if reject_points > 0:
            t37 = ET.SubElement(tdata, "t37")
            t37.text = string_utils.xstr(reject_points)

        t38 = ET.SubElement(tdata, "t38")
        t38.text = string_utils.xstr(general_case + special_case + reject_case)
        t39 = ET.SubElement(tdata, "t39")
        t39.text = string_utils.xstr(general_points + special_points + reject_points)

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
        d3 = ET.SubElement(dbody, "d3")
        d3.text = nhi_utils.REPLY_SAMPLE_CODE[string_utils.xstr(row["Sample"])]

        if string_utils.xstr(row["Reject"]) == "是":
            d4 = ET.SubElement(dbody, "d4")
            d4.text = "Y"

        point1 = number_utils.get_integer(row["Point1"])  # 立意抽樣點數
        if point1 > 0:
            d5 = ET.SubElement(dbody, "d5")
            d5.text = string_utils.xstr(point1)

        point2 = number_utils.get_integer(row["Point2"])  # 電腦核減點數
        if point2 > 0:
            d6 = ET.SubElement(dbody, "d6")
            d6.text = string_utils.xstr(point2)

        point3 = number_utils.get_integer(row["Point3"])  # 回推核減點數
        if point3 > 0:
            d7 = ET.SubElement(dbody, "d7")
            d7.text = string_utils.xstr(point3)

        ins_appeal_key = row["InsAppealKey"]
        self._add_pdata(dbody, ins_appeal_key)

    def _add_pdata(self, dbody, ins_appeal_key):
        rows = self._get_ins_appeal_items(ins_appeal_key)

        for row in rows:
            pdata = ET.SubElement(dbody, "pdata")
            p1 = ET.SubElement(pdata, "p1")
            p1.text = string_utils.xstr(row["OrderSeq"])

            p2 = ET.SubElement(pdata, "p2")
            p2.text = string_utils.xstr(row["InsCode"])

            reject_code = string_utils.xstr(row["RejectCode"])
            if reject_code != "":
                p3 = ET.SubElement(pdata, "p3")
                p3.text = reject_code

            percent = number_utils.get_integer(row["Percent"])
            if percent > 0:
                p4 = ET.SubElement(pdata, "p4")
                p4.text = f"{percent:06.2f}"

            quantity = number_utils.get_integer(row["Quantity"])
            if quantity > 0:
                p5 = ET.SubElement(pdata, "p5")
                p5.text = f"{quantity:07.1f}"

            p6 = ET.SubElement(pdata, "p6")
            p6.text = string_utils.xstr(row["Point"])

            file_link = string_utils.xstr(row["FileLink"])
            if file_link == "是":
                file_link = "Y"
            else:
                file_link = "N"

            p7 = ET.SubElement(pdata, "p7")
            p7.text = file_link

            reason1 = string_utils.xstr(row["Reason1"])
            if reason1 != "":
                p8 = ET.SubElement(pdata, "p8")
                p8.text = reason1

            reason2 = string_utils.xstr(row["Reason2"])
            if reason2 != "":
                p9 = ET.SubElement(pdata, "p9")
                p9.text = reason1

    def _add_edata(self, root):
        rows = self._get_edata_rows()
        for row in rows:
            ins_appeal_key = row["InsAppealKey"]
            self._add_edata_body(root, ins_appeal_key)

    def _add_edata_body(self, root, ins_appeal_key):
        rows = self._get_ins_appeal_items(ins_appeal_key)
        for row in rows:
            edata = ET.SubElement(root, "edata")

            e1 = ET.SubElement(edata, "e1")
            e1.text = string_utils.xstr(row["CaseType"])

            e2 = ET.SubElement(edata, "e2")
            e2.text = string_utils.xstr(row["Sequence"])

            e3 = ET.SubElement(edata, "e3")
            e3.text = string_utils.xstr(row["OrderSeq"])

            e4 = ET.SubElement(edata, "e4")
            e4.text = string_utils.xstr(row["InsCode"])

            e5 = ET.SubElement(edata, "e5")
            e5.text = string_utils.xstr(row["RejectCode"])

            percent = number_utils.get_integer(row["Percent"])
            if percent > 0:
                e6 = ET.SubElement(edata, "e6")
                e6.text = f"{percent:06.2f}"

            quantity = number_utils.get_integer(row["Quantity"])
            e7 = ET.SubElement(edata, "e7")
            e7.text = f"{quantity:07.1f}"

            e8 = ET.SubElement(edata, "e8")
            e8.text = string_utils.xstr(row["Point"])

            file_link = string_utils.xstr(row["FileLink"])
            if file_link == "是":
                file_link = "Y"
            else:
                file_link = "N"

            e9 = ET.SubElement(edata, "e9")
            e9.text = file_link

            reason1 = string_utils.xstr(row["Reason1"])
            if reason1 != "":
                e10 = ET.SubElement(edata, "e10")
                e10.text = reason1

            reason2 = string_utils.xstr(row["Reason2"])
            if reason2 != "":
                e11 = ET.SubElement(edata, "e11")
                e11.text = reason2
