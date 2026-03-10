from app import app
from flask import render_template

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