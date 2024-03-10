import os
import random

from flask import Flask, session
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for

from datetime import datetime, timedelta
import time
import mysql.connector
from mysql.connector import FieldType
from werkzeug.utils import secure_filename

import connect
from flask_hashing import Hashing

from utils import get_random_string

app = Flask(__name__)

dbconn = None
connection = None

app.secret_key = 'your secret key'
salt = "abcd"
hashing = Hashing(app)


def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser,
                                         password=connect.dbpass, host=connect.dbhost,
                                         database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn


@app.route('/')
def index():
    connection = getCursor()
    connection.execute('SELECT * FROM pest_guide')
    pest_guide_list = connection.fetchall()
    return render_template("index.html", pest_guide_list=pest_guide_list)


@app.route('/guide_detail/')
def guide_detail():
    guide_id = request.args.get("guide_id")
    connection = getCursor()
    connection.execute('SELECT * FROM pest_guide WHERE animal_id={}'.format(guide_id))
    pest_guide = connection.fetchone()

    connection.execute('SELECT * FROM pest_image WHERE pest_guide_id={}'.format(guide_id))
    pest_image_list = connection.fetchall()

    return render_template("pest_guide.html", pest_guide=pest_guide, pest_image_list=pest_image_list)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        address = request.form.get("address")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if first_name is None or last_name is None or address is None or email is None or phone_number is None or password1 is None or password2 is None:
            msg = 'Please fill in all the information!'
            return render_template("register.html", msg=msg)

        if password1 != password2:
            msg = "Password inconsistency!"
            return render_template("register.html", msg=msg)

        connection = getCursor()
        connection.execute('SELECT * FROM pest_controller WHERE email = "{}"'.format(email))
        account = connection.fetchone()
        if account:
            msg = 'Email already exists!'
            return render_template("register.html", msg=msg)

        connection.execute('SELECT * FROM pest_controller WHERE phone_number = "{}"'.format(phone_number))
        account = connection.fetchone()
        if account:
            msg = 'Phone number already exists!'
            return render_template("register.html", msg=msg)

        hashed = hashing.hash_value(password1, salt=salt)

        insert = "INSERT INTO pest_controller(first_name,last_name,address,email,phone_number,password,date_joined,status) " \
                 "VALUES('{}','{}','{}','{}','{}','{}','{}',{})" \
            .format(first_name, last_name, address, email, phone_number, hashed, datetime.now(), 1)
        connection.execute(insert)

        msg = "Registration is successful, please go to the login page to login!"
        return render_template("register.html", msg=msg)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        user_type = request.form.get("user_type")
        email = request.form.get("email")
        password = request.form.get("password")

        if email is None or password is None or user_type is None:
            msg = 'Please fill in all the information!'
            return render_template("login.html", msg=msg)
        # 1 Pest Controller \ 2 Staff \ 3 Administrator
        connection = getCursor()
        if str(user_type) == '1':
            connection.execute('SELECT * FROM pest_controller WHERE email = "{}" and password = "{}"'
                               .format(email, hashing.hash_value(password, salt=salt)))
        elif str(user_type) == '2':
            connection.execute('SELECT * FROM staff WHERE email = "{}" and password = "{}"'
                               .format(email, hashing.hash_value(password, salt=salt)))
        elif str(user_type) == '3':
            connection.execute('SELECT * FROM admin WHERE email = "{}" and password = "{}"'
                               .format(email, hashing.hash_value(password, salt=salt)))
        else:
            msg = 'User type Error!'
            return render_template("login.html", msg=msg)

        account = connection.fetchone()
        if account is None:
            msg = 'The account or password is incorrect!'
            return render_template("login.html", msg=msg)

        session['loggedin'] = True
        session['role'] = user_type
        session['userId'] = account[0]
        session['username'] = account[1]
        if str(user_type) == '2' or str(user_type) == '3':
            return redirect("/index_admin")
        else:
            return redirect("/")


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect("/")


