
# 52. 醫師班表, 醫護班表 共用   100.07.01

# 醫師班表- 提供掛號醫師名單 (敏盛, 童綜掛號收據列印用)
# 醫護班表- 提供健保申報用. InsGenerate

CREATE TABLE IF NOT EXISTS SchedDoctor
(
    SchedDoctorKey   INT AUTO_INCREMENT NOT NULL,  # 醫師班表序號
    Type		    VARCHAR(10),  # 類別: 醫師, 理療師, 醫師護士, 醫師調劑(99.03.08)
    Room		    INT,		      # 診別: 醫師:01-10, 理療師:11-20

    Sunday1	    VARCHAR(10),	# 星期日 早班 姓名  Redefine 資料月份 YYYY/MM (西元)
    Sunday2	    VARCHAR(10),	# 星期日 午班 姓名
    Sunday3	    VARCHAR(10),	# 星期日 晚班 姓名

    Monday1	    VARCHAR(10),	# 星期一 早班 姓名  Redefine 醫護: 醫師姓名
    Monday2	    VARCHAR(10),	# 星期一 午班 姓名           護士姓名
    Monday3	    VARCHAR(10),	# 星期一 晚班 姓名

    Tuesday1	  VARCHAR(10),	# 星期二 早班 姓名  Redefine 開始日期 YYYY/MM/DD (西元)
    Tuesday2	  VARCHAR(10),	# 星期二 午班 姓名           結束日期 YYYY/MM/DD (西元)
    Tuesday3	  VARCHAR(10),	# 星期二 晚班 姓名           班別: 早班, 午班, 晚班 17.04.25

    Wednesday1	VARCHAR(10),	# 星期三 早班 姓名
    Wednesday2	VARCHAR(10),	# 星期三 午班 姓名
    Wednesday3	VARCHAR(10),	# 星期三 晚班 姓名

    Thursday1	VARCHAR(10),	  # 星期四 早班 姓名
    Thursday2	VARCHAR(10),	  # 星期四 午班 姓名
    Thursday3	VARCHAR(10),	  # 星期四 晚班 姓名

    Friday1	    VARCHAR(10),  # 星期五 早班 姓名
    Friday2	    VARCHAR(10),  # 星期五 午班 姓名
    Friday3	    VARCHAR(10),  # 星期五 晚班 姓名

    Saturday1	VARCHAR(10),	  # 星期六 早班 姓名
    Saturday2	VARCHAR(10),	  # 星期六 午班 姓名
    Saturday3	VARCHAR(10),	  # 星期六 晚班 姓名

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(SchedDoctorKey),
    INDEX(Room)
) CHARACTER SET utf8;

# 診別 班別  星期日   星期一   星期二   星期三   星期四   星期五   星期六
# 01診 早班  張先生   歐陽先生 張先生12 張先生12 張先生12 歐陽先生 歐先生
#      午班
#      晚班
# 02診 早班  張先生12 歐陽先生 張先生   張先生   張先生   歐陽先生 歐先生
#      午班
#      晚班
# 03診 早班  張先生   歐陽先生 張先生   張先生   張先生   歐陽先生 歐先生
#      午班
#      晚班

