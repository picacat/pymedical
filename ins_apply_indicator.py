# -*- coding: UTF-8 -*-

import calendar
import datetime

from PyQt5 import QtCore, QtWidgets

from libs import (
    class_utils,
    date_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)

# ---------------------------------------------------------------------------
# 【處理邏輯 2】指標 03~21 的共同排除
#
#   「指標 03~21 排除之資料：不含職業災害案件【案件分類 B6】、特定疾病門診
#     加強照護【案件分類 30】、預防保健【案件分類 A3】及專案專用案件
#    （案件分類 25 或 案件分類 22 且特定治療項目代號 C8、J7、J9、JA、JB、
#     JC、JD、JE、JF、JG（105 年 9 月修正））。」
#
# 對應到本程式的指標列：
#   0 每位醫師申請點數(04) / 1 用藥日數重複率(06) / 2 重複就診率(07) /
#   3 隔日申報診察費率(09) / 4 平均就醫次數(10) / 5 申請診察費次數(11) /
#   6 29案件每位醫師平均每件申請點數(18) / 7 針灸傷科次數(20) /
#   8 慢性病案件平均每件給藥日份(14-1) / 11 慢性病案件申報件數佔率(14-2)
# 不套用（不在 03~21 範圍內）：
#   9 中醫職災申報率(24)  <- 分子本來就是 B6，套下去會變成 0
#  10 當月院所週日開診天數(27)
# ---------------------------------------------------------------------------
EXCLUDE_COMMON_CASE_TYPE = ["25", "30", "A3", "B6"]

# 案件分類 22 且特定治療項目代號為下列之一者，也算「專案專用案件」。
#
# 公文（105/09 修正）的字面清單只有這些：
OFFICIAL_SPECIAL_CODE = [
    "C8",
    "J7",
    "J9",
    "JA",
    "JB",
    "JC",
    "JD",
    "JE",
    "JF",
    "JG",
]


# 但那份公文是 105/09 定的，之後陸續新增的照護專案（肺癌、大腸癌、胃癌、
# 慢性腎病、照護機構中醫照護……）同樣是案件分類 22 的專案專用案件，
# 只是還沒被寫進公文。這裡直接從 nhi_utils 推出「會被歸成案別 22 的
# 照護項目」對應的代號，以後在 nhi_utils 新增照護項目就會自動跟著排除，
# 不必回來改這一支。
#
#   IMPROVE_CARE_TREAT -> get_case_type() 會回傳 "22"
#   LONG_TERM_CARE     -> 掛號別為照護機構中醫照護時也是 "22"
def _get_care_special_code():
    """從 nhi_utils 推出「會被歸成案別 22 的照護項目」對應的特定治療項目代號.

    nhi_utils 沒有這些定義時就回傳空清單，退回公文的字面清單，
    不要讓整支模組在 import 階段就掛掉。
    """
    try:
        treat_type_list = list(nhi_utils.IMPROVE_CARE_TREAT) + list(
            nhi_utils.LONG_TERM_CARE
        )
        special_code_dict = nhi_utils.SPECIAL_CODE_DICT
    except AttributeError:
        return []

    return [
        special_code_dict.get(treat_type)
        for treat_type in treat_type_list
        if special_code_dict.get(treat_type)
    ]


CARE_SPECIAL_CODE = _get_care_special_code()

EXCLUDE_COMMON_SPECIAL_CODE = sorted(
    set(OFFICIAL_SPECIAL_CODE) | set(CARE_SPECIAL_CODE)
)

# ---------------------------------------------------------------------------
# 業務組
#
# nhi_utils 裡兩種寫法都有（DIVISION 用「台北業務組」、get_division_code 用
# 「臺北業務組」），兩個都認。
# ---------------------------------------------------------------------------
DIVISION_TAIPEI = ["台北業務組", "臺北業務組"]

# 臺北業務組「中醫門診總額抽樣抽審實施方案」114/07 起適用（114/06/19 修訂）
TAIPEI_SEPARATOR = "── 臺北業務組 抽樣抽審實施方案（114/07 起適用）──"

TAIPEI_INDICATOR_ITEM_LIST = [
    "C1 隔日申報診察費比率",
    "C2 療程中申報診察費比率",
    f"C6 同月同病患申請針灸、傷科處置費≧{nhi_utils.MAX_TREAT}次（人數）",
    "C7 重複就診率（同一日同一病患就診≧2次）",
    "C8 針傷科與內科交替（療程期間另起內科案件人數）",
    "D1 院所申請醫療費用點數",
    "D2 任一醫師針傷及脫臼整復29案件申請點數",
    "D3 院所醫師平均申請醫療費用點數",
    "D5 病患平均就醫次數",
    "D6 平均每位醫師針灸合併傷科處置費次數",
    "E5 申報職災（B6）案件件數",
    "E14/E15 案件分類22專款計畫申報人數",
]

# 針灸合併傷科治療處置：支付標準第四部第六章，醫令代碼 F 開頭
MERGE_TREAT_CODE_PREFIX = "F"

# 內科案件（C8 用）
INTERNAL_CASE_TYPE = ["21"]

# 針傷案件（C6 / C8 用）
TREAT_CASE_TYPE = ["29"]

# 一筆申報最多幾個特定治療項目代號
MAX_SPECIAL_CODE = 4

# 指標 06【用藥日數重複率】在共同排除之外，自己再排除的案別
#     「排除：案件分類 24、26、27、28、29 案件」
# C5（法定傳染病）不在官方清單內，是本院自己加的，維持原樣。
EXCLUDE_DUPLICATE_PRES_CASE_TYPE = ["24", "26", "27", "28", "29", "C5"]

# 針傷次數檢查的案別
TREAT_COUNT_CASE_TYPE = ["22", "24", "29"]

# 慢性病案件申報件數佔率的分母 / 分子
CASE_TYPE_24_RATE_DENOMINATOR = ["21", "24", "28"]
CASE_TYPE_24_RATE_NUMERATOR = ["24", "28"]

# IN (...) 一次帶幾個值
CHUNK_SIZE = 500

# 一筆申報最多幾個療程醫令
MAX_TREAT_COURSE = 6


