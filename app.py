from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'), static_folder=os.path.join(basedir, 'static'))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'saree.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Secret key for login sessions
app.secret_key = "digital_saree_secret_key"
UPLOAD_FOLDER = os.path.join(basedir, "static", "images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    connection = sqlite3.connect(os.path.join(basedir, "database.db"))
    connection.row_factory = sqlite3.Row
    return connection

# -----------------------------
# INIT DB - ADDED FOR RENDER
# -----------------------------
def init_db():
    conn = get_db_connection()
    conn.execute("""
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
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            saree_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (saree_id) REFERENCES sarees(id)
        )
    """)
    conn.execute("""
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
    conn.execute("""
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
    count = conn.execute("SELECT COUNT(*) FROM sarees").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)", ("Admin","admin@saree.com","admin123","admin"))
        conn.execute("INSERT INTO sarees (name, category, fabric, color, price, stock, description, image) VALUES (?,?,?,?,?,?,?,?)", ("Kanchipuram Silk Saree","Silk","Pure Silk","Red",4500,10,"Beautiful traditional Kanchipuram silk saree.",""))
        conn.execute("INSERT INTO sarees (name, category, fabric, color, price, stock, description, image) VALUES (?,?,?,?,?,?,?,?)", ("Banarasi Silk Saree","Silk","Banarasi Silk","Blue",3800,8,"Elegant Banarasi silk saree with traditional design.",""))
        conn.execute("INSERT INTO sarees (name, category, fabric, color, price, stock, description, image) VALUES (?,?,?,?,?,?,?,?)", ("Cotton Saree","Cotton","Cotton","Green",1200,20,"Comfortable cotton saree for everyday use.",""))
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")
# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        address = request.form["address"]
        connection = get_db_connection()
        try:
            connection.execute("""
                INSERT INTO users
                (name, email, password, phone, address, role)
                VALUES (?,?,?,?,?,?)
            """, (
                name,
                email,
                password,
                phone,
                address,
                "customer"
            ))
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            return "Email already registered!"
        connection.close()
        return redirect(url_for("login"))
    return render_template("register.html")
# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        connection = get_db_connection()
        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email =? AND password =?
        """, (email, password)).fetchone()
        connection.close()
        if user:
            # Store user information in session
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            # Admin goes to admin dashboard
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            # Customer goes to catalog
            return redirect(url_for("catalog"))
        return "Invalid email or password!"
    return render_template("login.html")
# -----------------------------
# CATALOG
# -----------------------------
@app.route("/catalog")
def catalog():
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    connection = get_db_connection()
    query = """
        SELECT *
        FROM sarees
        WHERE 1=1
    """
    params = []
    if search:
        query += """
            AND (
                name LIKE?
                OR fabric LIKE?
                OR color LIKE?
            )
        """
        search_value = f"%{search}%"
        params.extend([
            search_value,
            search_value,
            search_value
        ])
    if category:
        query += " AND category =?"
        params.append(category)
    query += " ORDER BY id DESC"
    sarees = connection.execute(
        query,
        params
    ).fetchall()
    categories = connection.execute("""
        SELECT DISTINCT category
        FROM sarees
        WHERE category IS NOT NULL
        AND category!= ''
        ORDER BY category
    """).fetchall()
    connection.close()
    return render_template(
        "catalog.html",
        sarees=sarees,
        categories=categories,
        search=search,
        selected_category=category
    )
# -----------------------------
# SAREE DETAILS
# -----------------------------
@app.route("/saree/<int:saree_id>")
def saree_details(saree_id):
    connection = get_db_connection()
    saree = connection.execute("""
        SELECT *
        FROM sarees
        WHERE id =?
    """, (saree_id,)).fetchone()
    connection.close()
    if saree is None:
        return "Saree not found!"
    return render_template(
        "saree_details.html",
        saree=saree
    )
# -----------------------------
# ADD TO CART
# -----------------------------
@app.route("/add-to-cart/<int:saree_id>", methods=["POST"])
def add_to_cart(saree_id):
    # Check whether user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    quantity = int(request.form["quantity"])
    connection = get_db_connection()
    # Check saree exists and get stock
    saree = connection.execute("""
        SELECT *
        FROM sarees
        WHERE id =?
    """, (saree_id,)).fetchone()
    if saree is None:
        connection.close()
        return "Saree not found!"
    # Check stock
    if quantity > saree["stock"]:
        connection.close()
        return "Not enough stock available!"
    # Check whether saree is already in cart
    existing_item = connection.execute("""
        SELECT *
        FROM cart
        WHERE user_id =? AND saree_id =?
    """, (
        session["user_id"],
        saree_id
    )).fetchone()
    if existing_item:
        new_quantity = existing_item["quantity"] + quantity
        if new_quantity > saree["stock"]:
            connection.close()
            return "Not enough stock available!"
        connection.execute("""
            UPDATE cart
            SET quantity =?
            WHERE id =?
        """, (
            new_quantity,
            existing_item["id"]
        ))
    else:
        connection.execute("""
            INSERT INTO cart
            (user_id, saree_id, quantity)
            VALUES (?,?,?)
        """, (
            session["user_id"],
            saree_id,
            quantity
        ))
    connection.commit()
    connection.close()
    return redirect(url_for("cart"))
# -----------------------------
# CART
# -----------------------------
@app.route("/cart")
def cart():
    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))
    connection = get_db_connection()
    cart_items = connection.execute("""
        SELECT
            cart.id,
            cart.quantity,
            sarees.name,
            sarees.price,
            sarees.image
        FROM cart
        JOIN sarees
        ON cart.saree_id = sarees.id
        WHERE cart.user_id =?
    """, (
        session["user_id"],
    )).fetchall()
    connection.close()
    total = 0
    for item in cart_items:
        total += item["price"] * item["quantity"]
    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )
# -----------------------------
# REMOVE FROM CART
# -----------------------------
@app.route("/remove-from-cart/<int:cart_id>", methods=["POST"])
def remove_from_cart(cart_id):
    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))
    connection = get_db_connection()
    connection.execute("""
        DELETE FROM cart
        WHERE id =? AND user_id =?
    """, (
        cart_id,
        session["user_id"]
    ))
    connection.commit()
    connection.close()
    return redirect(url_for("cart"))
# -----------------------------
# CHECKOUT
# -----------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    connection = get_db_connection()
    # Get cart items
    cart_items = connection.execute("""
        SELECT
            cart.id,
            cart.saree_id,
            cart.quantity,
            sarees.name,
            sarees.price,
            sarees.stock
        FROM cart
        JOIN sarees
        ON cart.saree_id = sarees.id
        WHERE cart.user_id =?
    """, (
        session["user_id"],
    )).fetchall()
    # Empty cart
    if not cart_items:
        connection.close()
        return redirect(url_for("cart"))
    # Calculate total
    total = 0
    for item in cart_items:
        total += item["price"] * item["quantity"]
    # -----------------------------
    # PLACE ORDER
    # -----------------------------
    if request.method == "POST":
        delivery_address = request.form["address"]
        # Check stock before placing order
        for item in cart_items:
            if item["quantity"] > item["stock"]:
                connection.close()
                return (
                    f"Not enough stock available for "
                    f"{item['name']}"
                )
        # Create order
        cursor = connection.execute("""
            INSERT INTO orders
            (user_id, total_amount, status, delivery_address)
            VALUES (?,?,?,?)
        """, (
            session["user_id"],
            total,
            "Pending",
            delivery_address
        ))
        order_id = cursor.lastrowid
        # Add order items
        for item in cart_items:
            connection.execute("""
                INSERT INTO order_items
                (order_id, saree_id, quantity, price)
                VALUES (?,?,?,?)
            """, (
                order_id,
                item["saree_id"],
                item["quantity"],
                item["price"]
            ))
            # Reduce stock
            connection.execute("""
                UPDATE sarees
                SET stock = stock -?
                WHERE id =?
            """, (
                item["quantity"],
                item["saree_id"]
            ))
        # Clear user's cart
        connection.execute("""
            DELETE FROM cart
            WHERE user_id =?
        """, (
            session["user_id"],
        ))
        connection.commit()
        connection.close()
        return redirect(
            url_for(
                "order_success",
                order_id=order_id
            )
        )
    connection.close()
    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )
# -----------------------------
# ORDER SUCCESS
# -----------------------------
@app.route("/order-success/<int:order_id>")
def order_success(order_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    connection = get_db_connection()
    order = connection.execute("""
        SELECT *
        FROM orders
        WHERE id =? AND user_id =?
    """, (
        order_id,
        session["user_id"]
    )).fetchone()
    connection.close()
    if order is None:
        return "Order not found!"
    return render_template(
        "order_success.html",
        order=order
    )
# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    connection = get_db_connection()
    saree_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM sarees
    """).fetchone()["count"]
    customer_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'customer'
    """).fetchone()["count"]
    order_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """).fetchone()["count"]
    pending_orders = connection.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Pending'
    """).fetchone()["count"]
    connection.close()
    return render_template(
        "admin/dashboard.html",
        saree_count=saree_count,
        customer_count=customer_count,
        order_count=order_count,
        pending_orders=pending_orders
    )
# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
# -----------------------------
# MY ORDERS
# -----------------------------
@app.route("/orders")
def my_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))
    connection = get_db_connection()
    orders = connection.execute("""
        SELECT *
        FROM orders
        WHERE user_id =?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()
    order_items = {}
    for order in orders:
        items = connection.execute("""
            SELECT
                order_items.quantity,
                order_items.price,
                sarees.name,
                sarees.image
            FROM order_items
            JOIN sarees
            ON order_items.saree_id = sarees.id
            WHERE order_items.order_id =?
        """, (
            order["id"],
        )).fetchall()
        order_items[order["id"]] = items
    connection.close()
    return render_template(
        "my_orders.html",
        orders=orders,
        order_items=order_items
    )
