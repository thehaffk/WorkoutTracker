"""
Тесты для модуля работы с файлами
Проверяет загрузку выгрузку удаление файлов и экспорт в ZIP архив
"""
import pytest
from models import db, User, Exercise, Workout, WorkoutExercise, Attachment
import io
import os
import zipfile
import json


def test_upload_valid_file(auth_client, app, sample_exercise):
    """
    Тест загрузки валидного файла к упражнению
    Проверяет что система корректно принимает и сохраняет файл допустимого формата
    """
    # Создаём тестовый файл
    data = {
        'file': (io.BytesIO(b'test file content'), 'test.png')
    }

    response = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'успешно загружен' in response.get_data(as_text=True)

    # Проверка что файл добавлен в базу данных
    with app.app_context():
        attachment = Attachment.query.filter_by(exercise_id=sample_exercise).first()
        assert attachment is not None
        assert attachment.original_filename == 'test.png'


def test_upload_invalid_extension(auth_client, sample_exercise):
    """
    Тест загрузки файла с недопустимым расширением
    Проверяет что система отклоняет файлы неразрешённых типов
    """
    # Создаём файл с недопустимым расширением
    data = {
        'file': (io.BytesIO(b'test content'), 'test.exe')
    }

    response = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'тип файла не поддерживается' in response.get_data(as_text=True)


def test_upload_too_large(auth_client, sample_exercise):
    """
    Тест загрузки файла превышающего максимально допустимый размер
    Проверяет что система отклоняет слишком большие файлы
    """
    # Создаём файл размером больше 20 МБ
    large_content = b'x' * (21 * 1024 * 1024)  # 21 МБ
    data = {
        'file': (io.BytesIO(large_content), 'large_file.png')
    }

    response = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'Размер загружаемого файла слишком велик' in response.get_data(as_text=True)


def test_total_size_limit(auth_client, app, sample_exercise):
    """
    Тест проверки суммарного лимита размера файлов на объект
    Проверяет что система контролирует общий объём прикреплённых файлов
    """
    # Загружаем несколько файлов чтобы приблизиться к лимиту
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        # Создаём файл размером 80 МБ в базе данных
        attachment = Attachment(
            filename='existing_large.png',
            original_filename='existing_large.png',
            file_path='/tmp/existing_large.png',
            file_size=80 * 1024 * 1024,  # 80 МБ
            mime_type='image/png',
            exercise_id=sample_exercise,
            owner_id=editor.id
        )
        db.session.add(attachment)
        db.session.commit()

    # Пытаемся загрузить ещё один большой файл (25 МБ)
    # Это превысит лимит 100 МБ
    content = b'x' * (25 * 1024 * 1024)  # Изменено на 25 МБ чтобы превысить лимит
    data = {
        'file': (io.BytesIO(content), 'another_file.png')
    }

    response = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    # Должно быть сообщение о превышении лимита
    content_text = response.get_data(as_text=True)
    assert 'суммарный размер' in content_text.lower() or 'превышает' in content_text.lower()


def test_zip_export(auth_client, app, sample_workout):
    """
    Тест экспорта тренировки в ZIP архив
    Проверяет что система корректно создаёт ZIP файл с данными тренировки
    """
    response = auth_client.get(f'/workouts/{sample_workout}/export_zip')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/zip'
    assert 'attachment' in response.headers['Content-Disposition']


def test_zip_contains_json(auth_client, app, sample_workout):
    """
    Тест наличия workout.json в ZIP архиве
    Проверяет что ZIP архив содержит файл с метаданными тренировки в формате JSON
    """
    response = auth_client.get(f'/workouts/{sample_workout}/export_zip')

    # Читаем содержимое ZIP
    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, 'r') as zip_file:
        # Проверяем наличие workout.json
        assert 'workout.json' in zip_file.namelist()

        # Читаем и парсим JSON
        json_content = zip_file.read('workout.json').decode('utf-8')
        workout_data = json.loads(json_content)

        # Проверяем структуру JSON
        assert 'id' in workout_data
        assert 'date' in workout_data
        assert 'workout_type' in workout_data
        assert 'exercises' in workout_data
        assert isinstance(workout_data['exercises'], list)


def test_zip_contains_attachments(auth_client, app, sample_workout):
    """
    Тест наличия прикреплённых файлов в ZIP архиве
    Проверяет что все файлы упражнений включены в архив
    """
    # Добавляем файл к упражнению
    with app.app_context():
        workout = Workout.query.get(sample_workout)
        exercise_id = workout.workout_exercises[0].exercise_id
        editor = User.query.filter_by(username='editor').first()

        # Создаём временный файл
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        test_file_path = os.path.join(upload_folder, 'test_attachment.txt')

        with open(test_file_path, 'w') as f:
            f.write('Test attachment content')

        # Добавляем запись в БД
        attachment = Attachment(
            filename='test_attachment.txt',
            original_filename='test_attachment.txt',
            file_path=test_file_path,
            file_size=100,
            mime_type='text/plain',
            exercise_id=exercise_id,
            owner_id=editor.id
        )
        db.session.add(attachment)
        db.session.commit()

    # Экспортируем тренировку
    response = auth_client.get(f'/workouts/{sample_workout}/export_zip')

    # Проверяем ZIP архив
    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, 'r') as zip_file:
        # Проверяем наличие папки attachments
        attachment_files = [name for name in zip_file.namelist() if name.startswith('attachments/')]
        assert len(attachment_files) > 0


