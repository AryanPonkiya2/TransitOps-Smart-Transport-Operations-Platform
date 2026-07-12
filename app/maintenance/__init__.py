from flask import Blueprint

maintenance_bp = Blueprint('maintenance', __name__, template_folder='../templates/maintenance')

from app.maintenance import routes
