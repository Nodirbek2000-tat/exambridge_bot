from environs import Env

env = Env()
env.read_env()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN = env.str("BOT_TOKEN")
# Telegram ID'lari (vergul bilan). /admin, to'lovlarni tasdiqlash va kanallar
# faqat shu odamlarga ochiq.
ADMINS = [int(x) for x in env.list("ADMINS", []) if str(x).strip().lstrip('-').isdigit()]

# ── ExamBridge sayti ──────────────────────────────────────────────────────────
# Serverda bot sayt bilan bitta Docker tarmog'ida (exambridge_net) ishlaydi,
# shuning uchun ichki manzil: http://web:8000
BACKEND_URL = env.str("BACKEND_URL", "http://web:8000").rstrip("/")
# Ichki manzilga murojaat qilganda Django shu domen nomini ko'radi (ALLOWED_HOSTS).
BACKEND_HOST = env.str("BACKEND_HOST", "exambridge.uz")
# Saytdagi TELEGRAM_BOT_API_SECRET bilan bir xil bo'lishi shart.
BOT_API_SECRET = env.str("BOT_API_SECRET")
SITE_URL = env.str("SITE_URL", "https://exambridge.uz").rstrip("/")
SUPPORT_USERNAME = env.str("SUPPORT_USERNAME", "nodirbek_shukurov1").lstrip("@")
