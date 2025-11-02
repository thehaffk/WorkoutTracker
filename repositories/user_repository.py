"""
Репозиторий для работы с пользователями
"""
from repositories.database import get_db
from werkzeug.security import generate_password_hash, check_password_hash

class UserRepository:
    """Класс для работы с пользователями"""
    
    @staticmethod
    def create_user(username, email, password, is_trainer=False):
        """
        Создать нового пользователя
        
        Args:
            username (str): Имя пользователя
            email (str): Email
            password (str): Пароль (будет захеширован)
            is_trainer (bool): Является ли пользователь тренером
            
        Returns:
            int: ID созданного пользователя или None
        """
        password_hash = generate_password_hash(password)
        
        query = """
            INSERT INTO users (username, email, password_hash, is_trainer)
            VALUES (%s, %s, %s, %s)
        """
        
        with get_db() as db:
            return db.execute_query(query, (username, email, password_hash, is_trainer))
    
    @staticmethod
    def get_user_by_id(user_id):
        """Получить пользователя по ID"""
        query = "SELECT * FROM users WHERE id = %s"
        
        with get_db() as db:
            return db.fetch_one(query, (user_id,))
    
    @staticmethod
    def get_user_by_username(username):
        """Получить пользователя по имени"""
        query = "SELECT * FROM users WHERE username = %s"
        
        with get_db() as db:
            return db.fetch_one(query, (username,))
    
    @staticmethod
    def get_user_by_email(email):
        """Получить пользователя по email"""
        query = "SELECT * FROM users WHERE email = %s"
        
        with get_db() as db:
            return db.fetch_one(query, (email,))
    
    @staticmethod
    def verify_password(user, password):
        """
        Проверить пароль пользователя
        
        Args:
            user (dict): Данные пользователя из БД
            password (str): Пароль для проверки
            
        Returns:
            bool: True если пароль верный
        """
        if not user:
            return False
        return check_password_hash(user['password_hash'], password)
    
    @staticmethod
    def update_user_goals(user_id, age, weight, height, gender, experience_level, goal):
        """Обновить данные пользователя для калькулятора"""
        query = """
            UPDATE users 
            SET age = %s, weight = %s, height = %s, gender = %s, 
                experience_level = %s, goal = %s
            WHERE id = %s
        """
        
        with get_db() as db:
            return db.execute_query(query, (age, weight, height, gender, 
                                           experience_level, goal, user_id))
    
    @staticmethod
    def update_recommendations(user_id, weekly_workouts, duration, intensity):
        """Сохранить рекомендации калькулятора"""
        query = """
            UPDATE users 
            SET recommended_weekly_workouts = %s, 
                recommended_workout_duration = %s,
                recommended_intensity = %s
            WHERE id = %s
        """
        
        with get_db() as db:
            return db.execute_query(query, (weekly_workouts, duration, intensity, user_id))
    
    @staticmethod
    def get_all_users():
        """Получить всех пользователей (для тренера)"""
        query = "SELECT id, username, email, is_trainer, created_at FROM users ORDER BY created_at DESC"
        
        with get_db() as db:
            return db.fetch_all(query)
