from flask import Flask, render_template, jsonify
from config import get_connection
import pymysql
from flask import request, redirect, url_for
import xml.etree.ElementTree as ET
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import re


app = Flask(__name__)
app.secret_key = 'your-strong-secret-key-here'  # 必须设置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 指定登录入口

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # 表单数据验证
            if request.form['password'] != request.form['confirm_password']:
                return render_template('register.html', error="密码不一致")

            if not re.match(r'^[0-9]{10}$', request.form['username']):
                return render_template('register.html', error="学工号格式错误")

            conn = get_connection()
            with conn.cursor() as cursor:
                # 检查用户名唯一性
                cursor.execute("SELECT UserId FROM `User` WHERE username = %s",  # 表名用反引号包裹
                             (request.form['username'],))
                if cursor.fetchone():
                    return render_template('register.html', error="该学工号已注册")

                # 密码哈希处理
                from werkzeug.security import generate_password_hash
                pwd_hash = generate_password_hash(request.form['password'])
                
                # 插入新用户
                cursor.execute("""
                    INSERT INTO `User`  # 修改表名
                    (Name, username, password_hash, Email, ContactNumber)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    request.form['name'],
                    request.form['username'],
                    pwd_hash,
                    request.form['email'],
                    request.form['phone']
                ))
                conn.commit()
                return render_template('register.html', registration_success=True)
        except pymysql.Error as e:
            conn.rollback()
            return render_template('register.html', error=f"注册失败: {str(e)}")
        finally:
            if conn: conn.close()
    return render_template('register.html')

# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT UserId, password_hash  # 修改字段名
                    FROM `User`  # 修改表名
                    WHERE username = %s AND is_active = 1
                """, (request.form['username'],))
                user = cursor.fetchone()
                
                if user:
                    from werkzeug.security import check_password_hash
                    if check_password_hash(user['password_hash'], request.form['password']):
                        login_user(User(user['UserId']))  # 修改字段名
                        return redirect(url_for('index'))
                return "无效凭证"
        except Exception as e:
            return f"登录错误: {str(e)}"
        finally:
            if conn: conn.close()
    return render_template('login.html')

# 基础路由
@app.route('/')
@login_required  # 新增装饰器
def index():
    return render_template('index.html')

# 用户登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 人员信息管理
@app.route('/persons')
def show_persons():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 联合查询人员基础信息及角色详情
            cursor.execute("""
                SELECT 
                    p.PersonId,
                    p.Name,
                    p.Address,
                    p.Gender,
                    p.Email,
                    p.ContactNumber,
                    COALESCE(s.Major, f.College, st.Position, '普通用户') AS RoleDetail,
                    CASE 
                        WHEN s.PersonId IS NOT NULL THEN '学生'
                        WHEN f.PersonId IS NOT NULL THEN '教职工'
                        WHEN st.PersonId IS NOT NULL THEN '行政人员'
                        ELSE '普通用户'
                    END AS UserType
                FROM Person p
                LEFT JOIN Student s ON p.PersonId = s.PersonId
                LEFT JOIN Faculty f ON p.PersonId = f.PersonId
                LEFT JOIN Staff st ON p.PersonId = st.PersonId
                ORDER BY p.PersonId DESC
                LIMIT 100
            """)
            persons = cursor.fetchall()
        return render_template('persons.html', persons=persons)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

@app.route('/dashboard')
def dashboard():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 获取系统关键指标
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM Person) AS total_users,
                    (SELECT COUNT(*) FROM `Order`) AS total_orders,
                    (SELECT COUNT(*) FROM Driver WHERE IsAuthorized=1) AS active_drivers,
                    (SELECT SUM(TotalPrice) FROM `Order`) AS total_revenue
            """)
            metrics = cursor.fetchone()
            
            # 获取实时订单状态
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN TIMESTAMPDIFF(MINUTE, DeliveryTime, NOW()) < 30 THEN '进行中'
                        ELSE '已完成'
                    END AS status,
                    COUNT(*) AS count
                FROM `Order`
                GROUP BY status
            """)
            order_status = cursor.fetchall()
            
        return render_template('dashboard.html', 
                             metrics=metrics,
                             order_status=order_status)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

