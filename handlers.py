import secrets
import asyncio
import random
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    PreCheckoutQuery, LabeledPrice,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import (
    ADMIN_IDS, CHANNEL_ID, CHANNEL_LINK, ORDERS_CHANNEL_ID,
    STARS_PER_ATTEMPT, REFS_PER_ATTEMPT, START_ATTEMPTS,
)
from database import (
    init_db, get_user, create_user, add_attempts, remove_attempts, set_attempts,
    get_all_users, get_user_by_username, ban_user, update_last_free, get_stats,
    create_snos_order, get_snos_orders, save_referral, get_referral,
    mark_referral_paid, get_ref_count, update_ref_count,
    add_admin, get_all_admins, remove_admin, is_admin_db,
    add_channel, get_all_channels, remove_channel,
)
from keyboards import (
    subscribe_menu, captcha_menu, main_menu, snos_type_menu, confirm_snos_menu,
    back_menu, cancel_menu, buy_attempt_menu, admin_menu,
)
from states import CaptchaStates, SnosStates, AdminStates

import emojis as E

router = Router()

SNOS_ANIMATION_TOTAL = 200
SNOS_ANIMATION_DELAY = 0.075  # 200 * 0.075 = 15 секунд


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


async def is_admin_full(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return True
    return await is_admin_db(uid)


# ========== ПОДПИСКА ==========
async def check_subscription(bot: Bot, user_id: int) -> bool:
    # Проверка основного канала
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status not in ("member", "administrator", "creator"):
            return False
    except Exception:
        return False

    # Проверка доп. каналов из БД
    channels = await get_all_channels()
    for ch_id, _ in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            continue

    return True


async def require_sub(message: Message, bot: Bot) -> bool:
    if not await check_subscription(bot, message.from_user.id):
        await message.answer(
            f"{E.SUBSCRIBE} <b>Подпишись на канал:</b>\n\n👉 {CHANNEL_LINK}",
            parse_mode="HTML", reply_markup=subscribe_menu()
        )
        return False
    return True


async def require_sub_cb(call: CallbackQuery, bot: Bot) -> bool:
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Подпишись на канал!", show_alert=True)
        return False
    return True


# ========== START ==========
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    user = await get_user(message.from_user.id)

    if not user:
        await create_user(message.from_user.id, message.from_user.username or "", START_ATTEMPTS)

        args = message.text.split(maxsplit=1)
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                ref_id = int(args[1].replace("ref_", ""))
                if ref_id != message.from_user.id:
                    await save_referral(ref_id, message.from_user.id)
            except Exception:
                pass

        if not await check_subscription(bot, message.from_user.id):
            await message.answer(
                f"{E.ROCKET} <b>Добро пожаловать в Stake Del!</b>\n\n"
                f"{E.SUBSCRIBE} <b>Подпишись на канал:</b>\n\n👉 {CHANNEL_LINK}",
                parse_mode="HTML", reply_markup=subscribe_menu()
            )
            return

        # Проверка реферального бонуса
        await try_pay_ref_bonus(message.from_user.id, bot)

        await message.answer(
            f"{E.ROCKET} <b>Добро пожаловать!</b>\n\n"
            f"{E.GIFT} Тебе начислено: <b>{START_ATTEMPTS} попытка</b>\n\n"
            f"Выбирай действие 👇",
            parse_mode="HTML", reply_markup=main_menu()
        )
        return

    if user[5] == 1:
        await message.answer(f"{E.BAN} Ты забанен.", parse_mode="HTML")
        return

    if not await check_subscription(bot, message.from_user.id):
        await message.answer(
            f"{E.SUBSCRIBE} <b>Подпишись на канал:</b>\n\n👉 {CHANNEL_LINK}",
            parse_mode="HTML", reply_markup=subscribe_menu()
        )
        return

    await try_pay_ref_bonus(message.from_user.id, bot)

    await message.answer(
        f"{E.ROCKET} <b>Главное меню</b>",
        parse_mode="HTML", reply_markup=main_menu()
    )


async def try_pay_ref_bonus(user_id: int, bot: Bot):
    ref = await get_referral(user_id)
    if not ref:
        return
    referrer_id = ref[1]
    paid = ref[3]
    if paid == 1:
        return

    if not await check_subscription(bot, user_id):
        return

    await mark_referral_paid(user_id)
    count = await get_ref_count(referrer_id)
    await update_ref_count(referrer_id, count)

    # Каждые REFS_PER_ATTEMPT рефералов = +1 попытка
    if count % REFS_PER_ATTEMPT == 0:
        await add_attempts(referrer_id, 1)
        try:
            await bot.send_message(
                referrer_id,
                f"{E.BONUS} <b>+1 попытка за {REFS_PER_ATTEMPT} рефералов!</b>\n\n"
                f"{E.REFERRALS} Всего рефералов: <b>{count}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data == "check_sub")
async def check_sub_cb(call: CallbackQuery, bot: Bot):
    if await check_subscription(bot, call.from_user.id):
        await try_pay_ref_bonus(call.from_user.id, bot)
        await call.message.edit_text(
            f"{E.SUCCESS} <b>Подписка подтверждена!</b>",
            parse_mode="HTML", reply_markup=main_menu()
        )
    else:
        await call.answer("❌ Ты ещё не подписался!", show_alert=True)


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except Exception:
        pass
    try:
        await call.message.answer(
            f"{E.ROCKET} <b>Главное меню</b>",
            parse_mode="HTML", reply_markup=main_menu()
        )
    except Exception:
        pass


# ========== МОИ ПОПЫТКИ ==========
@router.callback_query(F.data == "my_attempts")
async def my_attempts(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    user = await get_user(cb.from_user.id)
    attempts = user[2] if user else 0
    text = (
        f"{E.BALANCE} <b>Мои попытки</b>\n\n"
        f"{E.STARS} Доступно попыток: <b>{attempts}</b>\n\n"
        f"💡 1 попытка = 1 снос\n"
        f"{E.STARS} Стоимость: <b>{STARS_PER_ATTEMPT} звёзд</b>\n"
        f"{E.REFERRALS} Или {REFS_PER_ATTEMPT} рефералов = +1 попытка"
    )
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=back_menu())


# ========== КУПИТЬ ПОПЫТКУ ==========
@router.callback_query(F.data == "buy_attempt")
async def buy_attempt(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    text = (
        f"{E.STARS} <b>Купить попытку</b>\n\n"
        f"1 попытка = <b>{STARS_PER_ATTEMPT} звёзд</b>\n\n"
        f"После оплаты попытка зачислится автоматически."
    )
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=buy_attempt_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=buy_attempt_menu())


@router.callback_query(F.data == "pay_attempt")
async def pay_attempt_cb(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    try:
        await bot.send_invoice(
            chat_id=cb.from_user.id,
            title="Покупка попытки сноса",
            description=f"1 попытка сноса за {STARS_PER_ATTEMPT} звёзд",
            payload=f"attempt_{cb.from_user.id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Попытка", amount=STARS_PER_ATTEMPT)],
        )
        await cb.answer("⭐ Оплати счёт выше")
    except Exception as e:
        await cb.answer(f"Ошибка: {e}", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    if not payment:
        return
    payload = payment.invoice_payload

    if payload.startswith("attempt_"):
        try:
            user_id = int(payload.replace("attempt_", ""))
        except Exception:
            user_id = message.from_user.id

        await add_attempts(user_id, 1)
        user = await get_user(user_id)
        attempts = user[2] if user else 0

        await message.answer(
            f"{E.SUCCESS} <b>Оплата получена!</b>\n\n"
            f"{E.PLUS} +1 попытка\n"
            f"{E.BALANCE} Всего попыток: <b>{attempts}</b>",
            parse_mode="HTML", reply_markup=main_menu()
        )


# ========== РЕФЕРАЛЫ ==========
@router.callback_query(F.data == "refs")
async def refs_cb(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{cb.from_user.id}"
    count = await get_ref_count(cb.from_user.id)

    text = (
        f"{E.REFERRALS} <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей — получай попытки!\n"
        f"<b>{REFS_PER_ATTEMPT} рефералов</b> = <b>+1 попытка</b>\n\n"
        f"{E.USERS} Приглашено: <b>{count}</b>\n"
        f"{E.GIFT} До бонуса: <b>{REFS_PER_ATTEMPT - (count % REFS_PER_ATTEMPT)}</b>\n\n"
        f"{E.LINK} Твоя ссылка:\n<code>{ref_link}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={ref_link}", style="success")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main", style="danger")],
    ])

    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)


