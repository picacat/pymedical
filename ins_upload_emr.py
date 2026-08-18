# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets

try:
    from PyPDF2 import PdfWriter as _PdfMergerClass
except Exception:
    from PyPDF2 import PdfFileMerger as _PdfMergerClass

import datetime
import os
import shutil
import subprocess
import traceback

from lxml import etree as ET

from libs import (
    date_utils,
    nhi_utils,
    printer_utils,
    string_utils,
    system_utils,
    xml_utils,
)


# 健保電子化抽審 2018.11.05
class InsUploadEMR(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_date = args[2]
        self.apply_type = args[3]
        self.period = args[4]
        self.clinic_id = args[5]
        self.apply_upload_date = args[6]
        self.months = args[7]

        self.ui = None
        self.start_no = 1
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]
        self.apply_year = int(self.apply_date[:3]) + 1911
        self.apply_month = int(self.apply_date[3:5])

        export_dir = nhi_utils.get_dir(self.system_settings, "申報路徑")
        self.EXPORT_DIR = f"{export_dir}/emr{self.apply_date}"

        # 整批作業共用同一個時間戳記, 避免跨午夜時 ATT 與 XML 檔名日期不一致
        self.now = None  # 西元 yyyymmdd
        self.nhi_now = None  # 民國日期

        self.errors = []  # 記錄每一筆的失敗原因

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
        pass

    # 設定信號
    def _set_signal(self):
        pass

    # 設定整批作業共用的時間戳記
    def _init_timestamp(self):
        if self.now is None:
            now = datetime.datetime.now()
            self.now = now.strftime("%Y%m%d")
            self.nhi_now = date_utils.west_date_to_nhi_date(now)

    # 執行 7z, 回傳 (returncode, output)
    @staticmethod
    def _run_7z(cmd):
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
        }
        # Windows 下不要閃出黑色主控台視窗
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        sp = subprocess.Popen(cmd, **kwargs)
        out, _ = sp.communicate()
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")

        return sp.returncode, string_utils.xstr(out)

    def create_emr_files(self):
        self._generate_emr_files()

    def upload_emr_files(self):
        apply_date = f"{self.apply_year}-{self.apply_month:0>2}"
        sql = f'''
            SELECT * FROM system_log
            WHERE
                LogType = "抽審日期" AND
                LogName = "{apply_date}"
        '''
        rows = self.database.select_record(sql)
        self.start_no += len(rows) * 1000

        if not self._generate_emr_files():
            return

        type_code = "15"  # 費用抽審批次上傳
        zip_file = self._get_zip_file_name()

        if not os.path.isfile(zip_file) or os.path.getsize(zip_file) <= 0:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "壓縮檔建立失敗",
                '<font size="5" color="red"><b>上傳用的壓縮檔未建立成功, 已中止上傳.</b></font>',
                f"檔案: {zip_file}",
            )
            return

        nhi_utils.NHI_SendB(self.system_settings, type_code, zip_file)

        generate_date = datetime.date.today().strftime("%Y-%m-%d")
        fields = ["LogType", "LogName", "Log"]
        data = ["抽審日期", apply_date, generate_date]
        self.database.insert_record("system_log", fields, data)

    def _generate_emr_files(self):
        self.now = None
        self._init_timestamp()
        self.errors = []

        shutil.rmtree(self.EXPORT_DIR, ignore_errors=True)
        try:
            os.makedirs(self.EXPORT_DIR, exist_ok=True)
        except OSError as e:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "無法建立輸出目錄",
                '<font size="5" color="red"><b>無法建立抽審檔輸出目錄.</b></font>',
                f"{self.EXPORT_DIR}\n{e}",
            )
            return False

        # 上一輪若有檔案被鎖住, rmtree 會靜默失敗, 這裡確認目錄確實是空的
        leftovers = [
            f
            for f in os.listdir(self.EXPORT_DIR)
            if os.path.isfile(os.path.join(self.EXPORT_DIR, f))
        ]
        if leftovers:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "輸出目錄未清空",
                '<font size="5" color="red"><b>輸出目錄殘留舊檔案, 無法清除, 請關閉佔用該目錄的程式後再執行.</b></font>',
                f"{self.EXPORT_DIR}\n殘留 {len(leftovers)} 個檔案: {', '.join(leftovers[:10])}",
            )
            return False

        sql = f'''
            SELECT
                InsApplyKey, ApplyDate, CaseType, Sequence, PatientKey, ID, Visit, CaseKey1
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Note = "*"
            ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)
        if row_count <= 0:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "無抽審資料",
                '<font size="5" color="red"><b>找不到註記的資料, 請註記流水號後再執行抽審上傳作業.</b></font>',
                "請確定讀卡機是否連接, 或VPN網路是否暢通.",
            )
            return False

        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生電子抽審檔中, 請稍後...", "取消", 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        canceled = False
        try:
            for row_no, row in enumerate(rows):
                progress_dialog.setValue(row_no)
                if progress_dialog.wasCanceled():
                    canceled = True
                    break

                case_type = string_utils.xstr(row["CaseType"])
                sequence = string_utils.xstr(row["Sequence"])
                try:
                    pdf_file = self._create_pdf_files(row)
                    self._zip_pdf_file(row_no, pdf_file)
                    self._create_xml_files(row_no, row, pdf_file)
                except Exception as e:
                    self.errors.append(f"{case_type}-{sequence}: {e}")
                    traceback.print_exc()
                    continue

            progress_dialog.setValue(row_count)
        finally:
            progress_dialog.close()
            progress_dialog.deleteLater()

        if canceled:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Warning,
                "已取消",
                '<font size="5" color="red"><b>抽審檔產生作業已被取消, 未產生上傳檔.</b></font>',
                "請重新執行抽審上傳作業.",
            )
            return False

        # 只要有任何一筆失敗就中止, 不要送出殘缺的批次
        if self.errors:
            detail = "\n".join(self.errors[:20])
            if len(self.errors) > 20:
                detail += f"\n... 其餘 {len(self.errors) - 20} 筆"
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "抽審檔產生失敗",
                f'<font size="5" color="red"><b>有 {len(self.errors)} 筆資料產生失敗, 已中止上傳.</b></font>',
                detail,
            )
            return False

        if not self._zip_all_files():
            return False

        return True

    # 建立抽審用pdf檔
    def _create_pdf_files(self, row):
        ins_apply_key = row["InsApplyKey"]
        patient_key = row["PatientKey"]
        case_key = row["CaseKey1"]

        start_date, end_date = date_utils.get_two_month_date(
            self.database,
            self.system_settings,
            patient_key,
            self.apply_year,
            self.apply_month,
            month_range=self.months,
        )

        case_type = string_utils.xstr(row["CaseType"]).strip()
        sequence = string_utils.xstr(row["Sequence"]).strip()

        printer_utils.print_form_medical_chart(
            self,
            self.database,
            self.system_settings,
            patient_key,
            self.apply_date,
            "pdf",
        )
        chart_file = f"{self.EXPORT_DIR}/chart_{patient_key:0>6}.pdf"

        printer_utils.print_form_medical_records(
            self,
            self.database,
            self.system_settings,
            patient_key,
            None,
            start_date,
            end_date,
            "pdf",
        )
        medical_records_file = f"{self.EXPORT_DIR}/case_{patient_key:0>6}.pdf"

        pdfs = [chart_file, medical_records_file]

        if string_utils.xstr(row["Visit"]) == "初診照護":
            printer_utils.print_form_patient_new_care(
                self,
                self.database,
                self.system_settings,
                patient_key,
                case_key,
                self.apply_date,
                "pdf",
            )
            patient_new_care_file = (
                f"{self.EXPORT_DIR}/patient_new_care_{patient_key:0>6}.pdf"
            )
            pdfs += [patient_new_care_file]

        if self.system_settings.field("健保業務") != "台北業務組":
            printer_utils.print_form_ins_apply_order(
                self,
                self.database,
                self.system_settings,
                self.apply_year,
                self.apply_month,
                self.apply_type,
                ins_apply_key,
                "pdf",
            )
            ins_order_file = (
                f"{self.EXPORT_DIR}/ins_order_{case_type}{sequence:0>6}.pdf"
            )
            pdfs += [ins_order_file]

        # 合併前先確認每一支來源檔都真的印出來了
        for pdf in pdfs:
            if not os.path.isfile(pdf):
                raise FileNotFoundError(f"來源PDF未產生: {os.path.basename(pdf)}")
            if os.path.getsize(pdf) <= 0:
                raise ValueError(f"來源PDF為空檔: {os.path.basename(pdf)}")

        filename = f"14A{case_type}{sequence:0>6}001.pdf"
        merged_pdf = f"{self.EXPORT_DIR}/{filename}"

        merger = _PdfMergerClass()
        pdf_files_stream = []
        try:
            for pdf in pdfs:
                # 舊版 PdfFileMerger 需要 stream 保持開啟到 write() 之後
                pdf_file = open(pdf, "rb")
                pdf_files_stream.append(pdf_file)
                merger.append(pdf_file)

            with open(merged_pdf, "wb") as f_out:
                merger.write(f_out)
        finally:
            # 不論成功失敗都要關檔, 否則 Windows 會留下鎖住的 handle
            try:
                merger.close()
            except Exception:
                pass
            for pdf_stream in pdf_files_stream:
                try:
                    pdf_stream.close()
                except Exception:
                    pass

        if not os.path.isfile(merged_pdf) or os.path.getsize(merged_pdf) <= 0:
            raise RuntimeError(f"合併後PDF未產生或為空檔: {filename}")

        # 來源檔刪不掉不該中斷整個流程
        for pdf in pdfs:
            try:
                os.remove(pdf)
            except OSError:
                pass

        return filename

    def _get_sequence(self, row_no):
        # self.start_no = 8000  # 測試用, 用完要comment
        sequence = row_no + self.start_no  # 應該是 +1, 暫時的，for 抽審測試
        return sequence

    def _zip_pdf_file(self, row_no, pdf_file):
        self._init_timestamp()

        sequence = self._get_sequence(row_no)
        att_file = f"ATT{self.clinic_id}_{self.now}{sequence:0>8}.7z"
        zip_file = f"{self.EXPORT_DIR}/{att_file}"
        source_file = f"{self.EXPORT_DIR}/{pdf_file}"

        # 7z 在來源檔不存在時仍會產生一個合法但空的壓縮檔(exit code 1),
        # 所以壓縮前後都要自己檢查
        if not os.path.isfile(source_file):
            raise FileNotFoundError(f"待壓縮PDF不存在: {pdf_file}")
        if os.path.getsize(source_file) <= 0:
            raise ValueError(f"待壓縮PDF為空檔: {pdf_file}")

        if os.path.isfile(zip_file):
            try:
                os.remove(zip_file)  # 7z a 是「追加」, 舊檔要先清掉
            except OSError as e:
                raise RuntimeError(f"無法移除舊的壓縮檔 {att_file}: {e}")

        cmd = ["7z", "a", "-y", zip_file, source_file]
        returncode, output = self._run_7z(cmd)
        if returncode != 0:
            raise RuntimeError(
                f"7z 壓縮失敗({returncode}) {att_file}: {output.strip()}"
            )

        if not os.path.isfile(zip_file) or os.path.getsize(zip_file) <= 0:
            raise RuntimeError(f"7z 壓縮檔未建立: {att_file}")

        # 回頭驗證壓縮檔內容確實含有該 pdf
        returncode, listing = self._run_7z(["7z", "l", zip_file])
        if returncode != 0 or pdf_file not in listing:
            raise RuntimeError(
                f"壓縮檔 {att_file} 內找不到 {pdf_file}: {listing.strip()}"
            )

        return att_file

    # 建立抽審用xml檔
    def _create_xml_files(self, row_no, row, pdf_file):
        self._init_timestamp()

        sequence = self._get_sequence(row_no)
        xml_file_name = (
            f"{self.EXPORT_DIR}/XML{self.clinic_id}_{self.now}{sequence:0>8}.XML"
        )

        root = ET.Element("feereview")
        tree = ET.ElementTree(root)

        cdata = ET.SubElement(root, "cdata")

        chead = ET.SubElement(cdata, "chead")
        c1 = ET.SubElement(chead, "c1")
        # c1.text = "2"  # 1=當期送審 2=事後審查 3=補件
        c1.text = "1"  # 1=當期送審 2=事後審查 3=補件  2026-07-16 IDC建議
        c2 = ET.SubElement(chead, "c2")
        c2.text = self.system_settings.field("院所代號")
        c3 = ET.SubElement(chead, "c3")
        c3.text = "14"  # 醫事類別: 14=中醫
        c4 = ET.SubElement(chead, "c4")
        c4.text = self.apply_date
        c5 = ET.SubElement(chead, "c5")
        c5.text = self.apply_type_code
        c6 = ET.SubElement(chead, "c6")
        c6.text = self.apply_upload_date.toString("yyyyMMdd")

        cbody = ET.SubElement(cdata, "cbody")
        c7 = ET.SubElement(cbody, "c7")
        c7.text = string_utils.xstr(row["CaseType"])
        c8 = ET.SubElement(cbody, "c8")
        c8.text = string_utils.xstr(row["Sequence"])
        c9 = ET.SubElement(cbody, "c9")
        c9.text = string_utils.xstr(row["PatientKey"])
        c10 = ET.SubElement(cbody, "c10")
        c10.text = string_utils.xstr(row["ID"])

        fdata = ET.SubElement(cbody, "fdata")
        f1 = ET.SubElement(fdata, "f1")
        f1.text = pdf_file
        f2 = ET.SubElement(fdata, "f2")
        f2.text = "PDF"
        f3 = ET.SubElement(fdata, "f3")
        f3.text = "ATT"
        f4 = ET.SubElement(fdata, "f4")
        f4.text = "病歷本文(含病歷首頁, 雙月病歷及服務點數醫令清單)"

        xml_utils.write_big5_xml(root, xml_file_name)

        if not os.path.isfile(xml_file_name) or os.path.getsize(xml_file_name) <= 0:
            raise RuntimeError(f"XML未產生: {os.path.basename(xml_file_name)}")

    def _get_zip_file_name(self):
        self._init_timestamp()
        zip_file_name = f"{self.EXPORT_DIR}/{self.clinic_id}_{self.nhi_now}_001.zip"
        return zip_file_name

    def _zip_all_files(self):
        zip_file = self._get_zip_file_name()

        if os.path.isfile(zip_file):
            try:
                os.remove(zip_file)
            except OSError as e:
                system_utils.show_message_box(
                    QtWidgets.QMessageBox.Critical,
                    "無法移除舊的上傳檔",
                    '<font size="5" color="red"><b>無法移除上一次產生的上傳壓縮檔.</b></font>',
                    f"{zip_file}\n{e}",
                )
                return False

        list_files = [
            f
            for f in os.listdir(self.EXPORT_DIR)
            if os.path.isfile(os.path.join(self.EXPORT_DIR, f))
        ]
        list_files.sort()

        added = 0
        for file in list_files:
            ext_file_name = os.path.splitext(file)[1].lstrip(".").upper()
            if ext_file_name not in ["XML", "7Z"]:
                continue

            source_file = f"{self.EXPORT_DIR}/{file}"
            cmd = ["7z", "a", "-tzip", "-y", zip_file, source_file]
            returncode, output = self._run_7z(cmd)
            if returncode != 0:
                system_utils.show_message_box(
                    QtWidgets.QMessageBox.Critical,
                    "壓縮失敗",
                    '<font size="5" color="red"><b>建立上傳壓縮檔時失敗, 已中止.</b></font>',
                    f"{file}\n{output.strip()}",
                )
                return False

            added += 1
            try:
                os.remove(source_file)
            except OSError:
                pass

        if added <= 0 or not os.path.isfile(zip_file) or os.path.getsize(zip_file) <= 0:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Critical,
                "壓縮失敗",
                '<font size="5" color="red"><b>上傳壓縮檔沒有任何內容.</b></font>',
                f"{zip_file}",
            )
            return False

        return True
