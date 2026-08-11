-- ------------------------------------------------------------
-- 資料表 certificate
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:24
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `certificate` (
  `CertificateKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL,
  `PatientKey` int(11) NOT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Doctor` varchar(20) DEFAULT NULL,
  `CertificateDate` date DEFAULT NULL,
  `CertificateType` varchar(10) DEFAULT NULL,
  `InsType` varchar(10) DEFAULT NULL,
  `TreatType` varchar(20) DEFAULT NULL,
  `StartDate` date DEFAULT NULL,
  `EndDate` date DEFAULT NULL,
  `Diagnosis` mediumtext DEFAULT NULL,
  `DoctorComment` mediumtext DEFAULT NULL,
  `CertificateFee` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`CertificateKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`,`CertificateDate`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
