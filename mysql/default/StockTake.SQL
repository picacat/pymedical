
# 27-藥局盤點檔 	92/05/09

CREATE TABLE IF NOT EXISTS StockTake
(
  StockTakeKey	INT AUTO_INCREMENT NOT NULL,  # 盤點序號
  StockTakeDate Date,           # 盤點日期
  Sequence      VARCHAR(10),    # 盤點單號
  StockTaker    VARCHAR(10),    # 盤點人

  MedicineKey	INT,		    # 詞庫處方序號, 處方詞庫檔內之各藥品
  MedicineType	VARCHAR(04),	# 類別: 單方,複方,水藥,外用,高貴,穴道,處置,
				        		#	器材,成方
  MedicineName	VARCHAR(40),	# 處方名稱
  Quantity	    Double(10, 2),	# 藥品用量
  Unit		    VARCHAR(10),	# 單位
  AdjustDate    Date,           # 調整至藥局

  Remark        VARCHAR(100),	# 備註

  TimeStamp	    TIMESTAMP,	# 上次異動日期

  PRIMARY KEY(StockTakeKey),
  INDEX(StockTakeDate, Sequence, MedicineKey)
);

