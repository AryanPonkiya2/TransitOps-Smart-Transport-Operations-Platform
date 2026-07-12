from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.models.user import User
from app.extensions import login_manager, db

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact the administrator.", "danger")
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f"Welcome back, {user.name}! Logged in as {user.role}.", "success")
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('auth.login'))
