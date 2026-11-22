from flask import Blueprint, render_template

questions_bp = Blueprint("questions", __name__, url_prefix="/questions")


@questions_bp.get("/vista-ia")
def vista_ia():
    return render_template("questions/ai_selector.html")