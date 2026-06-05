"""
Author: Neil Zhang
Time: 2020/1/4
Descriptions:
  Cenerate API objects for Blueprint. only import views function.
"""
from flask import Blueprint

api = Blueprint('api', __name__)

# from . import authentication, posts, users, comments, errors
from . import views
