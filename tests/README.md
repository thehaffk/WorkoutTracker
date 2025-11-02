# Тесты WorkoutTracker

Комплексный набор тестов для приложения системы учёта тренировок.

## Содержание

- **55 тестов** покрывающих все основные модули
- Автоматическая изоляция тестов с временной БД
- Фикстуры для разных ролей пользователей
- Проверка RBAC и прав доступа

## Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск всех тестов

```bash
pytest tests/ -v
```

### Запуск конкретного модуля

```bash
# Тесты аутентификации
pytest tests/test_auth.py -v

# Тесты RBAC
pytest tests/test_rbac.py -v

# Тесты упражнений
pytest tests/test_exercises.py -v

# Тесты отчётов
pytest tests/test_reports.py -v

# Тесты файлов
pytest tests/test_files.py -v
```

### Запуск одного теста

```bash
pytest tests/test_auth.py::test_login_success -v
```

### Запуск с покрытием кода

```bash
# Установка coverage
pip install pytest-cov

# Запуск с отчётом
pytest tests/ --cov=. --cov-report=html

# Открыть отчёт
open htmlcov/index.html
```

## Структура тестов

```
tests/
├── __init__.py                 # Инициализация пакета
├── conftest.py                 # Общие фикстуры
├── test_auth.py                # Тесты аутентификации (10)
├── test_rbac.py                # Тесты прав доступа (10)
├── test_exercises.py           # Тесты упражнений (11)
├── test_reports.py             # Тесты отчётов (11)
├── test_files.py               # Тесты файлов (13)
├── TEST_SUMMARY.md             # Подробная сводка
└── README.md                   # Эта инструкция
```

## Фикстуры

### Базовые фикстуры

- **app** - тестовое Flask приложение с временной БД
- **client** - HTTP клиент для запросов
- **db_session** - сессия БД с автоматическим откатом

### Фикстуры аутентификации

- **auth_client** - клиент авторизованный как editor
- **viewer_client** - клиент авторизованный как viewer
- **admin_client** - клиент авторизованный как admin

### Фикстуры данных

- **sample_exercise** - тестовое упражнение
- **sample_workout** - тестовая тренировка с упражнением

## Тестовые пользователи

Автоматически создаются при запуске тестов:

| Username | Password     | Role   | Описание                    |
|----------|--------------|--------|-----------------------------|
| viewer   | Password123  | viewer | Только просмотр             |
| editor   | Password123  | editor | Создание и редактирование   |
| admin    | Password123  | admin  | Полный доступ               |

## Покрытие функционала

### ✅ Аутентификация (10 тестов)
- Регистрация с валидацией
- Вход/выход из системы
- Проверка дубликатов
- Защита маршрутов

### ✅ RBAC (10 тестов)
- Проверка прав viewer
- Проверка прав editor
- Проверка прав admin
- Владение объектами

### ✅ Упражнения (11 тестов)
- CRUD операции
- Поиск и фильтрация
- Пагинация
- Валидация данных

### ✅ Отчёты (11 тестов)
- Отчёт по объёму
- Отчёт по рекордам
- Экспорт в CSV
- Фильтры по датам

### ✅ Файлы (13 тестов)
- Загрузка файлов
- Валидация типов
- Контроль размера
- Экспорт в ZIP

## Примеры использования

### Проверка авторизации

```python
def test_login_success(client, app):
    """Тест успешного входа"""
    response = client.post('/login', data={
        'username': 'editor',
        'password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'успешно вошли' in response.get_data(as_text=True)
```

### Проверка RBAC

```python
def test_viewer_cannot_create(viewer_client):
    """Viewer не может создавать"""
    response = viewer_client.get('/exercises/create',
                                 follow_redirects=True)

    assert 'недостаточно прав' in response.get_data(as_text=True)
```

### Проверка БД

```python
def test_create_exercise(auth_client, app):
    """Создание сохраняется в БД"""
    auth_client.post('/exercises/create', data={...})

    with app.app_context():
        exercise = Exercise.query.filter_by(name='Новое').first()
        assert exercise is not None
```

## Особенности

### Изоляция тестов
Каждый тест работает с чистой БД. Изменения автоматически откатываются.

### Временная БД
Используется SQLite в памяти. После тестов всё удаляется.

### Реальные HTTP запросы
Тесты имитируют настоящие запросы браузера через Flask test client.

### Проверка на всех уровнях
- HTTP ответы (коды, содержимое)
- Состояние БД (записи созданы/удалены)
- Flash сообщения (уведомления пользователю)

## Отладка

### Запуск с подробным выводом

```bash
pytest tests/ -vv
```

### Остановка на первой ошибке

```bash
pytest tests/ -x
```

### Запуск только упавших тестов

```bash
pytest tests/ --lf
```

### Вывод print в тестах

```bash
pytest tests/ -s
```

### Подробный traceback

```bash
pytest tests/ --tb=long
```

## Continuous Integration

Для CI/CD можно использовать:

```bash
# Запуск в CI окружении
pytest tests/ --junitxml=report.xml --cov=. --cov-report=xml
```

## Разработка новых тестов

### Шаблон теста

```python
def test_my_feature(auth_client, app):
    """
    Описание что тестируем
    """
    # Arrange - подготовка данных
    with app.app_context():
        # создание тестовых данных
        pass

    # Act - выполнение действия
    response = auth_client.post('/url', data={...})

    # Assert - проверка результата
    assert response.status_code == 200
    assert 'expected text' in response.get_data(as_text=True)

    # Проверка БД
    with app.app_context():
        # проверка изменений в БД
        pass
```

### Использование фикстур

```python
@pytest.fixture
def my_data(app):
    """Создание тестовых данных"""
    with app.app_context():
        obj = Model(name='test')
        db.session.add(obj)
        db.session.commit()
        return obj.id
```

## Дополнительные ресурсы

- [Pytest документация](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [TEST_SUMMARY.md](TEST_SUMMARY.md) - полная сводка тестов

## Вопросы и проблемы

Если тесты не запускаются:

1. Проверьте установку зависимостей: `pip list | grep pytest`
2. Убедитесь что находитесь в корне проекта
3. Проверьте версию Python: `python --version` (требуется 3.8+)
4. Попробуйте пересоздать venv и переустановить зависимости
