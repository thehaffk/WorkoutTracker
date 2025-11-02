"""
Модуль для работы с файлами - загрузка, выгрузка и экспорт в ZIP
Содержит функции для управления файловыми вложениями к упражнениям и тренировкам

Разрешённые типы файлов: PNG, JPG, JPEG, PDF, TXT, CSV, JSON
Ограничения:
- Максимальный размер одного файла: 20 МБ
- Максимальный суммарный размер файлов на объект: 100 МБ

Структура ZIP-архива при экспорте тренировки:
workout_export_<id>_<timestamp>.zip
├── workout.json                    # JSON с данными тренировки
│   {
│       "id": <id>,
│       "date": "YYYY-MM-DD",
│       "workout_type": "Силовая/Кардио/Смешанная",
│       "duration": <minutes>,
│       "notes": "...",
│       "exercises": [
│           {
│               "exercise_id": <id>,
│               "name": "...",
│               "sets": <count>,
│               "reps": <count>,
│               "weight": <kg>,
│               "duration": <seconds>,
│               "distance": <km>,
│               "notes": "...",
│               "attachments": ["filename1.jpg", "filename2.pdf"]
│           }
│       ]
│   }
└── attachments/                    # Папка с файлами упражнений
    ├── <exercise_id>_<filename1>.jpg
    ├── <exercise_id>_<filename2>.pdf
    └── ...
"""

from flask import Blueprint, request, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Attachment, Exercise, Workout, WorkoutExercise
import os
import uuid
from datetime import datetime
import json
import zipfile
import io

# Создание Blueprint для работы с файлами
files_bp = Blueprint('files', __name__)

# Константы для валидации файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt', 'csv', 'json'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ в байтах
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100 МБ в байтах


# Регистрация функции форматирования размера файла как фильтра Jinja2
@files_bp.app_template_filter('filesize')
def filesize_filter(size_bytes):
    """
    Фильтр Jinja2 для форматирования размера файла

    Args:
        size_bytes: Размер файла в байтах

    Returns:
        Отформатированная строка с размером файла
    """
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"


