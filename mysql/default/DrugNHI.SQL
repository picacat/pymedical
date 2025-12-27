
# 35-1. DrugNHI 同健保藥品檔 drug           from 健保局 xls 檔
#   DrugNHI 檔置於友杏網站, 供院所下載
#   Generated from CVTDrugNHI Data NHI file

CREATE TABLE IF NOT EXISTS DrugNHI
(
    DrugNHIKey  INT AUTO_INCREMENT NOT NULL,  # 1.健保藥品序號

    DrugUpdate  VARCHAR(06),  # 更新年月(西元)  YYYYMM  201207

    InsCode	    VARCHAR(12),	# 2.健保碼
    DrugName	  VARCHAR(40),	# 3.藥品名稱

    Unit		    VARCHAR(10),	# 4.單位, 劑型
    InsPrice	  Decimal(10, 2), # 5.健保價
    Supplier	  VARCHAR(20),	# 6.廠商

    ValidDate   Date,         # 7.有效期限; 轉檔後已合理化, 除非空白

    Remark      VARCHAR(50),  # 8.備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(DrugNHIKey),
    INDEX(InsCode)
) CHARACTER SET utf8;


