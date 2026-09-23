import psycopg2
import os

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
connection = psycopg2.connect(
    os.environ["DATABASE_URL"]
)

cursor = connection.cursor()

# -----------------------------
# CREATE USERS TABLE
# -----------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
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
cursor.execute("""
    CREATE TABLE IF NOT EXISTS sarees (
        id SERIAL PRIMARY KEY,
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
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id SERIAL PRIMARY KEY,
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
cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        delivery_address TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# -----------------------------
# CREATE ORDER ITEMS TABLE
# -----------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
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
cursor.execute("""
    SELECT COUNT(*)
    FROM users
    WHERE role = 'admin'
""")

admin_count = cursor.fetchone()[0]

if admin_count == 0:
    cursor.execute("""
        INSERT INTO users
        (name, email, password, role)
        VALUES (%s, %s, %s, %s)
    """, (
        "Admin",
        "admin@saree.com",
        "admin123",
        "admin"
    ))

# -----------------------------
# ADD DEFAULT SAREES
# -----------------------------
cursor.execute("""
    SELECT COUNT(*)
    FROM sarees
""")

saree_count = cursor.fetchone()[0]

if saree_count == 0:

    cursor.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

    cursor.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

    cursor.execute("""
        INSERT INTO sarees
        (name, category, fabric, color, price, stock, description, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

# -----------------------------
# SAVE CHANGES
# -----------------------------
connection.commit()

cursor.close()
connection.close()

print("PostgreSQL database initialized successfully!")