from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from app.models import Vehicle, Driver

class TripForm(FlaskForm):
    source = StringField('Source Location', validators=[
        DataRequired(message="Source is required.")
    ])
    destination = StringField('Destination Location', validators=[
        DataRequired(message="Destination is required.")
    ])
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[
        DataRequired(message="Please select a vehicle.")
    ])
    driver_id = SelectField('Driver', coerce=int, validators=[
        DataRequired(message="Please select a driver.")
    ])
    cargo_weight = FloatField('Cargo Weight (kg)', validators=[
        DataRequired(message="Cargo weight is required."),
        NumberRange(min=0.1, message="Cargo weight must be greater than 0.")
    ])
    distance = FloatField('Distance (km)', validators=[
        DataRequired(message="Distance is required."),
        NumberRange(min=0.1, message="Distance must be greater than 0.")
    ])
    trip_notes = TextAreaField('Trip Notes')
    
    submit = SubmitField('Save Trip')

    def __init__(self, trip_id=None, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)
        self.trip_id = trip_id

    def validate_cargo_weight(self, field):
        vehicle = Vehicle.query.get(self.vehicle_id.data)
        if vehicle and field.data > vehicle.max_load_capacity:
            raise ValidationError(
                f"Cargo weight ({field.data} kg) exceeds vehicle capacity ({vehicle.max_load_capacity} kg)."
            )


class TripCompleteForm(FlaskForm):
    final_odometer = FloatField('Final Odometer (km)', validators=[
        DataRequired(message="Final odometer is required."),
        NumberRange(min=0.0, message="Odometer cannot be negative.")
    ])
    fuel_consumed = FloatField('Fuel Consumed (L)', validators=[
        DataRequired(message="Fuel consumed is required."),
        NumberRange(min=0.0, message="Fuel consumed cannot be negative.")
    ])
    trip_notes = TextAreaField('Closing Notes')
    
    submit = SubmitField('Complete Trip')

    def __init__(self, start_odometer=0.0, *args, **kwargs):
        super(TripCompleteForm, self).__init__(*args, **kwargs)
        self.start_odometer = start_odometer

    def validate_final_odometer(self, field):
        if field.data < self.start_odometer:
            raise ValidationError(
                f"Final odometer ({field.data} km) cannot be less than start odometer ({self.start_odometer} km)."
            )
