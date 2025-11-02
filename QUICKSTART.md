# Быстрый старт

## Вариант 1: Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/thehaffk/WorkoutTracker.git
cd WorkoutTracker

# Собрать и запустить контейнер
docker-compose up -d

# Загрузить демо-данные
docker exec workout-tracker-app python seed.py

# Приложение доступно на http://localhost:8888
```

Остановка:
```bash
docker-compose down
```

Просмотр логов:
```bash
docker-compose logs -f
```

## Вариант 2: Локальный запуск

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/thehaffk/WorkoutTracker.git
cd WorkoutTracker

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
# Запустить приложение (создаст БД и роли)
python app.py

# Остановить Ctrl+C

# Загрузить демо-данные
python seed.py

# Снова запустить приложение
python app.py
```

Приложение доступно: http://localhost:8080

## Тестовые пользователи (после seed.py)

- **admin** / Admin123 - администратор
- **trainer1** / Trainer123 - редактор (тренер)
- **trainer2** / Trainer223 - редактор (тренер)
- **user1** / User1Pass - просмотр
- **user2** / User2Pass - просмотр

## Запуск тестов

```bash
pytest tests/ -v
```

## Структура

- `/exercises` - управление упражнениями
- `/workouts` - управление тренировками
- `/reports` - отчёты с CSV экспортом
- `/files/exercises/<id>/upload` - загрузка файлов

## Функции

✅ Аутентификация (вход/выход/регистрация)
✅ 3 роли (viewer, editor, admin)
✅ CRUD упражнений
✅ CRUD тренировок
✅ Отчёт "Объём тренировок за период" + CSV
✅ Отчёт "Динамика личных рекордов" + CSV
✅ Загрузка файлов (PNG, JPG, JPEG, PDF, TXT, CSV, JSON)
✅ Экспорт упражнений в ZIP
✅ Поиск, фильтры, пагинация
✅ 55 тестов pytest
