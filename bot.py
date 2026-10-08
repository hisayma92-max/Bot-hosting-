import asyncio
import logging
import os
import secrets
import shutil
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
from dotenv import load_dotenv

from database import Database

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "7740120627"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@ansar_564").strip()
UPDATES_INVITE_LINK = os.getenv("UPDATES_INVITE_LINK", "https://t.me/HT_HACKER_TEAM_OFFICIAL").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
HTML_DIR = DATA_DIR / "html"
HTML_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("hosting-bot")
db = Database(DATA_DIR / "bot.db")
router = Router()

PACKAGES = {
    "free": {"name": "🆓 Free", "ram": "128MB", "files": 3, "price": 0},
    "basic": {"name": "🥉 Basic Bot Hosting", "ram": "256MB", "files": 10, "price": 199},
    "pro": {"name": "🥈 Pro Bot Hosting", "ram": "512MB", "files": 30, "price": 399},
    "premium": {"name": "🥇 Premium Bot Hosting", "ram": "1GB", "files": 100, "price": 799},
}

class AdminState(StatesGroup):
    broadcast = State()
    update = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def save_user(message: Message):
    u = message.from_user
    username = f"@{u.username}" if u.username else "Not set"
    db.upsert_user(u.id, username, u.first_name or "", u.last_name or "")

async def profile_photo_file_id(bot: Bot, user_id: int):
    try:
        photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
        if photos.total_count:
            return photos.photos[0][-1].file_id
    except Exception:
        pass
    return None


def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Updates Channel", url=UPDATES_INVITE_LINK), InlineKeyboardButton(text="💎 Hosting Packages", callback_data="packages")],
        [InlineKeyboardButton(text="📤 Upload File", callback_data="upload"), InlineKeyboardButton(text="📁 Check Files", callback_data="files")],
        [InlineKeyboardButton(text="📊 My Usage", callback_data="usage"), InlineKeyboardButton(text="🎁 Claim Trial", callback_data="trial")],
        [InlineKeyboardButton(text="🔗 Referral", callback_data="referral"), InlineKeyboardButton(text="⬆️ Upgrade Request", callback_data="upgrade")],
        [InlineKeyboardButton(text="⚡ Bot Speed", callback_data="speed"), InlineKeyboardButton(text="📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton(text="❓ Help", callback_data="help"), InlineKeyboardButton(text="📞 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 New Update", callback_data="admin_update"), InlineKeyboardButton(text="📣 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Users", callback_data="admin_users"), InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬆️ Upgrade Requests", callback_data="admin_upgrades"), InlineKeyboardButton(text="🛠 Packages", callback_data="admin_packages")],
        [InlineKeyboardButton(text="🗃 Database Info", callback_data="admin_db"), InlineKeyboardButton(text="🏠 Main Menu", callback_data="home")],
    ])


def admin_only(call: CallbackQuery) -> bool:
    return is_admin(call.from_user.id)

@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    await save_user(message)
    u = message.from_user
    row = db.get_user(u.id)
    count = db.file_count(u.id)
    username = f"@{u.username}" if u.username else "Not set"
    p = PACKAGES.get((row["package"] or "Free").lower(), PACKAGES["free"])
    text = (f"〽️ <b>Welcome, 𝙏𝙀𝘼𝙈 𝙊𝙒𝙉𝙀𝙍!</b>\n\n"
            f"🆔 <b>Your User ID:</b>\n<code>{u.id}</code>\n\n"
            f"✳️ <b>Username:</b>\n<code>{esc(username)}</code>\n\n"
            f"🔰 <b>Status:</b> {esc(row['status'])}\n"
            f"📦 <b>Package:</b> {esc(p['name'])} (RAM {p['ram']})\n"
            f"📁 <b>Files:</b> {count} / {row['file_limit']}\n\n"
            "🌐 <b>HTML Hosting:</b> Free\n"
            "🤖 <b>Bot Hosting:</b> Paid packages available\n\n"
            "👇 <b>Use the buttons or type /help.</b>")
    if is_admin(u.id):
        text += "\n\n👑 <b>Admin:</b> /admin"
    photo_id = await profile_photo_file_id(bot, u.id)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=main_keyboard())
    else:
        await message.answer(text, reply_markup=main_keyboard())

