from abc import ABC, abstractmethod

from google import genai

# Se necesita GEMINI_API_KEY en tu archivo env.


class Strategy(ABC):
    @abstractmethod
    def createResponse(self, title: str, body: str) -> str:
        pass


class ConcreteStrategyGemini(Strategy):
    def createResponse(self, title: str, body: str) -> str:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=(
                "Responde a la siguiente pregunta:\n"
                f"titulo:{title}"
                f"Detalle: {body}"
            ),
        )
        return response.text


class ConcreteStrategyOpenAI(Strategy):
    def createResponse(self, title: str, body: str) -> str:
        return f"[OpenAI] Respuesta para '{title}': {body} "


class ConcreteLocal(Strategy):
    def createResponse(self, title: str, body: str) -> str:
        return f"[Local] Respuesta para '{title}': {body} "


# Aliases para los nombres usados en el enunciado de la issue #33.
StrategyGemini = ConcreteStrategyGemini
StrategyOpenAI = ConcreteStrategyOpenAI
Local = ConcreteLocal
