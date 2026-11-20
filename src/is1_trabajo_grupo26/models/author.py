from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class TipoRol(str, Enum):
    """Roles válidos para los distintos tipos de autores del sistema."""

    USERGRAL = "USERGRAL"
    ADMIN = "ADMIN"
    BOT = "BOT"

    @classmethod
    def from_value(cls, value: "TipoRol | str") -> "TipoRol":
        """Normaliza y valida un rol recibido como TipoRol o cadena."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            try:
                return cls(normalized)
            except ValueError as exc:
                raise ValueError(f"Rol inválido: {value!r}") from exc
        raise ValueError(f"Rol inválido: {value!r}")


class AuthorResponse(ABC):
    """Interfaz común para cualquier autor capaz de responder en el sistema."""

    def __init__(self, nombre: str, rol: TipoRol | str) -> None:
        cleaned_name = nombre.strip() if isinstance(nombre, str) else ""
        if not cleaned_name:
            raise ValueError("El nombre del autor no puede estar vacío.")
        self.nombre: str = cleaned_name
        self.rol: TipoRol = TipoRol.from_value(rol)

    @abstractmethod
    def get_nombre(self) -> str:
        """Retorna el nombre visible del autor."""

    @abstractmethod
    def get_rol(self) -> TipoRol:
        """Retorna el rol asignado al autor."""


class User(AuthorResponse):
    """Autor humano del sistema (usuario general o administrador)."""

    _ALLOWED_ROLES = frozenset({TipoRol.USERGRAL, TipoRol.ADMIN})

    def __init__(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: TipoRol | str = TipoRol.USERGRAL,
    ) -> None:
        parsed_rol = TipoRol.from_value(rol)
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

    def get_nombre(self) -> str:
        return self.nombre

    def get_rol(self) -> TipoRol:
        return self.rol


class LLM(AuthorResponse):
    """Autor automático que genera respuestas mediante una estrategia de IA."""

    def __init__(
        self,
        nombre: str,
        rol: TipoRol | str = TipoRol.BOT,
        strategy: Any | None = None,
    ) -> None:
        parsed_rol = TipoRol.from_value(rol)
        if parsed_rol != TipoRol.BOT:
            raise ValueError(
                f"Un autor LLM debe tener rol BOT, no {parsed_rol.value}."
            )

        super().__init__(nombre=nombre, rol=parsed_rol)
        self.strategy: Any | None = strategy

    def get_nombre(self) -> str:
        return self.nombre

    def get_rol(self) -> TipoRol:
        return self.rol

    def set_strategy(self, strategy: Any) -> None:
        """Asocia o reemplaza la estrategia de generación de respuestas (Issue #33)."""
        self.strategy = strategy