@app.route('/my_information/', methods=['GET', 'POST'])
def my_information():
    if request.method == "GET":
        user_type = request.args.get("userType")
        user_id = request.args.get("userId")

        if user_type is None or user_id is None:
            return redirect("/")

        connection = getCursor()
        if str(user_type) == '1':
            connection.execute('SELECT * FROM pest_controller WHERE id_number = "{}"'.format(user_id))
        elif str(user_type) == '2':
            connection.execute('SELECT * FROM staff WHERE staff_number = "{}"'.format(user_id))
        elif str(user_type) == '3':
            connection.execute('SELECT * FROM admin WHERE staff_number = "{}"'.format(user_id))
        else:
            return redirect("/")
        account = connection.fetchone()
        if str(user_type) == '1':
            return render_template("my_information.html", account=account, user_type=user_type)
        else:
            return render_template("admin/my_information_admin.html", account=account, user_type=user_type)

    else:
        user_type = request.form.get("user_type")
        user_id = request.form.get("user_id")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        address = request.form.get("address")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")

        if user_id is None or first_name is None or last_name is None or address is None or email is None or phone_number is None:
            connection = getCursor()
            connection.execute('SELECT * FROM pest_controller WHERE id_number = {}'.format(user_id))
            account = connection.fetchone()
            msg = 'Please fill in all the information!'
            return render_template("my_information.html", msg=msg, user_type=user_type, account=account)

        connection = getCursor()
        connection.execute('SELECT * FROM pest_controller WHERE id_number = {}'.format(user_id))
        account = connection.fetchone()
        if account is None:
            msg = 'Account does not exist!'
            return render_template("my_information.html", msg=msg, account=account, user_type=user_type)

        connection.execute(
            'UPDATE pest_controller SET first_name="{}", last_name="{}", address="{}", email="{}", phone_number="{}" WHERE id_number={}'
                .format(first_name, last_name, address, email, phone_number, user_id))

        connection.execute('SELECT * FROM pest_controller WHERE id_number = {}'.format(user_id))
        account = connection.fetchone()

        msg = "Update Success!"
        return render_template("my_information.html", account=account, msg=msg, user_type=user_type)


@app.route('/update_password/', methods=['GET', 'POST'])
def update_password():
    if request.method == "GET":
        user_type = request.args.get("userType")
        user_id = request.args.get("userId")

        if user_type is None or user_id is None:
            return redirect("/")
        if str(user_type) == '1':
            return render_template("update_password.html", user_id=user_id, user_type=user_type)
        else:
            return render_template("admin/update_password_admin.html", user_id=user_id, user_type=user_type)

    else:
        user_type = request.form.get("user_type")
        user_id = request.form.get("user_id")
        old_password = request.form.get("old_password")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if user_id is None or user_type is None or password1 is None or password2 is None:
            msg = 'Please fill in all the information!'
            return render_template("update_password.html", msg=msg, user_id=user_id, user_type=user_type)

        if password1 != password2:
            msg = "Password inconsistency!"
            return render_template("update_password.html", msg=msg, user_id=user_id, user_type=user_type)

        connection = getCursor()
        connection.execute('SELECT * FROM pest_controller WHERE id_number = {} and password = "{}"'.format(user_id,
                                                                                                           hashing.hash_value(
                                                                                                               old_password,
                                                                                                               salt=salt)))
        account = connection.fetchone()
        if account is None:
            msg = 'Old password is incorrect!'
            return render_template("update_password.html", msg=msg, user_id=user_id, user_type=user_type)

        connection.execute(
            'UPDATE pest_controller SET password="{}" WHERE id_number={}'
                .format(hashing.hash_value(password1, salt=salt), user_id))

        connection.execute('SELECT * FROM pest_controller WHERE id_number = {}'.format(user_id))
        account = connection.fetchone()

        msg = "Update Success!"
        return render_template("update_password.html", account=account, msg=msg, user_id=user_id, user_type=user_type)


