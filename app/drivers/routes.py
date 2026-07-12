from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.drivers import drivers_bp
from app.drivers.forms import DriverForm
from app.models import Driver, DriverDocument, Trip, User, ActivityLog, AuditLog
from app.extensions import db
from app.utils.decorators import role_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime

@drivers_bp.route('/')
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Financial Analyst')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    status_filter = request.args.get('status', '', type=str)
    sort_by = request.args.get('sort_by', 'name', type=str)
    sort_order = request.args.get('sort_order', 'asc', type=str)

    query = Driver.query

    if search_query:
        query = query.filter(
            (Driver.name.ilike(f'%{search_query}%')) |
            (Driver.license_number.ilike(f'%{search_query}%')) |
            (Driver.phone.ilike(f'%{search_query}%')) |
            (Driver.email.ilike(f'%{search_query}%')) |
            (Driver.license_category.ilike(f'%{search_query}%'))
        )

    if status_filter:
        query = query.filter(Driver.status == status_filter)

    if hasattr(Driver, sort_by):
        column = getattr(Driver, sort_by)
        if sort_order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Driver.name.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    drivers = pagination.items

    return render_template(
        'drivers/index.html',
        drivers=drivers,
        pagination=pagination,
        search=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@drivers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def create():
    form = DriverForm()
    
    driver_users = User.query.filter_by(role='Driver', is_active=True).all()
    linked_user_ids = [d.user_id for d in Driver.query.filter(Driver.user_id != None).all()]
    available_users = [u for u in driver_users if u.id not in linked_user_ids]
    
    form.user_id.choices = [(0, '-- None (No Portal Access) --')] + [(u.id, f"{u.name} ({u.email})") for u in available_users]
    
    if form.validate_on_submit():
        photo_filename = None
        if form.photo_file.data:
            f = form.photo_file.data
            filename = secure_filename(f.filename)
            filename = f"{int(datetime.now().timestamp())}_{filename}"
            upload_dir = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            f.save(os.path.join(upload_dir, filename))
            photo_filename = filename
            
        driver = Driver(
            name=form.name.data.strip(),
            photo=photo_filename,
            license_number=form.license_number.data.strip().upper(),
            license_category=form.license_category.data,
            license_expiry=form.license_expiry.data,
            phone=form.phone.data.strip(),
            email=form.email.data.strip().lower(),
            address=form.address.data.strip(),
            emergency_contact_name=form.emergency_contact_name.data.strip(),
            emergency_contact_phone=form.emergency_contact_phone.data.strip(),
            safety_score=form.safety_score.data,
            status=form.status.data,
            user_id=form.user_id.data if form.user_id.data != 0 else None
        )
        
        db.session.add(driver)
        db.session.flush()

        # Audit Logs
        ActivityLog.log_activity(
            action=f"Added driver {driver.name} (License: {driver.license_number})",
            module="Drivers",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="drivers",
            row_id=driver.id,
            action_type="INSERT",
            new_value=f"Name: {driver.name}, License: {driver.license_number}, Status: {driver.status}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash(f"Driver {driver.name} has been added successfully.", "success")
        return redirect(url_for('drivers.index'))
        
    return render_template('drivers/create.html', form=form)

@drivers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def edit(id):
    driver = Driver.query.get_or_404(id)
    form = DriverForm(driver_id=driver.id, obj=driver)
    
    driver_users = User.query.filter_by(role='Driver', is_active=True).all()
    linked_user_ids = [d.user_id for d in Driver.query.filter(Driver.user_id != None, Driver.id != driver.id).all()]
    available_users = [u for u in driver_users if u.id not in linked_user_ids]
    
    form.user_id.choices = [(0, '-- None (No Portal Access) --')] + [(u.id, f"{u.name} ({u.email})") for u in available_users]
    
    if request.method == 'GET':
        form.user_id.data = driver.user_id or 0
        
    if form.validate_on_submit():
        old_val = f"Name: {driver.name}, License: {driver.license_number}, Status: {driver.status}"
        
        if form.photo_file.data:
            f = form.photo_file.data
            filename = secure_filename(f.filename)
            filename = f"{int(datetime.now().timestamp())}_{filename}"
            upload_dir = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            f.save(os.path.join(upload_dir, filename))
            driver.photo = filename
            
        driver.name = form.name.data.strip()
        driver.license_number = form.license_number.data.strip().upper()
        driver.license_category = form.license_category.data
        driver.license_expiry = form.license_expiry.data
        driver.phone = form.phone.data.strip()
        driver.email = form.email.data.strip().lower()
        driver.address = form.address.data.strip()
        driver.emergency_contact_name = form.emergency_contact_name.data.strip()
        driver.emergency_contact_phone = form.emergency_contact_phone.data.strip()
        driver.safety_score = form.safety_score.data
        driver.status = form.status.data
        driver.user_id = form.user_id.data if form.user_id.data != 0 else None
        
        ActivityLog.log_activity(
            action=f"Updated driver details for {driver.name}",
            module="Drivers",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="drivers",
            row_id=driver.id,
            action_type="UPDATE",
            old_value=old_val,
            new_value=f"Name: {driver.name}, License: {driver.license_number}, Status: {driver.status}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash(f"Driver {driver.name} profile updated.", "success")
        return redirect(url_for('drivers.index'))
        
    return render_template('drivers/edit.html', form=form, driver=driver)

@drivers_bp.route('/<int:id>')
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Financial Analyst')
def details(id):
    driver = Driver.query.get_or_404(id)
    trips = Trip.query.filter_by(driver_id=driver.id).order_by(Trip.created_date.desc()).all()
    documents = DriverDocument.query.filter_by(driver_id=driver.id).all()
    return render_template('drivers/details.html', driver=driver, trips=trips, documents=documents)

@drivers_bp.route('/change-status/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Administrator')
def change_status(id):
    driver = Driver.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status in ['available', 'on_trip', 'off_duty', 'suspended']:
        old_status = driver.status
        driver.status = new_status
        ActivityLog.log_activity(
            action=f"Changed driver {driver.name} status from {old_status} to {new_status}",
            module="Drivers",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="drivers",
            row_id=driver.id,
            action_type="UPDATE",
            old_value=f"Status: {old_status}",
            new_value=f"Status: {new_status}",
            user_id=current_user.id
        )
        db.session.commit()
        flash(f"Driver {driver.name} status updated to {new_status.title()}.", "success")
    return redirect(url_for('drivers.details', id=driver.id))

@drivers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def delete(id):
    driver = Driver.query.get_or_404(id)
    name = driver.name
    
    ActivityLog.log_activity(
        action=f"Deleted driver {name}",
        module="Drivers",
        user_id=current_user.id
    )
    AuditLog.log_audit(
        table_name="drivers",
        row_id=driver.id,
        action_type="DELETE",
        old_value=f"Name: {driver.name}, License: {driver.license_number}, Status: {driver.status}",
        user_id=current_user.id
    )
    
    db.session.delete(driver)
    db.session.commit()
    flash(f"Driver {name} deleted successfully.", "success")
    return redirect(url_for('drivers.index'))

@drivers_bp.route('/<int:id>/document/upload', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def upload_document(id):
    driver = Driver.query.get_or_404(id)
    doc_name = request.form.get('document_name')
    doc_type = request.form.get('document_type')
    expiry_date_str = request.form.get('expiry_date')
    file = request.files.get('file')

    if not doc_name or not doc_type or not file:
        flash("Fields and file are required for uploading driver document.", "danger")
        return redirect(url_for('drivers.details', id=driver.id))

    expiry_date = None
    if expiry_date_str:
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('drivers.details', id=driver.id))

    filename = secure_filename(file.filename)
    filename = f"{int(datetime.now().timestamp())}_{filename}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    doc = DriverDocument(
        driver_id=driver.id,
        document_name=doc_name,
        document_type=doc_type,
        expiry_date=expiry_date,
        file_path=filename
    )
    db.session.add(doc)
    
    ActivityLog.log_activity(
        action=f"Uploaded document '{doc_name}' for driver {driver.name}",
        module="Drivers",
        user_id=current_user.id
    )
    db.session.commit()
    flash("Driver document uploaded successfully.", "success")
    return redirect(url_for('drivers.details', id=driver.id))

@drivers_bp.route('/document/delete/<int:doc_id>', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def delete_document(doc_id):
    doc = DriverDocument.query.get_or_404(doc_id)
    driver_id = doc.driver_id
    driver_name = doc.driver.name
    doc_name = doc.document_name
    
    ActivityLog.log_activity(
        action=f"Deleted document '{doc_name}' for driver {driver_name}",
        module="Drivers",
        user_id=current_user.id
    )
    db.session.delete(doc)
    db.session.commit()
    flash("Driver document deleted successfully.", "success")
    return redirect(url_for('drivers.details', id=driver_id))
