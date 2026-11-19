import asyncio
import logging
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
from config import ADMIN_IDS, ALLOW_ALL_MEMBERS, BOT_TOKEN, CHANNEL_ID, TEAM_NAME

router = Router()
BOT_USERNAME = ""


# ───────────────────────── состояния ─────────────────────────
class Apply(StatesGroup):
    nickname = State()
    age = State()
    experience = State()
    equipment = State()
    hours = State()
    source = State()
    confirm = State()


class AdminWrite(StatesGroup):
    text = State()


# ───────────────────────── клавиатуры ─────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Подать заявку", callback_data="apply")
    kb.button(text="ℹ️ О нас", callback_data="about")
    kb.button(text="🤝 Моя реферальная ссылка", callback_data="ref")
    kb.adjust(1)
    return kb.as_markup()


def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data=f"{prefix}:Да")
    kb.button(text="Нет", callback_data=f"{prefix}:Нет")
    kb.button(text="✖️ Отмена", callback_data="cancel")
    kb.adjust(2, 1)
    return kb.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✖️ Отмена", callback_data="cancel")]])


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Отправить", callback_data="send_app")
    kb.button(text="🔄 Заполнить заново", callback_data="apply")
    kb.button(text="✖️ Отмена", callback_data="cancel")
    kb.adjust(1)
    return kb.as_markup()


