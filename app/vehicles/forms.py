from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from app.models.vehicle import Vehicle, VehicleType, FuelType
import re

class VehicleForm(FlaskForm):
    registration_number = StringField('Registration Number', validators=[
        DataRequired(message="Registration number is required."),
        Length(min=3, max=50, message="Registration number must be between 3 and 50 characters.")
    ])
    name = StringField('Vehicle Name/Brand', validators=[
        DataRequired(message="Vehicle name is required."),
        Length(max=100)
    ])
    model = StringField('Model Name', validators=[
        DataRequired(message="Model name is required."),
        Length(max=100)
    ])
    vehicle_type_id = SelectField('Vehicle Type', coerce=int, validators=[DataRequired()])
    fuel_type_id = SelectField('Fuel Type', coerce=int, validators=[DataRequired()])
    
    max_load_capacity = FloatField('Max Load Capacity (kg)', validators=[
        DataRequired(message="Maximum load capacity is required."),
        NumberRange(min=0.1, message="Load capacity must be greater than 0.")
    ])
    current_odometer = FloatField('Current Odometer (km)', validators=[
        DataRequired(message="Odometer reading is required."),
        NumberRange(min=0, message="Odometer cannot be negative.")
    ])
    purchase_date = DateField('Purchase Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="Purchase date is required.")
    ])
    acquisition_cost = FloatField('Acquisition Cost (₹)', validators=[
        DataRequired(message="Acquisition cost is required."),
        NumberRange(min=0, message="Cost cannot be negative.")
    ])
    insurance_expiry = DateField('Insurance Expiry Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="Insurance expiry date is required.")
    ])
    rc_expiry = DateField('Registration Certificate (RC) Expiry Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="RC expiry date is required.")
    ])
    status = SelectField('Status', choices=[
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('in_shop', 'In Shop'),
        ('retired', 'Retired')
    ], default='available', validators=[DataRequired()])
    
    submit = SubmitField('Save Vehicle')

    def __init__(self, vehicle_id=None, *args, **kwargs):
        super(VehicleForm, self).__init__(*args, **kwargs)
        self.vehicle_id = vehicle_id
        # Load choices dynamically
        self.vehicle_type_id.choices = [(t.id, t.name) for t in VehicleType.query.order_by(VehicleType.name.asc()).all()]
        self.fuel_type_id.choices = [(f.id, f.name) for f in FuelType.query.order_by(FuelType.name.asc()).all()]

    def validate_registration_number(self, field):
        reg = field.data.strip().upper()
        # Regex to validate Indian registration number format (e.g. GJ01AB4587, MH12XY4521, DL8C1234)
        # Standard format is 2 letters (state), 2 digits (district), 1 or 2 letters, 4 digits.
        pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'
        if not re.match(pattern, reg):
            raise ValidationError("Invalid Indian Registration format. Must be GJ01AB4587 (No spaces/special characters).")
        
        existing = Vehicle.query.filter_by(registration_number=reg).first()
        if existing and (self.vehicle_id is None or existing.id != self.vehicle_id):
            raise ValidationError("Registration number is already registered to another vehicle.")
