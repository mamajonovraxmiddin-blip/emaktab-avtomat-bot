import os
import io
import asyncio
import pandas as pd
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# emaktab faylidan funksiyani ulaymiz
from emaktab import try_emaktab_login

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MASTER_SECRET_CODE = os.getenv("MASTER_SECRET_CODE")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class SetupState(StatesGroup):
    waiting_for_class_name = State()
    waiting_for_secret_code = State()

bot_config = {"class_name": "8-G", "is_authorized": False, "entered_pin": ""}
db_students = {}
db_parents = {}

# PIN-kod klaviaturasi
def get_pin_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(1, 10):
        builder.button(text=str(i), callback_data=f"pin_num_{i}")
    builder.button(text="❌ C", callback_data="pin_clear")
    builder.button(text="0", callback_data="pin_num_0")
    builder.button(text="✅ OK", callback_data="pin_submit")
    builder.adjust(3)
    return builder.as_markup()

# Asosiy menyu
async def show_main_menu(message_or_callback, class_name):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨‍🎓 O'quvchilar ro'yxati", callback_data="view_students"))
    builder.row(types.InlineKeyboardButton(text="🧓 Ota-onalar ro'yxati", callback_data="view_parents"))
    text = f"✨ <b>{class_name} sinf</b> uchun emaktab.uz platformasiga kirishni amalga oshiruvchi botga xush kelibsiz!\n\nKerakli bo'limni tanlang:"
    
    try:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            await message_or_callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        pass

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    bot_config["entered_pin"] = ""
    if bot_config["is_authorized"]:
        await show_main_menu(message, bot_config["class_name"])
    else:
        await message.answer("👋 Salom! Men eMaktab avtomatlashtirish botiman.\n\nIltimos, sinf nomini kiriting (Masalan: <b>8-G</b>):", parse_mode="HTML")
        await state.set_state(SetupState.waiting_for_class_name)

@dp.message(SetupState.waiting_for_class_name)
async def process_class_name(message: types.Message, state: FSMContext):
    await state.update_data(class_name=message.text.strip())
    await message.answer("✅ Sinf nomi qabul qilindi.\n\n⚠️ Botdan foydalanish uchun <b>PIN-kodni bosing</b>:\nKiritildi: <code>Ochiq maydon</code>", reply_markup=get_pin_keyboard(), parse_mode="HTML")
    await state.set_state(SetupState.waiting_for_secret_code)

