CREATE TABLE patient_assessment (
    AssessmentKey   INT AUTO_INCREMENT PRIMARY KEY,
    PatientKey      INT NOT NULL,
    AssessmentType  VARCHAR(20) NOT NULL DEFAULT 'FB',
    FormVersion     VARCHAR(10) NOT NULL DEFAULT '1.0',
    Doctor          VARCHAR(10),        -- d007 醫事人員身分證號
    CaseType        VARCHAR(1),         -- d008 個案類別
    CaseDate        DATE,               -- d009 收案日期
    VisitDate       DATE,               -- c003 就醫日期
    CloseDate       DATE,               -- c004 結案日期
    CloseReason     VARCHAR(1),         -- c005 結案原因 1/2/3/X
    Content         TEXT,               -- h001~h043 JSON，之後再做
    UploadDate      DATE,               -- 已上傳批次年月，NULL=未上傳
    TimeStamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_patient (PatientKey, CaseDate)
);
