from app import app
from flask import render_template
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
    return render_template('login.html', title="Sign In", form=form)