from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Импорты модулей (будут созданы позже)
# from auth import auth_bp
# from exercises import exercises_bp
# from workouts import workouts_bp
# from pages import pages_bp

# Регистрация blueprints
# app.register_blueprint(auth_bp)
# app.register_blueprint(exercises_bp)
# app.register_blueprint(workouts_bp)
# app.register_blueprint(pages_bp)

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def trainer_required(f):
    """Декоратор для проверки прав тренера"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_trainer'):
            flash('У вас нет прав для выполнения этого действия', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        return redirect(url_for('workouts_list'))
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
