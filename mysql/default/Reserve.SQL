
# 06. 預約檔	100.07.01

CREATE TABLE IF NOT EXISTS Reserve
(
    ReserveKey	INT AUTO_INCREMENT NOT NULL,  # 預約序號

    PatientKey	INT NOT NULL,	# 系統號 (基本資料)     (初診 999999)
    Name		    VARCHAR(10),	# 病患姓名
  
    ReserveDate	DATETIME,	    # 預約日期: 定時間:報到時間, 未定:實際報到
    Period	    VARCHAR(04),	# 預約班別: 早班, 午班, 晚班
    Room		    INT,		      # 預約診別: 1-10
    ReserveNo	  INT,		      # 預約診號  (含增加號); 報到時 => RegistNo
    Doctor      VARCHAR(10),	# 醫師姓名
    Arrival	    ENUM("False", "True") NOT NULL,     # 原 Regist
		                          # 報到 (掛號為準): 1-報到 0-未報到 (若 日期已過, 則爽約)
    PatInitial  VARCHAR(200), # 樓中亮: 初診預約, 避免佔號
                              # 4      1-初診
                              #10      5-ID身分證
                              # 4     15-性別
                              # 8     19-生日YYYYMMDD (西元)
                              #10     27-病歷號
                              #10     37-保險
                              #10     47-優待
                              #15     57-電話
                              #15     72-行動電話
                              #50     87-地址

    Remark	    VARCHAR(100), # 備註

    TimeStamp	  TIMESTAMP,	  # 上次異動日期 / 登錄日期

    PRIMARY KEY(ReserveKey),
    INDEX(PatientKey, ReserveDate)
) CHARACTER SET utf8;

# Rules:
# 1. 預約診號
#    一天前預約 	     :	預約當天最大診號 + 01
#    門診當天 (早上預約下午) :	if 當天診號 (病歷檔) > 00
#				   當天診號 + 01
#				else  (可能還未掛號)
#				   預約當天最大診號 + 01
#				end if

# 2. 預約報到
#    - 診號照舊
#    - 候診名單顯示:  報到者時間 + 診號 ( 可能時間相同)
#    - 報到者時間     if 名單 < 03
#			 報到者時間直接排入
#		      else (名單 >= 03)
#			 if 候診第 3名 就診類別 非預約 (現場掛號)
#			    報到者時間 = 候診第 3名掛號時間 - 1秒
#			 else (候診第 3名:就診類別:預約)
#			    if 候診第 3名診號 < 報到者
#			       報到者時間 =  候診第 3 名掛號時間 + 1秒
#			    else
#			       報到者時間 =  候診第 3 名掛號時間 - 1秒
#			    end if
#			 end if
#		      end if
# 3. Functions: 登錄, 報到, 查詢, 爽約, 修正, 刪除, 離開
#		查詢 : 時間, 類別 ( 未到, 已到, 全部)

