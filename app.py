from flask import Flask,redirect,request,session,flash,url_for,render_template
from extensions import db
from werkzeug.security import generate_password_hash,check_password_hash
from models import ParkingSpot
from datetime import datetime

import os

app=Flask(__name__)
app.secret_key='secretkey'  

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False
db.init_app(app)


from models import User,ParkingSpot,Booking,ParkingLot


Admin_EMAIL='admin@gmail.com'
Admin_PASSWORD='ad123'



@app.route('/')
@app.route('/login',methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        typed_email=request.form['email']
        typed_password=request.form['password']
        role=request.form['role']

        if role=='admin' and typed_email==Admin_EMAIL and typed_password==Admin_PASSWORD:
            session['user_type']='admin'
            session['user_id']='admin' 
            return redirect(url_for('admin_dashboard'))  

        user=User.query.filter_by(email=typed_email).first()
        if user and check_password_hash(user.password, typed_password):
            session['user_id']=user.id
            session['user_type']='user'
            return redirect(url_for('user_dashboard')) 

        flash("Login in failed. Please try again.")

    return render_template('login.html')

@app.route('/register',methods=['GET', 'POST'])
def register():
    if request.method=='POST':
        person_name= request.form['name']
        email_id=request.form['email']
        vno=request.form['vehicle_no']
        password =generate_password_hash(request.form['password'])

        
        if User.query.filter_by(email=email_id).first():
            flash("Email already registered.")
        else:
            new_user = User(name=person_name
                ,email=email_id
                ,vehicle_no=vno
                ,password=password
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Successful! Please login.")
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type')!='admin':
        flash('Only admin can view this page')
        return redirect(url_for('login'))
    lots=ParkingLot.query.all()
    spots = []
    for lot in lots:
        total = len(lot.spots)
        available = sum(1 for s in lot.spots if s.status=='A')
        occupied = total-available
        spots.append({
            'lots':lot,
            'total_lot':total,
            'available_lot':available,
            'occupied_lot':occupied })
    return render_template('admin_dashboard.html', spot_stats=spots)


@app.route('/admin/add_lot',methods=['GET','POST'])
def add_lot():
    if session.get('user_type')!='admin':
        flash('Only admin can view this page')
        return redirect(url_for('login'))
    if request.method=='POST':
        loc=request.form['prime_location']
        addr=request.form['address']
        pin=request.form['pincode']
        price=int(request.form['price_per_hour'])
        maximum= int(request.form['max_spots'])
   
        new_lot =ParkingLot(
            prime_location=loc,
            address=addr,
            pincode=pin,
            price_per_hour=price,
            max_spots=maximum
        )
        db.session.add(new_lot)
        db.session.commit()
     
        for _ in range(maximum):
            spot = ParkingSpot(status='A', lot_id=new_lot.id)
            db.session.add(spot)
        db.session.commit()
        flash("lot added successfully!")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_lot.html')

@app.route('/user/dashboard',methods=['GET', 'POST'])
def user_dashboard():
    if 'user_id' not in session or session.get('user_type')!='user':
        flash('Please login first!')
        return redirect(url_for('login'))

    user_id=session['user_id']
    user=User.query.get(user_id)
    search= request.args.get('search','')
    if search:
        lots=ParkingLot.query.filter(ParkingLot.prime_location.ilike(f"%{search}%")).all()
    else:
        lots=ParkingLot.query.all()
    active_booking=Booking.query.filter_by(user_id=user_id,leaving_time=None).first()
    recent_bookings=Booking.query.filter_by(user_id=user_id).order_by(Booking.booking_time.desc()).limit(5).all()

    return render_template('user_dashboard.html',
        user=user,
        lot=lots,
        booking=active_booking,
        search_query=search,
        history=recent_bookings
    )

@app.route('/vacate_spot',methods=['POST'])
def vacate_spot():
    user_id=session.get('user_id')
    booking=Booking.query.filter_by(user_id=user_id, leaving_time=None).first()
    if booking:
        booking.leaving_time=datetime.now()
        duration=(booking.leaving_time-booking.parking_time).total_seconds()/3600
        booking.cost_per_hour=round(duration*booking.spot.lot.price_per_hour)
        booking.spot.status='A'
        db.session.commit()
        flash("Spot vacated successfully!")

    return redirect(url_for('user_dashboard'))

@app.route('/admin/users')
def view_users():
    if session.get('user_type')!='admin':
        flash("Only admin can view this page")
        return redirect(url_for('login'))

    all_users=User.query.all()
    return render_template('view_users.html',users=all_users)

@app.route('/admin/summary')
def admin_summary():
    if session.get('user_type')!='admin':
        flash("Only admin can view this page")
        return redirect(url_for('login'))

    available=ParkingSpot.query.filter_by(status='A').count()
    occupied=ParkingSpot.query.filter_by(status='O').count()
    return render_template('summary.html',av=available,occ=occupied)

@app.route('/book/<int:lot_id>',methods=['POST'])
def book_spot(lot_id):
    if 'user_id' not in session:
        flash('You must signin to book lot')
        return redirect(url_for('login'))

    acc_id=session['user_id']
    lot=ParkingLot.query.get_or_404(lot_id)
    available_spot=ParkingSpot.query.filter_by(lot_id=lot.id,status='A').first()

    if not available_spot:
        flash('No available spots in this lot')
        return redirect(url_for('user_dashboard'))
    
    available_spot.status='O'
    db.session.commit()
  
    new_booking = Booking(
        user_id=acc_id,
        spot_id=available_spot.id,
        cost_per_hour=lot.price_per_hour
    )
    db.session.add(new_booking)
    db.session.commit()

    print("A spot was just booked! Spot ID:", available_spot.id)
    flash('Spot booked successfully')
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/view_spots/<int:lot_id>')
def view_spots(lot_id):
    lot=ParkingLot.query.get_or_404(lot_id)
    spots=ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('view_spots.html',lot=lot, spots=spots)

@app.route('/admin/edit-lot/<int:lot_id>', methods=['GET','POST'])
def edit_lot(lot_id):
    if session.get('user_type')!='admin':
        flash("Only admin can view this page")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method=='POST':
        lot.prime_location=request.form['prime_location']
        lot.address=request.form['address']
        lot.pincode=request.form['pincode']
        lot.price_per_hour=request.form['price_per_hour']
        db.session.commit()
        flash('Parking lot updated successfully')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html',lot=lot)

@app.route('/admin/lot/<int:lot_id>/spots')
def view_lot_spots(lot_id):
    lot=ParkingLot.query.get_or_404(lot_id)
    spots=ParkingSpot.query.filter_by(lot_id=lot.id).all()

    spot_statuses=[]
    for spot in spots:
        active_booking=Booking.query.filter_by(spot_id=spot.id,leaving_time=None).first()
        spot_statuses.append({
            'spot':spot,
            'status':'occupied' if active_booking else 'available'
        })

    return render_template('lot_spots.html',lot=lot, spot_statuses=spot_statuses)

@app.route('/admin/delete-lot/<int:lot_id>',methods=['POST'])
def delete_lot(lot_id):
    if session.get('user_type')!='admin':
        flash("Only admin can view this page")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)

    for spot in lot.spots:
        for booking in spot.bookings:
            db.session.delete(booking)
        db.session.delete(spot)
    db.session.delete(lot)
    db.session.commit()
    flash("Parking lot deleted successfully.")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
