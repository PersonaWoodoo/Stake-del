from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PRIVACY_URL, RULES_URL


def privacy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Политика конфиденциальности", url=PRIVACY_URL, style="danger")],
        [InlineKeyboardButton(text="📜 Правила использования", url=RULES_URL, style="danger")],
        [InlineKeyboardButton(text="✅ Подтверждаю", callback_data="accept_privacy", style="success")],
    ])


def subscribe_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/stake_del", style="primary")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub", style="success")],
    ])


def captcha_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я не робот", callback_data="captcha_pass", style="success")],
    ])


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать снос", callback_data="snos_start", style="success")],
        [
            InlineKeyboardButton(text="💎 Мои попытки", callback_data="my_attempts", style="primary"),
            InlineKeyboardButton(text="💰 Купить попытку", callback_data="buy_attempt", style="primary"),
        ],
        [
            InlineKeyboardButton(text="🎁 Рефералы", callback_data="refs", style="success"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile", style="primary"),
        ],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help", style="primary")],
    ])


def snos_type_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Канал / Чат", callback_data="snos_channel", style="primary")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="snos_account", style="primary")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main", style="danger")],
    ])


def confirm_snos_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="snos_confirm", style="success")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main", style="danger")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main", style="danger")],
    ])


def cancel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main", style="danger")],
    ])


def buy_attempt_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить 1 попытку — 5 звёзд", callback_data="pay_attempt", style="success")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main", style="danger")],
    ])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats", style="primary")],
        [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_orders", style="primary")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users", style="primary")],
        [InlineKeyboardButton(text="📢 Добавить канал", callback_data="admin_add_channel", style="success")],
        [InlineKeyboardButton(text="👑 Добавить админа", callback_data="admin_add_admin", style="success")],
        [InlineKeyboardButton(text="💎 Выдать попытки", callback_data="admin_give_att", style="primary")],
        [InlineKeyboardButton(text="➖ Забрать попытки", callback_data="admin_take_att", style="danger")],
        [InlineKeyboardButton(text="🎁 Выдать всем", callback_data="admin_give_all", style="primary")],
        [InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban", style="danger")],
        [InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban", style="success")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="back_main", style="danger")],
    ])


def broadcast_confirm_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ссылку", callback_data="bc_add_link", style="primary")],
        [InlineKeyboardButton(text="✅ Отправить", callback_data="bc_send", style="success")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="bc_cancel", style="danger")],
    ])


def broadcast_links_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="bc_add_link", style="primary")],
        [InlineKeyboardButton(text="✅ Отправить", callback_data="bc_send", style="success")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="bc_cancel", style="danger")],
    ])
