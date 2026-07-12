from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from app.models.maintenance import MaintenanceType
from app.models.vehicle import Vehicle

class MaintenanceForm(FlaskForm):
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[
        DataRequired(message="Please select a vehicle.")
    ])
    maintenance_type_id = SelectField('Maintenance Type', coerce=int, validators=[
        DataRequired(message="Please select a maintenance type.")
    ])
    
    description = TextAreaField('Description of Work', validators=[
        DataRequired(message="Please enter a description.")
    ])
    start_date = DateField('Start Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="Start date is required.")
    ])
    end_date = DateField('End Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="End date is required.")
    ])
    cost = FloatField('Maintenance Cost (₹)', validators=[
        DataRequired(message="Cost is required."),
        NumberRange(min=0.0, message="Cost cannot be negative.")
    ])
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], default='pending', validators=[DataRequired()])
    
    submit = SubmitField('Log Maintenance')

    def __init__(self, *args, **kwargs):
        super(MaintenanceForm, self).__init__(*args, **kwargs)
        self.vehicle_id.choices = [(0, '-- Select Vehicle to Service --')] + [(v.id, f"{v.registration_number} - {v.name}") for v in Vehicle.query.filter(Vehicle.status != 'retired').all()]
        self.maintenance_type_id.choices = [(0, '-- Select Maintenance Type --')] + [(t.id, t.name) for t in MaintenanceType.query.order_by(MaintenanceType.name.asc()).all()]

    def validate_end_date(self, field):
        if self.start_date.data and field.data < self.start_date.data:
            raise ValidationError("End date cannot be earlier than start date.")
