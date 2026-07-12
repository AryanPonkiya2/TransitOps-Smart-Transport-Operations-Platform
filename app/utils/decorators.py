from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to restrict access to specific user roles.
    Example usage:
        @role_required('Fleet Manager', 'Safety Officer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            if current_user.role != 'Administrator' and current_user.role not in roles:
                # Provide a custom 403 message or raise 403 forbidden
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
