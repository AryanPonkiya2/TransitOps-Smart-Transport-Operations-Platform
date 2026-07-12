from app.extensions import db

class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True) # Fuel, Repair, Insurance, FASTag, Toll Tax, Parking, Miscellaneous
    description = db.Column(db.String(255), nullable=True)

    expenses = db.relationship('Expense', back_populates='category')

    def __repr__(self):
        return f"<ExpenseCategory {self.name}>"

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='SET NULL'), nullable=True)
    expense_category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id', ondelete='RESTRICT'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)

    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='expenses')
    trip = db.relationship('Trip', back_populates='expenses')
    category = db.relationship('ExpenseCategory', back_populates='expenses')

    @property
    def expense_type(self):
        return self.category.name if self.category else None

    def __repr__(self):
        return f"<Expense Category {self.expense_type} for Vehicle ID {self.vehicle_id} - Amount: {self.amount}>"
