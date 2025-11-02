"""
Модуль отчётов с экспортом в CSV формат
Данный модуль предоставляет обширный функционал для формирования различных отчётов
по тренировочной деятельности пользователей системы с возможностью экспорта данных
в формат CSV для последующей обработки и анализа в офисных приложениях

ОТЧЁТ 1: "Объём тренировок за период"
Данный отчёт позволяет получить развёрнутую информацию об общем объёме тренировочной нагрузки
Формулы расчёта агрегированных показателей по типам тренировок:
- total_workouts = COUNT(workouts) - общее количество тренировок данного типа
- total_duration = SUM(duration) - суммарная продолжительность всех тренировок в минутах
- total_exercises = SUM(workout_exercises.sets * reps) - общее количество выполненных упражнений
- total_weight = SUM(workout_exercises.sets * reps * weight) - суммарный поднятый вес в килограммах
CSV схема: Тип тренировки | Количество тренировок | Общее время (мин) | Всего упражнений | Общий вес (кг)

ОТЧЁТ 2: "Динамика личных рекордов"
Данный отчёт предназначен для отслеживания динамики улучшения показателей по каждому упражнению
Формулы расчёта максимальных показателей:
- max_weight = MAX(weight) WHERE exercise_id = X AND date BETWEEN from AND to - максимальный рабочий вес
- max_reps = MAX(reps) WHERE weight = max_weight - максимальное количество повторений с максимальным весом
CSV схема: Дата | Упражнение | Макс вес (кг) | Подходы | Повторения
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

    Данный отчёт предоставляет детализированную информацию об объёме тренировочной нагрузки
    с агрегацией данных по типам тренировок для удобства анализа и планирования дальнейших занятий

    Формулы расчёта агрегированных показателей:
    - total_workouts = COUNT(workouts) - общее количество тренировок данного типа за период
    - total_duration = SUM(duration) - суммарная продолжительность всех тренировок в минутах
    - total_exercises = SUM(workout_exercises.sets * reps) - общее количество выполненных упражнений
    - total_weight = SUM(workout_exercises.sets * reps * weight) - суммарный поднятый вес

    Параметры фильтрации:
    - date_from: дата начала периода анализа (по умолчанию: 30 дней назад от текущей даты)
    - date_to: дата окончания периода анализа (по умолчанию: текущая дата)

    Формат CSV экспорта:
    Колонки: Тип тренировки, Количество тренировок, Общее время (мин), Всего упражнений, Общий вес (кг)
    Кодировка: UTF-8 с BOM для корректного отображения кириллицы в Microsoft Excel
    Разделитель: точка с запятой для совместимости с русской локалью
    """
    # Получение параметров фильтрации из HTTP запроса
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Установка значений по умолчанию для параметров если они не были переданы пользователем
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    # Преобразование строковых представлений дат в объекты date для корректной работы с БД
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        flash('Произошла ошибка при обработке введённых дат. Пожалуйста, убедитесь что вы используете правильный формат даты ГГГГ-ММ-ДД', 'danger')
        return redirect(url_for('reports.volume'))

    # Выполнение запроса к базе данных для получения всех тренировок пользователя за указанный период
    workouts = Workout.query.filter(
        and_(
            Workout.owner_id == current_user.id,
            Workout.date >= date_from_obj,
            Workout.date <= date_to_obj
        )
    ).all()

    # Группировка данных по типам тренировок для формирования агрегированного отчёта
    # Используем словарь для накопления показателей по каждому типу тренировки
    workout_types_data = {}

    # Итерация по всем тренировкам для расчёта агрегированных показателей
    for workout in workouts:
        workout_type = workout.workout_type

        # Инициализация структуры данных для нового типа тренировки если он встретился впервые
        if workout_type not in workout_types_data:
            workout_types_data[workout_type] = {
                'workout_type': workout_type,
                'total_workouts': 0,      # Счётчик количества тренировок
                'total_duration': 0,      # Суммарная продолжительность
                'total_exercises': 0,     # Суммарное количество выполненных упражнений
                'total_weight': 0.0       # Суммарный поднятый вес
            }

        # Формула 1: COUNT(workouts) - увеличиваем счётчик тренировок данного типа
        workout_types_data[workout_type]['total_workouts'] += 1

        # Формула 2: SUM(duration) - добавляем продолжительность текущей тренировки к общей сумме
        if workout.duration:
            workout_types_data[workout_type]['total_duration'] += workout.duration

        # Обработка всех упражнений в рамках текущей тренировки для расчёта детализированных показателей
        for we in workout.workout_exercises:
            # Формула 3: SUM(sets × reps) - подсчёт общего количества выполненных упражнений
            sets = we.sets if we.sets else 0
            reps = we.reps if we.reps else 0
            workout_types_data[workout_type]['total_exercises'] += sets * reps

            # Формула 4: SUM(sets × reps × weight) - подсчёт общего поднятого веса
            if we.weight:
                workout_types_data[workout_type]['total_weight'] += sets * reps * we.weight

    # Преобразование словаря в список для удобства отображения и сортировки данных
    report_data = []
    for data in workout_types_data.values():
        report_data.append({
            'workout_type': data['workout_type'],
            'total_workouts': data['total_workouts'],
            'total_duration': data['total_duration'],
            'total_exercises': data['total_exercises'],
            'total_weight': round(data['total_weight'], 2)  # Округление до двух знаков после запятой
        })

    # Сортировка отчёта по типу тренировки в алфавитном порядке для удобства восприятия
    report_data.sort(key=lambda x: x['workout_type'])

    # Отображение HTML страницы с результатами отчёта
    return render_template('reports/volume.html',
                         report_data=report_data,
                         date_from=date_from,
                         date_to=date_to)


