USE car_data;
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'cars')
BEGIN
    CREATE TABLE cars (
        id INT IDENTITY(1,1) PRIMARY KEY,
        Make VARCHAR(100),
        Model VARCHAR(100),
        Engine_capacity FLOAT,
        Power_HP FLOAT,
        Mileage_in_km FLOAT,
        Fuel_Type VARCHAR(100),
        Gearbox VARCHAR(100),
        Year INT,
        City VARCHAR(255),
        Province VARCHAR(255),
        Seller_Type VARCHAR(100),
        Price FLOAT,
        Currency VARCHAR(10),
        Otomoto_ID BIGINT,
        Otomoto_Indicator VARCHAR(100),
        Title VARCHAR(255),
        Link VARCHAR(255),
        Description VARCHAR(MAX),
        Scraping_Date DATETIME        
    );
END;
GO
