import asyncio
import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from PIL import Image, ImageDraw, ImageFont

# ================= НАСТРОЙКИ =================

BOT_TOKEN = os.getenv("8345555276:AAGQZOZ4lzDtO84oUDBsIv2rP4E_42JPuBk")  # Railway env
OWNER_ID = 6560956429  # ТВОЙ TG ID

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
PROMO_FILE = f"{DATA_DIR}/promocodes.json"
PACKAGES_FILE = f"{DATA_DIR}/packages.json"
PAYMENTS_FILE = f"{DATA_DIR}/payments.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ================= БАЗА =================

def load(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
    with open(file, "r") as f:
        return json.load(f)

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ================= INIT =================

bot = Bot(8345555276:AAGQZOZ4lzDtO84oUDBsIv2rP4E_42JPuBk)
dp = Dispatcher()

# ================= КНОПКИ =================

def user_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Мои пакеты", callback_data="my_packages")
    kb.button(text="🛒 Купить пакет", callback_data="buy_menu")
    kb.adjust(1)
    kb.button(text="🎁 Активировать промокод", callback_data="activate_promo")
    return kb.as_markup()

def buy_menu():
    packages = load(PACKAGES_FILE, [])
    kb = InlineKeyboardBuilder()
    for p in packages:
        kb.button(
            text=f"{p['name']} — {p['price']}⭐",
            callback_data=f"buy_{p['id']}"
        )
    kb.adjust(1)
    return kb.as_markup()

# ================= СТАРТ =================

@dp.message(F.text)
async def start(msg: types.Message):
    users = load(USERS_FILE, {})
    uid = str(msg.from_user.id)

    if uid not in users:
        users[uid] = {
            "username": msg.from_user.username,
            "packages": []
        }
        save(USERS_FILE, users)

    await msg.answer(
        "👋 Добро пожаловать!\nВыбери действие:",
        reply_markup=user_menu()
    )

# ================= ПОКУПКА =================

@dp.callback_query(F.data.startswith("buy_"))
async def buy(cb: types.CallbackQuery):
    package_id = cb.data.split("_")[1]
    packages = load(PACKAGES_FILE, [])
    package = next(p for p in packages if p["id"] == package_id)

    prices = [LabeledPrice(label=package["name"], amount=package["price"])]

    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"Покупка пакета {package['name']}",
        description=package["description"],
        payload=f"pkg:{package_id}:{cb.from_user.id}",
        currency="XTR",  # TELEGRAM STARS
        prices=prices
    )

# ================= ЗАЩИТА =================

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

# ================= УСПЕШНАЯ ОПЛАТА =================

@dp.message(F.successful_payment)
async def success(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    _, package_id, user_id = payload.split(":")

    users = load(USERS_FILE, {})
    packages = load(PACKAGES_FILE, [])
    payments = load(PAYMENTS_FILE, [])

    package = next(p for p in packages if p["id"] == package_id)

    expires = (
        datetime.now() + timedelta(days=package["days"])
    ).strftime("%Y-%m-%d %H:%M")

    users[user_id]["packages"].append({
        "name": package["name"],
        "expires": expires
    })

    payment_id = f"PAY-{len(payments)+1:05d}"

    payments.append({
        "payment_id": payment_id,
        "user_id": user_id,
        "package": package["name"],
        "stars": package["price"],
        "time": datetime.now().isoformat()
    })

    save(USERS_FILE, users)
    save(PAYMENTS_FILE, payments)

    receipt_path = generate_receipt(
        payment_id,
        msg.from_user.username or user_id,
        package["name"],
        package["price"]
    )

    await msg.answer_photo(
        photo=types.FSInputFile(receipt_path),
        caption=(
            f"✅ Пакет **{package['name']}** активирован!\n"
            f"⏳ До: {expires}"
        ),
        parse_mode="Markdown"
    )

# ================= МОИ ПАКЕТЫ =================

@dp.callback_query(F.data == "my_packages")
async def my_packages(cb: types.CallbackQuery):
    users = load(USERS_FILE, {})
    uid = str(cb.from_user.id)
    packs = users[uid]["packages"]

    if not packs:
        await cb.message.answer("❌ У тебя нет активных пакетов")
        return

    text = "📦 Твои пакеты:\n\n"
    for p in packs:
        text += f"• {p['name']} — до {p['expires']}\n"

    await cb.message.answer(text)

# ================= ЧЕК (КАРТИНКА) =================

def generate_receipt(payment_id, user, package, stars):
    img = Image.new("RGB", (600, 400), "#111111")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    lines = [
        "TELEGRAM STARS RECEIPT",
        "",
        f"Payment ID: {payment_id}",
        f"User: @{user}",
        f"Package: {package}",
        f"Paid: {stars} ⭐",
        "",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]

    y = 40
    for line in lines:
        draw.text((40, y), line, fill="white", font=font)
        y += 40

    path = f"{DATA_DIR}/{payment_id}.png"
    img.save(path)
    return path

# ================= ЗАПУСК =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