# ========== ПРОФИЛЬ ==========
@router.callback_query(F.data == "profile")
async def profile_cb(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Профиль не найден")
        return

    attempts = user[2]
    ref_count = user[3]

    text = (
        f"{E.PROFILE} <b>Профиль</b>\n\n"
        f"👤 @{cb.from_user.username or cb.from_user.id}\n"
        f"🆔 ID: <code>{cb.from_user.id}</code>\n\n"
        f"{E.BALANCE} Попыток: <b>{attempts}</b>\n"
        f"{E.REFERRALS} Рефералов: <b>{ref_count}</b>"
    )

    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=back_menu())


# ========== ПОМОЩЬ ==========
@router.callback_query(F.data == "help")
async def help_cb(cb: CallbackQuery, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return
    text = (
        f"{E.HELP} <b>Помощь</b>\n\n"
        f"{E.ROCKET} Начать снос — выбрать цель\n"
        f"{E.BALANCE} Мои попытки — посмотреть\n"
        f"{E.STARS} Купить попытку — {STARS_PER_ATTEMPT} звёзд\n"
        f"{E.REFERRALS} Рефералы — {REFS_PER_ATTEMPT} рефов = +1\n\n"
        f"{E.SUBSCRIBE} Канал: {CHANNEL_LINK}"
    )
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=back_menu())


