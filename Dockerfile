FROM python:3.13

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание необходимых директорий с правильными правами
RUN mkdir -p logs media src/staticfiles && \
    chmod 755 logs media src/staticfiles

# Создание непривилегированного пользователя
RUN adduser --disabled-password --gecos '' appuser

# Изменение владельца файлов после копирования
RUN chown -R appuser:appuser /app

# Переключение на непривилегированного пользователя
USER appuser

# Переменные окружения
ENV PYTHONPATH=/app/src
ENV DJANGO_SETTINGS_MODULE=document_search.settings

# Открытие порта
EXPOSE 8000

# Команда по умолчанию
CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]