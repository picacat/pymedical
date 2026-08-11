-- ------------------------------------------------------------
-- 資料表 insappeal
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:30
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `insappeal` (
  `InsAppealKey` int(11) NOT NULL AUTO_INCREMENT,
  `InsApplyKey` int(11) NOT NULL,
  `ClinicID` varchar(10) DEFAULT NULL,
  `ApplyDate` varchar(5) DEFAULT NULL,
  `ApplyPeriod` varchar(6) DEFAULT NULL,
  `ApplyType` varchar(1) DEFAULT NULL,
  `CaseType` varchar(2) DEFAULT NULL,
  `Sequence` int(11) DEFAULT NULL,
  `Sample` varchar(10) DEFAULT NULL,
  `Reject` varchar(10) DEFAULT NULL,
  `Point1` int(11) DEFAULT NULL,
  `Point2` int(11) DEFAULT NULL,
  `Point3` int(11) DEFAULT NULL,
  `Note` varchar(1) DEFAULT NULL,
  `Message` varchar(40) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`InsAppealKey`),
  KEY `ApplyDate` (`ApplyDate`,`CaseType`,`Sequence`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
