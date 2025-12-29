-- MariaDB dump 10.19  Distrib 10.6.4-MariaDB, for Win64 (AMD64)
--
-- Host: 192.168.0.168    Database: lin
-- ------------------------------------------------------
-- Server version	10.11.11-MariaDB-0+deb12u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `special_schedule`
--

DROP TABLE IF EXISTS `special_schedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `special_schedule` (
  `SpecialScheduleKey` int(11) NOT NULL AUTO_INCREMENT,
  `Period` varchar(4) DEFAULT NULL,
  `Monday` varchar(10) DEFAULT NULL,
  `Tuesday` varchar(10) DEFAULT NULL,
  `Wednesday` varchar(10) DEFAULT NULL,
  `Thursday` varchar(10) DEFAULT NULL,
  `Friday` varchar(10) DEFAULT NULL,
  `Saturday` varchar(10) DEFAULT NULL,
  `Sunday` varchar(10) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`SpecialScheduleKey`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `special_schedule`
--

LOCK TABLES `special_schedule` WRITE;
/*!40000 ALTER TABLE `special_schedule` DISABLE KEYS */;
INSERT INTO `special_schedule` VALUES (1,'早班',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2025-06-11 10:16:12');
INSERT INTO `special_schedule` VALUES (2,'午班',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2025-09-05 08:32:47');
INSERT INTO `special_schedule` VALUES (3,'晚班',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2025-08-27 05:45:54');
/*!40000 ALTER TABLE `special_schedule` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 13:00:01
