"""
Скрипт для генерации демонстрационных данных в базе данных
Использует библиотеку Faker для создания реалистичных тестовых данных
"""
import os
import random
from datetime import datetime, timedelta
from faker import Faker
from app import app
from models import db, User, Role, Exercise, Workout, WorkoutExercise, Attachment

# Инициализация Faker с русской локализацией
fake = Faker('ru_RU')

# Константы для генерации данных
MUSCLE_GROUPS = ['Грудь', 'Спина', 'Ноги', 'Плечи', 'Руки', 'Пресс', 'Ягодицы']
EQUIPMENT = ['Штанга', 'Гантели', 'Тренажёр', 'Без оборудования', 'Турник', 'Кроссовер']
DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']
WORKOUT_TYPES = ['Силовая', 'Кардио', 'Смешанная', 'Растяжка', 'Функциональная']
GENDERS = ['male', 'female', 'other']

# Реалистичные названия упражнений по группам мышц
EXERCISES_BY_GROUP = {
    'Грудь': [
        'Жим штанги лёжа', 'Жим гантелей лёжа', 'Жим на наклонной скамье',
        'Разводка гантелей', 'Отжимания от пола', 'Отжимания на брусьях',
        'Жим в тренажёре', 'Кроссовер на блоках', 'Пуловер с гантелью'
    ],
    'Спина': [
        'Становая тяга', 'Подтягивания', 'Тяга штанги в наклоне',
        'Тяга гантели в наклоне', 'Тяга верхнего блока', 'Тяга нижнего блока',
        'Гиперэкстензия', 'Тяга Т-грифа', 'Шраги со штангой'
    ],
    'Ноги': [
        'Приседания со штангой', 'Жим ногами', 'Разгибания ног',
        'Сгибания ног', 'Выпады с гантелями', 'Приседания в Смите',
        'Болгарские сплит-приседания', 'Подъёмы на носки', 'Румынская тяга'
    ],
    'Плечи': [
        'Жим штанги стоя', 'Жим гантелей сидя', 'Махи гантелями в стороны',
        'Махи гантелями в наклоне', 'Махи перед собой', 'Жим Арнольда',
        'Тяга штанги к подбородку', 'Разведение рук в тренажёре'
    ],
    'Руки': [
        'Подъём штанги на бицепс', 'Подъём гантелей на бицепс',
        'Французский жим', 'Разгибания на блоке', 'Молотковые сгибания',
        'Жим узким хватом', 'Сгибания на скамье Скотта', 'Отжимания обратным хватом'
    ],
    'Пресс': [
        'Скручивания', 'Подъём ног в висе', 'Планка',
        'Боковые скручивания', 'Велосипед', 'Русские скручивания',
        'Подъём ног лёжа', 'Скручивания на блоке', 'Планка с поворотами'
    ],
    'Ягодицы': [
        'Ягодичный мост', 'Отведение ноги в тренажёре', 'Выпады назад',
        'Приседания сумо', 'Гиперэкстензия для ягодиц', 'Махи ногой назад'
    ]
}

# Описания упражнений
EXERCISE_DESCRIPTIONS = [
    'Базовое упражнение для развития силы и массы. Выполняется с правильной техникой под присмотром.',
    'Эффективное упражнение для изолированной проработки целевой группы мышц.',
    'Комплексное упражнение, задействующее несколько групп мышц одновременно.',
    'Изолирующее упражнение для точечной проработки целевой мышечной группы.',
    'Функциональное упражнение для развития координации и баланса.',
    'Классическое упражнение для набора мышечной массы и развития силы.',
    'Упражнение средней сложности, подходит для проработки целевых мышц.',
    'Рекомендуется для начинающих атлетов, безопасное и эффективное упражнение.'
]


