import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from app.models import User, Task, Submission, TestCase

@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Task': Task, 'Submission': Submission, 'TestCase': TestCase}

@app.cli.command("reset-db")
def reset_db():
    from app import db
    from app.models import (
        Submission, TestCase, ExamTask, ExamStudent,
        Task, Exam, User
    )

    db.session.query(Submission).delete()
    db.session.query(TestCase).delete()
    db.session.query(ExamTask).delete()
    db.session.query(ExamStudent).delete()
    db.session.query(Task).delete()
    db.session.query(Exam).delete()
    db.session.query(User).delete()

    db.session.commit()
    print("Database fully cleared.")