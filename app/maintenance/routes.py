from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.maintenance import maintenance_bp
from app.maintenance.forms import MaintenanceForm
from app.models import Maintenance, MaintenanceType, Vehicle, Expense, ExpenseCategory, ActivityLog, AuditLog, Notification
from app.extensions import db
from app.utils.decorators import role_required
from datetime import date

@maintenance_bp.route('/')
@login_required
@role_required('Fleet Manager', 'Safety Officer', 'Financial Analyst')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    status_filter = request.args.get('status', '', type=str)
    type_filter = request.args.get('type', '', type=str)
    sort_by = request.args.get('sort_by', 'start_date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    query = Maintenance.query.join(Vehicle).join(MaintenanceType)

    if search_query:
        query = query.filter(
            (Maintenance.description.ilike(f'%{search_query}%')) |
            (MaintenanceType.name.ilike(f'%{search_query}%')) |
            (Vehicle.registration_number.ilike(f'%{search_query}%')) |
            (Vehicle.name.ilike(f'%{search_query}%'))
        )

    if status_filter:
        query = query.filter(Maintenance.status == status_filter)
    if type_filter:
        query = query.filter(MaintenanceType.name == type_filter)

    if sort_by == 'registration_number':
        column = Vehicle.registration_number
    elif sort_by == 'type':
        column = MaintenanceType.name
    elif hasattr(Maintenance, sort_by):
        column = getattr(Maintenance, sort_by)
    else:
        column = Maintenance.start_date

    if sort_order == 'desc':
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    maintenances = pagination.items
    
    types = MaintenanceType.query.all()

    return render_template(
        'maintenance/index.html',
        maintenances=maintenances,
        pagination=pagination,
        types=types,
        search=search_query,
        status_filter=status_filter,
        type_filter=type_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@maintenance_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def create():
    form = MaintenanceForm()
    
    # Refresh choices (exclude retired)
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    form.vehicle_id.choices = [(v.id, f"{v.registration_number} - {v.name} (Status: {v.status.title()})") for v in vehicles]
    
    if form.validate_on_submit():
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        
        maintenance = Maintenance(
            vehicle_id=form.vehicle_id.data,
            maintenance_type_id=form.maintenance_type_id.data,
            description=form.description.data.strip(),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            cost=form.cost.data,
            status=form.status.data
        )
        db.session.add(maintenance)
        db.session.flush() # get ID
        
        # ERP Business Logic
        if maintenance.status in ['pending', 'in_progress']:
            vehicle.status = 'in_shop'
            Notification.log_notification(
                title="Vehicle In Shop",
                message=f"Vehicle {vehicle.registration_number} is scheduled for maintenance ({maintenance.type}) and is now In Shop.",
                category="warning"
            )
        elif maintenance.status == 'completed':
            vehicle.status = 'available'
            # Auto-generate Expense under Category 'Repair'
            cat = ExpenseCategory.query.filter_by(name='Repair').first()
            if not cat:
                cat = ExpenseCategory(name='Repair', description='Repair and maintenance costs')
                db.session.add(cat)
                db.session.flush()
                
            expense = Expense(
                vehicle_id=vehicle.id,
                expense_category_id=cat.id,
                amount=maintenance.cost,
                description=f"Auto-generated repair expense for Maintenance Record #{maintenance.id}: {maintenance.type}.",
                date=maintenance.end_date
            )
            db.session.add(expense)
            Notification.log_notification(
                title="Maintenance Completed",
                message=f"Maintenance for vehicle {vehicle.registration_number} completed. Vehicle returned to Available.",
                category="success"
            )
            
        ActivityLog.log_activity(
            action=f"Logged maintenance for vehicle {vehicle.registration_number}. Cost: ₹{maintenance.cost}. Status: {maintenance.status}",
            module="Maintenance",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="maintenances",
            row_id=maintenance.id,
            action_type="INSERT",
            new_value=f"Vehicle ID: {maintenance.vehicle_id}, Cost: {maintenance.cost}, Status: {maintenance.status}",
            user_id=current_user.id
        )
            
        db.session.commit()
        flash(f"Maintenance logged for vehicle {vehicle.registration_number}. Status: {maintenance.status.title()}.", "success")
        return redirect(url_for('maintenance.index'))
        
    return render_template('maintenance/create.html', form=form)

@maintenance_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def edit(id):
    maintenance = Maintenance.query.get_or_404(id)
    form = MaintenanceForm(obj=maintenance)
    
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    form.vehicle_id.choices = [(v.id, f"{v.registration_number} - {v.name} (Status: {v.status.title()})") for v in vehicles]
    
    if form.validate_on_submit():
        old_val = f"Vehicle ID: {maintenance.vehicle_id}, Cost: {maintenance.cost}, Status: {maintenance.status}"
        
        maintenance.vehicle_id = form.vehicle_id.data
        maintenance.maintenance_type_id = form.maintenance_type_id.data
        maintenance.description = form.description.data.strip()
        maintenance.start_date = form.start_date.data
        maintenance.end_date = form.end_date.data
        maintenance.cost = form.cost.data
        maintenance.status = form.status.data
        
        vehicle = Vehicle.query.get(maintenance.vehicle_id)
        
        # Apply ERP status updates
        if maintenance.status in ['pending', 'in_progress']:
            vehicle.status = 'in_shop'
        elif maintenance.status == 'completed':
            vehicle.status = 'available'
            
            # Check if repair expense was already generated
            cat = ExpenseCategory.query.filter_by(name='Repair').first()
            if not cat:
                cat = ExpenseCategory(name='Repair', description='Repair and maintenance costs')
                db.session.add(cat)
                db.session.flush()
                
            match_str = f"Maintenance Record #{maintenance.id}:"
            existing_expense = Expense.query.filter(
                Expense.vehicle_id == vehicle.id,
                Expense.expense_category_id == cat.id,
                Expense.description.like(f"%{match_str}%")
            ).first()
            
            if not existing_expense:
                expense = Expense(
                    vehicle_id=vehicle.id,
                    expense_category_id=cat.id,
                    amount=maintenance.cost,
                    description=f"Auto-generated repair expense for Maintenance Record #{maintenance.id}: {maintenance.type}.",
                    date=maintenance.end_date
                )
                db.session.add(expense)
            else:
                existing_expense.amount = maintenance.cost
                existing_expense.date = maintenance.end_date
                existing_expense.description = f"Auto-generated repair expense for Maintenance Record #{maintenance.id}: {maintenance.type}."
                
            Notification.log_notification(
                title="Maintenance Work Completed",
                message=f"Maintenance order #{maintenance.id} for {vehicle.registration_number} completed. Vehicle returned to Available.",
                category="success"
            )
                
        ActivityLog.log_activity(
            action=f"Updated maintenance record #{maintenance.id} for vehicle {vehicle.registration_number}",
            module="Maintenance",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="maintenances",
            row_id=maintenance.id,
            action_type="UPDATE",
            old_value=old_val,
            new_value=f"Vehicle ID: {maintenance.vehicle_id}, Cost: {maintenance.cost}, Status: {maintenance.status}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash(f"Maintenance record updated for vehicle {vehicle.registration_number}.", "success")
        return redirect(url_for('maintenance.index'))
        
    return render_template('maintenance/edit.html', form=form, maintenance=maintenance)

@maintenance_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Safety Officer')
def delete(id):
    maintenance = Maintenance.query.get_or_404(id)
    vehicle = maintenance.vehicle
    
    ActivityLog.log_activity(
        action=f"Deleted maintenance record #{maintenance.id} for vehicle {vehicle.registration_number}",
        module="Maintenance",
        user_id=current_user.id
    )
    AuditLog.log_audit(
        table_name="maintenances",
        row_id=maintenance.id,
        action_type="DELETE",
        old_value=f"Vehicle ID: {maintenance.vehicle_id}, Cost: {maintenance.cost}, Status: {maintenance.status}",
        user_id=current_user.id
    )
    
    db.session.delete(maintenance)
    db.session.commit()
    
    # Check if vehicle has other active maintenance records. If not, restore to available!
    active_maint = Maintenance.query.filter(
        Maintenance.vehicle_id == vehicle.id,
        Maintenance.status.in_(['pending', 'in_progress'])
    ).count()
    
    if active_maint == 0 and vehicle.status == 'in_shop':
        vehicle.status = 'available'
        db.session.commit()
        
    flash("Maintenance record deleted successfully.", "success")
    return redirect(url_for('maintenance.index'))
