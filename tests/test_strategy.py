from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from is1_trabajo_grupo26.models.author import LLM, TipoRol
from is1_trabajo_grupo26.services import AuthorConcreteFactory
from is1_trabajo_grupo26.services import strategy as strategy_module
from is1_trabajo_grupo26.services.strategy import (
    ConcreteLocal,
    ConcreteStrategyGemini,
    ConcreteStrategyOpenAI,
    Local,
    Strategy,
    StrategyGemini,
    StrategyOpenAI,
)


@dataclass
class FakeQuestion:
    title: str
    body: str
    tags: list[str] = field(default_factory=list)


class FakeStrategy:
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def createResponse(self, title: str, body: str) -> str:
        self.calls.append((title, body))
        if self.error is not None:
            raise self.error
        return self.response or ""


class FakeGeminiClient:
    def __init__(self, text: str) -> None:
        self.calls: list[dict[str, str]] = []
        self.models = SimpleNamespace(generate_content=self._generate_content)
        self.text = text

    def _generate_content(self, *, model: str, contents: str):
        self.calls.append({"model": model, "contents": contents})
        return SimpleNamespace(text=self.text)


def test_strategy_defines_an_abstract_create_response():
    with pytest.raises(TypeError):
        Strategy()

    class IncompleteStrategy(Strategy):
        pass

    with pytest.raises(TypeError):
        IncompleteStrategy()


def test_gemini_strategy_builds_the_prompt_and_returns_the_text(monkeypatch):
    client = FakeGeminiClient(" respuesta de gemini ")
    monkeypatch.setattr(strategy_module.genai, "Client", lambda: client)

    response = ConcreteStrategyGemini().createResponse(
        "¿Cómo estudiar?",
        "Quiero una guía.",
    )

    assert response == " respuesta de gemini "
    assert client.calls == [
        {
            "model": "gemini-flash-lite-latest",
            "contents": (
                "Responde a la siguiente pregunta:\n"
                "titulo:¿Cómo estudiar?"
                "Detalle: Quiero una guía."
            ),
        }
    ]


def test_openai_strategy_returns_its_literal_response():
    assert ConcreteStrategyOpenAI().createResponse("Título", "Cuerpo") == (
        "[OpenAI] Respuesta para 'Título': Cuerpo "
    )


def test_local_strategy_returns_its_literal_response():
    assert ConcreteLocal().createResponse("Título", "Cuerpo") == (
        "[Local] Respuesta para 'Título': Cuerpo "
    )


def test_issue_aliases_point_to_the_concrete_strategies():
    assert StrategyGemini is ConcreteStrategyGemini
    assert StrategyOpenAI is ConcreteStrategyOpenAI
    assert Local is ConcreteLocal


def test_factory_creates_the_official_llm_with_its_strategy():
    strategy = ConcreteLocal()

    bot = AuthorConcreteFactory().createAutor(
        author_type="llm",
        nombre="Asistente",
        strategy=strategy,
    )

    assert isinstance(bot, LLM)
    assert bot.get_nombre() == "Asistente"
    assert bot.get_rol() is TipoRol.BOT
    assert bot.strategy is strategy


def test_llm_delegates_to_the_selected_strategy_and_can_switch():
    first = FakeStrategy("Desde la primera estrategia")
    second = FakeStrategy("Desde la segunda estrategia")
    bot = AuthorConcreteFactory().createAutor(
        author_type="llm",
        nombre="Asistente",
        strategy=first,
    )
    question = FakeQuestion("Pregunta", "Detalle")

    assert bot.answerQuestion(question) == "Desde la primera estrategia"
    assert first.calls == [("Pregunta", "Detalle")]

    bot.set_strategy(second)

    assert bot.answerQuestion(question) == "Desde la segunda estrategia"
    assert second.calls == [("Pregunta", "Detalle")]


def test_llm_handles_a_failing_strategy():
    failing = FakeStrategy(error=RuntimeError("falló el proveedor"))
    bot = AuthorConcreteFactory().createAutor(
        author_type="llm",
        nombre="Asistente",
        strategy=failing,
    )

    response = bot.answerQuestion(FakeQuestion("Pregunta", "Detalle"))

    assert "No se pudo generar la respuesta" in response
    assert "falló el proveedor" in response


def test_llm_handles_a_missing_strategy():
    bot = AuthorConcreteFactory().createAutor(
        author_type="llm",
        nombre="Asistente",
    )

    response = bot.answerQuestion(FakeQuestion("Pregunta", "Detalle"))

    assert "estrategia" in response


def test_llm_only_answers_questions_tagged_for_ai_help():
    bot = AuthorConcreteFactory().createAutor(
        author_type="llm",
        nombre="Asistente",
        strategy=ConcreteLocal(),
    )

    assert bot.shouldAnswer(FakeQuestion("Pregunta", "Detalle", ["#IA-HELP"]))
    assert not bot.shouldAnswer(FakeQuestion("Pregunta", "Detalle", ["otro"]))
    assert not bot.shouldAnswer(FakeQuestion("Pregunta", "Detalle"))
