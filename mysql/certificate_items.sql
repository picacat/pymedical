-- MariaDB dump 10.19  Distrib 10.11.6-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: pymedical
-- ------------------------------------------------------
-- Server version	10.11.6-MariaDB-0+deb12u1
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `certificate_items`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
) ENGINE=MyISAM  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
