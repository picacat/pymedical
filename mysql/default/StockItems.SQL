
# 41. 庫存明細檔    100.07.01

CREATE TABLE IF NOT EXISTS StockItems
(
    StockItemsKey	INT AUTO_INCREMENT NOT NULL,  # 庫存明細序號

    StockKey	    INT,		    # 庫存主檔
    MedicineKey	    INT,		    # 詞庫處方序號, 處方詞庫檔內之各藥品
    MedicineType	VARCHAR(04),	# 類別: 單方, 複方, 水藥, 外用, 高貴, 器材
    MedicineName	VARCHAR(40),	# 處方名稱

    Quantity	    Decimal(10, 2), # 進銷量;   盤點實際量
    Unit		      VARCHAR(10),	# 單位      斤 -> 錢 ?

    Price           Decimal(10, 2), # 單價      盤點用: Medicine庫存量
    Amount          Decimal(10, 2), # 金額      盤點用: 盤點實際量 與 Medicine庫存量 差異量

    Note            VarChar(02),    # 註記
    Remark          VARCHAR(100),	# 備註

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(StockItemsKey),
    INDEX(StockKey, MedicineKey)
) CHARACTER SET utf8;

