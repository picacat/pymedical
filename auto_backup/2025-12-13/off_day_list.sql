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
-- Table structure for table `off_day_list`
--

DROP TABLE IF EXISTS `off_day_list`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `off_day_list` (
  `OffDayListKey` int(11) NOT NULL AUTO_INCREMENT,
  `OffDate` date DEFAULT NULL,
  `Period` varchar(20) DEFAULT NULL,
  `Doctor` varchar(20) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`OffDayListKey`),
  KEY `OffDate` (`OffDate`,`Period`)
) ENGINE=MyISAM AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `off_day_list`
--

LOCK TABLES `off_day_list` WRITE;
/*!40000 ALTER TABLE `off_day_list` DISABLE KEYS */;
INSERT INTO `off_day_list` VALUES (2,'2025-07-03','早班',NULL,'2025-05-26 07:54:35');
INSERT INTO `off_day_list` VALUES (3,'2025-07-03','午班',NULL,'2025-05-26 07:54:38');
INSERT INTO `off_day_list` VALUES (4,'2025-07-03','晚班',NULL,'2025-05-26 07:54:40');
INSERT INTO `off_day_list` VALUES (5,'2025-07-04','早班',NULL,'2025-05-26 07:54:46');
INSERT INTO `off_day_list` VALUES (6,'2025-07-04','午班',NULL,'2025-05-26 07:54:48');
INSERT INTO `off_day_list` VALUES (7,'2025-07-04','晚班',NULL,'2025-05-26 07:54:50');
INSERT INTO `off_day_list` VALUES (8,'2025-07-05','早班',NULL,'2025-05-26 07:54:56');
INSERT INTO `off_day_list` VALUES (9,'2025-07-05','午班',NULL,'2025-05-26 07:54:58');
INSERT INTO `off_day_list` VALUES (10,'2025-07-05','晚班',NULL,'2025-05-26 07:55:08');
INSERT INTO `off_day_list` VALUES (15,'2025-11-01','早班',NULL,'2025-08-18 04:08:33');
INSERT INTO `off_day_list` VALUES (14,'2025-10-31','早班',NULL,'2025-08-18 04:08:10');
INSERT INTO `off_day_list` VALUES (44,'2025-10-30','晚班',NULL,'2025-09-27 03:48:40');
INSERT INTO `off_day_list` VALUES (42,'2025-10-30','晚班',NULL,'2025-09-27 03:46:33');
INSERT INTO `off_day_list` VALUES (18,'2025-10-31','午班',NULL,'2025-08-18 05:05:43');
INSERT INTO `off_day_list` VALUES (19,'2025-10-31','晚班',NULL,'2025-08-18 05:05:46');
INSERT INTO `off_day_list` VALUES (20,'2025-11-01','午班',NULL,'2025-08-18 05:05:54');
INSERT INTO `off_day_list` VALUES (21,'2025-11-01','晚班',NULL,'2025-08-18 05:05:59');
INSERT INTO `off_day_list` VALUES (53,'2026-01-17','午班',NULL,'2025-10-27 06:17:42');
INSERT INTO `off_day_list` VALUES (45,'2025-10-30','早班',NULL,'2025-09-27 03:48:54');
INSERT INTO `off_day_list` VALUES (46,'2025-10-30','早班',NULL,'2025-09-27 03:48:56');
INSERT INTO `off_day_list` VALUES (52,'2026-01-17','早班',NULL,'2025-10-27 06:17:36');
INSERT INTO `off_day_list` VALUES (48,'2025-10-30','早班',NULL,'2025-09-27 03:49:03');
INSERT INTO `off_day_list` VALUES (50,'2025-10-10','早班',NULL,'2025-09-30 08:29:07');
INSERT INTO `off_day_list` VALUES (43,'2025-10-30','午班',NULL,'2025-09-27 03:48:35');
INSERT INTO `off_day_list` VALUES (40,'2025-10-06','晚班',NULL,'2025-09-24 13:19:49');
INSERT INTO `off_day_list` VALUES (54,'2026-02-16','晚班',NULL,'2025-10-27 06:20:16');
INSERT INTO `off_day_list` VALUES (55,'2026-02-17','早班',NULL,'2025-10-27 06:20:47');
INSERT INTO `off_day_list` VALUES (56,'2026-02-18','晚班',NULL,'2025-10-27 06:21:34');
INSERT INTO `off_day_list` VALUES (57,'2026-02-20','早班',NULL,'2025-10-27 06:22:50');
INSERT INTO `off_day_list` VALUES (58,'2026-02-21','早班',NULL,'2025-10-27 06:23:31');
INSERT INTO `off_day_list` VALUES (60,'2026-02-21','午班',NULL,'2025-10-27 06:24:01');
INSERT INTO `off_day_list` VALUES (62,'2025-11-08','午班',NULL,'2025-10-31 05:27:16');
INSERT INTO `off_day_list` VALUES (63,'2025-11-22','午班',NULL,'2025-11-02 07:43:42');
INSERT INTO `off_day_list` VALUES (64,'2026-01-03','午班',NULL,'2025-11-30 10:26:37');
INSERT INTO `off_day_list` VALUES (65,'2026-01-10','午班',NULL,'2025-11-30 10:26:47');
INSERT INTO `off_day_list` VALUES (66,'2026-01-24','午班',NULL,'2025-11-30 10:26:53');
INSERT INTO `off_day_list` VALUES (67,'2026-01-31','午班',NULL,'2025-11-30 10:26:57');
INSERT INTO `off_day_list` VALUES (68,'2026-02-07','午班',NULL,'2025-11-30 10:27:47');
INSERT INTO `off_day_list` VALUES (69,'2026-02-14','午班',NULL,'2025-11-30 10:28:06');
INSERT INTO `off_day_list` VALUES (70,'2026-02-14','午班',NULL,'2025-11-30 10:28:10');
INSERT INTO `off_day_list` VALUES (71,'2026-02-28','午班',NULL,'2025-11-30 10:28:16');
INSERT INTO `off_day_list` VALUES (72,'2026-03-07','午班',NULL,'2025-11-30 10:28:54');
/*!40000 ALTER TABLE `off_day_list` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 12:59:59
