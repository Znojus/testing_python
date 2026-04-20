from app import app
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, RegistrationForm, SubmitTaskForm, TestCaseForm, SubmissionForm, ExamForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app import db
from app.models import User, Task, TestCase, Submission, Exam, ExamStudent, ExamTask
from urllib.parse import urlsplit
from app.docker_runner import run_student_code, validate_requirements
import docker
from datetime import datetime, timezone

@app.route('/')
@app.route('/index')
@login_required
def index():
    if current_user.role == 'lecturer':
        tasks = db.session.execute(sa.select(Task)).scalars().all()
        exams = db.session.execute(sa.select(Exam)).scalars().all()
        return render_template('index.html', tasks=tasks, exams=exams)
    else:
        exams = db.session.execute(
            sa.select(Exam).join(ExamStudent).where(ExamStudent.student_id == current_user.id)
        ).scalars().all()
        return render_template('student_index.html', exams=exams)

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

@app.route('/task/<int:task_id>')
@app.route('/exam/<int:exam_id>/task/<int:task_id>')
@login_required
def task_view(task_id, exam_id=None):
    task = db.session.get(Task, task_id)
    if task is None:
        flash('Task not found.')
        return redirect(url_for('index'))
    test_cases = db.session.execute(
        sa.select(TestCase).where(TestCase.task_id == task_id)
    ).scalars().all()
    return render_template('task.html', task=task, test_cases=test_cases, exam_id=exam_id)

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

