
from flask_login import UserMixin
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from extensions import db



class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    vehicle_no = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    bookings = db.relationship('Booking', backref='user', lazy=True)

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prime_location = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    price_per_hour = db.Column(db.Integer, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)

    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1), default='A')  

    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    bookings = db.relationship('Booking', backref='spot', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parking_time = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_time = db.Column(db.DateTime)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)
    cost_per_hour = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
