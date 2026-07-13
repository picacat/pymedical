# -*- coding: UTF-8 -*-
# 全民健康保險中醫三高病人加強照護方案 FB.XML 產生器
# 格式依據: 健保署「中醫三高病人加強照護方案 XML 批次上傳格式說明」

import datetime
import json
import os

# ---------- 共用轉換 ----------


def to_xml_value(value):
    """None 或空白轉 'N'(無)，用於 h017/h034/h036/h037 等欄位"""
    if value is None or str(value).strip() == "":
        return "N"
    return str(value)


def to_xml_date(value):
    """date 物件或 'YYYY-MM-DD' 字串 -> 'YYYYMMDD'，None 回傳空字串"""
    if value is None:
        return ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y%m%d")
    return str(value).replace("-", "")


def to_xml_text(value):
    """跳脫 XML 特殊字元（地址、姓名、其他說明等自由文字欄位使用）"""
    if value is None:
        return ""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def xml_tag(tag, value):
    """組單一標籤: <d001>A123456789</d001>"""
    return f"<{tag}>{value}</{tag}>"


# ---------- 檔名 ----------
def get_next_sequence(database, prefix):
    """從 patient_assessment.UploadFileName 取同年月最大流水號 +1"""
    sql = """
        SELECT MAX(SUBSTR(UploadFileName, %s, 3)) AS MaxSequence
        FROM patient_assessment
        WHERE UploadFileName LIKE %s
    """
    rows = database.select_record(sql, (len(prefix) + 1, f"{prefix}%"))
    max_sequence = rows[0]["MaxSequence"] if rows else None
    return int(max_sequence) + 1 if max_sequence else 1


def get_upload_file_name(database, division, hosp_id):
    today = datetime.date.today()
    roc_year_month = f"{today.year - 1911:03d}{today.month:02d}"
    prefix = f"{division}{hosp_id}{roc_year_month}"
    sequence = get_next_sequence(database, prefix)
    return f"{prefix}{sequence:03d}FB.xml"


# ---------- XML 區段 ----------


def build_case_section(row):
    """case 段 d001~d009，row 需含 patient 與 assessment 的 JOIN 結果"""
    gender = "1" if row["Gender"] == "男" else "2"  # d004

    return [
        "<case>",
        xml_tag("d001", row["ID"]),  # 身分證號
        xml_tag("d002", to_xml_date(row["Birthday"])),  # 生日
        xml_tag("d003", to_xml_text(row["Name"])),  # 姓名
        xml_tag("d004", gender),  # 性別 1男 2女
        xml_tag("d005", to_xml_text(row["Address"])),  # 地址
        xml_tag("d006", row["Cellphone"] or row["Telephone"] or ""),  # 電話
        xml_tag("d007", row["Doctor"]),  # 醫事人員身分證號
        xml_tag("d008", row["CaseType"]),  # 個案類別
        xml_tag("d009", to_xml_date(row["CaseDate"])),  # 收案日期
        "</case>",
    ]


# ---------- 主函數 ----------


def generate_fb_xml(database, division, hosp_id, rows, upload_folder):
    """產生 FB 上傳檔，回傳完整檔案路徑"""
    xml_lines = ['<?xml version="1.0" encoding="Big5"?>', "<fb>"]
    xml_lines.append(xml_tag("hospid", hosp_id))

    for row in rows:
        xml_lines.extend(build_case_section(row))

    for row in rows:
        if row["CloseDate"] is not None:
            xml_lines.extend(build_close_section(row))

        content = json.loads(row["Content"])
        scores = calc_lifestyle_scores(content, row["Gender"])
        xml_lines.extend(build_health_section(row, content, scores))

    xml_lines.append("</fb>")

    file_name = get_upload_file_name(database, division, hosp_id)  # 只管取名
    file_path = os.path.join(upload_folder, file_name)  # 只在這裡用資料夾
    with open(file_path, "w", encoding="cp950", errors="strict") as f:
        f.write("\n".join(xml_lines))

    # verify_xml(file_path)  # 自我驗證，格式不良立刻炸

    return file_path


def build_close_section(row):
    """close 段 c001~c005，僅結案個案呼叫"""
    return [
        "<close>",
        xml_tag("c001", row["ID"]),  # 身分證號
        xml_tag("c002", to_xml_date(row["Birthday"])),  # 生日
        xml_tag("c003", to_xml_date(row["VisitDate"])),  # 就醫日期
        xml_tag("c004", to_xml_date(row["CloseDate"])),  # 結案日期
        xml_tag("c005", row["CloseReason"]),  # 結案原因
        "</close>",
    ]


# ---------- 生活型態量表計分 (附件4) ----------


def _score_from_text(text, score_table, default=0):
    """依 comboBox 文字查配分表"""
    return score_table.get(str(text), default)


