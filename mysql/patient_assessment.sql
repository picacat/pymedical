-- ------------------------------------------------------------
-- 資料表 patient_assessment
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:33
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `patient_assessment` (
  `AssessmentKey` int(11) NOT NULL AUTO_INCREMENT,
  `PatientKey` int(11) NOT NULL,
  `AssessmentType` varchar(20) NOT NULL DEFAULT 'FB',
  `FormVersion` varchar(10) NOT NULL DEFAULT '1.0',
  `Doctor` varchar(10) DEFAULT NULL,
  `CaseType` varchar(1) DEFAULT NULL,
  `CaseDate` date DEFAULT NULL,
  `VisitDate` date DEFAULT NULL,
  `CloseDate` date DEFAULT NULL,
  `CloseReason` varchar(1) DEFAULT NULL,
  `Content` text DEFAULT NULL,
  `UploadDate` date DEFAULT NULL,
  `UploadFileName` varchar(30) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`AssessmentKey`),
  KEY `idx_patient` (`PatientKey`,`CaseDate`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
