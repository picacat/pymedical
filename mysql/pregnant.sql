-- ------------------------------------------------------------
-- 資料表 pregnant
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:34
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `pregnant` (
  `PregnantKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `LowTemperature` varchar(10) DEFAULT NULL,
  `HighTemperature` varchar(10) DEFAULT NULL,
  `FollTemperature` decimal(10,2) DEFAULT NULL,
  `FollDays` int(11) DEFAULT NULL,
  `OvulateDate` date DEFAULT NULL,
  `OvulateTemperature` decimal(10,2) DEFAULT NULL,
  `LuteumTemperature` decimal(10,2) DEFAULT NULL,
  `LuteumDays` int(11) DEFAULT NULL,
  `Sperm` int(11) DEFAULT NULL,
  `Yield` varchar(10) DEFAULT NULL,
  `Liquefaction` varchar(10) DEFAULT NULL,
  `Impurity` varchar(10) DEFAULT NULL,
  `Activity` varchar(10) DEFAULT NULL,
  `Spouse` varchar(10) DEFAULT NULL,
  `HeartBeat` int(11) DEFAULT NULL,
  `BPLow` int(11) DEFAULT NULL,
  `BPHigh` int(11) DEFAULT NULL,
  `Vomit` int(11) DEFAULT NULL,
  `Bleed` int(11) DEFAULT NULL,
  `SymptomLine` varchar(20) DEFAULT NULL,
  `PhysiqueLine` varchar(20) DEFAULT NULL,
  `AnxietyGrade` int(11) DEFAULT NULL,
  `AnxietyLine` varchar(20) DEFAULT NULL,
  `Fertilization` varchar(4) DEFAULT NULL,
  `WesternCure` varchar(4) DEFAULT NULL,
  `InitDATE` date DEFAULT NULL,
  `DiseaseName` varchar(40) DEFAULT NULL,
  `BirthFoetus` int(11) DEFAULT NULL,
  `StillFoetus` int(11) DEFAULT NULL,
  `Foetus` int(11) DEFAULT NULL,
  `Remark` longtext DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PregnantKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