# ========== СНОС ==========
@router.callback_query(F.data == "snos_start")
async def snos_start(cb: CallbackQuery, state: FSMContext, bot: Bot):
    if not await require_sub_cb(cb, bot):
        return

    user = await get_user(cb.from_user.id)
    if user and user[5] == 1:
        await cb.answer("❌ Ты забанен", show_alert=True)
        return

    attempts = user[2] if user else 0
    if attempts <= 0:
        await cb.answer(f"❌ Нет попыток! Купи или пригласи рефералов.", show_alert=True)
        return

    await state.set_state(SnosStates.target_type)
    try:
        await cb.message.edit_text(
            f"{E.ROCKET} <b>Выберите раздел</b>\n\n"
            f"Что нужно снести?",
            parse_mode="HTML", reply_markup=snos_type_menu()
        )
    except Exception:
        await cb.message.answer(
            f"{E.ROCKET} <b>Выберите раздел</b>",
            parse_mode="HTML", reply_markup=snos_type_menu()
        )


@router.callback_query(F.data.startswith("snos_"), SnosStates.target_type)
async def snos_type_chosen(cb: CallbackQuery, state: FSMContext):
    if cb.data == "snos_channel":
        await state.update_data(target_type="Канал / Чат")
        await state.set_state(SnosStates.target_link)
        try:
            await cb.message.edit_text(
                f"📢 <b>Укажите @username или ссылку на канал/чат</b>\n\n"
                f"Например: <code>@channel</code> или <code>https://t.me/channel</code>",
                parse_mode="HTML", reply_markup=cancel_menu()
            )
        except Exception:
            await cb.message.answer(
                f"📢 <b>Укажите @username или ссылку:</b>",
                parse_mode="HTML", reply_markup=cancel_menu()
            )
        return

    if cb.data == "snos_account":
        await state.update_data(target_type="Аккаунт")
        await state.set_state(SnosStates.target_link)
        try:
            await cb.message.edit_text(
                f"👤 <b>Укажите @username аккаунта</b>\n\n"
                f"Например: <code>@username</code>",
                parse_mode="HTML", reply_markup=cancel_menu()
            )
        except Exception:
            await cb.message.answer(
                f"👤 <b>Укажите @username:</b>",
                parse_mode="HTML", reply_markup=cancel_menu()
            )
        return


