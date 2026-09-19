"""
db.py — SQLite data layer for BabyBloom Pregnancy Care Tracker.

Everything the app stores lives in one local SQLite file (bloom.db),
created on first run inside the app's private data directory.

Schema is intentionally simple and easy to extend — add a column or a
table here and wire it up in the relevant screen; nothing else in the
app needs to change.
"""

import sqlite3
import os
from datetime import datetime

try:
    from kivy.app import App
except ImportError:
    App = None

# The six sugar reading slots requested. Add more here later
# (e.g. "midnight", "bedtime") and the Sugar screen will pick them up
# automatically — see screens/sugar_screen.py SLOT_ORDER.
SUGAR_SLOTS = [
    "Before Breakfast",
    "After Breakfast",
    "Before Lunch",
    "After Lunch",
    "Before Dinner",
    "After Dinner",
]

# Non-sugar vital types the Readings screen can log, any number of
# times per day, all optional. "two_values" means it needs two number
# fields (systolic/diastolic for BP) instead of one.
VITAL_TYPES = {
    "BP":     {"label": "Blood Pressure", "unit": "mmHg", "icon": "heart-pulse",
               "two_values": True, "value1_label": "Systolic", "value2_label": "Diastolic"},
    "O2":     {"label": "Oxygen (SpO2)", "unit": "%", "icon": "lungs",
               "two_values": False, "value1_label": "SpO2"},
    "Pulse":  {"label": "Pulse", "unit": "bpm", "icon": "heart-outline",
               "two_values": False, "value1_label": "Pulse"},
    "Weight": {"label": "Weight", "unit": "kg", "icon": "scale-bathroom",
               "two_values": False, "value1_label": "Weight"},
}
VITAL_TYPE_ORDER = ["BP", "O2", "Pulse", "Weight"]


def get_db_path():
    """Store the DB in the app's proper private storage.

    On Android, only the app's own sandboxed directory is writable —
    os.path.expanduser("~") resolves to "/data" there (the root of the
    whole data partition), NOT the app's sandbox, and writing there
    raises PermissionError and crashes the app on launch (confirmed via
    a real device crash log: "PermissionError: [Errno 13] Permission
    denied: '/data/.babybloom'"). Kivy's App.user_data_dir handles this
    correctly per-platform (Android, iOS, desktop) using the right
    OS-provided app-private directory, so use it whenever a Kivy App is
    running — which is always true on-device, and true on desktop from
    the moment MDApp.build() starts.

    Only fall back to a plain home-folder location when there's no
    running App at all (e.g. this module imported standalone, like from
    assets/generate_assets.py) — desktop-only, since Android always
    runs inside an App.
    """
    if App and App.get_running_app():
        app = App.get_running_app()
        # Best-effort only: on Linux/WSL desktop, Kivy's user_data_dir
        # property creates its folder with os.mkdir() (not makedirs()),
        # which can raise if the parent (~/.config) doesn't exist yet on
        # a fresh machine — pre-create it to avoid that. This must NEVER
        # be allowed to crash the app itself: on Android, "~" ALSO
        # resolves to the unwritable /data root (same root cause as the
        # bug this whole function exists to avoid), so attempting this
        # there would raise the exact same PermissionError we're fixing.
        # Wrapped so a failure here is silently ignored either way.
        try:
            os.makedirs(os.path.expanduser(os.path.join("~", ".config")), exist_ok=True)
        except OSError:
            pass
        base = app.user_data_dir
    else:
        base = os.path.join(os.path.expanduser("~"), ".babybloom")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "bloom.db")


