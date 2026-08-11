-- ------------------------------------------------------------
-- 資料表 patient
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:32
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `patient` (
  `PatientKey` int(11) NOT NULL AUTO_INCREMENT,
  `CardNo` varchar(12) DEFAULT NULL,
  `ChartNo` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Era` char(1) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `ID` varchar(10) DEFAULT NULL,
  `Nationality` varchar(4) DEFAULT NULL,
  `Gender` varchar(4) DEFAULT NULL,
  `BloodType` varchar(10) DEFAULT NULL,
  `Sex` varchar(4) DEFAULT NULL,
  `Telephone` varchar(15) DEFAULT NULL,
  `Officephone` varchar(15) DEFAULT NULL,
  `Cellphone` varchar(15) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  `ZipCode` varchar(5) DEFAULT NULL,
  `Address` varchar(50) DEFAULT NULL,
  `Marriage` varchar(10) DEFAULT NULL,
  `Education` varchar(10) DEFAULT NULL,
  `Occupation` varchar(10) DEFAULT NULL,
  `DiscountType` varchar(20) DEFAULT NULL,
  `DiscountReason` varchar(40) DEFAULT NULL,
  `InsType` varchar(10) DEFAULT NULL,
  `PrivateInsurance` varchar(10) DEFAULT NULL,
  `FamilyPatientKey` varchar(10) DEFAULT NULL,
  `EmergencyContact` varchar(20) DEFAULT NULL,
  `EmergencyContactPhone` varchar(40) DEFAULT NULL,
  `EmergencyRelevant` varchar(100) DEFAULT NULL,
  `Reference` varchar(10) DEFAULT NULL,
  `Trace` char(2) DEFAULT NULL,
  `TraceTime` varchar(4) DEFAULT NULL,
  `TraceType` varchar(10) DEFAULT NULL,
  `InitDate` datetime DEFAULT NULL,
  `LastDate` datetime DEFAULT NULL,
  `Alergy` longtext DEFAULT NULL,
  `Allergy` longtext DEFAULT NULL,
  `NursingHome` varchar(50) DEFAULT NULL,
  `NursingHomeID` varchar(20) DEFAULT NULL,
  `NursingHomeInDate` varchar(10) DEFAULT NULL,
  `History` longtext DEFAULT NULL,
  `Description` longtext DEFAULT NULL,
  `Remark` longtext DEFAULT NULL,
  `Note` char(1) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PatientKey`),
  KEY `Birthday` (`Birthday`),
  KEY `idx_select_optimization` (`Name`,`ID`,`Telephone`,`Cellphone`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
