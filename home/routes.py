# -------------------- Página Inicial --------------------

from flask import Blueprint, render_template

# Criando o blueprint de "home"
home_bp = Blueprint("home", __name__, template_folder="../templates")

@home_bp.route("/")
def index():
    return render_template("home.html")