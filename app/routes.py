from app import app
from flask import render_template, flash, redirect
from app.forms import LoginForm

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Alvydas'}
    assignments = [
        {
            'task_title': 'Assignment 1',
            'body': 'Fibonacci sequence'
        },
        {
            'task_title': 'Assignment 2',
            'body': 'FizzBuzz'
        }
    ]
    return render_template('index.html', title='Home', user=user, assignments=assignments)

@app.route('/login')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect('/index')
    return render_template('login.html', title='Sign In', form=form)