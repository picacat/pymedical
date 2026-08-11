-- ------------------------------------------------------------
-- 資料表 wait
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:40
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `wait` (
  `WaitKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL DEFAULT 0,
  `CaseDate` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `PatientKey` int(11) NOT NULL DEFAULT 0,
  `RegistrationNo` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Era` char(1) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `Sex` varchar(4) DEFAULT NULL,
  `Visit` varchar(4) DEFAULT NULL,
  `RegistTypex` varchar(10) DEFAULT NULL,
  `RegistType` varchar(10) DEFAULT NULL,
  `TreatType` varchar(100) DEFAULT NULL,
  `Share` varchar(50) DEFAULT NULL,
  `InsType` varchar(4) DEFAULT NULL,
  `Card` varchar(6) DEFAULT NULL,
  `Continuance` int(11) DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Room` int(11) NOT NULL DEFAULT 1,
  `MassageRoom` int(11) DEFAULT NULL,
  `RegistNo` int(11) DEFAULT NULL,
  `MassageNo` int(11) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `InProgress` varchar(10) DEFAULT NULL,
  `Massager` varchar(10) DEFAULT NULL,
  `DoctorDone` enum('False','True') NOT NULL DEFAULT 'False',
  `MassagerDone` enum('False','True') NOT NULL DEFAULT 'False',
  `ChargeDone` enum('False','True') NOT NULL DEFAULT 'False',
  `DrugDone` enum('False','True') NOT NULL DEFAULT 'False',
  `DrugPickupDone` enum('False','True') NOT NULL DEFAULT 'False',
  `Remark` varchar(100) DEFAULT NULL,
  `VHCReqCode` varchar(256) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`WaitKey`),
  KEY `CaseKey` (`CaseKey`,`CaseDate`,`PatientKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
