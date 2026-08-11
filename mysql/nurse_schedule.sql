-- ------------------------------------------------------------
-- 資料表 nurse_schedule
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:32
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `nurse_schedule` (
  `NurseScheduleKey` int(11) NOT NULL AUTO_INCREMENT,
  `ScheduleDate` date DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `Nurse1` varchar(10) DEFAULT NULL,
  `Nurse2` varchar(10) DEFAULT NULL,
  `Nurse3` varchar(10) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`NurseScheduleKey`),
  KEY `ScheduleDate` (`ScheduleDate`,`Doctor`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
