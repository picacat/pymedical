
# 09. 退貨檔 2024-04-27 同安

CREATE TABLE IF NOT EXISTS ReturnGoods
(
    ReturnGoodsKey      INT AUTO_INCREMENT NOT NULL,    # 退貨鍵
    ReturnGoodsDate	    DATETIME,	                    # 退貨日期
    Period 	            VARCHAR(04),	                # 欠款班別: 早班, 午班, 晚班
    ItemName	        VARCHAR(200),	                # 退貨品項名稱
    Quantity		    DECIMAL(10, 2),		            # 退貨數量
    Amount		        Int,		                    # 退貨金額
    ReturnGoodsReason	VARCHAR(200),	                # 退貨原因
    Cashier	            VARCHAR(200),	                # 經手人
    TimeStamp	        TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ReturnGoodsKey),
    INDEX(ReturnGoodsDate, Period)
) CHARACTER SET utf8;


