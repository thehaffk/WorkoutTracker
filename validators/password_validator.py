"""
Валидатор паролей для системы
"""
import re

def password_validator(password):
    """
    Проверяет пароль на соответствие требованиям безопасности.
    
    Требования:
    - Длина от 8 до 128 символов
    - Минимум одна заглавная буква
    - Минимум одна строчная буква
    - Минимум одна цифра
    - Без пробелов
    - Только разрешённые символы
    
    Args:
        password (str): Пароль для проверки
        
    Returns:
        str or None: Текст ошибки или None если пароль валиден
    """
    if password is None or len(password) < 8:
        return "Пароль должен содержать как минимум 8 символов!"
    
    if len(password) > 128:
        return "Пароль должен содержать не более 128 символов!"
    
    if not re.search(r'[А-ЯA-Z]', password):
        return "Пароль должен содержать хотя бы одну заглавную букву!"
    
    if not re.search(r'[а-яa-z]', password):
        return "Пароль должен содержать хотя бы одну строчную букву!"
    
    if not re.search(r'[0-9]', password):
        return "Пароль должен содержать хотя бы одну цифру!"
    
    if " " in password:
        return "Пароль не должен содержать пробелов!"
    
    allowed_characters = r'^[A-Za-zА-Яа-я0-9~!?@#$%^&*_\-+\(\)\[\]\{\}><\/\\|\"\'.,:;]+$'
    if not re.match(allowed_characters, password):
        return r"""Используются запрещённые символы! Вводите только латинские или кириллические буквы, 
цифры 0-9, а также любые из спец. символов: ~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " ' . , : ;"""
    
    return None


def validate_username(username):
    """Валидация имени пользователя"""
    if not username or len(username) < 3:
        return "Имя пользователя должно содержать минимум 3 символа!"
    
    if len(username) > 50:
        return "Имя пользователя слишком длинное (максимум 50 символов)!"
    
    if not re.match(r'^[A-Za-z0-9_-]+$', username):
        return "Имя пользователя может содержать только латинские буквы, цифры, _ и -"
    
    return None


def validate_email(email):
    """Валидация email"""
    if not email:
        return "Email обязателен для заполнения!"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return "Некорректный формат email!"
    
    return None
