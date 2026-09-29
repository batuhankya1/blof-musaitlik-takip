import sqlite3
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    DB_PATH = '/tmp/kimbos.db'
    source_db = os.path.join(BASE_DIR, 'kimbos.db')
    if os.path.exists(source_db) and not os.path.exists(DB_PATH):
        import shutil
        try:
            shutil.copyfile(source_db, DB_PATH)
        except Exception as e:
            print("DB copy error:", e)
else:
    DB_PATH = os.path.join(BASE_DIR, 'kimbos.db')

AVATAR_COLORS = [
    '#4F46E5', '#7C3AED', '#EC4899', '#EF4444', 
    '#F59E0B', '#10B981', '#06B6D4', '#3B82F6', 
    '#8B5CF6', '#14B8A6'
]

DAYS = [
    {"index": 0, "name": "Pazartesi", "short": "Pzt"},
    {"index": 1, "name": "Salı", "short": "Sal"},
    {"index": 2, "name": "Çarşamba", "short": "Çar"},
    {"index": 3, "name": "Perşembe", "short": "Per"},
    {"index": 4, "name": "Cuma", "short": "Cum"},
    {"index": 5, "name": "Cumartesi", "short": "Cmt"},
    {"index": 6, "name": "Pazar", "short": "Paz"}
]

DAY_NAME_TO_INDEX = {d["name"].lower(): d["index"] for d in DAYS}
DAY_INDEX_TO_NAME = {d["index"]: d["name"] for d in DAYS}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table: name has NOCASE collation for case-insensitive matching
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE COLLATE NOCASE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            avatar_color TEXT DEFAULT '#4F46E5',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Classes / Schedule table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day_index INTEGER NOT NULL,
            day_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT DEFAULT '',
            color TEXT DEFAULT '#3b82f6',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Index for fast lookup by user and day
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_classes_user_day 
        ON classes(user_id, day_index)
    ''')
    
    # System settings (e.g. optional Gemini API Key)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()

    # Eğer kullanıcı tablosu tamamen boşsa, varsayılan demo verilerini yükle
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        try:
            from seed_data import seed_demo_data
            seed_demo_data()
        except Exception as e:
            print("Auto-seed hatası:", e)

def find_user_by_name(name):
    """Case-insensitive search by user name"""
    if not name:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE LOWER(name) = LOWER(?)", 
        (name.strip(),)
    ).fetchone()
    conn.close()
    return user

def find_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def find_user_by_email(email):
    if not email:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", 
        (email.strip(),)
    ).fetchone()
    conn.close()
    return user

def create_user(name, email, password_hash, avatar_color=None):
    if not avatar_color:
        avatar_color = random.choice(AVATAR_COLORS)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, avatar_color) VALUES (?, ?, ?, ?)",
        (name.strip(), email.strip().lower(), password_hash, avatar_color)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_user_classes(user_id, day_index=None):
    conn = get_db()
    if day_index is not None:
        rows = conn.execute(
            "SELECT * FROM classes WHERE user_id = ? AND day_index = ? ORDER BY start_time ASC",
            (user_id, day_index)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM classes WHERE user_id = ? ORDER BY day_index ASC, start_time ASC",
            (user_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_user_classes(user_id):
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_class(user_id, day_index, start_time, end_time, title, location="", color="#3b82f6"):
    day_name = DAY_INDEX_TO_NAME.get(int(day_index), "Pazartesi")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO classes (user_id, day_index, day_name, start_time, end_time, title, location, color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, int(day_index), day_name, start_time.strip(), end_time.strip(), title.strip(), location.strip(), color))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_class(class_id, user_id, day_index, start_time, end_time, title, location="", color="#3b82f6"):
    day_name = DAY_INDEX_TO_NAME.get(int(day_index), "Pazartesi")
    conn = get_db()
    conn.execute('''
        UPDATE classes 
        SET day_index = ?, day_name = ?, start_time = ?, end_time = ?, title = ?, location = ?, color = ?
        WHERE id = ? AND user_id = ?
    ''', (int(day_index), day_name, start_time.strip(), end_time.strip(), title.strip(), location.strip(), color, class_id, user_id))
    conn.commit()
    conn.close()

def delete_class(class_id, user_id):
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE id = ? AND user_id = ?", (class_id, user_id))
    conn.commit()
    conn.close()

def save_all_classes_for_user(user_id, classes_list):
    """Replaces all classes of a user with a new list"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM classes WHERE user_id = ?", (user_id,))
    for c in classes_list:
        d_idx = int(c.get('day_index', 0))
        d_name = DAY_INDEX_TO_NAME.get(d_idx, c.get('day_name', 'Pazartesi'))
        cursor.execute('''
            INSERT INTO classes (user_id, day_index, day_name, start_time, end_time, title, location, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            d_idx,
            d_name,
            c.get('start_time', '09:00').strip(),
            c.get('end_time', '10:00').strip(),
            c.get('title', 'Ders').strip(),
            c.get('location', '').strip(),
            c.get('color', '#3b82f6')
        ))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    users = conn.execute("SELECT id, name, email, avatar_color, created_at FROM users ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(u) for u in users]

def delete_user(user_id):
    """Kullanıcıyı ve derslerini veritabanından tamamen siler"""
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_demo_users():
    """Hazır demo hesaplarını (Ahmet, Zeynep, Burak, Ayşe) siler"""
    demo_names = ['Ahmet', 'Zeynep', 'Burak', 'Ayşe', 'Ayse']
    conn = get_db()
    placeholders = ','.join(['?'] * len(demo_names))
    conn.execute(f"DELETE FROM users WHERE LOWER(name) IN ({','.join(['LOWER(?)'] * len(demo_names))})", demo_names)
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

