from functools import wraps
from io import BytesIO
import os
import shutil

from flask import Flask, flash, redirect, render_template, request, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from base import (
    add_new_product,
    authenticate_user,
    create_order,
    create_user,
    get_all_orders,
    get_all_products,
    get_user_by_id,
    get_user_by_username,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shop-secret-key-2026")

FILE_PATH = os.path.join(os.getcwd(), "static", "img")
os.makedirs(FILE_PATH, exist_ok=True)

ROOT_IMG_PATH = os.path.join(os.getcwd(), "img")
if os.path.exists(ROOT_IMG_PATH):
    for file_name in os.listdir(ROOT_IMG_PATH):
        src = os.path.join(ROOT_IMG_PATH, file_name)
        dst = os.path.join(FILE_PATH, file_name)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy(src, dst)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("You need to log in to access this page.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_user():
    user = None
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
    return {"current_user": user}


@app.route("/")
def main_handler():
    return render_template("main.html")


@app.route("/products")
def products_handler():
    products = get_all_products()
    return render_template("products.html", products=products)


@app.route("/orders")
@login_required
def orders_handler():
    orders = get_all_orders()
    return render_template("orders.html", orders=orders)


@app.route("/make_order", methods=["GET", "POST"])
@login_required
def make_order():
    if request.method == "POST":
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        product_id = request.form.get("product_id")

        if not email or not phone_number or not product_id:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("make_order"))

        try:
            create_order(email=email, phone_number=int(phone_number), product_id=int(product_id))
            flash("Order created successfully!", "success")
            return redirect(url_for("products_handler"))
        except Exception as e:
            flash(f"Error creating order: {e}", "danger")
            return redirect(url_for("make_order"))

    selected_id = request.args.get("product_id", type=int)
    products = get_all_products()
    return render_template("make_order.html", products=products, selected_id=selected_id)


@app.route("/add_new_product", methods=["GET"])
@login_required
def add_new_product_page():
    return render_template("add_new_product.html")


@app.route("/add_new_product/", methods=["POST"])
@login_required
def add_new_product_route():
    image = request.files.get("image")
    if not image or image.filename == "":
        return "No file", 400

    image_data = image.read()
    if len(image_data) > 10 * 1024 ** 2:
        return "File size reached allowed limit."

    try:
        with Image.open(BytesIO(image_data)) as uploaded_image:
            image_type = uploaded_image.format
    except UnidentifiedImageError:
        return "Wrong image type"

    if image_type not in ["PNG", "JPEG"]:
        return "Wrong image type"

    image_name = secure_filename(image.filename)
    if not image_name:
        return "Wrong image filename"

    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")
    image_path = os.path.join(FILE_PATH, image_name)
    image.seek(0)
    image.save(image_path)

    try:
        add_new_product(
            name=name,
            description=description,
            price=float(price),
            image_filename=f"img/{image_name}",
        )
    except Exception as e:
        return f"Database error: {e}", 500

    flash("Product added successfully!", "success")
    return redirect(url_for("products_handler"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Username and password are required.", "danger")
        return render_template("register.html")

    if get_user_by_username(username):
        flash("This username is already registered.", "warning")
        return render_template("register.html")

    try:
        create_user(username, password)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    except Exception as e:
        flash(f"Registration error: {e}", "danger")
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = authenticate_user(username, password)

    if user:
        session["user_id"] = user.id
        session["username"] = user.name
        flash("You are logged in successfully.", "success")
        return redirect(url_for("main_handler"))

    flash("Invalid username or password.", "danger")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    flash("You have logged out.", "info")
    return redirect(url_for("main_handler"))


if __name__ == "__main__":
    app.run(debug=True)
