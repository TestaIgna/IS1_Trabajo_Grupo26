from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import Role_Type
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.services.author_factory import AuthorConcreteFactory
from is1_trabajo_grupo26.services.strategy import (
    ConcreteLocal,
    ConcreteStrategyGemini,
    ConcreteStrategyOpenAI,
    Strategy,
)

AI_PROVIDERS: dict[str, tuple[str, type[Strategy]]] = {
    "local": ("Local Bot", ConcreteLocal),
    "openai": ("OpenAI Bot", ConcreteStrategyOpenAI),
    "gemini": ("Gemini Bot", ConcreteStrategyGemini),
}


def resolve_ai_strategy(provider: str = "local") -> tuple[str, Strategy]:
    """Resuelve el nombre del bot y la estrategia concreta para un proveedor de IA."""
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("El proveedor de IA debe ser una cadena no vacía.")

    normalized = provider.strip().lower()
    entry = AI_PROVIDERS.get(normalized)
    if entry is None:
        valid = ", ".join(sorted(AI_PROVIDERS))
        raise ValueError(
            f"Proveedor de IA no soportado: {provider!r}. Opciones válidas: {valid}."
        )

    bot_name, strategy_cls = entry
    return bot_name, strategy_cls()


def get_or_create_bot_author(bot_name: str) -> Author:
    """Obtiene o registra un autor ORM persistente con rol BOT."""
    bot = db.session.execute(
        db.select(Author).where(
            Author.role == Role_Type.BOT,
            Author.name == bot_name,
        )
    ).scalar_one_or_none()
    if bot is None:
        bot = Author(name=bot_name, role=Role_Type.BOT)
        db.session.add(bot)
        db.session.flush()
    return bot


def generate_ai_response_for_question(
    question: Question,
    *,
    provider: str = "local",
    strategy: Strategy | None = None,
    bot_name: str | None = None,
) -> Response | None:
    """Genera y agrega a la sesión una respuesta de IA si la pregunta tiene #ia-help."""
    if strategy is not None:
        resolved_strategy = strategy
        resolved_name = bot_name or "IA Bot"
    else:
        default_name, resolved_strategy = resolve_ai_strategy(provider)
        resolved_name = bot_name or default_name

    llm = AuthorConcreteFactory().createAuthor(
        author_type="llm",
        nombre=resolved_name,
        rol=Role_Type.BOT,
        strategy=resolved_strategy,
    )
    if not llm.shouldAnswer(question):
        return None

    generated_body = llm.answerQuestion(question)
    bot_author = get_or_create_bot_author(llm.getName())
    ai_response = Response(
        body=generated_body,
        question=question,
        author=bot_author,
    )
    db.session.add(ai_response)
    return ai_response
