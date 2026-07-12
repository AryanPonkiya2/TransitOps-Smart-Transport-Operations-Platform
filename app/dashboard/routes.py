from flask import render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp
from app.models import Vehicle, Driver, Trip, Maintenance, FuelLog, Expense, ExpenseCategory
from app.extensions import db
from datetime import date, datetime, timedelta
from sqlalchemy import func

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver:
            return render_template('dashboard/driver_portal.html', 
                                   driver=None, 
                                   assigned_trips=[],
                                   kpis={})
        
        assigned_trips = Trip.query.filter_by(driver_id=driver.id).order_by(Trip.created_date.desc()).all()
        
        kpis = {
            'total_trips': len(assigned_trips),
            'dispatched_trips': sum(1 for t in assigned_trips if t.status == 'dispatched'),
            'completed_trips': sum(1 for t in assigned_trips if t.status == 'completed'),
            'safety_score': driver.safety_score,
            'license_status': 'Expired' if driver.is_license_expired else 'Valid',
            'license_expiry': driver.license_expiry.strftime('%d-%m-%Y')
        }
        
        return render_template('dashboard/driver_portal.html', 
                               driver=driver, 
                               assigned_trips=assigned_trips[:10], 
                               kpis=kpis)
    
    today = date.today()
    
    # KPI Calculations
    total_vehicles = Vehicle.query.count()
    available_vehicles = Vehicle.query.filter_by(status='available').count()
    on_trip_vehicles = Vehicle.query.filter_by(status='on_trip').count()
    in_shop_vehicles = Vehicle.query.filter_by(status='in_shop').count()
    retired_vehicles = Vehicle.query.filter_by(status='retired').count()
    
    available_drivers = Driver.query.filter_by(status='available').count()
    on_trip_drivers = Driver.query.filter_by(status='on_trip').count()
    
    active_trips = Trip.query.filter_by(status='dispatched').count()
    pending_trips = Trip.query.filter_by(status='draft').count()
    
    # Today's financials
    today_fuel_cost = db.session.query(func.sum(FuelLog.total_cost)).filter(FuelLog.date == today).scalar() or 0.0
    today_expenses = db.session.query(func.sum(Expense.amount)).filter(Expense.date == today).scalar() or 0.0
    
    maintenance_due = Maintenance.query.filter(Maintenance.status.in_(['pending', 'in_progress'])).count()
    
    # Lists for table displays
    recent_trips = Trip.query.order_by(Trip.created_date.desc()).limit(5).all()
    recent_maintenance = Maintenance.query.order_by(Maintenance.start_date.desc()).limit(5).all()
    
    # Driver license expiration monitoring (next 30 days)
    expiry_limit = today + timedelta(days=30)
    expiring_licenses = Driver.query.filter(Driver.license_expiry <= expiry_limit).order_by(Driver.license_expiry.asc()).all()
    
    # Chart Data calculations
    
    # 1. Trips Per Day (last 7 days)
    trips_per_day = []
    days_labels = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days_labels.append(d.strftime('%b %d'))
        count = db.session.query(func.count(Trip.id)).filter(func.date(Trip.created_date) == d).scalar() or 0
        trips_per_day.append(count)
        
    # 2. Vehicle Status Distribution
    vehicle_statuses = ['Available', 'On Trip', 'In Shop', 'Retired']
    vehicle_status_counts = [
        available_vehicles,
        on_trip_vehicles,
        in_shop_vehicles,
        retired_vehicles
    ]
    
    # 3. Fuel Consumption Trend (last 6 months)
    fuel_months = []
    fuel_quantities = []
    for i in range(5, -1, -1):
        first_of_month = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_label = first_of_month.strftime('%b %Y')
        fuel_months.append(month_label)
        
        next_month_start = (first_of_month + timedelta(days=32)).replace(day=1)
        qty = db.session.query(func.sum(FuelLog.fuel_quantity)).filter(
            FuelLog.date >= first_of_month,
            FuelLog.date < next_month_start
        ).scalar() or 0.0
        fuel_quantities.append(round(qty, 1))

    # 4. Expense Breakdown (using joins over normalized Category)
    expense_categories = ['Fuel', 'Repair', 'FASTag', 'Toll Tax', 'Parking', 'Insurance', 'Miscellaneous']
    expense_category_sums = []
    for category in expense_categories:
        amount = db.session.query(func.sum(Expense.amount))\
            .join(ExpenseCategory)\
            .filter(ExpenseCategory.name == category)\
            .scalar() or 0.0
        expense_category_sums.append(round(amount, 2))
        
    chart_data = {
        'trips_per_day_labels': days_labels,
        'trips_per_day_data': trips_per_day,
        'vehicle_status_labels': vehicle_statuses,
        'vehicle_status_data': vehicle_status_counts,
        'fuel_consumption_labels': fuel_months,
        'fuel_consumption_data': fuel_quantities,
        'expense_labels': expense_categories,
        'expense_data': expense_category_sums
    }

    return render_template(
        'dashboard/index.html',
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        on_trip_vehicles=on_trip_vehicles,
        in_shop_vehicles=in_shop_vehicles,
        available_drivers=available_drivers,
        on_trip_drivers=on_trip_drivers,
        active_trips=active_trips,
        pending_trips=pending_trips,
        today_fuel_cost=today_fuel_cost,
        today_expenses=today_expenses,
        maintenance_due=maintenance_due,
        recent_trips=recent_trips,
        recent_maintenance=recent_maintenance,
        expiring_licenses=expiring_licenses,
        chart_data=chart_data
    )
