from app import app
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, RegistrationForm, SubmitTaskForm, TestCaseForm, SubmissionForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app import db
from app.models import User, Task, TestCase, Submission
from urllib.parse import urlsplit
from app.docker_runner import run_student_code

@app.route('/')
@app.route('/index')
@login_required
def index():
    tasks = db.session.execute(sa.select(Task)).scalars().all()
    return render_template('index.html', title='Home', tasks=tasks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data, group=form.group.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/create-task', methods=['GET', 'POST'])
@login_required
def create_task():
    if current_user.role != 'lecturer':
        flash('Only lecturers can create tasks.')
        return (redirect(url_for('index')))
    form = SubmitTaskForm()
    if form.validate_on_submit():
        task = Task(
            title = form.title.data,
            description = form.description.data,
            created_by = current_user.id,
            show_examples=form.show_examples.data
            )
        db.session.add(task)
        db.session.commit()
        flash('Task created!')
        return redirect(url_for('index'))
    return render_template('create_task.html', form=form)

@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_view(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        flash('Task not found.')
        return redirect(url_for('index'))
    test_cases = db.session.execute(
        sa.select(TestCase).where(TestCase.task_id == task_id)
    ).scalars().all()
    return render_template('task.html', task=task, test_cases=test_cases)

@app.route('/task/<int:task_id>/add-test', methods=['GET', 'POST'])
@login_required
def add_test_case(task_id):
    if current_user.role != 'lecturer':
        return (redirect(url_for('index')))
    form = TestCaseForm()
    if form.validate_on_submit():
        test = TestCase(
            task_id = task_id,
            input_data = form.input_data.data,
            expected_output = form.expected_output.data
            )
        db.session.add(test)
        db.session.commit()
        flash('Test case added!')
    return render_template('add_test_case.html', form=form, task_id=task_id)

@app.route('/task/<int:task_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_solution(task_id):
    if current_user.role != 'student':
        return redirect(url_for('index'))
    student_id = current_user.id
    form = SubmissionForm()
    if form.validate_on_submit():
        file = form.code_file.data
        code = file.read().decode('utf-8')

        if len(code) > 50000:
            flash('File is too large')
            return redirect(url_for('submit_solution', task_id=task_id))
        
        submission = Submission(
            task_id=task_id,
            user_id=student_id,
            code=code,
            result="PENDING"
        )
        db.session.add(submission)

        #testavimas ----------------
        test_cases = db.session.execute(
            sa.select(TestCase).where(TestCase.task_id == task_id)
        ).scalars().all()

        tests_data = [
            {"input": t.input_data, "expected": t.expected_output}
            for t in test_cases
        ]

        db.session.commit()
        submission_id = submission.id

        results = []
        all_passed = True
        for test in tests_data:
            result = run_student_code(code, test["input"])
            passed = (result["status"] == "SUCCESS" 
                     and result["output"] == test["expected"].strip())
            results.append({
                "input": test["input"],
                "expected": test["expected"],
                "actual": result["output"],
                "status": result["status"],
                "passed": passed
            })
            if not passed:
                all_passed = False

        submission_to_update = db.session.get(Submission, submission_id)
        submission_to_update.result = "PASSED" if all_passed else "FAILED"
        db.session.commit()

        return render_template('results.html', results=results, submission=submission_to_update, task_id=task_id)

    return render_template('submit_solution.html', form = form, task_id = task_id)