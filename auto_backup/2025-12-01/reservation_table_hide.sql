/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
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
-- Table structure for table `reservation_table_hide`
--

DROP TABLE IF EXISTS `reservation_table_hide`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `reservation_table_hide` (
  `ReservationTableHideKey` int(11) NOT NULL AUTO_INCREMENT,
  `Weekday` varchar(10) DEFAULT NULL,
  `Period` varchar(10) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `ReserveNo` int(11) DEFAULT NULL,
  PRIMARY KEY (`ReservationTableHideKey`),
  KEY `Weekday` (`Weekday`,`Period`,`ReserveNo`)
) ENGINE=MyISAM AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reservation_table_hide`
--

LOCK TABLES `reservation_table_hide` WRITE;
/*!40000 ALTER TABLE `reservation_table_hide` DISABLE KEYS */;
INSERT INTO `reservation_table_hide` VALUES (6,'星期二','早班','特約門診',24);
INSERT INTO `reservation_table_hide` VALUES (5,'星期二','早班','特約門診',22);
INSERT INTO `reservation_table_hide` VALUES (4,'星期二','早班','特約門診',20);
INSERT INTO `reservation_table_hide` VALUES (17,'星期四','午班','林胤谷',2);
INSERT INTO `reservation_table_hide` VALUES (18,'星期四','午班','林胤谷',4);
INSERT INTO `reservation_table_hide` VALUES (13,'星期二','早班','林胤谷',20);
INSERT INTO `reservation_table_hide` VALUES (14,'星期二','早班','林胤谷',22);
INSERT INTO `reservation_table_hide` VALUES (15,'星期二','早班','林胤谷',24);
INSERT INTO `reservation_table_hide` VALUES (19,'星期四','午班','林胤谷',6);
INSERT INTO `reservation_table_hide` VALUES (20,'星期四','午班','林胤谷',8);
INSERT INTO `reservation_table_hide` VALUES (21,'星期四','午班','林胤谷',10);
INSERT INTO `reservation_table_hide` VALUES (22,'星期四','午班','林胤谷',12);
INSERT INTO `reservation_table_hide` VALUES (23,'星期四','午班','林胤谷',24);
INSERT INTO `reservation_table_hide` VALUES (24,'星期四','午班','林胤谷',22);
INSERT INTO `reservation_table_hide` VALUES (25,'星期四','午班','林胤谷',20);
INSERT INTO `reservation_table_hide` VALUES (26,'星期四','午班','林胤谷',18);
INSERT INTO `reservation_table_hide` VALUES (27,'星期四','午班','林胤谷',16);
INSERT INTO `reservation_table_hide` VALUES (28,'星期四','午班','林胤谷',28);
INSERT INTO `reservation_table_hide` VALUES (29,'星期四','午班','林胤谷',30);
INSERT INTO `reservation_table_hide` VALUES (30,'星期四','午班','林胤谷',32);
INSERT INTO `reservation_table_hide` VALUES (31,'星期四','午班','林胤谷',34);
INSERT INTO `reservation_table_hide` VALUES (32,'星期四','午班','林胤谷',36);
INSERT INTO `reservation_table_hide` VALUES (33,'星期四','午班','林胤谷',14);
INSERT INTO `reservation_table_hide` VALUES (34,'星期四','午班','林胤谷',26);
INSERT INTO `reservation_table_hide` VALUES (41,'星期一','午班','林胤谷',24);
INSERT INTO `reservation_table_hide` VALUES (42,'星期一','午班','林胤谷',22);
INSERT INTO `reservation_table_hide` VALUES (47,'星期一','午班','林胤谷',26);
INSERT INTO `reservation_table_hide` VALUES (48,'星期一','午班','林胤谷',28);
INSERT INTO `reservation_table_hide` VALUES (49,'星期一','午班','林胤谷',30);
INSERT INTO `reservation_table_hide` VALUES (50,'星期一','午班','林胤谷',32);
INSERT INTO `reservation_table_hide` VALUES (51,'星期一','午班','林胤谷',34);
INSERT INTO `reservation_table_hide` VALUES (52,'星期一','午班','林胤谷',36);
INSERT INTO `reservation_table_hide` VALUES (64,'星期四','晚班','林胤谷',2);
/*!40000 ALTER TABLE `reservation_table_hide` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-01  6:36:40
