-- Создание базы данных для системы управления тренировками
CREATE DATABASE IF NOT EXISTS workout_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE workout_tracker;

-- Таблица пользователей
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    is_trainer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Данные для калькулятора нагрузки
    age INT NULL,
    weight DECIMAL(5,2) NULL,
    height INT NULL,
    gender ENUM('male', 'female', 'other') NULL,
    experience_level ENUM('beginner', 'intermediate', 'advanced') NULL,
    goal ENUM('lose_weight', 'maintain', 'gain_muscle', 'strength') NULL,
    
    -- Рекомендуемая нагрузка (устанавливается калькулятором)
    recommended_weekly_workouts INT NULL,
    recommended_workout_duration INT NULL COMMENT 'В минутах',
    recommended_intensity ENUM('low', 'moderate', 'high') NULL,
    
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- Таблица упражнений
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    exercise_name VARCHAR(100) NOT NULL,
    muscle_group VARCHAR(50) NOT NULL COMMENT 'Грудь, Спина, Ноги, Плечи, Руки, Пресс и т.д.',
    equipment VARCHAR(50) NULL COMMENT 'Штанга, гантели, тренажёр, без оборудования',
    difficulty ENUM('beginner', 'intermediate', 'advanced') DEFAULT 'beginner',
    calories_per_set INT NOT NULL DEFAULT 0 COMMENT 'Примерные калории за подход',
    description TEXT NULL COMMENT 'Описание техники выполнения',
    img_path TEXT NULL,
    is_public BOOLEAN DEFAULT FALSE COMMENT 'Общее упражнение (добавил тренер) или личное',
    owner_id INTEGER NULL COMMENT 'Создатель упражнения, NULL если публичное',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_muscle_group (muscle_group),
    INDEX idx_difficulty (difficulty),
    INDEX idx_owner (owner_id)
) ENGINE=InnoDB;

-- Таблица тренировок
CREATE TABLE workouts (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    workout_date DATE NOT NULL,
    workout_type VARCHAR(50) NOT NULL COMMENT 'Силовая, Кардио, Смешанная, Растяжка',
    duration INT NOT NULL COMMENT 'Длительность в минутах',
    intensity ENUM('low', 'moderate', 'high') DEFAULT 'moderate',
    
    -- Итоговые показатели
    total_exercises INT NOT NULL DEFAULT 0,
    total_sets INT NOT NULL DEFAULT 0,
    total_reps INT NOT NULL DEFAULT 0,
    total_weight DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT 'Общий поднятый вес в кг',
    total_calories INT NOT NULL DEFAULT 0,
    
    notes TEXT NULL COMMENT 'Заметки о тренировке',
    owner_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_workout_date (workout_date),
    INDEX idx_owner (owner_id),
    INDEX idx_type (workout_type)
) ENGINE=InnoDB;

-- Связь многие-ко-многим: упражнения в тренировках
CREATE TABLE m2m_exercises_workouts (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    workout_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    
    -- Детали выполнения упражнения
    sets INT NOT NULL DEFAULT 1 COMMENT 'Количество подходов',
    reps INT NOT NULL DEFAULT 1 COMMENT 'Количество повторений',
    weight DECIMAL(6,2) NULL COMMENT 'Вес в кг (если применимо)',
    duration INT NULL COMMENT 'Длительность в секундах (для статических упражнений)',
    distance DECIMAL(6,2) NULL COMMENT 'Дистанция в км (для кардио)',
    calories INT NOT NULL DEFAULT 0 COMMENT 'Сожжённые калории',
    
    notes TEXT NULL COMMENT 'Заметки по упражнению',
    order_in_workout INT NOT NULL DEFAULT 0 COMMENT 'Порядок в тренировке',
    
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    INDEX idx_workout (workout_id),
    INDEX idx_exercise (exercise_id)
) ENGINE=InnoDB;

-- Вставка тестовых данных

-- Тренер (администратор)
INSERT INTO users (username, email, password_hash, is_trainer) VALUES 
('trainer', 'trainer@example.com', 'pbkdf2:sha256:600000$test$hashed_password', TRUE);

-- Обычный пользователь
INSERT INTO users (username, email, password_hash, is_trainer, age, weight, height, gender, experience_level, goal) VALUES 
('user', 'user@example.com', 'pbkdf2:sha256:600000$test$hashed_password', FALSE, 25, 75.5, 180, 'male', 'intermediate', 'gain_muscle');

-- Публичные упражнения (от тренера)
INSERT INTO exercises (exercise_name, muscle_group, equipment, difficulty, calories_per_set, description, is_public, owner_id) VALUES 
('Жим штанги лёжа', 'Грудь', 'Штанга', 'intermediate', 15, 'Базовое упражнение для развития грудных мышц', TRUE, 1),
('Приседания со штангой', 'Ноги', 'Штанга', 'intermediate', 20, 'Базовое упражнение для развития ног', TRUE, 1),
('Становая тяга', 'Спина', 'Штанга', 'advanced', 25, 'Базовое упражнение для спины и общей силы', TRUE, 1),
('Подтягивания', 'Спина', 'Турник', 'intermediate', 12, 'Упражнение с собственным весом для спины', TRUE, 1),
('Жим гантелей сидя', 'Плечи', 'Гантели', 'intermediate', 10, 'Упражнение для развития дельтовидных мышц', TRUE, 1),
('Сгибания на бицепс', 'Руки', 'Гантели', 'beginner', 8, 'Изолирующее упражнение на бицепс', TRUE, 1),
('Скручивания', 'Пресс', 'Без оборудования', 'beginner', 5, 'Упражнение для пресса', TRUE, 1),
('Бег', 'Кардио', 'Без оборудования', 'beginner', 50, 'Кардио-упражнение', TRUE, 1);
