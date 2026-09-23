import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
database = os.path.join(basedir, "database.db")

connection = sqlite3.connect(database)

# -----------------------------
# CREATE USERS TABLE
# -----------------------------
connection.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        role TEXT DEFAULT 'customer'
    )
""")

# -----------------------------
# CREATE SAREES TABLE
# -----------------------------
connection.execute("""
    CREATE TABLE IF NOT EXISTS sarees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        fabric TEXT,
        color TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        description TEXT,
        image TEXT
    )
""")

# -----------------------------
# CREATE CART TABLE
# -----------------------------
connection.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        saree_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (saree_id) REFERENCES sarees(id)
    )
""")

# -----------------------------
# CREATE ORDERS TABLE
# -----------------------------
connection.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        delivery_address TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# -----------------------------
# CREATE ORDER ITEMS TABLE
# -----------------------------
connection.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        saree_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (saree_id) REFERENCES sarees(id)
    )
""")

# -----------------------------
# CREATE ADMIN USER
# -----------------------------
admin_count = connection.execute(
    "SELECT COUNT(*) FROM users WHERE role = 'admin'"
).fetchone()[0]

if admin_count == 0:
    connection.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Admin",
        "admin@saree.com",
        "admin123",
        "admin"
    ))

# -----------------------------
# ADD DEFAULT SAREES
# -----------------------------
saree_count = connection.execute(
    "SELECT COUNT(*) FROM sarees"
).fetchone()[0]

if saree_count == 0:
    connection.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Kanchipuram Silk Saree",
        "Silk",
        "Pure Silk",
        "Red",
        4500,
        10,
        "Beautiful traditional Kanchipuram silk saree.",
        ""
    ))

    connection.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Banarasi Silk Saree",
        "Silk",
        "Banarasi Silk",
        "Blue",
        3800,
        8,
        "Elegant Banarasi silk saree with traditional design.",
        ""
    ))

    connection.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Cotton Saree",
        "Cotton",
        "Cotton",
        "Green",
        1200,
        20,
        "Comfortable cotton saree for everyday use.",
        ""
    ))

connection.commit()
connection.close()

print("Database initialized successfully!")