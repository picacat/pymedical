
# 52. 值班表(藥師/支援醫師)	100.07.01
CREATE TABLE IF NOT EXISTS Schedule
(
    ScheduleKey INT AUTO_INCREMENT NOT NULL,  # 藥師班表序號
    Type		    VARCHAR(10),	# 類別: 藥師, 支援醫師
    ScheduleDate	Date,

    Name1		    VARCHAR(10), 	# 藥師, 支援醫師 早班
    Name2		    VARCHAR(10), 	# 藥師, 支援醫師 午班
    Name3		    VARCHAR(10), 	# 藥師, 支援醫師 晚班

    Remark	    VARCHAR(100), # 備註

    TimeStamp	  TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(ScheduleKey),
    INDEX(Type, ScheduleDate)
) CHARACTER SET utf8;