# 司机及车辆管理
@app.route('/drivers')
def show_drivers():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT 
                d.DriverId,
                p.Name,
                p.ContactNumber,
                d.LicenseNumber,
                d.Rating,
                d.HiringDate,
                d.StudentId,
                GROUP_CONCAT(DISTINCT v.VehicleType SEPARATOR ', ') AS Vehicles,
                COUNT(o.OrderId) AS CompletedOrders
            FROM Driver d
            JOIN student s ON d.StudentId = s.StudentId
            JOIN Person p ON s.PersonId = p.PersonId
            LEFT JOIN Vehicle v ON d.DriverId = v.DriverId
            LEFT JOIN `Order` o ON d.DriverId = o.DriverId
            GROUP BY d.DriverId
            ORDER BY d.Rating DESC
            """)
            drivers = cursor.fetchall()
        return render_template('drivers.html', drivers=drivers)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

@app.route('/update_driver/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def update_driver(driver_id):
    conn = get_connection()
    if request.method == 'POST':
        try:
            new_name = request.form['name']
            new_contact = request.form['contact']
            new_license = request.form['license']
            new_rating = request.form['rating']
            new_hiring_date = request.form['hiring_date']
            new_vehicles = request.form['vehicles']
            new_completed_orders = request.form['completed_orders']
            with conn.cursor() as cursor:
            # 修改后的调用，仅传入 7 个参数
                cursor.execute("CALL sp_update_driver_info(%s, %s, %s, %s, %s, %s, %s)",
                    (driver_id, new_name, new_contact, new_license, new_rating, new_hiring_date, new_vehicles))
            conn.commit()
            return redirect(url_for('show_drivers'))
        except Exception as e:
            if conn:
                conn.rollback()
            return f"更新失败: {str(e)}"
        finally:
            conn.close()
    else:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        d.DriverId,
                        p.Name,
                        p.ContactNumber,
                        d.LicenseNumber,
                        d.Rating,
                        d.HiringDate,
                        d.StudentId,
                        (SELECT v.VehicleType 
                        FROM Vehicle v 
                        WHERE v.DriverId = d.DriverId 
                        LIMIT 1) AS Vehicle,
                        COUNT(o.OrderId) AS CompletedOrders
                    FROM Driver d
                    JOIN Person p ON d.StudentId = p.PersonId
                    LEFT JOIN `Order` o ON d.DriverId = o.DriverId
                    WHERE d.IsAuthorized = 1
                    GROUP BY d.DriverId
                    ORDER BY d.Rating DESC
                """)
                driver = cursor.fetchone()
            return render_template('update_driver.html', driver=driver)
        except Exception as e:
            return f"查询司机信息失败: {str(e)}"
        finally:
            conn.close()

# 订单管理
@app.route('/orders')
def show_orders():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 订单基本信息关联配送信息
            cursor.execute("""
                SELECT 
                    o.OrderId,
                    p.Name AS Customer,
                    l.Name AS LocationName,
                    o.TotalPrice,
                    dr.Name AS DriverName,
                    o.DeliveryTime,
                    COUNT(oi.ItemRestaurantMappingId) AS ItemCount
                FROM `Order` o
                JOIN Person p ON o.PersonId = p.PersonId
                JOIN Location l ON o.LocationId = l.LocationId
                LEFT JOIN Driver d ON o.DriverId = d.DriverId
                LEFT JOIN student s ON d.StudentId = s.StudentId
                LEFT JOIN Person dr ON s.PersonId = dr.PersonId
                LEFT JOIN OrderItems oi ON o.OrderId = oi.OrderId
                GROUP BY o.OrderId
                ORDER BY o.DeliveryTime DESC
                LIMIT 50
            """)
            orders = cursor.fetchall()
        return render_template('orders.html', orders=orders)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

# 订单详情
@app.route('/order/<int:order_id>')
def order_details(order_id):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 订单基本信息
            cursor.execute("""
                SELECT 
                    o.OrderId,
                    p.Name AS CustomerName,
                    p.ContactNumber,
                    l.Name AS LocationName,
                    l.Address,
                    o.TotalPrice,
                    dr.Name AS DriverName,
                    o.DeliveryTime,
                    o.DeliveryCharges
                FROM `Order` o
                JOIN Person p ON o.PersonId = p.PersonId
                JOIN Location l ON o.LocationId = l.LocationId
                LEFT JOIN Driver d ON o.DriverId = d.DriverId
                LEFT JOIN student s ON d.StudentId = s.StudentId
                LEFT JOIN Person dr ON s.PersonId = dr.PersonId
                WHERE o.OrderId = %s
            """, (order_id,))
            order_info = cursor.fetchone()
            
            # 订单明细项
            cursor.execute("""
                SELECT 
                    im.Name AS ItemName,
                    im.NutritionValue,
                    im.Calories,
                    im.Proteins,
                    r.Name AS RestaurantName,
                    COUNT(*) AS Quantity
                FROM OrderItems oi
                JOIN ItemRestaurantMapping irm ON oi.ItemRestaurantMappingId = irm.ItemRestaurantMappingId
                JOIN ItemMaster im ON irm.ItemId = im.ItemId
                JOIN Restaurant r ON irm.RestaurantId = r.RestaurantId
                WHERE oi.OrderId = %s
                GROUP BY im.ItemId, r.RestaurantId
            """, (order_id,))
            items = cursor.fetchall()
            
        return render_template('order_detail.html', order=order_info, items=items)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

