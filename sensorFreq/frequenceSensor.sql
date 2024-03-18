create database sensorFreq;
use sensorFreq;
create table HeartRateData (
    id int auto_increment primary key,
    timestamp datetime,
    heart_rate int,
    animal varchar(50),
    sensor_id int
);
select * from HeartRateData;
