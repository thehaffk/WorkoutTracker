# Сводка по тестам WorkoutTracker

Создан комплект из **55 тестов** для приложения WorkoutTracker, покрывающих все основные модули системы.

## Структура тестов

### 1. conftest.py - Фикстуры (7 фикстур)
- `app` - тестовое приложение Flask с временной БД
- `client` - тестовый HTTP клиент
- `db_session` - сессия БД с автоматическим откатом
- `auth_client` - клиент авторизованный как editor
- `viewer_client` - клиент авторизованный как viewer
- `admin_client` - клиент авторизованный как admin
- `sample_exercise` - тестовое упражнение
- `sample_workout` - тестовая тренировка

### 2. test_auth.py - Аутентификация (10 тестов)
- `test_login_success` - успешный вход в систему
- `test_login_fail` - неверный пароль
- `test_register_success` - успешная регистрация
- `test_register_duplicate` - дубликат username
- `test_logout` - выход из системы
- `test_login_required` - редирект для неавторизованных
- `test_register_password_mismatch` - несовпадающие пароли
- `test_register_duplicate_email` - дубликат email
- `test_dashboard_requires_login` - доступ к dashboard
- `test_authenticated_redirect_from_login` - редирект с login

### 3. test_rbac.py - Ролевая модель (10 тестов)
- `test_viewer_cannot_create_exercise` - viewer не может создать
- `test_editor_can_create_exercise` - editor может создать
- `test_admin_can_delete_any` - admin может удалить любое
- `test_owner_can_edit_own` - owner может редактировать своё
- `test_role_required_decorator` - декоратор работает корректно
- `test_viewer_can_view_exercises` - viewer может просматривать
- `test_viewer_can_view_exercise_detail` - viewer видит детали
- `test_non_owner_cannot_edit` - не владелец не может редактировать
- `test_non_owner_cannot_delete` - не владелец не может удалить
- `test_editor_can_edit_own` - editor редактирует своё

### 4. test_exercises.py - Упражнения (11 тестов)
- `test_list_exercises` - список отображается
- `test_create_exercise` - создание упражнения
- `test_edit_exercise` - редактирование
- `test_delete_exercise` - удаление
- `test_search_exercises` - поиск работает
- `test_filter_by_muscle_group` - фильтр по группе мышц
- `test_create_exercise_without_required_fields` - валидация полей
- `test_view_exercise_detail` - просмотр деталей
- `test_filter_by_difficulty` - фильтр по сложности
- `test_pagination_exercises` - пагинация
- `test_create_private_exercise` - приватное упражнение

### 5. test_reports.py - Отчёты (11 тестов)
- `test_volume_report` - отчёт по объёму
- `test_volume_csv_export` - CSV экспорт объёма
- `test_volume_csv_structure` - структура CSV
- `test_records_report` - отчёт по рекордам
- `test_records_csv_export` - CSV экспорт рекордов
- `test_volume_report_with_date_filter` - фильтр по датам
- `test_records_report_with_exercise_filter` - фильтр по упражнению
- `test_volume_report_calculation` - корректность расчётов
- `test_records_report_max_weight` - определение макс веса
- `test_empty_volume_report` - пустой отчёт
- `test_empty_records_report` - пустой отчёт рекордов

### 6. test_files.py - Файлы (13 тестов)
- `test_upload_valid_file` - загрузка валидного файла
- `test_upload_invalid_extension` - отклонение неверного типа
- `test_upload_too_large` - отклонение по размеру
- `test_total_size_limit` - проверка суммарного лимита
- `test_zip_export` - экспорт в ZIP
- `test_zip_contains_json` - ZIP содержит JSON
- `test_zip_contains_attachments` - ZIP содержит файлы
- `test_delete_file` - удаление файла
- `test_upload_without_file` - загрузка без файла
- `test_exercise_export_to_zip` - экспорт упражнения
- `test_upload_multiple_files` - множественная загрузка
- `test_upload_file_to_nonexistent_exercise` - несуществующее упражнение
- `test_json_export_structure` - структура JSON экспорта

## Покрытие функционала

### Аутентификация и авторизация
- ✅ Регистрация пользователей
- ✅ Вход/выход из системы
- ✅ Защита маршрутов (@login_required)
- ✅ Ролевая модель (viewer, editor, admin)
- ✅ Проверка прав доступа

### Управление упражнениями
- ✅ CRUD операции (создание, чтение, редактирование, удаление)
- ✅ Поиск по названию
- ✅ Фильтрация по группе мышц и сложности
- ✅ Пагинация
- ✅ Публичные/приватные упражнения

### Отчёты
- ✅ Отчёт по объёму тренировок
- ✅ Отчёт по личным рекордам
- ✅ Экспорт в CSV с правильной кодировкой
- ✅ Фильтрация по датам и упражнениям
- ✅ Корректность математических расчётов

### Работа с файлами
- ✅ Загрузка файлов к упражнениям
- ✅ Валидация типов и размеров файлов
- ✅ Контроль суммарного размера
- ✅ Удаление файлов
- ✅ Экспорт в ZIP архив
- ✅ Корректность структуры JSON

## Запуск тестов

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск всех тестов
pytest tests/ -v

# Запуск конкретного файла
pytest tests/test_auth.py -v

# Запуск с покрытием
pytest tests/ --cov=. --cov-report=html

# Запуск конкретного теста
pytest tests/test_auth.py::test_login_success -v
```

## Особенности реализации

1. **Изоляция тестов**: Каждый тест использует временную БД SQLite в памяти
2. **Автоматический rollback**: Изменения БД откатываются после каждого теста
3. **Фикстуры для ролей**: Готовые клиенты для тестирования разных уровней доступа
4. **Реальные HTTP запросы**: Тесты используют Flask test client для имитации браузера
5. **Проверка БД**: Тесты проверяют не только HTTP ответы, но и состояние БД

## Стиль кода

- Подробные docstrings на русском языке
- Описательные имена тестов
- Комментарии для сложной логики
- Следование PEP 8
- Джуниорский стиль (понятный и подробный)
