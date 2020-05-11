import sys
from os import path, remove
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, request, url_for

bpname = Blueprint('bpname', __name__, url_prefix='/endpoint')