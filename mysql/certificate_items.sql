-- ------------------------------------------------------------
-- 資料表 certificate_items
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:25
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `certificate_items` (
  `CertificateItemsKey` int(11) NOT NULL AUTO_INCREMENT,
  `CertificateKey` int(11) NOT NULL,
  `CaseKey` int(11) NOT NULL,
  `CaseDate` datetime DEFAULT NULL,
  `InsType` varchar(10) DEFAULT NULL,
  `RegistFee` int(11) DEFAULT NULL,
  `DiagFee` int(11) DEFAULT NULL,
  `InterDrugFee` int(11) DEFAULT NULL,
  `PharmacyFee` int(11) DEFAULT NULL,
  `AcupunctureFee` int(11) DEFAULT NULL,
  `MassageFee` int(11) DEFAULT NULL,
  `DislocateFee` int(11) DEFAULT NULL,
  `ExamFee` int(11) DEFAULT NULL,
  `InsApplyFee` int(11) DEFAULT NULL,
  `SDiagShareFee` int(11) DEFAULT NULL,
  `SDrugShareFee` int(11) DEFAULT NULL,
  `SDiagFee` int(11) DEFAULT NULL,
  `SDrugFee` int(11) DEFAULT NULL,
  `SHerbFee` int(11) DEFAULT NULL,
  `SExpensiveFee` int(11) DEFAULT NULL,
  `SAcupunctureFee` int(11) DEFAULT NULL,
  `SMassageFee` int(11) DEFAULT NULL,
  `SDislocateFee` int(11) DEFAULT NULL,
  `SMaterialFee` int(11) DEFAULT NULL,
  `SExamFee` int(11) DEFAULT NULL,
  `SMiscFee` int(11) DEFAULT NULL,
  `SelfTotalFee` int(11) DEFAULT NULL,
  `DiscountFee` int(11) DEFAULT NULL,
  `TotalFee` int(11) DEFAULT NULL,
  `ReceiptFee` int(11) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`CertificateItemsKey`),
  KEY `CertificateKey` (`CertificateKey`,`CaseKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
