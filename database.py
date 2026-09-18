import sqlite3
import asyncio

DB_PATH = "stake_del.db"


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            attempts INTEGER DEFAULT 0,
            ref_count INTEGER DEFAULT 0,
            last_free TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snos_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            target_type TEXT,
            target_link TEXT,
            chance INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            can_manage_admins INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE,
            channel_link TEXT,
            added_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ===== USERS =====
def _get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def _create_user(user_id, username="", attempts=0):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, attempts) VALUES (?, ?, ?)",
        (user_id, username, attempts)
    )
    conn.commit()
    conn.close()


def _add_attempts(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET attempts = attempts + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def _remove_attempts(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET attempts = MAX(0, attempts - ?) WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def _set_attempts(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET attempts = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def _get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT user_id, username, attempts, is_banned, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def _get_user_by_username(username):
    if not username:
        return None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (username.lower(),))
    row = cur.fetchone()
    conn.close()
    return row


def _ban_user(user_id, ban=True):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id))
    conn.commit()
    conn.close()


def _update_last_free(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET last_free = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def _get_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM snos_orders")
    total_orders = cur.fetchone()[0]
    conn.close()
    return total_users, total_orders


# ===== SNOS ORDERS =====
def _create_snos_order(user_id, username, target_type, target_link, chance):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO snos_orders (user_id, username, target_type, target_link, chance) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, target_type, target_link, chance)
    )
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return oid


def _get_snos_orders(limit=20):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT * FROM snos_orders ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ===== REFERRALS =====
def _save_referral(referrer_id, referred_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def _get_referral(referred_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
    row = cur.fetchone()
    conn.close()
    return row


def _mark_referral_paid(referred_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE referrals SET paid = 1 WHERE referred_id = ?", (referred_id,))
    conn.commit()
    conn.close()


def _get_ref_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND paid = 1", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def _update_ref_count(user_id, count):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET ref_count = ? WHERE user_id = ?", (count, user_id))
    conn.commit()
    conn.close()


# ===== ADMINS =====
def _add_admin(user_id, added_by, can_manage=0):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO admins (user_id, added_by, can_manage_admins) VALUES (?, ?, ?)",
            (user_id, added_by, can_manage)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def _get_all_admins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT user_id, added_by, can_manage_admins FROM admins")
    rows = cur.fetchall()
    conn.close()
    return rows


def _remove_admin(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def _is_admin_db(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


# ===== CHANNELS =====
def _add_channel(channel_id, channel_link, added_by):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO channels (channel_id, channel_link, added_by) VALUES (?, ?, ?)",
            (channel_id, channel_link, added_by)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def _get_all_channels():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT channel_id, channel_link FROM channels")
    rows = cur.fetchall()
    conn.close()
    return rows


def _remove_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()


# ===== ASYNC ОБЁРТКИ =====
async def init_db():
    await asyncio.to_thread(_init_db)


async def get_user(user_id):
    return await asyncio.to_thread(_get_user, user_id)


async def create_user(user_id, username="", attempts=0):
    await asyncio.to_thread(_create_user, user_id, username, attempts)


async def add_attempts(user_id, amount):
    await asyncio.to_thread(_add_attempts, user_id, amount)


async def remove_attempts(user_id, amount):
    await asyncio.to_thread(_remove_attempts, user_id, amount)


async def set_attempts(user_id, amount):
    await asyncio.to_thread(_set_attempts, user_id, amount)


async def get_all_users():
    return await asyncio.to_thread(_get_all_users)


async def get_user_by_username(username):
    return await asyncio.to_thread(_get_user_by_username, username)


async def ban_user(user_id, ban=True):
    await asyncio.to_thread(_ban_user, user_id, ban)


async def update_last_free(user_id):
    await asyncio.to_thread(_update_last_free, user_id)


async def get_stats():
    return await asyncio.to_thread(_get_stats)


async def create_snos_order(user_id, username, target_type, target_link, chance):
    return await asyncio.to_thread(_create_snos_order, user_id, username, target_type, target_link, chance)


async def get_snos_orders(limit=20):
    return await asyncio.to_thread(_get_snos_orders, limit)


async def save_referral(referrer_id, referred_id):
    return await asyncio.to_thread(_save_referral, referrer_id, referred_id)


async def get_referral(referred_id):
    return await asyncio.to_thread(_get_referral, referred_id)


async def mark_referral_paid(referred_id):
    await asyncio.to_thread(_mark_referral_paid, referred_id)


async def get_ref_count(user_id):
    return await asyncio.to_thread(_get_ref_count, user_id)


async def update_ref_count(user_id, count):
    await asyncio.to_thread(_update_ref_count, user_id, count)


async def add_admin(user_id, added_by, can_manage=0):
    return await asyncio.to_thread(_add_admin, user_id, added_by, can_manage)


async def get_all_admins():
    return await asyncio.to_thread(_get_all_admins)


async def remove_admin(user_id):
    await asyncio.to_thread(_remove_admin, user_id)


async def is_admin_db(user_id):
    return await asyncio.to_thread(_is_admin_db, user_id)


async def add_channel(channel_id, channel_link, added_by):
    return await asyncio.to_thread(_add_channel, channel_id, channel_link, added_by)


async def get_all_channels():
    return await asyncio.to_thread(_get_all_channels)


async def remove_channel(channel_id):
    await asyncio.to_thread(_remove_channel, channel_id)
