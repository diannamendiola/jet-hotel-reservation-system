from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import exists, func
from models import db, User, Room, Reservation, Transaction, Notification
from forms import RegistrationForm, LoginForm, RoomForm, ReservationForm, ContactForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/hotel_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jethoteldemo@gmail.com'  # Replace
app.config['MAIL_PASSWORD'] = 'smmi bdpq rgxr afns'     # Replace
app.config['MAIL_DEFAULT_SENDER'] = "Hotel Reservation System <jethoteldemo@gmail.com>"

mail = Mail(app)
db.init_app(app)

# Make request available in templates
app.jinja_env.globals.update(request=request)

with app.app_context():
    db.create_all()

    # Default admin
    if not User.query.filter_by(email="admin@hotel.com").first():
        admin = User(
            full_name="Admin",
            email="admin@hotel.com",
            contact_info="N/A",
            password=generate_password_hash("admin123"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

    # Sample rooms - only create if no rooms exist
    if Room.query.count() == 0:
        rooms = [
            Room(name="Deluxe Room", price=150.0, description="A comfortable deluxe room with modern amenities.", image="deluxe.jpg"),
            Room(name="Suite", price=250.0, description="A luxurious suite with spacious living area.", image="suite.jpg"),
            Room(name="Standard Room", price=100.0, description="Affordable standard room perfect for budget travelers.", image="standard.jpg"),
            Room(name="Executive Room", price=200.0, description="Executive room with business amenities and city view.", image="executive.jpg"),
            Room(name="Family Room", price=180.0, description="Spacious family room with extra beds and play area.", image="family.jpg"),
            Room(name="Penthouse Suite", price=350.0, description="Exclusive penthouse suite with panoramic views.", image="penthouse.jpg"),
            Room(name="Ocean View Room", price=220.0, description="Beautiful ocean view room with balcony.", image="oceanview.jpg"),
            Room(name="Garden View Room", price=160.0, description="Peaceful garden view room with natural surroundings.", image="gardenview.jpg"),
            Room(name="Presidential Suite", price=400.0, description="The ultimate luxury experience with premium services.", image="presidential.jpg")
        ]
        db.session.add_all(rooms)
        db.session.commit()

    # Sample reservations and notifications if none exist
    if not Reservation.query.first():
        # Get sample rooms
        sample_rooms = Room.query.limit(5).all()
        if sample_rooms:
            from datetime import timedelta
            today = datetime.now().date()
            reservations = []
            notifications = []

            for i, room in enumerate(sample_rooms):
                # Create current bookings for all 5 rooms
                check_in = today - timedelta(days=1)
                check_out = today + timedelta(days=1)
                reservation = Reservation(
                    user_id=1,  # admin user
                    room_id=room.id,
                    check_in=check_in,
                    check_out=check_out,
                    status="Confirmed"
                )
                reservations.append(reservation)

                # Admin notification
                admin_notif = Notification(
                    user_id=None,
                    message=f"Sample reservation #{i+1} created for {room.name}"
                )
                notifications.append(admin_notif)

                # User notification
                user_notif = Notification(
                    user_id=1,
                    message=f"Your sample reservation for {room.name} is confirmed. Check-in: {check_in}, Check-out: {check_out}"
                )
                notifications.append(user_notif)

            db.session.add_all(reservations)
            db.session.add_all(notifications)
            db.session.commit()
# -----------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def home():
    # Prevent admin from accessing user home page
    if session.get('is_admin'):
        return redirect(url_for('dashboard'))

    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    # Get all rooms
    all_rooms = Room.query.all()
    rooms = all_rooms

    # Get all reservations to check current bookings
    reservations = Reservation.query.all()

    # If dates are provided, filter for availability
    if check_in and check_out:
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            # Validate dates
            today = datetime.now().date()
            if check_in_date < today:
                flash("Check-in date cannot be in the past.")
                check_in = check_out = None
            elif check_out_date <= check_in_date:
                flash("Check-out date must be after check-in date.")
                check_in = check_out = None
            else:
                # Get available rooms for the date range
                rooms = Room.get_available_rooms_for_dates(check_in_date, check_out_date)
        except ValueError:
            flash("Invalid date format.")
            check_in = check_out = None

    # Add availability status to each room
    rooms_with_status = []
    for room in all_rooms:
        # Check if room is currently booked (check-in <= today < check-out)
        current_bookings = [r for r in reservations if r.room_id == room.id and r.check_in <= datetime.now().date() < r.check_out]
        is_currently_booked = len(current_bookings) > 0

        if check_in and check_out:
            # For specific date range search
            is_available = room in rooms
        else:
            # For general display, show as unavailable if currently booked
            is_available = not is_currently_booked and room.available

        room_data = {
            'room': room,
            'is_available': is_available
        }
        rooms_with_status.append(room_data)

    today = datetime.now().date().isoformat()
    return render_template('home.html', rooms=rooms_with_status, check_in=check_in, check_out=check_out, today=today)

@app.route('/rooms')
def rooms():
    return redirect(url_for('home') + '#rooms')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        password = generate_password_hash(form.password.data)
        user = User(full_name=form.full_name.data, email=form.email.data, contact_info=form.contact_info.data, password=password)
        db.session.add(user)
        db.session.commit()   # Save first

        # Automatically log in the user after registration
        session['user_id'] = user.id
        session['username'] = user.full_name
        session['is_admin'] = user.is_admin

        # Send welcome email
        msg = Message(
            subject="Welcome to Our Hotel!",
            recipients=[user.email],
            body=f"""
Hello {user.full_name},

Thank you for registering at our hotel reservation system.
You are now logged in and can book rooms.

Best regards,
Hotel Management
"""
        )
        email_sent = False
        try:
            mail.send(msg)
            email_sent = True
        except Exception as e:
            print("Email failed:", e)

        if email_sent:
            flash("Registration successful! Welcome email sent. You are now logged in.")
        else:
            flash("Registration successful! You are now logged in. (Welcome email could not be sent)")
        return redirect(url_for('home'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.full_name
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard') if user.is_admin else url_for('home'))
        else:
            flash("Invalid credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

# -----------------
# User Reservations & Transactions & Notifications
# -----------------
@app.route('/user_reservations')
def user_reservations():
    if not session.get('user_id'):
        flash("Please login first.")
        return redirect(url_for('login'))
    reservations = Reservation.query.filter_by(user_id=session['user_id']).order_by(Reservation.created_at.desc()).all()
    return render_template('user_reservations.html', reservations=reservations)

@app.route('/transactions')
def transactions():
    if not session.get('user_id'):
        flash("Please login first.")
        return redirect(url_for('login'))
    # Get transactions with related reservation and room data
    transactions = Transaction.query.join(Reservation).filter(
        Reservation.user_id == session['user_id']
    ).order_by(Transaction.created_at.desc()).all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/confirm_payment/<int:transaction_id>', methods=['POST'])
def confirm_payment(transaction_id):
    if not session.get('user_id'):
        flash("Please login first.")
        return redirect(url_for('login'))

    transaction = Transaction.query.get_or_404(transaction_id)

    # Ensure the transaction belongs to the current user
    if transaction.reservation.user_id != session['user_id']:
        flash("Access denied!")
        return redirect(url_for('transactions'))

    # Check if already paid or cancelled
    if transaction.status != "Pending":
        flash("This transaction is already processed.")
        return redirect(url_for('transactions'))

    # Update transaction status to "Payment Confirmed" (user has indicated payment made)
    transaction.status = "Payment Confirmed"

    # Create admin notification for payment confirmation
    admin_notification = Notification(
        user_id=None,  # admin
        message=f"User {session['username']} has confirmed payment for Transaction #{transaction.id} - ₱{transaction.amount}"
    )
    db.session.add(admin_notification)

    # Create user notification
    user_notification = Notification(
        user_id=session['user_id'],
        message=f"You have confirmed payment for Transaction #{transaction.id}. Waiting for admin approval."
    )
    db.session.add(user_notification)

    db.session.commit()

    # Send payment confirmation email to user
    user = User.query.get(session['user_id'])
    room = transaction.reservation.room
    nights = (transaction.reservation.check_out - transaction.reservation.check_in).days

    msg = Message(
        subject="Payment Confirmation Received - Pending Admin Approval",
        recipients=[user.email],
        body=f"""
Hello {user.full_name},

We have received your payment confirmation for the following reservation:

Reservation Details:
Room: {room.name}
Check-in: {transaction.reservation.check_in}
Check-out: {transaction.reservation.check_out}
Nights: {nights}
Price per night: ₱{room.price}
Total Amount: ₱{transaction.amount}

Your payment confirmation has been sent to our admin team for approval.
You will receive another email once your payment is approved and your reservation is confirmed.

Thank you for choosing our hotel!

Best regards,
Hotel Management Team
"""
    )
    try:
        mail.send(msg)
        flash("Payment confirmation sent to admin. Confirmation email sent to your email address.")
    except Exception as e:
        print("Email failed:", e)
        flash("Payment confirmation sent to admin. Please wait for approval.")

    return redirect(url_for('transactions'))

@app.route('/admin/approve_payment/<int:transaction_id>', methods=['POST'])
def approve_payment(transaction_id):
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))

    transaction = Transaction.query.get_or_404(transaction_id)

    # Update transaction status to "Paid"
    transaction.status = "Paid"

    # Update reservation status to "Confirmed"
    transaction.reservation.status = "Confirmed"

    # Create user notification
    user_notification = Notification(
        user_id=transaction.reservation.user_id,
        message=f"Your payment for Reservation #{transaction.reservation.id} has been approved. Your reservation is now confirmed!"
    )
    db.session.add(user_notification)

    # Create admin notification
    admin_notification = Notification(
        user_id=None,  # admin
        message=f"Payment approved for Transaction #{transaction.id} - Reservation #{transaction.reservation.id}"
    )
    db.session.add(admin_notification)

    db.session.commit()

    # Send confirmation email to user
    user = User.query.get(transaction.reservation.user_id)
    room = transaction.reservation.room
    nights = (transaction.reservation.check_out - transaction.reservation.check_in).days

    msg = Message(
        subject="Payment Approved - Reservation Confirmed",
        recipients=[user.email],
        body=f"""
    Hello {user.full_name},

    Your payment has been approved and your reservation is now confirmed!

    Reservation Details:
    Room: {room.name}
    Check-in: {transaction.reservation.check_in}
    Check-out: {transaction.reservation.check_out}
    Nights: {nights}
    Price per night: ₱{room.price}
    Total Amount: ₱{transaction.amount}

    Thank you for choosing our hotel!
    """
    )
    mail.send(msg)

    flash("Payment approved successfully! Confirmation email sent to user.")
    return redirect(url_for('dashboard'))

@app.route('/notifications')
def notifications():
    if not session.get('user_id'):
        flash("Please login first.")
        return redirect(url_for('login'))
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

# -----------------
# Reservation
# -----------------
@app.route('/reserve/<int:room_id>', methods=['GET', 'POST'])
def reserve(room_id):
    # Require login
    if not session.get('user_id'):
        flash("Please login first.")
        return redirect(url_for('login'))

    room = Room.query.get_or_404(room_id)

    if request.method == 'POST':
        # Get dates from form
        check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')

        # Validate dates
        today = datetime.now().date()
        if check_in.date() < today:
            flash("Check-in date cannot be in the past.")
            return redirect(url_for('reserve', room_id=room_id))
        if check_out <= check_in:
            flash("Check-out date must be after check-in date.")
            return redirect(url_for('reserve', room_id=room_id))

        # Check if room is already reserved for these dates
        existing_reservation = Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.check_in < check_out,
            Reservation.check_out > check_in
        ).first()
        if existing_reservation:
            flash("This room is already reserved for the selected dates.")
            return redirect(url_for('reserve', room_id=room_id))

        # 1️⃣ Create reservation with Pending status
        reservation = Reservation(
            user_id=session['user_id'],
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
            status="Pending"  # Reservation is pending payment
        )
        db.session.add(reservation)
        db.session.commit()   # ✅ SAVE RESERVATION FIRST

        # 2️⃣ Calculate total amount (room price × number of nights)
        nights = (check_out.date() - check_in.date()).days
        total_amount = room.price * nights

        # 3️⃣ Create transaction record with Pending status
        transaction = Transaction(
            reservation_id=reservation.id,
            amount=total_amount,
            status="Pending"  # Payment is pending
        )
        db.session.add(transaction)

        # 4️⃣ Create admin notification
        admin_notification = Notification(
            user_id=None,  # admin
            message=f"New reservation #{reservation.id} created by User {session['username']} - ₱{total_amount} (Pending Payment)"
        )
        db.session.add(admin_notification)

        # 5️⃣ Create user notification
        user_notification = Notification(
            user_id=session['user_id'],
            message=f"Your reservation for {room.name} is pending payment. Check-in: {check_in.date()}, Check-out: {check_out.date()}. Total: ₱{total_amount}. Please proceed to payment."
        )
        db.session.add(user_notification)

        db.session.commit()   # ✅ SAVE ALL RECORDS

        # 6️⃣ Send reservation created email to user
        user = User.query.get(session['user_id'])

        msg = Message(
            subject="Reservation Created - Payment Pending",
            recipients=[user.email],
            body=f"""
        Hello {user.full_name},

        Your reservation has been created and is pending payment confirmation.

        Room: {room.name}
        Check-in: {check_in.date()}
        Check-out: {check_out.date()}
        Nights: {nights}
        Price per night: ₱{room.price}
        Total Amount: ₱{total_amount}

        Please proceed to the transactions page to confirm your payment.
        You can pay over-the-counter or through online payment.

        Thank you for choosing our hotel!
        """
        )
        mail.send(msg)

        flash("Reservation created! Please proceed to payment confirmation.")
        return redirect(url_for('home'))

    today = datetime.now().date().isoformat()
    return render_template('reserve.html', room=room, today=today)

# -----------------
# Admin Dashboard
# -----------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))

    reservations = Reservation.query.join(User).join(Room).order_by(Reservation.created_at.desc()).all()

    # Get all rooms with their current status
    all_rooms = Room.query.all()
    rooms_with_status = []

    for room in all_rooms:
        # Check if room has any reservations
        room_reservations = [r for r in reservations if r.room_id == room.id]
        if room_reservations:
            # Room has reservations, show as booked
            status = 'booked'
            # Find the latest checkout date for display
            checkout_dates = [r.check_out for r in room_reservations]
            booked_until = max(checkout_dates)
        else:
            booked_until = None
            status = 'available' if room.available else 'unavailable'

        room.status = status
        room.booked_until = booked_until
        rooms_with_status.append(room)

    # Separate rooms into booked and unbooked sections
    booked_rooms = [room for room in rooms_with_status if room.status == 'booked']
    unbooked_rooms = [room for room in rooms_with_status if room.status != 'booked']

    total_bookings = Reservation.query.count()
    total_revenue = Transaction.get_total_revenue()
    total_available_rooms = len([r for r in rooms_with_status if r.status == 'available'])
    notifications = Notification.query.filter_by(user_id=None).order_by(Notification.created_at.desc()).limit(5).all()
    rooms = Room.query.all()  # Add rooms for the manage rooms tab

    # Get pending payment confirmations for the payment approvals tab
    pending_transactions = Transaction.query.filter_by(status="Payment Confirmed").join(Reservation).all()

    # Determine which tab should be active by default
    active_tab = 'payment-approvals' if pending_transactions else 'overview'

    today = datetime.now().date().isoformat()

    return render_template('dashboard.html',
                           reservations=reservations,
                           all_rooms=rooms_with_status,
                           booked_rooms=booked_rooms,
                           unbooked_rooms=unbooked_rooms,
                           total_bookings=total_bookings,
                           total_revenue=total_revenue,
                           total_available_rooms=len([r for r in rooms_with_status if r.status == 'available']),
                           notifications=notifications,
                           rooms=rooms,
                           pending_transactions=pending_transactions,
                           active_tab=active_tab,
                           today=today)

# -----------------
# Admin Room Management
# -----------------
@app.route('/admin/rooms')
def admin_rooms():
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))
    rooms = Room.query.all()
    return render_template('admin_rooms.html', rooms=rooms)

