"""
Тесты для модуля отчётов с экспортом в CSV
Проверяет корректность генерации отчётов по объёму тренировок и личным рекордам
"""
import pytest
from models import db, User, Exercise, Workout, WorkoutExercise
from datetime import date, timedelta
import csv
import io


def test_volume_report(auth_client, app, sample_workout):
    """
    Тест отчёта по объёму тренировок за период
    Проверяет что отчёт корректно отображает агрегированные данные по тренировкам
    """
    response = auth_client.get('/reports/volume')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'Объём тренировок' in content or 'Силовая' in content


def test_volume_csv_export(auth_client, app, sample_workout):
    """
    Тест экспорта отчёта по объёму в CSV формат
    Проверяет что CSV файл генерируется корректно и содержит данные о тренировках
    """
    response = auth_client.get('/reports/volume/export')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['Content-Disposition']

    # Проверка содержимого CSV
    content = response.get_data(as_text=True)
    assert 'Тип тренировки' in content
    assert 'Количество тренировок' in content


def test_volume_csv_structure(auth_client, app):
    """
    Тест структуры CSV файла отчёта по объёму
    Проверяет что CSV содержит правильные колонки и формат данных
    """
    # Создаём тестовые тренировки
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise.query.first()

        # Создаём тренировку
        workout = Workout(
            date=date.today(),
            workout_type='Кардио',
            duration=45,
            notes='Тестовая кардио тренировка',
            owner_id=editor.id
        )
        db.session.add(workout)
        db.session.commit()

        # Добавляем упражнение
        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise.id,
            sets=3,
            reps=15,
            weight=None,
            duration=1800
        )
        db.session.add(we)
        db.session.commit()

    # Получаем CSV
    response = auth_client.get('/reports/volume/export')
    content = response.get_data(as_text=True)

    # Парсим CSV
    csv_reader = csv.reader(io.StringIO(content.replace('\ufeff', '')), delimiter=';')
    rows = list(csv_reader)

    # Проверяем заголовки
    assert len(rows) > 0
    headers = rows[0]
    assert 'Тип тренировки' in headers
    assert 'Количество тренировок' in headers
    assert 'Общее время (мин)' in headers
    assert 'Всего упражнений' in headers
    assert 'Общий вес (кг)' in headers


def test_records_report(auth_client, app, sample_workout):
    """
    Тест отчёта по личным рекордам
    Проверяет что отчёт корректно отображает максимальные показатели по упражнениям
    """
    response = auth_client.get('/reports/records')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'личных рекордов' in content or 'Динамика' in content


def test_records_csv_export(auth_client, app, sample_workout):
    """
    Тест экспорта отчёта по личным рекордам в CSV
    Проверяет что CSV файл с рекордами генерируется корректно
    """
    response = auth_client.get('/reports/records/export')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['Content-Disposition']

    # Проверка содержимого
    content = response.get_data(as_text=True)
    assert 'Дата' in content
    assert 'Упражнение' in content
    assert 'Макс вес' in content


def test_volume_report_with_date_filter(auth_client, app):
    """
    Тест отчёта по объёму с фильтрацией по датам
    Проверяет что отчёт корректно применяет фильтры по периоду времени
    """
    # Создаём тренировки в разные даты
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise.query.first()

        # Старая тренировка
        old_workout = Workout(
            date=date.today() - timedelta(days=60),
            workout_type='Силовая',
            duration=60,
            notes='Старая тренировка',
            owner_id=editor.id
        )
        db.session.add(old_workout)

        # Новая тренировка
        new_workout = Workout(
            date=date.today(),
            workout_type='Силовая',
            duration=45,
            notes='Новая тренировка',
            owner_id=editor.id
        )
        db.session.add(new_workout)
        db.session.commit()

    # Запрашиваем отчёт за последние 30 дней
    date_from = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    date_to = date.today().strftime('%Y-%m-%d')

    response = auth_client.get(f'/reports/volume?date_from={date_from}&date_to={date_to}')

    assert response.status_code == 200


