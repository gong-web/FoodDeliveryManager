# db_config.py

import pymysql

def get_connection():
    return pymysql.connect(
        host='localhost',       # 主机地址
        user='root',            # 用户名
        password='nk658',     # 数据库密码
        database='fooddeliverysystem',  # 比如 student_db
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
