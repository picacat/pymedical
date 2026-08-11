-- ------------------------------------------------------------
-- 資料表 reserve
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:36
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `reserve` (
  `ReserveKey` int(11) NOT NULL AUTO_INCREMENT,
  `PatientKey` int(11) NOT NULL DEFAULT 0,
  `Name` varchar(100) DEFAULT NULL,
  `ReserveDate` datetime DEFAULT NULL,
  `CreateTime` datetime DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Room` int(11) DEFAULT NULL,
  `Sequence` int(11) DEFAULT NULL,
  `ReserveNo` int(11) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `Arrival` enum('False','True') NOT NULL,
  `Frozen` tinyint(1) NOT NULL DEFAULT 0,
  `PatInitial` varchar(200) DEFAULT NULL,
  `Source` varchar(10) DEFAULT NULL,
  `Registrar` varchar(10) DEFAULT NULL,
  `Regist` enum('False','True') NOT NULL DEFAULT 'False',
  `Remark` longtext DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ReserveKey`),
  KEY `PatientKey` (`PatientKey`,`ReserveDate`),
  KEY `idx_reserve_date` (`ReserveDate`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
