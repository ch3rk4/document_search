#!/usr/bin/env python
"""
Скрипт для инициализации проекта поисковика документов
"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Запуск команды с описанием"""
    print(f"\n📋 {description}")
    print(f"💻 Выполняем: {command}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Успешно: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e.stderr}")
        return False


def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверяем зависимости...")

    dependencies = {
        'python': 'python --version',
        'pip': 'pip --version',
        'docker': 'docker --version',
        'docker-compose': 'docker-compose --version'
    }

    for name, command in dependencies.items():
        if run_command(command, f"Проверяем {name}"):
            print(f"✅ {name} доступен")
        else:
            print(f"❌ {name} не найден")
            return False

    return True


def init_project():
    """Инициализация проекта"""
    print("🚀 Инициализация проекта поисковика документов")
    print("=" * 50)

    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    print(f"📁 Рабочая директория: {project_root}")

    # Проверяем зависимости
    if not check_dependencies():
        print("\n❌ Не все зависимости установлены. Проверьте установку Python, pip, Docker и docker-compose")
        return False

    # Создаем необходимые директории
    directories = ['logs', 'media', 'src/staticfiles']
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Создана директория: {directory}")

    # Копируем .env.example в .env если .env не существует
    env_example = project_root / '.env.example'
    env_file = project_root / '.env'

    if env_example.exists() and not env_file.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("📄 Создан файл .env из .env.example")

    print("\n🐳 Запуск контейнеров Docker...")

    # Останавливаем существующие контейнеры
    run_command("docker-compose down", "Остановка существующих контейнеров")

    # Собираем и запускаем контейнеры
    if run_command("docker-compose up -d --build", "Сборка и запуск контейнеров"):
        print("\n✅ Проект успешно инициализирован!")
        print("\n📋 Что дальше:")
        print("1. Откройте http://localhost в браузере")
        print("2. Для админ-панели: http://localhost/admin")
        print("3. Войдите как admin/admin123 или author/author123")
        print("4. Загружайте файлы и ищите слова в документах!")

        print("\n🛠️  Полезные команды:")
        print("• Остановить проект: docker-compose down")
        print("• Посмотреть логи: docker-compose logs -f")
        print("• Перезапустить: docker-compose restart")

        return True
    else:
        print("\n❌ Ошибка при запуске контейнеров")
        return False


if __name__ == '__main__':
    success = init_project()
    sys.exit(0 if success else 1)