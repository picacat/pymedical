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
-- Table structure for table `person`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
) ENGINE=MyISAM  DEFAULT CHARSET=big5 COLLATE=big5_chinese_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