@reports_bp.route('/volume/export', methods=['GET'])
@login_required
def volume_export():
    """
    Экспорт отчёта "Объём тренировок за период" в формат CSV

    Данная функция осуществляет формирование и выгрузку отчёта в формате CSV
    с использованием специальных настроек кодировки и форматирования для обеспечения
    корректного открытия файла в приложении Microsoft Excel
    """
    # Получение параметров фильтрации из HTTP запроса
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Установка значений по умолчанию для параметров если они не были переданы
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    # Преобразование строковых представлений дат в объекты date
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        flash('Произошла ошибка при обработке дат для экспорта', 'danger')
        return redirect(url_for('reports.volume'))

    # Получение данных тренировок (аналогично основной функции)
    workouts = Workout.query.filter(
        and_(
            Workout.owner_id == current_user.id,
            Workout.date >= date_from_obj,
            Workout.date <= date_to_obj
        )
    ).all()

    # Группировка по типам тренировок
    workout_types_data = {}
    for workout in workouts:
        workout_type = workout.workout_type
        if workout_type not in workout_types_data:
            workout_types_data[workout_type] = {
                'total_workouts': 0,
                'total_duration': 0,
                'total_exercises': 0,
                'total_weight': 0.0
            }

        workout_types_data[workout_type]['total_workouts'] += 1
        if workout.duration:
            workout_types_data[workout_type]['total_duration'] += workout.duration

        for we in workout.workout_exercises:
            sets = we.sets if we.sets else 0
            reps = we.reps if we.reps else 0
            workout_types_data[workout_type]['total_exercises'] += sets * reps
            if we.weight:
                workout_types_data[workout_type]['total_weight'] += sets * reps * we.weight

    # Создание CSV файла в памяти с использованием кодировки UTF-8 с BOM
    # BOM (Byte Order Mark) необходим для того чтобы Microsoft Excel правильно определил кодировку файла
    output = io.StringIO()
    output.write('\ufeff')  # Добавление UTF-8 BOM в начало файла

    # Инициализация CSV writer с разделителем "точка с запятой" для русской локали Excel
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Запись заголовков колонок согласно схеме отчёта
    writer.writerow(['Тип тренировки', 'Количество тренировок', 'Общее время (мин)', 'Всего упражнений', 'Общий вес (кг)'])

    # Запись строк данных в CSV файл
    for workout_type, data in sorted(workout_types_data.items()):
        writer.writerow([
            workout_type,                           # Тип тренировки
            data['total_workouts'],                 # Количество тренировок данного типа
            data['total_duration'],                 # Общая продолжительность в минутах
            data['total_exercises'],                # Общее количество упражнений
            round(data['total_weight'], 2)          # Общий вес с округлением
        ])

    # Формирование HTTP ответа с корректными заголовками для скачивания файла
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=workout_volume_{date_from}_{date_to}.csv'
    return response


