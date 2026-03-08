from app import app
from flask import render_template

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Alvydas'}
    assignments = [
        {
            'task_title': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'task_title': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template('index.html', title='Home', user=user, assignments=assignments)