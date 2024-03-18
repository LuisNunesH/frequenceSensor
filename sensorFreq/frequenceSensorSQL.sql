CREATE TABLE HeartRateData (
    id int IDENTITY(1,1) PRIMARY KEY,
    timestamp datetime,
    heart_rate int,
    animal varchar(50),
    sensor_id int
);

SELECT * FROM HeartRateData;
