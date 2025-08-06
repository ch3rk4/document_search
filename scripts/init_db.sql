-- Инициализация базы данных PostgreSQL
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Создание индексов для полнотекстового поиска
-- Эти индексы будут созданы после применения миграций Django