
# 41. 庫存進銷貨主檔    100.07.01

CREATE TABLE IF NOT EXISTS Stock
(
    StockKey	INT AUTO_INCREMENT NOT NULL,  # 庫存序號
    TransDate   Date,           # 進銷貨日期;  銷貨-門診日期 CaseDate;  盤點日期
    Sequence    VARCHAR(10),    # 進銷貨單號;  銷貨-CaseKey;            盤點單號

    StockType	VARCHAR(10),	# 類別: 進貨, 銷貨(病歷), 出貨(買賣), 盤點
    Amount      Int,            # 總價 (進貨單)

    Supplier    VARCHAR(50),    # 出貨廠商;    銷貨-醫師;     盤點人
    AdjustDate  Date,           # 過檔日期 - 調整至 Medicine; Null = 未過檔

    Remark      VARCHAR(100),   # 備註;     銷貨無備註;    盤點備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(StockKey),
    INDEX(TransDate, Sequence)
) CHARACTER SET utf8;

