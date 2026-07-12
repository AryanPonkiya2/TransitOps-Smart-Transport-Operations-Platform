from app.extensions import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='info', nullable=False) # success, warning, danger, info
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True) # nullable for global
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User')

    @staticmethod
    def log_notification(title, message, category='info', user_id=None):
        noti = Notification(
            title=title,
            message=message,
            category=category,
            user_id=user_id
        )
        db.session.add(noti)
        # Commit will be handled by the session context calling it.
        return noti

    def __repr__(self):
        return f"<Notification {self.title} - Read: {self.is_read}>"

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(100), nullable=False) # Vehicles, Drivers, Trips, Maintenance, Fuel, Expenses, Auth
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='activity_logs')

    @staticmethod
    def log_activity(action, module, user_id=None):
        log = ActivityLog(
            user_id=user_id,
            action=action,
            module=module
        )
        db.session.add(log)
        return log

    def __repr__(self):
        return f"<ActivityLog {self.action} by User {self.user_id}>"

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    table_name = db.Column(db.String(100), nullable=False)
    row_id = db.Column(db.Integer, nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # INSERT, UPDATE, DELETE
    old_value = db.Column(db.Text, nullable=True) # JSON representation
    new_value = db.Column(db.Text, nullable=True) # JSON representation
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User')

    @staticmethod
    def log_audit(table_name, row_id, action_type, old_value=None, new_value=None, user_id=None):
        log = AuditLog(
            user_id=user_id,
            table_name=table_name,
            row_id=row_id,
            action_type=action_type,
            old_value=old_value,
            new_value=new_value
        )
        db.session.add(log)
        return log

    def __repr__(self):
        return f"<AuditLog {self.action_type} on {self.table_name} Row {self.row_id}>"
