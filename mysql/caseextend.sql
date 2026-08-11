-- ------------------------------------------------------------
-- 資料表 caseextend
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:24
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `caseextend` (
  `CaseExtendKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) DEFAULT NULL,
  `ExtendType` varchar(10) DEFAULT NULL,
  `Content` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`CaseExtendKey`),
  KEY `CaseKey` (`CaseKey`,`ExtendType`),
  KEY `idx_case_type` (`CaseKey`,`ExtendType`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
