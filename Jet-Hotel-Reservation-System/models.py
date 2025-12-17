from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact_info = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(200), nullable=True)
    available = db.Column(db.Boolean, default=True)
    reservations = db.relationship('Reservation', backref='room', lazy=True)

    def is_available_for_dates(self, check_in_date, check_out_date):
        """Check if room is available for the given date range"""
        if not self.available:
            return False

        # Check for overlapping reservations
        overlapping_reservation = Reservation.query.filter(
            Reservation.room_id == self.id,
            Reservation.check_in < check_out_date,
            Reservation.check_out > check_in_date
        ).first()

        return overlapping_reservation is None

    @classmethod
    def get_available_rooms_for_dates(cls, check_in_date, check_out_date):
        """Get all rooms available for the given date range"""
        all_rooms = cls.query.filter_by(available=True).all()
        available_rooms = []

        for room in all_rooms:
            if room.is_available_for_dates(check_in_date, check_out_date):
                available_rooms.append(room)

        return available_rooms

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Booked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='reservation', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Paid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_total_revenue(cls):
        """Get total revenue from all paid transactions"""
        from sqlalchemy import func
        return db.session.query(func.sum(cls.amount)).filter(cls.status == 'Paid').scalar() or 0

    @classmethod
    def cancel_transaction(cls, reservation_id):
        """Cancel transaction for a reservation"""
        transaction = cls.query.filter_by(reservation_id=reservation_id).first()
        if transaction:
            transaction.status = "Cancelled"
            transaction.reservation_id = None
            db.session.commit()
        return transaction

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    message = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
