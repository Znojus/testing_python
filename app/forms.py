from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
import sqlalchemy as sa
from app import db
from app.models import User
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.fields import DateTimeLocalField

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('student', 'Student'), ('lecturer', 'Lecturer')])
    group = StringField('Group')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('Username exists. Please use a different username.')
        
    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data))
        if user is not None:
            raise ValidationError('Email already exsists. Please use a different email address.')

class SubmitTaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Task Description', validators=[DataRequired()])
    show_examples = BooleanField('Show test case examples to students', default=True)
    submit = SubmitField('Add task')

class TestCaseForm(FlaskForm):
    input_data = TextAreaField('Standard Input', validators=[DataRequired()])
    expected_output = TextAreaField('Expected Output', validators=[DataRequired()])
    submit = SubmitField('Add task')

class SubmissionForm(FlaskForm):
    code_file = FileField('Upload .py file', validators=[FileRequired(), FileAllowed(['py'], 'Only .py files')])
    submit = SubmitField('Submit Solution')

class ExamForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    type = SelectField('Type', choices=[('homework', 'Homework'), ('test', 'Test'),
                                        ('exam', 'Exam')])
    deadline = DateTimeLocalField('Deadline (optional)')
    docker_image = StringField('Docker Image (optional)')
    allow_requirements = BooleanField('Allow students to upload requirements.txt')
    submit = SubmitField('Create Exam')