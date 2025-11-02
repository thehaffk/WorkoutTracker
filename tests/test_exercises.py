"""
Тесты для модуля управления упражнениями
Проверяет функции просмотра создания редактирования удаления и фильтрации упражнений
"""
import pytest
from models import db, User, Exercise


def test_list_exercises(auth_client, sample_exercise):
    """
    Тест отображения списка упражнений
    Проверяет что страница со списком упражнений загружается корректно и отображает упражнения
    """
    response = auth_client.get('/exercises/')

    assert response.status_code == 200
    assert 'Тестовое упражнение' in response.get_data(as_text=True)


def test_create_exercise(auth_client, app):
    """
    Тест создания нового упражнения
    Проверяет что пользователь с правами editor может успешно создать новое упражнение в системе
    """
    response = auth_client.post('/exercises/create', data={
        'name': 'Жим гантелей',
        'description': 'Упражнение для развития грудных мышц',
        'muscle_group': 'Грудь',
        'equipment': 'Гантели',
        'difficulty': 'intermediate',
        'is_public': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Упражнение успешно добавлено' in response.get_data(as_text=True)

    # Проверка что упражнение создано в базе данных
    with app.app_context():
        exercise = Exercise.query.filter_by(name='Жим гантелей').first()
        assert exercise is not None
        assert exercise.muscle_group == 'Грудь'
        assert exercise.equipment == 'Гантели'
        assert exercise.difficulty == 'intermediate'
        assert exercise.is_public == True


def test_edit_exercise(auth_client, app):
    """
    Тест редактирования существующего упражнения
    Проверяет что пользователь может изменить параметры существующего упражнения
    """
    # Создаём упражнение для редактирования
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Приседания',
            description='Базовое упражнение для ног',
            muscle_group='Ноги',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Редактируем упражнение
    response = auth_client.post(f'/exercises/{exercise_id}/edit', data={
        'name': 'Приседания со штангой',
        'description': 'Базовое упражнение для развития мышц ног',
        'muscle_group': 'Ноги',
        'equipment': 'Штанга',
        'difficulty': 'advanced',
        'is_public': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Изменения в упражнении успешно сохранены' in response.get_data(as_text=True)

    # Проверка что изменения сохранены
    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise.name == 'Приседания со штангой'
        assert exercise.difficulty == 'advanced'


def test_delete_exercise(auth_client, app):
    """
    Тест удаления упражнения из системы
    Проверяет что пользователь может удалить своё упражнение
    """
    # Создаём упражнение для удаления
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Упражнение для удаления',
            description='Это упражнение будет удалено в тесте',
            muscle_group='Пресс',
            equipment='Без оборудования',
            difficulty='beginner',
            is_public=False,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Удаляем упражнение
    response = auth_client.post(f'/exercises/{exercise_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'Упражнение успешно удалено' in response.get_data(as_text=True)

    # Проверка что упражнение удалено из базы данных
    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise is None


def test_search_exercises(auth_client, app):
    """
    Тест поиска упражнений по названию
    Проверяет что функция поиска корректно фильтрует упражнения по введённому запросу
    """
    # Создаём несколько упражнений с разными названиями
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        exercise1 = Exercise(
            name='Жим штанги лёжа',
            description='Упражнение для груди',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        exercise2 = Exercise(
            name='Жим гантелей сидя',
            description='Упражнение для плеч',
            muscle_group='Плечи',
            equipment='Гантели',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        exercise3 = Exercise(
            name='Подтягивания',
            description='Упражнение для спины',
            muscle_group='Спина',
            equipment='Турник',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        db.session.add(exercise1)
        db.session.add(exercise2)
        db.session.add(exercise3)
        db.session.commit()

    # Ищем упражнения со словом "жим"
    response = auth_client.get('/exercises/?search=жим')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'Жим штанги лёжа' in content
    assert 'Жим гантелей сидя' in content
    assert 'Подтягивания' not in content


def test_filter_by_muscle_group(auth_client, app):
    """
    Тест фильтрации упражнений по группе мышц
    Проверяет что фильтр по группе мышц корректно отбирает упражнения
    """
    # Создаём упражнения для разных групп мышц
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        exercise1 = Exercise(
            name='Жим лёжа',
            description='Для груди',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        exercise2 = Exercise(
            name='Тяга штанги',
            description='Для спины',
            muscle_group='Спина',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True,
            owner_id=editor.id
        )

        db.session.add(exercise1)
        db.session.add(exercise2)
        db.session.commit()

    # Фильтруем по группе мышц "Грудь"
    response = auth_client.get('/exercises/?muscle_group=Грудь')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'Жим лёжа' in content


def test_create_exercise_without_required_fields(auth_client):
    """
    Тест создания упражнения без обязательных полей
    Проверяет что система требует заполнения всех обязательных полей при создании упражнения
    """
    response = auth_client.post('/exercises/create', data={
        'name': '',  # Пустое название
        'description': 'Описание',
        'muscle_group': '',  # Пустая группа мышц
        'difficulty': ''  # Пустой уровень сложности
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Необходимо указать название упражнения' in response.get_data(as_text=True)


def test_view_exercise_detail(auth_client, sample_exercise):
    """
    Тест просмотра детальной информации об упражнении
    Проверяет что страница с подробной информацией об упражнении отображается корректно
    """
    response = auth_client.get(f'/exercises/{sample_exercise}')

    assert response.status_code == 200
    assert 'Тестовое упражнение' in response.get_data(as_text=True)


def test_filter_by_difficulty(auth_client, app):
    """
    Тест фильтрации упражнений по уровню сложности
    Проверяет что фильтр по уровню сложности корректно отбирает упражнения
    """
    # Создаём упражнения разной сложности
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        exercise1 = Exercise(
            name='Лёгкое упражнение',
            description='Для начинающих',
            muscle_group='Пресс',
            equipment='Без оборудования',
            difficulty='beginner',
            is_public=True,
            owner_id=editor.id
        )

        exercise2 = Exercise(
            name='Сложное упражнение',
            description='Для продвинутых',
            muscle_group='Спина',
            equipment='Штанга',
            difficulty='advanced',
            is_public=True,
            owner_id=editor.id
        )

        db.session.add(exercise1)
        db.session.add(exercise2)
        db.session.commit()

    # Фильтруем по уровню сложности beginner
    response = auth_client.get('/exercises/?difficulty=beginner')

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'Лёгкое упражнение' in content


def test_pagination_exercises(auth_client, app):
    """
    Тест пагинации списка упражнений
    Проверяет что пагинация работает корректно при большом количестве упражнений
    """
    # Создаём много упражнений для проверки пагинации
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        for i in range(15):
            exercise = Exercise(
                name=f'Упражнение {i}',
                description=f'Описание упражнения {i}',
                muscle_group='Грудь',
                equipment='Штанга',
                difficulty='intermediate',
                is_public=True,
                owner_id=editor.id
            )
            db.session.add(exercise)

        db.session.commit()

    # Проверяем первую страницу
    response = auth_client.get('/exercises/?page=1')
    assert response.status_code == 200

    # Проверяем вторую страницу
    response = auth_client.get('/exercises/?page=2')
    assert response.status_code == 200


def test_create_private_exercise(auth_client, app):
    """
    Тест создания приватного упражнения (не публичного)
    Проверяет что можно создать упражнение доступное только владельцу
    """
    response = auth_client.post('/exercises/create', data={
        'name': 'Приватное упражнение',
        'description': 'Это упражнение видно только мне',
        'muscle_group': 'Ноги',
        'equipment': 'Гантели',
        'difficulty': 'intermediate'
        # Не передаём is_public
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Упражнение успешно добавлено' in response.get_data(as_text=True)

    with app.app_context():
        exercise = Exercise.query.filter_by(name='Приватное упражнение').first()
        assert exercise is not None
        assert exercise.is_public == False