@reports_bp.route('/records', methods=['GET'])
@login_required
def records():
    """
    ОТЧЁТ 2: Динамика личных рекордов

    Данный отчёт предназначен для детального отслеживания максимальных достижений пользователя
    по каждому выполняемому упражнению с возможностью анализа прогресса за выбранный период времени

    Формулы расчёта максимальных показателей для каждого упражнения:
    - max_weight = MAX(weight) WHERE exercise_id = X AND date BETWEEN from AND to - максимальный рабочий вес
    - max_reps = MAX(reps) WHERE weight = max_weight - максимальное количество повторений с максимальным весом

    Параметры фильтрации:
    - date_from: дата начала периода анализа (опционально, по умолчанию: 30 дней назад)
    - date_to: дата окончания периода анализа (опционально, по умолчанию: текущая дата)
    - exercise_id: идентификатор упражнения для отображения данных только по одному упражнению (опционально)

    Формат CSV экспорта:
    Колонки: Дата, Упражнение, Макс вес (кг), Подходы, Повторения
    Кодировка: UTF-8 с BOM для корректного отображения в Microsoft Excel
    Разделитель: точка с запятой для совместимости с русской локалью
    """
    # Получение параметров фильтрации из HTTP запроса
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    exercise_id = request.args.get('exercise_id', type=int)

    # Установка значений по умолчанию для параметров дат если они не были переданы пользователем
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    # Преобразование строковых представлений дат в объекты date для корректной работы с базой данных
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        flash('Произошла ошибка при обработке введённых дат. Пожалуйста, убедитесь что вы используете правильный формат даты ГГГГ-ММ-ДД', 'danger')
        return redirect(url_for('reports.records'))

    # Построение базового SQL запроса для получения данных о личных рекордах по упражнениям
    # Применяем фильтрацию по датам для получения рекордов только за указанный период
    base_query = db.session.query(WorkoutExercise, Workout, Exercise).join(
        Workout, WorkoutExercise.workout_id == Workout.id
    ).join(
        Exercise, WorkoutExercise.exercise_id == Exercise.id
    ).filter(
        and_(
            Workout.owner_id == current_user.id,
            Workout.date >= date_from_obj,
            Workout.date <= date_to_obj
        )
    )

    # Применение дополнительного фильтра по упражнению если он был указан пользователем
    if exercise_id:
        base_query = base_query.filter(Exercise.id == exercise_id)

    # Выполнение запроса и получение всех записей тренировок с упражнениями
    workout_exercises_data = base_query.all()

    # Группировка данных по упражнениям для подсчёта максимальных показателей
    # Используем словарь где ключ - это ID упражнения, значение - список всех выполнений
    exercises_records = {}
    for we, workout, exercise in workout_exercises_data:
        if exercise.id not in exercises_records:
            exercises_records[exercise.id] = {
                'exercise_name': exercise.name,
                'records': []  # Список всех выполнений упражнения
            }

        # Добавляем информацию о выполнении упражнения в список записей
        exercises_records[exercise.id]['records'].append({
            'date': workout.date,
            'weight': we.weight if we.weight else 0,
            'sets': we.sets if we.sets else 0,
            'reps': we.reps if we.reps else 0
        })

    # Формирование итогового отчёта с личными рекордами
    report_data = []
    for exercise_id, data in exercises_records.items():
        if not data['records']:
            continue

        # Формула 1: MAX(weight) - поиск максимального веса среди всех выполнений упражнения
        max_weight_record = max(data['records'], key=lambda x: x['weight'])

        # Формула 2: MAX(reps) WHERE weight = max_weight - поиск максимального количества повторений при максимальном весе
        max_weight = max_weight_record['weight']
        records_with_max_weight = [r for r in data['records'] if r['weight'] == max_weight]
        max_reps_record = max(records_with_max_weight, key=lambda x: x['reps']) if records_with_max_weight else max_weight_record

        # Добавление рассчитанных данных в отчёт
        report_data.append({
            'exercise_name': data['exercise_name'],
            'date': max_reps_record['date'],
            'max_weight': round(max_weight, 2),
            'sets': max_reps_record['sets'],
            'reps': max_reps_record['reps']
        })

    # Сортировка отчёта по дате в обратном порядке (новые записи первыми)
    report_data.sort(key=lambda x: x['date'], reverse=True)

    # Получение списка всех упражнений пользователя для выпадающего списка фильтров
    all_exercises = db.session.query(Exercise).join(
        WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id
    ).join(
        Workout, WorkoutExercise.workout_id == Workout.id
    ).filter(
        Workout.owner_id == current_user.id
    ).distinct().order_by(Exercise.name).all()

    # Отображение HTML страницы с результатами отчёта
    return render_template('reports/records.html',
                         report_data=report_data,
                         all_exercises=all_exercises,
                         selected_exercise_id=exercise_id,
                         date_from=date_from,
                         date_to=date_to)