# -----------------------------
# ADMIN - MANAGE SAREES
# -----------------------------
@app.route("/admin/sarees")
def admin_sarees():
    # Only logged-in admin can access
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    connection = get_db_connection()
    sarees = connection.execute("""
        SELECT *
        FROM sarees
        ORDER BY id DESC
    """).fetchall()
    connection.close()
    return render_template(
        "admin/sarees.html",
        sarees=sarees
    )
# -----------------------------
# ADMIN - ADD SAREE
# -----------------------------
@app.route("/admin/sarees/add", methods=["GET", "POST"])
def add_saree():
    # Check admin login
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        fabric = request.form["fabric"]
        color = request.form["color"]
        price = request.form["price"]
        stock = request.form["stock"]
        description = request.form["description"]
        image = request.files["image"]
        image_filename = ""
        if image and image.filename!= "":
            image_filename = image.filename
            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    image_filename
                )
            )
        connection = get_db_connection()
        connection.execute("""
            INSERT INTO sarees
            (name, category, fabric, color, price, stock, description, image)
            VALUES (?,?,?,?,?,?,?,?)
            """, (
                name,
                category,
                fabric,
                color,
                price,
                stock,
                description,
                image_filename
            ))
        connection.commit()
        connection.close()
        return redirect(url_for("admin_sarees"))
    return render_template("admin/add_saree.html")
