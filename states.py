from aiogram.fsm.state import State, StatesGroup


class CaptchaStates(StatesGroup):
    waiting = State()


class SnosStates(StatesGroup):
    target_type = State()
    target_link = State()


class AdminStates(StatesGroup):
    add_channel = State()
    add_admin = State()
    give_attempts_user = State()
    give_attempts_amount = State()
    take_attempts_user = State()
    take_attempts_amount = State()
    give_all_amount = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