class Database:
    _instance = None

    def __init__(self):
        self.path = get_db_path()
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _create_tables(self):
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS sugar_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,          -- YYYY-MM-DD
                slot TEXT NOT NULL,              -- one of SUGAR_SLOTS
                value REAL,                      -- mg/dL
                reading_time TEXT,               -- HH:MM
                previous_meal_time TEXT,          -- HH:MM
                fasting INTEGER DEFAULT 0,        -- 0/1
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                name TEXT NOT NULL,
                dosage TEXT,
                scheduled_time TEXT,
                taken INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                title TEXT NOT NULL,
                event_type TEXT DEFAULT 'appointment',  -- appointment/scan/reminder/other
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Generic key/value settings table so new features can persist
        # small bits of state without a schema migration.
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS vitals_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,          -- YYYY-MM-DD
                vital_type TEXT NOT NULL,        -- one of VITAL_TYPES keys (BP/O2/Pulse/Weight)
                value1 REAL,                     -- systolic for BP, else the single value
                value2 REAL,                     -- diastolic for BP only, else NULL
                reading_time TEXT,               -- e.g. "09:47 AM"
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS consultation_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    # ---------------- Sugar log ----------------

    def add_sugar_reading(self, log_date, slot, value, reading_time,
                           previous_meal_time, fasting, notes=""):
        self.conn.execute(
            """INSERT INTO sugar_log
               (log_date, slot, value, reading_time, previous_meal_time, fasting, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_date, slot, value, reading_time, previous_meal_time,
             1 if fasting else 0, notes),
        )
        self.conn.commit()

    def update_sugar_reading(self, entry_id, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [entry_id]
        self.conn.execute(f"UPDATE sugar_log SET {cols} WHERE id = ?", values)
        self.conn.commit()

    def delete_sugar_reading(self, entry_id):
        self.conn.execute("DELETE FROM sugar_log WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_sugar_for_date(self, log_date):
        cur = self.conn.execute(
            "SELECT * FROM sugar_log WHERE log_date = ? ORDER BY id", (log_date,)
        )
        return _rows_to_dicts(cur)

    def get_sugar_range(self, start_date, end_date):
        cur = self.conn.execute(
            """SELECT * FROM sugar_log WHERE log_date BETWEEN ? AND ?
               ORDER BY log_date, id""",
            (start_date, end_date),
        )
        return _rows_to_dicts(cur)

    def get_all_sugar(self):
        cur = self.conn.execute("SELECT * FROM sugar_log ORDER BY log_date, id")
        return _rows_to_dicts(cur)

    # ---------------- Medications ----------------

    def add_medication(self, log_date, name, dosage, scheduled_time, notes=""):
        self.conn.execute(
            """INSERT INTO medications (log_date, name, dosage, scheduled_time, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (log_date, name, dosage, scheduled_time, notes),
        )
        self.conn.commit()

    def set_medication_taken(self, med_id, taken=True):
        self.conn.execute(
            "UPDATE medications SET taken = ? WHERE id = ?", (1 if taken else 0, med_id)
        )
        self.conn.commit()

    def delete_medication(self, med_id):
        self.conn.execute("DELETE FROM medications WHERE id = ?", (med_id,))
        self.conn.commit()

    def get_medications_for_date(self, log_date):
        cur = self.conn.execute(
            "SELECT * FROM medications WHERE log_date = ? ORDER BY scheduled_time",
            (log_date,),
        )
        return _rows_to_dicts(cur)

    # ---------------- Calendar events ----------------

    def add_event(self, event_date, title, event_type="appointment", notes=""):
        self.conn.execute(
            """INSERT INTO calendar_events (event_date, title, event_type, notes)
               VALUES (?, ?, ?, ?)""",
            (event_date, title, event_type, notes),
        )
        self.conn.commit()

    def delete_event(self, event_id):
        self.conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        self.conn.commit()

    def get_events_for_date(self, event_date):
        cur = self.conn.execute(
            "SELECT * FROM calendar_events WHERE event_date = ? ORDER BY id",
            (event_date,),
        )
        return _rows_to_dicts(cur)

    def get_events_for_month(self, year, month):
        prefix = f"{year:04d}-{month:02d}"
        cur = self.conn.execute(
            "SELECT * FROM calendar_events WHERE event_date LIKE ? ORDER BY event_date",
            (f"{prefix}%",),
        )
        return _rows_to_dicts(cur)

    # ---------------- Vitals (BP / O2 / Pulse / Weight) ----------------

    def add_vital_reading(self, log_date, vital_type, value1, value2, reading_time, notes=""):
        self.conn.execute(
            """INSERT INTO vitals_log (log_date, vital_type, value1, value2, reading_time, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (log_date, vital_type, value1, value2, reading_time, notes),
        )
        self.conn.commit()

    def update_vital_reading(self, entry_id, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [entry_id]
        self.conn.execute(f"UPDATE vitals_log SET {cols} WHERE id = ?", values)
        self.conn.commit()

    def delete_vital_reading(self, entry_id):
        self.conn.execute("DELETE FROM vitals_log WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_vitals_for_date(self, log_date):
        cur = self.conn.execute(
            "SELECT * FROM vitals_log WHERE log_date = ? ORDER BY id", (log_date,)
        )
        return _rows_to_dicts(cur)

    def get_vitals_range(self, start_date, end_date):
        cur = self.conn.execute(
            """SELECT * FROM vitals_log WHERE log_date BETWEEN ? AND ?
               ORDER BY log_date, id""",
            (start_date, end_date),
        )
        return _rows_to_dicts(cur)

    def get_all_vitals(self):
        cur = self.conn.execute("SELECT * FROM vitals_log ORDER BY log_date, id")
        return _rows_to_dicts(cur)

    # ---------------- Consultation notes ----------------

    def add_consultation_note(self, log_date, notes):
        self.conn.execute(
            "INSERT INTO consultation_notes (log_date, notes) VALUES (?, ?)",
            (log_date, notes),
        )
        self.conn.commit()

    def delete_consultation_note(self, note_id):
        self.conn.execute("DELETE FROM consultation_notes WHERE id = ?", (note_id,))
        self.conn.commit()

    def get_consultation_notes_for_date(self, log_date):
        cur = self.conn.execute(
            "SELECT * FROM consultation_notes WHERE log_date = ? ORDER BY id",
            (log_date,),
        )
        return _rows_to_dicts(cur)

    def get_all_consultation_notes(self):
        cur = self.conn.execute("SELECT * FROM consultation_notes ORDER BY log_date, id")
        return _rows_to_dicts(cur)

    # ---------------- Settings ----------------

    def get_setting(self, key, default=None):
        cur = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()


def _rows_to_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def now_hhmm():
    return datetime.now().strftime("%H:%M")