# ---------------
@app.route('/index_admin/')
def index_admin():
    if session.get('role') != '2' and session.get('role') != '3':
        return redirect("/")

    connection = getCursor()
    connection.execute('SELECT * FROM pest_guide')
    pest_guide_list = connection.fetchall()
    return render_template("admin/index_admin.html", pest_guide_list=pest_guide_list)


@app.route('/add_pest_guide/', methods=['GET', 'POST'])
def add_pest_guide():
    if request.method == "GET":
        return render_template("admin/add_pest_guide.html")
    else:
        animal_name = request.form.get("animal_name")
        description = request.form.get("description")
        distribution = request.form.get("distribution")
        size = request.form.get("size")
        droppings = request.form.get("droppings")
        foot_prints = request.form.get("foot_prints")
        impacts = request.form.get("impacts")
        control_methods = request.form.get("control_methods")

        if request.files.__len__() == 0:
            msg = 'No selected image!'
            return render_template("admin/add_pest_guide.html", msg=msg)

        image_file = request.files['primary_image']
        if animal_name is None or description is None \
                or distribution is None or size is None or droppings is None \
                or foot_prints is None or impacts is None or control_methods is None:
            msg = 'Please fill in all the information!'
            return render_template("admin/add_pest_guide.html", msg=msg)

        if image_file is None or image_file.filename == '':
            msg = 'No selected image!'
            return render_template("admin/add_pest_guide.html", msg=msg)

        dot_idx = image_file.filename.find(".")
        filename = str(int(time.time())) + "_" + str(get_random_string()) + image_file.filename[dot_idx:]
        filename = secure_filename(filename)
        image_file.save(os.path.join('static/upload/', filename))
        print("file upload successfully ：" + str(filename))

        animal_name = animal_name.replace("'", "").replace('"', "")
        description = description.replace("'", "").replace('"', "")
        distribution = distribution.replace("'", "").replace('"', "")
        size = size.replace("'", "").replace('"', "")
        droppings = droppings.replace("'", "").replace('"', "")
        foot_prints = foot_prints.replace("'", "").replace('"', "")
        impacts = impacts.replace("'", "").replace('"', "")
        control_methods = control_methods.replace("'", "").replace('"', "")

        connection = getCursor()
        insert = "INSERT INTO pest_guide(animal_name,description,distribution,size,droppings,foot_prints,impacts,control_methods,primary_image) " \
                 "VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}')" \
            .format(animal_name, description, distribution, size, droppings, foot_prints,
                    impacts, control_methods, filename)
        connection.execute(insert)

        msg = "Add successfully! To add more images please go to the list page!"
        return render_template("admin/add_pest_guide.html", msg=msg)


