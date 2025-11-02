"""
Модели базы данных для системы учёта тренировок
В данном файле представлены все основные модели данных приложения
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Role(db.Model):
    """
    Модель для хранения информации о ролях пользователей в системе
    Используется для разграничения прав доступа к различным функциям
    """
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    # Отношения с пользователями
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """
    Модель пользователя системы
    Содержит всю информацию о пользователе включая учётные данные и личные параметры
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Роль пользователя
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    # Персональные данные для расчёта нагрузки
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Integer)
    gender = db.Column(db.String(10))  # male, female, other

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    exercises = db.relationship('Exercise', backref='owner', lazy=True, cascade='all, delete-orphan')
    workouts = db.relationship('Workout', backref='owner', lazy=True, cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='owner', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Установить хэш пароля"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверить пароль"""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """Проверить наличие роли"""
        return self.role.name == role_name

    def can_edit(self):
        """Может ли пользователь редактировать данные"""
        return self.role.name in ['editor', 'admin']

    def is_admin(self):
        """Является ли пользователь администратором"""
        return self.role.name == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Exercise(db.Model):
    """
    Модель упражнения
    Хранит информацию об упражнениях - как публичных так и личных
    """
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    muscle_group = db.Column(db.String(50), nullable=False, index=True)  # Грудь, Спина, Ноги и т.д.
    equipment = db.Column(db.String(50))  # Штанга, гантели, тренажёр, без оборудования
    difficulty = db.Column(db.String(20))  # beginner, intermediate, advanced

    # Флаг публичности
    is_public = db.Column(db.Boolean, default=False)

    # Владелец (NULL для публичных упражнений)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    workout_exercises = db.relationship('WorkoutExercise', backref='exercise', lazy=True, cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='exercise', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Exercise {self.name}>'


class Workout(db.Model):
    """
    Модель тренировки
    Содержит общую информацию о тренировке и её результаты
    """
    __tablename__ = 'workouts'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    workout_type = db.Column(db.String(50), nullable=False)  # Силовая, Кардио, Смешанная
    duration = db.Column(db.Integer)  # Длительность в минутах
    notes = db.Column(db.Text)

    # Владелец тренировки
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    workout_exercises = db.relationship('WorkoutExercise', backref='workout', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Workout {self.date} - {self.workout_type}>'


class WorkoutExercise(db.Model):
    """
    Модель для связи тренировки и упражнения
    Хранит детали выполнения конкретного упражнения в рамках тренировки
    Включает подходы, повторения, вес и другие параметры
    """
    __tablename__ = 'workout_exercises'

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)

    # Детали выполнения
    sets = db.Column(db.Integer, nullable=False, default=1)  # Количество подходов
    reps = db.Column(db.Integer, nullable=False, default=1)  # Количество повторений
    weight = db.Column(db.Float)  # Вес в кг
    duration = db.Column(db.Integer)  # Длительность в секундах (для статических)
    distance = db.Column(db.Float)  # Дистанция в км (для кардио)

    notes = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)  # Порядок в тренировке

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WorkoutExercise W:{self.workout_id} E:{self.exercise_id}>'


class Attachment(db.Model):
    """
    Модель для хранения файловых вложений
    Поддерживает различные типы файлов с валидацией размера и типа
    Разрешённые типы файлов: PNG, JPEG, PDF, TXT, CSV, JSON
    Максимальный размер файла: 20 МБ
    Максимальный суммарный размер на объект: 100 МБ
    """
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Размер в байтах
    mime_type = db.Column(db.String(100))

    # Привязка к сущностям
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Attachment {self.original_filename}>'
