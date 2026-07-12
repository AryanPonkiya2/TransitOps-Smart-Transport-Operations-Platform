from app.extensions import db
from datetime import datetime

class Trip(db.Model):
    __tablename__ = 'trips'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False)
    
    cargo_weight = db.Column(db.Float, nullable=False) # in kg
    distance = db.Column(db.Float, nullable=False) # in km
    status = db.Column(db.String(50), default='draft', nullable=False) # draft, dispatched, completed, cancelled
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dispatch_date = db.Column(db.DateTime, nullable=True)
    completion_date = db.Column(db.DateTime, nullable=True)
    
    final_odometer = db.Column(db.Float, nullable=True)
    fuel_consumed = db.Column(db.Float, nullable=True) # in Litres
    trip_notes = db.Column(db.Text, nullable=True)

    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='trips')
    driver = db.relationship('Driver', back_populates='trips')
    fuel_logs = db.relationship('FuelLog', back_populates='trip', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='trip', cascade='all, delete-orphan')
    histories = db.relationship('TripHistory', back_populates='trip', cascade='all, delete-orphan')

    @staticmethod
    def generate_trip_code():
        current_year = datetime.now().year
        count = db.session.query(Trip).filter(Trip.trip_code.like(f"TRIP-{current_year}-%")).count()
        return f"TRIP-{current_year}-{str(count + 1).zfill(4)}"

    def log_history(self, status, remarks, user_id=None):
        history = TripHistory(
            trip=self,
            status=status,
            remarks=remarks,
            updated_by_id=user_id,
            updated_at=datetime.utcnow()
        )
        db.session.add(history)

    def __repr__(self):
        return f"<Trip {self.trip_code} - {self.source} to {self.destination}>"

class TripHistory(db.Model):
    __tablename__ = 'trip_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    trip = db.relationship('Trip', back_populates='histories')
    updated_by = db.relationship('User')

    def __repr__(self):
        return f"<TripHistory ID {self.id} for Trip {self.trip_id} - Status: {self.status}>"
