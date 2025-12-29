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
-- Table structure for table `insreply`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `insreply` (
  `InsReplyKey` int(11) NOT NULL AUTO_INCREMENT,
  `ClinicID` varchar(10) DEFAULT NULL,
  `ApplyDate` varchar(5) DEFAULT NULL,
  `ApplyPeriod` varchar(6) DEFAULT NULL,
  `ApplyType` varchar(1) DEFAULT NULL,
  `CaseType` varchar(2) DEFAULT NULL,
  `Sequence` int(11) DEFAULT NULL,
  `Sample` varchar(10) DEFAULT NULL,
  `Point1` int(11) DEFAULT NULL,
  `Point2` int(11) DEFAULT NULL,
  `Point3` int(11) DEFAULT NULL,
  `Reject` varchar(10) DEFAULT NULL,
  `OrderSeq` int(11) DEFAULT NULL,
  `InsCode` varchar(12) DEFAULT NULL,
  `ChangeSeq` int(11) DEFAULT NULL,
  `Percent` int(11) DEFAULT NULL,
  `Quantity` int(11) DEFAULT NULL,
  `Point` int(11) DEFAULT NULL,
  `FileLink` varchar(2) DEFAULT NULL,
  `Reason1` varchar(1000) DEFAULT NULL,
  `Reason2` varchar(1000) DEFAULT NULL,
  `ReplySeq` int(11) DEFAULT NULL,
  `ReplyInsCode` varchar(12) DEFAULT NULL,
  `RejectCode` varchar(10) DEFAULT NULL,
  `ReplyPercent` int(11) DEFAULT NULL,
  `ReplyQuantity` int(11) DEFAULT NULL,
  `ReplyPoint` int(11) DEFAULT NULL,
  `ReplyFileLink` varchar(2) DEFAULT NULL,
  `ReplyReason1` varchar(1000) DEFAULT NULL,
  `ReplyReason2` varchar(1000) DEFAULT NULL,
  `Note` varchar(1) DEFAULT NULL,
  `Message` varchar(40) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`InsReplyKey`),
  KEY `ApplyDate` (`ApplyDate`,`CaseType`,`Sequence`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
