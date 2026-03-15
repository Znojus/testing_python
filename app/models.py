from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db

class User(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    role: so.Mapped[str] = so.mapped_column(sa.String(20), index=True)
    group: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50), index=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Task(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(200))
    description: so.Mapped[str] = so.mapped_column(sa.Text)
    created_by: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'))
    created_at: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)

    def __repr__(self):
        return '<Task {}>'.format(self.title)   