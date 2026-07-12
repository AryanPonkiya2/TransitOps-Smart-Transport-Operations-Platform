from app.extensions import db
from datetime import datetime

class VehicleType(db.Model):
    __tablename__ = 'vehicle_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. Truck, Van, Flatbed, Refrigerated, Bus, Car
    description = db.Column(db.String(255), nullable=True)

    vehicles = db.relationship('Vehicle', back_populates='vehicle_type')

    def __repr__(self):
        return f"<VehicleType {self.name}>"

class FuelType(db.Model):
    __tablename__ = 'fuel_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False, index=True) # Petrol, Diesel, CNG, EV
    
    vehicles = db.relationship('Vehicle', back_populates='fuel_type')

    def __repr__(self):
        return f"<FuelType {self.name}>"

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey('vehicle_types.id', ondelete='RESTRICT'), nullable=False)
    max_load_capacity = db.Column(db.Float, nullable=False) # in kg
    current_odometer = db.Column(db.Float, default=0.0, nullable=False) # in km
    purchase_date = db.Column(db.Date, nullable=False)
    acquisition_cost = db.Column(db.Float, nullable=False)
    insurance_expiry = db.Column(db.Date, nullable=False)
    rc_expiry = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='available', nullable=False) # available, on_trip, in_shop, retired
    fuel_type_id = db.Column(db.Integer, db.ForeignKey('fuel_types.id', ondelete='RESTRICT'), nullable=False)

    # Relationships
    vehicle_type = db.relationship('VehicleType', back_populates='vehicles')
    fuel_type = db.relationship('FuelType', back_populates='vehicles')
    documents = db.relationship('VehicleDocument', back_populates='vehicle', cascade='all, delete-orphan')
    trips = db.relationship('Trip', back_populates='vehicle', cascade='all, delete-orphan')
    maintenances = db.relationship('Maintenance', back_populates='vehicle', cascade='all, delete-orphan')
    fuel_logs = db.relationship('FuelLog', back_populates='vehicle', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='vehicle', cascade='all, delete-orphan')

    @property
    def total_operating_cost(self):
        return sum(expense.amount for expense in self.expenses)

    @property
    def fuel_efficiency(self):
        completed_trips = [t for t in self.trips if t.status == 'completed']
        total_distance = sum(t.distance for t in completed_trips)
        total_fuel = sum(t.fuel_consumed for t in completed_trips if t.fuel_consumed is not None)
        if total_fuel > 0:
            return round(total_distance / total_fuel, 2) # KM/L
        return 0.0

    @property
    def type(self):
        return self.vehicle_type.name if self.vehicle_type else None

    @property
    def fuel_type_name(self):
        return self.fuel_type.name if self.fuel_type else None

    def __repr__(self):
        return f"<Vehicle {self.registration_number} - {self.name}>"

class VehicleDocument(db.Model):
    __tablename__ = 'vehicle_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    document_name = db.Column(db.String(100), nullable=False) # e.g. Insurance Policy, RC Smart Card, National Permit
    document_type = db.Column(db.String(50), nullable=False) # Insurance, RC, Permit, Fitness, PUC
    expiry_date = db.Column(db.Date, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    vehicle = db.relationship('Vehicle', back_populates='documents')

    @property
    def is_expired(self):
        return self.expiry_date < datetime.now().date()

    def __repr__(self):
        return f"<VehicleDocument {self.document_name} for Vehicle ID {self.vehicle_id}>"
