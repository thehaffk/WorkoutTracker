"""
Blueprint для управления упражнениями
Данный модуль предоставляет функционал для просмотра списка упражнений
создания редактирования и удаления упражнений с учётом прав доступа пользователей
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import db, Exercise
from sqlalchemy import or_

exercises_bp = Blueprint('exercises', __name__, url_prefix='/exercises')


def role_required(*role_names):
    """
    Декоратор для проверки наличия необходимой роли у пользователя
    Используется для ограничения доступа к определённым функциям системы
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Необходимо выполнить вход в систему для доступа к данной функции', 'warning')
                return redirect(url_for('login'))
            if current_user.role.name not in role_names:
                flash('У вас недостаточно прав для выполнения данного действия в системе', 'danger')
                return redirect(url_for('exercises.list'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@exercises_bp.route('/')
@login_required
def list():
    """
    Список упражнений с возможностью фильтрации и поиска
    Поддерживает фильтры по группе мышц уровню сложности и поиск по названию
    Реализована пагинация для удобного просмотра большого количества упражнений
    """
    # Получение параметров фильтрации из запроса
    page = request.args.get('page', 1, type=int)
    per_page = 10

    search = request.args.get('search', '').strip()
    muscle_group = request.args.get('muscle_group', '').strip()
    difficulty = request.args.get('difficulty', '').strip()

    # Формирование запроса
    query = Exercise.query

    # Фильтр по доступности: публичные упражнения или созданные текущим пользователем
    query = query.filter(
        or_(
            Exercise.is_public == True,
            Exercise.owner_id == current_user.id
        )
    )

    # Применение фильтров
    if search:
        query = query.filter(Exercise.name.ilike(f'%{search}%'))

    if muscle_group:
        query = query.filter(Exercise.muscle_group == muscle_group)

    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)

    # Сортировка и пагинация
    query = query.order_by(Exercise.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Получение уникальных значений для фильтров
    muscle_groups = db.session.query(Exercise.muscle_group.distinct()).filter(
        or_(
            Exercise.is_public == True,
            Exercise.owner_id == current_user.id
        )
    ).all()
    muscle_groups = [mg[0] for mg in muscle_groups if mg[0]]

    difficulties = ['beginner', 'intermediate', 'advanced']

    return render_template('exercises/list.html',
                         exercises=pagination.items,
                         pagination=pagination,
                         search=search,
                         muscle_group=muscle_group,
                         difficulty=difficulty,
                         muscle_groups=muscle_groups,
                         difficulties=difficulties)


@exercises_bp.route('/<int:id>')
@login_required
def detail(id):
    """
    Просмотр детальной информации об упражнении
    Отображает полное описание упражнения включая группу мышц оборудование и уровень сложности
    """
    exercise = Exercise.query.get_or_404(id)

    # Проверка доступа: публичное или принадлежит пользователю
    if not exercise.is_public and exercise.owner_id != current_user.id:
        flash('У вас нет доступа к просмотру данного упражнения в системе', 'danger')
        return redirect(url_for('exercises.list'))

    return render_template('exercises/detail.html', exercise=exercise)


@exercises_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('editor', 'admin')
def create():
    """
    Создание нового упражнения
    Доступно только для пользователей с ролями editor и admin
    Позволяет добавить новое упражнение в систему с указанием всех необходимых параметров
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        muscle_group = request.form.get('muscle_group', '').strip()
        equipment = request.form.get('equipment', '').strip()
        difficulty = request.form.get('difficulty', '').strip()
        is_public = request.form.get('is_public') == 'on'

        # Валидация обязательных полей
        if not name:
            flash('Необходимо указать название упражнения для добавления его в систему', 'danger')
            return render_template('exercises/form.html',
                                 exercise=None,
                                 form_data=request.form)

        if not muscle_group:
            flash('Необходимо указать группу мышц для данного упражнения в системе', 'danger')
            return render_template('exercises/form.html',
                                 exercise=None,
                                 form_data=request.form)

        if not difficulty:
            flash('Необходимо указать уровень сложности для данного упражнения в системе', 'danger')
            return render_template('exercises/form.html',
                                 exercise=None,
                                 form_data=request.form)

        # Создание нового упражнения
        exercise = Exercise(
            name=name,
            description=description,
            muscle_group=muscle_group,
            equipment=equipment,
            difficulty=difficulty,
            is_public=is_public,
            owner_id=current_user.id
        )

        db.session.add(exercise)
        db.session.commit()

        flash('Упражнение успешно добавлено в систему и доступно для использования в тренировках', 'success')
        return redirect(url_for('exercises.detail', id=exercise.id))

    return render_template('exercises/form.html', exercise=None)


@exercises_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('editor', 'admin')
def edit(id):
    """
    Редактирование существующего упражнения
    Доступно только для пользователей с ролями editor и admin
    Позволяет изменить параметры упражнения с сохранением изменений в базе данных
    """
    exercise = Exercise.query.get_or_404(id)

    # Проверка прав на редактирование
    if exercise.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас нет прав для редактирования данного упражнения в системе', 'danger')
        return redirect(url_for('exercises.detail', id=id))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        muscle_group = request.form.get('muscle_group', '').strip()
        equipment = request.form.get('equipment', '').strip()
        difficulty = request.form.get('difficulty', '').strip()
        is_public = request.form.get('is_public') == 'on'

        # Валидация обязательных полей
        if not name:
            flash('Необходимо указать название упражнения для сохранения изменений в системе', 'danger')
            return render_template('exercises/form.html',
                                 exercise=exercise,
                                 form_data=request.form)

        if not muscle_group:
            flash('Необходимо указать группу мышц для сохранения изменений в системе', 'danger')
            return render_template('exercises/form.html',
                                 exercise=exercise,
                                 form_data=request.form)

        if not difficulty:
            flash('Необходимо указать уровень сложности для сохранения изменений в системе', 'danger')
            return render_template('exercises/form.html',
                                 exercise=exercise,
                                 form_data=request.form)

        # Обновление данных упражнения
        exercise.name = name
        exercise.description = description
        exercise.muscle_group = muscle_group
        exercise.equipment = equipment
        exercise.difficulty = difficulty
        exercise.is_public = is_public

        db.session.commit()

        flash('Изменения в упражнении успешно сохранены и доступны для использования в системе', 'success')
        return redirect(url_for('exercises.detail', id=exercise.id))

    return render_template('exercises/form.html', exercise=exercise)


@exercises_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('editor', 'admin')
def delete(id):
    """
    Удаление упражнения из системы
    Доступно только для владельца упражнения или администратора системы
    Выполняет полное удаление упражнения из базы данных системы
    """
    exercise = Exercise.query.get_or_404(id)

    # Проверка прав на удаление: владелец или администратор
    if exercise.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас нет прав для удаления данного упражнения из системы учёта тренировок', 'danger')
        return redirect(url_for('exercises.detail', id=id))

    # Проверка наличия связанных тренировок
    if exercise.workout_exercises:
        flash('Невозможно удалить упражнение так как оно используется в тренировках пользователей системы', 'danger')
        return redirect(url_for('exercises.detail', id=id))

    db.session.delete(exercise)
    db.session.commit()

    flash('Упражнение успешно удалено из системы и больше не доступно для использования', 'success')
    return redirect(url_for('exercises.list'))
