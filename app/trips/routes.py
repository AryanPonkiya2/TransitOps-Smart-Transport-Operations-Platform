from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.trips import trips_bp
from app.trips.forms import TripForm, TripCompleteForm
from app.models import Trip, TripHistory, Vehicle, Driver, FuelLog, FuelType, Expense, ExpenseCategory, ActivityLog, AuditLog, Notification
from app.extensions import db
from app.utils.decorators import role_required
from datetime import datetime, date

@trips_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    status_filter = request.args.get('status', '', type=str)
    sort_by = request.args.get('sort_by', 'created_date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    query = Trip.query

    # Driver role limits
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver:
            return render_template('trips/index.html', trips=[], pagination=None, search='', status_filter='', sort_by=sort_by, sort_order=sort_order)
        query = query.filter(Trip.driver_id == driver.id)
    
    if search_query:
        query = query.filter(
            (Trip.trip_code.ilike(f'%{search_query}%')) |
            (Trip.source.ilike(f'%{search_query}%')) |
            (Trip.destination.ilike(f'%{search_query}%'))
        )

    if status_filter:
        query = query.filter(Trip.status == status_filter)

    if hasattr(Trip, sort_by):
        column = getattr(Trip, sort_by)
        if sort_order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Trip.created_date.desc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    trips = pagination.items

    return render_template(
        'trips/index.html',
        trips=trips,
        pagination=pagination,
        search=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@trips_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def create():
    form = TripForm()
    
    # Choices (exclude retired and suspended)
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    drivers = Driver.query.filter(Driver.status != 'suspended').all()
    
    form.vehicle_id.choices = [(0, '-- Select Vehicle --')] + [(v.id, f"{v.registration_number} - {v.name} (Max: {v.max_load_capacity}kg, Status: {v.status.title()})") for v in vehicles]
    form.driver_id.choices = [(0, '-- Select Driver --')] + [(d.id, f"{d.name} (Status: {d.status.title()})") for d in drivers]
    
    if form.validate_on_submit():
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        driver = Driver.query.get(form.driver_id.data)
        
        # Validations
        if vehicle.status == 'in_shop':
            form.vehicle_id.errors.append("Vehicle in Shop cannot be selected.")
            return render_template('trips/create.html', form=form)
        if vehicle.status == 'retired':
            form.vehicle_id.errors.append("Retired Vehicle cannot be selected.")
            return render_template('trips/create.html', form=form)
        if driver.status == 'suspended':
            form.driver_id.errors.append("Suspended Driver cannot be selected.")
            return render_template('trips/create.html', form=form)
        if driver.is_license_expired:
            form.driver_id.errors.append("Expired License Driver cannot be selected.")
            return render_template('trips/create.html', form=form)
            
        trip = Trip(
            trip_code=Trip.generate_trip_code(),
            source=form.source.data.strip(),
            destination=form.destination.data.strip(),
            vehicle_id=form.vehicle_id.data,
            driver_id=form.driver_id.data,
            cargo_weight=form.cargo_weight.data,
            distance=form.distance.data,
            trip_notes=form.trip_notes.data,
            status='draft'
        )
        db.session.add(trip)
        db.session.flush()
        
        # Log History and Activity
        trip.log_history('draft', 'Trip request created as Draft.', current_user.id)
        
        ActivityLog.log_activity(
            action=f"Created trip request {trip.trip_code} from {trip.source} to {trip.destination}",
            module="Trips",
            user_id=current_user.id
        )
        
        Notification.log_notification(
            title="New Trip Created",
            message=f"Trip request {trip.trip_code} was created in Draft from {trip.source} to {trip.destination}.",
            category="info"
        )
        
        db.session.commit()
        flash(f"Trip {trip.trip_code} created as Draft. Ready for dispatch.", "success")
        return redirect(url_for('trips.index'))
        
    return render_template('trips/create.html', form=form)

@trips_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def edit(id):
    trip = Trip.query.get_or_404(id)
    if trip.status != 'draft':
        flash("Only Draft trips can be modified.", "warning")
        return redirect(url_for('trips.details', id=trip.id))
        
    form = TripForm(trip_id=trip.id, obj=trip)
    
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    drivers = Driver.query.filter(Driver.status != 'suspended').all()
    
    form.vehicle_id.choices = [(0, '-- Select Vehicle --')] + [(v.id, f"{v.registration_number} - {v.name} (Max: {v.max_load_capacity}kg, Status: {v.status.title()})") for v in vehicles]
    form.driver_id.choices = [(0, '-- Select Driver --')] + [(d.id, f"{d.name} (Status: {d.status.title()})") for d in drivers]
    
    if form.validate_on_submit():
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        driver = Driver.query.get(form.driver_id.data)
        
        # Validations (excluding current assigned vehicle/driver from blocking itself if unchanged)
        if vehicle.status == 'in_shop' and trip.vehicle_id != vehicle.id:
            form.vehicle_id.errors.append("Vehicle in Shop cannot be selected.")
            return render_template('trips/edit.html', form=form, trip=trip)
        if vehicle.status == 'retired':
            form.vehicle_id.errors.append("Retired Vehicle cannot be selected.")
            return render_template('trips/edit.html', form=form, trip=trip)
        if driver.status == 'suspended':
            form.driver_id.errors.append("Suspended Driver cannot be selected.")
            return render_template('trips/edit.html', form=form, trip=trip)
        if driver.is_license_expired:
            form.driver_id.errors.append("Expired License Driver cannot be selected.")
            return render_template('trips/edit.html', form=form, trip=trip)
            
        trip.source = form.source.data.strip()
        trip.destination = form.destination.data.strip()
        trip.vehicle_id = form.vehicle_id.data
        trip.driver_id = form.driver_id.data
        trip.cargo_weight = form.cargo_weight.data
        trip.distance = form.distance.data
        trip.trip_notes = form.trip_notes.data
        
        trip.log_history('draft', 'Trip request details updated.', current_user.id)
        
        db.session.commit()
        flash(f"Trip {trip.trip_code} details updated.", "success")
        return redirect(url_for('trips.details', id=trip.id))
        
    return render_template('trips/edit.html', form=form, trip=trip)

@trips_bp.route('/<int:id>')
@login_required
def details(id):
    trip = Trip.query.get_or_404(id)
    
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver or trip.driver_id != driver.id:
            abort(403)
            
    return render_template('trips/details.html', trip=trip)

@trips_bp.route('/dispatch/<int:id>', methods=['POST'])
@login_required
def dispatch(id):
    trip = Trip.query.get_or_404(id)
    
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver or trip.driver_id != driver.id:
            abort(403)
    elif current_user.role not in ['Fleet Manager', 'Safety Officer', 'Administrator']:
        abort(403)

    if trip.status != 'draft':
        flash("Only Draft trips can be dispatched.", "warning")
        return redirect(url_for('trips.details', id=trip.id))
        
    vehicle = trip.vehicle
    driver = trip.driver
    
    # Strict Business Validations on Dispatch
    if vehicle.status == 'in_shop':
        flash("Dispatch failed: Vehicle is In Shop.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
    if vehicle.status == 'retired':
        flash("Dispatch failed: Vehicle is Retired.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
    if vehicle.status == 'on_trip':
        flash("Dispatch failed: Vehicle is already on another active trip.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
        
    if driver.status == 'suspended':
        flash("Dispatch failed: Driver is Suspended.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
    if driver.status == 'on_trip':
        flash("Dispatch failed: Driver is already driving another active trip.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
    if driver.is_license_expired:
        flash("Dispatch failed: Driver license is expired.", "danger")
        return redirect(url_for('trips.details', id=trip.id))
        
    if trip.cargo_weight > vehicle.max_load_capacity:
        flash(f"Dispatch failed: Cargo Weight ({trip.cargo_weight} kg) exceeds vehicle max capacity ({vehicle.max_load_capacity} kg).", "danger")
        return redirect(url_for('trips.details', id=trip.id))
        
    # Process status updates
    trip.status = 'dispatched'
    trip.dispatch_date = datetime.utcnow()
    vehicle.status = 'on_trip'
    driver.status = 'on_trip'
    
    trip.log_history('dispatched', 'Trip successfully Dispatched. Vehicle & Driver status set to On Trip.', current_user.id)
    
    ActivityLog.log_activity(
        action=f"Dispatched trip {trip.trip_code} with vehicle {vehicle.registration_number} and driver {driver.name}",
        module="Trips",
        user_id=current_user.id
    )
    
    Notification.log_notification(
        title="Trip Dispatched",
        message=f"Trip {trip.trip_code} was dispatched. Vehicle {vehicle.registration_number} & Driver {driver.name} are now On Trip.",
        category="warning",
        user_id=driver.user_id # Notify specific driver
    )
    
    db.session.commit()
    flash(f"Trip {trip.trip_code} dispatched successfully. Vehicle and driver status updated to On Trip.", "success")
    return redirect(url_for('trips.details', id=trip.id))

@trips_bp.route('/complete/<int:id>', methods=['GET', 'POST'])
@login_required
def complete(id):
    trip = Trip.query.get_or_404(id)
    
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver or trip.driver_id != driver.id:
            abort(403)
    elif current_user.role not in ['Fleet Manager', 'Financial Analyst', 'Administrator']:
        abort(403)

    if trip.status != 'dispatched':
        flash("Only Dispatched trips can be completed.", "warning")
        return redirect(url_for('trips.details', id=trip.id))
        
    form = TripCompleteForm(start_odometer=trip.vehicle.current_odometer)
    
    if form.validate_on_submit():
        final_odom = form.final_odometer.data
        fuel_qty = form.fuel_consumed.data
        closing_notes = form.trip_notes.data
        
        fuel_price = request.form.get('fuel_price', 0.0, type=float)
        fuel_station = request.form.get('fuel_station', 'Self Station', type=str).strip()
        
        # 1. Update Trip
        trip.status = 'completed'
        trip.completion_date = datetime.utcnow()
        trip.final_odometer = final_odom
        trip.fuel_consumed = fuel_qty
        trip.trip_notes = closing_notes
        
        # 2. Update Vehicle and Driver Status
        vehicle = trip.vehicle
        driver = trip.driver
        
        vehicle.current_odometer = final_odom
        vehicle.status = 'available'
        driver.status = 'available'
        
        trip.log_history('completed', f"Trip completed. Vehicle odometer updated to {final_odom} km. Driver status set to Available.", current_user.id)
        
        # 3. Create Fuel log & Expense if fuel recorded
        if fuel_qty > 0 and fuel_price > 0:
            total_fuel_cost = round(fuel_qty * fuel_price, 2)
            
            # Find or create FuelType
            ft = FuelType.query.filter_by(name=vehicle.fuel_type_name).first()
            if not ft:
                ft = FuelType(name=vehicle.fuel_type_name or 'Diesel')
                db.session.add(ft)
                db.session.flush()
                
            fuel_log = FuelLog(
                vehicle_id=vehicle.id,
                trip_id=trip.id,
                fuel_type_id=ft.id,
                fuel_quantity=fuel_qty,
                fuel_price=fuel_price,
                fuel_station=fuel_station,
                date=date.today()
            )
            db.session.add(fuel_log)
            db.session.flush()
            
            # Find or create ExpenseCategory for 'Fuel'
            cat = ExpenseCategory.query.filter_by(name='Fuel').first()
            if not cat:
                cat = ExpenseCategory(name='Fuel', description='Fuel Charges')
                db.session.add(cat)
                db.session.flush()
                
            expense = Expense(
                vehicle_id=vehicle.id,
                trip_id=trip.id,
                expense_category_id=cat.id,
                amount=total_fuel_cost,
                description=f"Auto-generated fuel expense for Trip {trip.trip_code} via completion form at {fuel_station}.",
                date=date.today()
            )
            db.session.add(expense)
            
        ActivityLog.log_activity(
            action=f"Completed trip {trip.trip_code} with vehicle {vehicle.registration_number}",
            module="Trips",
            user_id=current_user.id
        )
        
        Notification.log_notification(
            title="Trip Completed",
            message=f"Trip {trip.trip_code} was completed. Vehicle {vehicle.registration_number} has returned. Driver {driver.name} is now Available.",
            category="success"
        )
        
        db.session.commit()
        flash(f"Trip {trip.trip_code} completed successfully. Vehicle and driver status updated to Available.", "success")
        return redirect(url_for('trips.details', id=trip.id))
        
    return render_template('trips/complete.html', form=form, trip=trip)

@trips_bp.route('/cancel/<int:id>', methods=['POST'])
@login_required
def cancel(id):
    trip = Trip.query.get_or_404(id)
    
    if current_user.role == 'Driver':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver or trip.driver_id != driver.id:
            abort(403)
    elif current_user.role not in ['Fleet Manager', 'Safety Officer', 'Administrator']:
        abort(403)

    if trip.status not in ['draft', 'dispatched']:
        flash("Only draft or dispatched trips can be cancelled.", "warning")
        return redirect(url_for('trips.details', id=trip.id))
        
    vehicle = trip.vehicle
    driver = trip.driver
    
    trip.status = 'cancelled'
    
    # Restore status if dispatched
    if vehicle.status == 'on_trip':
        vehicle.status = 'available'
    if driver.status == 'on_trip':
        driver.status = 'available'
        
    trip.log_history('cancelled', 'Trip cancelled. Assigned vehicle and driver status restored to Available.', current_user.id)
    
    ActivityLog.log_activity(
        action=f"Cancelled trip {trip.trip_code}",
        module="Trips",
        user_id=current_user.id
    )
    
    Notification.log_notification(
        title="Trip Cancelled",
        message=f"Trip {trip.trip_code} was cancelled. Assigned assets are now Available.",
        category="danger"
    )
    
    db.session.commit()
    flash(f"Trip {trip.trip_code} cancelled. Assigned assets status restored to Available.", "success")
    return redirect(url_for('trips.details', id=trip.id))

@trips_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager')
def delete(id):
    trip = Trip.query.get_or_404(id)
    code = trip.trip_code
    
    ActivityLog.log_activity(
        action=f"Deleted trip request {code}",
        module="Trips",
        user_id=current_user.id
    )
    AuditLog.log_audit(
        table_name="trips",
        row_id=trip.id,
        action_type="DELETE",
        old_value=f"Code: {trip.trip_code}, Status: {trip.status}",
        user_id=current_user.id
    )
    
    db.session.delete(trip)
    db.session.commit()
    flash(f"Trip request {code} deleted successfully.", "success")
    return redirect(url_for('trips.index'))

@trips_bp.route('/api/<int:id>', methods=['GET'])
@login_required
def get_trip_api(id):
    trip = Trip.query.get_or_404(id)
    return jsonify({
        'id': trip.id,
        'vehicle_id': trip.vehicle_id,
        'driver_id': trip.driver_id,
        'vehicle_name': trip.vehicle.name,
        'vehicle_reg': trip.vehicle.registration_number
    })
