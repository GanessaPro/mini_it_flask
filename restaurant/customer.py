from flask import Blueprint, render_template ,request ,redirect, url_for, flash, current_app,session ,send_from_directory, send_file
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import os

from .models import Menu,User,Transactions,Orders
from . import db
from .pdfmodel import Invoice


customer = Blueprint('customer', __name__)

UPLOAD_FOLDER_1 = './restaurant/static/receipts'
UPLOAD_FOLDER = './static/receipts'

# @customer.route("/base")
# def customer_base_page():
#     return render_template("customer_base.html")


@customer.route("/customer_settings")
def customer_settings():
    currentusername = session['username']
    id = session['user_id']
    user = User.query.filter_by(id=id).first()
    fullname = user.fullname
    email = user.email
    phonenum = user.phonenum
    gender = user.gender
    role = user.role
    return render_template("customer_settings.html",currentusername = session['username'], currentuserid = session['user_id'], email = email, fullname=fullname, phonenum=phonenum,gender=gender)


@customer.route('/change_settings/<int:currentuserid>', methods=['POST'])
def change_credentials(currentuserid):
    user = User.query.get(currentuserid)
    if request.form.get('action') == 'change_credentials':
        customer_username = request.form.get('username')
        customer_pass = generate_password_hash(request.form.get('password'), method='pbkdf2:sha1', salt_length=8)
        print(customer_username, customer_pass,user)

        tempuser = User.query.filter_by(username=customer_username).first()
        print(tempuser)

        if tempuser is not None:
            if user.id != tempuser.id:
                print('Username already taken')
                flash('Username already taken')
                return redirect(url_for('customer.customer_settings'))

        if user.username != customer_username:
            user.username = customer_username
            print(user.username)
             
        
        user.password = customer_pass
        db.session.commit()
        return redirect(url_for('main.index'))

    elif request.form.get('action') == 'terminate_account':
        # Code to deactivate or terminate account goes here
        print(user,"account terminated")
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('main.index'))


@customer.route("/main_page_customer")
def main_page_customer():
    print('Current user is', current_user)
    print('Is user authenticated ', current_user.is_authenticated)
    menus = Menu.query.all()
    return render_template("main_page_customer.html", menus=menus)

@customer.route("/add_to_cart")
def add_to_cart():
    #Get transaction id
    query = None
    
    totalprice = 0
    quantity = 0

    try:
        # Get transaction id
        current_trx_id = session['trx_id']
        print("This is current", current_trx_id)
        query = db.session.query(Orders, Menu).join( Menu).filter(Orders.trxid == current_trx_id)
        for q,s in query:
            totalprice += q.quantity*s.priceperunit
            quantity += q.quantity

    except KeyError:
        flash('No menu items in the cart')
        print("Transaction ID does not exist.")
        current_trx_id = None
        
    return render_template("add_to_cart.html", menus = query, totalprice = totalprice, quantity = quantity,current_trx_id = current_trx_id)

@customer.route("/add_to_cart", methods=['POST'])
def cart_recalculate():

    try:
        orders = Orders.query.filter_by(trxid=session['trx_id']).all()
        print(orders)
        for order in orders:
            order.quantity = request.form.get(str(order.id))
            print(order.quantity)
        db.session.commit()
    except KeyError: 
        flash('The cart is empty')
        print("Please add a menu to calculate.")

    return redirect(url_for('customer.add_to_cart'))
   
@customer.route('/addtocartbtn/<menu_id>')
def addtocartbtn(menu_id):
    id = menu_id
    added_menu = Menu.query.get(id)
    #print(session['user_id'])
    #print(session['trx_id'])
    if 'trx_id' not in session:
        new_transaction = Transactions( customer_id=session['user_id'], payment_method="None",order_date= date.today(),delivery_address="None")
        db.session.add(new_transaction)
        db.session.commit()
        session['trx_id'] = new_transaction.id
        print('Session trans id',session['trx_id'])
        first_order = Orders( trxid=session['trx_id'],menu_id = id,quantity=1)
        db.session.add(first_order)
        db.session.commit()
    # add the new user to the database
    else:
        print(id,session['trx_id'])
        further_orders = Orders( trxid=session['trx_id'],menu_id = id,quantity=1)
        db.session.add(further_orders)
        db.session.commit()

    #return render_template('add_to_cart.html',menu=added_menu)
    return redirect(url_for('customer.add_to_cart'))