def clear_database():
    """Очистка базы данных перед заполнением"""
    print('Очистка базы данных...')
    with app.app_context():
        # Удаление данных в правильном порядке (из-за foreign keys)
        Attachment.query.delete()
        WorkoutExercise.query.delete()
        Workout.query.delete()
        Exercise.query.delete()
        User.query.delete()
        db.session.commit()
        print('База данных очищена')


def create_users():
    """Создание пользователей разных ролей"""
    print('\nСоздание пользователей...')

    # Получение ролей
    admin_role = Role.query.filter_by(name='admin').first()
    editor_role = Role.query.filter_by(name='editor').first()
    viewer_role = Role.query.filter_by(name='viewer').first()

    users = []

    # 1 администратор
    admin = User(
        username='admin',
        email='admin@workout.com',
        role_id=admin_role.id,
        age=random.randint(25, 40),
        weight=random.uniform(70, 90),
        height=random.randint(170, 190),
        gender=random.choice(['male', 'female'])
    )
    admin.set_password('Admin123')
    users.append(admin)
    print(f'  Создан администратор: admin / Admin123')

    # 2 редактора (тренеры)
    for i in range(1, 3):
        username = f'trainer{i}'
        editor = User(
            username=username,
            email=f'{username}@workout.com',
            role_id=editor_role.id,
            age=random.randint(25, 45),
            weight=random.uniform(65, 95),
            height=random.randint(165, 195),
            gender=random.choice(['male', 'female'])
        )
        editor.set_password(f'Trainer{i}23')
        users.append(editor)
        print(f'  Создан тренер: {username} / Trainer{i}23')

    # 2-4 обычных пользователя
    num_viewers = random.randint(2, 4)
    for i in range(1, num_viewers + 1):
        first_name = fake.first_name()
        username = f'user{i}'
        viewer = User(
            username=username,
            email=f'{username}@workout.com',
            role_id=viewer_role.id,
            age=random.randint(18, 50),
            weight=random.uniform(55, 100),
            height=random.randint(155, 195),
            gender=random.choice(GENDERS)
        )
        viewer.set_password(f'User{i}Pass')
        users.append(viewer)
        print(f'  Создан пользователь: {username} / User{i}Pass')

    # Сохранение пользователей в базе данных
    for user in users:
        db.session.add(user)
    db.session.commit()

    print(f'Создано пользователей: {len(users)}')
    return users


def create_exercises(users):
    """Создание упражнений"""
    print('\nСоздание упражнений...')

    exercises = []
    exercise_count = random.randint(15, 20)

    # Получаем редакторов и админов для создания публичных упражнений
    editors = [u for u in users if u.role.name in ['admin', 'editor']]

    created_names = set()

    while len(exercises) < exercise_count:
        # Выбираем группу мышц
        muscle_group = random.choice(MUSCLE_GROUPS)

        # Выбираем упражнение из списка для этой группы
        available_exercises = [ex for ex in EXERCISES_BY_GROUP[muscle_group] if ex not in created_names]
        if not available_exercises:
            continue

        name = random.choice(available_exercises)
        created_names.add(name)

        # Определяем сложность в зависимости от типа упражнения
        difficulty = random.choice(DIFFICULTY_LEVELS)

        # Выбираем оборудование
        equipment = random.choice(EQUIPMENT)

        # 80% упражнений - публичные (от тренеров), 20% - личные
        is_public = random.random() < 0.8
        owner = random.choice(editors) if is_public else random.choice(users)

        exercise = Exercise(
            name=name,
            description=random.choice(EXERCISE_DESCRIPTIONS),
            muscle_group=muscle_group,
            equipment=equipment,
            difficulty=difficulty,
            is_public=is_public,
            owner_id=owner.id if not is_public else random.choice(editors).id
        )

        exercises.append(exercise)
        print(f'  Создано упражнение: {name} ({muscle_group}, {difficulty})')

    # Сохранение упражнений
    for exercise in exercises:
        db.session.add(exercise)
    db.session.commit()

    print(f'Создано упражнений: {len(exercises)}')
    return exercises


