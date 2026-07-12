from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, FloatField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
from app.models.driver import Driver
import re

class DriverForm(FlaskForm):
    name = StringField('Driver Name', validators=[
        DataRequired(message="Driver name is required."),
        Length(max=100)
    ])
    photo_file = FileField('Driver Photo', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    license_number = StringField('License Number', validators=[
        DataRequired(message="License number is required."),
        Length(max=50)
    ])
    license_category = SelectField('License Category', choices=[
        ('LMV', 'Light Motor Vehicle (LMV)'),
        ('HMV', 'Heavy Motor Vehicle (HMV)'),
        ('TRANS', 'Transport Vehicle (TRANS)'),
        ('HAZ', 'Hazardous Goods (HAZ)')
    ], validators=[DataRequired()])
    
    license_expiry = DateField('License Expiry Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="License expiry date is required.")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=10, max=15, message="Phone number must be between 10 and 15 digits.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email address is required."),
        Email(message="Please enter a valid email address.")
    ])
    address = TextAreaField('Residential Address', validators=[
        DataRequired(message="Residential address is required.")
    ])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[
        DataRequired(message="Emergency contact name is required."),
        Length(max=100)
    ])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[
        DataRequired(message="Emergency contact phone number is required."),
        Length(min=10, max=15, message="Phone number must be between 10 and 15 digits.")
    ])
    safety_score = FloatField('Safety Score (0 - 100)', default=100.0, validators=[
        DataRequired(message="Safety score is required."),
        NumberRange(min=0.0, max=100.0, message="Safety score must be between 0 and 100.")
    ])
    status = SelectField('Status', choices=[
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('off_duty', 'Off Duty'),
        ('suspended', 'Suspended')
    ], default='available', validators=[DataRequired()])
    
    user_id = SelectField('Linked User Account', coerce=int, validators=[])

    submit = SubmitField('Save Driver Profile')

    def __init__(self, driver_id=None, *args, **kwargs):
        super(DriverForm, self).__init__(*args, **kwargs)
        self.driver_id = driver_id

    def validate_license_number(self, field):
        lic = field.data.strip().upper()
        # Indian DL format: SS-RRYYYYYNNNNNNN
        # (2 letters code, 2 digits RTO code, 4 digits year of issue, 7 digits license number)
        # Let's enforce standard length/chars check
        # Allow general characters/numbers but must be unique and have length >= 10
        if len(lic) < 10:
            raise ValidationError("License number must be a valid driving license number.")
            
        existing = Driver.query.filter_by(license_number=lic).first()
        if existing and (self.driver_id is None or existing.id != self.driver_id):
            raise ValidationError("License number already registered to another driver.")

    def validate_email(self, field):
        existing = Driver.query.filter_by(email=field.data.strip().lower()).first()
        if existing and (self.driver_id is None or existing.id != self.driver_id):
            raise ValidationError("Email address is already registered to another driver.")

    def validate_phone(self, field):
        ph = field.data.strip()
        if not re.match(r'^\+?[0-9]{10,15}$', ph):
            raise ValidationError("Invalid phone number format.")

    def validate_emergency_contact_phone(self, field):
        ph = field.data.strip()
        if not re.match(r'^\+?[0-9]{10,15}$', ph):
            raise ValidationError("Invalid emergency contact phone number.")
