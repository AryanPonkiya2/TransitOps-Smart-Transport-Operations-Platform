from flask import Blueprint

vehicles_bp = Blueprint('vehicles', __name__, template_folder='../templates/vehicles')

from app.vehicles import routes
