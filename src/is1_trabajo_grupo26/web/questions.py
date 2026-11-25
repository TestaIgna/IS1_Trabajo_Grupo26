import logging
import secrets
import unicodedata

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.tag import Tag
from is1_trabajo_grupo26.models.vote import VoteType
from is1_trabajo_grupo26.services.strategy import (
    ConcreteLocal,
    ConcreteStrategyGemini,
    ConcreteStrategyOpenAI,
)
from is1_trabajo_grupo26.services.vote_service import register_vote

logger = logging.getLogger(__name__)

questions_bp = Blueprint("questions", __name__, url_prefix="/questions")

STRATEGIES = {
    "gemini": ("Gemini Bot", "gemini-bot@ia.local", ConcreteStrategyGemini),
    "openai": ("OpenAI Bot", "openai-bot@ia.local", ConcreteStrategyOpenAI),
    "local": ("Local Bot", "local-bot@ia.local", ConcreteLocal),
}

MAX_TITLE_LENGTH = 200
MAX_TAG_LENGTH = 20
IA_HELP_TAG = "#ia-help"
DEFAULT_RECOMMENDED_TAGS = ["duda", "ayuda", "buenas-practicas", "debug"]
CATEGORY_TAG_RECOMMENDATIONS: list[tuple[tuple[str, ...], list[str]]] = [
    (
        ("python", "flask", "django", "backend"),
        ["python", "flask", "sqlalchemy", "pytest", "api"],
    ),
    (
        ("base", "datos", "sql", "sqlite", "postgres"),
        ["sql", "sqlite", "alembic", "modelado", "orm"],
    ),
    (
        ("ingenier", "arquitect", "disen", "patron", "uml"),
        ["uml", "patrones", "arquitectura", "testing", "solid"],
    ),
    (
        ("front", "web", "html", "css", "interfaz", "ui"),
        ["html", "css", "jinja2", "ui", "formularios"],
    ),
    (
        ("ia", "inteligencia", "llm", "bot"),
        ["llm", "strategy", "gemini", "openai", "prompt"],
    ),
]


