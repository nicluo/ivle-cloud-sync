CREATE DATABASE  IF NOT EXISTS `dbdrop` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE `dbdrop`;
-- MySQL dump 10.13  Distrib 5.5.16, for Win32 (x86)
--
-- Host: localhost    Database: dbdrop
-- ------------------------------------------------------
-- Server version	5.5.29

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `auth`
--

DROP TABLE IF EXISTS `auth`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `dropbox_uid` int(11) NOT NULL COMMENT 'To store Dropbox user credentials (user id and access token)',
  `dropbox_key` varchar(45) DEFAULT NULL,
  `dropbox_secret` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth`
--

LOCK TABLES `auth` WRITE;
/*!40000 ALTER TABLE `auth` DISABLE KEYS */;
INSERT INTO `auth` VALUES (1,11184820,'ahzo2wqoms0j1g7','8pdo1cyd4rlop6k');
/*!40000 ALTER TABLE `auth` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dropbox_copy_ref_store`
--

DROP TABLE IF EXISTS `dropbox_copy_ref_store`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dropbox_copy_ref_store` (
  `store_id` int(11) NOT NULL AUTO_INCREMENT,
  `file_id` varchar(50) NOT NULL,
  `dropbox_copy_ref` varchar(45) DEFAULT NULL,
  `dropbox_copy_ref_expiry` datetime DEFAULT NULL,
  `source_file_path` varchar(200) DEFAULT NULL,
  `source_user_id` int(11) DEFAULT NULL,
  `source_file_revision` int(11) DEFAULT NULL,
  PRIMARY KEY (`store_id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dropbox_jobs`
--

DROP TABLE IF EXISTS `dropbox_jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dropbox_jobs` (
  `job_id` int(11) NOT NULL AUTO_INCREMENT,
  `file_id` varchar(50) DEFAULT NULL,
  `http_url` varchar(100) DEFAULT NULL,
  `method` varchar(50) DEFAULT NULL,
  `user_id` varchar(50) DEFAULT NULL,
  `target_path` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dropbox_jobs`
--

LOCK TABLES `dropbox_jobs` WRITE;
/*!40000 ALTER TABLE `dropbox_jobs` DISABLE KEYS */;
INSERT INTO `dropbox_jobs` VALUES (1,'1000','http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf','http','1','CS2106/pr3.pdf'),(2,'1001','http://ics.uci.edu/~bic/courses/OS-2012/Lectures-on-line/proj3.pptx','http','1','CS2106/proj3.pptx'),(3,'1000','http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf','http','1','CS2106/hello.pdf');
/*!40000 ALTER TABLE `dropbox_jobs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dropbox_upload_history`
--

DROP TABLE IF EXISTS `dropbox_upload_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dropbox_upload_history` (
  `history_id` int(11) NOT NULL AUTO_INCREMENT,
  `job_id` int(11) DEFAULT NULL,
  `file_id` varchar(50) DEFAULT NULL,
  `http_url` varchar(200) DEFAULT NULL,
  `method` varchar(10) DEFAULT NULL,
  `user_id` varchar(50) DEFAULT NULL,
  `target_path` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`history_id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;


/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2012-12-25 13:41:22