def calc_lifestyle_scores(content, gender):
    """從 content 的原始作答計算五領域分數 h009~h013
    gender: '男' or '女'，第15/16題計分用
    """
    get = content.get

    # h009 正向社會連結: 第1,3,5,7,9題各2分 (h009_items 勾選明細)
    items = get("h009_items") or ""
    h009 = len([i for i in items.split("_") if i]) * 2

    # h010 身體活動: 第13題(0,1天=0,1分,2天以上=2分), 第19,22題級距
    ls13 = get("ls13") or 0
    score13 = min(ls13, 2)  # 0->0, 1->1, 2~7->2
    score19 = _score_from_text(
        get("ls19"),
        {
            "少於1": 3,
            "1": 3,
            "2": 3,
            "3": 3,
            "4": 3,
            "5": 3,
            "6": 1,
            "7": 1,
        },
        default=0,
    )  # 8以上=0分 (3,1,0)

    score22 = _score_from_text(
        get("ls22"),
        {
            "小於30": 0,
            "30": 1,
            "45": 1,
            "60": 2,
            "90": 3,
            "120": 4,
            "150": 5,
            "180": 5,
            "210": 5,
            "240": 5,
            "270": 5,
            "300": 5,
            "大於300": 5,
        },
    )

    h010 = score13 + score19 + score22

    # h011 避免危害物質: 第6題否=5分, 第11題否=1分, 第15,16題依性別
    h011 = 0
    if get("ls06") != 1:
        h011 += 5
    if get("ls11") != 1:
        h011 += 1
    limit_15 = (
        {"少於1", "1", "2", "3"} if gender == "女" else {"少於1", "1", "2", "3", "4"}
    )
    if str(get("ls15")) in limit_15:
        h011 += 2  # 女3以下、男4以下
    limit_16 = {"少於1", "1"} if gender == "女" else {"少於1", "1", "2"}
    if str(get("ls16")) in limit_16:
        h011 += 2  # 女1以下、男2以下

    # h012 睡眠與壓力管理: 第4,8題各2分, 第10題1分, 第17題(0,3,5分)
    h012 = 0
    if get("ls04") == 1:
        h012 += 2
    if get("ls08") == 1:
        h012 += 2
    if get("ls10") == 1:
        h012 += 1
    h012 += _score_from_text(
        get("ls17"),
        {
            "少於1": 0,
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5": 0,
            "6": 0,
            "7": 3,
            "8": 5,
            "9": 5,
            "10或更多": 5,
        },
    )

    # h013 營養: 第2,12題各1分, 第14,18,20,21題級距各2分
    h013 = 0
    if get("ls02") == 1:
        h013 += 1
    if get("ls12") == 1:
        h013 += 1

    h013 += _score_from_text(get("ls14"), {"少於1": 2, "1": 2})  # 少於1、1=2分
    h013 += _score_from_text(
        get("ls18"),
        {
            "少於1": 0,
            "1": 1,
            "2": 2,
            "3": 2,
            "4": 2,
            "5": 2,
            "6": 2,
            "7": 2,
            "8": 2,
            "9": 2,
            "10或更多": 2,
        },
    )
    h013 += _score_from_text(get("ls20"), {"少於1": 2, "1": 2})  # 少於1,1=2分

    h013 += _score_from_text(
        get("ls21"),
        {
            "少於1": 0,
            "1": 1,
            "2": 1,
            "3": 2,
            "4": 2,
            "5": 2,
            "6": 2,
            "7": 2,
            "8": 2,
            "9": 2,
            "10或更多": 2,
        },
    )

    return {"h009": h009, "h010": h010, "h011": h011, "h012": h012, "h013": h013}


def build_health_section(row, content, scores):
    """health 段 h001~h043"""
    lines = [
        "<health>",
        xml_tag("h001", row["ID"]),
        xml_tag("h002", to_xml_date(row["Birthday"])),
    ]

    # h003~h008 基本
    lines.append(xml_tag("h003", to_xml_text(content.get("h003"))))
    lines.append(xml_tag("h004", content.get("h004") or ""))
    if content.get("h004") == "9":
        lines.append(xml_tag("h005", to_xml_text(content.get("h005"))))
    lines.append(xml_tag("h006", content.get("h006") or ""))
    lines.append(xml_tag("h007", content.get("h007") or ""))
    if "99" in (content.get("h007") or "").split("_"):
        lines.append(xml_tag("h008", to_xml_text(content.get("h008"))))

    # h009~h013 分數
    for code in ("h009", "h010", "h011", "h012", "h013"):
        lines.append(xml_tag(code, scores[code]))

    # h014~h016 菸酒檳榔 (非必填，有值才輸出)
    for code in ("h014", "h015", "h016"):
        if content.get(code):
            lines.append(xml_tag(code, content[code]))

    # h017~h018 慢性病史 (無勾選->N)
    lines.append(xml_tag("h017", to_xml_value(content.get("h017"))))
    if "99" in (content.get("h017") or "").split("_"):
        lines.append(xml_tag("h018", to_xml_text(content.get("h018"))))

    # h019~h033 家族病史
    lines.append(xml_tag("h019", content.get("h019") or "Y"))
    if content.get("h019") == "N":
        for code in (
            "h020",
            "h021",
            "h022",
            "h023",
            "h024",
            "h025",
            "h026",
            "h027",
            "h028",
            "h029",
            "h030",
        ):
            if content.get(code):
                lines.append(xml_tag(code, content[code]))
        if content.get("h031"):
            lines.append(xml_tag("h031", to_xml_text(content["h031"])))
        if content.get("h032"):
            lines.append(xml_tag("h032", content["h032"]))
        lines.append(xml_tag("h033", content.get("h033") or "N"))

    # h034~h035 長期藥物 (無勾選->N)
    lines.append(xml_tag("h034", to_xml_value(content.get("h034"))))
    if "99" in (content.get("h034") or "").split("_"):
        lines.append(xml_tag("h035", to_xml_text(content.get("h035"))))

    # h036~h037 過敏史 (空白->N)
    lines.append(xml_tag("h036", to_xml_text(content.get("h036")) or "N"))
    lines.append(xml_tag("h037", to_xml_text(content.get("h037")) or "N"))

    # h038~h043 身體數據
    for code in ("h038", "h039", "h040", "h041", "h042", "h043"):
        lines.append(xml_tag(code, content.get(code) or ""))

    lines.append("</health>")
    return lines
