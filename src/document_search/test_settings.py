"""
Настройки Django для тестов
"""
from typing import Any, Dict

# Используем SQLite для тестов (быстрее чем PostgreSQL)
DATABASES: Dict[str, Dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Отключаем миграции для ускорения тестов
class DisableMigrations:
    def __contains__(self, item: Any) -> bool:
        return True

    def __getitem__(self, item: Any) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()

# Простой пароль хашер для тестов
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Отключаем логирование в тестах
LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
        },
    },
}

# Отключаем кэширование
CACHES: Dict[str, Dict[str, str]] = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
