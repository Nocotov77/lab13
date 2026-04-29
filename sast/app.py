from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import subprocess

app = Flask(__name__)

# Инициализация базы данных (без хардкода паролей в коде — оставляем тестовые для демо,
# но в реальном проекте они должны быть захешированы и добавлены через безопасный механизм)
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Тестовые данные (в реальности пароли должны быть захешированы)
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, username, email, password) VALUES (?, ?, ?, ?)",
        (1, 'admin', 'admin@example.com', 'admin123')
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, username, email, password) VALUES (?, ?, ?, ?)",
        (2, 'user', 'user@example.com', 'user123')
    )
    conn.commit()
    conn.close()

# Чувствительный ключ из переменной окружения
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise RuntimeError("Не задана переменная окружения API_KEY. Экспортируйте её перед запуском.")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>User Management</title>
</head>
<body>
    <h1>User Management System</h1>
    <form action="/user" method="GET">
        <label>User ID:</label>
        <input type="text" name="id">
        <button type="submit">Get User</button>
    </form>

    <form action="/search" method="GET">
        <label>Search by username:</label>
        <input type="text" name="username">
        <button type="submit">Search</button>
    </form>

    <div id="result">
        {content}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE.format(content="<p>Enter user ID or search by username</p>"))

@app.route('/user')
def get_user():
    """Получение пользователя по ID — БЕЗОПАСНАЯ ВЕРСИЯ"""
    user_id = request.args.get('id')

    if not user_id:
        return jsonify({"error": "Missing id parameter"}), 400

    # Простая валидация: id должен быть числом
    if not user_id.isdigit():
        return jsonify({"error": "Invalid id parameter, must be integer"}), 400

    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        # Параметризованный запрос: используем ? как плейсхолдер
        query = "SELECT * FROM users WHERE id = ?"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({"id": user[0], "username": user[1], "email": user[2]})
        return jsonify({"error": "User not found"}), 404
    except sqlite3.Error as e:
        return jsonify({"error": "Database error"}), 500

@app.route('/search')
def search_users():
    """Поиск пользователей по имени — БЕЗОПАСНАЯ ВЕРСИЯ"""
    username = request.args.get('username', '')

    if not username:
        return jsonify({"error": "Missing username parameter"}), 400

    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        # Параметризованный запрос: % оборачивается в подставляемое значение
        query = "SELECT * FROM users WHERE username LIKE ?"
        cursor.execute(query, (f'%{username}%',))
        users = cursor.fetchall()
        conn.close()
        result = [{"id": u[0], "username": u[1], "email": u[2]} for u in users]
        return jsonify(result)
    except sqlite3.Error as e:
        return jsonify({"error": "Database error"}), 500

@app.route('/api/data')
def get_data():
    """Эндпоинт с секретным ключом — теперь ключ берётся из окружения"""
    # В реальном приложении здесь должна быть аутентификация перед отдачей ключа
    return jsonify({"api_key": API_KEY, "message": "This is sensitive data"})

# Эндпоинт /execute удалён из соображений безопасности.
# Если функциональность критична, используйте строгий allow-list:
# @app.route('/execute')
# def execute_command():
#     ALLOWED_COMMANDS = ['echo', 'date', 'whoami']
#     cmd = request.args.get('cmd', '')
#     if not any(cmd.startswith(f"{c} ") or cmd == c for c in ALLOWED_COMMANDS):
#         return jsonify({"error": "Command not allowed"}), 403
#     # Без shell=True, с передачей аргументов списком
#     try:
#         result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
#         return jsonify({"output": result.stdout})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    # debug=False и только локальный доступ
    app.run(debug=False, host='127.0.0.1', port=5000)