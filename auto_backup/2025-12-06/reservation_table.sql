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
-- Table structure for table `reservation_table`
--

DROP TABLE IF EXISTS `reservation_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reservation_table` (
  `ReservationTableKey` int(11) NOT NULL AUTO_INCREMENT,
  `ReserveType` varchar(10) DEFAULT NULL,
  `Room` int(11) DEFAULT NULL,
  `Period` varchar(10) DEFAULT NULL,
  `Weekday` varchar(10) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `RowNo` int(11) DEFAULT NULL,
  `ColumnNo` int(11) DEFAULT NULL,
  `Time` varchar(10) DEFAULT NULL,
  `ReserveNo` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ReservationTableKey`),
  KEY `Room` (`Room`,`Period`,`ColumnNo`,`RowNo`)
) ENGINE=MyISAM AUTO_INCREMENT=1647 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reservation_table`
--

LOCK TABLES `reservation_table` WRITE;
/*!40000 ALTER TABLE `reservation_table` DISABLE KEYS */;
INSERT INTO `reservation_table` VALUES (67,NULL,NULL,'早班',NULL,'特約門診',4,0,'08:40',10,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (66,NULL,NULL,'早班',NULL,'特約門診',3,8,'10:30',32,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (65,NULL,NULL,'早班',NULL,'特約門診',3,4,'09:30',20,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (64,NULL,NULL,'早班',NULL,'特約門診',3,0,'08:30',8,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (63,NULL,NULL,'早班',NULL,'特約門診',2,12,'11:20',42,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (62,NULL,NULL,'早班',NULL,'特約門診',2,8,'10:20',30,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (61,NULL,NULL,'早班',NULL,'特約門診',2,4,'09:20',18,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (60,NULL,NULL,'早班',NULL,'特約門診',2,0,'08:20',6,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (59,NULL,NULL,'早班',NULL,'特約門診',1,12,'11:10',40,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (58,NULL,NULL,'早班',NULL,'特約門診',1,8,'10:10',28,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (57,NULL,NULL,'早班',NULL,'特約門診',1,4,'09:10',16,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (56,NULL,NULL,'早班',NULL,'特約門診',1,0,'08:10',4,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (55,NULL,NULL,'早班',NULL,'特約門診',0,12,'11:00',38,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (54,NULL,NULL,'早班',NULL,'特約門診',0,8,'10:00',26,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (53,NULL,NULL,'早班',NULL,'特約門診',0,4,'09:00',14,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (52,'初診',NULL,'早班',NULL,'特約門診',0,0,'08:00',2,'2025-04-19 07:04:21');
INSERT INTO `reservation_table` VALUES (328,NULL,NULL,'晚班',NULL,'林胤谷',4,4,'16:24',15,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (327,NULL,NULL,'晚班',NULL,'林胤谷',4,0,'15:24',5,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (326,NULL,NULL,'晚班',NULL,'林胤谷',3,12,'18:18',34,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (325,NULL,NULL,'晚班',NULL,'林胤谷',3,8,'17:18',24,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (324,NULL,NULL,'晚班',NULL,'林胤谷',3,4,'16:18',14,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (322,NULL,NULL,'晚班',NULL,'林胤谷',2,12,'18:12',33,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (40,NULL,NULL,'晚班',NULL,'特約門診',0,0,'16:00',2,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (41,NULL,NULL,'晚班',NULL,'特約門診',0,4,'17:00',10,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (42,NULL,NULL,'晚班',NULL,'特約門診',0,8,'18:00',18,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (43,NULL,NULL,'晚班',NULL,'特約門診',1,0,'16:15',4,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (44,NULL,NULL,'晚班',NULL,'特約門診',1,4,'17:15',12,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (45,NULL,NULL,'晚班',NULL,'特約門診',1,8,'18:15',20,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (46,NULL,NULL,'晚班',NULL,'特約門診',2,0,'16:30',6,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (47,NULL,NULL,'晚班',NULL,'特約門診',2,4,'17:30',14,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (48,NULL,NULL,'晚班',NULL,'特約門診',2,8,'18:30',22,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (49,NULL,NULL,'晚班',NULL,'特約門診',3,0,'16:45',8,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (50,NULL,NULL,'晚班',NULL,'特約門診',3,4,'17:45',16,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (51,NULL,NULL,'晚班',NULL,'特約門診',3,8,'18:45',24,'2025-04-01 06:59:53');
INSERT INTO `reservation_table` VALUES (68,NULL,NULL,'早班',NULL,'特約門診',4,4,'09:40',22,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (69,NULL,NULL,'早班',NULL,'特約門診',4,8,'10:40',34,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (70,NULL,NULL,'早班',NULL,'特約門診',5,0,'08:50',12,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (71,NULL,NULL,'早班',NULL,'特約門診',5,4,'09:50',24,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (72,NULL,NULL,'早班',NULL,'特約門診',5,8,'10:50',36,'2025-04-01 07:02:22');
INSERT INTO `reservation_table` VALUES (323,NULL,NULL,'晚班',NULL,'林胤谷',3,0,'15:18',4,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (321,NULL,NULL,'晚班',NULL,'林胤谷',2,8,'17:12',23,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (320,NULL,NULL,'晚班',NULL,'林胤谷',2,4,'16:12',13,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (318,NULL,NULL,'晚班',NULL,'林胤谷',1,12,'18:06',32,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (319,NULL,NULL,'晚班',NULL,'林胤谷',2,0,'15:12',3,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (317,NULL,NULL,'晚班',NULL,'林胤谷',1,8,'17:06',22,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (316,NULL,NULL,'晚班',NULL,'林胤谷',1,4,'16:06',12,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (315,NULL,NULL,'晚班',NULL,'林胤谷',1,0,'15:06',2,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (314,NULL,NULL,'晚班',NULL,'林胤谷',0,12,'18:00',31,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (313,NULL,NULL,'晚班',NULL,'林胤谷',0,8,'17:00',21,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (197,NULL,NULL,'午班',NULL,'特約門診',5,8,'15:50',36,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (196,NULL,NULL,'午班',NULL,'特約門診',5,4,'14:50',24,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (195,NULL,NULL,'午班',NULL,'特約門診',5,0,'13:50',12,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (194,NULL,NULL,'午班',NULL,'特約門診',4,8,'15:40',34,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (193,NULL,NULL,'午班',NULL,'特約門診',4,4,'14:40',22,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (192,NULL,NULL,'午班',NULL,'特約門診',4,0,'13:40',10,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (191,NULL,NULL,'午班',NULL,'特約門診',3,8,'15:30',32,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (190,NULL,NULL,'午班',NULL,'特約門診',3,4,'14:30',20,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (189,NULL,NULL,'午班',NULL,'特約門診',3,0,'13:30',8,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (188,NULL,NULL,'午班',NULL,'特約門診',2,8,'15:20',30,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (187,NULL,NULL,'午班',NULL,'特約門診',2,4,'14:20',18,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (186,NULL,NULL,'午班',NULL,'特約門診',2,0,'13:20',6,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (185,NULL,NULL,'午班',NULL,'特約門診',1,8,'15:10',28,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (184,NULL,NULL,'午班',NULL,'特約門診',1,4,'14:10',16,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (183,NULL,NULL,'午班',NULL,'特約門診',1,0,'13:10',4,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (182,NULL,NULL,'午班',NULL,'特約門診',0,8,'15:00',26,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (181,NULL,NULL,'午班',NULL,'特約門診',0,4,'14:00',14,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (180,NULL,NULL,'午班',NULL,'特約門診',0,0,'13:00',2,'2025-06-09 06:34:07');
INSERT INTO `reservation_table` VALUES (312,NULL,NULL,'晚班',NULL,'林胤谷',0,4,'16:00',11,'2025-09-19 09:44:25');
INSERT INTO `reservation_table` VALUES (311,NULL,NULL,'晚班',NULL,'林胤谷',0,0,'15:00',1,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (329,NULL,NULL,'晚班',NULL,'林胤谷',4,8,'17:24',25,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (330,NULL,NULL,'晚班',NULL,'林胤谷',4,12,'18:24',35,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (331,NULL,NULL,'晚班',NULL,'林胤谷',5,0,'15:30',6,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (332,NULL,NULL,'晚班',NULL,'林胤谷',5,4,'16:30',16,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (333,NULL,NULL,'晚班',NULL,'林胤谷',5,8,'17:30',26,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (334,NULL,NULL,'晚班',NULL,'林胤谷',5,12,'18:30',36,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (335,NULL,NULL,'晚班',NULL,'林胤谷',6,0,'15:36',7,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (336,NULL,NULL,'晚班',NULL,'林胤谷',6,4,'16:36',17,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (337,NULL,NULL,'晚班',NULL,'林胤谷',6,8,'17:36',27,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (338,NULL,NULL,'晚班',NULL,'林胤谷',6,12,'18:36',37,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (339,NULL,NULL,'晚班',NULL,'林胤谷',7,0,'15:42',8,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (340,NULL,NULL,'晚班',NULL,'林胤谷',7,4,'16:42',18,'2025-09-19 09:44:25');
INSERT INTO `reservation_table` VALUES (341,NULL,NULL,'晚班',NULL,'林胤谷',7,8,'17:42',28,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (342,NULL,NULL,'晚班',NULL,'林胤谷',7,12,'18:42',38,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (343,NULL,NULL,'晚班',NULL,'林胤谷',8,0,'15:48',9,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (344,NULL,NULL,'晚班',NULL,'林胤谷',8,4,'16:48',19,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (345,NULL,NULL,'晚班',NULL,'林胤谷',8,8,'17:48',29,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (346,NULL,NULL,'晚班',NULL,'林胤谷',8,12,'18:48',39,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (347,NULL,NULL,'晚班',NULL,'林胤谷',9,0,'15:54',10,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (348,NULL,NULL,'晚班',NULL,'林胤谷',9,4,'16:54',20,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (349,NULL,NULL,'晚班',NULL,'林胤谷',9,8,'17:54',30,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (350,NULL,NULL,'晚班',NULL,'林胤谷',9,12,'18:54',40,'2025-06-13 14:45:04');
INSERT INTO `reservation_table` VALUES (1408,NULL,NULL,'午班','星期一','林胤谷',9,4,'14:54',15,'2025-09-27 22:48:19');
INSERT INTO `reservation_table` VALUES (1407,NULL,NULL,'午班','星期一','林胤谷',8,4,'14:48',14,'2025-09-27 22:48:19');
INSERT INTO `reservation_table` VALUES (1406,NULL,NULL,'午班','星期一','林胤谷',7,4,'14:42',13,'2025-09-27 22:48:19');
INSERT INTO `reservation_table` VALUES (1405,NULL,NULL,'午班','星期一','林胤谷',6,4,'14:36',12,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1404,NULL,NULL,'午班','星期一','林胤谷',5,4,'14:30',11,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1403,NULL,NULL,'午班','星期一','林胤谷',4,8,'15:24',20,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1402,NULL,NULL,'午班','星期一','林胤谷',4,4,'14:24',10,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1401,NULL,NULL,'午班','星期一','林胤谷',4,0,'13:54',5,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1400,NULL,NULL,'午班','星期一','林胤谷',3,8,'15:18',19,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1399,NULL,NULL,'午班','星期一','林胤谷',3,4,'14:18',9,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1398,NULL,NULL,'午班','星期一','林胤谷',3,0,'13:48',4,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1397,NULL,NULL,'午班','星期一','林胤谷',2,8,'15:12',18,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1396,NULL,NULL,'午班','星期一','林胤谷',2,4,'14:12',8,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1395,NULL,NULL,'午班','星期一','林胤谷',2,0,'13:42',3,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1394,NULL,NULL,'午班','星期一','林胤谷',1,8,'15:06',17,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1393,NULL,NULL,'午班','星期一','林胤谷',1,4,'14:06',7,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1392,NULL,NULL,'午班','星期一','林胤谷',1,0,'13:36',2,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1391,NULL,NULL,'午班','星期一','林胤谷',0,8,'15:00',16,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1390,NULL,NULL,'午班','星期一','林胤谷',0,4,'14:00',6,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1389,NULL,NULL,'午班','星期一','林胤谷',0,0,'13:30',1,'2025-09-27 22:48:18');
INSERT INTO `reservation_table` VALUES (1369,NULL,NULL,'午班','星期六','林胤谷',0,0,'13:30',1,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1370,NULL,NULL,'午班','星期六','林胤谷',0,4,'14:00',6,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1371,NULL,NULL,'午班','星期六','林胤谷',0,8,'15:00',16,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1372,NULL,NULL,'午班','星期六','林胤谷',1,0,'13:36',2,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1373,NULL,NULL,'午班','星期六','林胤谷',1,4,'14:06',7,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1374,NULL,NULL,'午班','星期六','林胤谷',1,8,'15:06',17,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1375,NULL,NULL,'午班','星期六','林胤谷',2,0,'13:42',3,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1376,NULL,NULL,'午班','星期六','林胤谷',2,4,'14:12',8,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1377,NULL,NULL,'午班','星期六','林胤谷',2,8,'15:12',18,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1378,NULL,NULL,'午班','星期六','林胤谷',3,0,'13:48',4,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1379,NULL,NULL,'午班','星期六','林胤谷',3,4,'14:18',9,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1380,NULL,NULL,'午班','星期六','林胤谷',3,8,'15:18',19,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1381,NULL,NULL,'午班','星期六','林胤谷',4,0,'13:54',5,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1382,NULL,NULL,'午班','星期六','林胤谷',4,4,'14:24',10,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1383,NULL,NULL,'午班','星期六','林胤谷',4,8,'15:24',20,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1384,NULL,NULL,'午班','星期六','林胤谷',5,4,'14:30',11,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1385,NULL,NULL,'午班','星期六','林胤谷',6,4,'14:36',12,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1386,NULL,NULL,'午班','星期六','林胤谷',7,4,'14:42',13,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1387,NULL,NULL,'午班','星期六','林胤谷',8,4,'14:48',14,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1388,NULL,NULL,'午班','星期六','林胤谷',9,4,'14:54',15,'2025-09-27 22:43:01');
INSERT INTO `reservation_table` VALUES (1634,NULL,NULL,'早班','星期六','林胤谷',8,12,'11:40',45,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1633,NULL,NULL,'早班','星期六','林胤谷',8,8,'10:40',33,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1632,NULL,NULL,'早班','星期六','林胤谷',8,4,'09:40',21,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1631,NULL,NULL,'早班','星期六','林胤谷',8,0,'08:40',9,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1629,NULL,NULL,'早班','星期六','林胤谷',7,8,'10:35',32,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1630,NULL,NULL,'早班','星期六','林胤谷',7,12,'11:35',44,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1628,NULL,NULL,'早班','星期六','林胤谷',7,4,'09:35',20,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1626,NULL,NULL,'早班','星期六','林胤谷',6,12,'11:30',43,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1627,NULL,NULL,'早班','星期六','林胤谷',7,0,'08:35',8,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1625,NULL,NULL,'早班','星期六','林胤谷',6,8,'10:30',31,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1623,NULL,NULL,'早班','星期六','林胤谷',6,0,'08:30',7,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1624,NULL,NULL,'早班','星期六','林胤谷',6,4,'09:30',19,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1622,NULL,NULL,'早班','星期六','林胤谷',5,12,'11:25',42,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1621,NULL,NULL,'早班','星期六','林胤谷',5,8,'10:25',30,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1620,NULL,NULL,'早班','星期六','林胤谷',5,4,'09:25',18,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1619,NULL,NULL,'早班','星期六','林胤谷',5,0,'08:25',6,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1618,NULL,NULL,'早班','星期六','林胤谷',4,12,'11:20',41,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1617,NULL,NULL,'早班','星期六','林胤谷',4,8,'10:20',29,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1616,NULL,NULL,'早班','星期六','林胤谷',4,4,'09:20',17,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1558,NULL,NULL,'早班',NULL,'林胤谷',9,12,'11:54',40,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1557,NULL,NULL,'早班',NULL,'林胤谷',9,8,'10:54',30,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1556,NULL,NULL,'早班',NULL,'林胤谷',9,4,'09:54',20,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1555,NULL,NULL,'早班',NULL,'林胤谷',9,0,'08:54',10,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1554,NULL,NULL,'早班',NULL,'林胤谷',8,12,'11:48',39,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1553,NULL,NULL,'早班',NULL,'林胤谷',8,8,'10:48',29,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1552,NULL,NULL,'早班',NULL,'林胤谷',8,4,'09:48',19,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1551,NULL,NULL,'早班',NULL,'林胤谷',8,0,'08:48',9,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1550,NULL,NULL,'早班',NULL,'林胤谷',7,12,'11:42',38,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1549,NULL,NULL,'早班',NULL,'林胤谷',7,8,'10:42',28,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1548,NULL,NULL,'早班',NULL,'林胤谷',7,4,'09:42',18,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1547,NULL,NULL,'早班',NULL,'林胤谷',7,0,'08:42',8,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1546,NULL,NULL,'早班',NULL,'林胤谷',6,12,'11:36',37,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1545,NULL,NULL,'早班',NULL,'林胤谷',6,8,'10:36',27,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1544,NULL,NULL,'早班',NULL,'林胤谷',6,4,'09:36',17,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1543,NULL,NULL,'早班',NULL,'林胤谷',6,0,'08:36',7,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1542,NULL,NULL,'早班',NULL,'林胤谷',5,12,'11:30',36,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1541,NULL,NULL,'早班',NULL,'林胤谷',5,8,'10:30',26,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1540,NULL,NULL,'早班',NULL,'林胤谷',5,4,'09:30',16,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1539,NULL,NULL,'早班',NULL,'林胤谷',5,0,'08:30',6,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1538,NULL,NULL,'早班',NULL,'林胤谷',4,12,'11:24',35,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1537,NULL,NULL,'早班',NULL,'林胤谷',4,8,'10:24',25,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1536,NULL,NULL,'早班',NULL,'林胤谷',4,4,'09:24',15,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1535,NULL,NULL,'早班',NULL,'林胤谷',4,0,'08:24',5,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1534,NULL,NULL,'早班',NULL,'林胤谷',3,12,'11:18',34,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1533,NULL,NULL,'早班',NULL,'林胤谷',3,8,'10:18',24,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1532,NULL,NULL,'早班',NULL,'林胤谷',3,4,'09:18',14,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1531,NULL,NULL,'早班',NULL,'林胤谷',3,0,'08:18',4,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1530,NULL,NULL,'早班',NULL,'林胤谷',2,12,'11:12',33,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1529,NULL,NULL,'早班',NULL,'林胤谷',2,8,'10:12',23,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1528,NULL,NULL,'早班',NULL,'林胤谷',2,4,'09:12',13,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1527,NULL,NULL,'早班',NULL,'林胤谷',2,0,'08:12',3,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1526,NULL,NULL,'早班',NULL,'林胤谷',1,12,'11:06',32,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1525,NULL,NULL,'早班',NULL,'林胤谷',1,8,'10:06',22,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1524,NULL,NULL,'早班',NULL,'林胤谷',1,4,'09:06',12,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1523,NULL,NULL,'早班',NULL,'林胤谷',1,0,'08:06',2,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1522,NULL,NULL,'早班',NULL,'林胤谷',0,12,'11:00',31,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1521,NULL,NULL,'早班',NULL,'林胤谷',0,8,'10:00',21,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1520,NULL,NULL,'早班',NULL,'林胤谷',0,4,'09:00',11,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1519,NULL,NULL,'早班',NULL,'林胤谷',0,0,'08:00',1,'2025-11-30 07:38:39');
INSERT INTO `reservation_table` VALUES (1615,NULL,NULL,'早班','星期六','林胤谷',4,0,'08:20',5,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1614,NULL,NULL,'早班','星期六','林胤谷',3,12,'11:15',40,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1613,NULL,NULL,'早班','星期六','林胤谷',3,8,'10:15',28,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1612,NULL,NULL,'早班','星期六','林胤谷',3,4,'09:15',16,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1611,NULL,NULL,'早班','星期六','林胤谷',3,0,'08:15',4,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1610,NULL,NULL,'早班','星期六','林胤谷',2,12,'11:10',39,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1609,NULL,NULL,'早班','星期六','林胤谷',2,8,'10:10',27,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1608,NULL,NULL,'早班','星期六','林胤谷',2,4,'09:10',15,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1607,NULL,NULL,'早班','星期六','林胤谷',2,0,'08:10',3,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1606,NULL,NULL,'早班','星期六','林胤谷',1,12,'11:05',38,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1605,NULL,NULL,'早班','星期六','林胤谷',1,8,'10:05',26,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1604,NULL,NULL,'早班','星期六','林胤谷',1,4,'09:05',14,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1603,NULL,NULL,'早班','星期六','林胤谷',1,0,'08:05',2,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1602,NULL,NULL,'早班','星期六','林胤谷',0,12,'11:00',37,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1601,NULL,NULL,'早班','星期六','林胤谷',0,8,'10:00',25,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1600,NULL,NULL,'早班','星期六','林胤谷',0,4,'09:00',13,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1599,NULL,NULL,'早班','星期六','林胤谷',0,0,'08:00',1,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1635,NULL,NULL,'早班','星期六','林胤谷',9,0,'08:45',10,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1636,NULL,NULL,'早班','星期六','林胤谷',9,4,'09:45',22,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1637,NULL,NULL,'早班','星期六','林胤谷',9,8,'10:45',34,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1638,NULL,NULL,'早班','星期六','林胤谷',9,12,'11:45',46,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1639,NULL,NULL,'早班','星期六','林胤谷',10,0,'08:50',11,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1640,NULL,NULL,'早班','星期六','林胤谷',10,4,'09:50',23,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1641,NULL,NULL,'早班','星期六','林胤谷',10,8,'10:50',35,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1642,NULL,NULL,'早班','星期六','林胤谷',10,12,'11:50',47,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1643,NULL,NULL,'早班','星期六','林胤谷',11,0,'08:55',12,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1644,NULL,NULL,'早班','星期六','林胤谷',11,4,'09:55',24,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1645,NULL,NULL,'早班','星期六','林胤谷',11,8,'10:55',36,'2025-11-30 07:42:58');
INSERT INTO `reservation_table` VALUES (1646,NULL,NULL,'早班','星期六','林胤谷',11,12,'11:55',48,'2025-11-30 07:42:58');
/*!40000 ALTER TABLE `reservation_table` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-06  7:00:32
