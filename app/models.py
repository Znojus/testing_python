from typing import Optional
from datetime import datetime, timezone
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    role: so.Mapped[str] = so.mapped_column(sa.String(20))
    group: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(200))
    description: so.Mapped[str] = so.mapped_column(sa.Text)
    created_by: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    created_at: so.Mapped[datetime] = so.mapped_column(index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Task {}>'.format(self.title)
    
class TestCase(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task.id'), index=True)
    input_data: so.Mapped[str] = so.mapped_column(sa.Text)
    expected_output: so.Mapped[str] = so.mapped_column(sa.Text)

    def __repr__(self):
        return '<TestCase for Task {}>'.format(self.task_id)


class Submission(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task.id'), index=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    code: so.Mapped[str] = so.mapped_column(sa.Text)
    result: so.Mapped[str] = so.mapped_column(sa.String(20), default="PENDING")
    submitted_at: so.Mapped[datetime] = so.mapped_column(index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Submission by User {} for Task {}>'.format(self.user_id, self.task_id)