"""
Тесты для системы аутентификации и авторизации пользователей
Проверяет корректность работы регистрации, входа, выхода и защиты маршрутов
"""
import pytest
from models import db, User, Role


def test_login_success(client, app):
    """
    Тест успешного входа в систему с корректными учётными данными
    Проверяет что пользователь может войти в систему используя правильный логин и пароль
    """
    response = client.post('/login', data={
        'username': 'editor',
        'password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Вы успешно вошли в систему' in response.get_data(as_text=True)


def test_login_fail(client):
    """
    Тест неудачного входа в систему с неверным паролем
    Проверяет что система корректно отклоняет попытку входа с неправильными учётными данными
    """
    response = client.post('/login', data={
        'username': 'editor',
        'password': 'wrongpassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Неверное имя пользователя или пароль' in response.get_data(as_text=True)


def test_register_success(client, app):
    """
    Тест успешной регистрации нового пользователя в системе
    Проверяет что новый пользователь может зарегистрироваться с корректными данными
    """
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@test.com',
        'password': 'NewPassword123',
        'confirm_password': 'NewPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Регистрация прошла успешно' in response.get_data(as_text=True)

    # Проверка что пользователь создан в базе данных
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@test.com'
        assert user.role.name == 'viewer'  # По умолчанию роль viewer


def test_register_duplicate(client, app):
    """
    Тест попытки регистрации пользователя с существующим именем
    Проверяет что система не позволяет создать дубликат пользователя
    """
    response = client.post('/register', data={
        'username': 'editor',  # Пользователь уже существует
        'email': 'newemail@test.com',
        'password': 'NewPassword123',
        'confirm_password': 'NewPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Пользователь с таким именем уже существует' in response.get_data(as_text=True)


def test_logout(client):
    """
    Тест выхода пользователя из системы
    Проверяет что пользователь может успешно завершить сессию
    """
    # Сначала входим в систему
    client.post('/login', data={
        'username': 'editor',
        'password': 'Password123'
    }, follow_redirects=True)

    # Выходим из системы
    response = client.get('/logout', follow_redirects=True)

    assert response.status_code == 200
    assert 'Вы успешно вышли из системы' in response.get_data(as_text=True)


def test_login_required(client):
    """
    Тест редиректа для неавторизованных пользователей при попытке доступа к защищённым маршрутам
    Проверяет что система корректно перенаправляет неавторизованных пользователей на страницу входа
    """
    response = client.get('/dashboard', follow_redirects=False)

    # Должен быть редирект на страницу логина
    assert response.status_code == 302
    assert '/login' in response.location


def test_register_password_mismatch(client):
    """
    Тест регистрации с несовпадающими паролями
    Проверяет что система отклоняет регистрацию если пароли не совпадают
    """
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'testuser@test.com',
        'password': 'Password123',
        'confirm_password': 'DifferentPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Введённые пароли не совпадают' in response.get_data(as_text=True)


def test_register_duplicate_email(client, app):
    """
    Тест попытки регистрации с существующим email
    Проверяет что система не позволяет использовать email который уже зарегистрирован
    """
    response = client.post('/register', data={
        'username': 'newusername',
        'email': 'editor@test.com',  # Email уже существует
        'password': 'NewPassword123',
        'confirm_password': 'NewPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Пользователь с таким email уже зарегистрирован' in response.get_data(as_text=True)


def test_dashboard_requires_login(client):
    """
    Тест доступа к панели управления без авторизации
    Проверяет что неавторизованный пользователь не может получить доступ к dashboard
    """
    response = client.get('/dashboard', follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.location


def test_authenticated_redirect_from_login(client):
    """
    Тест редиректа с страницы входа для уже авторизованного пользователя
    Проверяет что авторизованный пользователь автоматически перенаправляется на dashboard
    """
    # Входим в систему
    client.post('/login', data={
        'username': 'editor',
        'password': 'Password123'
    }, follow_redirects=True)

    # Пытаемся снова зайти на страницу логина
    response = client.get('/login', follow_redirects=False)

    assert response.status_code == 302
    assert '/dashboard' in response.location
