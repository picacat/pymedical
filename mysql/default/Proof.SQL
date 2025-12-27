
# 10. 證明文件	100.07.01

CREATE TABLE IF NOT EXISTS Proof
(
    ProofKey	  INT AUTO_INCREMENT NOT NULL,  # 證明序號
    PatientKey	INT NOT NULL,	# 系統號
    Name  	    VARCHAR(10),	# 病患姓名
    ProofDate	  DATE,		      # 開立證明日期

    ProofType	VARCHAR(10),	  # 證明類別: 診斷證明, 收費證明
                              #           收費收據 (98.10.22 翰林 CaseQuery)-僅用開立證明日期 (CasQuery 收費列印日期)

    InsType	    VARCHAR(10),	# 收據(保險)類別: 全部, 健保, 健保負擔(收費證明用), 自費
    StartDate	  DATE,		      # 病歷統計開始日期
    StopDate	  DATE,		      # 病歷統計結束日期

    Disease     BLOB,         # 診斷證明-病名
    Diagnosis   BLOB,         # 診斷證明-囑言

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ProofKey),
    INDEX(PatientKey, ProofDate)
) CHARACTER SET utf8;

# Content:
#    診斷證明 
#	Symptom		VarChar(100)	病名, 主要症狀
#	Instruction 	VarChar(100)	醫師囑言