@dp.callback_query(SetupState.waiting_for_secret_code, F.data.startswith("pin_num_"))
async def process_pin_digits(callback: types.CallbackQuery, state: FSMContext):
    num = callback.data.split("_")[-1]
    bot_config["entered_pin"] += str(num)
    stars = "⭐" * len(bot_config["entered_pin"])
    
    try:
        await callback.message.edit_text(f"⚠️ Botdan foydalanish uchun <b>PIN-kodni bosing</b>:\nKiritildi: {stars}", reply_markup=get_pin_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(SetupState.waiting_for_secret_code, F.data == "pin_clear")
async def process_pin_clear(callback: types.CallbackQuery, state: FSMContext):
    bot_config["entered_pin"] = ""
    try:
        await callback.message.edit_text("⚠️ Botdan foydalanish uchun <b>PIN-kodni bosing</b>:\nKiritildi: <code>Ochiq maydon</code>", reply_markup=get_pin_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(SetupState.waiting_for_secret_code, F.data == "pin_submit")
async def process_pin_submit(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    class_name = user_data.get("class_name")
    
    if len(bot_config["entered_pin"]) < 4:
        await callback.answer("❌ PIN-kod uzunligi kamida 4 ta raqam bo'lishi kerak!", show_alert=True)
        return
        
    if str(bot_config["entered_pin"]) == str(MASTER_SECRET_CODE):
        bot_config["class_name"] = class_name
        bot_config["is_authorized"] = True
        await state.clear()
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("🔒 Kod to'g'ri! Bot muvaffaqiyatli faollashtirildi.")
        await show_main_menu(callback, class_name)
    else:
        bot_config["entered_pin"] = ""
        await callback.answer("❌ PIN-kod noto'g'ri!", show_alert=True)
        try:
            await callback.message.edit_text("❌ PIN-kod noto'g'ri! Qaytadan kiriting:\nKiritildi: <code>Ochiq maydon</code>", reply_markup=get_pin_keyboard(), parse_mode="HTML")
        except Exception:
            pass

@dp.callback_query(F.data.in_({"view_students", "view_parents"}))
async def view_list(callback: types.CallbackQuery):
    if not bot_config["is_authorized"]: return
    role = "students" if callback.data == "view_students" else "parents"
    current_db = db_students if role == "students" else db_parents
    label = "o'quvchilar" if role == "students" else "ota-onalar"
    builder = InlineKeyboardBuilder()

    if not current_db:
        df = pd.DataFrame(columns=["Ism_Familiya", "Login", "Parol"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        template = BufferedInputFile(output.getvalue(), filename=f"{bot_config['class_name']}_{label}_shabloni.xlsx")
        await callback.message.answer_document(template, caption=f"⚠️ Tizimda {label} ro'yxati yo'q. To'ldirib yuboring.")
    else:
        for name in current_db.keys():
            builder.button(text=name, callback_data=f"go_{role}_{name}")
        builder.adjust(2)
        builder.row(types.InlineKeyboardButton(text="🔄 Ro'yxatni o'zgartirish", callback_data=f"change_{role}"))
        builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_main"))
        try:
            await callback.message.edit_text(f"📋 {bot_config['class_name']} sinf {label} ro'yxati:", reply_markup=builder.as_markup())
        except Exception:
            pass
    await callback.answer()

@dp.callback_query(F.data.startswith("change_"))
async def change_list_template(callback: types.CallbackQuery):
    role = callback.data.split("_")[1]
    label = "o'quvchilar" if role == "students" else "ota-onalar"
    df = pd.DataFrame(columns=["Ism_Familiya", "Login", "Parol"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    template = BufferedInputFile(output.getvalue(), filename=f"{bot_config['class_name']}_{label}_yangi_shabloni.xlsx")
    await callback.message.answer_document(template, caption=f"🔄 Ro'yxatni yangilash uchun shablon.")
    await callback.answer()

@dp.message(F.document)
async def handle_excel_upload(message: types.Message):
    if not bot_config["is_authorized"]: return
    file_name = message.document.file_name.lower()
    if not file_name.endswith(('.xlsx', '.xls')): return
    msg = await message.reply("⏳ Ro'yxat yangilanmoqda...")
    file_info = await bot.get_file(message.document.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    try:
        df = pd.read_excel(io.BytesIO(downloaded_file.read()))
        role = "parents" if "ota" in file_name else "students"
        current_db = db_students if role == "students" else db_parents
        current_db.clear()
        builder = InlineKeyboardBuilder()
        for _, row in df.iterrows():
            name = str(row['Ism_Familiya']).strip()
            login = str(row['Login']).strip()
            parol = str(row['Parol']).strip()
            if name and login and parol:
                current_db[name] = {"login": login, "parol": parol}
                builder.button(text=name, callback_data=f"go_{role}_{name}")
        builder.adjust(2)
        builder.row(types.InlineKeyboardButton(text="🔄 Ro'yxatni o'zgartirish", callback_data=f"change_{role}"))
        builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_main"))
        await msg.edit_text("✅ Ro'yxat yangilandi!", reply_markup=builder.as_markup())
    except Exception:
        await msg.edit_text("❌ Faylni o'qishda xatolik.")

@dp.callback_query(F.data.startswith("go_"))
async def process_emaktab_login(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    role = data_parts[1] # indeks 1 etib to'g'rilandi
    name = callback.data.replace(f"go_{role}_", "")
    
    current_db = db_students if role == "students" else db_parents
    user_data = current_db.get(name)
    if not user_data: return
    
    status_msg = await callback.message.answer(f"⏳ <b>{name}</b> profiliga kirilmoqda...")
    await callback.answer()
    result = await try_emaktab_login(user_data["login"], user_data["parol"])
    await status_msg.edit_text(f"👤 Foydalanuvchi: <b>{name}</b>\nNatija: {result}", parse_mode="HTML")

@dp.callback_query(F.data == "back_main")
async def back_to_main_menu(callback: types.CallbackQuery):
    await show_main_menu(callback, bot_config["class_name"])
    await callback.answer()

# Web server Render uchun
async def start_web_server():
    from aiohttp import web
    
    async def handle(request):
        return web.Response(text="Bot is running active!")
        
    app = web.Application()
    app.router.add_get('/', handle)
    
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    # 1. Render talab qiladigan veb-serverni fonda yoqamiz
    await start_web_server()
    
    # 2. Telegram botni to'g'ridan-to'g'ri va barqaror asinxron rejimda ishga tushiramiz
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
