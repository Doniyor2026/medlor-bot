import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
import aiosqlite

BOT_TOKEN = "7818964713:AAGM1ZgnwqLgSjyeyT-ocd6GsTtew-X5Yhg"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class AppointmentStates(StatesGroup):
    choosing_doctor = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()

# Админ ID лар — ўзингизникини қўйинг!
ADMIN_IDS = [654646785, 7956881727]

DOCTORS = {
    "lor": "ЛОР",
    "pediatr": "Педиатр"
}

SERVICES = [
    "Shifokor ko'rigi",
    "Tomoq yuvish",
    "Burun yuvish (Kukushka)",
    "Inektsiyalar-ukol (v/i, m/o va t/o)"
]

AVAILABLE_TIMES = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
                   "13:00", "13:30", "14:00", "15:00", "16:00", "17:00", "18:00",
                   "19:00", "20:00", "21:00", "22:00"]

async def init_db():
    async with aiosqlite.connect("appointments.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                doctor TEXT,
                service TEXT,
                date TEXT,
                time TEXT,
                patient_name TEXT,
                patient_phone TEXT
            )
        """)
        try:
            await db.execute("ALTER TABLE appointments ADD COLUMN service TEXT")
            await db.execute("ALTER TABLE appointments ADD COLUMN patient_name TEXT")
            await db.execute("ALTER TABLE appointments ADD COLUMN patient_phone TEXT")
        except:
            pass
        await db.commit()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    rows = []
    chunk_size = 2
    items = list(DOCTORS.items())
    for i in range(0, len(items), chunk_size):
        row = []
        for key, name in items[i:i+chunk_size]:
            row.append(InlineKeyboardButton(text=name, callback_data=f"doctor:{key}"))
        rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer("🏥 Салом! Medlor клиникага хуш келибсиз!\n\nКасбни танланг 👇", reply_markup=keyboard)
    await state.set_state(AppointmentStates.choosing_doctor)

@dp.callback_query(lambda c: c.data.startswith("doctor:"))
async def choose_doctor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Тез жавоб
    doctor_key = callback.data.split(":", 1)[1]
    doctor_name = DOCTORS.get(doctor_key, "Номаълум")
    await state.update_data(doctor=doctor_name)
    
    rows = []
    chunk_size = 2
    for i in range(0, len(SERVICES), chunk_size):
        row = []
        for service in SERVICES[i:i+chunk_size]:
            row.append(InlineKeyboardButton(text=service, callback_data=f"service:{service}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Орқага", callback_data="back")])
    services_kb = InlineKeyboardMarkup(inline_keyboard=rows)
    
    await callback.message.edit_text(f"Танланган касб: {doctor_name}\n\nХизматни танланг:", reply_markup=services_kb)
    await state.set_state(AppointmentStates.choosing_service)

@dp.callback_query(lambda c: c.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    service = callback.data.split(":", 1)[1]
    await state.update_data(service=service)
    data = await state.get_data()
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Орқага", callback_data="back")]])
    
    await callback.message.edit_text(f"Касб: {data['doctor']}\nХизмат: {service}\n\nСанани танланг:", reply_markup=back_kb)
    await callback.message.answer("Календар:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(AppointmentStates.choosing_date)

@dp.callback_query(SimpleCalendarCallback.filter())
async def process_date(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await callback.answer()
        date_str = date.strftime("%Y-%m-%d")
        await state.update_data(date=date_str)
        
        rows = []
        chunk_size = 3
        for i in range(0, len(AVAILABLE_TIMES), chunk_size):
            row = []
            for time in AVAILABLE_TIMES[i:i+chunk_size]:
                row.append(InlineKeyboardButton(text=time, callback_data=f"time:{time}"))
            rows.append(row)
        rows.append([InlineKeyboardButton(text="◀️ Орқага", callback_data="back")])
        times_kb = InlineKeyboardMarkup(inline_keyboard=rows)
        
        await callback.message.edit_text(f"Сана: {date_str}\nВақтни танланг:", reply_markup=times_kb)
        await state.set_state(AppointmentStates.choosing_time)

@dp.callback_query(lambda c: c.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    time = callback.data.split(":", 1)[1]
    await state.update_data(time=time)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Орқага", callback_data="back")]])
    
    await callback.message.edit_text("Илтимос, фамилия ва исмингизни киритинг (масалан: Абдуллаев Алишер)", reply_markup=back_kb)
    await state.set_state(AppointmentStates.entering_name)

@dp.message(AppointmentStates.entering_name)
async def enter_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 5:
        await message.answer("❌ Илтимос, тўлиқ ФИО киритинг!")
        return
    await state.update_data(patient_name=name)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Орқага", callback_data="back")]])
    
    await message.answer("Илтимос, телефон рақамингизни киритинг (+998 форматида):", reply_markup=back_kb)
    await state.set_state(AppointmentStates.entering_phone)

@dp.message(AppointmentStates.entering_phone)
async def enter_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    if not (phone.startswith("+998") and len(phone) == 13) and not (len(phone) == 9 and phone.isdigit()):
        await message.answer("❌ Формат нотўғри! Масалан: +998901234567")
        return
    
    if len(phone) == 9:
        phone = "+998" + phone
        
    data = await state.get_data()
    
    async with aiosqlite.connect("appointments.db") as db:
        await db.execute("INSERT INTO appointments (user_id, doctor, service, date, time, patient_name, patient_phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (message.from_user.id, data['doctor'], data['service'], data['date'], data['time'], data['patient_name'], phone))
        await db.commit()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, 
                f"🆕 **Янги ёзилиш!**\n\n"
                f"👤 {data['patient_name']}\n"
                f"📞 {phone}\n"
                f"👨‍⚕️ {data['doctor']}\n"
                f"🛠 {data['service']}\n"
                f"📅 {data['date']} | 🕙 {data['time']}",
                parse_mode="Markdown")
        except:
            pass
    
    await message.answer(
        f"✅ Ёзилиш муваффақиятли!\n\n"
        f"Пациент: {data['patient_name']}\n"
        f"Телефон: {phone}\n"
        f"Касб: {data['doctor']}\n"
        f"Хизмат: {data['service']}\n"
        f"Сана: {data['date']}\n"
        f"Вақт: {data['time']}\n\n"
        f"Раҳмат! 😊"
    )
    await state.clear()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Сизга бу буйруққа рухсат йўқ!")
        return
    
    async with aiosqlite.connect("appointments.db") as db:
        async with db.execute("SELECT doctor, service, date, time, patient_name, patient_phone FROM appointments ORDER BY id DESC LIMIT 30") as cursor:
            rows = await cursor.fetchall()
    
    if not rows:
        await message.answer("📭 Ҳозирча ҳеч ким ёзилмаган.")
        return
    
    text = "📋 **Сўнгги ёзилишлар** (охирги 30 та):\n\n"
    for i, row in enumerate(rows, 1):
        doctor, service, date, time, name, phone = row
        text += f"{i}. 👤 {name or 'Номаълум'}\n"
        text += f"   📞 {phone or 'Йўқ'}\n"
        text += f"   👨‍⚕️ {doctor}\n"
        text += f"   🛠 {service}\n"
        text += f"   📅 {date} | 🕙 {time}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Рухсат йўқ!")
        return
    
    async with aiosqlite.connect("appointments.db") as db:
        async with db.execute("SELECT COUNT(*) FROM appointments") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT date, COUNT(*) FROM appointments GROUP BY date ORDER BY date DESC LIMIT 7") as cursor:
            daily = await cursor.fetchall()
    
    text = f"📊 **Статистика**\n\nУмумий ёзилишлар: {total}\n\nСўнгги 7 кун:\n"
    for date, count in daily:
        text += f"{date} — {count} та\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Дарров жавоб — loading ни ўчиради
    
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == AppointmentStates.choosing_service.state:
        await start(callback.message, state)
    
    elif current_state == AppointmentStates.choosing_date.state:
        await choose_doctor(callback, state)
    
    elif current_state == AppointmentStates.choosing_time.state:
        await choose_service(callback, state)
    
    elif current_state in [AppointmentStates.entering_name.state, AppointmentStates.entering_phone.state]:
        date_str = data.get('date', 'Белгиланмаган')
        
        rows = []
        chunk_size = 3
        for i in range(0, len(AVAILABLE_TIMES), chunk_size):
            row = []
            for time in AVAILABLE_TIMES[i:i+chunk_size]:
                row.append(InlineKeyboardButton(text=time, callback_data=f"time:{time}"))
            rows.append(row)
        rows.append([InlineKeyboardButton(text="◀️ Орқага", callback_data="back")])
        times_kb = InlineKeyboardMarkup(inline_keyboard=rows)
        
        await callback.message.edit_text(f"Сана: {date_str}\nВақтни танланг:", reply_markup=times_kb)
        await state.set_state(AppointmentStates.choosing_time)
    
    else:
        await start(callback.message, state)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())