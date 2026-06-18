import asyncio
import logging
import os
from keep_alive import keep_alive
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ContentType, WebAppInfo
import json

# ────────────────────────────────────────────────
# НАСТРОЙКИ
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORWARD_TO_CHAT_ID = -1003544935955  
# ────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


class OrderForm(StatesGroup):
    materials_text = State()     # ввод текста материалов
    materials_photo = State()    # ожидание фото + кнопка "Дальше"
    choosing = State()           # выбор поля (объект/изделие)
    entering_object = State()
    entering_product = State()
    sending_extra_photos = State() # доп фото после webapp

# Клавиатуры
WEBAPP_URL = "https://floyd666-lab.github.io/botbionika/" # Позже заменим на реальный URL

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Открыть форму (WebApp)", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📝 Новая заявка (Старый метод)")]
    ],
    resize_keyboard=True
)

choice_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Объект"),     KeyboardButton(text="Изделие")],
        [KeyboardButton(text="⬅ Назад"),    KeyboardButton(text="✅ Отправить заявку")]
    ],
    resize_keyboard=True
)

photo_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➜ Дальше")],
        [KeyboardButton(text="⬅ Назад")]
    ],
    resize_keyboard=True
)


@router.message(CommandStart())
@router.message(F.text.in_({"📝 Новая заявка (Старый метод)", "⬅ Назад"}))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(object="", product="", materials="", photos=[])
    
    await message.answer(
        "👷 <b>Новая заявка</b>\n\n"
        "1. Напиши <b>список материалов</b> и количество одним сообщением.\n\n"
        "<i>Пример:</i>\n"
        "Медь 120-10 — 25 метров\n"
        "Шпильки 3 - 10 шт\n"
        "<b>Фото прикреплять не обязательно</b>, но кому надо отправляйте",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderForm.materials_text)