@router.message(SnosStates.target_link)
async def snos_target_entered(message: Message, state: FSMContext, bot: Bot):
    target_link = message.text.strip()
    if len(target_link) < 3:
        await message.answer(
            f"{E.ERROR} Слишком короткий. Попробуй ещё раз.",
            parse_mode="HTML", reply_markup=cancel_menu()
        )
        return

    data = await state.get_data()
    target_type = data.get("target_type", "Канал / Чат")

    user = await get_user(message.from_user.id)
    attempts = user[2] if user else 0
    if attempts <= 0:
        await message.answer(
            f"{E.ERROR} У тебя нет попыток!",
            parse_mode="HTML", reply_markup=main_menu()
        )
        await state.clear()
        return

    # Списываем попытку
    await remove_attempts(message.from_user.id, 1)

    # Шанс сноса (30% или 70%)
    chance = random.choice([30, 70])

    # Создаём заявку
    order_id = await create_snos_order(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        target_type=target_type,
        target_link=target_link,
        chance=chance
    )

    # Анимация "работа идёт"
    anim_msg = await message.answer(
        f"<b>Работа идёт...</b>\n\n"
        f"<code>0/{SNOS_ANIMATION_TOTAL}</code>",
        parse_mode="HTML"
    )

    for i in range(1, SNOS_ANIMATION_TOTAL + 1):
        await asyncio.sleep(SNOS_ANIMATION_DELAY)
        if i % 10 == 0 or i == SNOS_ANIMATION_TOTAL:
            try:
                await anim_msg.edit_text(
                    f"<b>Работа идёт...</b>\n\n"
                    f"<code>{i}/{SNOS_ANIMATION_TOTAL}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # Финальный результат
    try:
        await anim_msg.edit_text(
            f"{E.SUCCESS} <b>Готово!</b>\n\n"
            f"Окончательное решение даст поддержка Telegram.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception:
        await message.answer(
            f"{E.SUCCESS} <b>Готово!</b>\n\n"
            f"Окончательное решение даст поддержка Telegram.",
            parse_mode="HTML", reply_markup=main_menu()
        )

    # Отправка в канал заявок
    now = datetime.now().strftime("%H:%M:%S")
    order_text = (
        f"{E.ROCKET} <b>Новая заявка на снос</b>\n\n"
        f"👤 Юзер: @{message.from_user.username or message.from_user.id} "
        f"(ID: <code>{message.from_user.id}</code>)\n"
        f"🎯 Цель: <code>{target_link}</code>\n"
        f"📢 Тип: <b>{target_type}</b>\n"
        f"🔥 Шанс сноса: <b>{chance}%</b>\n"
        f"⏰ Время: {now}\n"
        f"🆔 Заявка #{order_id}"
    )

    try:
        await bot.send_message(
            ORDERS_CHANNEL_ID,
            order_text,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки заявки: {e}")

    await state.clear()


# ========== АДМИНКА ==========
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not await is_admin_full(message.from_user.id):
        await message.answer(f"{E.ERROR} Нет доступа.", parse_mode="HTML")
        return
    await message.answer(
        f"{E.ADMIN} <b>Админ-панель Stake Del</b>",
        parse_mode="HTML", reply_markup=admin_menu()
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(cb: CallbackQuery):
    if not await is_admin_full(cb.from_user.id):
        return
    total_users, total_orders = await get_stats()
    text = (
        f"{E.STATS} <b>Статистика</b>\n\n"
        f"{E.USERS} Юзеров: <code>{total_users}</code>\n"
        f"{E.REQUESTS} Заявок: <code>{total_orders}</code>"
    )
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=admin_menu())


@router.callback_query(F.data == "admin_orders")
async def admin_orders(cb: CallbackQuery):
    if not await is_admin_full(cb.from_user.id):
        return
    orders = await get_snos_orders(20)
    if not orders:
        await cb.answer("📭 Нет заявок", show_alert=True)
        return
    text = f"{E.REQUESTS} <b>Последние 20 заявок</b>\n\n"
    for o in orders:
        oid, uid, uname, ttype, tlink, chance, status, created = o
        text += (
            f"#{oid} | @{uname or uid} | "
            f"{ttype}: <code>{tlink}</code> | "
            f"<b>{chance}%</b>\n"
        )
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=admin_menu())


@router.callback_query(F.data == "admin_users")
async def admin_users(cb: CallbackQuery):
    if not await is_admin_full(cb.from_user.id):
        return
    users = await get_all_users()
    text = f"{E.USERS} <b>Последние 20 юзеров</b>\n\n"
    for u in users[:20]:
        uid, uname, attempts, banned, created = u
        flag = E.BAN if banned else E.SUCCESS
        text += f"{flag} <code>{uid}</code> @{uname or '—'} — <b>{attempts}</b>\n"
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=admin_menu())


# ===== ДОБАВИТЬ КАНАЛ =====
@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.add_channel)
    await cb.message.edit_text(
        f"📢 <b>Добавить канал для подписки</b>\n\n"
        f"Отправь ID канала (например <code>-1001234567890</code>) "
        f"или ссылку <code>https://t.me/channel</code>",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.add_channel)
