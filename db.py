import sqlite3
import json
from pathlib import Path
import datetime
from zoneinfo import ZoneInfo

DB_PATH = Path(__file__).parent / 'reminder_log.db'
DEFAULT_TZ = 'America/New_York'

def get_connection():
    """Create and return database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    with get_connection() as conn:
        conn.execute('PRAGMA foreign_keys = ON;')
        # Groups table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        ''')
        # Reminders table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                times TEXT NOT NULL,
                timezone TEXT NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(chat_id) ON DELETE CASCADE
            )
        ''')
        # History table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pill_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

def add_reminder(chat_id, times, timezone, name):
    """Add new reminder to database"""
    with get_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO groups (chat_id) VALUES (?)', (chat_id,))
        conn.execute('''
            INSERT INTO reminders (group_id, times, timezone, name)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, json.dumps(times), timezone, name))
        conn.commit()

def get_reminder(reminder_id):
    """Get reminder details by ID"""
    with get_connection() as conn:
        cursor = conn.execute('''
            SELECT * FROM reminders 
            WHERE id = ?
        ''', (reminder_id,))
        row = cursor.fetchone()
        return {
            'id': row['id'],
            'group_id': row['group_id'],
            'times': json.loads(row['times']),
            'timezone': row['timezone'],
            'name': row['name']
        } if row else None
    
    
def log_pill(reminder_id, user_id, username):
    """Log pill intake with local timestamp"""
    with get_connection() as conn:
        # Get reminder's timezone
        cursor = conn.execute('''
            SELECT timezone FROM reminders WHERE id = ?
        ''', (reminder_id,))
        timezone = cursor.fetchone()['timezone']
        
        # Create timestamp with timezone
        local_time = datetime.datetime.now(ZoneInfo(timezone)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('''
            INSERT INTO pill_logs (reminder_id, user_id, username, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (reminder_id, user_id, username, local_time))
        conn.commit()

def get_history(reminder_id):
    """Get pill history"""
    with get_connection() as conn:
        cursor = conn.execute('''
            SELECT timestamp, username
            FROM pill_logs
            WHERE reminder_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
        ''', (reminder_id,))
        return [
            {
                "timestamp": row["timestamp"],
                "username": row["username"]
            }
            for row in cursor.fetchall()
        ]
    
def get_last_reminder_id(chat_id):
    """Get ID of last created reminder"""
    with get_connection() as conn:
        cursor = conn.execute('''
            SELECT id FROM reminders 
            WHERE group_id = ? 
            ORDER BY id DESC 
            LIMIT 1
        ''', (chat_id,))
        row = cursor.fetchone()
        return row['id'] if row else None