@app.route('/edit_pest_guide/', methods=['GET', 'POST'])
def edit_pest_guide():
    if request.method == "GET":
        guide_id = request.args.get("guide_id")
        if guide_id is None:
            return redirect("/admin_index")

        connection = getCursor()
        connection.execute('SELECT * FROM pest_guide WHERE animal_id={}'.format(guide_id))
        pest_guide = connection.fetchone()
        return render_template("admin/edit_pest_guide.html", pest_guide=pest_guide)
    else:
        animal_id = request.form.get("animal_id")
        animal_name = request.form.get("animal_name")
        description = request.form.get("description")
        distribution = request.form.get("distribution")
        size = request.form.get("size")
        droppings = request.form.get("droppings")
        foot_prints = request.form.get("foot_prints")
        impacts = request.form.get("impacts")
        control_methods = request.form.get("control_methods")

        if animal_name is None or description is None \
                or distribution is None or size is None or droppings is None \
                or foot_prints is None or impacts is None or control_methods is None:
            msg = 'Please fill in all the information!'
            return render_template("admin/add_pest_guide.html", msg=msg)

        filename = None
        if request.files.__len__() != 0:
            image_file = request.files['primary_image']
            dot_idx = image_file.filename.find(".")
            filename = str(int(time.time())) + "_" + str(get_random_string()) + image_file.filename[dot_idx:]
            filename = secure_filename(filename)
            image_file.save(os.path.join('static/upload/', filename))
            print("file upload successfully ：" + str(filename))

        animal_name = animal_name.replace("'", "").replace('"', "")
        description = description.replace("'", "").replace('"', "")
        distribution = distribution.replace("'", "").replace('"', "")
        size = size.replace("'", "").replace('"', "")
        droppings = droppings.replace("'", "").replace('"', "")
        foot_prints = foot_prints.replace("'", "").replace('"', "")
        impacts = impacts.replace("'", "").replace('"', "")
        control_methods = control_methods.replace("'", "").replace('"', "")

        connection = getCursor()
        if filename is None:
            update = 'UPDATE pest_guide SET animal_name="{}", description="{}", distribution="{}", size="{}",' \
                     ' droppings="{}", foot_prints="{}", impacts="{}", control_methods="{}" WHERE animal_id = {}' \
                .format(animal_name, description, distribution, size, droppings, foot_prints,
                        impacts, control_methods, animal_id)
            connection.execute(update)
        else:
            update = 'UPDATE pest_guide SET animal_name="{}", description="{}", distribution="{}", size="{}",' \
                     ' droppings="{}", foot_prints="{}", impacts="{}", control_methods="{}",primary_image="{}"  WHERE animal_id = {}' \
                .format(animal_name, description, distribution, size, droppings, foot_prints,
                        impacts, control_methods, filename, animal_id)
            connection.execute(update)

        msg = "Update successfully! To add more images please go to the list page!"
        connection = getCursor()
        connection.execute('SELECT * FROM pest_guide WHERE animal_id={}'.format(animal_id))
        pest_guide = connection.fetchone()
        return render_template("admin/edit_pest_guide.html", pest_guide=pest_guide, msg=msg)


@app.route('/pest_guide_image_edit/', methods=['GET', 'POST'])
def pest_guide_image_edit():
    if request.method == "GET":
        guide_id = request.args.get("guide_id")
        if guide_id is None:
            return redirect("/admin_index")

        connection = getCursor()
        connection.execute('SELECT * FROM pest_image WHERE pest_guide_id={}'.format(guide_id))
        pest_image_list = connection.fetchall()

        connection.execute('SELECT * FROM pest_guide WHERE animal_id={}'.format(guide_id))
        pest_guide = connection.fetchone()

        return render_template("admin/pest_guide_image_edit.html", pest_guide=pest_guide,
                               pest_image_list=pest_image_list)
    else:
        animal_id = request.form.get("animal_id")
        if request.files.__len__() == 0:
            msg = 'No selected image!'
            return redirect("/pest_guide_image_edit/?guide_id=" + str(animal_id))

        image_file = request.files['primary_image']

        if animal_id is None:
            return redirect("/admin_index")

        if image_file is None or image_file.filename == '':
            msg = 'No selected image!'
            return redirect("/pest_guide_image_edit/?guide_id=" + str(animal_id))

        dot_idx = image_file.filename.find(".")
        filename = str(int(time.time())) + "_" + str(get_random_string()) + image_file.filename[dot_idx:]
        filename = secure_filename(filename)
        image_file.save(os.path.join('static/upload/', filename))
        print("file upload successfully ：" + str(filename))

        connection = getCursor()
        insert = "INSERT INTO pest_image(image_path,pest_guide_id) VALUES('{}','{}')".format(filename, animal_id)
        connection.execute(insert)
        return redirect("/pest_guide_image_edit/?guide_id=" + str(animal_id))