def review_kb(app_id: int, with_decision: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if with_decision:
        rows.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{app_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{app_id}"),
        ])
    rows.append([InlineKeyboardButton(
        text="✉️ Написать кандидату", url=f"https://t.me/{BOT_USERNAME}?start=write_{app_id}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ───────────────────────── тексты ─────────────────────────
def welcome_text(name: str) -> str:
    return (
        f"🔻 <b>{TEAM_NAME}</b>\n\n"
        f"Привет, <b>{escape(name)}</b>! 👋\n\n"
        "Здесь можно подать заявку в команду. Ответь на несколько вопросов — "
        "анкета уйдёт на рассмотрение, и тебе придёт ответ прямо сюда."
    )


def application_text(app, user_id: int) -> str:
    return (
        f"🔻 <b>{TEAM_NAME} / ЗАЯВКА #{app['id']}</b>\n\n"
        f"👤 {escape(app['nickname'])}\n"
        f"🆔 Telegram: <a href=\"tg://user?id={user_id}\">{user_id}</a>\n"
        f"🎂 Возраст: {app['age']}\n"
        f"💼 Опыт в сфере: {escape(app['experience'])}\n"
        f"🎧 Discord, CS2, микрофон: {escape(app['equipment'])}\n"
        f"⏱ Время на работу: {escape(app['hours'])}\n"
        f"🤝 Реферальный код: {escape(app['ref_code'])}\n"
        f"📯 Откуда про нас узнали: {escape(app['source'])}"
    )


def preview_text(data: dict) -> str:
    return (
        "📋 <b>Проверь анкету:</b>\n\n"
        f"👤 Ник: {escape(data['nickname'])}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"💼 Опыт в сфере: {data['experience']}\n"
        f"🎧 Discord, CS2, микрофон: {data['equipment']}\n"
        f"⏱ Время на работу: {escape(data['hours'])}\n"
        f"📯 Откуда узнал: {escape(data['source'])}\n\n"
        "Всё верно?"
    )


def admin_tag(user) -> str:
    return f"@{user.username}" if user.username else escape(user.full_name)


async def is_admin(bot: Bot, user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    if ADMIN_IDS and not ALLOW_ALL_MEMBERS:
        return False
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
    except Exception:
        return False
    allowed = [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    if ALLOW_ALL_MEMBERS:
        allowed.append(ChatMemberStatus.MEMBER)
        # ограниченный (restricted) участник, который всё ещё в группе
        if member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False):
            return True
    return member.status in allowed


# ───────────────────────── старт / меню ─────────────────────────
@router.message(CommandStart(deep_link=True, magic=F.args.startswith("write_")))
async def start_write(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    """Админ нажал «Написать кандидату» в канале → попал сюда."""
    if not await is_admin(bot, message.from_user.id):
        return await message.answer("⛔️ Нет доступа.")
    try:
        app = db.get_application(int(command.args.split("_", 1)[1]))
    except ValueError:
        app = None
    if not app:
        return await message.answer("Заявка не найдена.")
    await state.set_state(AdminWrite.text)
    await state.update_data(target_id=app["user_id"], app_id=app["id"])
    await message.answer(
        f"✉️ Пишешь кандидату по заявке <b>#{app['id']}</b> ({escape(app['nickname'])}).\n"
        "Отправь сообщение (текст, фото, голос — что угодно). /cancel — отмена."
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    invited_by = command.args if command.args and command.args.startswith("RF-") else None
    db.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name, invited_by)
    await message.answer(welcome_text(message.from_user.first_name), reply_markup=main_menu_kb())


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.callback_query(F.data == "cancel")
async def cancel_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Отменено. Возвращайся, когда будешь готов 🙂", reply_markup=main_menu_kb())


@router.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        f"🔻 <b>{TEAM_NAME}</b>\n\n"
        "Тут описание команды: чем занимаетесь, кого ищете, условия.\n"
        "(поменяй текст в bot.py → функция about)",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "ref")
async def ref_link(call: CallbackQuery):
    user = db.get_or_create_user(call.from_user.id, call.from_user.username, call.from_user.full_name)
    await call.answer()
    await call.message.answer(
        f"🤝 Твой реферальный код: <code>{user['ref_code']}</code>\n"
        f"Ссылка: https://t.me/{BOT_USERNAME}?start={user['ref_code']}"
    )


# ───────────────────────── анкета ─────────────────────────
@router.callback_query(F.data == "apply")
async def apply_start(call: CallbackQuery, state: FSMContext):
    db.get_or_create_user(call.from_user.id, call.from_user.username, call.from_user.full_name)
    last = db.last_application(call.from_user.id)
    if last and last["status"] == "pending":
        return await call.answer(f"Твоя заявка #{last['id']} уже на рассмотрении ⏳", show_alert=True)
    if last and last["status"] == "approved":
        return await call.answer("Твоя заявка уже одобрена ✅", show_alert=True)

    await call.answer()
    await state.clear()
    await state.set_state(Apply.nickname)
    await call.message.answer("1/6 · 👤 Как тебя называть? (ник)", reply_markup=cancel_kb())


@router.message(Apply.nickname, F.text)
async def q_nickname(message: Message, state: FSMContext):
    nick = message.text.strip()
    if not 1 <= len(nick) <= 32:
        return await message.answer("Ник должен быть от 1 до 32 символов.")
    await state.update_data(nickname=nick)
    await state.set_state(Apply.age)
    await message.answer("2/6 · 🎂 Сколько тебе лет?", reply_markup=cancel_kb())


@router.message(Apply.age, F.text)
async def q_age(message: Message, state: FSMContext):
    if not message.text.strip().isdigit() or not 10 <= int(message.text) <= 99:
        return await message.answer("Введи возраст числом, например <b>20</b>.")
    await state.update_data(age=int(message.text))
    await state.set_state(Apply.experience)
    await message.answer("3/6 · 💼 Есть опыт в сфере?", reply_markup=yes_no_kb("exp"))


@router.callback_query(Apply.experience, F.data.startswith("exp:"))
async def q_experience(call: CallbackQuery, state: FSMContext):
    await state.update_data(experience=call.data.split(":", 1)[1])
    await state.set_state(Apply.equipment)
    await call.message.edit_text(f"3/6 · 💼 Опыт в сфере: <b>{call.data.split(':', 1)[1]}</b>")
    await call.message.answer("4/6 · 🎧 Есть Discord, CS2 и микрофон?", reply_markup=yes_no_kb("eq"))


@router.callback_query(Apply.equipment, F.data.startswith("eq:"))
async def q_equipment(call: CallbackQuery, state: FSMContext):
    await state.update_data(equipment=call.data.split(":", 1)[1])
    await state.set_state(Apply.hours)
    await call.message.edit_text(f"4/6 · 🎧 Discord, CS2, микрофон: <b>{call.data.split(':', 1)[1]}</b>")
    await call.message.answer("5/6 · ⏱ Сколько часов в день готов уделять работе?", reply_markup=cancel_kb())


@router.message(Apply.hours, F.text)
async def q_hours(message: Message, state: FSMContext):
    hours = message.text.strip()
    if len(hours) > 20:
        return await message.answer("Коротко, пожалуйста — например <b>4</b> или <b>3-5</b>.")
    await state.update_data(hours=hours)
    await state.set_state(Apply.source)
    await message.answer("6/6 · 📯 Откуда про нас узнал?", reply_markup=cancel_kb())


@router.message(Apply.source, F.text)
async def q_source(message: Message, state: FSMContext):
    await state.update_data(source=message.text.strip()[:200])
    await state.set_state(Apply.confirm)
    await message.answer(preview_text(await state.get_data()), reply_markup=confirm_kb())


@router.message(StateFilter(Apply.nickname, Apply.age, Apply.hours, Apply.source))
async def q_not_text(message: Message):
    await message.answer("Ответь текстом 🙂")


@router.callback_query(Apply.confirm, F.data == "send_app")
async def send_application(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    user = db.get_or_create_user(call.from_user.id, call.from_user.username, call.from_user.full_name)

    app_id = db.create_application(call.from_user.id, data, user["ref_code"])
    app = db.get_application(app_id)
    try:
        sent = await bot.send_message(CHANNEL_ID, application_text(app, call.from_user.id), reply_markup=review_kb(app_id))
        db.set_channel_msg(app_id, sent.message_id)
    except Exception as e:
        logging.exception("Не удалось отправить заявку в канал")
        db.set_status(app_id, "rejected", 0)
        return await call.message.edit_text(f"⚠️ Не получилось отправить заявку, попробуй позже.\n<code>{escape(str(e))}</code>")

    await call.message.edit_text(
        f"✅ Заявка <b>#{app_id}</b> отправлена!\n\nОжидай ответа — мы напишем сюда."
    )


# ───────────────────────── модерация в канале ─────────────────────────
@router.callback_query(F.data.regexp(r"^(approve|reject):\d+$"))
async def review(call: CallbackQuery, bot: Bot):
    if not await is_admin(bot, call.from_user.id):
        return await call.answer("⛔️ Только для админов", show_alert=True)

    action, app_id = call.data.split(":")
    app_id = int(app_id)
    status = "approved" if action == "approve" else "rejected"

    if not db.set_status(app_id, status, call.from_user.id):
        return await call.answer("Заявка уже рассмотрена", show_alert=True)

    app = db.get_application(app_id)
    mark = "✅ <b>Одобрено</b>" if status == "approved" else "❌ <b>Отклонено</b>"
    await call.message.edit_text(
        application_text(app, app["user_id"]) + f"\n\n{mark} — {admin_tag(call.from_user)}",
        reply_markup=review_kb(app_id, with_decision=False),
    )
    await call.answer("Готово")

    text = (
        f"🎉 Твоя заявка <b>#{app_id}</b> одобрена!\nСкоро с тобой свяжутся."
        if status == "approved"
        else f"😔 Твоя заявка <b>#{app_id}</b> отклонена.\nМожешь попробовать подать заново позже."
    )
    try:
        await bot.send_message(app["user_id"], text, reply_markup=main_menu_kb() if status == "rejected" else None)
    except Exception:
        logging.warning("Не удалось уведомить пользователя %s", app["user_id"])


# ───────────────────────── переписка админ ↔ кандидат ─────────────────────────
@router.callback_query(F.data.startswith("reply:"))
async def admin_reply_btn(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await is_admin(bot, call.from_user.id):
        return await call.answer("⛔️", show_alert=True)
    target_id = int(call.data.split(":")[1])
    await state.set_state(AdminWrite.text)
    await state.update_data(target_id=target_id, app_id=None)
    await call.answer()
    await call.message.answer("✉️ Отправь ответ кандидату. /cancel — отмена.")


@router.message(AdminWrite.text)
async def admin_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    target_id = data["target_id"]
    try:
        await bot.send_message(target_id, "📩 <b>Сообщение от администрации:</b>")
        await message.copy_to(target_id)
    except Exception as e:
        return await message.answer(f"⚠️ Не доставлено (кандидат заблокировал бота?)\n<code>{escape(str(e))}</code>")
    db.set_last_admin(target_id, message.from_user.id)
    await message.answer("✅ Отправлено. Ответ кандидата придёт сюда.")


@router.message(F.chat.type == "private")
async def from_candidate(message: Message, bot: Bot):
    """Любое сообщение кандидата вне анкеты → админу, который ему писал."""
    user = db.get_user(message.from_user.id)
    if not user or not user["last_admin_id"]:
        return await message.answer("Выбери действие 👇", reply_markup=main_menu_kb())

    last = db.last_application(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✉️ Ответить", callback_data=f"reply:{message.from_user.id}")
    ]])
    try:
        await bot.send_message(
            user["last_admin_id"],
            f"💬 Ответ кандидата <b>{escape(message.from_user.full_name)}</b>"
            + (f" (заявка #{last['id']})" if last else "") + ":",
        )
        await message.copy_to(user["last_admin_id"], reply_markup=kb)
        await message.answer("✅ Передано администрации.")
    except Exception:
        await message.answer("Не удалось доставить сообщение, попробуй позже.")


# ───────────────────────── запуск ─────────────────────────
async def main():
    global BOT_USERNAME
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    BOT_USERNAME = (await bot.me()).username
    dp = Dispatcher()
    dp.include_router(router)
    logging.info("Бот @%s запущен", BOT_USERNAME)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
