from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.errors
import os

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'), static_folder=os.path.join(basedir, 'static'))

# Secret key for login sessions
app.secret_key = "digital_saree_secret_key"

UPLOAD_FOLDER = os.path.join(basedir, "static", "images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    connection = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )
    return connection

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return redirect(url_for("catalog"))

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
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO users
                (name, email, password, phone, address, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                name,
                email,
                password,
                phone,
                address,
                "customer"
            ))
            connection.commit()

        except psycopg2.errors.UniqueViolation:
            connection.rollback()
            cursor.close()
            connection.close()
            return "Email already registered!"

        cursor.close()
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
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = %s AND password = %s
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

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
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM sarees
        WHERE 1=1
    """

    params = []

    if search:
        query += """
            AND (
                name LIKE %s
                OR fabric LIKE %s
                OR color LIKE %s
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if category:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY id DESC"

    cursor.execute(
        query,
        params
    )

    sarees = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT category
        FROM sarees
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
    """)

    categories = cursor.fetchall()

    cursor.close()
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
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM sarees
        WHERE id = %s
    """, (
        saree_id,
    ))

    saree = cursor.fetchone()

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    quantity = int(request.form["quantity"])

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM sarees
        WHERE id = %s
    """, (
        saree_id,
    ))

    saree = cursor.fetchone()

    if saree is None:
        cursor.close()
        connection.close()
        return "Saree not found!"

    if quantity > saree["stock"]:
        cursor.close()
        connection.close()
        return "Not enough stock available!"

    cursor.execute("""
        SELECT *
        FROM cart
        WHERE user_id = %s AND saree_id = %s
    """, (
        session["user_id"],
        saree_id
    ))

    existing_item = cursor.fetchone()

    if existing_item:
        new_quantity = existing_item["quantity"] + quantity

        if new_quantity > saree["stock"]:
            cursor.close()
            connection.close()
            return "Not enough stock available!"

        cursor.execute("""
            UPDATE cart
            SET quantity = %s
            WHERE id = %s
        """, (
            new_quantity,
            existing_item["id"]
        ))

    else:
        cursor.execute("""
            INSERT INTO cart
            (user_id, saree_id, quantity)
            VALUES (%s, %s, %s)
        """, (
            session["user_id"],
            saree_id,
            quantity
        ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("cart"))

# -----------------------------
# CART
# -----------------------------
@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            cart.id,
            cart.quantity,
            sarees.name,
            sarees.price,
            sarees.image
        FROM cart
        JOIN sarees
        ON cart.saree_id = sarees.id
        WHERE cart.user_id = %s
    """, (
        session["user_id"],
    ))

    cart_items = cursor.fetchall()

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM cart
        WHERE id = %s AND user_id = %s
    """, (
        cart_id,
        session["user_id"]
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("cart"))

# -----------------------------
# CHECKOUT
# -----------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
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
        WHERE cart.user_id = %s
    """, (
        session["user_id"],
    ))

    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        connection.close()
        return redirect(url_for("cart"))

    total = 0

    for item in cart_items:
        total += item["price"] * item["quantity"]

    if request.method == "POST":
        delivery_address = request.form["address"]

        for item in cart_items:
            if item["quantity"] > item["stock"]:
                cursor.close()
                connection.close()

                return (
                    f"Not enough stock available for "
                    f"{item['name']}"
                )

        cursor.execute("""
            INSERT INTO orders
            (user_id, total_amount, status, delivery_address)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            session["user_id"],
            total,
            "Pending",
            delivery_address
        ))

        order_id = cursor.fetchone()["id"]

        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items
                (order_id, saree_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (
                order_id,
                item["saree_id"],
                item["quantity"],
                item["price"]
            ))

            cursor.execute("""
                UPDATE sarees
                SET stock = stock - %s
                WHERE id = %s
            """, (
                item["quantity"],
                item["saree_id"]
            ))

        cursor.execute("""
            DELETE FROM cart
            WHERE user_id = %s
        """, (
            session["user_id"],
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "order_success",
                order_id=order_id
            )
        )

    cursor.close()
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
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            orders.*,
            users.name AS customer_name,
            users.email AS customer_email
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        WHERE orders.id = %s
        AND orders.user_id = %s
    """, (
        order_id,
        session["user_id"]
    ))

    order = cursor.fetchone()

    if order is None:
        cursor.close()
        connection.close()
        return "Order not found!"

    cursor.execute("""
        SELECT
            order_items.quantity,
            order_items.price,
            sarees.name
        FROM order_items
        JOIN sarees
        ON order_items.saree_id = sarees.id
        WHERE order_items.order_id = %s
    """, (
        order_id,
    ))

    items = cursor.fetchall()

    order_items_text = ""

    for item in items:
        order_items_text += (
            f"{item['name']} x {item['quantity']} "
            f"- ₹{item['price'] * item['quantity']}\n"
        )

    cursor.close()
    connection.close()

    return render_template(
        "order_success.html",
        order=order,
        order_items_text=order_items_text
    )

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!"

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM sarees
    """)
    saree_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'customer'
    """)
    customer_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """)
    order_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Pending'
    """)
    pending_orders = cursor.fetchone()["count"]

    cursor.close()
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
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY id DESC
    """, (
        session["user_id"],
    ))

    orders = cursor.fetchall()

    order_items = {}

    for order in orders:
        cursor.execute("""
            SELECT
                order_items.quantity,
                order_items.price,
                sarees.name,
                sarees.image
            FROM order_items
            JOIN sarees
            ON order_items.saree_id = sarees.id
            WHERE order_items.order_id = %s
        """, (
            order["id"],
        ))

        items = cursor.fetchall()

        order_items[order["id"]] = items

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!"

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM sarees
        ORDER BY id DESC
    """)

    sarees = cursor.fetchall()

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
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

        if image and image.filename != "":
            image_filename = image.filename

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    image_filename
                )
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO sarees
            (name, category, fabric, color, price, stock, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

        cursor.close()
        connection.close()

        return redirect(url_for("admin_sarees"))

    return render_template("admin/add_saree.html")

# -----------------------------
# ADMIN - EDIT SAREE
# -----------------------------
@app.route("/admin/sarees/edit/<int:saree_id>", methods=["GET", "POST"])
def edit_saree(saree_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!"

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM sarees
        WHERE id = %s
    """, (
        saree_id,
    ))

    saree = cursor.fetchone()

    if saree is None:
        cursor.close()
        connection.close()
        return "Saree not found!"

    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        fabric = request.form["fabric"]
        color = request.form["color"]
        price = request.form["price"]
        stock = request.form["stock"]
        description = request.form["description"]

        cursor.execute("""
            UPDATE sarees
            SET
                name = %s,
                category = %s,
                fabric = %s,
                color = %s,
                price = %s,
                stock = %s,
                description = %s
            WHERE id = %s
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

        cursor.close()
        connection.close()

        return redirect(url_for("admin_sarees"))

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!"

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM sarees
        WHERE id = %s
    """, (
        saree_id,
    ))

    saree = cursor.fetchone()

    if saree is None:
        cursor.close()
        connection.close()
        return "Saree not found!"

    cursor.execute("""
        DELETE FROM sarees
        WHERE id = %s
    """, (
        saree_id,
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_sarees"))

# -----------------------------
# ADMIN - MANAGE ORDERS
# -----------------------------
@app.route("/admin/orders")
def admin_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!"

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
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
    """)

    orders = cursor.fetchall()

    order_items = {}

    for order in orders:
        cursor.execute("""
            SELECT
                order_items.quantity,
                order_items.price,
                sarees.name,
                sarees.image
            FROM order_items
            JOIN sarees
            ON order_items.saree_id = sarees.id
            WHERE order_items.order_id = %s
        """, (
            order["id"],
        ))

        items = cursor.fetchall()

        order_items[order["id"]] = items

    cursor.close()
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
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
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = %s
        WHERE id = %s
    """, (
        status,
        order_id
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_orders"))

# -----------------------------
# RUN APPLICATION
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)