"""
Файл конфигурации pytest с общими фикстурами для тестирования приложения WorkoutTracker
Содержит базовые фикстуры для работы с приложением, базой данных и аутентификацией
"""
import pytest
import os
import tempfile
from app import app as flask_app, init_db
from models import db, User, Role, Exercise, Workout, WorkoutExercise, Attachment
from datetime import datetime, date


@pytest.fixture
def app():
    """
    Фикстура для создания тестового приложения Flask
    Настраивает приложение в тестовом режиме с временной базой данных SQLite в памяти
    """
    # Создание временного файла для базы данных
    db_fd, db_path = tempfile.mkstemp()

    # Настройка приложения для тестирования
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SECRET_KEY'] = 'test-secret-key'

    # Настройка директории для загрузки файлов
    upload_folder = tempfile.mkdtemp()
    flask_app.config['UPLOAD_FOLDER'] = upload_folder

    # Инициализация базы данных с тестовыми данными
    with flask_app.app_context():
        db.create_all()

        # Создание ролей для тестирования
        viewer_role = Role(name='viewer', description='Роль для просмотра данных без возможности редактирования')
        editor_role = Role(name='editor', description='Роль для редактирования данных в предметной области тренировок')
        admin_role = Role(name='admin', description='Административная роль с полным доступом ко всем функциям системы')

        db.session.add(viewer_role)
        db.session.add(editor_role)
        db.session.add(admin_role)
        db.session.commit()

        # Создание тестовых пользователей с разными ролями
        # Пользователь с ролью viewer
        viewer_user = User(username='viewer', email='viewer@test.com', role_id=viewer_role.id)
        viewer_user.set_password('Password123')

        # Пользователь с ролью editor
        editor_user = User(username='editor', email='editor@test.com', role_id=editor_role.id)
        editor_user.set_password('Password123')

        # Пользователь с ролью admin
        admin_user = User(username='admin', email='admin@test.com', role_id=admin_role.id)
        admin_user.set_password('Password123')

        db.session.add(viewer_user)
        db.session.add(editor_user)
        db.session.add(admin_user)
        db.session.commit()

    yield flask_app

    # Очистка после тестов
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """
    Фикстура для создания тестового клиента Flask
    Позволяет выполнять HTTP запросы к приложению в тестовом режиме
    """
    return app.test_client()


@pytest.fixture
def db_session(app):
    """
    Фикстура для доступа к сессии базы данных
    Автоматически откатывает изменения после каждого теста для изоляции
    """
    with app.app_context():
        yield db
        db.session.rollback()


@pytest.fixture
def auth_client(client, app):
    """
    Фикстура для создания клиента с авторизованным пользователем
    По умолчанию авторизуется под пользователем editor для тестирования функций редактирования
    """
    with app.app_context():
        # Авторизация как editor (доступны функции редактирования)
        client.post('/login', data={
            'username': 'editor',
            'password': 'Password123'
        }, follow_redirects=True)

    return client


@pytest.fixture
def viewer_client(client, app):
    """
    Фикстура для создания клиента с авторизованным пользователем-viewer
    Используется для тестирования ограничений доступа
    """
    with app.app_context():
        client.post('/login', data={
            'username': 'viewer',
            'password': 'Password123'
        }, follow_redirects=True)

    return client


@pytest.fixture
def admin_client(client, app):
    """
    Фикстура для создания клиента с авторизованным администратором
    Используется для тестирования административных функций
    """
    with app.app_context():
        client.post('/login', data={
            'username': 'admin',
            'password': 'Password123'
        }, follow_redirects=True)

    return client


@pytest.fixture
def sample_exercise(app):
    """
    Фикстура для создания тестового упражнения
    Возвращает публичное упражнение доступное всем пользователям
    """
    with app.app_context():
        exercise = Exercise(
            name='Тестовое упражнение',
            description='Описание тестового упражнения для проверки функционала системы',
            muscle_group='Грудь',
            equipment='Штанга',
            difficulty='intermediate',
            is_public=True
        )
        db.session.add(exercise)
        db.session.commit()

        # Возвращаем ID для использования в тестах
        exercise_id = exercise.id

    return exercise_id


@pytest.fixture
def sample_workout(app, sample_exercise):
    """
    Фикстура для создания тестовой тренировки
    Создаёт тренировку с упражнением для пользователя editor
    """
    with app.app_context():
        # Получение пользователя editor для привязки тренировки
        editor = User.query.filter_by(username='editor').first()

        # Создание тренировки
        workout = Workout(
            date=date.today(),
            workout_type='Силовая',
            duration=60,
            notes='Тестовая тренировка для проверки функционала',
            owner_id=editor.id
        )
        db.session.add(workout)
        db.session.commit()

        # Добавление упражнения к тренировке
        workout_exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=sample_exercise,
            sets=3,
            reps=10,
            weight=50.0,
            order=1
        )
        db.session.add(workout_exercise)
        db.session.commit()

        workout_id = workout.id

    return workout_id
