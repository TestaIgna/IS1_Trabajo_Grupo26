import pytest

from is1_trabajo_grupo26.models import LLM, AuthorResponse, Role_Type, TipoRol, User
from is1_trabajo_grupo26.services import AuthorConcreteFactory, AuthorFactory


def test_abstract_classes_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AuthorResponse(nombre="Base", rol=Role_Type.USERGRAL)

    with pytest.raises(TypeError):
        AuthorFactory()


def test_factory_creates_general_user_by_default():
    factory: AuthorFactory = AuthorConcreteFactory()

    author = factory.createAuthor(
        author_type="user",
        nombre="Matias",
        email="matias@example.com",
        password="hashed-password",
    )

    assert isinstance(author, AuthorResponse)
    assert isinstance(author, User)
    assert author.getName() == "Matias"
    assert author.getRoleType() is Role_Type.USERGRAL
    assert author.email == "matias@example.com"


def test_factory_creates_admin_user_with_string_or_enum_role():
    factory = AuthorConcreteFactory()

    admin_from_enum = factory.createAuthor(
        author_type="USER",
        nombre="Admin1",
        rol=Role_Type.ADMIN,
        email="admin1@example.com",
        password="secret",
    )
    admin_from_str = factory.createAuthor(
        author_type="user",
        nombre="Admin2",
        rol="admin",
        email="admin2@example.com",
        password="secret",
    )

    assert isinstance(admin_from_enum, User)
    assert admin_from_enum.getRoleType() is Role_Type.ADMIN
    assert isinstance(admin_from_str, User)
    assert admin_from_str.getRoleType() is Role_Type.ADMIN


def test_factory_creates_llm_with_bot_role_and_optional_strategy():
    factory = AuthorConcreteFactory()
    dummy_strategy = object()

    bot = factory.createAuthor(
        author_type="llm",
        nombre="GeminiBot",
        strategy=dummy_strategy,
    )

    assert isinstance(bot, AuthorResponse)
    assert isinstance(bot, LLM)
    assert bot.getName() == "GeminiBot"
    assert bot.getRoleType() is Role_Type.BOT
    assert bot.strategy is dummy_strategy


def test_factory_validates_invalid_types_and_roles():
    factory = AuthorConcreteFactory()

    with pytest.raises(ValueError, match="no soportado"):
        factory.createAuthor(author_type="guest", nombre="Anonimo")

    with pytest.raises(ValueError, match="email"):
        factory.createAuthor(author_type="user", nombre="SinCredenciales")

    with pytest.raises(ValueError, match="USERGRAL o ADMIN"):
        factory.createAuthor(
            author_type="user",
            nombre="MalRol",
            rol=Role_Type.BOT,
            email="u@example.com",
            password="123",
        )

    with pytest.raises(ValueError, match="BOT"):
        factory.createAuthor(
            author_type="llm",
            nombre="MalBot",
            rol=Role_Type.USERGRAL,
        )

    with pytest.raises(ValueError, match="Rol inválido"):
        factory.createAuthor(
            author_type="user",
            nombre="RolInexistente",
            rol="MODERATOR",
            email="u@example.com",
            password="123",
        )


def test_legacy_author_aliases_remain_compatible():
    assert TipoRol is Role_Type

    factory = AuthorConcreteFactory()
    user = factory.createAutor(
        author_type="user",
        nombre="Ale",
        email="ale@example.com",
        password="secret",
    )
    bot = factory.createAutor(author_type="llm", nombre="Asistente")

    assert user.get_nombre() == "Ale"
    assert user.get_rol() is TipoRol.USERGRAL
    assert bot.get_nombre() == "Asistente"
    assert bot.get_rol() is TipoRol.BOT
