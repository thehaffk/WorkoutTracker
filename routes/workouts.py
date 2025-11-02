"""
Blueprint для управления тренировками
Реализует CRUD операции для работы с тренировками и упражнениями в тренировках
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Workout, WorkoutExercise, Exercise
from datetime import datetime, date
from functools import wraps

workouts_bp = Blueprint('workouts', __name__, url_prefix='/workouts')


def owner_or_admin_required(f):
    """
    Декоратор для проверки владельца тренировки или прав администратора
    Используется для ограничения доступа к редактированию и удалению тренировок
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        workout_id = kwargs.get('id')
        if workout_id:
            workout = Workout.query.get_or_404(workout_id)
            if workout.owner_id != current_user.id and not current_user.is_admin():
                flash('У вас нет прав для выполнения данного действия', 'danger')
                return redirect(url_for('workouts.list'))
        return f(*args, **kwargs)
    return decorated_function


@workouts_bp.route('/')
@login_required
def list():
    """
    Список тренировок с фильтрами и пагинацией
    Фильтры: дата (от/до), тип тренировки
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Получение параметров фильтрации
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    workout_type = request.args.get('workout_type', '')

    # Базовый запрос - показываем только тренировки текущего пользователя или все для админа
    if current_user.is_admin():
        query = Workout.query
    else:
        query = Workout.query.filter_by(owner_id=current_user.id)

    # Применение фильтров
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Workout.date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Workout.date <= date_to_obj)
        except ValueError:
            pass

    if workout_type:
        query = query.filter(Workout.workout_type == workout_type)

    # Сортировка по дате (сначала новые)
    query = query.order_by(Workout.date.desc(), Workout.created_at.desc())

    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    workouts = pagination.items

    # Список типов тренировок для фильтра
    workout_types = ['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная']

    return render_template('workouts/list.html',
                         workouts=workouts,
                         pagination=pagination,
                         date_from=date_from,
                         date_to=date_to,
                         workout_type=workout_type,
                         workout_types=workout_types)


@workouts_bp.route('/<int:id>')
@login_required
def view(id):
    """
    Просмотр детальной информации о тренировке с упражнениями
    """
    workout = Workout.query.get_or_404(id)

    # Проверка доступа - владелец или админ
    if workout.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас нет доступа к этой тренировке', 'danger')
        return redirect(url_for('workouts.list'))

    # Получение упражнений тренировки с информацией об упражнениях
    workout_exercises = WorkoutExercise.query.filter_by(workout_id=id).order_by(WorkoutExercise.order).all()

    # Получение доступных упражнений (публичные + собственные)
    available_exercises = Exercise.query.filter(
        db.or_(
            Exercise.is_public == True,
            Exercise.owner_id == current_user.id
        )
    ).order_by(Exercise.muscle_group, Exercise.name).all()

    return render_template('workouts/view.html',
                         workout=workout,
                         workout_exercises=workout_exercises,
                         available_exercises=available_exercises)


@workouts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """
    Создание новой тренировки
    Доступно всем авторизованным пользователям (включая viewer)
    """
    if request.method == 'POST':
        # Получение данных из формы
        workout_date = request.form.get('date')
        workout_type = request.form.get('workout_type')
        duration = request.form.get('duration')
        notes = request.form.get('notes', '')

        # Валидация
        if not workout_date or not workout_type:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return render_template('workouts/form.html',
                                 workout_types=['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная'])

        try:
            workout_date_obj = datetime.strptime(workout_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты', 'danger')
            return render_template('workouts/form.html',
                                 workout_types=['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная'])

        # Создание тренировки
        workout = Workout(
            date=workout_date_obj,
            workout_type=workout_type,
            duration=int(duration) if duration else None,
            notes=notes,
            owner_id=current_user.id
        )

        db.session.add(workout)
        db.session.commit()

        flash('Тренировка успешно создана', 'success')
        return redirect(url_for('workouts.view', id=workout.id))

    # GET запрос - отображение формы
    workout_types = ['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная']
    return render_template('workouts/form.html',
                         workout=None,
                         workout_types=workout_types,
                         today=date.today().isoformat())


@workouts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@owner_or_admin_required
def edit(id):
    """
    Редактирование тренировки
    Доступно только владельцу или администратору
    """
    workout = Workout.query.get_or_404(id)

    if request.method == 'POST':
        # Получение данных из формы
        workout_date = request.form.get('date')
        workout_type = request.form.get('workout_type')
        duration = request.form.get('duration')
        notes = request.form.get('notes', '')

        # Валидация
        if not workout_date or not workout_type:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return render_template('workouts/form.html',
                                 workout=workout,
                                 workout_types=['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная'])

        try:
            workout_date_obj = datetime.strptime(workout_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты', 'danger')
            return render_template('workouts/form.html',
                                 workout=workout,
                                 workout_types=['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная'])

        # Обновление тренировки
        workout.date = workout_date_obj
        workout.workout_type = workout_type
        workout.duration = int(duration) if duration else None
        workout.notes = notes

        db.session.commit()

        flash('Тренировка успешно обновлена', 'success')
        return redirect(url_for('workouts.view', id=workout.id))

    # GET запрос - отображение формы с данными
    workout_types = ['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная']
    return render_template('workouts/form.html',
                         workout=workout,
                         workout_types=workout_types)


@workouts_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@owner_or_admin_required
def delete(id):
    """
    Удаление тренировки
    Доступно только владельцу или администратору
    """
    workout = Workout.query.get_or_404(id)

    db.session.delete(workout)
    db.session.commit()

    flash('Тренировка успешно удалена', 'success')
    return redirect(url_for('workouts.list'))


@workouts_bp.route('/<int:id>/add_exercise', methods=['POST'])
@login_required
@owner_or_admin_required
def add_exercise(id):
    """
    Добавление упражнения в тренировку
    """
    workout = Workout.query.get_or_404(id)

    # Получение данных из формы
    exercise_id = request.form.get('exercise_id')
    sets = request.form.get('sets')
    reps = request.form.get('reps')
    weight = request.form.get('weight')
    duration = request.form.get('duration')
    distance = request.form.get('distance')
    notes = request.form.get('notes', '')

    # Валидация
    if not exercise_id:
        flash('Выберите упражнение', 'danger')
        return redirect(url_for('workouts.view', id=id))

    # Проверка существования упражнения и доступа к нему
    exercise = Exercise.query.get_or_404(exercise_id)
    if not exercise.is_public and exercise.owner_id != current_user.id:
        flash('У вас нет доступа к этому упражнению', 'danger')
        return redirect(url_for('workouts.view', id=id))

    # Получение максимального порядка для добавления в конец
    max_order = db.session.query(db.func.max(WorkoutExercise.order)).filter_by(workout_id=id).scalar() or 0

    # Создание связи
    workout_exercise = WorkoutExercise(
        workout_id=id,
        exercise_id=exercise_id,
        sets=int(sets) if sets else 1,
        reps=int(reps) if reps else 1,
        weight=float(weight) if weight else None,
        duration=int(duration) if duration else None,
        distance=float(distance) if distance else None,
        notes=notes,
        order=max_order + 1
    )

    db.session.add(workout_exercise)
    db.session.commit()

    flash('Упражнение успешно добавлено в тренировку', 'success')
    return redirect(url_for('workouts.view', id=id))


@workouts_bp.route('/<int:id>/exercises/<int:ex_id>/delete', methods=['POST'])
@login_required
@owner_or_admin_required
def delete_exercise(id, ex_id):
    """
    Удаление упражнения из тренировки
    """
    workout = Workout.query.get_or_404(id)
    workout_exercise = WorkoutExercise.query.get_or_404(ex_id)

    # Проверка что упражнение принадлежит этой тренировке
    if workout_exercise.workout_id != id:
        flash('Упражнение не найдено в этой тренировке', 'danger')
        return redirect(url_for('workouts.view', id=id))

    db.session.delete(workout_exercise)
    db.session.commit()

    flash('Упражнение удалено из тренировки', 'success')
    return redirect(url_for('workouts.view', id=id))
