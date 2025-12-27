# 2018.04.30
from PyQt5.QtWidgets import QMessageBox, QPushButton

import io
import base64

from libs import class_utils
from libs import date_utils
from libs import patient_utils
from libs import number_utils
from libs import nhi_utils
from libs import string_utils
from libs import case_utils
import base64

NORMAL_CARD = '1'
RETURN_CARD = '2'

CSHIS6_ERROR_MESSAGE = {
    -1: ['不明的錯誤', None],
    1001: ['控制軟體已初始化', None],
}

ERROR_MESSAGE = {
    -1: ['不明的錯誤', None],
    0000: ['正確有效', None],
    1000: ['控制軟體尚未初始化', None],
    1001: ['控制軟體已初始化', None],
    1002: ['未查詢到指定的或是任何有效的裝置名稱', None],
    1003: ['正式卡與測試卡不能混用', None],
    1004: ['向雲端 server 取健保卡資料失敗', None],
    1005: ['向雲端 server 取 QRCodeToken 失敗', None],
    1006: ['向雲端 server 更新健保卡資料失敗', None],
    1007: ['向雲端 server 取就醫序號失敗', None],
    1009: ['向雲端 server 退掛失敗', None],
    1010: ['向雲端 server 清除健保卡資料失敗', None],
    1011: ['取 HospID & SAMID 錯誤', None],
    1012: ['清除虛擬健保卡資料失敗', None],
    1013: ['認證碼編號無效，請重新安裝或聯絡虛擬健保卡技術團隊', None],
    1014: ['清除計時器失敗', None],
    1015: ['Device Token 過期，請關閉程式後再重新啟動', None],
    1016: ['Device Token 失效，請關閉程式後再重新啟動', None],
    1017: ['Device Token 不存在，請關閉程式後再重新啟動', None],
    1018: ['QRCode 過期，請重刷 QRCode', None],
    1019: ['QRCode 不存在，請重刷 QRCode', None],
    1020: ['重複使用 QRCode，請就診民眾重新整理頁面產生新的 QRCode', None],
    1021: ['QRCode Token 過期，請重刷 QRCode', None],
    1022: ['QRCode Token 失效，請重刷 QRCode', None],
    1023: ['QRCode Token 不存在，請重刷 QRCode', None],
    1024: ['裝置認證金鑰錯誤', None],
    1025: ['設置檔無認證編碼', None],
    1026: ['設置檔無 Device Token', None],
    1027: ['取重大傷病資料失敗', None],
    1028: ['取 ICD10 押碼失敗', None],
    1029: ['取 ICD10 解押碼失敗', None],
    1030: ['重大傷病組數異常', None],
    1033: ['計算就醫診療日期個數失敗', None],
    1034: ['計算民眾身分證個數失敗', None],
    1035: ['更新資料庫單一就診民眾就醫診療資料物件失敗', None],
    1036: ['更新資料庫就醫診療資料失敗', None],
    1037: ['刪除資料庫就醫資料失敗', None],
    1038: ['處方箋資料離線寫入資料庫失敗', None],
    1039: ['依狀態取資料庫離線處方箋資料失敗', None],
    1040: ['更新資料庫處方箋資料失敗', None],
    1041: ['刪除處方箋資料失敗', None],
    1042: ['醫事機構未參與虛擬健保卡試辦案', None],
    1043: ['版本不正確', None],
    1045: ['無登錄資料且離線，請使用者接上網路進行安裝', None],
    1046: ['離線使用認證已過期，請連上網路更新', None],
    1050: ['註冊失敗', None],
    1051: ['註冊失敗', None],
    1053: ['註冊失敗', None],
    1054: ['重複註冊', None],
    1055: ['雲端伺服器錯誤', None],
    1056: ['雲端伺服器錯誤', None],
    1057: ['登錄資料錯誤', None],
    1058: ['登錄資料錯誤', None],
    1059: ['登錄資料有效時間異常', None],
    1099: ['離線不提供此 API 服務', None],

    1100: ['沒有發現預設 PCSC 讀卡機', None],
    1101: ['目前沒有使用任何 PCSC 讀卡機', None],
    1102: ['未置入卡片，若卡片已插入，請將卡片取出再重新插入一次', '請重新插入卡片至讀卡機'],
    1103: ['切換卡片應用程式失敗', None],
    1199: ['PCSC 發生其它錯誤', None],

    1200: ['無法載入 Reader.dll 檔案', None],
    1201: ['開啟 Comport 失敗', None],
    1202: ['操作實體讀卡機失敗', None],
    1300: ['SAM 進入模式一失敗', None],
    1301: ['SAM 進入模式二失敗', None],
    1302: ['醫事機構已超過合約起迄', None],
    1303: ['醫事機構已停權', None],
    1304: ['SAM 已註銷', None],

    1400: ['醫事人員卡進入模式一失敗', None],
    1401: ['醫事人員卡進入模式二失敗', None],
    1402: ['醫事人員卡進入模式三失敗', '請插入醫事人員卡並完成醫事人員卡驗證'],
    1403: ['醫事人員卡不支援此功能', None],
    1410: ['醫事人員卡驗證 PIN 碼失敗', None],
    1420: ['HCA 驗簽失敗', None],
    1421: ['HCA 簽章逾時', None],
    1422: ['憑證不在有效期內', None],
    1423: ['未查詢到信任上層憑證', None],
    1424: ['憑證已註銷', None],

    1500: ['健保卡進入模式一失敗', None],
    1501: ['健保卡進入模式二失敗', None],
    1502: ['健保卡進入模式三失敗', None],
    1510: ['實體健保卡並無設定 PIN 碼', None],
    1511: ['尚未驗證 PIN 碼', None],
    1512: ['停用 HC PIN 碼失敗', None],
    1513: ['PIN 碼已驗證', None],
    1514: ['驗證 HC PIN 碼失敗', None],
    1515: ['呼叫的功能僅支援實體健保卡', None],
    1520: ['虛擬健保卡 Token 格式錯誤', None],
    1521: ['虛擬健保卡 Token 已逾時', None],
    1522: ['虛擬卡 Token 格式不符', None],
    1523: ['虛擬卡 Token 驗簽失敗', None],
    1524: ['虛擬卡 Token 已逾期', None],
    1525: ['虛擬卡 Token 已超過驗證次數', None],
    1526: ['虛擬卡無法呼叫 PIN 相關函式', None],
    1527: ['呼叫的功能僅支援虛擬健保卡', None],
    1528: ['找不到虛擬健保卡轉移暫存資料', None],
    1529: ['此虛擬健保卡轉移已被其它狀置使用', None],
    1530: ['虛擬健保卡轉移只能使用在同一家醫事機構', None],
    1531: ['虛擬健保卡已轉移或已失效', None],

    1600: ['使用讀卡機名稱無法查詢到 PCSC 讀卡機', None],
    1601: ['自動偵測預設讀卡機失敗', None],
    1610: ['雲端安全模組檔案格式錯誤', None],
    1611: ['沒有查詢到雲端安全模組編號', None],

    1700: ['與 DC 通訊連線異常', None],
    1701: ['與 DC 通訊命令代碼不存在', None],
    1702: ['與 DC 通訊回覆 HTTP 相關異常代碼', None],
    1703: ['Session 不存在或已逾期', None],
    1704: ['參數格式異常', None],
    1705: ['參數格式異常', None],
    1706: ['參數格式異常', None],
    1707: ['HCA 卡片已登出或在其它主機登入', None],
    1799: ['DC 端未定義錯誤', None],

    3100: ['驗證簽章錯誤', None],

    3200: ['尚未驗證健保卡 PIN 碼', None],
    3201: ['超過卡片有期限', None],
    3202: ['非醫療院所', None],
    3203: ['卡片已註銷', None],
    3204: ['就醫識別碼編碼失敗', None],
    3205: ['限制就醫', None],
    3206: ['無新生兒生日', None],
    3207: ['新生兒依附就醫已逾時', None],
    3208: ['找不到「就醫資料登錄」中的該組資料', None],
    3209: ['已寫入診斷碼', None],
    3210: ['ICD 10 編碼失敗', None],
    3211: ['非同一家醫事機構', None],
    3212: ['僅用醫師才有權限呼叫此函式', None],
    3213: ['就醫可用次數為零', None],
    3214: ['最近 6 次就醫不含就醫類別 AC，不可單獨寫入預防保健或產檢紀錄', None],
    3215: ['最近 24 小時內同院所未曾執行保健服務項目紀錄，故不可取消保健服務（輸入 YA~YF 時檢查）', None],
    3216: ['不為女性', None],
    3217: ['近 24 小時內同院所未曾執行產檢服務紀錄，故不可取消產檢（輸入 XA 時檢查）', None],
    3218: ['不允許退掛，退掛時間已超過 24 小時', None],
    3219: ['就醫類別為數值才可退掛', None],
    3220: ['本筆就醫記錄已經退掛過，不可重覆退掛', None],
    3221: ['就醫可用次數不合理', None],
    3222: ['最近一次就醫序號不合理', None],
    3223: ['最近一次就醫年不合理', None],
    3224: ['最近一次就醫序號不合理', None],
    3225: ['就醫累計資料年不合理', None],
    3226: ['門住診就醫累計次數不合理', None],
    3227: ['就醫日期不一致', None],
    3228: ['不在保', None],
    3229: ['已停保', None],
    3230: ['已退保', None],
    3231: ['已停保或已退保 (查保)', None],
    3232: ['在查保名單中 (查保)', None],
    3233: ['個人及單位均欠費', None],
    3234: ['聲明不實', None],
    3235: ['其它原因', None],
    3236: ['同一時間重覆上傳', None],
    3237: ['未查詢到 Access Token', None],
    3238: ['Access Token 已逾時', None],
    3239: ['Access Token 尚未授權', None],
    3240: ['Access Token 拒絕授權', None],
    3241: ['虛擬卡 Token 不存在', None],
    3242: ['同時就醫時間相同', None],
    3243: ['非醫師或藥師', None],
    3244: ['虛擬健保卡 QR Code 已取得就醫資料', None],
    3245: ['簽章已取得就醫資料', None],

    3300: ['金鑰不存在', None],
    3301: ['無虛擬卡模型資料', None],
    3302: ['無 SAM 資料', None],
    3303: ['無虛擬健保卡暫存資料', None],
    3304: ['無驗簽暫存資料', None],

    3400: ['卡片更新失敗', None],
    3401: ['退掛失敗', None],
    3402: ['查保失敗', None],

    3500: ['PKI 服務失敗', None],
    3501: ['所傳入的診斷碼不在押碼範圍或所傳入的押碼內容不是有效的資料', None],
    3502: ['相容性元件版本不在白名單中', None],
    3503: ['相容性元件版本在黑名單中', None],

    4000: ['讀卡機timeout', '請檢查讀卡機連接埠是否接妥, 或是系統設定->讀卡機連接埠是否正確'],
    4012: ['未置入安全模組卡', '安全模組可能未正確安裝至讀卡機內, 請關掉讀卡機電源, 打開螺絲背蓋, 檢查安全模組卡是否安裝妥當.'],
    4013: ['未置入健保IC卡/虛擬健保卡', '請確定健保IC卡已經正確的插入讀卡機'],
    4014: ['未置入醫事人員卡', '請插入醫事人員卡'],
    4029: ['IC卡權限不足', None],
    4032: ['所插入非安全模組卡', None],
    4033: ['所置入非健保IC卡', None],
    4034: ['所置入非醫事人員卡', None],
    4042: ['醫事人員卡PIN尚未認證成功', None],
    4043: ['健保卡讀取/寫入作業異常', None],
    4050: ['安全模組尚未與IDC認證', '請執行[健保讀卡機安全模組認證]'],
    4051: ['安全模組與IDC認證失敗', None],
    4061: ['網路不通', '請檢查電腦網路接頭是否鬆脫或中華電信VPN網路數據機是否正常, 如有檢查困難, 請致電中華電信 0800-080-128 查詢'],
    4071: ['健保IC卡與IDC認證失敗', None],
    5001: ['就醫可用次數不足', '請執行[更新病患健保卡內容]作業, 若仍然無法取得可用次數, 請確認病患健保卡加保狀態'],
    5002: ['卡片已註銷', None],
    5003: ['卡片已過有限期限', None],
    5004: ['非新生兒一個月內就診', None],
    5005: ['讀卡機的日期時間讀取失敗', None],
    5006: ['讀取安全模組內的「醫療院所代碼」失敗', None],
    5007: ['寫入一組新的「就醫資料登錄」失敗', None],
    5008: ['安全模組簽章失敗', None],
    5009: ['無寫入就醫相關紀錄之權限', None],
    5010: ['同一天看診兩科(含)以上', None],
    5012: ['此人未在保或欠費', None],
    5015: ['「門診處方箋」讀取失敗。', None],
    5016: ['「長期處方箋」讀取失敗。', None],
    5017: ['「重要醫令」讀取失敗。', None],
    5020: ['要寫入的資料和健保IC卡不是屬於同一人。', None],
    5022: ['找不到「就醫資料登錄」中的該組資料。', None],
    5023: ['「就醫資料登錄」寫入失敗。', None],
    5028: ['HC卡「就醫費用紀錄」寫入失敗。', None],
    5033: ['「門診處方箋」寫入失敗。', None],
    5051: ['新生兒註記寫入失敗', None],
    5052: ['有新生兒出生日期，但無新生兒胞胎註記資料', None],
    5056: ['讀取醫事人員ID失敗', None],
    5057: ['過敏藥物寫入失敗。', None],
    5061: ['同意器官捐贈及安寧緩和醫療註記寫入失敗寫入失敗', None],
    5062: ['放棄同意器官捐贈及安寧緩和醫療註記輸入', None],
    5067: ['安全模組卡「醫療院所代碼」讀取失敗', None],
    5068: ['預防保健資料寫入失敗', None],
    5069: ['兒童預防保健服務紀錄寫入孕婦產檢欄位失敗', None],
    5071: ['緊急聯絡電話寫失敗。', None],
    5078: ['產前檢查資料寫入失敗', None],
    5079: ['性別不符，健保IC卡記載為男性', None],
    5081: ['最近24小時內同院所未曾就醫，故不可取消就醫', None],
    5082: ['最近24小時內同院所未曾執行產檢服務紀錄，故不可取消產檢', None],
    5083: ['最近6次就醫不含就醫類別AC，不可單獨寫入預防保健或產檢紀錄', None],
    5084: ['最近24小時內同院所未曾執行保健服務項目紀錄，故不可取消保健服務', None],
    5087: ['刪除「孕婦產前檢查(限女性)」全部11 組的資料失敗。', None],
    5093: ['預防接種資料寫入失敗', None],
    5102: ['使用者所輸入之pin 值，與卡上之pin值不合', None],
    5105: ['原PIN碼尚未通過認證', '請先執行[驗證病患健保卡密碼]作業'],
    5107: ['使用者輸入兩次新PIN 值，兩次PIN 值不合', None],
    5108: ['密碼變更失敗', None],
    5109: ['密碼輸入過程按『取消』鍵', None],
    5110: ['變更健保IC卡密碼時, 請移除醫事人員卡', None],
    5111: ['停用失敗，且健保IC卡之Pin 碼輸入功能仍啟用', None],
    5122: ['被鎖住的醫事人員卡仍未解開', None],
    5130: ['更新健保IC卡內容失敗。', None],
    5141: ['未置入醫事人員卡, 僅能讀取重大傷病有效起訖日期', None],
    5150: ['卡片中無此筆就醫記錄', None],
    5151: ['就醫類別為數值才可退掛', None],
    5152: ['醫療院所不同，不可退掛', None],
    5153: ['本筆就醫記錄已經退掛過，不可重覆退掛', None],
    5154: ['退掛日期不符合規定', None],
    5160: ['就醫可用次數不合理', None],
    5161: ['最近一次就醫年不合理', None],
    5162: ['最近一次就醫序號不合理', None],
    5163: ['住診費用總累計不合理', None],
    5164: ['門診費用總累計不合理', None],
    5165: ['就醫累計資料年不合理', None],
    5166: ['門住診就醫累計次數不合理', None],
    5167: ['門診部分負擔費用累計不合理', None],
    5168: ['住診急性30天、慢性180天以下部分負擔費用累計不合理', None],
    5169: ['住診急性31天、慢性181天以上部分負擔費用累計不合理', None],
    5170: ['門診+住診部分負擔費用累計不合理', None],
    5171: ['[門診+住診(急性30天、慢性180天以下)]部分負擔費用累計不合理', None],
    5172: ['門診醫療費用累計不合理', None],
    5173: ['住診醫療費用累計不合理', None],
    5174: ['取就醫識別碼失敗', '請確定是否安裝新版讀卡機控制軟體'],
    6005: ['安全模組卡的外部認證失敗', None],
    6006: ['IDC的外部認證失敗', None],
    6007: ['安全模組卡的內部認證失敗', None],
    6008: ['寫入讀卡機日期時間失敗', None],
    6014: ['IDC 驗證簽章失敗', None],
    6015: ['檔案大小不合或檔案傳輸失敗', '建議分段上傳, 一次上傳30筆資料'],
    6016: ['記憶體空間不足', None],
    6017: ['權限不足無法開啟檔案或找不到檔案', None],
    6018: ['傳入參數錯誤', None],
    6019: ['醫事人員卡密碼不能為空白', '請輸入醫事人員卡密碼'],
    9001: ['送至IDC Message Header 檢核不符', None],
    9002: ['送至IDC語法不符', None],
    9003: ['與IDC作業逾時', None],
    9004: ['IDC異常無法Service', None],
    9005: ['要求的函式無法執行', '1.請確定元件是否為最新版, 2.讀卡機問題, 請更換讀卡機試試看'],
    9010: ['IDC無法驗證該卡片', None],
    9011: ['IDC驗證健保IC卡失敗', None],
    9012: ['IDC無該卡片資料', None],
    9013: ['無效的安全模組卡', None],
    9014: ['IDC對安全模組卡認證失敗', None],
    9015: ['安全模組卡對IDC認證失敗', None],
    9020: ['IDC驗章錯誤', None],
    9030: ['無法執行卡片管理系統的認證', None],
    9039: ['密碼(PIN碼)不正確', None],
    9040: ['無法執行健保IC卡Applet Perso認證', None],
    9041: ['PI碼長度錯誤', 'PIN碼長度不正確, PIN碼長度虛為6到8碼'],
    9042: ['密碼已過期', '請電醫事憑證管理中心詢問'],
    9043: ['PIN碼已鎖住', '請至醫事憑證管理中心進行解鎖碼作業'],
    9045: ['憑證狀態為已被撤銷', None],
    9050: ['無法執行安全模組卡世代碼更新認證', None],
    9051: ['安全模組卡世代碼更新認證失敗', None],
    9056: ['讀卡機或憑證未安裝', '偵測不到憑證載具'],
    9060: ['安全模組卡遭停約處罰', None],
    9061: ['安全模組卡不在有效期內', None],
    9062: ['安全模組卡合約逾期或尚未生效', None],
    9070: ['上傳資料大小不符無法接收檔案', None],
    9071: ['上傳日期與 Data Center 不一致', None],
    9081: ['卡片可用次數大於3次, 未達可更新標準', '不須執行健保卡卡片內容更新作業'],
    9082: ['此卡已被註銷, 無法進行卡片更新作業', '請改掛健保或自費'],
    9083: ['不在保', '請改掛健保或自費'],
    9084: ['停保中', '請改掛健保或自費'],
    9085: ['已退保', '請改掛健保或自費'],
    9086: ['個人欠費', '請改掛欠卡或自費'],
    9087: ['負責人欠費', None],
    9088: ['投保單位欠費', None],
    9089: ['個人及單位均欠費', None],
    9090: ['欠費且未在保', '請改掛欠卡或自費'],
    9091: ['聲明不實', None],
    9092: ['其他', None],
    9093: ['即時查保', '投保身分不一致'],
    9094: ['即時查保', '停保或退保'],
    9095: ['即時查保', '欠費'],
    9100: ['藥師藥局無權限', None],
    9101: ['所置入非醫師卡', None],
    9127: ['診斷碼異常', None],
    9129: ['持卡人於非限制院所就診', None],
    9130: ['醫事卡失效', None],
    9140: ['醫事卡逾效期', None],

    9200: ['安全模組檔目錄錯誤或不存在或數量超過一個以上', None],
    9201: ['初始安全模組檔讀取異常，請在C:\\NHI\\SAM\\COMX1目錄下放置健保署正確安全模組檔', None],
    9202: ['安全模組檔讀取異常，已在其它電腦使用過，請在C:\\NHI\\SAM\\COMX1目錄下放置健保署正確安全模組檔。', None],
    9203: ['卡片配對錯誤，正式卡與測試卡不能混用', None],
    9204: ['找不到讀卡機，或PCSC環境異常', None],
    9205: ['開啟讀卡機連結埠失敗', None],
    9210: ['健保IC卡內部認證失敗', None],
    9211: ['雲端安全模組(IDC)對健保IC卡認證失敗', None],
    9212: ['健保IC卡對雲端安全模組認證失敗', None],
    9213: ['雲端安全模組卡片更新逾時', None],
    9220: ['醫事人員卡內部認證失敗', None],
    9221: ['雲端安全模組(IDC)驗證醫事人員卡失敗', None],
    9230: ['安全模組檔「醫療院所名稱」讀取失敗', None],
    9231: ['安全模組檔「醫療院所簡稱」讀取失敗', None],
    9240: ['雲端安全模組主控台沒起動 ', None],
    9250: ['虛擬醫師驗 PIN 失敗', None],
    9251: ['虛擬醫師卡逾時,請重新登入', None],
    9267: ['同一醫師卡在另外一台電腦登入', None],

    9999: ['找不到醫事人員卡讀卡機', None],
    66008: ['防重送驗驗證失敗, 該序號失效', None],
    66501: ['憑證尚未生效或者已過期', None],
    66503: ['憑證狀態為已被撤銷', None],
    66508: ['展期或更新時發現憑證已展期完成', None],
}

