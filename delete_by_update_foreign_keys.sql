-- 指定要操作的数据库
USE `FoodDeliverySystem`;

-- 关闭自动提交
SET autocommit = 0;

-- 定义错误处理变量
SET @error_occurred = 0;

-- 临时修改分隔符以支持存储过程语法
DELIMITER $$

-- 创建存储过程
CREATE PROCEDURE modify_constraints()
BEGIN
  -- 错误处理：失败时回滚并恢复外键检查
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    SET @error_occurred = 1;
    ROLLBACK;
    SET FOREIGN_KEY_CHECKS = 1;
  END;

  -- 显式开始事务
  START TRANSACTION;

  -- 禁用外键检查
  SET FOREIGN_KEY_CHECKS = 0;

  -- 修改Person相关约束
  ALTER TABLE Student 
    DROP FOREIGN KEY FK_Student_Person;
  ALTER TABLE Student 
    ADD CONSTRAINT FK_Student_Person_Cascade 
      FOREIGN KEY (PersonId) REFERENCES Person(PersonId) 
      ON DELETE CASCADE;

  ALTER TABLE Faculty 
    DROP FOREIGN KEY FK_Faculty_Person;
  ALTER TABLE Faculty 
    ADD CONSTRAINT FK_Faculty_Person_Cascade 
      FOREIGN KEY (PersonId) REFERENCES Person(PersonId) 
      ON DELETE CASCADE;

  ALTER TABLE Staff 
    DROP FOREIGN KEY FK_Staff_Person;
  ALTER TABLE Staff 
    ADD CONSTRAINT FK_Staff_Person_Cascade 
      FOREIGN KEY (PersonId) REFERENCES Person(PersonId) 
      ON DELETE CASCADE;

  ALTER TABLE `order`
    DROP FOREIGN KEY FK_Order_Person;
  ALTER TABLE `order`
    ADD CONSTRAINT FK_Order_Person
      FOREIGN KEY (PersonId) REFERENCES person(PersonId)
      ON DELETE CASCADE;

  ALTER TABLE OrderItems DROP FOREIGN KEY FK_OI_Order;
  ALTER TABLE OrderItems
    ADD CONSTRAINT FK_OI_Order
    FOREIGN KEY (OrderId) REFERENCES `order`(OrderId)
    ON DELETE CASCADE;

  -- 恢复外键检查
  SET FOREIGN_KEY_CHECKS = 1;

  -- 根据错误标记提交/回滚
  IF @error_occurred = 0 THEN
    COMMIT;
  ELSE
    ROLLBACK;
  END IF;
END
$$

-- 恢复默认分隔符
DELIMITER ;

-- 执行存储过程
CALL modify_constraints();

-- 清理存储过程
DROP PROCEDURE modify_constraints;

-- 恢复自动提交
SET autocommit = 1;

-- 学生表报错无法删除时运行下面的sql语句
-- USE `FoodDeliverySystem`;

-- -- 禁用外键检查
-- SET FOREIGN_KEY_CHECKS = 0;

-- -- 删除原有外键
-- ALTER TABLE `order` DROP FOREIGN KEY FK_Order_Person;

-- -- 添加带有级联删除的外键
-- ALTER TABLE `order`
--   ADD CONSTRAINT FK_Order_Person
--   FOREIGN KEY (PersonId) REFERENCES person(PersonId)
--   ON DELETE CASCADE;

-- -- 恢复外键检查
-- SET FOREIGN_KEY_CHECKS = 1;
-- 禁用外键检查
-- SET FOREIGN_KEY_CHECKS = 0;

-- -- 删除原有外键
-- ALTER TABLE OrderItems DROP FOREIGN KEY FK_OI_Order;

-- -- 添加带有级联删除的外键
-- ALTER TABLE OrderItems
--   ADD CONSTRAINT FK_OI_Order
--   FOREIGN KEY (OrderId) REFERENCES `order`(OrderId)
--   ON DELETE CASCADE;

-- -- 恢复外键检查
-- SET FOREIGN_KEY_CHECKS = 1;