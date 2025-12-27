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
-- Table structure for table `patient`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `patient` (
  `PatientKey` int(11) NOT NULL AUTO_INCREMENT,
  `CardNo` varchar(12) DEFAULT NULL,
  `ChartNo` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Era` char(1) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `ID` varchar(10) DEFAULT NULL,
  `Nationality` varchar(4) DEFAULT NULL,
  `Gender` varchar(4) DEFAULT NULL,
  `BloodType` varchar(10) DEFAULT NULL,
  `Sex` varchar(4) DEFAULT NULL,
  `Telephone` varchar(15) DEFAULT NULL,
  `Officephone` varchar(15) DEFAULT NULL,
  `Cellphone` varchar(15) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  `ZipCode` varchar(5) DEFAULT NULL,
  `Address` varchar(50) DEFAULT NULL,
  `Marriage` varchar(10) DEFAULT NULL,
  `Education` varchar(10) DEFAULT NULL,
  `Occupation` varchar(10) DEFAULT NULL,
  `DiscountType` varchar(20) DEFAULT NULL,
  `DiscountReason` varchar(40) DEFAULT NULL,
  `InsType` varchar(10) DEFAULT NULL,
  `PrivateInsurance` varchar(10) DEFAULT NULL,
  `FamilyPatientKey` varchar(10) DEFAULT NULL,
  `EmergencyContact` varchar(20) DEFAULT NULL,
  `EmergencyContactPhone` varchar(40) DEFAULT NULL,
  `EmergencyRelevant` varchar(100) DEFAULT NULL,
  `Reference` varchar(10) DEFAULT NULL,
  `Trace` char(2) DEFAULT NULL,
  `TraceTime` varchar(4) DEFAULT NULL,
  `TraceType` varchar(10) DEFAULT NULL,
  `InitDate` datetime DEFAULT NULL,
  `LastDate` datetime DEFAULT NULL,
  `Alergy` mediumtext DEFAULT NULL,
  `Allergy` mediumtext DEFAULT NULL,
  `NursingHome` varchar(50) DEFAULT NULL,
  `NursingHomeID` varchar(20) DEFAULT NULL,
  `NursingHomeInDate` varchar(10) DEFAULT NULL,
  `History` mediumtext DEFAULT NULL,
  `Description` mediumtext DEFAULT NULL,
  `Remark` mediumtext DEFAULT NULL,
  `Note` char(1) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PatientKey`),
  KEY `Birthday` (`Birthday`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