def _normalize_lookup(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.lower().strip()


def _dedupe_tags(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = item.strip()
        if not clean:
            continue
        key = clean.lower()
        if key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _curated_tags_for_category(category_name: str) -> list[str]:
    lookup = _normalize_lookup(category_name)
    matched: list[str] = []
    for keywords, tags in CATEGORY_TAG_RECOMMENDATIONS:
        if any(keyword in lookup for keyword in keywords):
            matched.extend(tags)
    if matched:
        return _dedupe_tags(matched)
    return list(DEFAULT_RECOMMENDED_TAGS)


def _build_tag_context(
    categories: list[Category],
) -> tuple[dict[str, list[str]], list[str]]:
    tags_by_category: dict[str, list[str]] = {}
    for category in categories:
        used_in_category = sorted(
            {
                tag.title.strip()
                for question in category.questions
                for tag in question.tags
                if tag.title
                and tag.title.strip().lower() != IA_HELP_TAG
                and len(tag.title.strip()) <= MAX_TAG_LENGTH
            },
            key=str.lower,
        )
        curated = _curated_tags_for_category(category.name)
        tags_by_category[str(category.id)] = _dedupe_tags(used_in_category + curated)

    all_tags = db.session.execute(db.select(Tag).order_by(Tag.title)).scalars().all()
    existing_tags = _dedupe_tags(
        [
            tag.title
            for tag in all_tags
            if tag.title
            and tag.title.strip().lower() != IA_HELP_TAG
            and len(tag.title.strip()) <= MAX_TAG_LENGTH
        ]
    )
    return tags_by_category, existing_tags


def _parse_and_validate_tags(
    selected_tags: list[str],
    raw_tags: str,
) -> tuple[list[str], str | None]:
    raw_candidates = list(selected_tags) + raw_tags.split(",")
    normalized_tags = _dedupe_tags(raw_candidates)
    too_long = [tag for tag in normalized_tags if len(tag) > MAX_TAG_LENGTH]
    if too_long:
        listed = ", ".join(too_long)
        return (
            [],
            f"Las etiquetas no pueden superar los {MAX_TAG_LENGTH} caracteres (excedidas: {listed}).",
        )
    return normalized_tags, None


def _active_recommended_tags(
    category_id: int | None,
    tags_by_category: dict[str, list[str]],
) -> list[str]:
    if category_id is not None and str(category_id) in tags_by_category:
        return list(tags_by_category[str(category_id)])
    return list(DEFAULT_RECOMMENDED_TAGS)


@questions_bp.route("", methods=["GET"])
def list_questions():
    questions = db.session.execute(
        db.select(Question).order_by(Question.id.desc())
    ).scalars().all()
    return render_template("questions/list.html", questions=questions)


@questions_bp.route("/nueva", methods=["GET", "POST"])
def create_question():
    author_id = session.get("user_id")
    if author_id is None:
        flash("Necesitás iniciar sesión para crear una pregunta.", "warning")
        return redirect(url_for("users.registro"))

    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    author = db.session.get(Author, author_id)
    if author is None:
        session.pop("user_id", None)
        flash("La sesión no corresponde a un usuario válido.", "danger")
        return redirect(url_for("users.registro"))

    tags_by_category, existing_tags = _build_tag_context(categories)

    if request.method == "GET":
        category_id = request.args.get("category_id", type=int)
        return render_template(
            "questions/create.html",
            categories=categories,
            errors={},
            title="",
            body="",
            category_id=category_id,
            tags_input="",
            selected_tags=set(),
            active_recommended_tags=_active_recommended_tags(category_id, tags_by_category),
            tags_by_category=tags_by_category,
            default_recommended_tags=DEFAULT_RECOMMENDED_TAGS,
            existing_tags=existing_tags,
            max_title_length=MAX_TITLE_LENGTH,
            max_tag_length=MAX_TAG_LENGTH,
        )

    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    category_id = request.form.get("category_id", type=int)
    selected_tags_raw = request.form.getlist("selected_tags")
    tags_input = (request.form.get("tags") or "").strip()

    errors: dict[str, str] = {}
    if not title:
        errors["title"] = "El título es obligatorio."
    elif len(title) > MAX_TITLE_LENGTH:
        errors["title"] = f"El título no puede superar los {MAX_TITLE_LENGTH} caracteres."

    if not body:
        errors["body"] = "La consulta es obligatoria."

    category = db.session.get(Category, category_id) if category_id else None
    if category is None:
        errors["category_id"] = "Debés seleccionar una categoría válida."

    normalized_tags, tags_error = _parse_and_validate_tags(selected_tags_raw, tags_input)
    if tags_error is not None:
        errors["tags"] = tags_error

    if errors:
        selected_tags = {t.strip().lower() for t in selected_tags_raw if t.strip()}
        return (
            render_template(
                "questions/create.html",
                categories=categories,
                errors=errors,
                title=title,
                body=body,
                category_id=category_id,
                tags_input=tags_input,
                selected_tags=selected_tags,
                active_recommended_tags=_active_recommended_tags(
                    category_id if category is not None else None,
                    tags_by_category,
                ),
                tags_by_category=tags_by_category,
                default_recommended_tags=DEFAULT_RECOMMENDED_TAGS,
                existing_tags=existing_tags,
                max_title_length=MAX_TITLE_LENGTH,
                max_tag_length=MAX_TAG_LENGTH,
            ),
            400,
        )

    tags = []
    for title_tag in normalized_tags:
        tag = db.session.execute(
            db.select(Tag).where(db.func.lower(Tag.title) == title_tag.lower())
        ).scalar_one_or_none()
        if tag is None:
            tag = Tag(title=title_tag)
            db.session.add(tag)
            db.session.flush()
        if tag not in tags:
            tags.append(tag)

    question = Question(
        title=title,
        body=body,
        category=category,
        author=author,
        tags=tags,
    )
    db.session.add(question)
    db.session.commit()
    flash("Pregunta creada correctamente.", "success")
    return redirect(url_for("questions.detail", question_id=question.id))


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


@questions_bp.route("/<int:question_id>/vote", methods=["POST"])
def vote_question(question_id: int):
    user_id = session.get("user_id")
    if user_id is None:
        flash("Necesitás registrarte para votar.", "warning")
        return redirect(url_for("users.registro"))

    question = db.get_or_404(Question, question_id)
    raw_vote = (request.form.get("vote") or "").strip().upper()
    vote_type = {
        "POSITIVE": VoteType.POSITIVE,
        "NEGATIVE": VoteType.NEGATIVE,
    }.get(raw_vote)
    if vote_type is None:
        flash("El voto seleccionado no es válido.", "danger")
        return redirect(url_for("questions.detail", question_id=question.id))

    try:
        register_vote(
            user_id=user_id,
            vote_type=vote_type,
            question_id=question.id,
        )
        flash("Tu voto fue registrado.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("questions.detail", question_id=question.id))


@questions_bp.route("/answers/<int:answer_id>/vote", methods=["POST"])
def vote_answer(answer_id: int):
    user_id = session.get("user_id")
    if user_id is None:
        flash("Necesitás registrarte para votar.", "warning")
        return redirect(url_for("users.registro"))

    answer = db.session.get(Response, answer_id)
    if answer is None:
        return ("Respuesta no encontrada.", 404)

    raw_vote = (request.form.get("vote") or "").strip().upper()
    vote_type = {
        "POSITIVE": VoteType.POSITIVE,
        "NEGATIVE": VoteType.NEGATIVE,
    }.get(raw_vote)
    if vote_type is None:
        flash("El voto seleccionado no es válido.", "danger")
        return redirect(url_for("questions.detail", question_id=answer.question_id))

    try:
        register_vote(
            user_id=user_id,
            vote_type=vote_type,
            response_id=answer.id,
        )
        flash("Tu voto en la respuesta fue registrado.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("questions.detail", question_id=answer.question_id))


@questions_bp.route("/<int:question_id>/answers", methods=["POST"])
def create_answer(question_id: int):
    user_id = session.get("user_id")
    if user_id is None:
        flash("Necesitás iniciar sesión para responder.", "warning")
        return redirect(url_for("users.registro"))

    question = db.get_or_404(Question, question_id)
    author = db.session.get(Author, user_id)
    if author is None:
        session.pop("user_id", None)
        flash("La sesión no corresponde a un usuario válido.", "danger")
        return redirect(url_for("users.registro"))

    body = (request.form.get("body") or "").strip()
    if not body:
        flash("La respuesta no puede estar vacía.", "danger")
        return redirect(url_for("questions.detail", question_id=question.id))

    db.session.add(Response(body=body, question=question, author=author))
    db.session.commit()
    flash("Respuesta publicada correctamente.", "success")
    return redirect(url_for("questions.detail", question_id=question.id))


@questions_bp.route("/answers/<int:answer_id>/accept", methods=["POST"])
def accept_answer(answer_id: int):
    user_id = session.get("user_id")
    if user_id is None:
        flash("Necesitás iniciar sesión para aceptar una respuesta.", "warning")
        return redirect(url_for("users.registro"))

    answer = db.session.get(Response, answer_id)
    if answer is None:
        return ("Respuesta no encontrada.", 404)

    if answer.question.author_id != user_id:
        flash("Solo el autor de la pregunta puede aceptar respuestas.", "danger")
        return redirect(url_for("questions.detail", question_id=answer.question_id))

    if answer.is_accepted:
        answer.is_accepted = False
        flash("La respuesta dejó de estar marcada como aceptada.", "success")
    else:
        for other in answer.question.responses:
            other.is_accepted = False
        answer.is_accepted = True
        flash("Respuesta aceptada correctamente.", "success")
    db.session.commit()
    return redirect(url_for("questions.detail", question_id=answer.question_id))
