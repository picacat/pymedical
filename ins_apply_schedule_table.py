# -*- coding: UTF-8 -*-
import calendar
import datetime

from PyQt5 import QtWidgets

from libs import (
    nhi_utils,
    number_utils,
    printer_utils,
    string_utils,
    system_utils,
    ui_utils,
)

# 診別 -> nurse_schedule 的欄位
PERIOD_NURSE_FIELD = {
    "早班": "Nurse1",
    "午班": "Nurse2",
    "晚班": "Nurse3",
}


# 醫護排班表 2026-09-05
class InsApplyScheduleTable(QtWidgets.QMainWindow):
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
        self.ins_generate_date = args[9]
        self.ins_calculated_table = args[10]
        self.ui = None
        self.nurse_list = []

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

        # system_settings.field() 每次呼叫都真的查資料庫, 這裡只需要各取一次
        self._clinic_name = self.system_settings.field("院所名稱")
        self._telephone = self.system_settings.field("院所電話")

        # 排班表內容不會變動, 顯示/列印/匯出 PDF 共用同一份 HTML
        self._html = None

        self.month_table = self._get_month_table()
        self.medical_record = self._get_medical_record()

        self._set_ui()
        self._set_signal()
        self._display_schedule_table()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_SCHEDULE_TABLE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print.clicked.connect(self._print_total_fee)
        self.ui.toolButton_export_pdf.clicked.connect(self._export_pdf)

    def _display_schedule_table(self):
        html = self._get_html()
        self.ui.textEdit_schedule_table.setHtml(html)

    @staticmethod
    def _to_date(value):
        if value is None:
            return None

        if isinstance(value, datetime.datetime):
            return value.date()

        if isinstance(value, datetime.date):
            return value

        text = string_utils.xstr(value)[:10]
        try:
            return datetime.datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _get_nurse_schedule(self, first_date, last_date):
        """整月護理師班表一次撈回.

        回傳 {(日, 醫師姓名, 診別): 護理師姓名}, 取代原本逐筆病歷各查一次
        nurse_schedule 的 N+1。
        """
        nurse_schedule = {}

        sql = f'''
            SELECT ScheduleDate, Doctor, Nurse1, Nurse2, Nurse3
            FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{first_date}" AND "{last_date}"
        '''
        try:
            rows = self.database.select_record(sql)
        except Exception:
            return nurse_schedule

        for row in rows:
            schedule_date = self._to_date(row["ScheduleDate"])
            if schedule_date is None:
                continue

            doctor = string_utils.xstr(row["Doctor"])
            for period, field_name in PERIOD_NURSE_FIELD.items():
                nurse = string_utils.xstr(row[field_name])
                if nurse == "":
                    continue

                key = (schedule_date.day, doctor, period)
                if key not in nurse_schedule:  # 同日同醫師重複列只取第一筆
                    nurse_schedule[key] = nurse

        return nurse_schedule

    def _get_medical_record(self):
        last_day = calendar.monthrange(self.apply_year, self.apply_month)[1]
        medical_record = [
            {"早班": [], "午班": [], "晚班": []} for x in range(last_day + 1)
        ]

        first_date = datetime.date(self.apply_year, self.apply_month, 1)
        last_date = datetime.date(self.apply_year, self.apply_month, last_day)
        start_date = f"{first_date} 00:00:00"
        end_date = f"{last_date} 23:59:59"

        nurse_schedule = self._get_nurse_schedule(first_date, last_date)

        # 原本是撈回全月每一筆病歷再於 Python 端去重複, 一個月上千列;
        # 實際只需要相異的 (日, 診別, 醫師), 直接在資料庫端 GROUP BY,
        # 以 MIN(CaseDate) 排序維持原本「依就診時間先後」的護理師名單順序
        sql = f'''
            SELECT
                DayOfMonth(CaseDate) AS CaseDay, Period, Doctor,
                MIN(CaseDate) AS FirstCaseDate
            FROM cases
            WHERE
                (InsType = "健保") AND
                (ApplyType != '不申報') AND
                (CaseDate BETWEEN "{start_date}" AND "{end_date}")
            GROUP BY CaseDay, Period, Doctor
            ORDER BY MIN(CaseDate), Doctor
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            case_day = number_utils.get_integer(row["CaseDay"])
            period = string_utils.xstr(row["Period"])

            if case_day < 1 or case_day > last_day:
                continue

            if period not in medical_record[case_day]:  # 診別空白或非早/午/晚班
                continue

            real_doctor_name = string_utils.xstr(row["Doctor"])
            doctor_name = real_doctor_name.replace(",", "")

            nurse = nurse_schedule.get((case_day, real_doctor_name, period), "")
            if nurse != "":
                doctor_name += f"({nurse})"
                if nurse not in self.nurse_list:
                    self.nurse_list.append(nurse)

            if doctor_name not in medical_record[case_day][period]:
                medical_record[case_day][period].append(doctor_name)

        return medical_record

    def _get_summary_html(self):
        year = self.ins_generate_date.year() - 1911
        month = self.ins_generate_date.month()
        day = self.ins_generate_date.day()
        apply_date = f"{year:0>3} 年 {month:0>2} 月 {day:0>2} 日"

        doctor_count = 0
        total_days = 0
        doctor_html = ""
        for row in self.ins_calculated_table:
            if row["doctor_type"] == "醫師":
                doctor_count += 1
                total_days += row["diag_days"]
                doctor_name = row["doctor_name"]
                doctor_days = row["diag_days"]
                doctor_html += f"""
                    <tr>
                        <td>
                            {doctor_name}醫師: {doctor_days}天
                        </td>
                    </tr>
                """

        nurse_html = ""
        for nurse in self.nurse_list:
            nurse_html += f"""
                <tr>
                    <td>
                        {nurse}護理師
                    </td>
                </tr>
            """

        nurse_count = len(self.nurse_list)

        html = f"""
            <div>
                <table align=center cellpadding="1" cellspacing="0" width="90%">
                    <tbody>
                        <br>
                        <tr>
                            <td>
                                <h4>* 本月份專任醫師合計{doctor_count}名, 門診天數合計{total_days}天.</h4>
                            </td>
                        </tr>
                        {doctor_html}
                        <br>
                        <tr>
                            <td>
                                <h4>* 本月份護理人員合計{nurse_count}名, 名單如下.</h4>
                            </td>
                        </tr>
                        {nurse_html}
                        <br><br>
                        <tr>
                            <td><h4>負責醫師 (簽名):</h4></td>
                            <td><h4>日期: {apply_date}</h4></td>
                        </hr>
                    </tbody>
                </table>
            </div
        """

        return html

    def _get_html(self):
        if self._html is not None:  # 顯示/列印/匯出共用, 不必重組
            return self._html

        apply_date = (
            f"{self.apply_year - 1911:0>3}年{self.apply_month:0>2}月 {self.period}"
        )
        summary = self._get_summary_html()
        clinic_name = self._clinic_name
        telephone = self._telephone

        week_html = "".join([self._get_week_data(week_no) for week_no in range(1, 7)])

        self._html = f"""
            <html>
                <body>
                    <div>
                        <h2 style="text-align: center;">{clinic_name}  醫師護理師(月)門診排班表</h2>
                        <h4 style="text-align: center;">
                            院所代號: {self.clinic_id}  電話: {telephone}  送核月份: {apply_date}
                        </h4>
                    </div>
                    <div>
                        <table align=center cellpadding="1" cellspacing="0" width="100%"
                         style="border-width: 1px; border-style: solid;">
                            <thead>
                                <tr>
                                    <th width="5%">周別</th>
                                    <th width="13%">週日</th>
                                    <th width="13%">週一</th>
                                    <th width="13%">週二</th>
                                    <th width="13%">週三</th>
                                    <th width="13%">週四</th>
                                    <th width="13%">週五</th>
                                    <th width="13%">週六</th>
                                </tr>
                            </thead>
                            <tbody>
                                {week_html}
                            </tbody>
                        </table>
                    </div>
                    {summary}
                </body>
            </html>
        """

        return self._html

    def _get_doctor_list(self, day, period):
        if day == "":
            return None

        doctor_list = []
        for doctor in sorted(
            self.medical_record[day][period], reverse=True
        ):  # 醫師姓名長的放在前面
            if len(doctor_list) == 0:
                doctor_list.append(doctor)
                continue

            duplicated = False
            for doctor_name in doctor_list:
                if doctor in doctor_name:  # 過濾重複的醫師姓名 (有護理師與醫師逗號衝突)
                    duplicated = True
                    break

            if not duplicated:
                doctor_list.append(doctor)

        return doctor_list

    def _get_week_data(self, week_no):
        week_list = ["", "", "", "", "", "", ""]
        doctor_week = [
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
        ]
        doctor_list = [
            ["", "", "", "", "", "", ""],
            ["", "", "", "", "", "", ""],
            ["", "", "", "", "", "", ""],
        ]

        for day in range(1, len(self.month_table) + 1):
            week = self.month_table[day][0]
            if week == week_no:
                week_day = self.month_table[day][1]
                week_list[week_day] = day
                doctor_week[0][week_day] = self._get_doctor_list(day, "早班")
                doctor_week[1][week_day] = self._get_doctor_list(day, "午班")
                doctor_week[2][week_day] = self._get_doctor_list(day, "晚班")

        for i in range(len(doctor_week)):
            for j in range(len(doctor_week[i])):
                if doctor_week[i][j] is not None:
                    doctor_list[i][j] = "<br>".join(doctor_week[i][j])

        html = self._get_week_html(week_list, doctor_list)

        return html

    @staticmethod
    def _get_week_html(week_list, doctor_list):
        sun, mon, tue, wed, thu, fri, sat = week_list

        (
            doctor_11,
            doctor_12,
            doctor_13,
            doctor_14,
            doctor_15,
            doctor_16,
            doctor_17,
        ) = doctor_list[0]
        (
            doctor_21,
            doctor_22,
            doctor_23,
            doctor_24,
            doctor_25,
            doctor_26,
            doctor_27,
        ) = doctor_list[1]
        (
            doctor_31,
            doctor_32,
            doctor_33,
            doctor_34,
            doctor_35,
            doctor_36,
            doctor_37,
        ) = doctor_list[2]

        html = f"""
            <tr bgcolor="LightGray">
                <td align=center>日期</td>
                <td><b>{sun}</b></td>
                <td><b>{mon}</b></td>
                <td><b>{tue}</b></td>
                <td><b>{wed}</b></td>
                <td><b>{thu}</b></td>
                <td><b>{fri}</b></td>
                <td><b>{sat}</b></td>
            </tr>
            <tr>
                <td style="text-align:center; vertical-align:middle">早診</td>
                <td>{doctor_11}</td>
                <td>{doctor_12}</td>
                <td>{doctor_13}</td>
                <td>{doctor_14}</td>
                <td>{doctor_15}</td>
                <td>{doctor_16}</td>
                <td>{doctor_17}</td>
            </tr>
            <tr>
                <td style="text-align:center; vertical-align:middle">午診</td>
                <td>{doctor_21}</td>
                <td>{doctor_22}</td>
                <td>{doctor_23}</td>
                <td>{doctor_24}</td>
                <td>{doctor_25}</td>
                <td>{doctor_26}</td>
                <td>{doctor_27}</td>
            </tr>
            <tr>
                <td style="text-align:center; vertical-align:middle">晚診</td>
                <td>{doctor_31}</td>
                <td>{doctor_32}</td>
                <td>{doctor_33}</td>
                <td>{doctor_34}</td>
                <td>{doctor_35}</td>
                <td>{doctor_36}</td>
                <td>{doctor_37}</td>
            </tr>
        """

        return html

    def _get_month_table(self):
        last_day = calendar.monthrange(self.apply_year, self.apply_month)[1]
        start_day = datetime.datetime(self.apply_year, self.apply_month, 1).weekday()
        if start_day == 6:
            start_day = 0
        else:
            start_day += 1

        month_table = {}
        week_no = 1
        for i in range(1, last_day + 1):
            month_table[i] = (week_no, start_day)
            start_day += 1
            if start_day > 6:
                start_day = 0
                week_no += 1

        return month_table

    # 列印醫護排班表
    def _print_total_fee(self):
        html = self._get_html()
        printer_utils.print_form_ins_apply_schedule_table(
            self, self.database, self.system_settings, html, self.apply_date
        )

    def _export_pdf(self):
        html = self._get_html()
        printer_utils.print_form_ins_apply_schedule_table(
            self, self.database, self.system_settings, html, self.apply_date, "pdf"
        )