@reports_bp.route('/records/export', methods=['GET'])
@login_required
def records_export():
    """
    Экспорт отчёта "Динамика личных рекордов" в формат CSV

    Данная функция осуществляет формирование и выгрузку отчёта о личных рекордах в формате CSV
    с использованием специальных настроек кодировки и форматирования для обеспечения
    корректного открытия файла в приложении Microsoft Excel
    """
    # Получение параметров фильтрации из HTTP запроса
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    exercise_id = request.args.get('exercise_id', type=int)

    # Установка значений по умолчанию для параметров если они не были переданы
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    # Преобразование строковых представлений дат в объекты date
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        flash('Произошла ошибка при обработке дат для экспорта', 'danger')
        return redirect(url_for('reports.records'))

    # Получение данных (аналогично основной функции)
    base_query = db.session.query(WorkoutExercise, Workout, Exercise).join(
        Workout, WorkoutExercise.workout_id == Workout.id
    ).join(
        Exercise, WorkoutExercise.exercise_id == Exercise.id
    ).filter(
        and_(
            Workout.owner_id == current_user.id,
            Workout.date >= date_from_obj,
            Workout.date <= date_to_obj
        )
    )

    if exercise_id:
        base_query = base_query.filter(Exercise.id == exercise_id)

    workout_exercises_data = base_query.all()

    # Группировка и расчёт рекордов
    exercises_records = {}
    for we, workout, exercise in workout_exercises_data:
        if exercise.id not in exercises_records:
            exercises_records[exercise.id] = {
                'exercise_name': exercise.name,
                'records': []
            }

        exercises_records[exercise.id]['records'].append({
            'date': workout.date,
            'weight': we.weight if we.weight else 0,
            'sets': we.sets if we.sets else 0,
            'reps': we.reps if we.reps else 0
        })

    # Формирование данных отчёта
    report_data = []
    for exercise_id, data in exercises_records.items():
        if not data['records']:
            continue

        max_weight_record = max(data['records'], key=lambda x: x['weight'])
        max_weight = max_weight_record['weight']
        records_with_max_weight = [r for r in data['records'] if r['weight'] == max_weight]
        max_reps_record = max(records_with_max_weight, key=lambda x: x['reps']) if records_with_max_weight else max_weight_record

        report_data.append({
            'exercise_name': data['exercise_name'],
            'date': max_reps_record['date'],
            'max_weight': round(max_weight, 2),
            'sets': max_reps_record['sets'],
            'reps': max_reps_record['reps']
        })

    report_data.sort(key=lambda x: x['date'], reverse=True)

    # Создание CSV файла в памяти с использованием кодировки UTF-8 с BOM
    # BOM (Byte Order Mark) необходим для того чтобы Microsoft Excel правильно определил кодировку файла
    output = io.StringIO()
    output.write('\ufeff')  # Добавление UTF-8 BOM в начало файла

    # Инициализация CSV writer с разделителем "точка с запятой" для русской локали Excel
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Запись заголовков колонок согласно схеме отчёта
    writer.writerow(['Дата', 'Упражнение', 'Макс вес (кг)', 'Подходы', 'Повторения'])

    # Запись строк данных в CSV файл
    for row in report_data:
        writer.writerow([
            row['date'].strftime('%d.%m.%Y'),      # Дата в формате ДД.ММ.ГГГГ
            row['exercise_name'],                   # Название упражнения
            row['max_weight'],                      # Максимальный вес в килограммах
            row['sets'],                            # Количество подходов
            row['reps']                             # Количество повторений
        ])

    # Формирование HTTP ответа с корректными заголовками для скачивания файла
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=personal_records_{date_from}_{date_to}.csv'
    return response
