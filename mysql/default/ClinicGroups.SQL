
# 32. 詞庫類別檔 	100.07.01   for clinic.sql

CREATE TABLE IF NOT EXISTS ClinicGroups       # 原 Groups
(
  GroupsKey	  INT AUTO_INCREMENT NOT NULL,	# 詞庫類別序號
  GroupsType	VARCHAR(20),	# 分類: 主訴: 內科, 傷科, 婦科,
                                #       辨證: 內辨, 傷辨
                                #       治則: 內治, 傷治
  GroupsName	VARCHAR(40),	# 名稱

  TimeStamp	TIMESTAMP,	        # 上次異動日期

  PRIMARY KEY(GroupsKey),
  INDEX(GroupsType)
) CHARACTER SET utf8;