INSURED_MARK_DICT = {
    '1': '低收入戶',
    '2': '榮民',
    '3': '基層醫療',
    '4': '中低收入戶',
    '8': '災民',
}

BASIC_DATA = {
    'card_no': '',
    'name': '',
    'patient_id': '',
    'birthday': '',
    'gender': '',
    'card_date': '',
    'cancel_mark': '',
    'emg_phone': '',
    'insured_code': '',
    'insured_mark': '',
    'card_valid_date': '',
    'card_available_count': '',
    'new_born_date': '',
    'new_born_mark': '',
}

TREAT_DATA = {
    'registered_date': '',
    'seq_number': '',
    'clinic_id': '',
    'security_signature': '',
    'sam_id': '',
    'register_duplicated': '',
    'identification': '',
}

TREATMENT_DATA = {
    'critical_illness': [],
    'treatments': [],
}

DISEASE_DATA = {
    'critical_illness': [],
    'diseases': [],
}

XML_FEEDBACK_DATA = {
    'sam_id': '',
    'clinic_id': '',
    'upload_time': '',
    'receive_time': '',
}


UPLOAD_TYPE_DICT = {
    None: '',
    '': '',
    '0': '0-尚未上傳',
    '1': '1-正常上傳',
    '2': '2-異常上傳',
    '3': '3-正常補正',
    '4': '4-異常補正',
}