# 健保指標 2026.09.05
class InsApplyIndicator(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)

        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_date = args[2]
        self.apply_period = args[3]
        self.apply_type_code = args[4]
        self.clinic_id = args[5]
        self.ui = None

        self.indicator_item_list = [
            "每位醫師申請點數",
            "用藥日數重複率",
            "重複就診率",
            "隔日申報診察費率",
            "平均就醫次數",
            f"申請診察費次數>={nhi_utils.MAX_DIAG + 1}次以上病患",
            "29案件每位醫師平均每件申請點數",
            f"22, 24, 29案件當月就醫針灸、傷科次數>{nhi_utils.MAX_TREAT}次",
            "慢性病案件平均每件給藥日份",
            "中醫職災申報率",
            "當月院所週日開診天數",
            "慢性病案件申報件數佔率",
        ]

        # 臺北業務組另外有一套抽樣抽審指標，接在後面（用分隔列隔開）
        self.taipei_row_no = None
        if self._use_taipei_spec():
            self.taipei_row_no = len(self.indicator_item_list) + 1
            self.indicator_item_list += [TAIPEI_SEPARATOR]
            self.indicator_item_list += TAIPEI_INDICATOR_ITEM_LIST

        # ---- 快取 ----
        self._apply_rows = None
        self._person_name_cache = {}
        self._incorrect_rows = []
        self._case_share_map = None

        self._set_ui()
        self._set_signal()
        self._check_ins_indicator()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_INDICATOR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_indicator = class_utils.get_table_widget(
            self.ui.tableWidget_indicator, self.database
        )
        self.table_widget_incorrect = class_utils.get_table_widget(
            self.ui.tableWidget_incorrect, self.database
        )

        self._set_table_width()

    def _set_table_width(self):
        width = [420, 100, 100, 160]
        self.table_widget_indicator.set_table_heading_width(width)
        width = [380, 100, 100, 100, 100]
        self.table_widget_incorrect.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    # -----------------------------------------------------------------------
    # 共用小工具
    # -----------------------------------------------------------------------
    @staticmethod
    def _date_of(value):
        """只取日期部分。

        insapply.CaseDate 是 DATETIME，原本直接拿整個時間戳去比「同一天」
        跟「隔一天」，結果會被看診時間影響（早上看跟晚上看算出來不一樣）。
        """
        if value is None:
            return None

        if isinstance(value, datetime.datetime):
            return value.date()

        if isinstance(value, datetime.date):
            return value

        try:
            return datetime.datetime.strptime(
                string_utils.xstr(value)[:10], "%Y-%m-%d"
            ).date()
        except ValueError:
            return None

    @staticmethod
    def _chunks(values, size=CHUNK_SIZE):
        values = list(values)
        for i in range(0, len(values), size):
            yield values[i : i + size]

    def _person_id_to_name(self, person_id):
        if person_id in self._person_name_cache:
            return self._person_name_cache[person_id]

        name = personnel_utils.person_id_to_name(self.database, person_id)
        self._person_name_cache[person_id] = name

        return name

    def _use_taipei_spec(self):
        """健保業務組決定要用哪一套指標。

        臺北業務組 -> 另外加上「中醫門診總額抽樣抽審實施方案」的指標；
        其他業務組 -> 只有原本這 12 項（依北區業務組專業審查篩選指標）。
        """
        division = string_utils.xstr(self.system_settings.field("健保業務"))

        return division in DIVISION_TAIPEI

    def _apply_month_range(self):
        """指標月的起訖日期字串。

        self.apply_date 是民國年月（例如 "11506"）。官方【處理邏輯 1】的
        指標月就是這個月份，註 1 又明文「非指標月份之就醫日期不納入計算」。
        取不出年月時回傳 (None, None)，呼叫端就不做月份過濾。
        """
        apply_date = string_utils.xstr(self.apply_date)
        if len(apply_date) < 5:
            return None, None

        year = number_utils.get_integer(apply_date[:-2]) + 1911
        month = number_utils.get_integer(apply_date[-2:])
        if not 1 <= month <= 12:
            return None, None

        try:
            last_day = calendar.monthrange(year, month)[1]
        except calendar.IllegalMonthError:
            return None, None

        return (
            f"{year:0>4}-{month:0>2}-01 00:00:00",
            f"{year:0>4}-{month:0>2}-{last_day:0>2} 23:59:59",
        )

    def _base_condition(self):
        return f"""
            ApplyDate = "{self.apply_date}" AND
            ApplyType = "{self.apply_type_code}" AND
            ApplyPeriod = "{self.apply_period}" AND
            ClinicID = "{self.clinic_id}"
        """

    @classmethod
    def _is_excluded_common(cls, row):
        """【處理邏輯 2】指標 03~21 共同排除的資料."""
        case_type = string_utils.xstr(row["CaseType"])
        if case_type in EXCLUDE_COMMON_CASE_TYPE:
            return True

        if case_type != "22":
            return False

        for i in range(1, MAX_SPECIAL_CODE + 1):
            special_code = string_utils.xstr(row.get(f"SpecialCode{i}"))
            if special_code in EXCLUDE_COMMON_SPECIAL_CODE:
                return True

        return False

    @staticmethod
    def _exclude_common_sql():
        """【處理邏輯 2】共同排除的 SQL 片段。

        一律用 COALESCE 包起來，避免 CaseType / SpecialCode 為 NULL 時
        整個條件變成 NULL，把本來該留下的資料一起濾掉。
        """
        if not EXCLUDE_COMMON_CASE_TYPE and not EXCLUDE_COMMON_SPECIAL_CODE:
            return " 1 = 1 "

        case_type_list = '", "'.join(EXCLUDE_COMMON_CASE_TYPE or ["\x00"])
        special_code_list = '", "'.join(EXCLUDE_COMMON_SPECIAL_CODE or ["\x00"])
        special = " OR ".join(
            [
                f'COALESCE(SpecialCode{i}, "") IN ("{special_code_list}")'
                for i in range(1, MAX_SPECIAL_CODE + 1)
            ]
        )

        return f"""
            COALESCE(CaseType, "") NOT IN ("{case_type_list}") AND
            NOT (COALESCE(CaseType, "") = "22" AND ({special}))
        """

    @staticmethod
    def _case_type_in(case_type, code_list):
        """重現 SQL 的 IN：NULL 一律不符合。"""
        if case_type is None:
            return False

        return string_utils.xstr(case_type) in code_list

    @staticmethod
    def _case_type_not_in(case_type, code_list):
        """重現 SQL 的 NOT IN：NULL 也是不符合（不會被選出來）。"""
        if case_type is None:
            return False

        return string_utils.xstr(case_type) not in code_list

    # -----------------------------------------------------------------------
    # 整個月的申報資料只撈一次
    # -----------------------------------------------------------------------
    def _get_apply_rows(self):
        """原本有 6 個指標各自下 SQL，其中 4 句一模一樣。改成撈一次共用。

        排序與原本相同（PatientKey, CaseDate），只多加一個 Sequence 當
        tie-break，讓時間戳完全相同的兩筆有固定順序（原本每跑一次可能不一樣）。
        子集合是在 Python 端過濾，過濾不會改變相對順序。
        """
        if self._apply_rows is not None:
            return self._apply_rows

        treat_code = ", ".join(
            [
                f"TreatCode{i}, TreatFee{i}"
                for i in range(1, nhi_utils.MAX_HOME_CARE + 1)
            ]
        )
        special_code = ", ".join(
            [f"SpecialCode{i}" for i in range(1, MAX_SPECIAL_CODE + 1)]
        )
        sql = f"""
            SELECT
                CaseType, Sequence, CaseDate, StopDate, PatientKey, Name,
                PresDays, DiagFee, InsApplyFee, AgentFee, DoctorID, CaseKey1,
                CaseKey2, {treat_code}, {special_code}
            FROM insapply
            WHERE
                {self._base_condition()}
            ORDER BY PatientKey, CaseDate, Sequence
        """
        self._apply_rows = self.database.select_record(sql)

        return self._apply_rows

    # -----------------------------------------------------------------------
    # 表格
    # -----------------------------------------------------------------------
    def _set_indicator_table(self):
        table_widget = self.ui.tableWidget_indicator
        table_widget.setRowCount(len(self.indicator_item_list))
        for row_no, item_name in enumerate(self.indicator_item_list):
            table_widget.setItem(row_no, 0, QtWidgets.QTableWidgetItem(item_name))

    def _insert_indicator_item(self, item_name):
        """保留原本的介面：單獨補一列指標."""
        self.indicator_item_list.append(item_name)
        row_no = self.ui.tableWidget_indicator.rowCount()
        self.ui.tableWidget_indicator.setRowCount(row_no + 1)
        self.ui.tableWidget_indicator.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(item_name)
        )

    def _insert_incorrect_row(self, ins_apply_row, item_no):
        """先收集，最後一次寫進表格（原本是每一筆都 setRowCount + setItem）。"""
        self._incorrect_rows.append(
            [
                self.indicator_item_list[item_no],
                ins_apply_row["CaseType"],
                ins_apply_row["Sequence"],
                ins_apply_row["PatientKey"],
                ins_apply_row["Name"],
            ]
        )

    def _list_incorrect_rows(self):
        table_widget = self.ui.tableWidget_incorrect
        table_widget.setRowCount(len(self._incorrect_rows))

        for row_no, row in enumerate(self._incorrect_rows):
            for col_no, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, value)
                table_widget.setItem(row_no, col_no, item)
                if col_no in [1, 2, 3]:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _set_table_widget_indicator_items(
        self, row_no, value1, value2, value3, show_number=True, show_percent=True
    ):
        if value1 is not None:
            self.ui.tableWidget_indicator.setItem(
                row_no, 1, QtWidgets.QTableWidgetItem(f"{value1}")
            )

        if value2 is not None:
            self.ui.tableWidget_indicator.setItem(
                row_no, 2, QtWidgets.QTableWidgetItem(f"{value2}")
            )

        if value1 is None and value2 is None:
            result = f"{value3}"
        else:
            percent_sign = "%" if show_percent else ""
            if show_number:
                result = f"{value3:.2f}{percent_sign}"
            else:
                result = f"{value3}"

        self.ui.tableWidget_indicator.setItem(
            row_no, 3, QtWidgets.QTableWidgetItem(result)
        )

        for col_no in [1, 2, 3]:
            item = self.ui.tableWidget_indicator.item(row_no, col_no)
            if item is not None:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    # -----------------------------------------------------------------------
    def _check_ins_indicator(self):
        self.ui.tableWidget_incorrect.setRowCount(0)
        self._incorrect_rows = []
        self._apply_rows = None
        self._set_indicator_table()

        rows = self._get_apply_rows()
        # 指標 03~21 一律先套用【處理邏輯 2】的共同排除
        common_rows = [row for row in rows if not self._is_excluded_common(row)]

        self._calculate_doctor_apply_fee(0)
        self._calculate_duplicate_pres_days(1, common_rows)
        self._calculate_duplicate_days(2, common_rows)
        self._calculate_next_day_diag_fee(3, common_rows)
        self._calculate_avg_case_count(4, common_rows)
        self._calculate_diag_fee_count(5, common_rows)
        self._calculate_case_type_29_apply_fee(6)
        self._calculate_treat_count(7, common_rows)
        self._calculate_case_type_24_avg_pres_days(8)
        # 指標 24 職災申報率不在 03~21 範圍內，分子就是 B6，不可套共同排除
        self._calculate_case_type_B6_rate(9, rows)
        # 指標 27 週日開診天數也不在 03~21 範圍內
        self._calculate_sunday_count(10)
        self._calculate_case_type_24_rate(11, common_rows)

        if self.taipei_row_no is not None:
            self._check_taipei_indicator(self.taipei_row_no)

        self._list_incorrect_rows()

        self.ui.tableWidget_indicator.resizeRowsToContents()
        self.ui.tableWidget_incorrect.resizeRowsToContents()

    # -----------------------------------------------------------------------
    # 0. 每位醫師申請點數
    # -----------------------------------------------------------------------
    def _calculate_doctor_apply_fee(self, row_no):
        sql = f"""
            SELECT SUM(InsApplyFee) AS ApplyFee, DoctorID FROM insapply
            WHERE
                {self._base_condition()} AND
                {self._exclude_common_sql()}
            GROUP BY DoctorID
            ORDER BY SUM(InsApplyFee) DESC
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0)
            return

        doctor_list = []
        for row in rows:
            doctor_name = self._person_id_to_name(string_utils.xstr(row["DoctorID"]))
            doctor_list.append(f"{doctor_name}: {row['ApplyFee']}")

        self._set_table_widget_indicator_items(
            row_no,
            None,
            None,
            "\n".join(doctor_list),
            show_number=False,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # 1. 用藥日數重複率
    # -----------------------------------------------------------------------
    def _calculate_duplicate_pres_days(self, row_no, apply_rows):
        rows = [
            row
            for row in apply_rows
            if self._case_type_not_in(row["CaseType"], EXCLUDE_DUPLICATE_PRES_CASE_TYPE)
            and number_utils.get_integer(row["PresDays"]) > 0
        ]
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        include_today = self.system_settings.field("當日用藥重複檢查")

        total_pres_days = 0
        duplicate_days = 0
        last_patient_key = 0
        last_case_date = None
        last_pres_days = 0

        for row in rows:
            pres_days = number_utils.get_integer(row["PresDays"])
            total_pres_days += pres_days
            case_date = self._date_of(row["CaseDate"])

            if (
                row["PatientKey"] == last_patient_key
                and case_date is not None
                and last_case_date is not None
            ):
                # 官方操作型定義：「前次給藥最後一日重複者不計」
                #   前次給藥區間 = last_case_date .. last_case_date + 日數 - 1
                #   重複天數     = 區間內在本次給藥日之後的天數, 但不含最後一日
                #                = (區間最後一日 - 本次給藥日).days
                # 官方例子: 1/1 給藥 7 天 (1/1~1/7), 1/7 再給藥
                #           -> (1/7 - 1/7).days = 0 天, 1/7 當日不計 (相符)
                # 原本多減了一個 1, 每一次重複都少算一天。
                days = (
                    last_case_date
                    + datetime.timedelta(days=last_pres_days - 1)
                    - case_date
                ).days
                if include_today == "Y":
                    days -= 1

                if days > 0:
                    duplicate_days += days
                    self._insert_incorrect_row(row, row_no)

            last_patient_key = row["PatientKey"]
            last_case_date = case_date
            last_pres_days = pres_days

        if total_pres_days <= 0:
            self._set_table_widget_indicator_items(row_no, duplicate_days, 0, 0)
            return

        duplicate_rate = duplicate_days / total_pres_days * 100
        self._set_table_widget_indicator_items(
            row_no, duplicate_days, total_pres_days, duplicate_rate
        )

    # -----------------------------------------------------------------------
    # 2. 重複就診率
    # -----------------------------------------------------------------------
    def _get_diag_fee_rows(self, apply_rows):
        return [
            row for row in apply_rows if number_utils.get_integer(row["DiagFee"]) > 0
        ]

    def _calculate_duplicate_days(self, row_no, apply_rows):
        rows = self._get_diag_fee_rows(apply_rows)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        # 官方定義: 重複就診率 = 該月重複就診【人數】/ 該月就醫人數 * 100
        #   重複就診人數 = 同一人、同一天、同一院所就診 2 次(含)以上之歸戶人數
        # 原本累加的是件數, 同一位病患重複好幾天會被算成好幾個。
        duplicate_patient = set()
        total_person = 0
        last_patient_key = 0
        last_case_date = None

        for row in rows:
            case_date = self._date_of(row["CaseDate"])

            if row["PatientKey"] == last_patient_key:
                # 同一天只比日期，不比看診時間
                if last_case_date is not None and last_case_date == case_date:
                    duplicate_patient.add(row["PatientKey"])
                    self._insert_incorrect_row(row, row_no)
            else:
                total_person += 1

            last_patient_key = row["PatientKey"]
            last_case_date = case_date

        duplicate_count = len(duplicate_patient)
        if total_person <= 0:
            self._set_table_widget_indicator_items(row_no, duplicate_count, 0, 0)
            return

        duplicate_rate = duplicate_count / total_person * 100
        self._set_table_widget_indicator_items(
            row_no, duplicate_count, total_person, duplicate_rate
        )

    # -----------------------------------------------------------------------
    # 3. 隔日申報診察費率
    # -----------------------------------------------------------------------
    def _calculate_next_day_diag_fee(self, row_no, apply_rows):
        rows = self._get_diag_fee_rows(apply_rows)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        next_days = 0
        total_case_count = 0
        last_patient_key = 0
        last_case_date = None

        for row in rows:
            total_case_count += 1
            case_date = self._date_of(row["CaseDate"])

            if row["PatientKey"] == last_patient_key:
                # 隔日只比日期，不比看診時間
                if (
                    case_date is not None
                    and last_case_date is not None
                    and (case_date - last_case_date).days == 1
                ):
                    next_days += 1
                    self._insert_incorrect_row(row, row_no)

            last_patient_key = row["PatientKey"]
            last_case_date = case_date

        rate = next_days / total_case_count * 100
        self._set_table_widget_indicator_items(
            row_no, next_days, total_case_count, rate
        )

    # -----------------------------------------------------------------------
    # 4. 平均就醫次數
    # -----------------------------------------------------------------------
    def _calculate_avg_case_count(self, row_no, apply_rows):
        rows = self._get_diag_fee_rows(apply_rows)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        person_count = 0
        total_case_count = 0
        last_patient_key = 0

        for row in rows:
            total_case_count += 1
            if row["PatientKey"] != last_patient_key:
                person_count += 1

            last_patient_key = row["PatientKey"]

        if person_count <= 0:
            self._set_table_widget_indicator_items(
                row_no, total_case_count, 0, 0, show_percent=False
            )
            return

        avg_count = total_case_count / person_count
        self._set_table_widget_indicator_items(
            row_no, total_case_count, person_count, avg_count, show_percent=False
        )

    # -----------------------------------------------------------------------
    # 5. 申請診察費次數 >= MAX_DIAG + 1 次以上病患
    # -----------------------------------------------------------------------
    def _calculate_diag_fee_count(self, row_no, apply_rows):
        rows = self._get_diag_fee_rows(apply_rows)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0)
            return

        error_patient = set()
        diag_count = 0
        last_patient_key = 0

        for row in rows:
            if row["PatientKey"] == last_patient_key:
                diag_count += 1
            else:
                # 這一筆就是該病患的第 1 次，原本從 0 起算會少算一次
                diag_count = 1

            if diag_count > nhi_utils.MAX_DIAG:
                error_patient.add(row["PatientKey"])
                self._insert_incorrect_row(row, row_no)

            last_patient_key = row["PatientKey"]

        self._set_table_widget_indicator_items(
            row_no, None, None, len(error_patient), show_percent=False
        )

    # -----------------------------------------------------------------------
    # 6. 29案件每位醫師平均每件申請點數
    # -----------------------------------------------------------------------
    def _calculate_case_type_29_apply_fee(self, row_no):
        sql = f"""
            SELECT
                SUM(InsApplyFee) AS ApplyFee,
                COUNT(InsApplyFee) AS RowCount,
                DoctorID
            FROM insapply
            WHERE
                {self._base_condition()} AND
                {self._exclude_common_sql()} AND
                CaseType = "29"
            GROUP BY DoctorID
            ORDER BY SUM(InsApplyFee)/COUNT(InsApplyFee) DESC
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(
                row_no, None, None, 0, show_percent=False
            )
            return

        numerator_list = []
        denominator_list = []
        doctor_list = []

        for row in rows:
            doctor_name = self._person_id_to_name(string_utils.xstr(row["DoctorID"]))
            apply_fee = number_utils.get_integer(row["ApplyFee"])
            row_count = number_utils.get_integer(row["RowCount"])

            numerator_list.append(f"{row['ApplyFee']}")
            denominator_list.append(f"{row['RowCount']}")
            if row_count <= 0:
                doctor_list.append(f"{doctor_name}: 0")
            else:
                doctor_list.append(f"{doctor_name}: {int(apply_fee / row_count)}")

        self._set_table_widget_indicator_items(
            row_no,
            "\n".join(numerator_list),
            "\n".join(denominator_list),
            "\n".join(doctor_list),
            show_number=False,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # 7. 22, 24, 29案件當月就醫針灸、傷科次數 > MAX_TREAT 次
    # -----------------------------------------------------------------------
    def _calculate_treat_count(self, row_no, apply_rows):
        rows = [
            row
            for row in apply_rows
            if self._case_type_in(row["CaseType"], TREAT_COUNT_CASE_TYPE)
        ]
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(
                row_no, None, None, 0, show_percent=False
            )
            return

        error_count = 0
        treat_count = 0
        last_patient_key = 0

        for row in rows:
            if row["PatientKey"] != last_patient_key:
                treat_count = 0

            for i in range(1, MAX_TREAT_COURSE + 1):
                treat_code = string_utils.xstr(row[f"TreatCode{i}"])
                if treat_code in nhi_utils.TREAT_ALL_CODE:
                    treat_count += 1

            if treat_count > nhi_utils.MAX_TREAT:
                error_count += 1
                treat_count = 0
                self._insert_incorrect_row(row, row_no)

            last_patient_key = row["PatientKey"]

        self._set_table_widget_indicator_items(
            row_no, None, None, error_count, show_percent=False
        )

    # -----------------------------------------------------------------------
    # 8. 慢性病案件平均每件給藥日份
    #
    # 官方定義: 慢性病案件總給藥日份 / 慢性病案件【給藥案件】之件數
    #           給藥案件 = 藥費不為 0 「或」給藥天數不為 0
    # 原本只用 DrugFee > 0, 少算了藥費 0 但有給藥天數的案件。
    # -----------------------------------------------------------------------
    def _calculate_case_type_24_avg_pres_days(self, row_no):
        sql = f"""
            SELECT
                COUNT(PresDays) AS CaseCount,
                SUM(PresDays) AS TotalPresDays
            FROM insapply
            WHERE
                {self._base_condition()} AND
                {self._exclude_common_sql()} AND
                CaseType = "24" AND
                (DrugFee > 0 OR PresDays > 0)
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0 or number_utils.get_integer(rows[0]["TotalPresDays"]) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        row = rows[0]
        total_pres_days = number_utils.get_integer(row["TotalPresDays"])
        total_case_count = number_utils.get_integer(row["CaseCount"])
        if total_case_count <= 0:
            self._set_table_widget_indicator_items(
                row_no, total_pres_days, 0, 0, show_percent=False
            )
            return

        avg_count = total_pres_days / total_case_count
        self._set_table_widget_indicator_items(
            row_no, total_pres_days, total_case_count, avg_count, show_percent=False
        )

    # -----------------------------------------------------------------------
    # 9. 中醫職災申報率
    # -----------------------------------------------------------------------
    def _calculate_case_type_B6_rate(self, row_no, apply_rows):
        total_case_count = len(apply_rows)
        if total_case_count <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        total_B6_count = 0
        for row in apply_rows:
            if string_utils.xstr(row["CaseType"]) == "B6":
                total_B6_count += 1

        rate = total_B6_count / total_case_count * 100
        self._set_table_widget_indicator_items(
            row_no, total_B6_count, total_case_count, rate, show_percent=True
        )

    # -----------------------------------------------------------------------
    # 10. 當月院所週日開診天數
    # -----------------------------------------------------------------------
    def _calculate_sunday_count(self, row_no):
        # 官方定義: 「指標月之【就醫日期】含週日日期的天數加計」
        #           註 1「非指標月份之就醫日期不納入計算」
        #
        # 三個地方要注意:
        #   1. 原本抓的是 StopDate (療程結束日), 應該用 CaseDate (就醫日期)
        #   2. GROUP BY 要對日期做, 否則帶時間會把同一天拆成好幾筆
        #   3. 療程首次落在上個月的申報記錄, CaseDate 就是上個月的日期,
        #      一定要用指標月把它們擋掉, 否則會算出一個月超過 5 個週日
        start_date, end_date = self._apply_month_range()
        month_condition = ""
        if start_date is not None:
            month_condition = (
                f''' AND CaseDate BETWEEN "{start_date}" AND "{end_date}"'''
            )

        sql = f"""
            SELECT DATE(CaseDate) AS case_date FROM insapply
            WHERE
                {self._base_condition()}
                {month_condition}
            GROUP BY case_date
            ORDER BY case_date
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(
                row_no, None, None, 0, show_percent=False
            )
            return

        sunday_count = 0
        for row in rows:
            case_date = self._date_of(row["case_date"])
            if case_date is None:
                continue

            weekday_name = date_utils.get_weekday_name(case_date.weekday())
            if weekday_name == "星期日":
                sunday_count += 1

        self._set_table_widget_indicator_items(
            row_no, None, None, sunday_count, show_percent=False
        )

    # -----------------------------------------------------------------------
    # 11. 慢性病案件申報件數佔率
    # -----------------------------------------------------------------------
    def _calculate_case_type_24_rate(self, row_no, apply_rows):
        rows = [
            row
            for row in apply_rows
            if self._case_type_in(row["CaseType"], CASE_TYPE_24_RATE_DENOMINATOR)
        ]
        total_case_count = len(rows)
        if total_case_count <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        total_24_count = 0
        for row in rows:
            if self._case_type_in(row["CaseType"], CASE_TYPE_24_RATE_NUMERATOR):
                total_24_count += 1

        rate = total_24_count / total_case_count * 100
        self._set_table_widget_indicator_items(
            row_no, total_24_count, total_case_count, rate, show_percent=True
        )

    # =======================================================================
    # 臺北業務組「中醫門診總額抽樣抽審實施方案」各項指標操作型定義
    #     衛生福利部中央健康保險署臺北業務組 114 年 6 月 19 日修訂
    #     114/07（費用年月）起適用
    #
    # 【通則】
    #   1. 除條件說明另有規定，資料擷取原則上不含代辦案件。
    #   2. 有申報醫療費用點數之院所皆納入母群體內計算。
    #
    # 這裡只做「本院自己算得出來」的項目。需要去年同期、全國同儕分位數
    # (PR97.5)、初審核減資料、虛擬健保卡或雲端查詢紀錄的指標沒有列入：
    #   A8 / A10          合約狀態、全國醫師數分位
    #   B1~B5、E8         需要去年同期
    #   C4 / C5           需要 PR97.5 同儕值
    #   D4                需要初審核減資料
    #   E10~E13           需要計畫參與狀態、虛擬健保卡、雲端查詢紀錄
    # =======================================================================
    def _check_taipei_indicator(self, first_row_no):
        rows = self._get_taipei_rows()

        self._calculate_taipei_next_day_diag(first_row_no)
        self._calculate_taipei_course_diag(first_row_no + 1, rows)
        self._calculate_taipei_treat_count(first_row_no + 2, rows)
        self._calculate_taipei_duplicate_visit(first_row_no + 3, rows)
        self._calculate_taipei_treat_internal(first_row_no + 4, rows)
        self._calculate_taipei_total_fee(first_row_no + 5, rows)
        self._calculate_taipei_doctor_treat_fee(first_row_no + 6, rows)
        self._calculate_taipei_doctor_avg_fee(first_row_no + 7, rows)
        self._calculate_taipei_avg_case_count(first_row_no + 8, rows)
        self._calculate_taipei_merge_treat(first_row_no + 9, rows)
        self._calculate_taipei_injury_count(first_row_no + 10, rows)
        self._calculate_taipei_special_project(first_row_no + 11)

    # -----------------------------------------------------------------------
    # 共用
    # -----------------------------------------------------------------------
    @staticmethod
    def _is_agent_case(row):
        """【通則 1】代辦案件。

        insapply 的 AgentFee 有值就是代辦（部分負擔由院所代收代辦）。
        若貴院的認定不同，改這一個函式即可。
        """
        return number_utils.get_integer(row["AgentFee"]) > 0

    @classmethod
    def _is_special_project_case(cls, row):
        """專款專用案件：案件分類 25，或案件分類 22 且帶專案代號。"""
        case_type = string_utils.xstr(row["CaseType"])
        if case_type == "25":
            return True

        if case_type != "22":
            return False

        for i in range(1, MAX_SPECIAL_CODE + 1):
            if (
                string_utils.xstr(row.get(f"SpecialCode{i}"))
                in EXCLUDE_COMMON_SPECIAL_CODE
            ):
                return True

        return False

    def _get_taipei_rows(self):
        """【通則 1】不含代辦案件。專款專用由各指標自己視條件說明排除。"""
        return [row for row in self._get_apply_rows() if not self._is_agent_case(row)]

    @classmethod
    def _without_special_project(cls, rows):
        return [row for row in rows if not cls._is_special_project_case(row)]

    @staticmethod
    def _with_diag_fee(rows):
        return [row for row in rows if number_utils.get_integer(row["DiagFee"]) > 0]

    def _get_case_share_map(self):
        """{CaseKey: cases.Share}，用來判斷重大傷病（insapply 沒有這個欄位）。"""
        if self._case_share_map is not None:
            return self._case_share_map

        self._case_share_map = {}
        keys = sorted(
            {
                number_utils.get_integer(row["CaseKey1"])
                for row in self._get_apply_rows()
                if number_utils.get_integer(row["CaseKey1"]) > 0
            }
        )
        for chunk in self._chunks(keys):
            in_list = ", ".join(str(key) for key in chunk)
            sql = f"""
                SELECT CaseKey, Share FROM cases
                WHERE
                    CaseKey IN ({in_list})
            """
            for row in self.database.select_record(sql):
                self._case_share_map[number_utils.get_integer(row["CaseKey"])] = (
                    string_utils.xstr(row["Share"])
                )

        return self._case_share_map

    def _is_serious_illness(self, row):
        """重大傷病（insapply 沒存，要回頭看病歷的部分負擔身分）。"""
        share_map = self._get_case_share_map()
        share = share_map.get(number_utils.get_integer(row["CaseKey1"]), "")

        return share == "重大傷病"

    @staticmethod
    def _group_by_patient(rows):
        grouped = {}
        for row in rows:
            grouped.setdefault(number_utils.get_integer(row["PatientKey"]), []).append(
                row
            )

        return grouped

    def _count_treat_order(self, row, code_list=None, prefix=None):
        """算一筆申報裡符合條件、且醫令費用不為 0 的處置醫令數量。"""
        count = 0
        for i in range(1, nhi_utils.MAX_HOME_CARE + 1):
            treat_code = string_utils.xstr(row.get(f"TreatCode{i}"))
            if treat_code == "":
                continue
            if number_utils.get_integer(row.get(f"TreatFee{i}")) == 0:
                continue
            if code_list is not None and treat_code not in code_list:
                continue
            if prefix is not None and not treat_code.startswith(prefix):
                continue
            count += 1

        return count

    # -----------------------------------------------------------------------
    # C1 隔日申報診察費比率
    # -----------------------------------------------------------------------
    def _calculate_taipei_next_day_diag(self, row_no):
        """分子：院所該月份同一人隔日申報診察費之件數
        分母：院所該月份申報診察費之總件數
        條件：1.保險對象身分證號相同者計一人 2.排除專款專用案件
              3.隔日申報診察費係指連續 2 日申報診察費不為 0 的案件，如連續
                3 日申報診察費不為 0，則重複件數為 2 件；另如同一日重複就
                醫者申報 2 次診察費，且隔日又申報 1 件診察費，重複件數為 2 件。

        由條件 3 的兩個例子推出的算法是「往後看一天」：
            連續三日 D1 D2 D3 -> D1(有D2) + D2(有D3) = 2 件
            同日兩件 + 隔日一件 D1a D1b D2 -> D1a + D1b = 2 件
        往前看一天的話第二個例子只會算到 1 件，與公文不符。
        """
        rows = self._with_diag_fee(
            self._without_special_project(self._get_taipei_rows())
        )
        total_count = len(rows)
        if total_count <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        date_set = {}
        for row in rows:
            case_date = self._date_of(row["CaseDate"])
            if case_date is None:
                continue
            date_set.setdefault(number_utils.get_integer(row["PatientKey"]), set()).add(
                case_date
            )

        next_day_count = 0
        for row in rows:
            case_date = self._date_of(row["CaseDate"])
            if case_date is None:
                continue
            patient_date = date_set.get(
                number_utils.get_integer(row["PatientKey"]), set()
            )
            if case_date + datetime.timedelta(days=1) in patient_date:
                next_day_count += 1
                self._insert_incorrect_row(row, row_no)

        self._set_table_widget_indicator_items(
            row_no,
            next_day_count,
            total_count,
            next_day_count / total_count * 100,
        )

    # -----------------------------------------------------------------------
    # C2 療程中申報診察費比率
    # -----------------------------------------------------------------------
    def _calculate_taipei_course_diag(self, row_no, taipei_rows):
        """分子：院所該月份同一病患療程中另申報診察費之件數
        分母：院所該月份申報診察費不為 0 之療程案件數
        條件：1.保險對象身分證號相同者計一人
              2.療程中另申報診察費比率係指療程起迄日中另申報診察費不為 0 的案件
              3.排除專款專用案件
        """
        rows = self._without_special_project(taipei_rows)
        course_rows = [
            row for row in rows if number_utils.get_integer(row["CaseKey2"]) > 0
        ]
        total_count = len(self._with_diag_fee(course_rows))
        if total_count <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        grouped = self._group_by_patient(self._with_diag_fee(rows))

        another_count = 0
        for course_row in course_rows:
            start_date = self._date_of(course_row["CaseDate"])
            stop_date = self._date_of(course_row["StopDate"])
            if start_date is None:
                continue
            if stop_date is None:
                stop_date = start_date

            for row in grouped.get(
                number_utils.get_integer(course_row["PatientKey"]), []
            ):
                if row is course_row:
                    continue
                case_date = self._date_of(row["CaseDate"])
                if case_date is None:
                    continue
                if start_date <= case_date <= stop_date:
                    another_count += 1
                    self._insert_incorrect_row(row, row_no)

        self._set_table_widget_indicator_items(
            row_no,
            another_count,
            total_count,
            another_count / total_count * 100,
        )

    # -----------------------------------------------------------------------
    # C6 同月同病患申請針灸、傷科處置費≧20 次
    # -----------------------------------------------------------------------
    def _calculate_taipei_treat_count(self, row_no, taipei_rows):
        """院所同月同病患申請針灸、傷科處置費≧20 次。
        條件：1.保險對象身分證號相同者計一人 2.29 針傷案件 3.排除專款專用案件

        次數以「醫令費用不為 0 的針傷處置醫令」計算，代碼取
        nhi_utils.TREAT_ALL_CODE；門檻取 nhi_utils.MAX_TREAT（目前 20）。
        """
        rows = [
            row
            for row in self._without_special_project(taipei_rows)
            if string_utils.xstr(row["CaseType"]) in TREAT_CASE_TYPE
        ]

        treat_count = {}
        sample_row = {}
        for row in rows:
            patient_key = number_utils.get_integer(row["PatientKey"])
            count = self._count_treat_order(row, code_list=nhi_utils.TREAT_ALL_CODE)
            if count <= 0:
                continue
            treat_count[patient_key] = treat_count.get(patient_key, 0) + count
            sample_row.setdefault(patient_key, row)

        over_patient = [
            patient_key
            for patient_key, count in treat_count.items()
            if count >= nhi_utils.MAX_TREAT
        ]
        for patient_key in over_patient:
            self._insert_incorrect_row(sample_row[patient_key], row_no)

        self._set_table_widget_indicator_items(
            row_no, None, None, len(over_patient), show_percent=False
        )

    # -----------------------------------------------------------------------
    # C7 重複就診率（同一日同一病患就診≧2 次比率）
    # -----------------------------------------------------------------------
    def _calculate_taipei_duplicate_visit(self, row_no, taipei_rows):
        """分子：院所該月份同一日同一病患申報 2（含）以上筆診察費件數
        分母：院所該月份申報診察費之總件數
        條件：保險對象身分證號相同者計一人

        註：本項條件說明沒有寫排除專款專用案件，所以不排除。
        """
        rows = self._with_diag_fee(taipei_rows)
        total_count = len(rows)
        if total_count <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        grouped = {}
        for row in rows:
            key = (
                number_utils.get_integer(row["PatientKey"]),
                self._date_of(row["CaseDate"]),
            )
            grouped.setdefault(key, []).append(row)

        duplicate_count = 0
        for group in grouped.values():
            if len(group) < 2:
                continue
            duplicate_count += len(group)
            for row in group:
                self._insert_incorrect_row(row, row_no)

        self._set_table_widget_indicator_items(
            row_no,
            duplicate_count,
            total_count,
            duplicate_count / total_count * 100,
        )

    # -----------------------------------------------------------------------
    # C8 針傷科與內科交替率人數
    # -----------------------------------------------------------------------
    def _calculate_taipei_treat_internal(self, row_no, taipei_rows):
        """同一院所、同一病患、針傷案件療程期間另起內科案件且申報診察費人數。
        條件：1.保險對象身分證號相同者計一人 2.內科案件為（21 案件）診察費>0

        註：114/06/19 修訂版把原本的「分子/分母比率」改成人數，
            也把「排除專款專用案件」拿掉了，所以這裡不排除。
        """
        course_rows = [
            row
            for row in taipei_rows
            if string_utils.xstr(row["CaseType"]) in TREAT_CASE_TYPE
        ]
        internal_rows = [
            row
            for row in self._with_diag_fee(taipei_rows)
            if string_utils.xstr(row["CaseType"]) in INTERNAL_CASE_TYPE
        ]
        grouped = self._group_by_patient(internal_rows)

        over_patient = set()
        for course_row in course_rows:
            start_date = self._date_of(course_row["CaseDate"])
            stop_date = self._date_of(course_row["StopDate"])
            if start_date is None:
                continue
            if stop_date is None:
                stop_date = start_date

            patient_key = number_utils.get_integer(course_row["PatientKey"])
            for row in grouped.get(patient_key, []):
                case_date = self._date_of(row["CaseDate"])
                if case_date is None:
                    continue
                if start_date <= case_date <= stop_date:
                    if patient_key not in over_patient:
                        self._insert_incorrect_row(row, row_no)
                    over_patient.add(patient_key)

        self._set_table_widget_indicator_items(
            row_no, None, None, len(over_patient), show_percent=False
        )

    # -----------------------------------------------------------------------
    # D1 院所申請醫療費用點數
    # -----------------------------------------------------------------------
    def _calculate_taipei_total_fee(self, row_no, taipei_rows):
        """院所該月份申請醫療費用點數加總。"""
        total_fee = sum(
            number_utils.get_integer(row["InsApplyFee"]) for row in taipei_rows
        )
        self._set_table_widget_indicator_items(
            row_no, None, None, total_fee, show_percent=False
        )

    # -----------------------------------------------------------------------
    # D2 任一醫師針傷及脫臼整復 29 案件申請醫療費用點數
    # -----------------------------------------------------------------------
    def _calculate_taipei_doctor_treat_fee(self, row_no, taipei_rows):
        """院所該月份任一醫師針傷案件申請醫療費用點數加總。"""
        doctor_fee = {}
        for row in taipei_rows:
            if string_utils.xstr(row["CaseType"]) not in TREAT_CASE_TYPE:
                continue
            doctor_id = string_utils.xstr(row["DoctorID"])
            doctor_fee[doctor_id] = doctor_fee.get(
                doctor_id, 0
            ) + number_utils.get_integer(row["InsApplyFee"])

        if not doctor_fee:
            self._set_table_widget_indicator_items(
                row_no, None, None, 0, show_percent=False
            )
            return

        doctor_list = [
            f"{self._person_id_to_name(doctor_id)}: {fee}"
            for doctor_id, fee in sorted(doctor_fee.items(), key=lambda item: -item[1])
        ]
        self._set_table_widget_indicator_items(
            row_no,
            None,
            None,
            "\n".join(doctor_list),
            show_number=False,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # D3 院所醫師平均申請醫療費用點數
    # -----------------------------------------------------------------------
    def _calculate_taipei_doctor_avg_fee(self, row_no, taipei_rows):
        """分子：院所該月份申請醫療費用點數加總
        分母：院所該月份申報醫師數
        """
        total_fee = 0
        doctor_set = set()
        for row in taipei_rows:
            total_fee += number_utils.get_integer(row["InsApplyFee"])
            doctor_id = string_utils.xstr(row["DoctorID"])
            if doctor_id != "":
                doctor_set.add(doctor_id)

        doctor_count = len(doctor_set)
        if doctor_count <= 0:
            self._set_table_widget_indicator_items(
                row_no, total_fee, 0, 0, show_percent=False
            )
            return

        self._set_table_widget_indicator_items(
            row_no,
            total_fee,
            doctor_count,
            total_fee / doctor_count,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # D5 病患平均就醫次數
    # -----------------------------------------------------------------------
    def _calculate_taipei_avg_case_count(self, row_no, taipei_rows):
        """分子：院所最近 1 個月申報診察費件數
        分母：院所最近 1 個月歸戶就醫人數
        條件：1.保險對象身分證號相同者計一人
              2.排除職災、重大傷病、診察費為 0 案件及專款專用案件
        """
        rows = [
            row
            for row in self._with_diag_fee(self._without_special_project(taipei_rows))
            if string_utils.xstr(row["CaseType"]) != "B6"
            and not self._is_serious_illness(row)
        ]
        case_count = len(rows)
        person_count = len(
            {number_utils.get_integer(row["PatientKey"]) for row in rows}
        )
        if person_count <= 0:
            self._set_table_widget_indicator_items(
                row_no, case_count, 0, 0, show_percent=False
            )
            return

        self._set_table_widget_indicator_items(
            row_no,
            case_count,
            person_count,
            case_count / person_count,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # D6 平均每位醫師針灸合併傷科處置費次數
    # -----------------------------------------------------------------------
    def _calculate_taipei_merge_treat(self, row_no, taipei_rows):
        """分子：申請針灸合併傷科治療處置費次數加總
        分母：申請針灸合併傷科治療處置費醫師數
        條件：1.以支付標準第四部第六章針灸合併傷科治療處置之所有醫令（F 碼）
                計算次數，且申報醫令費用不為 0
              2.排除職災案件、重大傷病及專款專用案件
        """
        rows = [
            row
            for row in self._without_special_project(taipei_rows)
            if string_utils.xstr(row["CaseType"]) != "B6"
            and not self._is_serious_illness(row)
        ]

        total_count = 0
        doctor_set = set()
        for row in rows:
            count = self._count_treat_order(row, prefix=MERGE_TREAT_CODE_PREFIX)
            if count <= 0:
                continue
            total_count += count
            doctor_id = string_utils.xstr(row["DoctorID"])
            if doctor_id != "":
                doctor_set.add(doctor_id)

        doctor_count = len(doctor_set)
        if doctor_count <= 0:
            self._set_table_widget_indicator_items(
                row_no, total_count, 0, 0, show_percent=False
            )
            return

        self._set_table_widget_indicator_items(
            row_no,
            total_count,
            doctor_count,
            total_count / doctor_count,
            show_percent=False,
        )

    # -----------------------------------------------------------------------
    # E5 申報職災（B6）案件件數
    # -----------------------------------------------------------------------
    def _calculate_taipei_injury_count(self, row_no, taipei_rows):
        """院所本月申報職業災害（B6 案件）件數。
        條件：排除診察費為 0 的案件。

        （≧2 件得減計權值點數 2 點；≧6 件再減 1 點；≧10 件再減 1 點，
          最高減計 4 點。這裡只列件數，權值不自動換算。）
        """
        count = len(
            [
                row
                for row in self._with_diag_fee(taipei_rows)
                if string_utils.xstr(row["CaseType"]) == "B6"
            ]
        )
        self._set_table_widget_indicator_items(
            row_no, None, None, count, show_percent=False
        )

    # -----------------------------------------------------------------------
    # E14 / E15 案件分類 22（中醫其他專案）之專款計畫申報人數
    # -----------------------------------------------------------------------
    def _calculate_taipei_special_project(self, row_no):
        """院所本月案件分類 22（中醫其他專案）之任一專款計畫申報人數。
        條件：保險對象身分證號相同者計一人。

        （≧1 人得減計權值點數 2 點；≧5 人再得減計 2 點，最高減計 6 點。）
        註：本項就是要看專款案件，所以不套用「排除專款專用案件」。
        """
        patient_set = set()
        for row in self._get_taipei_rows():
            if string_utils.xstr(row["CaseType"]) != "22":
                continue
            if not self._is_special_project_case(row):
                continue
            patient_set.add(number_utils.get_integer(row["PatientKey"]))

        self._set_table_widget_indicator_items(
            row_no, None, None, len(patient_set), show_percent=False
        )
