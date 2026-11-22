from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from is1_trabajo_grupo26.models.author import LLM, AuthorResponse, Role_Type, User


class AuthorFactory(ABC):
    """Fábrica abstracta para la creación de autores (Patrón Factory Method)."""

    @abstractmethod
    def createAuthor(
        self,
        author_type: str,
        nombre: str,
        rol: Role_Type | str | None = None,
        email: str | None = None,
        password: str | None = None,
        strategy: Any | None = None,
    ) -> AuthorResponse:
        """Crea y retorna una instancia concreta de AuthorResponse."""

    def createAutor(
        self,
        author_type: str,
        nombre: str,
        rol: Role_Type | str | None = None,
        email: str | None = None,
        password: str | None = None,
        strategy: Any | None = None,
    ) -> AuthorResponse:
        """Alias de compatibilidad para createAuthor."""
        return self.createAuthor(
            author_type=author_type,
            nombre=nombre,
            rol=rol,
            email=email,
            password=password,
            strategy=strategy,
        )


class AuthorConcreteFactory(AuthorFactory):
    """Fábrica concreta encargada de instanciar autores User o LLM."""

    def createAuthor(
        self,
        author_type: str,
        nombre: str,
        rol: Role_Type | str | None = None,
        email: str | None = None,
        password: str | None = None,
        strategy: Any | None = None,
    ) -> AuthorResponse:
        if not isinstance(author_type, str) or not author_type.strip():
            raise ValueError("El tipo de autor no puede estar vacío.")

        normalized_type = author_type.strip().lower()
        creators: dict[str, Callable[..., AuthorResponse]] = {
            "user": self._create_user,
            "llm": self._create_llm,
        }

        creator = creators.get(normalized_type)
        if creator is None:
            raise ValueError(
                f"Tipo de autor no soportado: {author_type!r}. "
                f"Opciones válidas: {sorted(creators)}."
            )

        return creator(
            nombre=nombre,
            rol=rol,
            email=email,
            password=password,
            strategy=strategy,
        )

    def _create_user(
        self,
        nombre: str,
        rol: Role_Type | str | None = None,
        email: str | None = None,
        password: str | None = None,
        **_unused: Any,
    ) -> User:
        if email is None or password is None:
            raise ValueError(
                "Para crear un autor de tipo 'user' se requieren 'email' y 'password'."
            )
        target_rol = Role_Type.USERGRAL if rol is None else rol
        return User(nombre=nombre, email=email, password=password, rol=target_rol)

    def _create_llm(
        self,
        nombre: str,
        rol: Role_Type | str | None = None,
        strategy: Any | None = None,
        **_unused: Any,
    ) -> LLM:
        target_rol = Role_Type.BOT if rol is None else rol
        return LLM(nombre=nombre, rol=target_rol, strategy=strategy)
