-- ------------------------------------------------------------
-- 資料表 massage_cases
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:30
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `massage_cases` (
  `MassageCaseKey` int(11) NOT NULL AUTO_INCREMENT,
  `MassageCustomerKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `ClinicName` varchar(50) DEFAULT NULL,
  `Name` varchar(20) DEFAULT NULL,
  `CaseDate` datetime NOT NULL,
  `FinishDate` datetime NOT NULL,
  `TreatType` varchar(10) DEFAULT NULL,
  `InsType` varchar(4) DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Massager` varchar(10) DEFAULT NULL,
  `Registrar` varchar(10) DEFAULT NULL,
  `Cashier` varchar(10) DEFAULT NULL,
  `Remark` blob DEFAULT NULL,
  `DesignatedMassager` enum('False','True') NOT NULL,
  `SelfTotalFee` int(11) DEFAULT NULL,
  `DiscountFee` int(11) DEFAULT NULL,
  `TotalFee` int(11) DEFAULT NULL,
  `ReceiptFee` int(11) DEFAULT NULL,
  `DebtFee` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`MassageCaseKey`),
  KEY `MassageCustomerKey` (`MassageCustomerKey`,`CaseDate`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
