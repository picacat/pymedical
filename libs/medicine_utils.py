# 2021.12.27
# -*- coding: UTF-8 -*-

import re
import webbrowser

from libs import string_utils


def set_medicine_extend(database, medicine_key, extend_type, description):
    sql = f'''
        SELECT MedicineKey FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        remove_medicine_extend(database, medicine_key, extend_type)

    fields = ["MedicineKey", "ExtendType", "Description"]
    data = [
        medicine_key,
        extend_type,
        description,
    ]
    database.insert_record("medextend", fields, data)


def get_medicine_extend(database, medicine_key, extend_type):
    description = None

    sql = f'''
        SELECT Description FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    rows = database.select_record(sql)
    if len(rows) > 0:
        row = rows[0]
        description = string_utils.xstr(row["Description"])

    return description


def remove_medicine_extend(database, medicine_key, extend_type):
    sql = f'''
        DELETE FROM medextend
        WHERE
            MedicineKey = {medicine_key} AND
            ExtendType = "{extend_type}"
    '''
    database.exec_sql(sql)


def open_medicine_library(medicine_type, medicine_name):
    MEDICINE_URL_LIST = {
        "車前子": "B00163",
        "一貫煎": "F00081",
        "九仙散": "F00087",
        "九味羌活湯": "F00003",
        "二妙散": "F00154",
        "二陳湯": "F00165",
        "八正散": "F00149",
        "八珍湯": "F00076",
        "十灰散": "F00123",
        "十棗湯": "F00024",
        "三子養親湯": "F00173",
        "三仁湯": "F00150",
        "大定風珠": "F00137",
        "大承氣湯": "F00017",
        "大柴胡湯": "F00027",
        "大秦艽湯": "F00129",
        "大陷胸湯": "F00019",
        "大黃牡丹湯": "F00018",
        "大黃附子湯": "F00020",
        "大補陰丸": "F00080",
        "小半夏湯": "F00111",
        "小青龍湯": "F00005",
        "小建中湯": "F00061",
        "小活絡單": "F00130",
        "小柴胡湯": "F00026",
        "小陷胸湯": "F00169",
        "川芎茶調散": "F00128",
        "五皮散": "F00158",
        "五苓散": "F00155",
        "六一散": "F00057",
        "六味地黃丸": "F00078",
        "升麻葛根湯": "F00012",
        "天王補心丹": "F00096",
        "天麻鉤藤飲": "F00136",
        "天臺烏藥散": "F00107",
        "止嗽散": "F00006",
        "仙方活命飲": "F00041",
        "加減葳蕤湯": "F00016",
        "半夏白朮天麻湯": "F00174",
        "半夏厚朴湯": "F00104",
        "半夏瀉心湯": "F00033",
        "右歸丸": "F00083",
        "四君子湯": "F00067",
        "四物湯": "F00073",
        "四神丸": "F00089",
        "四逆散": "F00030",
        "四逆湯": "F00063",
        "失笑散": "F00120",
        "左金丸": "F00044",
        "左歸丸": "F00079",
        "平胃散": "F00146",
        "正柴胡飲": "F00007",
        "玉女煎": "F00048",
        "玉屏風散": "F00071",
        "玉真散": "F00132",
        "瓜蒂散": "F00182",
        "甘露消毒丹": "F00151",
        "生化湯": "F00119",
        "生脈散": "F00070",
        "白虎湯": "F00034",
        "白頭翁湯": "F00051",
        "回陽救急湯": "F00064",
        "地黃飲子": "F00084",
        "安宮牛黃丸": "F00098",
        "朱砂安神丸": "F00095",
        "百合固金湯": "F00145",
        "竹葉石膏湯": "F00035",
        "至寶丹": "F00100",
        "血府逐瘀湯": "F00115",
        "吳茱萸湯": "F00062",
        "完帶湯": "F00072",
        "杏蘇散": "F00138",
        "牡蠣散": "F00086",
        "芍藥湯": "F00050",
        "貝母瓜蔞散": "F00171",
        "防己黃芪湯": "F00157",
        "固沖湯": "F00092",
        "固經丸": "F00093",
        "定喘湯": "F00110",
        "定癇丸": "F00175",
        "易黃湯": "F00094",
        "炙甘草湯": "F00077",
        "羌活勝濕湯": "F00163",
        "金鈴子散": "F00105",
        "金鎖固精丸": "F00090",
        "青蒿鱉甲湯": "F00052",
        "保和丸": "F00176",
        "厚朴溫中湯": "F00106",
        "咳血方": "F00124",
        "苓甘五味薑辛湯": "F00172",
        "苓桂朮甘湯": "F00159",
        "香蘇散": "F00004",
        "香薷散": "F00056",
        "桂枝湯": "F00002",
        "桂枝茯苓丸": "F00121",
        "桂苓甘露飲": "F00058",
        "桑杏湯": "F00139",
        "桑菊飲": "F00009",
        "桑螵蛸散": "F00091",
        "柴葛解肌湯": "F00011",
        "桃核承氣湯": "F00114",
        "消風散": "F00133",
        "烏梅丸": "F00181",
        "益胃湯": "F00143",
        "真人養臟湯": "F00088",
        "真武湯": "F00160",
        "茵陳蒿湯": "F00148",
        "健脾丸": "F00178",
        "參苓白朮散": "F00068",
        "參蘇飲": "F00014",
        "敗毒散": "F00013",
        "旋覆代赭湯": "F00112",
        "涼膈散": "F0039",
        "清胃散": "F00047",
        "清氣化痰丸": "F00168",
        "清骨散": "F00053",
        "清暑益氣湯": "F00059",
        "清絡飲": "F00055",
        "清營湯": "F00036",
        "清燥救肺湯": "F00140",
        "牽正散": "F00131",
        "理中丸": "F00060",
        "羚角鉤藤湯": "F00134",
        "逍遙散": "F00031",
        "連朴飲": "F00152",
        "麥門冬湯": "F00142",
        "麻子仁丸 (脾約丸) ": "F00022",
        "麻黃杏仁甘草石膏湯": "F00010",
        "麻黃細辛附子湯": "F00015",
        "麻黃湯": "F00001",
        "復元活血湯": "F00117",
        "普濟消毒飲": "F00040",
        "犀角地黃湯": "F00037",
        "痛瀉要方": "F00032",
        "紫雪丹": "F00099",
        "腎氣丸": "F00082",
        "越鞠丸": "F00102",
        "陽和湯": "F00066",
        "黃土湯": "F00127",
        "黃連解毒湯": "F00038",
        "黃龍湯": "F00025",
        "暖肝煎": "F00108",
        "溫脾湯": "F00021",
        "溫經湯": "F00118",
        "溫膽湯": "F00166",
        "當歸六黃湯": "F00054",
        "當歸四逆湯": "F00065",
        "當歸拈痛湯": "F00153",
        "當歸補血湯": "F00074",
        "葦莖湯": "F00045",
        "葛花解酲湯": "F00180",
        "葛根黃芩黄連湯": "F00049",
        "補中益氣湯": "F00069",
        "補陽還五湯": "F00116",
        "達原飲": "F00029",
        "實脾散": "F00161",
        "槐花散": "F00126",
        "滾痰丸": "F00170",
        "蒿芩清膽湯": "F00028",
        "酸棗仁湯": "F00097",
        "銀翹散": "F00008",
        "增液湯": "F00141",
        "豬苓湯": "F00156",
        "養陰清肺湯": "F00144",
        "導赤散": "F00042",
        "橘皮竹茹湯": "F00113",
        "獨活寄生湯": "F00164",
        "龍膽瀉肝湯": "F00043",
        "龜鹿二仙膠": "F00085",
        "濟川煎": "F00023",
        "歸脾湯": "F00075",
        "瀉白散": "F00046",
        "鎮肝熄風湯": "F00135",
        "蘇子降氣湯": "F00109",
        "蘇合香丸": "F00101",
        "鱉甲煎丸": "F00122",
        "枳實消痞丸": "F00179",
        "枳實導滯丸": "F0177",
        "枳實薤白桂枝湯": "F00103",
        "茯苓丸": "F00167",
        "萆薢分清散": "F00162",
        "藿香正氣散": "F00147",
    }

    if medicine_type in ["單方", "水藥"]:
        url = "https://sys01.lib.hkbu.edu.hk/cmed/mmid/detail.php?pid="
    else:
        url = "https://sys01.lib.hkbu.edu.hk/cmed/cmfid/detail.php?lang=cht&id="

    try:
        clean_name = re.sub(r"\s*\(.*\)", "", medicine_name).strip()
        if clean_name in MEDICINE_URL_LIST:
            med_id = MEDICINE_URL_LIST[clean_name]
            full_url = url + med_id

            # 打開預設瀏覽器並前往網址
            webbrowser.open(full_url)
        else:
            print(f"找不到藥名: {clean_name}")
            return
    except Exception:
        return
