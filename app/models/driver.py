from app.extensions import db
from datetime import datetime, date

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(255), nullable=True) # File name / path
    license_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    license_category = db.Column(db.String(50), nullable=False) # e.g. LMV, HGV, Trans, Hazard
    license_expiry = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    address = db.Column(db.Text, nullable=False)
    emergency_contact_name = db.Column(db.String(100), nullable=False)
    emergency_contact_phone = db.Column(db.String(20), nullable=False)
    safety_score = db.Column(db.Float, default=100.0, nullable=False)
    joining_date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(50), default='available', nullable=False) # available, on_trip, off_duty, suspended
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user = db.relationship('User', backref=db.backref('driver_profile', uselist=False))

    # Relationships
    documents = db.relationship('DriverDocument', back_populates='driver', cascade='all, delete-orphan')
    trips = db.relationship('Trip', back_populates='driver', cascade='all, delete-orphan')

    @property
    def is_license_expired(self):
        return self.license_expiry < date.today()

    def __repr__(self):
        return f"<Driver {self.name} - License: {self.license_number}>"

class DriverDocument(db.Model):
    __tablename__ = 'driver_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False)
    document_name = db.Column(db.String(100), nullable=False) # e.g. Driving License Card, Aadhaar Card, PAN Card
    document_type = db.Column(db.String(50), nullable=False) # License, Aadhaar, PAN, Medical certificate, Background check
    expiry_date = db.Column(db.Date, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    driver = db.relationship('Driver', back_populates='documents')

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < datetime.now().date()
        return False

    def __repr__(self):
        return f"<DriverDocument {self.document_name} for Driver ID {self.driver_id}>"
