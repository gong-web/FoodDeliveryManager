-- 先判断索引是否存在再删除（MySQL 5.x/8.x 通用写法）
-- 但 MySQL 没有直接的 IF EXISTS 语法，只能用如下方式：

-- 删除索引
DROP INDEX idx_irm_restaurant ON ItemRestaurantMapping;
DROP INDEX idx_irm_item ON ItemRestaurantMapping;
DROP INDEX idx_oi_mapping ON OrderItems;

-- 如果索引不存在会报错，但不影响后续 CREATE INDEX 执行
CREATE INDEX idx_irm_restaurant ON ItemRestaurantMapping (RestaurantId);
CREATE INDEX idx_irm_item ON ItemRestaurantMapping (ItemId);
CREATE INDEX idx_oi_mapping ON OrderItems (ItemRestaurantMappingId);

-- 重构视图，使用预聚合数据
CREATE OR REPLACE VIEW restaurant_item_full_view AS
WITH order_counts AS (
    SELECT 
        ItemRestaurantMappingId,
        COUNT(*) AS OrderCount
    FROM OrderItems
    GROUP BY ItemRestaurantMappingId
)
SELECT
    r.RestaurantId,
    r.Name AS RestaurantName,
    r.Address,
    r.PhoneNumber,
    DATE_FORMAT(r.RestaurantTiming, '%H:%i-%H:%i') AS OpenHours, -- 格式化时间
    r.Website,
    CAST(r.IsAuthorized AS UNSIGNED) AS IsAuthorized,
    im.ItemId,
    im.Name AS ItemName,
    FORMAT(im.NutritionValue, 2) AS NutritionValue, -- 格式化数值
    im.Calories,
    im.Proteins,
    irm.ItemRestaurantMappingId,
    COALESCE(oc.OrderCount, 0) AS OrderCount -- 处理空值
FROM Restaurant r
LEFT JOIN ItemRestaurantMapping irm 
    ON r.RestaurantId = irm.RestaurantId
LEFT JOIN ItemMaster im 
    ON irm.ItemId = im.ItemId
LEFT JOIN order_counts oc 
    ON irm.ItemRestaurantMappingId = oc.ItemRestaurantMappingId
WHERE r.IsAuthorized = 1 or r.IsAuthorized = 0 -- 只显示已授权餐厅
ORDER BY r.RestaurantId, oc.OrderCount DESC;