@app.route('/delete_other_image/', methods=['GET', 'POST'])
def delete_other_image():
    image_id = request.args.get("image_id")
    animal_id = request.args.get("animal_id")
    if image_id is None:
        return redirect("/admin_index")
    connection = getCursor()
    delete = "DELETE FROM pest_image WHERE id={}".format(image_id)
    connection.execute(delete)
    return redirect("/pest_guide_image_edit/?guide_id=" + str(animal_id))


@app.route('/pest_controller_list/', methods=['GET', 'POST'])
def pest_controller_list():
    connection = getCursor()
    connection.execute('SELECT * FROM pest_controller')
    pest_controller_list = connection.fetchall()
    return render_template("admin/pest_controller_list.html", pest_controller_list=pest_controller_list)


@app.route('/delete_pest_controller/', methods=['GET', 'POST'])
def delete_pest_controller():
    id = request.args.get("id")
    if id is None:
        return redirect("/pest_controller_list")
    connection = getCursor()
    delete = "DELETE FROM pest_controller WHERE id_number={}".format(id)
    connection.execute(delete)
    return redirect("/pest_controller_list/")


@app.route('/edit_pest_controller/', methods=['GET', 'POST'])
def edit_pest_controller():
    if request.method == "GET":
        id = request.args.get("id")
        if id is None:
            return redirect("/pest_controller_list")
        connection = getCursor()
        connection.execute('SELECT * FROM pest_controller WHERE id_number={}'.format(id))
        pest_controller = connection.fetchone()
        return render_template("admin/edit_pest_controller.html", pest_controller=pest_controller)
    else:
        id_number = request.form.get("id_number")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        address = request.form.get("address")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        status = request.form.get("status")

        if id_number is None or first_name is None or last_name is None or address is None \
                or email is None or phone_number is None or status is None:
            connection = getCursor()
            connection.execute('SELECT * FROM pest_controller WHERE id_number={}'.format(id_number))
            pest_controller = connection.fetchone()
            msg = 'Please fill in all the information!'
            return render_template("admin/edit_pest_controller.html", msg=msg, pest_controller=pest_controller)

        connection = getCursor()
        connection.execute(
            'UPDATE pest_controller SET first_name="{}", last_name="{}", address="{}", email="{}", phone_number="{}", status={} WHERE id_number={}'
                .format(first_name, last_name, address, email, phone_number, status, id_number))

        connection.execute('SELECT * FROM pest_controller WHERE id_number = {}'.format(id_number))
        pest_controller = connection.fetchone()

        msg = "Update Success!"
        return render_template("admin/edit_pest_controller.html", msg=msg, pest_controller=pest_controller)


@app.route('/add_pest_controller/', methods=['GET', 'POST'])
def add_pest_controller():
    if request.method == "GET":
        return render_template("admin/add_pest_controller.html")
    else:
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        address = request.form.get("address")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        status = request.form.get("status")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if first_name is None or last_name is None or address is None or email is None or phone_number is None \
                or password1 is None or password2 is None or status is None:
            msg = 'Please fill in all the information!'
            return render_template("admin/add_pest_controller.html", msg=msg)

        if password1 != password2:
            msg = "Password inconsistency!"
            return render_template("admin/add_pest_controller.html", msg=msg)

        connection = getCursor()
        connection.execute('SELECT * FROM pest_controller WHERE email = "{}"'.format(email))
        account = connection.fetchone()
        if account:
            msg = 'Email already exists!'
            return render_template("admin/add_pest_controller.html", msg=msg)

        connection.execute('SELECT * FROM pest_controller WHERE phone_number = "{}"'.format(phone_number))
        account = connection.fetchone()
        if account:
            msg = 'Phone number already exists!'
            return render_template("admin/add_pest_controller.html", msg=msg)

        hashed = hashing.hash_value(password1, salt=salt)

        insert = "INSERT INTO pest_controller(first_name,last_name,address,email,phone_number,password,date_joined,status) " \
                 "VALUES('{}','{}','{}','{}','{}','{}','{}',{})" \
            .format(first_name, last_name, address, email, phone_number, hashed, datetime.now(), status)
        connection.execute(insert)

        msg = "Add Pest Controller successful!"
        return render_template("admin/add_pest_controller.html", msg=msg)