def allowed_file(filename):
    """
    Проверка допустимости расширения файла

    Args:
        filename: Имя файла для проверки

    Returns:
        True если расширение разрешено, False в противном случае
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_total_size_for_exercise(exercise_id):
    """
    Вычисление суммарного размера всех файлов для упражнения

    Args:
        exercise_id: ID упражнения

    Returns:
        Суммарный размер всех файлов в байтах
    """
    attachments = Attachment.query.filter_by(exercise_id=exercise_id).all()
    return sum(att.file_size for att in attachments)


def generate_unique_filename(original_filename):
    """
    Генерация уникального имени файла с сохранением расширения

    Args:
        original_filename: Оригинальное имя файла

    Returns:
        Уникальное имя файла в формате: <uuid>_<secure_filename>.<ext>
    """
    # Безопасное имя файла
    safe_filename = secure_filename(original_filename)

    # Разделение на имя и расширение
    name, ext = os.path.splitext(safe_filename)

    # Генерация UUID и создание уникального имени
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    return f"{unique_id}_{timestamp}{ext}"


def format_file_size(size_bytes):
    """
    Форматирование размера файла в человекочитаемый вид для отображения пользователю

    Преобразует размер файла из байтов в более понятные единицы измерения
    такие как байты килобайты или мегабайты для удобного восприятия информации

    Args:
        size_bytes: Размер файла в байтах

    Returns:
        Отформатированная строка с размером файла и единицей измерения
    """
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"


@files_bp.route('/exercises/<int:exercise_id>/upload', methods=['POST'])
@login_required
def upload_file(exercise_id):
    """
    Загрузка файла к упражнению

    Выполняет следующие проверки на корректность загружаемых данных:
    1. Наличие файла в запросе от пользователя
    2. Корректность имени файла и его соответствие требованиям системы
    3. Разрешённый тип файла согласно политике безопасности (png, jpg, jpeg, pdf, txt, csv, json)
    4. Размер файла не превышает максимально допустимое значение в 20 МБ
    5. Суммарный размер всех файлов прикреплённых к упражнению не превышает лимит в 100 МБ
    6. Существование упражнения в базе данных системы
    7. Наличие прав доступа у пользователя для загрузки файлов (только владелец или администратор)

    Args:
        exercise_id: ID упражнения для прикрепления файла

    Returns:
        Редирект на страницу детального просмотра упражнения с сообщением об успехе или ошибке операции
    """
    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        flash('Не удалось обнаружить файл в запросе для загрузки в систему. Пожалуйста убедитесь что вы выбрали файл перед отправкой формы', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    file = request.files['file']

    # Проверка что файл был выбран пользователем
    if file.filename == '':
        flash('Вы не выбрали файл для загрузки в систему. Пожалуйста выберите файл который необходимо прикрепить к упражнению', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Проверка существования упражнения
    exercise = Exercise.query.get_or_404(exercise_id)

    # Проверка прав доступа - только владелец упражнения или администратор системы
    if not exercise.is_public and exercise.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас недостаточно прав для загрузки файлов к данному упражнению в системе', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Проверка типа файла на соответствие разрешённым форматам
    if not allowed_file(file.filename):
        flash(f'К сожалению данный тип файла не поддерживается системой для загрузки. Пожалуйста используйте файлы следующих форматов: {", ".join(ALLOWED_EXTENSIONS).upper()}', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Проверка размера загружаемого файла
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE // 1024 // 1024
        file_size_mb = file_size / 1024 / 1024
        flash(f'Размер загружаемого файла слишком велик для обработки системой. Размер вашего файла составляет {file_size_mb:.1f} МБ, в то время как максимально допустимый размер одного файла ограничен {max_size_mb} МБ. Пожалуйста выберите файл меньшего размера для загрузки', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Проверка суммарного размера всех файлов упражнения
    current_total_size = get_total_size_for_exercise(exercise_id)
    if current_total_size + file_size > MAX_TOTAL_SIZE:
        max_total_mb = MAX_TOTAL_SIZE // 1024 // 1024
        current_total_mb = current_total_size / 1024 / 1024
        remaining_mb = (MAX_TOTAL_SIZE - current_total_size) / 1024 / 1024
        flash(f'Суммарный размер всех файлов прикреплённых к данному упражнению превышает допустимый лимит системы. В настоящий момент к упражнению уже прикреплено {current_total_mb:.1f} МБ файлов, а максимально допустимый суммарный размер составляет {max_total_mb} МБ. У вас осталось всего {remaining_mb:.1f} МБ свободного места. Пожалуйста удалите некоторые из существующих файлов перед загрузкой новых', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Генерация уникального имени файла для предотвращения конфликтов
    unique_filename = generate_unique_filename(file.filename)

    # Создание директории для загрузок если её ещё нет в системе
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    # Сохранение файла на диск сервера
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Создание записи о файле в базе данных системы
    attachment = Attachment(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        exercise_id=exercise_id,
        owner_id=current_user.id
    )

    db.session.add(attachment)
    db.session.commit()

    flash(f'Файл "{file.filename}" был успешно загружен и прикреплён к упражнению в системе', 'success')
    return redirect(url_for('exercises.detail', id=exercise_id))


@files_bp.route('/files/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete_file(attachment_id):
    """
    Удаление файла из системы

    Позволяет владельцу файла или администратору системы удалить прикреплённый файл
    с физическим удалением файла с диска сервера и удалением соответствующей записи
    из базы данных системы учёта тренировок

    Args:
        attachment_id: ID файла для удаления из системы

    Returns:
        Редирект на страницу детального просмотра упражнения с сообщением о результате операции
    """
    attachment = Attachment.query.get_or_404(attachment_id)

    # Проверка прав доступа на удаление файла
    if attachment.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас недостаточно прав для удаления данного файла из системы. Удалять файлы могут только их владельцы или администраторы системы', 'danger')
        return redirect(url_for('dashboard'))

    exercise_id = attachment.exercise_id

    # Удаление физического файла с диска сервера
    try:
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
    except Exception as e:
        current_app.logger.error(f'Произошла ошибка при попытке удаления физического файла {attachment.file_path}: {str(e)}')
        flash(f'Произошла техническая ошибка при попытке удаления физического файла с диска сервера однако запись в базе данных будет удалена', 'warning')

    # Удаление записи из базы данных системы
    db.session.delete(attachment)
    db.session.commit()

    flash(f'Файл "{attachment.original_filename}" был успешно удалён из системы учёта тренировок', 'success')
    return redirect(url_for('exercises.detail', id=exercise_id))


@files_bp.route('/exercises/<int:exercise_id>/files', methods=['GET'])
@login_required
def get_exercise_files(exercise_id):
    """
    Получение списка файлов для упражнения

    Args:
        exercise_id: ID упражнения

    Returns:
        JSON со списком файлов
    """
    exercise = Exercise.query.get_or_404(exercise_id)

    # Проверка доступа
    if not exercise.is_public and exercise.owner_id != current_user.id:
        flash('У вас нет доступа к данному упражнению для просмотра файлов в системе', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    attachments = Attachment.query.filter_by(exercise_id=exercise_id).all()

    return redirect(url_for('exercises.detail', id=exercise_id))


@files_bp.route('/exercises/<int:exercise_id>/export', methods=['GET'])
@login_required
def export_exercise(exercise_id):
    """
    Экспорт упражнения в ZIP архив

    Создаёт ZIP архив содержащий JSON файл с метаданными упражнения
    а также папку со всеми прикреплёнными к упражнению файлами
    Предоставляет пользователю возможность полного экспорта данных упражнения
    из системы для резервного копирования или переноса данных на другое устройство

    Структура ZIP-архива:
    exercise_<id>.zip/
    ├── exercise.json  (id, name, description, muscle_group, equipment, difficulty)
    └── attachments/
        ├── file1.png
        ├── file2.pdf
        └── ...

    Args:
        exercise_id: ID упражнения для экспорта

    Returns:
        ZIP-файл для скачивания с данными упражнения и всеми прикреплёнными файлами
    """
    exercise = Exercise.query.get_or_404(exercise_id)

    # Проверка доступа к упражнению
    if not exercise.is_public and exercise.owner_id != current_user.id:
        flash('У вас нет доступа к данному упражнению для экспорта его данных из системы', 'danger')
        return redirect(url_for('exercises.detail', id=exercise_id))

    # Создание ZIP архива в памяти
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Создание JSON с данными упражнения
        exercise_data = {
            'id': exercise.id,
            'name': exercise.name,
            'description': exercise.description,
            'muscle_group': exercise.muscle_group,
            'equipment': exercise.equipment,
            'difficulty': exercise.difficulty,
            'is_public': exercise.is_public,
            'created_at': exercise.created_at.strftime('%Y-%m-%d %H:%M:%S') if exercise.created_at else None,
            'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'exported_by': current_user.username
        }

        # Добавление exercise.json в корень архива
        json_content = json.dumps(exercise_data, ensure_ascii=False, indent=2)
        zip_file.writestr('exercise.json', json_content)

        # Добавление прикреплённых файлов
        attachments = Attachment.query.filter_by(exercise_id=exercise_id).all()

        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment.file_path):
                    # Добавление файла в папку attachments с оригинальным именем
                    arcname = os.path.join('attachments', attachment.original_filename)
                    zip_file.write(attachment.file_path, arcname)

    # Подготовка буфера для отправки
    zip_buffer.seek(0)

    # Формирование имени файла для скачивания
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"exercise_{exercise_id}_{timestamp}.zip"

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename
    )


@files_bp.route('/workouts/<int:workout_id>/export_zip')
@login_required
def export_zip(workout_id):
    """
    Экспорт тренировки в ZIP-архив

    Создаёт ZIP-архив со следующей структурой:
    workout_export_<id>_<timestamp>.zip
    ├── workout.json                    # JSON с полными данными тренировки
    │   {
    │       "id": <id тренировки>,
    │       "date": "YYYY-MM-DD",
    │       "workout_type": "Силовая/Кардио/Смешанная",
    │       "duration": <длительность в минутах>,
    │       "notes": "заметки о тренировке",
    │       "owner": {
    │           "id": <id пользователя>,
    │           "username": "имя пользователя"
    │       },
    │       "exercises": [
    │           {
    │               "exercise_id": <id упражнения>,
    │               "name": "название упражнения",
    │               "description": "описание",
    │               "muscle_group": "группа мышц",
    │               "equipment": "оборудование",
    │               "sets": <количество подходов>,
    │               "reps": <количество повторений>,
    │               "weight": <вес в кг>,
    │               "duration": <длительность в секундах>,
    │               "distance": <дистанция в км>,
    │               "notes": "заметки",
    │               "order": <порядковый номер>,
    │               "attachments": ["filename1.jpg", "filename2.pdf"]
    │           },
    │           ...
    │       ],
    │       "created_at": "YYYY-MM-DD HH:MM:SS",
    │       "total_exercises": <количество упражнений>
    │   }
    └── attachments/                    # Папка с файлами упражнений
        ├── <exercise_id>_<filename1>.jpg
        ├── <exercise_id>_<filename2>.pdf
        └── ...

    Args:
        workout_id: ID тренировки для экспорта

    Returns:
        ZIP-файл для скачивания
    """
    # Получение тренировки
    workout = Workout.query.get_or_404(workout_id)

    # Проверка прав доступа
    if workout.owner_id != current_user.id and not current_user.is_admin():
        flash('У вас недостаточно прав для экспорта этой тренировки', 'danger')
        return redirect(url_for('index'))

    # Формирование данных для JSON
    workout_data = {
        'id': workout.id,
        'date': workout.date.isoformat() if workout.date else None,
        'workout_type': workout.workout_type,
        'duration': workout.duration,
        'notes': workout.notes,
        'owner': {
            'id': workout.owner.id,
            'username': workout.owner.username
        },
        'exercises': [],
        'created_at': workout.created_at.isoformat() if workout.created_at else None,
        'total_exercises': len(workout.workout_exercises)
    }

    # Сбор информации об упражнениях
    for we in workout.workout_exercises:
        exercise = we.exercise

        # Получение файлов упражнения
        attachments = Attachment.query.filter_by(exercise_id=exercise.id).all()
        attachment_filenames = [att.original_filename for att in attachments]

        exercise_data = {
            'exercise_id': exercise.id,
            'name': exercise.name,
            'description': exercise.description,
            'muscle_group': exercise.muscle_group,
            'equipment': exercise.equipment,
            'sets': we.sets,
            'reps': we.reps,
            'weight': we.weight,
            'duration': we.duration,
            'distance': we.distance,
            'notes': we.notes,
            'order': we.order,
            'attachments': attachment_filenames
        }

        workout_data['exercises'].append(exercise_data)

    # Создание ZIP-архива в памяти
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Добавление workout.json
        workout_json = json.dumps(workout_data, ensure_ascii=False, indent=4)
        zip_file.writestr('workout.json', workout_json)

        # Добавление файлов упражнений
        for we in workout.workout_exercises:
            exercise = we.exercise
            attachments = Attachment.query.filter_by(exercise_id=exercise.id).all()

            for att in attachments:
                if os.path.exists(att.file_path):
                    # Путь в архиве: attachments/<exercise_id>_<filename>
                    archive_path = f'attachments/{exercise.id}_{att.original_filename}'
                    zip_file.write(att.file_path, archive_path)

    # Подготовка буфера для отправки
    zip_buffer.seek(0)

    # Формирование имени файла
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'workout_export_{workout.id}_{timestamp}.zip'

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )
