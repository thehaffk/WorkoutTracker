"""
Главный файл приложения для системы учёта и управления тренировками
Данное приложение предназначено для ведения записей о тренировках пользователей,
управления упражнениями, формирования отчётов и анализа результатов занятий
"""
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from config import Config
from models import db, User, Role
import os

# Инициализация приложения Flask
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация базы данных
db.init_app(app)

# Инициализация Flask-Login для управления сессиями пользователей
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к данной странице необходимо выполнить вход в систему'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """
    Функция загрузки пользователя для Flask-Login
    Используется для получения объекта пользователя из базы данных по его идентификатору
    """
    return User.query.get(int(user_id))


def role_required(*role_names):
    """
    Декоратор для проверки наличия необходимой роли у пользователя
    Используется для ограничения доступа к определённым функциям системы
    в зависимости от роли пользователя в системе
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Необходимо выполнить вход в систему для доступа к данной функции', 'warning')
                return redirect(url_for('login'))
            if current_user.role.name not in role_names:
                flash('У вас недостаточно прав для выполнения данного действия в системе', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/')
def index():
    """
    Главная страница приложения
    Отображает основную информацию о системе и перенаправляет пользователя
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Панель управления пользователя
    Отображает основную статистику и информацию о тренировках пользователя
    """
    return render_template('dashboard.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Страница входа в систему
    Обрабатывает процесс аутентификации пользователя в приложении
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Вы успешно вошли в систему учёта тренировок', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль. Пожалуйста, проверьте введённые данные и попробуйте снова', 'danger')

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Страница регистрации нового пользователя в системе
    Обрабатывает процесс создания новой учётной записи пользователя
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        from validators.password_validator import password_validator, validate_username, validate_email

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Валидация всех введённых пользователем данных
        error = validate_username(username)
        if error:
            flash(error, 'danger')
            return render_template('auth/register.html')

        error = validate_email(email)
        if error:
            flash(error, 'danger')
            return render_template('auth/register.html')

        error = password_validator(password)
        if error:
            flash(error, 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Введённые пароли не совпадают. Пожалуйста, убедитесь что вы ввели одинаковый пароль в обоих полях', 'danger')
            return render_template('auth/register.html')

        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует в системе. Пожалуйста, выберите другое имя пользователя', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже зарегистрирован в системе. Пожалуйста, используйте другой адрес электронной почты', 'danger')
            return render_template('auth/register.html')

        # Создание нового пользователя с ролью viewer по умолчанию
        viewer_role = Role.query.filter_by(name='viewer').first()
        new_user = User(username=username, email=email, role_id=viewer_role.id)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация прошла успешно! Теперь вы можете войти в систему используя свои учётные данные', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    """
    Выход пользователя из системы
    Завершает текущую сессию пользователя и очищает данные авторизации
    """
    logout_user()
    flash('Вы успешно вышли из системы учёта тренировок', 'info')
    return redirect(url_for('login'))


def init_db():
    """
    Инициализация базы данных
    Создаёт все необходимые таблицы и заполняет базовые данные (роли)
    """
    with app.app_context():
        db.create_all()

        # Создание ролей если их ещё нет в системе
        if Role.query.count() == 0:
            roles = [
                Role(name='viewer', description='Роль для просмотра данных без возможности редактирования'),
                Role(name='editor', description='Роль для редактирования данных в предметной области тренировок'),
                Role(name='admin', description='Административная роль с полным доступом ко всем функциям системы')
            ]
            for role in roles:
                db.session.add(role)
            db.session.commit()
            print('Роли успешно созданы в базе данных')

        # Создание тестового администратора если пользователей нет
        if User.query.count() == 0:
            admin_role = Role.query.filter_by(name='admin').first()
            admin = User(username='admin', email='admin@example.com', role_id=admin_role.id)
            admin.set_password('Admin123')
            db.session.add(admin)
            db.session.commit()
            print('Тестовый администратор создан: admin / Admin123')


if __name__ == '__main__':
    # Создание папки для загрузок если её нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Инициализация базы данных
    init_db()

    # Запуск приложения
    app.run(host='0.0.0.0', port=8080, debug=True)
