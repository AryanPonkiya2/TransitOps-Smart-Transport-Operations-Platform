from app.extensions import db

class MaintenanceType(db.Model):
    __tablename__ = 'maintenance_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True) # Oil Change, Tyre, Battery, General Service, Accident Repair
    description = db.Column(db.String(255), nullable=True)

    maintenances = db.relationship('Maintenance', back_populates='maintenance_type')

    def __repr__(self):
        return f"<MaintenanceType {self.name}>"

class Maintenance(db.Model):
    __tablename__ = 'maintenances'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    maintenance_type_id = db.Column(db.Integer, db.ForeignKey('maintenance_types.id', ondelete='RESTRICT'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False) # pending, in_progress, completed

    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='maintenances')
    maintenance_type = db.relationship('MaintenanceType', back_populates='maintenances')

    @property
    def type(self):
        return self.maintenance_type.name if self.maintenance_type else None

    def __repr__(self):
        return f"<Maintenance ID {self.id} for Vehicle ID {self.vehicle_id} - Cost: {self.cost}>"
