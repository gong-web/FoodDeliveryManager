USE `fooddeliverysystem`;
DELIMITER $$

DROP PROCEDURE IF EXISTS sp_update_driver_info 
$$
CREATE PROCEDURE sp_update_driver_info(
    IN p_DriverId INT,
    IN p_NewName VARCHAR(100),
    IN p_NewContact VARCHAR(50),
    IN p_NewLicense VARCHAR(50),
    IN p_NewRating DOUBLE,
    IN p_NewHiringDate DATE,
    IN p_NewVehicles VARCHAR(255)
)
BEGIN
    DECLARE v_StudentId INT;
    DECLARE v_PersonId INT;
    
    -- 逻辑检查：p_NewName 不能为空
    IF TRIM(p_NewName) = '' THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid parameter: p_NewName cannot be empty';
    END IF;
    
    -- 逻辑检查：p_NewContact 不能为空
    IF TRIM(p_NewContact) = '' THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid parameter: p_NewContact cannot be empty';
    END IF;
    
    -- 逻辑检查：p_NewVehicles 不能为空
    IF TRIM(p_NewVehicles) = '' THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid parameter: p_NewVehicles cannot be empty';
    END IF;
    
    -- 逻辑检查：p_NewRating 必须在 0 到 10 之间
    IF p_NewRating < 0 OR p_NewRating > 10 THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid parameter: p_NewRating must be between 0 and 10';
    END IF;
    
    -- 逻辑检查：p_NewHiringDate 不得为未来日期
    IF p_NewHiringDate > CURDATE() THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid parameter: p_NewHiringDate cannot be in the future';
    END IF;
    
    -- 检查 p_DriverId 是否存在于 Driver 表中
    IF (SELECT COUNT(*) FROM Driver WHERE DriverId = p_DriverId) = 0 THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No data found (invalid p_DriverId)';
    END IF;
    
    -- 更新 Driver 表（更新存在的字段）
    UPDATE Driver
    SET 
        LicenseNumber = p_NewLicense,
        Rating = p_NewRating,
        HiringDate = p_NewHiringDate
    WHERE DriverId = p_DriverId;
    
    -- 获取当前司机对应的 StudentId
    SELECT StudentId INTO v_StudentId
    FROM Driver
    WHERE DriverId = p_DriverId;
    
    IF v_StudentId IS NULL THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No data found (invalid Driver.StudentId for given p_DriverId)';
    END IF;
    
    -- 根据 StudentId 获取 Person 表中的 PersonId
    SELECT PersonId INTO v_PersonId
    FROM Student
    WHERE StudentId = v_StudentId;
    
    IF v_PersonId IS NULL THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No data found (invalid Student.PersonId for given Driver.StudentId)';
    END IF;
    
    -- 检查 Person 表中是否存在该 PersonId
    IF (SELECT COUNT(*) FROM Person WHERE PersonId = v_PersonId) = 0 THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Foreign key constraint: Person does not exist';
    END IF;
    
    -- 更新 Person 表：更新司机姓名及联系方式
    UPDATE Person
    SET 
        Name = p_NewName,
        ContactNumber = p_NewContact
    WHERE PersonId = v_PersonId;
    
    -- 更新 Vehicle 表：更新对应车辆信息
    UPDATE Vehicle
    SET VehicleType = p_NewVehicles
    WHERE DriverId = p_DriverId;
END $$
DELIMITER ;