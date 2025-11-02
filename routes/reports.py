"""
Модуль отчётов с CSV экспортом
Содержит логику генерации отчётов по тренировкам и экспорт данных в CSV формат

ОТЧЁТ 1: "Объём тренировок за период"
Формула расчёта для каждой тренировки:
- Общее количество подходов = Σ(sets) всех упражнений в тренировке
- Общий вес = Σ(sets × reps × weight) всех упражнений
- Общее время = duration тренировки
CSV схема: Дата | Тип тренировки | Подходы | Повторы | Вес (кг) | Время (мин)

ОТЧЁТ 2: "Динамика личных рекордов"
Формула расчёта для каждого упражнения:
- Максимальный вес за 1 повтор (1RM) = max(weight) где reps = 1
- Максимальный объём = max(sets × reps × weight)
- Прогресс = ((последний_макс - первый_макс) / первый_макс) × 100%
CSV схема: Упражнение | Первая тренировка | Последняя тренировка | Макс вес (кг) | Прогресс (%)
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from flask_login import login_required, current_user
from models import db, Workout, WorkoutExercise, Exercise
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import csv
import io

# Создание Blueprint для модуля отчётов
reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    """
    Главная страница отчётов
    Отображает список доступных отчётов
    """
    return render_template('reports/index.html')


@reports_bp.route('/volume', methods=['GET'])
@login_required
def volume():
    """
    ОТЧЁТ 1: Объём тренировок за период

    Формулы расчёта:
    - Общее количество подходов = Σ(sets) для всех упражнений в тренировке
    - Общее количество повторов = Σ(reps × sets) для всех упражнений
    - Общий вес = Σ(sets × reps × weight) для всех упражнений
    - Общее время = workout.duration (в минутах)

    Фильтры:
    - date_from: дата начала периода (по умолчанию: 30 дней назад)
    - date_to: дата конца периода (по умолчанию: сегодня)
    - export: формат экспорта ('csv' для экспорта в CSV)

    CSV формат:
    Колонки: Дата, Тип тренировки, Подходы, Повторы, Вес (кг), Время (мин)
    Кодировка: UTF-8 с BOM для корректного отображения в Excel
    """
    # Получение параметров фильтрации из запроса
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    export_format = request.args.get('export')

    # Установка значений по умолчанию если параметры не переданы
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    # Парсинг дат для запроса к базе данных
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        flash('Неверный формат даты. Используйте формат ГГГГ-ММ-ДД', 'danger')
        return redirect(url_for('reports.volume'))

    # Запрос тренировок пользователя за указанный период
    workouts = Workout.query.filter(
        and_(
            Workout.owner_id == current_user.id,
            Workout.date >= date_from_obj,
            Workout.date <= date_to_obj
        )
    ).order_by(Workout.date.desc()).all()

    # Расчёт объёма для каждой тренировки
    # Формулы применяются к каждому упражнению в тренировке
    report_data = []
    for workout in workouts:
        # Инициализация переменных для расчёта
        total_sets = 0      # Общее количество подходов
        total_reps = 0      # Общее количество повторений
        total_weight = 0.0  # Общий вес (sets × reps × weight)

        # Перебор всех упражнений в тренировке для расчёта показателей
        for we in workout.workout_exercises:
            # Формула 1: Σ(sets) - суммируем количество подходов
            total_sets += we.sets if we.sets else 0

            # Формула 2: Σ(sets × reps) - суммируем общее количество повторений
            total_reps += (we.sets if we.sets else 0) * (we.reps if we.reps else 0)

            # Формула 3: Σ(sets × reps × weight) - суммируем общий поднятый вес
            if we.weight:
                total_weight += (we.sets if we.sets else 0) * (we.reps if we.reps else 0) * we.weight

        # Формула 4: duration тренировки (уже в минутах)
        total_duration = workout.duration if workout.duration else 0

        # Добавление рассчитанных данных в отчёт
        report_data.append({
            'date': workout.date,
            'workout_type': workout.workout_type,
            'sets': total_sets,
            'reps': total_reps,
            'weight': round(total_weight, 2),  # Округление до 2 знаков
            'duration': total_duration
        })

    # Экспорт в CSV если запрошен
    if export_format == 'csv':
        # Создание CSV файла в памяти с кодировкой UTF-8 BOM
        # BOM (Byte Order Mark) необходим для корректного отображения кириллицы в Excel
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM для Excel

        # Создание CSV writer с разделителем точка с запятой (для Excel)
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Заголовки CSV согласно схеме отчёта
        writer.writerow(['Дата', 'Тип тренировки', 'Подходы', 'Повторы', 'Вес (кг)', 'Время (мин)'])

        # Запись данных в CSV
        for row in report_data:
            writer.writerow([
                row['date'].strftime('%d.%m.%Y'),  # Дата в формате ДД.ММ.ГГГГ
                row['workout_type'],                # Тип тренировки
                row['sets'],                        # Общее количество подходов
                row['reps'],                        # Общее количество повторений
                row['weight'],                      # Общий вес в кг
                row['duration']                     # Время в минутах
            ])

        # Формирование HTTP ответа с CSV файлом
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=workout_volume_{date_from}_{date_to}.csv'
        return response

    # Отображение HTML страницы с отчётом
    return render_template('reports/volume.html',
                         report_data=report_data,
                         date_from=date_from,
                         date_to=date_to)


@reports_bp.route('/records', methods=['GET'])
@login_required
def records():
    """
    ОТЧЁТ 2: Динамика личных рекордов

    Формулы расчёта для каждого упражнения:
    - Максимальный вес за 1 повтор (1RM) = max(weight)
    - Максимальный объём = max(sets × reps × weight)
    - Прогресс = ((текущий_макс - первый_макс) / первый_макс) × 100%

    Фильтры:
    - exercise_id: ID упражнения для фильтрации (опционально)
    - export: формат экспорта ('csv' для экспорта в CSV)

    CSV формат:
    Колонки: Упражнение, Первая тренировка, Последняя тренировка, Макс вес (кг), Прогресс (%)
    Кодировка: UTF-8 с BOM для корректного отображения в Excel
    """
    # Получение параметров фильтрации
    exercise_id = request.args.get('exercise_id', type=int)
    export_format = request.args.get('export')

    # Базовый запрос: все упражнения пользователя из тренировок
    query = db.session.query(
        Exercise.id,
        Exercise.name,
        func.min(Workout.date).label('first_workout'),    # Дата первой тренировки
        func.max(Workout.date).label('last_workout')      # Дата последней тренировки
    ).join(
        WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id
    ).join(
        Workout, WorkoutExercise.workout_id == Workout.id
    ).filter(
        Workout.owner_id == current_user.id
    )

    # Применение фильтра по упражнению если указан
    if exercise_id:
        query = query.filter(Exercise.id == exercise_id)

    # Группировка по упражнениям
    query = query.group_by(Exercise.id, Exercise.name)
    exercises_data = query.all()

    # Расчёт личных рекордов для каждого упражнения
    report_data = []
    for ex_id, ex_name, first_date, last_date in exercises_data:
        # Получение всех записей упражнения для расчёта максимумов
        workout_exercises = db.session.query(WorkoutExercise).join(
            Workout, WorkoutExercise.workout_id == Workout.id
        ).filter(
            and_(
                WorkoutExercise.exercise_id == ex_id,
                Workout.owner_id == current_user.id
            )
        ).order_by(Workout.date).all()

        if not workout_exercises:
            continue

        # Формула 1: Максимальный вес за 1 повтор (1RM)
        # 1RM = max(weight) среди всех подходов упражнения
        max_weight = max(
            (we.weight if we.weight else 0 for we in workout_exercises),
            default=0
        )

        # Формула 2: Максимальный объём = max(sets × reps × weight)
        # Находим максимальный объём среди всех выполнений упражнения
        max_volume = max(
            ((we.sets if we.sets else 0) * (we.reps if we.reps else 0) * (we.weight if we.weight else 0)
             for we in workout_exercises),
            default=0
        )

        # Формула 3: Расчёт прогресса
        # Прогресс = ((последний_макс - первый_макс) / первый_макс) × 100%
        # Сравниваем максимальные веса в первой и последней тренировках

        # Получение первой тренировки с данным упражнением
        first_workout_exercises = [we for we in workout_exercises
                                  if db.session.query(Workout).get(we.workout_id).date == first_date]
        first_max_weight = max(
            (we.weight if we.weight else 0 for we in first_workout_exercises),
            default=0
        ) if first_workout_exercises else 0

        # Получение последней тренировки с данным упражнением
        last_workout_exercises = [we for we in workout_exercises
                                 if db.session.query(Workout).get(we.workout_id).date == last_date]
        last_max_weight = max(
            (we.weight if we.weight else 0 for we in last_workout_exercises),
            default=0
        ) if last_workout_exercises else 0

        # Расчёт процента прогресса
        # Если первый вес = 0, прогресс не может быть рассчитан
        if first_max_weight > 0:
            progress = ((last_max_weight - first_max_weight) / first_max_weight) * 100
        else:
            progress = 0

        # Добавление рассчитанных данных в отчёт
        report_data.append({
            'exercise_id': ex_id,
            'exercise_name': ex_name,
            'first_workout': first_date,
            'last_workout': last_date,
            'max_weight': round(max_weight, 2),      # Максимальный вес
            'max_volume': round(max_volume, 2),      # Максимальный объём
            'progress': round(progress, 2)            # Прогресс в процентах
        })

    # Экспорт в CSV если запрошен
    if export_format == 'csv':
        # Создание CSV файла в памяти с кодировкой UTF-8 BOM
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM для Excel

        # Создание CSV writer с разделителем точка с запятой
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Заголовки CSV согласно схеме отчёта
        writer.writerow(['Упражнение', 'Первая тренировка', 'Последняя тренировка',
                        'Макс вес (кг)', 'Макс объём (кг)', 'Прогресс (%)'])

        # Запись данных в CSV
        for row in report_data:
            writer.writerow([
                row['exercise_name'],                               # Название упражнения
                row['first_workout'].strftime('%d.%m.%Y'),         # Первая тренировка
                row['last_workout'].strftime('%d.%m.%Y'),          # Последняя тренировка
                row['max_weight'],                                  # Максимальный вес
                row['progress']                                     # Прогресс в процентах
            ])

        # Формирование HTTP ответа с CSV файлом
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=personal_records_{datetime.now().strftime("%Y%m%d")}.csv'
        return response

    # Получение списка всех упражнений пользователя для фильтра
    all_exercises = db.session.query(Exercise).join(
        WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id
    ).join(
        Workout, WorkoutExercise.workout_id == Workout.id
    ).filter(
        Workout.owner_id == current_user.id
    ).distinct().order_by(Exercise.name).all()

    # Отображение HTML страницы с отчётом
    return render_template('reports/records.html',
                         report_data=report_data,
                         all_exercises=all_exercises,
                         selected_exercise_id=exercise_id)
