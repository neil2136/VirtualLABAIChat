from flask import Blueprint
from flask import Flask

app = Flask(__name__)

main = Blueprint('main', __name__)

from . import views
from ..models import Permission

@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
