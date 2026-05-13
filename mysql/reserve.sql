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
-- Table structure for table `reserve`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
  `PatInitial` varchar(200) DEFAULT NULL,
  `Source` varchar(10) DEFAULT NULL,
  `Registrar` varchar(10) DEFAULT NULL,
  `Regist` enum('False','True') NOT NULL DEFAULT 'False',
  `Remark` mediumtext DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ReserveKey`),
  KEY `PatientKey` (`PatientKey`,`ReserveDate`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
