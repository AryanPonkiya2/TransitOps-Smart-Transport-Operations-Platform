from app.extensions import db

class FuelLog(db.Model):
    __tablename__ = 'fuel_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='SET NULL'), nullable=True)
    fuel_type_id = db.Column(db.Integer, db.ForeignKey('fuel_types.id', ondelete='RESTRICT'), nullable=False)
    fuel_quantity = db.Column(db.Float, nullable=False) # in Litres / KG
    fuel_price = db.Column(db.Float, nullable=False) # Price per Litre / KG
    fuel_station = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_cost = db.Column(db.Float, nullable=False) # Auto-calculated: quantity * price

    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='fuel_logs')
    trip = db.relationship('Trip', back_populates='fuel_logs')
    fuel_type = db.relationship('FuelType')

    def __init__(self, **kwargs):
        super(FuelLog, self).__init__(**kwargs)
        if self.fuel_quantity is not None and self.fuel_price is not None:
            self.total_cost = round(self.fuel_quantity * self.fuel_price, 2)

    def update_cost(self):
        if self.fuel_quantity is not None and self.fuel_price is not None:
            self.total_cost = round(self.fuel_quantity * self.fuel_price, 2)

    @property
    def fuel_type_name(self):
        return self.fuel_type.name if self.fuel_type else None

    def __repr__(self):
        return f"<FuelLog Vehicle ID {self.vehicle_id} - Qty: {self.fuel_quantity} - Cost: {self.total_cost}>"