TREAT_AFTER_CHECK_DICT = {
    None: '',
    '': '',
    '1': '1-正常',
    '2': '2-補卡',
}


def get_treat_item(course, share_type, treat_type=None):
    if share_type == '職業傷害':
        return 'AD'

    treat_item = '03'  # 中醫首次
    course_type = nhi_utils.get_course_type(course)
    
    if course_type == '療程':
        if treat_type in nhi_utils.HOME_CARE:  # 居家醫療
            treat_item = 'AH'  # 連續療程
        else:
            treat_item = 'AA'

    return treat_item


# 取得卡片註記
def get_cancel_mark(cancel_mark_code):
    cancel_mark = ''

    if cancel_mark_code == '1':
        cancel_mark = '正常卡'
    elif cancel_mark_code == '2':
        cancel_mark = '註銷卡'

    return cancel_mark


# 取得卡片保險身分
def get_insured_mark(insured_mark_code):
    try:
        insured_mark = INSURED_MARK_DICT[insured_mark_code]
    except Exception:
        insured_mark = '基層醫療'

    return insured_mark


# 取得健保卡內容
def decode_basic_data(buffer):
    basic_data_info = BASIC_DATA
    s = io.BytesIO(buffer)
    basic_data_info['card_no'] = s.read(12).decode('ascii').strip()
    basic_data_info['name'] = s.read(20).decode('big5', 'replace').strip()
    basic_data_info['patient_id'] = s.read(10).decode('ascii').strip()

    try:
        basic_data_info['birthday'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii'))
    except Exception:
        basic_data_info['birthday'] = None

    basic_data_info['gender'] = patient_utils.get_gender(s.read(1).decode('ascii').strip())

    try:
        basic_data_info['card_date'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii'))
    except Exception:
        basic_data_info['card_date'] = None

    basic_data_info['cancel_mark'] = get_cancel_mark(s.read(1).decode('ascii').strip())

    try:
        basic_data_info['emg_phone'] = s.read(14).decode('ascii').strip()
    except Exception:
        basic_data_info['emg_phone'] = None

    return basic_data_info


def decode_register_basic_data(buffer):
    basic_data_info = BASIC_DATA
    s = io.BytesIO(buffer)
    basic_data_info['card_no'] = s.read(12).decode('ascii').strip()
    basic_data_info['name'] = s.read(20).decode('big5', 'replace').strip()
    basic_data_info['patient_id'] = s.read(10).decode('ascii').strip()
    basic_data_info['birthday'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii'))
    basic_data_info['gender'] = patient_utils.get_gender(s.read(1).decode('ascii').strip())
    basic_data_info['card_date'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii'))
    basic_data_info['cancel_mark'] = get_cancel_mark(s.read(1).decode('ascii').strip())

    basic_data_info['insured_code'] = s.read(2).decode('ascii').strip()  # Reserved, not use
    basic_data_info['insured_mark'] = get_insured_mark(s.read(1).decode('ascii').strip())
    try:
        basic_data_info['card_valid_date'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii'))
    except Exception:
        basic_data_info['card_valid_date'] = ''

    basic_data_info['card_available_count'] = number_utils.get_integer(s.read(2).decode('ascii').strip())
    try:
        basic_data_info['new_born_date'] = date_utils.nhi_date_to_west_date(s.read(7).decode('ascii').strip())
    except Exception:
        basic_data_info['new_born_date'] = ''

    basic_data_info['new_born_mark'] = s.read(1).decode('ascii').strip()

    return basic_data_info


def decode_treat_data(buffer):
    treat_data_info = TREAT_DATA
    s = io.BytesIO(buffer)
    treat_data_info['registered_date'] = date_utils.nhi_datetime_to_west_datetime(s.read(13).decode('ascii'))
    treat_data_info['seq_number'] = s.read(4).decode('ascii').strip()
    treat_data_info['clinic_id'] = s.read(10).decode('ascii').strip()
    treat_data_info['security_signature'] = s.read(256).decode('ascii').strip()
    treat_data_info['sam_id'] = s.read(12).decode('ascii').strip()
    treat_data_info['register_duplicated'] = s.read(1).decode('ascii').strip()
    treat_data_info['identification'] = s.read(20).decode('ascii').strip()

    return treat_data_info


def decode_no_ic_card_treat_data(buffer):
    treat_data_info = TREAT_DATA
    s = io.BytesIO(buffer)
    treat_data_info['registered_date'] = date_utils.nhi_datetime_to_west_datetime(s.read(13).decode('ascii'))
    treat_data_info['seq_number'] = ''
    treat_data_info['clinic_id'] = s.read(10).decode('ascii').strip()
    treat_data_info['security_signature'] = ''
    treat_data_info['sam_id'] = ''
    treat_data_info['register_duplicated'] = ''
    treat_data_info['identification'] = s.read(20).decode('ascii').strip()

    return treat_data_info


def decode_treatment_data(buffer):
    treatment_data = TREATMENT_DATA
    treatment_data['critical_illness'].clear()
    treatment_data['treatments'].clear()

    s = io.BytesIO(buffer)
    for x in range(6):
        treatment_data['critical_illness'].append({
            'ci_validity_start': s.read(7).decode('ascii'),
            'ci_validity_end': s.read(7).decode('ascii')
        })

    for x in range(6):
        item = {}
        item['treat_item'] = s.read(2).decode('ascii')
        item['treat_newborn'] = s.read(1).decode('ascii')
        item['treat_date_time'] = s.read(13).decode('ascii')
        item['treat_after_check'] = s.read(1).decode('ascii')
        item['card'] = s.read(4).decode('ascii')
        item['treat_hosp_code'] = s.read(10).decode('ascii')
        item['treat_ot_tot_fee'] = int(s.read(8).decode('ascii'))
        item['hc_treat_ot_co_fee'] = int(s.read(8).decode('ascii'))
        item['treat_ot_inpa_fee'] = int(s.read(8).decode('ascii'))
        item['treat_ot_inpa_30'] = int(s.read(7).decode('ascii'))
        item['treat_ot_inpa_180'] = int(s.read(7).decode('ascii'))

        treatment_data['treatments'].append(item)

    return treatment_data


def decode_disease_data(buffer):
    disease_data = DISEASE_DATA
    disease_data['critical_illness'].clear()
    disease_data['diseases'].clear()

    s = io.BytesIO(buffer)
    for x in range(6):
        disease_data['critical_illness'].append({
            'ci_special_code': s.read(9).decode('ascii'),
            'ci_validity_start': s.read(7).decode('ascii'),
            'ci_validity_end': s.read(7).decode('ascii')
        })

    for x in range(6):
        item = {}
        item['case_date'] = s.read(13).decode('ascii')
        s.read(1).decode('ascii')
        item['disease1'] = s.read(7).decode('ascii')
        s.read(2).decode('ascii')
        item['disease2'] = s.read(7).decode('ascii')
        s.read(2).decode('ascii')
        item['disease3'] = s.read(7).decode('ascii')
        s.read(2).decode('ascii')
        item['disease4'] = s.read(7).decode('ascii')
        s.read(2).decode('ascii')
        s.read(7).decode('ascii')
        s.read(2).decode('ascii')
        s.read(7).decode('ascii')
        s.read(1).decode('ascii')

        disease_data['diseases'].append(item)

    return disease_data


def decode_xml_data(buffer):
    xml_feedback_data_info = XML_FEEDBACK_DATA
    s = io.BytesIO(buffer)

    xml_feedback_data_info['sam_id'] = s.read(12).decode('ascii').strip()
    xml_feedback_data_info['clinic_id'] = s.read(10).decode('ascii').strip()

    year = s.read(4).decode('ascii').strip()
    month = s.read(2).decode('ascii').strip()
    day = s.read(2).decode('ascii').strip()
    hour = s.read(2).decode('ascii').strip()
    minute = s.read(2).decode('ascii').strip()
    second = s.read(2).decode('ascii').strip()
    xml_feedback_data_info['upload_time'] = f'{year}-{month}-{day} {hour}:{minute}:{second}'

    year = s.read(4).decode('ascii').strip()
    month = s.read(2).decode('ascii').strip()
    day = s.read(2).decode('ascii').strip()
    hour = s.read(2).decode('ascii').strip()
    minute = s.read(2).decode('ascii').strip()
    second = s.read(2).decode('ascii').strip()
    xml_feedback_data_info['receive_time'] = f'{year}-{month}-{day} {hour}:{minute}:{second}'

    return xml_feedback_data_info


# 顯示讀卡機錯誤
def show_ic_card_message(error_code, process_name=None):
    if process_name is None:
        process_name = '健保讀卡機'

    if error_code == 0:
        icon = QMessageBox.Information
        error_message = f'''
            <font size='6'>
                <b>{process_name}作業成功!</b>
            </font>
        '''
        hint = f'恭喜您! 順利的完成{process_name}作業!'
    else:
        icon = QMessageBox.Critical
        message = ERROR_MESSAGE[error_code][0]
        hint = ERROR_MESSAGE[error_code][1]
        if hint is None:
            hint = ''

        error_message = f'''
            <font size='5' color='red'>
              <b>{process_name}作業失敗, 原因如下:</b><br><br>
            </font>
            <font size='5' color='black'>
              <b>
                錯誤代碼: {error_code}<br>
                錯誤訊息: {message}
              </b>
            </font>
        '''

    msg_box = QMessageBox()
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(process_name)
    msg_box.setText(error_message)
    msg_box.setInformativeText(hint)
    msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
    msg_box.exec_()


def need_write_ic_card(database, system_settings, case_key, write_position):
    if case_key in [None, '']:
        return False

    sql = f'''
        SELECT InsType, Card, XCard FROM cases
        WHERE
            CaseKey = {case_key}
    '''
    rows = database.select_record(sql)

    if len(rows) <= 0:
        return False

    row = rows[0]
    ins_type = string_utils.xstr(row['InsType'])
    card = string_utils.xstr(row['Card'])
    xcard = string_utils.xstr(row['XCard'])

    if ((ins_type == '健保') and
            (system_settings.field('產生醫令簽章位置') == write_position) and
            (system_settings.field('使用讀卡機') == 'Y') and
            (card not in nhi_utils.ABNORMAL_CARD) and
            (xcard not in nhi_utils.ABNORMAL_CARD) and
            (card != '欠卡')):
        return True

    return False


def get_host_name(database, hosp_id):
    sql = f'''
        SELECT * FROM hospid
        WHERE
            HospID = "{hosp_id}"
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return hosp_id

    return string_utils.xstr(rows[0]['HospName'])


def get_treatments_html(database, treatment_data):
    treatments = treatment_data['treatments']
    if len(treatments) <= 0:
        return '<br><br><br><center>無健保卡就醫資料</center>'

    records = ''
    for row_no, treatment in zip(range(1, len(treatments)+1), treatments):
        treat_item = string_utils.xstr(treatment['treat_item']).strip()
        treat_date_time = string_utils.xstr(treatment['treat_date_time']).strip()
        treat_after_check = string_utils.xstr(treatment['treat_after_check']).strip()
        card = string_utils.xstr(treatment['card']).strip()
        treat_hosp_code = string_utils.xstr(treatment['treat_hosp_code']).strip()

        try:
            treat_item = nhi_utils.TREAT_ITEM[treat_item]
        except KeyError:
            pass

        try:
            treat_date_time = date_utils.nhi_datetime_to_west_datetime(treat_date_time)
        except ValueError:
            treat_date_time = ''

        if treat_after_check == '1':
            treat_after_check = '正常'
        else:
            treat_after_check = '補卡'

        card = card.zfill(4)
        hosp_name = get_host_name(database, treat_hosp_code)

        records += f'''
            <tr>
                <td align="center">{row_no}</td>
                <td align="center">{treat_item}</td>
                <td>{treat_date_time}</td>
                <td align="center">{treat_after_check}</td>
                <td align="center">{card}</td>
                <td>{hosp_name}</td>
            </tr>
        '''

    html = f'''
        <table align=center cellpadding="2" cellspacing="0" width="98%"
         style="border-width: 1px; border-style: solid;">
            <thead>
                <tr bgcolor="LightGray">
                    <th style="text-align: center; padding-left: 8px" width="5%">序</th>
                    <th style="padding-left: 8px" width="15%" align="center">類別</th>
                    <th style="padding-right: 8px" align="center" width="25%">就醫日期</th>
                    <th style="padding-left: 8px" align="center" width="10%">讀卡</th>
                    <th style="padding-left: 8px" align="center" width="10%">卡序</th>
                    <th style="padding-left: 8px" align="center" width="35%">就醫院所</th>
                </tr>
            </thead>
            <tbody>
                {records}
            </tbody>
        </table>
    '''

    return html


# 取得健保卡內容
def decode_cshis6_basic_data(json):
    basic_data_info = BASIC_DATA
    basic_data_info['card_no'] = json['cardSn']
    basic_data_info['name'] = json['name']
    basic_data_info['patient_id'] = json['idCardNum']

    try:
        basic_data_info['birthday'] = json['birthday']
        basic_data_info['birthday'] = date_utils.nhi_date_to_west_date(json['birthday'])
    except Exception:
        basic_data_info['birthday'] = None

    basic_data_info['gender'] = patient_utils.get_gender(json['sex'])

    try:
        basic_data_info['card_date'] = date_utils.nhi_date_to_west_date(json['dateIssue'])
    except Exception:
        basic_data_info['card_date'] = None

    basic_data_info['cancel_mark'] = get_cancel_mark(json['cancelTermination'])

    return basic_data_info


# 取得健保卡內容
def decode_cshis6_register_basic_data(json):
    basic_data_info = BASIC_DATA
    basic_data_info['card_no'] = json['cardSn']
    basic_data_info['name'] = json['name']
    basic_data_info['patient_id'] = json['idCardNum']

    try:
        basic_data_info['birthday'] = json['birthday']
        basic_data_info['birthday'] = date_utils.nhi_date_to_west_date(json['birthday'])
    except Exception:
        basic_data_info['birthday'] = None

    basic_data_info['gender'] = patient_utils.get_gender(json['sex'])

    try:
        basic_data_info['card_date'] = date_utils.nhi_date_to_west_date(json['dateIssue'])
    except Exception:
        basic_data_info['card_date'] = None

    basic_data_info['cancel_mark'] = get_cancel_mark(json['cancelTermination'])
    basic_data_info['insured_code'] = json['insurerCode']
    basic_data_info['insured_mark'] = get_insured_mark(json['insurerId'])
    basic_data_info['card_valid_date'] = date_utils.nhi_date_to_west_date(json['cardValidity'])
    basic_data_info['card_available_count'] = json['treatmentCounter']
    try:
        basic_data_info['new_born_date'] = date_utils.nhi_date_to_west_date(json['newbornBirthday'])
    except Exception:
        basic_data_info['new_born_date'] = None

    basic_data_info['new_born_mark'] = json['newbornBaby']

    return basic_data_info


def decode_cshis6_treatment_data(json):
    treatment_data = TREATMENT_DATA
    treatment_data['critical_illness'].clear()
    treatment_data['treatments'].clear()

    for illness in json['criticalIllnesses']:
        treatment_data['critical_illness'].append({
            'ci_validity_start': illness['validityStart'],
            'ci_validity_end': illness['validityEnd']
        })

    for treatment in json['treatments']:
        item = {}
        item['treat_item'] = treatment['treatmentItem']
        item['treat_newborn'] = None
        item['treat_date_time'] = treatment['treatDateTime']
        item['treat_after_check'] = treatment['afterCheck']
        item['card'] = treatment['hospitalVisit']
        item['treat_hosp_code'] = treatment['hospitalId']
        item['treat_ot_tot_fee'] = treatment['outpatientFee']
        item['hc_treat_ot_co_fee'] = treatment['costFee']
        item['treat_ot_inpa_fee'] = treatment['inpatientFee']
        item['treat_ot_inpa_30'] = treatment['inpatient30Fee']
        item['treat_ot_inpa_180'] = treatment['inpatient180Fee']

        treatment_data['treatments'].append(item)

    return treatment_data


def decode_cshis6_treat_data(json):
    treat_data_info = TREAT_DATA
    treat_data_info['registered_date'] = date_utils.nhi_datetime_to_west_datetime(json['treatmentDateTime'])
    try:
        treat_data_info['seq_number'] = json['sequenceNumber'].strip()
    except Exception:
        treat_data_info['seq_number'] = ''

    treat_data_info['clinic_id'] = json['hospitalId']
    signature = json['signature']
    # padding_needed = 4 -len(signature) % 4
    # if padding_needed:
    #     signature += '=' * padding_needed

    # decoded_bytes = base64.b64decode(signature)
    # signature = decoded_bytes.decode('utf-8')

    treat_data_info['security_signature'] = signature
    treat_data_info['sam_id'] = json['samId']
    if json['isSameDay']:
        treat_data_info['register_duplicated'] = 'Y'
    else:
        treat_data_info['register_duplicated'] = ''

    treat_data_info['identification'] = json['treatmentNumber']

    return treat_data_info


def decode_cshis6_no_ic_card_treat_data(json):
    treat_data_info = TREAT_DATA

    treat_data_info['registered_date'] = date_utils.nhi_datetime_to_west_datetime(json['treatmentDateTime'])
    treat_data_info['seq_number'] = ''
    treat_data_info['clinic_id'] = json['hospitalId']
    treat_data_info['security_signature'] = ''
    treat_data_info['sam_id'] = ''
    treat_data_info['register_duplicated'] = ''
    treat_data_info['identification'] = json['treatmentNumber']

    return treat_data_info


def decode_cshis6_disease_data(json):
    disease_data = DISEASE_DATA
    disease_data['critical_illness'].clear()
    disease_data['diseases'].clear()

    for illness in json['criticalIllnesses']:
        disease_data['critical_illness'].append({
            'ci_special_code': illness['ciCode'],
            'ci_validity_start': illness['validityStart'],
            'ci_validity_end': illness['validityEnd']
        })

    for treatment in json['treatments']:
        item = {}
        item['case_date'] = treatment['treatDateTime']
        item['disease1'] = treatment['mainCode']
        item['disease2'] = treatment['subCode1']
        item['disease3'] = treatment['subCode2']
        item['disease4'] = treatment['subCode3']

        disease_data['diseases'].append(item)

    return disease_data


def set_identification(parent, database, system_settings, case_key):
    patient_key = patient_utils.get_patient_key(database, case_key)
    patient_id = patient_utils.get_patient_id(database, patient_key)

    try:
        ic_card = class_utils.get_cshis(parent, database, system_settings)
        ic_card_ok = ic_card.write_ic_card_abnormal(patient_id)
        if ic_card_ok is None:
            return
    except Exception:
        print('error')
        return None

    security = case_utils.treat_data_to_xml(ic_card.treat_data)

    upload_type = '2'        # 上傳格式 2: 異常卡序
    security = case_utils.update_xml_doc(
        security, 'upload_type', upload_type)

    treat_after_check = '1'  # 補卡註記 1:非欠卡        
    security = case_utils.update_xml_doc(
        security, 'treat_after_check', treat_after_check)
    security = security.decode('utf-8')        


    sql = f"""
        UPDATE cases
        SET
            Security = '{security}'
        WHERE
            CaseKey = {case_key}
    """
    database.exec_sql(sql)

