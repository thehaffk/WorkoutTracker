"""
Модуль для работы с базой данных MySQL
"""
import mysql.connector
from mysql.connector import Error
from config import Config

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Установить соединение с БД"""
        try:
            self.connection = mysql.connector.connect(**Config.DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            print(f"Ошибка подключения к MySQL: {e}")
            return False
    
    def disconnect(self):
        """Закрыть соединение с БД"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def execute_query(self, query, params=None):
        """
        Выполнить запрос (INSERT, UPDATE, DELETE)
        
        Args:
            query (str): SQL запрос
            params (tuple): Параметры запроса
            
        Returns:
            int: ID последней вставленной записи или количество затронутых строк
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            self.connection.commit()
            
            if query.strip().upper().startswith('INSERT'):
                return self.cursor.lastrowid
            return self.cursor.rowcount
        except Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            self.connection.rollback()
            return None
    
    def fetch_one(self, query, params=None):
        """
        Получить одну запись из БД
        
        Args:
            query (str): SQL запрос
            params (tuple): Параметры запроса
            
        Returns:
            dict: Словарь с данными или None
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            return self.cursor.fetchone()
        except Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            return None
    
    def fetch_all(self, query, params=None):
        """
        Получить все записи из БД
        
        Args:
            query (str): SQL запрос
            params (tuple): Параметры запроса
            
        Returns:
            list: Список словарей с данными
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            return []
    
    def __enter__(self):
        """Поддержка context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения при выходе из контекста"""
        self.disconnect()


def get_db():
    """Получить экземпляр базы данных"""
    return Database()
