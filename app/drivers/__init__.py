from flask import Blueprint

drivers_bp = Blueprint('drivers', __name__, template_folder='../templates/drivers')

from app.drivers import routes
