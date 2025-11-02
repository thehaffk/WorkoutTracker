"""
Тесты для системы ролевого управления доступом (RBAC)
Проверяет корректность работы разграничения прав доступа для разных ролей пользователей
"""
import pytest
from models import db, User, Exercise


def test_viewer_cannot_create_exercise(viewer_client):
    """
    Тест что пользователь с ролью viewer не может создать упражнение
    Проверяет что система корректно ограничивает доступ к функции создания упражнений
    """
    response = viewer_client.get('/exercises/create', follow_redirects=True)

    assert response.status_code == 200
    assert 'У вас недостаточно прав' in response.get_data(as_text=True)


def test_editor_can_create_exercise(auth_client, app):
    """
    Тест что пользователь с ролью editor может создать упражнение
    Проверяет что пользователи с правами редактора могут добавлять новые упражнения в систему
    """
    response = auth_client.post('/exercises/create', data={
        'name': 'Новое упражнение',
        'description': 'Описание нового упражнения для тестирования',
        'muscle_group': 'Спина',
        'equipment': 'Гантели',
        'difficulty': 'beginner',
        'is_public': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Упражнение успешно добавлено' in response.get_data(as_text=True)

    # Проверка что упражнение создано в базе данных
    with app.app_context():
        exercise = Exercise.query.filter_by(name='Новое упражнение').first()
        assert exercise is not None
        assert exercise.muscle_group == 'Спина'


def test_admin_can_delete_any(admin_client, app, sample_exercise):
    """
    Тест что администратор может удалить любое упражнение
    Проверяет что пользователи с ролью admin имеют полный доступ к удалению упражнений
    """
    # Создаём упражнение от имени другого пользователя
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Упражнение editor',
            description='Упражнение созданное пользователем editor',
            muscle_group='Ноги',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=False,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Администратор удаляет чужое упражнение
    response = admin_client.post(f'/exercises/{exercise_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'Упражнение успешно удалено' in response.get_data(as_text=True)

    # Проверка что упражнение удалено из базы данных
    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise is None


def test_owner_can_edit_own(auth_client, app):
    """
    Тест что владелец может редактировать своё упражнение
    Проверяет что пользователь может изменять упражнения которые он создал
    """
    # Создаём упражнение от имени editor
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Упражнение для редактирования',
            description='Исходное описание',
            muscle_group='Пресс',
            equipment='Без оборудования',
            difficulty='beginner',
            is_public=False,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Редактируем упражнение
    response = auth_client.post(f'/exercises/{exercise_id}/edit', data={
        'name': 'Обновлённое упражнение',
        'description': 'Обновлённое описание упражнения',
        'muscle_group': 'Пресс',
        'equipment': 'Без оборудования',
        'difficulty': 'intermediate'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Изменения в упражнении успешно сохранены' in response.get_data(as_text=True)

    # Проверка что изменения сохранены
    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise.name == 'Обновлённое упражнение'
        assert exercise.difficulty == 'intermediate'


def test_role_required_decorator(viewer_client):
    """
    Тест что декоратор role_required корректно работает
    Проверяет что декоратор правильно ограничивает доступ к функциям требующим определённых ролей
    """
    # Попытка создать упражнение с ролью viewer (недостаточно прав)
    response = viewer_client.post('/exercises/create', data={
        'name': 'Тестовое упражнение',
        'muscle_group': 'Грудь',
        'difficulty': 'beginner'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'У вас недостаточно прав' in response.get_data(as_text=True)


def test_viewer_can_view_exercises(viewer_client, sample_exercise):
    """
    Тест что viewer может просматривать упражнения
    Проверяет что пользователи с ролью viewer имеют доступ к просмотру списка упражнений
    """
    response = viewer_client.get('/exercises/', follow_redirects=True)

    assert response.status_code == 200
    # Страница со списком упражнений должна загрузиться успешно


def test_viewer_can_view_exercise_detail(viewer_client, sample_exercise):
    """
    Тест что viewer может просматривать детали упражнения
    Проверяет что пользователи с ролью viewer могут открывать страницы с подробной информацией об упражнениях
    """
    response = viewer_client.get(f'/exercises/{sample_exercise}', follow_redirects=True)

    assert response.status_code == 200


def test_non_owner_cannot_edit(viewer_client, app):
    """
    Тест что не владелец не может редактировать чужое упражнение
    Проверяет что система запрещает редактирование упражнений пользователями не являющимися их владельцами
    """
    # Создаём упражнение от имени editor
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Упражнение editor',
            description='Описание',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=False,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Попытка редактировать от имени viewer (нет прав вообще)
    response = viewer_client.get(f'/exercises/{exercise_id}/edit', follow_redirects=True)

    assert response.status_code == 200
    assert 'У вас недостаточно прав' in response.get_data(as_text=True)


def test_non_owner_cannot_delete(auth_client, app):
    """
    Тест что не владелец и не администратор не может удалить чужое упражнение
    Проверяет что система запрещает удаление упражнений пользователями без соответствующих прав
    """
    # Создаём упражнение от имени admin
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        exercise = Exercise(
            name='Упражнение admin',
            description='Описание',
            muscle_group='Спина',
            equipment='Турник',
            difficulty='advanced',
            is_public=False,
            owner_id=admin.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Попытка удалить от имени editor (не владелец и не admin)
    response = auth_client.post(f'/exercises/{exercise_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'У вас нет прав для удаления данного упражнения' in response.get_data(as_text=True)

    # Проверка что упражнение не удалено
    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise is not None


def test_editor_can_edit_own(auth_client, app):
    """
    Тест что editor может редактировать своё собственное упражнение
    Проверяет полный цикл создания и редактирования упражнения пользователем с ролью editor
    """
    # Создаём упражнение
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()
        exercise = Exercise(
            name='Моё упражнение',
            description='Описание',
            muscle_group='Плечи',
            equipment='Гантели',
            difficulty='beginner',
            is_public=True,
            owner_id=editor.id
        )
        db.session.add(exercise)
        db.session.commit()
        exercise_id = exercise.id

    # Редактируем
    response = auth_client.post(f'/exercises/{exercise_id}/edit', data={
        'name': 'Моё обновлённое упражнение',
        'description': 'Новое описание',
        'muscle_group': 'Плечи',
        'equipment': 'Гантели',
        'difficulty': 'intermediate'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Изменения в упражнении успешно сохранены' in response.get_data(as_text=True)

    with app.app_context():
        exercise = Exercise.query.get(exercise_id)
        assert exercise.name == 'Моё обновлённое упражнение'