@app.route('/restaurants', methods=['GET'])
def show_restaurants():
    search_restaurant = request.args.get('restaurant', '').strip()
    search_item = request.args.get('item', '').strip()
    min_orders = request.args.get('min_orders', '').strip()
    auth_status = request.args.get('auth_status', '').strip()

    sql = "SELECT * FROM restaurant_item_full_view"
    params = []
    conditions = []
    if search_restaurant:
        conditions.append("RestaurantName LIKE %s")
        params.append("%" + search_restaurant + "%")
    if search_item:
        conditions.append("ItemName LIKE %s")
        params.append("%" + search_item + "%")
    if min_orders and min_orders.isdigit():
        conditions.append("OrderCount >= %s")
        params.append(int(min_orders))
    if auth_status in ('0', '1'):
        conditions.append("IsAuthorized = %s")
        params.append(int(auth_status))
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY RestaurantId ASC, OrderCount DESC"

    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            restaurant_items = cursor.fetchall()
        search_opts = {
            'restaurant': search_restaurant,
            'item': search_item,
            'min_orders': min_orders,
            'auth_status': auth_status
        }
        return render_template('restaurants.html', restaurant_items=restaurant_items, search_opts=search_opts)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn:
            conn.close()

# 数据分析报表
@app.route('/analytics')
def show_analytics():
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 订单趋势分析
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(DeliveryTime, '%Y-%m') AS month,
                    COUNT(OrderId) AS order_count,
                    IFNULL(SUM(TotalPrice), 0) AS total_revenue,
                    IFNULL(AVG(TotalPrice), 0) AS avg_order_value
                FROM `Order`
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
            """)
            order_trend = cursor.fetchall() or []

            # 配送热点分析
            cursor.execute("""
                SELECT 
                    COALESCE(l.Name, '未知地点') AS location_name,
                    COUNT(o.OrderId) AS order_count,
                    ROUND(IFNULL(AVG(l.Latitude), 0), 4) AS avg_lat,
                    ROUND(IFNULL(AVG(l.Longitude), 0), 4) AS avg_lng
                FROM `Order` o
                LEFT JOIN Location l ON o.LocationId = l.LocationId
                GROUP BY l.LocationId
                ORDER BY order_count DESC
                LIMIT 10
            """)
            hot_spots = cursor.fetchall() or []

            # 菜品受欢迎程度
            cursor.execute("""
                SELECT 
                    COALESCE(im.Name, '未知菜品') AS item_name,
                    COUNT(oi.ItemRestaurantMappingId) AS order_count,
                    IFNULL(AVG(im.NutritionValue), 0) AS avg_nutrition,
                    IFNULL(SUM(im.Calories), 0) AS total_calories
                FROM OrderItems oi
                LEFT JOIN ItemRestaurantMapping irm ON oi.ItemRestaurantMappingId = irm.ItemRestaurantMappingId
                LEFT JOIN ItemMaster im ON irm.ItemId = im.ItemId
                GROUP BY im.ItemId
                ORDER BY order_count DESC
                LIMIT 10
            """)
            popular_items = cursor.fetchall() or []

        return render_template('analytics.html',
                             order_trend=order_trend,
                             hot_spots=hot_spots,
                             popular_items=popular_items)
    except pymysql.MySQLError as e:
        return f"数据库错误: {str(e)}"
    finally:
        if conn: conn.close()

@app.route('/delete_person/<int:person_id>', methods=['POST'])
@login_required
def delete_person(person_id):
    conn = None
    try:
        conn = get_connection()
        conn.begin()
        
        with conn.cursor() as cursor:
            # 获取关联订单（用于日志记录）
            cursor.execute("SELECT OrderId FROM `Order` WHERE PersonId = %s", (person_id,))
            orders = cursor.fetchall()
            
            # 级联删除将自动处理以下操作：
            # 1. 删除OrderItems（通过Order表级联）
            # 2. 删除Order（通过Person表级联）
            
            # 删除关联角色信息
            cursor.execute("DELETE FROM Faculty WHERE PersonId = %s", (person_id,))
            cursor.execute("DELETE FROM Student WHERE PersonId = %s", (person_id,))
            cursor.execute("DELETE FROM Staff WHERE PersonId = %s", (person_id,))
            
            # 删除人员主记录
            cursor.execute("DELETE FROM Person WHERE PersonId = %s", (person_id,))
            
            conn.commit()
            return redirect(url_for('show_persons'))
            
    except Exception as e:
        if conn: conn.rollback()
        error_msg = f"删除失败: {str(e)}"
        if isinstance(e, pymysql.Error):
            error_msg += f" (错误代码: {e.args[0]})"
        return error_msg
    finally:
        if conn: conn.close()

# ...existing code...
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        conn = None
        try:
            # 获取所有商品-餐厅映射信息
            items = []
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT irm.ItemRestaurantMappingId, im.Name, r.Name AS RestaurantName
                    FROM ItemRestaurantMapping irm
                    JOIN ItemMaster im ON irm.ItemId = im.ItemId
                    JOIN Restaurant r ON irm.RestaurantId = r.RestaurantId
                """)
                items = cursor.fetchall()
            # 统计每个商品的数量
            selected_items = []
            for item in items:
                qty = int(request.form.get(f'item_{item["ItemRestaurantMappingId"]}', 0))
                if qty > 0:  # 只处理数量大于0的商品
                    selected_items.extend([item["ItemRestaurantMappingId"]] * qty)
            delivery_charges = 8  # 固定配送费

            if not selected_items:
                raise ValueError("至少需要选择一个商品")
            # 获取选择的餐厅id
            restaurant_id = request.form.get('restaurant_id')
            if not restaurant_id:
                raise ValueError("请选择餐厅")
            # 校验司机
            driver_id = request.form.get('driver_id')
            if not driver_id or not driver_id.isdigit() or int(driver_id) <= 0:
                raise ValueError("请选择有效的司机")

            conn = get_connection()
            with conn.cursor() as cursor:
                # 校验 driver_id 是否存在且链路完整
                cursor.execute("""
                    SELECT d.DriverId
                    FROM Driver d
                    JOIN student s ON d.StudentId = s.StudentId
                    JOIN Person p ON s.PersonId = p.PersonId
                    WHERE d.DriverId = %s
                """, (int(driver_id),))
                valid_driver = cursor.fetchone()
                if not valid_driver:
                    raise ValueError("请选择有效的司机")

                # 插入主订单
                cursor.execute("""
                    INSERT INTO `Order` 
                    (PersonId, DriverId, LocationId, DeliveryCharges, DeliveryTime, TotalPrice)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    request.form['person_id'],
                    int(driver_id),
                    restaurant_id,
                    delivery_charges,
                    datetime.strptime(request.form['delivery_time'], '%Y-%m-%dT%H:%M'),
                    request.form['total_price']
                ))

                order_id = cursor.lastrowid

                # 插入订单商品
                cursor.executemany("""
                    INSERT INTO OrderItems (OrderId, ItemRestaurantMappingId)
                    VALUES (%s, %s)
                """, [(order_id, irm_id) for irm_id in selected_items])

                conn.commit()
                return redirect(url_for('order_details', order_id=order_id))
        except Exception as e:
            if conn: 
                conn.rollback()
            return render_template('create.html',
                       error=f"订单创建失败: {str(e)}",
                       now=datetime.now(),
                       **load_form_data())
        finally:
            if conn: 
                conn.close()
    else:
        try:
            return render_template('create.html',
                                **load_form_data(),
                                now=datetime.now())
        except Exception as e:
            return f"数据加载失败: {str(e)}"
# ...existing code...


def load_form_data():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT PersonId, Name, ContactNumber 
                FROM Person 
                WHERE PersonId IN (
                    SELECT DISTINCT PersonId 
                    FROM `Order`
                )
            """)
            persons = cursor.fetchall()
            cursor.execute("""
                SELECT d.DriverId, p.Name AS DriverName, d.LicenseNumber, d.Rating
                FROM Driver d
                JOIN student s ON d.StudentId = s.StudentId
                JOIN Person p ON s.PersonId = p.PersonId
                WHERE EXISTS (
                    SELECT 1 FROM Vehicle 
                    WHERE DriverId = d.DriverId
                )
            """)
            drivers = cursor.fetchall()
            # 查询所有商品-餐厅映射
            cursor.execute("""
                SELECT irm.ItemRestaurantMappingId, im.Name, r.Name AS RestaurantName
                FROM ItemRestaurantMapping irm
                JOIN ItemMaster im ON irm.ItemId = im.ItemId
                JOIN Restaurant r ON irm.RestaurantId = r.RestaurantId
                WHERE r.IsAuthorized = 1
            """)
            items = cursor.fetchall()
            cursor.execute("SELECT RestaurantId, Name FROM Restaurant WHERE IsAuthorized = 1")
            restaurants = cursor.fetchall()
            return {
                'persons': persons,
                'drivers': drivers,
                'items': items,
                'restaurants': restaurants
            }
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)