@app.route('/exam/<int:exam_id>/task/<int:task_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_solution(exam_id, task_id):
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    exam = db.session.get(Exam, exam_id)

    if exam.deadline and datetime.utcnow() > exam.deadline:
        flash('Deadline has passed!')
        return redirect(url_for('exam_view', exam_id=exam_id))

    student_id = current_user.id
    form = SubmissionForm()
    if form.validate_on_submit():
        file = form.code_file.data
        code = file.read().decode('utf-8')

        if len(code) > 50000:
            flash('File is too large')
            return redirect(url_for('submit_solution', exam_id=exam_id, task_id=task_id))
        
        submission = Submission(
            task_id=task_id,
            user_id=student_id,
            exam_id=exam_id, 
            code=code,
            result="PENDING"
        )
        db.session.add(submission)

        requirements = None
        if exam.requirements:
            requirements = exam.requirements
        elif exam.allow_requirements and form.requirements_file.data:
            requirements = form.requirements_file.data.read().decode('utf-8')
            valid, msg = validate_requirements(requirements)
            if not valid:
                flash(f'Invalid requirements.txt: {msg}')
                return redirect(url_for('submit_solution', exam_id=exam_id, task_id=task_id))

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

        image = exam.docker_image or "python:3.11-slim"

        results = []
        all_passed = True
        total_run_time = 0
        build_time = None

        for test in tests_data:
            result = run_student_code(code, test["input"], image=image, requirements=requirements)
            passed = (result["status"] == "SUCCESS" 
                     and result["output"] == test["expected"].strip())
            total_run_time += result["run_time"]
            if result["build_time"]:
                build_time = result["build_time"]
            results.append({
                "input": test["input"],
                "expected": test["expected"],
                "actual": result["output"],
                "status": result["status"],
                "passed": passed,
                "run_time": result["run_time"]
            })
            if not passed:
                all_passed = False

        submission_to_update = db.session.get(Submission, submission_id)
        submission_to_update.result = "PASSED" if all_passed else "FAILED"
        submission_to_update.build_time=build_time
        submission_to_update.total_run_time=round(total_run_time, 3)
        
        db.session.commit()

        return render_template('results.html', results=results, submission=submission_to_update, task_id=task_id, exam_id=exam_id)

    return render_template('submit_solution.html', form=form, task_id=task_id, exam_id=exam_id, exam_allows_requirements=exam.allow_requirements)

@app.route('/exam/<int:exam_id>')
@login_required
def exam_view(exam_id):
    exam = db.session.get(Exam, exam_id)
    if exam is None:
        flash('Exam not found.')
        return redirect(url_for('index'))

    exam_tasks = db.session.execute(
        sa.select(Task).join(ExamTask).where(ExamTask.exam_id == exam_id)
    ).scalars().all()

    if current_user.role == 'student':
        is_assigned = db.session.execute(
            sa.select(ExamStudent).where(
                ExamStudent.exam_id == exam_id,
                ExamStudent.student_id == current_user.id
            )
        ).scalars().first()

        if not is_assigned:
            flash('You are not assigned to this exam.')
            return redirect(url_for('index'))

        submissions = db.session.execute(
            sa.select(Submission).where(
                Submission.exam_id == exam_id,
                Submission.user_id == current_user.id
            )
        ).scalars().all()

        solved_task_ids = set()
        attempted_task_ids = set()
        for sub in submissions:
            if sub.result == "PASSED":
                solved_task_ids.add(sub.task_id)
            else:
                attempted_task_ids.add(sub.task_id)

        return render_template('exam_student.html',
            exam=exam,
            tasks=exam_tasks,
            solved_task_ids=solved_task_ids,
            attempted_task_ids=attempted_task_ids
        )

    else:
        exam_students = db.session.execute(sa.select(User).join(ExamStudent).where(
                ExamStudent.exam_id == exam_id
            )
        ).scalars().all()

        all_submissions = db.session.execute(
            sa.select(Submission).where(Submission.exam_id == exam_id)
        ).scalars().all()

        status_map = {}
        for sub in all_submissions:
            if sub.user_id not in status_map:
                status_map[sub.user_id] = {}
            current_status = status_map[sub.user_id].get(sub.task_id)
            if current_status != "PASSED":
                status_map[sub.user_id][sub.task_id] = sub.result

        student_stats = []
        for student in exam_students:
            student_statuses = status_map.get(student.id, {})
            solved = 0
            for s in student_statuses.values():
                if s == "PASSED":
                    solved = solved + 1
            attempted = 0
            for s in student_statuses.values():
                if s != "PASSED":
                    attempted = attempted + 1
            not_attempted = len(exam_tasks) - len(student_statuses)
            student_stats.append({
                "student": student,
                "statuses": student_statuses,
                "solved": solved,
                "attempted": attempted,
                "not_attempted": not_attempted
            })

        return render_template('exam_lecturer.html',exam=exam, tasks=exam_tasks, student_stats=student_stats)

@app.route('/create-exam', methods=['GET', 'POST'])
@login_required
def create_exam():
    if current_user.role != 'lecturer':
        return redirect(url_for('index'))
    form = ExamForm()

    tasks = db.session.execute(sa.select(Task)).scalars().all()
    students = db.session.execute(
        sa.select(User).where(User.role == 'student')
    ).scalars().all()

    if form.validate_on_submit():
        if form.docker_image.data:
            try:
                client = docker.from_env()
                client.images.get(form.docker_image.data)
            except docker.errors.ImageNotFound:
                flash(f'Docker image "{form.docker_image.data}" not found! Build it first.')
                return render_template('create_exam.html', form=form, tasks=tasks, students=students)
            except docker.errors.APIError:
                flash('Could not connect to Docker. Is Docker Desktop running?')
                return render_template('create_exam.html', form=form, tasks=tasks, students=students)
            except Exception as e:
                flash(f'Unexpected error: {e}')
                return render_template('create_exam.html', form=form, tasks=tasks, students=students)

        requirements_text = None
        if form.requirements_file.data:
            requirements_text = form.requirements_file.data.read().decode('utf-8')

        exam = Exam(
            title=form.title.data,
            type=form.type.data,
            created_by=current_user.id,
            deadline=form.deadline.data,
            docker_image=form.docker_image.data or None,
            requirements=requirements_text,
            allow_requirements=form.allow_requirements.data
        )
        db.session.add(exam)
        db.session.commit()

        selected_tasks = request.form.getlist('tasks')
        for task_id in selected_tasks:
            db.session.add(ExamTask(exam_id=exam.id, task_id=int(task_id)))

        selected_students = request.form.getlist('students')
        for student_id in selected_students:
            db.session.add(ExamStudent(exam_id=exam.id, student_id=int(student_id)))

        db.session.commit()
        flash('Exam created!')
        return redirect(url_for('index'))

    return render_template('create_exam.html', form=form, tasks=tasks, students=students)

@app.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    if current_user.role != 'lecturer':
        flash('Only lecturers can delete tasks.')
        return redirect(url_for('index'))
    task = db.session.get(Task, task_id)
    if task is None:
        flash('Task not found')
        return redirect(url_for('index'))

    db.session.execute(
        sa.delete(TestCase).where(TestCase.task_id == task_id)
    )
    db.session.execute(
        sa.delete(ExamTask).where(ExamTask.task_id == task_id)
    )
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted!')
    return redirect(url_for('index'))

@app.route('/testcase/<int:testcase_id>/delete', methods=['POST'])
@login_required
def delete_test_case(testcase_id):
    if current_user.role != 'lecturer':
        flash('Only lecturers can delete test cases.')
        return redirect(url_for('index'))
    test = db.session.get(TestCase, testcase_id)
    if test is None:
        flash('Test case not found.')
        return redirect(url_for('index'))
    task_id = test.task_id
    db.session.delete(test)
    db.session.commit()
    flash('Test case deleted!')
    return redirect(url_for('task_view', task_id=task_id))