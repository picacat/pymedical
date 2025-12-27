
# 33- 病名詞庫類別檔 	104.01.01 for Disease10.sql

CREATE TABLE IF NOT EXISTS Disease10Groups
(
    GroupsKey	  INT AUTO_INCREMENT NOT NULL,	# 詞庫類別序號

    GroupsType	VARCHAR(20),	# 分類: 病名
    GroupsName	VARCHAR(40),	# 名稱: 頭部, 腦血管 ... Pointer to Disease.Symptom

    TimeStamp	  TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(GroupsKey),
    INDEX(GroupsType)
) CHARACTER SET utf8;