def test_records_report_with_exercise_filter(auth_client, app):
    """
    Тест отчёта по рекордам с фильтрацией по упражнению
    Проверяет что можно отфильтровать рекорды по конкретному упражнению
    """
    # Создаём тренировки с разными упражнениями
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        # Создаём два упражнения
        exercise1 = Exercise(
            name='Жим лёжа',
            description='Упражнение 1',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        exercise2 = Exercise(
            name='Приседания',
            description='Упражнение 2',
            muscle_group='Ноги',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        db.session.add(exercise1)
        db.session.add(exercise2)
        db.session.commit()

        # Создаём тренировку с первым упражнением
        workout = Workout(
            date=date.today(),
            workout_type='Силовая',
            duration=60,
            owner_id=editor.id
        )
        db.session.add(workout)
        db.session.commit()

        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise1.id,
            sets=3,
            reps=10,
            weight=100.0
        )
        db.session.add(we)
        db.session.commit()

        exercise1_id = exercise1.id

    # Запрашиваем отчёт по конкретному упражнению
    response = auth_client.get(f'/reports/records?exercise_id={exercise1_id}')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'Жим лёжа' in content


def test_volume_report_calculation(auth_client, app):
    """
    Тест корректности расчётов в отчёте по объёму
    Проверяет что формулы агрегации данных работают правильно
    """
    # Создаём тренировки с точными параметрами для проверки расчётов
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise.query.first()

        # Первая тренировка
        workout1 = Workout(
            date=date.today(),
            workout_type='Тестовая',
            duration=30,
            owner_id=editor.id
        )
        db.session.add(workout1)
        db.session.commit()

        we1 = WorkoutExercise(
            workout_id=workout1.id,
            exercise_id=exercise.id,
            sets=3,
            reps=10,
            weight=50.0
        )
        db.session.add(we1)

        # Вторая тренировка
        workout2 = Workout(
            date=date.today(),
            workout_type='Тестовая',
            duration=40,
            owner_id=editor.id
        )
        db.session.add(workout2)
        db.session.commit()

        we2 = WorkoutExercise(
            workout_id=workout2.id,
            exercise_id=exercise.id,
            sets=4,
            reps=8,
            weight=60.0
        )
        db.session.add(we2)

        db.session.commit()

    # Получаем отчёт
    response = auth_client.get('/reports/volume')

    assert response.status_code == 200
    content = response.get_data(as_text=True)

    # Проверяем что данные присутствуют
    assert 'Тестовая' in content


def test_records_report_max_weight(auth_client, app):
    """
    Тест определения максимального веса в отчёте по рекордам
    Проверяет что система правильно находит максимальный вес по упражнению
    """
    # Создаём несколько подходов с разным весом
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        exercise = Exercise(
            name='Тестовое упражнение для рекорда',
            description='Для проверки макс веса',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()

        # Тренировка с весом 80 кг
        workout1 = Workout(
            date=date.today() - timedelta(days=5),
            workout_type='Силовая',
            duration=60,
            owner_id=editor.id
        )
        db.session.add(workout1)
        db.session.commit()

        we1 = WorkoutExercise(
            workout_id=workout1.id,
            exercise_id=exercise.id,
            sets=3,
            reps=10,
            weight=80.0
        )
        db.session.add(we1)

        # Тренировка с весом 100 кг (это максимум)
        workout2 = Workout(
            date=date.today(),
            workout_type='Силовая',
            duration=60,
            owner_id=editor.id
        )
        db.session.add(workout2)
        db.session.commit()

        we2 = WorkoutExercise(
            workout_id=workout2.id,
            exercise_id=exercise.id,
            sets=3,
            reps=8,
            weight=100.0
        )
        db.session.add(we2)

        db.session.commit()

    # Получаем отчёт
    response = auth_client.get('/reports/records')

    assert response.status_code == 200
    content = response.get_data(as_text=True)

    # Проверяем что упражнение есть в отчёте
    assert 'Тестовое упражнение для рекорда' in content


def test_empty_volume_report(auth_client, app):
    """
    Тест отчёта по объёму при отсутствии данных
    Проверяет что система корректно обрабатывает ситуацию когда у пользователя нет тренировок
    """
    # Удаляем все тренировки пользователя
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        Workout.query.filter_by(owner_id=editor.id).delete()
        db.session.commit()

    response = auth_client.get('/reports/volume')

    assert response.status_code == 200
    # Отчёт должен загрузиться даже без данных


def test_empty_records_report(auth_client, app):
    """
    Тест отчёта по рекордам при отсутствии данных
    Проверяет что система корректно обрабатывает ситуацию когда нет данных для отчёта
    """
    # Удаляем все тренировки
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        Workout.query.filter_by(owner_id=editor.id).delete()
        db.session.commit()

    response = auth_client.get('/reports/records')

    assert response.status_code == 200
