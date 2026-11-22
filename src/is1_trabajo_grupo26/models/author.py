from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class Role_Type(str, Enum):
    """Roles válidos para los distintos tipos de autores del sistema."""

    USERGRAL = "USERGRAL"
    ADMIN = "ADMIN"
    BOT = "BOT"

    @classmethod
    def from_value(cls, value: "Role_Type | str") -> "Role_Type":
        """Normaliza y valida un rol recibido como Role_Type o cadena."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            try:
                return cls(normalized)
            except ValueError as exc:
                raise ValueError(f"Rol inválido: {value!r}") from exc
        raise ValueError(f"Rol inválido: {value!r}")


TipoRol = Role_Type


class AuthorResponse(ABC):
    """Interfaz común para cualquier autor capaz de responder en el sistema."""

    def __init__(self, nombre: str, rol: Role_Type | str) -> None:
        cleaned_name = nombre.strip() if isinstance(nombre, str) else ""
        if not cleaned_name:
            raise ValueError("El nombre del autor no puede estar vacío.")
        self.nombre: str = cleaned_name
        self.rol: Role_Type = Role_Type.from_value(rol)

    @abstractmethod
    def getName(self) -> str:
        """Retorna el nombre visible del autor."""

    @abstractmethod
    def getRoleType(self) -> Role_Type:
        """Retorna el rol asignado al autor."""

    def get_nombre(self) -> str:
        """Alias de compatibilidad para getName."""
        return self.getName()

    def get_rol(self) -> Role_Type:
        """Alias de compatibilidad para getRoleType."""
        return self.getRoleType()


class User(AuthorResponse):
    """Autor humano del sistema (usuario general o administrador)."""

    _ALLOWED_ROLES = frozenset({Role_Type.USERGRAL, Role_Type.ADMIN})

    def __init__(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: Role_Type | str = Role_Type.USERGRAL,
    ) -> None:
        parsed_rol = Role_Type.from_value(rol)
        if parsed_rol not in self._ALLOWED_ROLES:
            raise ValueError(
                f"Un autor User solo puede tener rol USERGRAL o ADMIN, no {parsed_rol.value}."
            )

        cleaned_email = email.strip() if isinstance(email, str) else ""
        if not cleaned_email or "@" not in cleaned_email:
            raise ValueError("El email del usuario es inválido.")
        if not isinstance(password, str) or not password:
            raise ValueError("La contraseña del usuario no puede estar vacía.")

        super().__init__(nombre=nombre, rol=parsed_rol)
        self.email: str = cleaned_email
        self.password: str = password

    def getName(self) -> str:
        return self.nombre

    def getRoleType(self) -> Role_Type:
        return self.rol


class LLM(AuthorResponse):
    """Autor automático que genera respuestas mediante una estrategia de IA."""

    def __init__(
        self,
        nombre: str,
        rol: Role_Type | str = Role_Type.BOT,
        strategy: Any | None = None,
    ) -> None:
        parsed_rol = Role_Type.from_value(rol)
        if parsed_rol != Role_Type.BOT:
            raise ValueError(
                f"Un autor LLM debe tener rol BOT, no {parsed_rol.value}."
            )

        super().__init__(nombre=nombre, rol=parsed_rol)
        self.strategy: Any | None = strategy

    def getName(self) -> str:
        return self.nombre

    def getRoleType(self) -> Role_Type:
        return self.rol

    def set_strategy(self, strategy: Any) -> None:
        """Asocia o reemplaza la estrategia de generación de respuestas (Issue #33)."""
        self.strategy = strategy

    def answerQuestion(self, q) -> str:
        """Genera una respuesta delegando en la estrategia configurada."""
        if self.strategy is None:
            return (
                "No se pudo generar la respuesta: "
                "no hay una estrategia configurada."
            )

        try:
            return self.strategy.createResponse(q.title, q.body)
        except Exception as exc:  # noqa: BLE001 - la IA puede fallar por distintas razones
            return f"No se pudo generar la respuesta: {exc}"

    def shouldAnswer(self, q) -> bool:
        """Indica si la pregunta pide ayuda de IA mediante el tag '#ia-help'."""
        tags = getattr(q, "tags", [])
        for tag in tags:
            tag_name = tag if isinstance(tag, str) else getattr(tag, "title", "")
            if (
                isinstance(tag_name, str)
                and tag_name.strip().lower() == "#ia-help"
            ):
                return True
        return False