# -----------------------------
# ADMIN - EDIT SAREE
# -----------------------------
@app.route("/admin/sarees/edit/<int:saree_id>", methods=["GET", "POST"])
def edit_saree(saree_id):
    # Check admin login
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    connection = get_db_connection()
    saree = connection.execute("""
        SELECT *
        FROM sarees
        WHERE id =?
    """, (saree_id,)).fetchone()
    if saree is None:
        connection.close()
        return "Saree not found!"
    # Update saree
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        fabric = request.form["fabric"]
        color = request.form["color"]
        price = request.form["price"]
        stock = request.form["stock"]
        description = request.form["description"]
        connection.execute("""
            UPDATE sarees
            SET
                name =?,
                category =?,
                fabric =?,
                color =?,
                price =?,
                stock =?,
                description =?
            WHERE id =?
        """, (
            name,
            category,
            fabric,
            color,
            price,
            stock,
            description,
            saree_id
        ))
        connection.commit()
        connection.close()
        return redirect(url_for("admin_sarees"))
    connection.close()
    return render_template(
        "admin/edit_saree.html",
        saree=saree
    )
# -----------------------------
# ADMIN - DELETE SAREE
# -----------------------------
@app.route("/admin/sarees/delete/<int:saree_id>")
def delete_saree(saree_id):
    # Check admin login
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    connection = get_db_connection()
    saree = connection.execute("""
        SELECT *
        FROM sarees
        WHERE id =?
    """, (saree_id,)).fetchone()
    if saree is None:
        connection.close()
        return "Saree not found!"
    connection.execute("""
        DELETE FROM sarees
        WHERE id =?
    """, (saree_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("admin_sarees"))
# -----------------------------
# ADMIN - MANAGE ORDERS
# -----------------------------
@app.route("/admin/orders")
def admin_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role")!= "admin":
        return "Access denied!"
    connection = get_db_connection()
    orders = connection.execute("""
        SELECT
            orders.id,
            orders.total_amount,
            orders.status,
            orders.delivery_address,
            users.name,
            users.email
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """).fetchall()
    order_items = {}
    for order in orders:
        items = connection.execute("""
            SELECT
                order_items.quantity,
                order_items.price,
                sarees.name,
                sarees.image
            FROM order_items
            JOIN sarees
            ON order_items.saree_id = sarees.id
            WHERE order_items.order_id =?
        """, (order["id"],)).fetchall()
        order_items[order["id"]] = items
    connection.close()
    return render_template(
        "admin/orders.html",
        orders=orders,
        order_items=order_items
    )
# -----------------------------
# ADMIN - UPDATE ORDER STATUS
# -----------------------------
@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    # Check admin login
    if "user_id" not in session:
        return redirect(url_for("login"))
    # Check admin role
    if session.get("role")!= "admin":
        return "Access denied!"
    status = request.form["status"]
    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Cancelled"
    ]
    if status not in allowed_statuses:
        return "Invalid order status!"
    connection = get_db_connection()
    connection.execute("""
        UPDATE orders
        SET status =?
        WHERE id =?
    """, (
        status,
        order_id
    ))
    connection.commit()
    connection.close()
    return redirect(url_for("admin_orders"))
# -----------------------------
# RUN APPLICATION
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)