async def admin_add_channel_do(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin_full(message.from_user.id):
        return
    text = message.text.strip()

    channel_id = None
    channel_link = text

    if text.startswith("-100") or text.lstrip("-").isdigit():
        try:
            channel_id = int(text)
        except Exception:
            pass
    elif "t.me/" in text:
        username = text.split("t.me/")[-1].strip("/")
        channel_link = f"https://t.me/{username}"
        try:
            chat = await bot.get_chat(f"@{username}")
            channel_id = chat.id
        except Exception as e:
            await message.answer(
                f"{E.ERROR} Не удалось получить ID канала: {e}\n\n"
                f"Попробуй отправить числовой ID.",
                parse_mode="HTML", reply_markup=cancel_menu()
            )
            return

    if not channel_id:
        await message.answer(
            f"{E.ERROR} Не удалось определить ID канала.",
            parse_mode="HTML", reply_markup=cancel_menu()
        )
        return

    ok = await add_channel(channel_id, channel_link, message.from_user.id)
    await state.clear()

    if ok:
        await message.answer(
            f"{E.SUCCESS} <b>Канал добавлен!</b>\n\n"
            f"ID: <code>{channel_id}</code>\n"
            f"Ссылка: {channel_link}",
            parse_mode="HTML", reply_markup=admin_menu()
        )
    else:
        await message.answer(
            f"{E.ERROR} Канал уже добавлен.",
            parse_mode="HTML", reply_markup=admin_menu()
        )


# ===== ДОБАВИТЬ АДМИНА =====
@router.callback_query(F.data == "admin_add_admin")
async def admin_add_admin(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Только главный админ может добавлять админов", show_alert=True)
        return
    await state.set_state(AdminStates.add_admin)
    await cb.message.edit_text(
        f"👑 <b>Добавить админа</b>\n\n"
        f"Отправь ID юзера или @username",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.add_admin)
async def admin_add_admin_do(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.strip()
    target_id = None

    if text.startswith("@"):
        user = await get_user_by_username(text[1:])
        if user:
            target_id = user[0]
    else:
        try:
            target_id = int(text)
        except Exception:
            pass

    if not target_id:
        await message.answer(
            f"{E.ERROR} Юзер не найден в БД.",
            parse_mode="HTML", reply_markup=cancel_menu()
        )
        return

    ok = await add_admin(target_id, message.from_user.id, can_manage=0)
    await state.clear()

    if ok:
        await message.answer(
            f"{E.SUCCESS} <b>Админ добавлен!</b>\n\n"
            f"ID: <code>{target_id}</code>\n"
            f"⚠️ Он НЕ может выдавать/забирать админку.",
            parse_mode="HTML", reply_markup=admin_menu()
        )
    else:
        await message.answer(
            f"{E.ERROR} Уже админ.",
            parse_mode="HTML", reply_markup=admin_menu()
        )


# ===== ВЫДАТЬ ПОПЫТКИ =====
@router.callback_query(F.data == "admin_give_att")
async def admin_give_att(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.give_attempts_user)
    await cb.message.edit_text(
        f"{E.PLUS} <b>Выдать попытки</b>\n\n"
        f"Отправь ID или @username юзера",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.give_attempts_user)
async def admin_give_att_user(message: Message, state: FSMContext):
    if not await is_admin_full(message.from_user.id):
        return
    text = message.text.strip()
    target_id = None

    if text.startswith("@"):
        user = await get_user_by_username(text[1:])
        if user:
            target_id = user[0]
    else:
        try:
            target_id = int(text)
        except Exception:
            pass

    if not target_id:
        await message.answer(f"{E.ERROR} Не найден.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    await state.update_data(target=target_id)
    await state.set_state(AdminStates.give_attempts_amount)
    await message.answer(
        f"👤 ID: <code>{target_id}</code>\n\nСколько попыток выдать?",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.give_attempts_amount)
async def admin_give_att_amount(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin_full(message.from_user.id):
        return
    try:
        amount = int(message.text.strip())
    except Exception:
        await message.answer(f"{E.ERROR} Введи число.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    data = await state.get_data()
    target = data["target"]
    await add_attempts(target, amount)
    await state.clear()

    await message.answer(
        f"{E.SUCCESS} Выдано <b>{amount}</b> попыток юзеру <code>{target}</code>",
        parse_mode="HTML", reply_markup=admin_menu()
    )
    try:
        await bot.send_message(
            target,
            f"{E.GIFT} Тебе выдано <b>{amount}</b> попыток!",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ===== ЗАБРАТЬ ПОПЫТКИ =====
@router.callback_query(F.data == "admin_take_att")
async def admin_take_att(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.take_attempts_user)
    await cb.message.edit_text(
        f"{E.MINUS} <b>Забрать попытки</b>\n\n"
        f"Отправь ID или @username",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.take_attempts_user)
async def admin_take_att_user(message: Message, state: FSMContext):
    if not await is_admin_full(message.from_user.id):
        return
    text = message.text.strip()
    target_id = None

    if text.startswith("@"):
        user = await get_user_by_username(text[1:])
        if user:
            target_id = user[0]
    else:
        try:
            target_id = int(text)
        except Exception:
            pass

    if not target_id:
        await message.answer(f"{E.ERROR} Не найден.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    await state.update_data(target=target_id)
    await state.set_state(AdminStates.take_attempts_amount)
    await message.answer(
        f"👤 ID: <code>{target_id}</code>\n\nСколько забрать?",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.take_attempts_amount)
async def admin_take_att_amount(message: Message, state: FSMContext):
    if not await is_admin_full(message.from_user.id):
        return
    try:
        amount = int(message.text.strip())
    except Exception:
        await message.answer(f"{E.ERROR} Введи число.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    data = await state.get_data()
    target = data["target"]
    await remove_attempts(target, amount)
    await state.clear()

    await message.answer(
        f"{E.SUCCESS} Забрано <b>{amount}</b> попыток у <code>{target}</code>",
        parse_mode="HTML", reply_markup=admin_menu()
    )


# ===== ВЫДАТЬ ВСЕМ =====
@router.callback_query(F.data == "admin_give_all")
async def admin_give_all(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.give_all_amount)
    await cb.message.edit_text(
        f"{E.GIFT} <b>Выдать всем</b>\n\nСколько попыток выдать каждому?",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.give_all_amount)
async def admin_give_all_amount(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin_full(message.from_user.id):
        return
    try:
        amount = int(message.text.strip())
    except Exception:
        await message.answer(f"{E.ERROR} Введи число.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    users = await get_all_users()
    for u in users:
        await add_attempts(u[0], amount)

    await state.clear()
    await message.answer(
        f"{E.SUCCESS} Выдано <b>{amount}</b> попыток всем юзерам ({len(users)})",
        parse_mode="HTML", reply_markup=admin_menu()
    )


# ===== БАН =====
@router.callback_query(F.data == "admin_ban")
async def admin_ban(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.ban_user)
    await cb.message.edit_text(
        f"{E.BAN} <b>Бан</b>\n\nID или @username",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.ban_user)
async def admin_ban_do(message: Message, state: FSMContext):
    if not await is_admin_full(message.from_user.id):
        return
    text = message.text.strip()
    target_id = None

    if text.startswith("@"):
        user = await get_user_by_username(text[1:])
        if user:
            target_id = user[0]
    else:
        try:
            target_id = int(text)
        except Exception:
            pass

    if not target_id:
        await message.answer(f"{E.ERROR} Не найден.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    await ban_user(target_id, True)
    await state.clear()
    await message.answer(
        f"{E.SUCCESS} Юзер <code>{target_id}</code> забанен",
        parse_mode="HTML", reply_markup=admin_menu()
    )


# ===== РАЗБАН =====
@router.callback_query(F.data == "admin_unban")
async def admin_unban(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.unban_user)
    await cb.message.edit_text(
        f"{E.UNBAN} <b>Разбан</b>\n\nID или @username",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.unban_user)
async def admin_unban_do(message: Message, state: FSMContext):
    if not await is_admin_full(message.from_user.id):
        return
    text = message.text.strip()
    target_id = None

    if text.startswith("@"):
        user = await get_user_by_username(text[1:])
        if user:
            target_id = user[0]
    else:
        try:
            target_id = int(text)
        except Exception:
            pass

    if not target_id:
        await message.answer(f"{E.ERROR} Не найден.", parse_mode="HTML", reply_markup=cancel_menu())
        return

    await ban_user(target_id, False)
    await state.clear()
    await message.answer(
        f"{E.SUCCESS} Юзер <code>{target_id}</code> разбанен",
        parse_mode="HTML", reply_markup=admin_menu()
    )


# ===== РАССЫЛКА =====
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(cb: CallbackQuery, state: FSMContext):
    if not await is_admin_full(cb.from_user.id):
        return
    await state.set_state(AdminStates.broadcast)
    await cb.message.edit_text(
        f"{E.BROADCAST} <b>Рассылка</b>\n\nОтправь текст",
        parse_mode="HTML", reply_markup=cancel_menu()
    )


@router.message(AdminStates.broadcast)
async def admin_broadcast_do(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin_full(message.from_user.id):
        return
    users = await get_all_users()
    ok, fail = 0, 0
    for u in users:
        try:
            await bot.send_message(u[0], message.text, parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
    await state.clear()
    await message.answer(
        f"{E.SUCCESS} Доставлено: <b>{ok}</b>, ошибок: <b>{fail}</b>",
        parse_mode="HTML", reply_markup=admin_menu()
    )
