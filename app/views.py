from flask import Blueprint
from flask import render_template

views = Blueprint('views', __name__)

@views.route('/')
def student_dashboard():
    return render_template("student_dashboard.html")