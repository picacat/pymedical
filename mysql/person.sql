-- ------------------------------------------------------------
-- 資料表 person
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:34
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `person` (
  `PersonKey` int(11) NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `Code` varchar(5) DEFAULT NULL,
  `Title` varchar(20) DEFAULT NULL,
  `Position` varchar(10) DEFAULT NULL,
  `Room` int(11) DEFAULT NULL,
  `FullTime` varchar(10) DEFAULT NULL,
  `ID` varchar(10) DEFAULT NULL,
  `Gender` varchar(2) DEFAULT NULL,
  `Telephone` varchar(15) DEFAULT NULL,
  `Cellphone` varchar(15) DEFAULT NULL,
  `Address` varchar(50) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  `Department` varchar(20) DEFAULT NULL,
  `InputDate` date DEFAULT NULL,
  `Password` varchar(6) DEFAULT NULL,
  `Priority` int(11) DEFAULT NULL,
  `IME` varchar(6) DEFAULT NULL,
  `HISDocPK` varchar(20) DEFAULT NULL,
  `Certificate` varchar(50) DEFAULT NULL,
  `CertCardNo` varchar(50) DEFAULT NULL,
  `InitDate` date DEFAULT NULL,
  `QuitDate` date DEFAULT NULL,
  `Remark` varchar(100) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PersonKey`),
  KEY `Code` (`Code`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
