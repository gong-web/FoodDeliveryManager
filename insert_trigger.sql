USE `fooddeliverysystem`;

DELIMITER $$

DROP TRIGGER IF EXISTS `before_order_insert`$$
CREATE TRIGGER `before_order_insert`
BEFORE INSERT ON `Order`
FOR EACH ROW
BEGIN
  DECLARE driver_rating DOUBLE;
  DECLARE delivery_distance_km DOUBLE;
  DECLARE restaurant_location_id INT;
  DECLARE delivery_time TIME;
  DECLARE msg VARCHAR(255);
  DECLARE duplicate_count INT;

  -- 1. 验证司机评分 ≥ 4.0
  SELECT `Rating` INTO driver_rating
  FROM `Driver`
  WHERE `DriverId` = NEW.`DriverId`;

  IF driver_rating IS NULL OR driver_rating < 4.0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = '订单创建失败：司机评分必须 ≥ 4.0';
  END IF;

  -- 2. 强制配送时间在 09:00-21:00
  SET delivery_time = TIME(NEW.`DeliveryTime`);
  IF delivery_time NOT BETWEEN 
    STR_TO_DATE('09:00', '%H:%i') AND 
    STR_TO_DATE('21:00', '%H:%i')
  THEN
    SIGNAL SQLSTATE '45001'
      SET MESSAGE_TEXT = '订单创建失败：配送时间必须在 09:00 至 21:00 之间';
  END IF;

  -- 3. 验证配送距离 ≤15（学校坐标固定为 0,0）
  SET restaurant_location_id = NEW.`LocationId`;
  SET delivery_distance_km = (
    SELECT ST_Distance_Sphere(
             (SELECT POINT(`Longitude`, `Latitude`) 
              FROM `location` 
              WHERE `LocationId` = restaurant_location_id),
             POINT(0, 0)
           ) / 1000
  );

  IF delivery_distance_km > 15000 THEN
    SET msg = CONCAT(
      '订单创建失败: 配送距离超过15000米 (实际: ',
      CAST(ROUND(delivery_distance_km, 2) AS CHAR),
      '米)'
    );
    SIGNAL SQLSTATE '45003'
      SET MESSAGE_TEXT = msg;
  END IF;

  -- 4. 限制不能插入一模一样的订单内容
  SELECT COUNT(*) INTO duplicate_count
  FROM `Order`
  WHERE PersonId = NEW.PersonId
    AND DriverId = NEW.DriverId
    AND LocationId = NEW.LocationId
    AND DeliveryTime = NEW.DeliveryTime
    AND DeliveryCharges = NEW.DeliveryCharges
    AND IFNULL(TotalPrice, 0) = IFNULL(NEW.TotalPrice, 0);
    
  IF duplicate_count > 0 THEN
    SIGNAL SQLSTATE '45004'
      SET MESSAGE_TEXT = '订单创建失败：不能插入重复的订单内容';
  END IF;
END
$$

DELIMITER ;