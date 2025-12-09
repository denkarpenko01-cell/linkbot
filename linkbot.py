import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = "7870973074:AAEfuESNoX4PoFuG7s1upFM99BT83Rmz324"
ADMIN_ID = 7100925717  # <-- Вставь свой Telegram ID
DB_NAME = "links.db"

# ---------------- FSM ----------------
class AddLinkState(StatesGroup):
    waiting_for_title = State()
    waiting_for_url = State()

class EditLinkState(StatesGroup):
    waiting_for_select = State()
    waiting_for_title = State()
    waiting_for_url = State()

class DeleteLinkState(StatesGroup):
    waiting_for_select = State()

# ---------------- BOT ----------------
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- DB ----------------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT
            )
        """)
        await db.commit()

# ---------------- KEYBOARD ----------------
def main_kb(is_admin=False):
    buttons = [[KeyboardButton(text="/links")]]
    if is_admin:
        buttons.append([KeyboardButton(text="➕ Добавить ссылку")])
        buttons.append([KeyboardButton(text="✏️ Редактировать ссылку")])
        buttons.append([KeyboardButton(text="🗑️ Удалить ссылку")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ---------------- HANDLERS ----------------
@dp.message(Command("start"))
async def start_bot(message: Message):
    await message.answer(
        "👋 Привет!\n\n"
        "Пропишите /links для просмотра актуальных ссылок.",
        reply_markup=main_kb(is_admin=message.from_user.id==ADMIN_ID)
    )

@dp.message(Command("links"))
async def show_links(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, title, url FROM links") as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("❌ Ссылок пока нет.")
        return

    text = "📌 Актуальные ссылки:\n\n"
    for i, row in enumerate(rows, start=1):
        title = row[1] or "Без названия"
        text += f"{i}. {title}: {row[2]}\n"

    await message.answer(text)

# ---------------- ADD LINK ----------------
@dp.message(lambda m: m.text == "➕ Добавить ссылку")
async def add_link_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer("✏️ Введите название ссылки:")
    await state.set_state(AddLinkState.waiting_for_title)

@dp.message(AddLinkState.waiting_for_title)
async def add_link_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("🔗 Теперь введите URL:")
    await state.set_state(AddLinkState.waiting_for_url)

@dp.message(AddLinkState.waiting_for_url)
async def add_link_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("❌ Это не похоже на ссылку. Попробуйте снова.")
        return

    data = await state.get_data()
    title = data.get("title")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO links (title, url) VALUES (?, ?)", (title, url))
        await db.commit()

    await state.clear()
    await message.answer("✅ Ссылка успешно добавлена!", reply_markup=main_kb(is_admin=True))

# ---------------- DELETE LINK ----------------
@dp.message(lambda m: m.text == "🗑️ Удалить ссылку")
async def delete_link_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, title FROM links") as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("❌ Ссылок для удаления нет.")
        return

    text = "Выберите номер ссылки для удаления:\n"
    for i, row in enumerate(rows, start=1):
        title = row[1] or "Без названия"
        text += f"{i}. {title}\n"

    links_map = {str(i): row[0] for i, row in enumerate(rows, start=1)}
    await state.update_data(links_map=links_map)
    await state.set_state(DeleteLinkState.waiting_for_select)

    await message.answer(text)

@dp.message(DeleteLinkState.waiting_for_select)
async def delete_link_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    links_map = data.get("links_map", {})

    link_id = links_map.get(message.text.strip())
    if not link_id:
        await message.answer("❌ Неверный выбор. Попробуйте снова.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM links WHERE id=?", (link_id,))
        await db.commit()

    await state.clear()
    await message.answer("✅ Ссылка удалена.", reply_markup=main_kb(is_admin=True))

# ---------------- EDIT LINK ----------------
@dp.message(lambda m: m.text == "✏️ Редактировать ссылку")
async def edit_link_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, title FROM links") as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("❌ Ссылок для редактирования нет.")
        return

    text = "Выберите номер ссылки для редактирования:\n"
    for i, row in enumerate(rows, start=1):
        title = row[1] or "Без названия"
        text += f"{i}. {title}\n"

    links_map = {str(i): row[0] for i, row in enumerate(rows, start=1)}
    await state.update_data(links_map=links_map)
    await state.set_state(EditLinkState.waiting_for_select)

    await message.answer(text)

@dp.message(EditLinkState.waiting_for_select)
async def edit_link_select(message: Message, state: FSMContext):
    data = await state.get_data()
    links_map = data.get("links_map", {})
    link_id = links_map.get(message.text.strip())
    if not link_id:
        await message.answer("❌ Неверный выбор. Попробуйте снова.")
        return
    await state.update_data(edit_id=link_id)
    await message.answer("✏️ Введите новое название:")
    await state.set_state(EditLinkState.waiting_for_title)

@dp.message(EditLinkState.waiting_for_title)
async def edit_link_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("🔗 Введите новый URL:")
    await state.set_state(EditLinkState.waiting_for_url)

@dp.message(EditLinkState.waiting_for_url)
async def edit_link_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("❌ Это не похоже на ссылку. Попробуйте снова.")
        return

    data = await state.get_data()
    title = data.get("title")
    link_id = data.get("edit_id")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE links SET title=?, url=? WHERE id=?", (title, url, link_id))
        await db.commit()

    await state.clear()
    await message.answer("✅ Ссылка обновлена.", reply_markup=main_kb(is_admin=True))

# ---------------- MAIN ----------------
async def main():
    await init_db()
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