@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Admin access only.")
    await message.answer("👑 <b>ADMIN PANEL</b>\n\nFull bot management controls are below.", reply_markup=admin_keyboard())

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.answer()
    await call.message.answer("🏠 Main menu", reply_markup=main_keyboard())

@router.callback_query(F.data == "admin")
async def admin_panel(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return await call.message.answer("❌ Admin access only.")
    await call.message.answer("👑 <b>ADMIN PANEL</b>", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return
    await call.message.answer(f"📊 <b>Admin Statistics</b>\n\n👥 Users: {db.user_count()}\n📁 Hosted HTML files: {db.total_files()}\n⬆️ Pending upgrades: {len(db.pending_upgrades(1000))}", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return
    rows = db.latest_users(15)
    lines = ["👥 <b>Latest Users</b>\n"]
    for r in rows:
        name = esc((r["first_name"] or "") + (" " + r["last_name"] if r["last_name"] else "")) or "No name"
        lines.append(f"• <code>{r['user_id']}</code> — {name} — {esc(r['package'])}")
    await call.message.answer("\n".join(lines), reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_db")
async def admin_db(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return
    await call.message.answer(f"🗃 <b>Database</b>\n\nUsers: {db.user_count()}\nFiles: {db.total_files()}\nDatabase: data/bot.db\n\nUse the server's normal backup process to back up this SQLite file.", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_packages")
async def admin_packages(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return
    lines = ["🛠 <b>Current Packages</b>\n"]
    for key, p in PACKAGES.items():
        lines.append(f"<b>{key}</b>: {p['name']} | {p['ram']} | {p['files']} files | {p['price']} BDT/month")
    lines.append("\nTo change prices/limits, edit PACKAGES in bot.py and restart.")
    await call.message.answer("\n".join(lines), reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_upgrades")
async def admin_upgrades(call: CallbackQuery):
    await call.answer()
    if not admin_only(call): return
    rows = db.pending_upgrades(20)
    if not rows:
        return await call.message.answer("✅ No pending upgrade requests.", reply_markup=admin_keyboard())
    lines = ["⬆️ <b>Pending Upgrade Requests</b>\n"]
    for r in rows:
        who = esc(r["username"] or r["first_name"] or "Unknown")
        lines.append(f"#{r['id']} — User <code>{r['user_id']}</code> — {who} — <b>{esc(r['package'])}</b>")
    lines.append("\nUse /approve REQUEST_ID or /reject REQUEST_ID")
    await call.message.answer("\n".join(lines), reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if not admin_only(call): return
    await state.set_state(AdminState.broadcast)
    await call.message.answer("📣 Send the message you want to broadcast to all registered users. Send /cancel to stop.")

@router.callback_query(F.data == "admin_update")
async def admin_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if not admin_only(call): return
    await state.set_state(AdminState.update)
    await call.message.answer("📢 Send your new update. It will be saved as the latest update and sent to all registered users. Send /cancel to stop.")

@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Cancelled.", reply_markup=admin_keyboard() if is_admin(message.from_user.id) else main_keyboard())

async def send_to_all(bot: Bot, text: str, prefix: str = ""):
    ok = failed = 0
    for uid in db.all_user_ids():
        try:
            await bot.send_message(uid, prefix + text)
            ok += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)
    return ok, failed

@router.message(AdminState.broadcast)
async def receive_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return await state.clear()
    if message.text and message.text.startswith("/"): return
    ok, failed = await send_to_all(bot, message.text or "")
    await state.clear()
    await message.answer(f"📣 Broadcast complete.\n\n✅ Sent: {ok}\n❌ Failed: {failed}", reply_markup=admin_keyboard())

@router.message(AdminState.update)
async def receive_update(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return await state.clear()
    if message.text and message.text.startswith("/"): return
    text = message.text or ""
    db.set_setting("latest_update", text)
    ok, failed = await send_to_all(bot, text, "📢 <b>NEW UPDATE</b>\n\n")
    await state.clear()
    await message.answer(f"📢 Update published.\n\n✅ Sent: {ok}\n❌ Failed: {failed}", reply_markup=admin_keyboard())

@router.message(Command("approve"))
async def approve(message: Message):
    if not is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit(): return await message.answer("Usage: /approve REQUEST_ID")
    req = int(parts[1])
    rows = db.pending_upgrades(100)
    match = next((r for r in rows if r["id"] == req), None)
    if not match: return await message.answer("❌ Pending request not found.")
    p = PACKAGES.get(match["package"].lower())
    if not p: return await message.answer("❌ Package not found.")
    db.set_package(match["user_id"], match["package"], "Paid User", p["files"])
    db.set_upgrade_status(req, "approved")
    try: await message.bot.send_message(match["user_id"], f"✅ Your upgrade to <b>{esc(p['name'])}</b> has been approved by the admin.")
    except Exception: pass
    await message.answer(f"✅ Request #{req} approved.", reply_markup=admin_keyboard())

@router.message(Command("reject"))
async def reject(message: Message):
    if not is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit(): return await message.answer("Usage: /reject REQUEST_ID")
    req = int(parts[1])
    rows = db.pending_upgrades(100)
    match = next((r for r in rows if r["id"] == req), None)
    if not match: return await message.answer("❌ Pending request not found.")
    db.set_upgrade_status(req, "rejected")
    try: await message.bot.send_message(match["user_id"], "❌ Your upgrade request was rejected. Please contact the owner.")
    except Exception: pass
    await message.answer(f"❌ Request #{req} rejected.", reply_markup=admin_keyboard())

@router.message(Command("setpackage"))
async def setpackage(message: Message):
    if not is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or parts[2].lower() not in PACKAGES:
        return await message.answer("Usage: /setpackage USER_ID free|basic|pro|premium")
    uid, key = int(parts[1]), parts[2].lower()
    p = PACKAGES[key]
    status = "Free User" if key == "free" else "Paid User"
    db.set_package(uid, p["name"], status, p["files"])
    await message.answer(f"✅ User {uid} → {p['name']}")

@router.message(Command("help"))
async def help_cmd(message: Message):
    await save_user(message)
    await message.answer("🛠 <b>Help</b>\n\n📄 HTML Hosting: upload an .html file for a public URL.\n📦 Bot Hosting: paid plans are requested through Upgrade Request.\n📁 Files: view your hosted files.\n📊 Usage: view quota.\n\n⚠️ Do not upload malware, credential stealers, spam tools, or harmful content.", reply_markup=main_keyboard())

@router.callback_query(F.data == "packages")
async def packages(call: CallbackQuery):
    await call.answer()
    lines = ["💎 <b>Hosting Packages</b>\n"]
    for p in PACKAGES.values():
        price = "Free" if p["price"] == 0 else f"{p['price']} BDT/month"
        lines.append(f"{p['name']}\nRAM: {p['ram']} • Files: {p['files']} • {price}\n")
    await call.message.answer("\n".join(lines), reply_markup=main_keyboard())

@router.callback_query(F.data == "usage")
async def usage(call: CallbackQuery):
    await call.answer(); row = db.get_user(call.from_user.id); count = db.file_count(call.from_user.id)
    await call.message.answer(f"📊 <b>My Usage</b>\n\nStatus: {esc(row['status'])}\nPackage: {esc(row['package'])}\nFiles: {count} / {row['file_limit']}", reply_markup=main_keyboard())

@router.callback_query(F.data == "files")
async def files(call: CallbackQuery):
    await call.answer(); rows = db.list_files(call.from_user.id)
    if not rows: return await call.message.answer("📁 No files uploaded yet.", reply_markup=main_keyboard())
    lines = ["📁 <b>Your Files</b>\n"]
    for f in rows: lines.append(f"• <code>{esc(f['filename'])}</code>\n  {PUBLIC_BASE_URL}/site/{f['slug']}")
    await call.message.answer("\n".join(lines), reply_markup=main_keyboard())

@router.callback_query(F.data == "upload")
async def upload_info(call: CallbackQuery):
    await call.answer(); await call.message.answer("📤 <b>Upload File</b>\n\nSend an <code>.html</code> file for free HTML hosting.", reply_markup=main_keyboard())

@router.message(F.document)
async def document_upload(message: Message, bot: Bot):
    await save_user(message)
    doc = message.document; name = doc.file_name or "file"
    if not name.lower().endswith(".html"): return await message.answer("❌ Free hosting currently accepts only .html files.")
    row = db.get_user(message.from_user.id); count = db.file_count(message.from_user.id)
    if count >= row["file_limit"]: return await message.answer("❌ Your file limit is full.")
    if doc.file_size and doc.file_size > 2 * 1024 * 1024: return await message.answer("❌ Maximum HTML file size is 2 MB.")
    slug = secrets.token_urlsafe(8).replace("-", "").replace("_", "")
    folder = HTML_DIR / slug; folder.mkdir(parents=True, exist_ok=False); path = folder / "index.html"; tmp = folder / f"upload_{secrets.token_hex(4)}.tmp"
    try:
        tg_file = await bot.get_file(doc.file_id); await bot.download_file(tg_file.file_path, tmp); tmp.replace(path)
        db.add_file(message.from_user.id, name, slug, str(path))
        await message.answer(f"✅ <b>HTML Hosted Successfully!</b>\n\n📄 File: <code>{esc(name)}</code>\n🌐 URL: <code>{PUBLIC_BASE_URL}/site/{slug}</code>", reply_markup=main_keyboard())
    except Exception as e:
        shutil.rmtree(folder, ignore_errors=True); log.exception("Upload failed: %s", e); await message.answer("❌ Upload failed.")

@router.callback_query(F.data == "trial")
async def trial(call: CallbackQuery):
    await call.answer(); await call.message.answer("🎁 <b>Trial</b>\n\nFree HTML hosting is already available. Bot-hosting trials can be enabled by the admin.", reply_markup=main_keyboard())

@router.callback_query(F.data == "upgrade")
async def upgrade(call: CallbackQuery):
    await call.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{p['name']} — {p['price']} BDT", callback_data=f"req_{k}")] for k,p in PACKAGES.items() if k != "free"] + [[InlineKeyboardButton(text="🏠 Main Menu", callback_data="home")]])
    await call.message.answer("⬆️ <b>Choose your bot-hosting package:</b>", reply_markup=kb)

@router.callback_query(F.data.startswith("req_"))
async def request_upgrade(call: CallbackQuery):
    await call.answer("Request sent")
    key = call.data[4:]
    if key not in PACKAGES: return
    rid = db.add_upgrade_request(call.from_user.id, PACKAGES[key]["name"])
    try: await call.bot.send_message(ADMIN_ID, f"⬆️ <b>New Upgrade Request</b>\n\nRequest: #{rid}\nUser: <code>{call.from_user.id}</code>\nPackage: {PACKAGES[key]['name']}\n\nUse /approve {rid} or /reject {rid}")
    except Exception: pass
    await call.message.answer(f"✅ Upgrade request #{rid} submitted. The admin will review it.", reply_markup=main_keyboard())

@router.callback_query(F.data == "referral")
async def referral(call: CallbackQuery):
    await call.answer(); me = await call.bot.me(); await call.message.answer(f"🔗 <b>Referral</b>\n\nYour referral link:\n<code>https://t.me/{me.username}?start=ref_{call.from_user.id}</code>", reply_markup=main_keyboard())

@router.callback_query(F.data == "speed")
async def speed(call: CallbackQuery):
    await call.answer(); await call.message.answer("⚡ Bot Speed: Online\n\nAsync processing is enabled.", reply_markup=main_keyboard())

@router.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    await call.answer(); await call.message.answer(f"📊 <b>Statistics</b>\n\n👥 Users: {db.user_count()}\n📁 Hosted files: {db.total_files()}", reply_markup=main_keyboard())

@router.callback_query(F.data == "help")
async def help_button(call: CallbackQuery):
    await call.answer(); await call.message.answer("🛠 <b>Help</b>\n\nUpload an .html file for free hosting. Bot hosting is available through paid packages.", reply_markup=main_keyboard())

async def site_handler(request: web.Request):
    slug = request.match_info["slug"]; folder = HTML_DIR / slug
    if not folder.is_dir(): raise web.HTTPNotFound(text="Site not found")
    file_path = folder / "index.html"
    if not file_path.is_file(): raise web.HTTPNotFound(text="Site not found")
    return web.FileResponse(file_path)

async def health_handler(request): return web.json_response({"status": "ok", "service": "telegram-hosting-bot"})

async def run_web():
    app = web.Application(); app.router.add_get("/health", health_handler); app.router.add_get("/site/{slug}", site_handler)
    runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, WEB_HOST, WEB_PORT); await site.start(); log.info("Web server listening on %s:%s", WEB_HOST, WEB_PORT)

async def main():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is missing in .env")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)); dp = Dispatcher(); dp.include_router(router); await run_web(); log.info("Bot started")
    try: await dp.start_polling(bot)
    finally: await bot.session.close()

if __name__ == "__main__": asyncio.run(main())
