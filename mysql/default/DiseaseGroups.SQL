
# 33. 病名詞庫類別檔 	94/12/29  for Disease.sql

CREATE TABLE IF NOT EXISTS DiseaseGroups      # 原 GroupDisease
(
    GroupsKey	  INT AUTO_INCREMENT NOT NULL,	# 詞庫類別序號

    GroupsType	VARCHAR(20),	# 分類: 病名, ICD10 (105.01.08 Customized)
    GroupsName	VARCHAR(40),	# 名稱
                              # ICD10 類別(Single level) (105.01.08 Customized)

    TimeStamp	  TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(GroupsKey),
    INDEX(GroupsType)
) CHARACTER SET utf8;


