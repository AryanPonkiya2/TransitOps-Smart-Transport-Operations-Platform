from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app.vehicles import vehicles_bp
from app.vehicles.forms import VehicleForm
from app.models import Vehicle, VehicleType, FuelType, VehicleDocument, Trip, Maintenance, FuelLog, Expense, ActivityLog, AuditLog
from app.extensions import db
from app.utils.decorators import role_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime

@vehicles_bp.route('/')
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Financial Analyst')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    status_filter = request.args.get('status', '', type=str)
    type_filter = request.args.get('type', '', type=str)
    sort_by = request.args.get('sort_by', 'registration_number', type=str)
    sort_order = request.args.get('sort_order', 'asc', type=str)

    query = Vehicle.query.join(VehicleType)

    if search_query:
        query = query.filter(
            (Vehicle.registration_number.ilike(f'%{search_query}%')) |
            (Vehicle.name.ilike(f'%{search_query}%')) |
            (Vehicle.model.ilike(f'%{search_query}%')) |
            (VehicleType.name.ilike(f'%{search_query}%'))
        )

    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if type_filter:
        query = query.filter(VehicleType.name == type_filter)

    if sort_by == 'type':
        column = VehicleType.name
    elif hasattr(Vehicle, sort_by):
        column = getattr(Vehicle, sort_by)
    else:
        column = Vehicle.registration_number

    if sort_order == 'desc':
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    vehicles = pagination.items
    
    types = VehicleType.query.all()

    return render_template(
        'vehicles/index.html',
        vehicles=vehicles,
        pagination=pagination,
        types=types,
        search=search_query,
        status_filter=status_filter,
        type_filter=type_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@vehicles_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def create():
    form = VehicleForm()
    if form.validate_on_submit():
        vehicle = Vehicle(
            registration_number=form.registration_number.data.strip().upper(),
            name=form.name.data.strip(),
            model=form.model.data.strip(),
            vehicle_type_id=form.vehicle_type_id.data,
            fuel_type_id=form.fuel_type_id.data,
            max_load_capacity=form.max_load_capacity.data,
            current_odometer=form.current_odometer.data,
            purchase_date=form.purchase_date.data,
            acquisition_cost=form.acquisition_cost.data,
            insurance_expiry=form.insurance_expiry.data,
            rc_expiry=form.rc_expiry.data,
            status=form.status.data
        )
        db.session.add(vehicle)
        db.session.flush() # get vehicle ID

        # Logging action
        ActivityLog.log_activity(
            action=f"Registered vehicle {vehicle.registration_number} ({vehicle.name})",
            module="Vehicles",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="vehicles",
            row_id=vehicle.id,
            action_type="INSERT",
            new_value=f"Reg: {vehicle.registration_number}, Type ID: {vehicle.vehicle_type_id}, Status: {vehicle.status}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash(f"Vehicle {vehicle.registration_number} has been registered successfully.", "success")
        return redirect(url_for('vehicles.index'))
    
    return render_template('vehicles/create.html', form=form)

@vehicles_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def edit(id):
    vehicle = Vehicle.query.get_or_404(id)
    form = VehicleForm(vehicle_id=vehicle.id, obj=vehicle)
    
    if form.validate_on_submit():
        old_val = f"Reg: {vehicle.registration_number}, Type ID: {vehicle.vehicle_type_id}, Status: {vehicle.status}"
        
        # Read parameters from form
        vehicle.registration_number = form.registration_number.data.strip().upper()
        vehicle.name = form.name.data.strip()
        vehicle.model = form.model.data.strip()
        vehicle.vehicle_type_id = form.vehicle_type_id.data
        vehicle.fuel_type_id = form.fuel_type_id.data
        vehicle.max_load_capacity = form.max_load_capacity.data
        vehicle.current_odometer = form.current_odometer.data
        vehicle.purchase_date = form.purchase_date.data
        vehicle.acquisition_cost = form.acquisition_cost.data
        vehicle.insurance_expiry = form.insurance_expiry.data
        vehicle.rc_expiry = form.rc_expiry.data
        vehicle.status = form.status.data
        
        # Logging action
        ActivityLog.log_activity(
            action=f"Updated vehicle details for {vehicle.registration_number}",
            module="Vehicles",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="vehicles",
            row_id=vehicle.id,
            action_type="UPDATE",
            old_value=old_val,
            new_value=f"Reg: {vehicle.registration_number}, Type ID: {vehicle.vehicle_type_id}, Status: {vehicle.status}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash(f"Vehicle {vehicle.registration_number} details updated.", "success")
        return redirect(url_for('vehicles.index'))
    
    return render_template('vehicles/edit.html', form=form, vehicle=vehicle)

@vehicles_bp.route('/<int:id>')
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Financial Analyst')
def details(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    trips = Trip.query.filter_by(vehicle_id=vehicle.id).order_by(Trip.created_date.desc()).all()
    maintenances = Maintenance.query.filter_by(vehicle_id=vehicle.id).order_by(Maintenance.start_date.desc()).all()
    fuel_logs = FuelLog.query.filter_by(vehicle_id=vehicle.id).order_by(FuelLog.date.desc()).all()
    expenses = Expense.query.filter_by(vehicle_id=vehicle.id).order_by(Expense.date.desc()).all()
    documents = VehicleDocument.query.filter_by(vehicle_id=vehicle.id).all()
    
    return render_template(
        'vehicles/details.html',
        vehicle=vehicle,
        trips=trips,
        maintenances=maintenances,
        fuel_logs=fuel_logs,
        expenses=expenses,
        documents=documents
    )

@vehicles_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager')
def delete(id):
    vehicle = Vehicle.query.get_or_404(id)
    reg_number = vehicle.registration_number
    
    # Logging action
    ActivityLog.log_activity(
        action=f"Deleted vehicle {reg_number}",
        module="Vehicles",
        user_id=current_user.id
    )
    AuditLog.log_audit(
        table_name="vehicles",
        row_id=vehicle.id,
        action_type="DELETE",
        old_value=f"Reg: {vehicle.registration_number}, Type ID: {vehicle.vehicle_type_id}, Status: {vehicle.status}",
        user_id=current_user.id
    )
    
    db.session.delete(vehicle)
    db.session.commit()
    flash(f"Vehicle {reg_number} deleted successfully.", "success")
    return redirect(url_for('vehicles.index'))

@vehicles_bp.route('/<int:id>/document/upload', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def upload_document(id):
    vehicle = Vehicle.query.get_or_404(id)
    doc_name = request.form.get('document_name')
    doc_type = request.form.get('document_type')
    expiry_date_str = request.form.get('expiry_date')
    file = request.files.get('file')

    if not doc_name or not doc_type or not expiry_date_str or not file:
        flash("All fields and file are required for uploading vehicle document.", "danger")
        return redirect(url_for('vehicles.details', id=vehicle.id))

    try:
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for('vehicles.details', id=vehicle.id))

    filename = secure_filename(file.filename)
    # prepend timestamp to avoid collisions
    filename = f"{int(datetime.now().timestamp())}_{filename}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    doc = VehicleDocument(
        vehicle_id=vehicle.id,
        document_name=doc_name,
        document_type=doc_type,
        expiry_date=expiry_date,
        file_path=filename
    )
    db.session.add(doc)
    
    ActivityLog.log_activity(
        action=f"Uploaded document '{doc_name}' for vehicle {vehicle.registration_number}",
        module="Vehicles",
        user_id=current_user.id
    )
    db.session.commit()
    flash("Document uploaded successfully.", "success")
    return redirect(url_for('vehicles.details', id=vehicle.id))

@vehicles_bp.route('/document/delete/<int:doc_id>', methods=['POST'])
@login_required
@role_required('Fleet Manager')
def delete_document(doc_id):
    doc = VehicleDocument.query.get_or_404(doc_id)
    vehicle_id = doc.vehicle_id
    vehicle_reg = doc.vehicle.registration_number
    doc_name = doc.document_name
    
    ActivityLog.log_activity(
        action=f"Deleted document '{doc_name}' for vehicle {vehicle_reg}",
        module="Vehicles",
        user_id=current_user.id
    )
    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted successfully.", "success")
    return redirect(url_for('vehicles.details', id=vehicle_id))
