
# 06-1. 預約班表檔	101.06.25

CREATE TABLE IF NOT EXISTS ResSchedule
(
    ResScheduleKey	INT AUTO_INCREMENT NOT NULL,  # 預約班表序號
    Room		    INT,		      # 預約診別: 1-10
    Period	    VARCHAR(04),	# 預約班別: 早班, 午班, 晚班

    Sequence    INT,          # 預約序號 (位置) 1-100
    ReserveTime	VARCHAR(05),	# 時間: HH:MM  (24 時制)
    ReserveNo	  INT,		      # 預約診號

    Remark	    VARCHAR(100), # 備註

    TimeStamp	  TIMESTAMP,	  # 上次異動日期 / 登錄日期

    PRIMARY KEY(ResScheduleKey),
    INDEX(Sequence, ReserveTime, ReserveNo)
) CHARACTER SET utf8;


