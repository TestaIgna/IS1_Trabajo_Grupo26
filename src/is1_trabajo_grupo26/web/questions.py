import logging
import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.services.strategy import (
    ConcreteLocal,
    ConcreteStrategyGemini,
    ConcreteStrategyOpenAI,
)

logger = logging.getLogger(__name__)

questions_bp = Blueprint("questions", __name__, url_prefix="/questions")

STRATEGIES = {
    "gemini": ("Gemini Bot", "gemini-bot@ia.local", ConcreteStrategyGemini),
    "openai": ("OpenAI Bot", "openai-bot@ia.local", ConcreteStrategyOpenAI),
    "local": ("Local Bot", "local-bot@ia.local", ConcreteLocal),
}


def _has_ia_help_tag(question: Question) -> bool:
    has_tag_obj = any(
        (tag.title or "").strip().lower() in {"#ia-help", "ia-help"}
        for tag in getattr(question, "tags", [])
    )
    in_text = (
        "#ia-help" in (question.body or "").lower()
        or "#ia-help" in (question.title or "").lower()
    )
    return has_tag_obj or in_text


def _get_or_create_bot_author(bot_name: str, bot_email: str) -> Author:
    bot = db.session.execute(
        db.select(Author).where(Author.email == bot_email)
    ).scalar_one_or_none()
    if bot is None:
        bot = Author(
            name=bot_name,
            email=bot_email,
            password=secrets.token_urlsafe(32),
            role=TipoRol.BOT,
        )
        db.session.add(bot)
        db.session.flush()
    return bot


@questions_bp.route("/<int:question_id>", methods=["GET"])
def detail(question_id: int):
    question = db.get_or_404(Question, question_id)
    return render_template(
        "questions/detail.html",
        question=question,
        has_ia_tag=_has_ia_help_tag(question),
        selected_provider="gemini",
    )


@questions_bp.route("/<int:question_id>/generate-ai", methods=["POST"])
def generate_ai_answer(question_id: int):
    question = db.get_or_404(Question, question_id)

    if not _has_ia_help_tag(question):
        flash(
            "La pregunta debe incluir #ia-help para generar una respuesta automática.",
            "warning",
        )
        return redirect(url_for("questions.detail", question_id=question.id))

    provider = (request.form.get("provider") or "gemini").strip().lower()
    if provider not in STRATEGIES:
        flash("Proveedor de IA no válido.", "danger")
        return redirect(url_for("questions.detail", question_id=question.id))

    bot_name, bot_email, strategy_cls = STRATEGIES[provider]

    try:
        strategy = strategy_cls()
        generated_body = strategy.createResponse(question.title, question.body)

        bot_author = _get_or_create_bot_author(bot_name, bot_email)
        new_response = Response(
            body=generated_body,
            question_id=question.id,
            author_id=bot_author.id,
        )
        db.session.add(new_response)
        db.session.commit()

        flash(f"Respuesta generada con {bot_name}.", "success")
    except Exception:
        db.session.rollback()
        logger.exception("Error generando respuesta con IA (%s)", provider)
        flash("Ocurrió un error al generar la respuesta automática.", "danger")
    return redirect(url_for("questions.detail", question_id=question.id))