def create_workouts(users, exercises):
    """Создание тренировок за последние 3 месяца"""
    print('\nСоздание тренировок...')

    workouts = []
    workout_exercises_list = []

    num_workouts = random.randint(20, 30)

    # Дата начала - 3 месяца назад
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now()

    for _ in range(num_workouts):
        # Случайная дата в диапазоне последних 3 месяцев
        random_days = random.randint(0, 90)
        workout_date = (start_date + timedelta(days=random_days)).date()

        # Случайный пользователь
        owner = random.choice(users)

        # Тип тренировки
        workout_type = random.choice(WORKOUT_TYPES)

        # Длительность тренировки (30-120 минут)
        duration = random.randint(30, 120)

        # Заметки (опционально)
        notes = fake.text(max_nb_chars=200) if random.random() < 0.3 else None

        workout = Workout(
            date=workout_date,
            workout_type=workout_type,
            duration=duration,
            notes=notes,
            owner_id=owner.id
        )

        workouts.append(workout)

    # Сохранение тренировок
    for workout in workouts:
        db.session.add(workout)
    db.session.commit()

    print(f'Создано тренировок: {len(workouts)}')

    # Создание упражнений в тренировках
    print('\nДобавление упражнений в тренировки...')

    for workout in workouts:
        # 2-5 упражнений на тренировку
        num_exercises = random.randint(2, 5)
        selected_exercises = random.sample(exercises, min(num_exercises, len(exercises)))

        for order, exercise in enumerate(selected_exercises):
            # Количество подходов (1-5)
            sets = random.randint(1, 5)

            # Количество повторений (зависит от типа упражнения)
            if exercise.difficulty == 'beginner':
                reps = random.randint(12, 20)
            elif exercise.difficulty == 'intermediate':
                reps = random.randint(8, 15)
            else:  # advanced
                reps = random.randint(4, 10)

            # Вес (если применимо)
            weight = None
            if exercise.equipment in ['Штанга', 'Гантели', 'Тренажёр']:
                if exercise.muscle_group in ['Ноги', 'Спина']:
                    weight = random.uniform(40, 150)
                elif exercise.muscle_group in ['Грудь', 'Плечи']:
                    weight = random.uniform(20, 100)
                else:  # Руки, Пресс
                    weight = random.uniform(5, 40)

            # Длительность (для статических упражнений)
            duration_seconds = None
            if exercise.name in ['Планка', 'Планка с поворотами']:
                duration_seconds = random.randint(30, 180)

            # Дистанция (для кардио)
            distance = None
            if workout.workout_type == 'Кардио':
                distance = random.uniform(1, 10)

            workout_exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=exercise.id,
                sets=sets,
                reps=reps,
                weight=weight,
                duration=duration_seconds,
                distance=distance,
                order=order,
                notes=fake.sentence() if random.random() < 0.2 else None
            )

            workout_exercises_list.append(workout_exercise)

    # Сохранение упражнений в тренировках
    for we in workout_exercises_list:
        db.session.add(we)
    db.session.commit()

    print(f'Создано записей упражнений в тренировках: {len(workout_exercises_list)}')
    return workouts