def test_delete_file(auth_client, app, sample_exercise):
    """
    Тест удаления прикреплённого файла
    Проверяет что пользователь может удалить свой файл из системы
    """
    # Создаём файл для удаления
    with app.app_context():
        editor = User.query.filter_by(username='editor').first()

        # Создаём временный файл
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        test_file_path = os.path.join(upload_folder, 'file_to_delete.txt')

        with open(test_file_path, 'w') as f:
            f.write('This file will be deleted')

        # Добавляем в БД
        attachment = Attachment(
            filename='file_to_delete.txt',
            original_filename='file_to_delete.txt',
            file_path=test_file_path,
            file_size=100,
            mime_type='text/plain',
            exercise_id=sample_exercise,
            owner_id=editor.id
        )
        db.session.add(attachment)
        db.session.commit()
        attachment_id = attachment.id

    # Удаляем файл
    response = auth_client.post(f'/files/{attachment_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'успешно удалён' in response.get_data(as_text=True)

    # Проверяем что файл удалён из БД
    with app.app_context():
        attachment = Attachment.query.get(attachment_id)
        assert attachment is None


def test_upload_without_file(auth_client, sample_exercise):
    """
    Тест попытки загрузки без выбора файла
    Проверяет что система корректно обрабатывает пустой запрос на загрузку
    """
    response = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data={},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'файл' in response.get_data(as_text=True).lower()


def test_exercise_export_to_zip(auth_client, app, sample_exercise):
    """
    Тест экспорта упражнения в ZIP архив
    Проверяет что можно экспортировать отдельное упражнение со всеми файлами
    """
    response = auth_client.get(f'/exercises/{sample_exercise}/export')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/zip'
    assert 'attachment' in response.headers['Content-Disposition']

    # Проверяем содержимое ZIP
    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, 'r') as zip_file:
        # Должен быть exercise.json
        assert 'exercise.json' in zip_file.namelist()

        # Проверяем JSON
        json_content = zip_file.read('exercise.json').decode('utf-8')
        exercise_data = json.loads(json_content)

        assert 'id' in exercise_data
        assert 'name' in exercise_data
        assert 'muscle_group' in exercise_data


def test_upload_multiple_files(auth_client, app, sample_exercise):
    """
    Тест загрузки нескольких файлов к одному упражнению
    Проверяет что можно прикрепить несколько файлов к одному упражнению
    """
    # Загружаем первый файл
    data1 = {
        'file': (io.BytesIO(b'first file'), 'file1.txt')
    }
    response1 = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data1,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response1.status_code == 200

    # Загружаем второй файл
    data2 = {
        'file': (io.BytesIO(b'second file'), 'file2.txt')
    }
    response2 = auth_client.post(
        f'/exercises/{sample_exercise}/upload',
        data=data2,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response2.status_code == 200

    # Проверяем что оба файла в БД
    with app.app_context():
        attachments = Attachment.query.filter_by(exercise_id=sample_exercise).all()
        assert len(attachments) >= 2


def test_upload_file_to_nonexistent_exercise(auth_client):
    """
    Тест загрузки файла к несуществующему упражнению
    Проверяет что система корректно обрабатывает ошибку 404
    """
    data = {
        'file': (io.BytesIO(b'test'), 'test.txt')
    }

    response = auth_client.post(
        '/exercises/99999/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=False
    )

    # Должна быть ошибка 404
    assert response.status_code == 404


def test_json_export_structure(auth_client, app, sample_workout):
    """
    Тест структуры JSON данных в экспортируемом архиве
    Проверяет что JSON содержит все необходимые поля с корректными данными
    """
    response = auth_client.get(f'/workouts/{sample_workout}/export_zip')

    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, 'r') as zip_file:
        json_content = zip_file.read('workout.json').decode('utf-8')
        workout_data = json.loads(json_content)

        # Проверяем обязательные поля
        assert 'id' in workout_data
        assert 'date' in workout_data
        assert 'workout_type' in workout_data
        assert 'duration' in workout_data
        assert 'owner' in workout_data
        assert 'exercises' in workout_data

        # Проверяем структуру owner
        assert 'id' in workout_data['owner']
        assert 'username' in workout_data['owner']

        # Проверяем что exercises это список
        assert isinstance(workout_data['exercises'], list)

        # Если есть упражнения проверяем их структуру
        if len(workout_data['exercises']) > 0:
            exercise = workout_data['exercises'][0]
            assert 'exercise_id' in exercise
            assert 'name' in exercise
            assert 'sets' in exercise
            assert 'reps' in exercise
