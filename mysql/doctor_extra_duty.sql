-- ------------------------------------------------------------
-- 資料表 doctor_extra_duty
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:27
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `doctor_extra_duty` (
  `DoctorExtraDutyKey` int(11) NOT NULL AUTO_INCREMENT,
  `ExtraDutyDate` date DEFAULT NULL,
  `Period` varchar(20) DEFAULT NULL,
  `DoctorName` varchar(20) DEFAULT NULL,
  `TimeStamp` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`DoctorExtraDutyKey`),
  KEY `ExtraDutyDate` (`ExtraDutyDate`,`Period`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