@app.route('/staff_list/', methods=['GET', 'POST'])
def staff_list():
    connection = getCursor()
    connection.execute('SELECT * FROM staff')
    staff_list = connection.fetchall()
    return render_template("admin/staff_list.html", staff_list=staff_list)


@app.route('/delete_staff/', methods=['GET', 'POST'])
def delete_staff():
    id = request.args.get("id")
    if id is None:
        return redirect("/staff_list")
    connection = getCursor()
    delete = "DELETE FROM staff WHERE staff_number={}".format(id)
    connection.execute(delete)
    return redirect("/staff_list/")


@app.route('/edit_staff/', methods=['GET', 'POST'])
def edit_staff():
    if request.method == "GET":
        id = request.args.get("id")
        if id is None:
            return redirect("/staff_list")
        connection = getCursor()
        connection.execute('SELECT * FROM staff WHERE staff_number={}'.format(id))
        staff = connection.fetchone()
        return render_template("admin/edit_staff.html", staff=staff)
    else:
        staff_number = request.form.get("staff_number")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        position = request.form.get("position")
        department = request.form.get("position")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        status = request.form.get("status")

        if staff_number is None or first_name is None or last_name is None or position is None \
                or email is None or phone_number is None or status is None or department is None:
            connection = getCursor()
            connection.execute('SELECT * FROM staff WHERE staff_number={}'.format(staff_number))
            staff = connection.fetchone()
            msg = 'Please fill in all the information!'
            return render_template("admin/edit_staff.html", msg=msg, staff=staff)

        connection = getCursor()
        connection.execute(
            'UPDATE staff SET first_name="{}", last_name="{}", position="{}",department="{}", email="{}", phone_number="{}", status={} WHERE staff_number={}'
                .format(first_name, last_name, position, department, email, phone_number, status, staff_number))

        connection.execute('SELECT * FROM staff WHERE staff_number = {}'.format(staff_number))
        staff = connection.fetchone()

        msg = "Update Success!"
        return render_template("admin/edit_staff.html", msg=msg, staff=staff)


@app.route('/add_staff/', methods=['GET', 'POST'])
def add_staff():
    if request.method == "GET":
        return render_template("admin/add_staff.html")
    else:
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        position = request.form.get("position")
        department = request.form.get("department")
        status = request.form.get("status")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if first_name is None or last_name is None or position is None or email is None or phone_number is None \
                or password1 is None or password2 is None or status is None or department is None:
            msg = 'Please fill in all the information!'
            return render_template("admin/add_staff.html", msg=msg)

        if password1 != password2:
            msg = "Password inconsistency!"
            return render_template("admin/add_staff.html", msg=msg)

        connection = getCursor()
        connection.execute('SELECT * FROM staff WHERE email = "{}"'.format(email))
        account = connection.fetchone()
        if account:
            msg = 'Email already exists!'
            return render_template("admin/add_staff.html", msg=msg)

        connection.execute('SELECT * FROM staff WHERE phone_number = "{}"'.format(phone_number))
        account = connection.fetchone()
        if account:
            msg = 'Phone number already exists!'
            return render_template("admin/add_staff.html", msg=msg)

        hashed = hashing.hash_value(password1, salt=salt)

        insert = "INSERT INTO staff(first_name,last_name,email,phone_number,position,department ,password,hire_date,status) " \
                 "VALUES('{}','{}','{}','{}','{}','{}','{}','{}',{})" \
            .format(first_name, last_name, email, phone_number, position, department, hashed, datetime.now(), status)
        connection.execute(insert)

        msg = "Add Staff successful!"
        return render_template("admin/add_staff.html", msg=msg)


