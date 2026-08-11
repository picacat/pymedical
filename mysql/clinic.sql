-- ------------------------------------------------------------
-- 資料表 clinic
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:25
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `clinic` (
  `ClinicKey` int(11) NOT NULL AUTO_INCREMENT,
  `ClinicType` varchar(4) DEFAULT NULL,
  `ClinicCode` varchar(5) DEFAULT NULL,
  `InputCode` varchar(10) DEFAULT NULL,
  `ClinicName` varchar(200) DEFAULT NULL,
  `HitRate` int(11) DEFAULT 0,
  `Position` varchar(40) DEFAULT NULL,
  `Groups` varchar(40) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ClinicKey`),
  KEY `ClinicCode` (`ClinicCode`,`InputCode`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