@router.message(OrderForm.materials_text, F.content_type.in_({ContentType.TEXT, ContentType.PHOTO}))
async def process_materials_first_step(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if message.photo:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
        await message.answer(
            "Фото добавлено!\n\n"
            "Можешь прислать ещё или нажать «➜ Дальше»",
            reply_markup=photo_kb
        )
        await state.set_state(OrderForm.materials_photo)
        return

    # Текст
    text = message.text.strip()
    if len(text) < 10:
        await message.answer("📝 Список слишком короткий. Напиши ещё раз или пришли фото:")
        return

    await state.update_data(materials=text)
    await message.answer(
        "✅ Материалы сохранены!\n\n"
        "Теперь можешь прислать фото (необязательно)\n"
        "или сразу нажать «➜ Дальше»",
        reply_markup=photo_kb
    )
    await state.set_state(OrderForm.materials_photo)


@router.message(OrderForm.materials_photo, F.photo)
async def add_more_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    
    await message.answer(
        "Фото добавлено! Ещё фото или «➜ Дальше»?",
        reply_markup=photo_kb
    )


@router.message(OrderForm.materials_photo, F.text == "➜ Дальше")
async def skip_photos_and_continue(message: Message, state: FSMContext):
    await message.answer(
        "✅ Этап материалов завершён!\n\n"
        "Теперь заполни поля (в любом порядке):",
        reply_markup=choice_kb
    )
    await state.set_state(OrderForm.choosing)


@router.message(OrderForm.materials_photo, F.text == "⬅ Назад")
async def back_to_materials_text(message: Message, state: FSMContext):
    await message.answer(
        "Вернулись к вводу списка материалов.\n"
        "Можешь дополнить/изменить текст или сразу нажать «➜ Дальше»",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderForm.materials_text)


# === ВЫБОР ПОЛЕЙ ===
@router.message(OrderForm.choosing, F.text == "Объект")
async def ask_object(message: Message, state: FSMContext):
    await message.answer("📍 Напиши <b>объект</b> (название/номер):", parse_mode="HTML")
    await state.set_state(OrderForm.entering_object)


@router.message(OrderForm.choosing, F.text == "Изделие")
async def ask_product(message: Message, state: FSMContext):
    await message.answer("🔧 Напиши <b>изделие</b> (марка/номер):", parse_mode="HTML")
    await state.set_state(OrderForm.entering_product)


@router.message(OrderForm.choosing, F.text == "⬅ Назад")
async def back_to_photo_step(message: Message, state: FSMContext):
    await message.answer(
        "Вернулись к этапу материалов.\n"
        "Можешь добавить фото или сразу «➜ Дальше»",
        reply_markup=photo_kb
    )
    await state.set_state(OrderForm.materials_photo)


@router.message(OrderForm.choosing, F.text == "✅ Отправить заявку")
async def check_and_send(message: Message, state: FSMContext):
    data = await state.get_data()
    
    obj = data.get("object", "").strip()
    prod = data.get("product", "").strip()
    mats = data.get("materials", "—")
    photos = data.get("photos", [])

    if not obj or not prod:
        missing = []
        if not obj: missing.append("Объект")
        if not prod: missing.append("Изделие")
        await message.answer(f"❗ Заполни: <b>{' и '.join(missing)}</b>", parse_mode="HTML")
        return

    user = message.from_user
    final_text = (
        "🛒 <b>НОВАЯ ЗАЯВКА НА ЗАКУПКУ</b>\n\n"
        f"👤 <b>Сотрудник:</b> {user.first_name} {user.last_name or ''} (@{user.username or 'нет'})\n"
        f"🆔 <b>ID:</b> {user.id}\n"
        f"📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Материалы:</b>\n{mats}\n\n"
        f"<b>Объект:</b> {obj}\n"
        f"<b>Изделие:</b> {prod}\n\n"
        "───────────────"
    )

    try:
        await bot.send_message(FORWARD_TO_CHAT_ID, final_text, parse_mode="HTML")
        
        if photos:
            for photo_id in photos:
                await bot.send_photo(FORWARD_TO_CHAT_ID, photo_id)
            await bot.send_message(FORWARD_TO_CHAT_ID, "📸 Фото материалов к заявке выше ↑")

        await message.answer("✅ Заявка успешно отправлена!", reply_markup=main_kb)
        
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await message.answer("❌ Ошибка отправки. Попробуй позже.")
    
    await state.clear()


@router.message(OrderForm.entering_object)
async def save_object(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("Слишком коротко. Напиши ещё раз:")
        return
    await state.update_data(object=text)
    await message.answer("✅ Объект сохранён!", reply_markup=choice_kb)
    await state.set_state(OrderForm.choosing)


@router.message(OrderForm.entering_product)
async def save_product(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("Слишком коротко. Напиши ещё раз:")
        return
    await state.update_data(product=text)
    await message.answer("✅ Изделие сохранено!", reply_markup=choice_kb)
    await state.set_state(OrderForm.choosing)


# Отмена
@router.message(F.text.lower().in_({"отмена", "/cancel", "cancel"}))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Заявка отменена.", reply_markup=main_kb)


# Ловушка для непонятных сообщений
@router.message(F.text, ~F.text.startswith('/'))
async def unknown(message: Message):
    await message.answer("Воспользуйтесь кнопкой «📝 Открыть форму (WebApp)» в меню.", reply_markup=main_kb)


# === WEB APP HANDLER ===
@router.message(F.web_app_data)
async def process_web_app_data(message: Message, state: FSMContext):
    await state.clear()
    data = json.loads(message.web_app_data.data)
    
    mats = data.get("materials", "—")
    obj = data.get("object", "")
    prod = data.get("product", "")
    
    user = message.from_user
    final_text = (
        "🛒 <b>НОВАЯ ЗАЯВКА НА ЗАКУПКУ (Web)</b>\n\n"
        f"👤 <b>Сотрудник:</b> {user.first_name} {user.last_name or ''} (@{user.username or 'нет'})\n"
        f"🆔 <b>ID:</b> {user.id}\n"
        f"📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Материалы:</b>\n{mats}\n\n"
        f"<b>Объект:</b> {obj}\n"
        f"<b>Изделие:</b> {prod}\n\n"
        "───────────────"
    )
    
    try:
        await bot.send_message(FORWARD_TO_CHAT_ID, final_text, parse_mode="HTML")
        await message.answer(
            "✅ <b>Заявка успешно сформирована и отправлена!</b>\n\n"
            "📸 Если вам нужно прикрепить фото материалов к этой заявке, "
            "просто отправьте их сюда прямо сейчас (по одному или альбомом).",
            parse_mode="HTML",
            reply_markup=main_kb
        )
        await state.set_state(OrderForm.sending_extra_photos)
    except Exception as e:
        logger.error(f"Ошибка отправки из WebApp: {e}")
        await message.answer("❌ Ошибка отправки. Попробуй позже.")

@router.message(OrderForm.sending_extra_photos, F.photo)
async def handle_extra_photos(message: Message, state: FSMContext):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    try:
        await bot.send_photo(
            chat_id=FORWARD_TO_CHAT_ID, 
            photo=photo_id, 
            caption=f"📸 Дополнительное фото к последней заявке от {user.first_name}"
        )
        await message.answer("✅ Фото добавлено и отправлено!")
    except Exception as e:
        logger.error(f"Ошибка отправки доп фото: {e}")
        await message.answer("❌ Ошибка при отправке фото.")


async def main():
    keep_alive()   # ← ВАЖНО

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Webhook удалён (или его не было)")
    except Exception as e:
        print("Не удалось удалить webhook:", e)

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())