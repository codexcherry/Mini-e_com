import streamlit as st
import sqlite3
from datetime import datetime

# ---------------- DB ---------------- #
conn = sqlite3.connect("ecommerce.db", check_same_thread=False)
cur = conn.cursor()

def init_db():
    cur.execute("""CREATE TABLE IF NOT EXISTS products(
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        stock INTEGER
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS orders(
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TEXT,
        total_amount REAL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    )""")

    conn.commit()

init_db()

# ---------------- LOG ---------------- #
def log(msg):
    with open("logs.txt", "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

# ---------------- UI ---------------- #
st.set_page_config(page_title="Mini E-Commerce", layout="wide")

st.title("🛒 Mini E-Commerce Dashboard")

menu = st.sidebar.radio("Navigation", ["Dashboard", "Products", "Users", "Orders", "Reports"])

# ---------------- DASHBOARD ---------------- #
if menu == "Dashboard":
    st.subheader("📊 Dashboard Overview")
    
    # Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]
    
    cur.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cur.fetchone()[0] or 0
    
    col1.metric("📦 Total Products", total_products)
    col2.metric("👥 Total Users", total_users)
    col3.metric("🛒 Total Orders", total_orders)
    col4.metric("💰 Revenue", f"₹{total_revenue:.2f}")
    
    st.divider()
    
    # Charts Section
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.write("### 📈 Top 5 Selling Products")
        cur.execute("""
            SELECT p.name, SUM(oi.quantity) as total_qty
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY p.name
            ORDER BY total_qty DESC
            LIMIT 5
        """)
        top_products = cur.fetchall()
        
        if top_products:
            import pandas as pd
            df_top = pd.DataFrame(top_products, columns=["Product", "Quantity Sold"])
            st.bar_chart(df_top.set_index("Product"))
        else:
            st.info("No sales data available yet")
    
    with col_right:
        st.write("### 📊 Low Stock Alert")
        cur.execute("SELECT name, stock FROM products WHERE stock < 10 ORDER BY stock ASC")
        low_stock = cur.fetchall()
        
        if low_stock:
            for product, stock in low_stock:
                if stock == 0:
                    st.error(f"🔴 {product}: Out of Stock")
                elif stock < 5:
                    st.warning(f"🟡 {product}: {stock} units left")
                else:
                    st.info(f"🟢 {product}: {stock} units left")
        else:
            st.success("✅ All products have sufficient stock!")
    
    st.divider()
    
    # Recent Activity
    st.write("### 🕒 Recent Orders")
    cur.execute("""
        SELECT o.order_id, u.name, o.order_date, o.total_amount
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_id DESC
        LIMIT 5
    """)
    recent_orders = cur.fetchall()
    
    if recent_orders:
        import pandas as pd
        df_orders = pd.DataFrame(recent_orders, columns=["Order ID", "Customer", "Date", "Amount (₹)"])
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.info("No orders placed yet")
    
    # Quick Stats
    st.divider()
    st.write("### 📋 Quick Statistics")
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    
    with stat_col1:
        cur.execute("SELECT AVG(total_amount) FROM orders")
        avg_order = cur.fetchone()[0] or 0
        st.metric("Average Order Value", f"₹{avg_order:.2f}")
    
    with stat_col2:
        cur.execute("SELECT SUM(stock) FROM products")
        total_inventory = cur.fetchone()[0] or 0
        st.metric("Total Inventory Items", total_inventory)
    
    with stat_col3:
        cur.execute("SELECT COUNT(*) FROM products WHERE stock = 0")
        out_of_stock = cur.fetchone()[0]
        st.metric("Out of Stock Products", out_of_stock)

# ---------------- PRODUCTS ---------------- #
elif menu == "Products":
    st.subheader("📦 Product Management")

    with st.form("add_product"):
        st.write("### Add New Product")
        name = st.text_input("Name")
        price = st.number_input("Price", 0.0)
        stock = st.number_input("Stock", 0)

        if st.form_submit_button("Add"):
            try:
                cur.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
                conn.commit()
                log(f"Added product {name}")
                st.success("Product Added")
            except:
                st.error("Product already exists")

    st.divider()

    st.write("### Product List")
    cur.execute("SELECT * FROM products")
    st.dataframe(cur.fetchall())

# ---------------- USERS ---------------- #
elif menu == "Users":
    st.subheader("👤 User Management")

    with st.form("add_user"):
        name = st.text_input("Name")
        email = st.text_input("Email")

        if st.form_submit_button("Add User"):
            cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            conn.commit()
            log(f"Added user {name}")
            st.success("User Added")

    st.divider()

    cur.execute("SELECT * FROM users")
    st.dataframe(cur.fetchall())

# ---------------- ORDERS ---------------- #
elif menu == "Orders":
    st.subheader("🛒 Place Order")

    cur.execute("SELECT user_id, name FROM users")
    users = cur.fetchall()

    if not users:
        st.warning("No users available")
    else:
        user_map = {f"{u[1]} (ID:{u[0]})": u[0] for u in users}
        selected_user = st.selectbox("Select User", list(user_map.keys()))
        user_id = user_map[selected_user]

        cur.execute("SELECT product_id, name, stock, price FROM products")
        products = cur.fetchall()

        selected_items = []

        for p in products:
            col1, col2 = st.columns([3,1])
            col1.write(f"{p[1]} | ₹{p[3]} | Stock: {p[2]}")
            qty = col2.number_input("Qty", 0, key=p[0])

            if qty > 0:
                selected_items.append((p, qty))

        if st.button("Place Order"):
            total = 0
            valid = True

            for item in selected_items:
                if item[1] > item[0][2]:
                    valid = False
                    st.error(f"Not enough stock: {item[0][1]}")

            if valid and selected_items:
                cur.execute("INSERT INTO orders (user_id, order_date, total_amount) VALUES (?, ?, ?)",
                            (user_id, datetime.now().strftime("%Y-%m-%d"), 0))
                order_id = cur.lastrowid

                for item in selected_items:
                    p, qty = item
                    total += qty * p[3]

                    cur.execute("INSERT INTO order_items VALUES (NULL, ?, ?, ?, ?)",
                                (order_id, p[0], qty, p[3]))

                    cur.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?",
                                (qty, p[0]))

                cur.execute("UPDATE orders SET total_amount=? WHERE order_id=?", (total, order_id))
                conn.commit()

                log(f"Order {order_id} placed")
                st.success(f"Order placed successfully! Total ₹{total}")

    st.divider()
    st.write("### Order History")

    cur.execute("""
    SELECT o.order_id, u.name, o.total_amount
    FROM orders o JOIN users u ON o.user_id = u.user_id
    """)
    st.dataframe(cur.fetchall())

# ---------------- REPORTS ---------------- #
elif menu == "Reports":
    st.subheader("📊 Reports")

    st.write("### Top Selling Products")

    cur.execute("""
    SELECT p.name, SUM(oi.quantity)
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.name
    ORDER BY SUM(oi.quantity) DESC
    """)

    st.dataframe(cur.fetchall())

    st.write("### Revenue")

    cur.execute("SELECT SUM(total_amount) FROM orders")
    revenue = cur.fetchone()[0]
    st.metric("Total Revenue", f"₹{revenue if revenue else 0}")