@app.route('/my_information_admin/', methods=['POST'])
def my_information_admin():
    if request.method == "POST":
        user_type = request.form.get("user_type")
        staff_number = request.form.get("staff_number")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        position = request.form.get("position")
        department = request.form.get("department")

        if user_type is None or first_name is None or last_name is None or staff_number is None or email is None \
                or phone_number is None or position is None or department is None:
            account = None
            if user_type == '2':
                connection = getCursor()
                connection.execute('SELECT * FROM staff WHERE id_number = {}'.format(staff_number))
                account = connection.fetchone()
            elif user_type == '3':
                connection = getCursor()
                connection.execute('SELECT * FROM admin WHERE id_number = {}'.format(staff_number))
                account = connection.fetchone()
            else:
                return redirect("/index_admin/")
            msg = 'Please fill in all the information!'
            return render_template("admin/my_information_admin.html", msg=msg, user_type=user_type, account=account)

        connection = getCursor()
        if user_type == '2':
            connection.execute(
                'UPDATE staff SET first_name="{}", last_name="{}", email="{}", phone_number="{}", position="{}", department="{}" WHERE staff_number={}'
                    .format(first_name, last_name, email, phone_number, position, department, staff_number))
        elif user_type == '3':
            connection.execute(
                'UPDATE admin SET first_name="{}", last_name="{}", email="{}", phone_number="{}", position="{}", department="{}" WHERE staff_number={}'
                    .format(first_name, last_name, email, phone_number, position, department, staff_number))
        else:
            return redirect("/index_admin/")
        connection.execute('SELECT * FROM staff WHERE staff_number = {}'.format(staff_number))
        account = connection.fetchone()

        msg = "Update Success!"
        return render_template("admin/my_information_admin.html", account=account, msg=msg, user_type=user_type)


@app.route('/update_password_admin/', methods=['POST'])
def update_password_admin():
    if request.method == "POST":
        user_type = request.form.get("user_type")
        user_id = request.form.get("user_id")
        old_password = request.form.get("old_password")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if user_id is None or user_type is None or password1 is None or password2 is None:
            msg = 'Please fill in all the information!'
            return render_template("admin/update_password_admin.html", msg=msg, user_id=user_id, user_type=user_type)

        if password1 != password2:
            msg = "Password inconsistency!"
            return render_template("admin/update_password_admin.html", msg=msg, user_id=user_id, user_type=user_type)

        connection = getCursor()

        if user_type == '2':
            connection.execute('SELECT * FROM staff WHERE staff_number = {} and password = "{}"'
                               .format(user_id, hashing.hash_value(old_password, salt=salt)))
        elif user_type == '3':
            connection.execute('SELECT * FROM admin WHERE staff_number = {} and password = "{}"'
                               .format(user_id, hashing.hash_value(old_password, salt=salt)))
        else:
            return redirect("/index_admin/")

        account = connection.fetchone()
        if account is None:
            msg = 'Old password is incorrect!'
            return render_template("admin/update_password_admin.html", msg=msg, user_id=user_id, user_type=user_type)

        if user_type == '2':
            connection.execute('UPDATE staff SET password="{}" WHERE staff_number={}'
                               .format(hashing.hash_value(password1, salt=salt), user_id))
        elif user_type == '3':
            connection.execute('UPDATE admin SET password="{}" WHERE staff_number={}'
                               .format(hashing.hash_value(password1, salt=salt), user_id))
        else:
            return redirect("/index_admin/")

        if user_type == '2':
            connection.execute('SELECT * FROM staff WHERE staff_number = {}'.format(user_id))
        elif user_type == '3':
            connection.execute('SELECT * FROM admin WHERE staff_number = {}'.format(user_id))
        account = connection.fetchone()

        msg = "Update Success!"
        return render_template("admin/update_password_admin.html", account=account, msg=msg, user_id=user_id,
                               user_type=user_type)


if __name__ == '__main__':
    app.run()
