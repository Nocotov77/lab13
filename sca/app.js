// Для работы с переменными окружения из .env (необязательно)
try { require('dotenv').config(); } catch(e) {}

const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');
const crypto = require('crypto');

const app = express();
const port = process.env.PORT || 3000;

// Шаблонизатор
app.set('view engine', 'ejs');
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

// ====== Content Security Policy (CSP) с nonce ======
app.use((req, res, next) => {
    const nonce = crypto.randomBytes(16).toString('base64');
    res.locals.nonce = nonce;
    res.setHeader(
        'Content-Security-Policy',
        `default-src 'self'; script-src 'self' 'nonce-${nonce}'; style-src 'self' 'unsafe-inline'`
    );
    next();
});

// ====== API‑ключ из переменной окружения (больше не хранится в коде) ======
const API_KEY = process.env.API_KEY || 'change-me-in-production';

// ====== База данных ======
const db = new sqlite3.Database('./comments.db');
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    db.run(`INSERT OR IGNORE INTO comments (id, username, comment) VALUES
        (1, 'admin', 'Добро пожаловать на сайт!'),
        (2, 'user1', 'Отличный ресурс'),
        (3, 'user2', 'Очень полезная информация')`);
});

// ====== Функция санитизации ======
function sanitize(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

// ====== Маршруты ======

// Главная страница
app.get('/', (req, res) => {
    db.all('SELECT * FROM comments ORDER BY created_at DESC', [], (err, comments) => {
        if (err) return res.status(500).send('Ошибка базы данных');
        res.render('index', { comments, error: null, nonce: res.locals.nonce });
    });
});

// Добавление комментария (с санитизацией)
app.post('/comment', (req, res) => {
    const username = sanitize(req.body.username || 'Anonymous');
    const comment = sanitize(req.body.comment || '');
    db.run('INSERT INTO comments (username, comment) VALUES (?, ?)', [username, comment], (err) => {
        if (err) return res.status(500).send('Ошибка сохранения');
        res.redirect('/');
    });
});

// API: список комментариев (allow‑list для сортировки)
app.get('/api/comments', (req, res) => {
    const sort = req.query.sort || 'created_at DESC';
    const allowed = ['created_at DESC', 'created_at ASC', 'username ASC', 'username DESC'];
    if (!allowed.includes(sort)) {
        return res.status(400).json({ error: 'Недопустимый параметр сортировки' });
    }
    db.all(`SELECT * FROM comments ORDER BY ${sort}`, [], (err, rows) => {
        if (err) return res.status(500).json({ error: 'Ошибка БД' });
        res.json(rows);
    });
});

// API: поиск (параметризованный запрос)
app.get('/api/search', (req, res) => {
    const q = req.query.q || '';
    db.all('SELECT * FROM comments WHERE comment LIKE ?', [`%${q}%`], (err, rows) => {
        if (err) return res.status(500).json({ error: 'Ошибка БД' });
        res.json(rows);
    });
});

// API: конфигурация (API‑ключ скрыт)
app.get('/api/config', (req, res) => {
    res.json({
        environment: process.env.NODE_ENV || 'development',
        debug: process.env.NODE_ENV !== 'production'
    });
});

// API: внешний запрос (защита от SSRF)
app.get('/api/external', async (req, res) => {
    const url = req.query.url;
    if (!url) return res.status(400).json({ error: 'Требуется параметр url' });
    try {
        const parsed = new URL(url);
        if (!['http:', 'https:'].includes(parsed.protocol)) {
            return res.status(400).json({ error: 'Разрешены только HTTP/HTTPS' });
        }
        const blocked = ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254'];
        if (blocked.includes(parsed.hostname)) {
            return res.status(403).json({ error: 'Доступ к этому хосту запрещён' });
        }
        const response = await axios.get(url, { timeout: 5000 });
        res.json(response.data);
    } catch (e) {
        res.status(500).json({ error: 'Ошибка внешнего запроса' });
    }
});

// Запуск сервера
app.listen(port, () => {
    console.log(`Сервер запущен на http://localhost:${port}`);
});