@app.route('/admin/rooms/add', methods=['GET','POST'])
def add_room():
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))
    if request.method == 'POST':
        room = Room(
            name=request.form['name'],
            price=float(request.form['price']),
            description=request.form['description'],
            image=request.form['image'],
            available=request.form.get('available')=='on'
        )
        db.session.add(room)
        db.session.commit()
        flash("Room added successfully!")
        return redirect(url_for('dashboard') + '#manage-rooms')
    return render_template('add_room.html')

@app.route('/admin/rooms/edit/<int:room_id>', methods=['GET','POST'])
def edit_room(room_id):
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form['name']
        room.price = float(request.form['price'])
        room.description = request.form['description']
        room.image = request.form['image']
        room.available = request.form.get('available')=='on'
        db.session.commit()
        flash("Room updated successfully!")
        return redirect(url_for('dashboard') + '#manage-rooms')
    return render_template('edit_room.html', room=room)

@app.route('/admin/rooms/delete/<int:room_id>')
def delete_room(room_id):
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash("Room deleted successfully!")
    return redirect(url_for('dashboard') + '#manage-rooms')



@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    if not session.get('is_admin'):
        flash("Admin access required!")
        return redirect(url_for('login'))
    reservation = Reservation.query.get_or_404(reservation_id)

    # Update transaction status to cancelled and remove reservation reference
    transaction = Transaction.query.filter_by(reservation_id=reservation_id).first()
    if transaction:
        transaction.status = "Cancelled"
        transaction.reservation_id = None

    # Create notification for the user
    user_notification = Notification(
        user_id=reservation.user_id,
        message=f"Your reservation #{reservation.id} has been cancelled by admin."
    )
    db.session.add(user_notification)

    # Create notification for admin
    admin_notification = Notification(
        user_id=None,  # admin
        message=f"Reservation #{reservation.id} cancelled successfully."
    )
    db.session.add(admin_notification)

    db.session.delete(reservation)
    db.session.commit()
    flash("Reservation cancelled successfully!")
    return redirect(url_for('dashboard'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Send email to jethoteldemo@gmail.com
        msg = Message(
            subject=f"Contact Form Message from {name}",
            recipients=['jethoteldemo@gmail.com'],
            body=f"""
Name: {name}
Email: {email}

Message:
{message}
"""
        )
        try:
            mail.send(msg)
            flash("Message sent successfully!")
        except Exception as e:
            print("Email failed:", e)
            flash("Failed to send message. Please try again.")

        return redirect(url_for('contact'))
    return render_template('contact.html')

# -----------------
# Run App
# -----------------
if __name__ == '__main__':
    app.run(debug=True)