def create_attachments(users, exercises):
    """Создание файловых вложений"""
    print('\nСоздание файловых вложений...')

    attachments = []
    num_attachments = random.randint(5, 10)

    # Убедимся, что директория для загрузок существует
    upload_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    for i in range(num_attachments):
        # Случайный тип файла
        file_type = random.choice(['image', 'document', 'data'])

        if file_type == 'image':
            extension = random.choice(['png', 'jpg', 'jpeg'])
            mime_type = f'image/{extension}'
            original_filename = f'exercise_photo_{i+1}.{extension}'
        elif file_type == 'document':
            extension = 'pdf'
            mime_type = 'application/pdf'
            original_filename = f'training_plan_{i+1}.pdf'
        else:  # data
            extension = random.choice(['txt', 'csv', 'json'])
            mime_type = f'text/{extension}' if extension != 'json' else 'application/json'
            original_filename = f'workout_data_{i+1}.{extension}'

        # Генерируем уникальное имя файла
        filename = f'{fake.uuid4()}.{extension}'
        file_path = os.path.join(upload_dir, filename)

        # Создаём пустой файл
        with open(file_path, 'w') as f:
            if extension == 'json':
                f.write('{"data": "demo"}')
            elif extension == 'csv':
                f.write('column1,column2\nvalue1,value2')
            else:
                f.write('Demo content')

        # Получаем размер файла
        file_size = os.path.getsize(file_path)

        # Случайный владелец и упражнение
        owner = random.choice(users)
        exercise = random.choice(exercises) if random.random() < 0.7 else None

        attachment = Attachment(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            exercise_id=exercise.id if exercise else None,
            owner_id=owner.id
        )

        attachments.append(attachment)
        print(f'  Создано вложение: {original_filename} ({file_size} bytes)')

    # Сохранение вложений
    for attachment in attachments:
        db.session.add(attachment)
    db.session.commit()

    print(f'Создано файловых вложений: {len(attachments)}')
    return attachments


def print_statistics():
    """Вывод статистики созданных данных"""
    print('\n' + '='*60)
    print('СТАТИСТИКА СОЗДАННЫХ ДАННЫХ')
    print('='*60)

    with app.app_context():
        users_count = User.query.count()
        exercises_count = Exercise.query.count()
        workouts_count = Workout.query.count()
        workout_exercises_count = WorkoutExercise.query.count()
        attachments_count = Attachment.query.count()

        print(f'\nПользователи: {users_count}')
        print(f'  - Администраторы: {User.query.join(Role).filter(Role.name == "admin").count()}')
        print(f'  - Редакторы (тренеры): {User.query.join(Role).filter(Role.name == "editor").count()}')
        print(f'  - Пользователи (viewer): {User.query.join(Role).filter(Role.name == "viewer").count()}')

        print(f'\nУпражнения: {exercises_count}')
        print(f'  - Публичные: {Exercise.query.filter_by(is_public=True).count()}')
        print(f'  - Личные: {Exercise.query.filter_by(is_public=False).count()}')

        print(f'\nТренировки: {workouts_count}')
        print(f'Записей упражнений в тренировках: {workout_exercises_count}')
        print(f'Файловых вложений: {attachments_count}')

        print('\n' + '='*60)
        print('ДАННЫЕ ДЛЯ ВХОДА:')
        print('='*60)
        print('\nАдминистратор:')
        print('  Логин: admin')
        print('  Пароль: Admin123')
        print('\nТренеры:')
        print('  Логин: trainer1 / Пароль: Trainer123')
        print('  Логин: trainer2 / Пароль: Trainer223')
        print('\nПользователи:')
        for i in range(1, 5):
            print(f'  Логин: user{i} / Пароль: User{i}Pass')
        print('='*60)


def main():
    """Основная функция для запуска генерации данных"""
    print('='*60)
    print('ГЕНЕРАЦИЯ ДЕМОНСТРАЦИОННЫХ ДАННЫХ')
    print('='*60)

    with app.app_context():
        # Очистка базы данных (кроме ролей)
        clear_database()

        # Проверка наличия ролей
        if Role.query.count() == 0:
            print('\nОШИБКА: Роли не найдены в базе данных!')
            print('Сначала запустите app.py для инициализации ролей')
            return

        # Генерация данных
        users = create_users()
        exercises = create_exercises(users)
        workouts = create_workouts(users, exercises)
        attachments = create_attachments(users, exercises)

        # Вывод статистики
        print_statistics()

        print('\n✓ Генерация демонстрационных данных завершена успешно!')


if __name__ == '__main__':
    main()
