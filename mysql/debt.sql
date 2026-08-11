-- ------------------------------------------------------------
-- 資料表 debt
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:26
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `debt` (
  `DebtKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL DEFAULT 0,
  `PrescriptKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) NOT NULL DEFAULT 0,
  `DebtType` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `CaseDate` datetime DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `Fee` int(11) DEFAULT NULL,
  `PaymentType` varchar(20) DEFAULT '現金',
  `ReturnDate1` datetime DEFAULT NULL,
  `Period1` varchar(4) DEFAULT NULL,
  `Casher1` varchar(10) DEFAULT NULL,
  `Cashier1` varchar(10) DEFAULT NULL,
  `Fee1` int(11) DEFAULT NULL,
  `ReturnDate2` datetime DEFAULT NULL,
  `Period2` varchar(4) DEFAULT NULL,
  `Casher2` varchar(10) DEFAULT NULL,
  `Cashier2` varchar(10) DEFAULT NULL,
  `Fee2` int(11) DEFAULT NULL,
  `ReturnDate3` datetime DEFAULT NULL,
  `Period3` varchar(4) DEFAULT NULL,
  `Casher3` varchar(10) DEFAULT NULL,
  `Cashier3` varchar(10) DEFAULT NULL,
  `Fee3` int(11) DEFAULT NULL,
  `TotalReturn` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`DebtKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`,`CaseDate`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