# Route for deleting a order in (add to cart page)
@customer.route('/delete_order/<int:order_id>', methods=['GET', 'POST'])
def delete_order(order_id):
    order = Orders.query.get(order_id)
    ordertrxcount = Orders.query.filter_by(trxid = order.trxid).count()
    print(ordertrxcount)

    if ordertrxcount > 1:
        db.session.delete(order)
        db.session.commit()
    else:
        trxidforoneorder = Transactions.query.get(order.trxid)
        db.session.delete(order)
        db.session.delete(trxidforoneorder)
        session.pop('trx_id')
        db.session.commit()
    return redirect(url_for('customer.add_to_cart'))  # Redirect to the menu list page after deletion




@customer.route("/confirm_order")
def confirm_order():
    confirm_trx_id = request.args.get('current_trx_id')
    print(confirm_trx_id)
    if confirm_trx_id is not None:
        print("Confirm trx_id is",confirm_trx_id)
        "Proceed to receipt"
        return render_template("customer_receipt.html", confirm_trx_id = confirm_trx_id)
    else:
        print("Please add menu in your cart")
            
    return redirect(url_for('customer.add_to_cart'))

@customer.route("/confirm_order", methods=["POST"])
def process_order():
    confirm_trx_id = int(request.form.get('confirm_trx_id'))
    delivery_address = request.form.get('delivery_address')
    payment_method = request.form.get('payment')
    

    
    customer_id = session["user_id"]
    user = User.query.filter_by(id=customer_id).first()
    fullname = user.fullname
    email = user.email
    phonenum = user.phonenum
    print(fullname , phonenum , email , customer_id)

    transaction = Transactions.query.get(confirm_trx_id)
    transaction.payment_method = payment_method
    transaction.delivery_address =delivery_address

    db.session.commit()
    print(f"Tansaction ID: {confirm_trx_id}, Address : {delivery_address}, Payment method : {payment_method},")

    query = db.session.query(Orders, Menu).join( Menu).filter(Orders.trxid == confirm_trx_id)
    items = []
    total_RM = 0
    for q, s in query:
        quantity = q.quantity
        price_per_unit = s.priceperunit
        total_menu_price = price_per_unit * quantity
        total_RM += total_menu_price

        item = {
            'menu_name': s.menuname,
            'menu_type': s.menutype,
            'quantity': str(quantity),
            'price': f'{price_per_unit:.2f}',  # Format the price with 2 decimal places
            'total_menu_price': f'{total_menu_price:.2f}',  # Format the total price with 2 decimal places
        }
        items.append(item)

    invoice = Invoice()
    invoice.add_page()

    invoice.add_info(
    {
        'Customer name': fullname,
        'Address': delivery_address,
        'Phone': str(phonenum),
        'Email': email,
        'Customer ID': str(customer_id),
        'Payment method': payment_method,
    },
    {
        'Invoice #': '213423',
        'Date': datetime.now().date().strftime("%d %B %Y"),

    },
    {
        'Transaction ID': str(confirm_trx_id),
    }
    )
    
    invoice.add_items(items,f'{total_RM:.2f}')
    invoice.output(f'{UPLOAD_FOLDER_1}/transaction_id_{confirm_trx_id}.pdf', 'F')
    session.pop('trx_id')


    return redirect(url_for('customer.customer_notifications'))

@customer.route("/customer_notifications")
def customer_notifications():
    #user_id = session['username']
    
    #user_id = User.query.filter_by(id=id).first()
    id = session['user_id']
    #print(id)
    confirmed_transactions = Transactions.query.filter(Transactions.payment_method.isnot("None"),Transactions.customer_id == id).all()
    #print(confirmed_transactions)
    
    return render_template("customer_notifications.html", history = confirmed_transactions)


@customer.route("/customer_view_receipt/<int:trx_id>", methods=['GET', 'POST'])
def customer_view_receipt(trx_id):
    filename = f'transaction_id_{trx_id}.pdf'
    uploads = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    filepath = os.path.join(uploads, filename)

    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return "Receipt not found."
