import asyncio
import random
import string
import json
import os
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
_owner_id_raw = os.environ.get("OWNER_ID")
if not BOT_TOKEN:
    raise RuntimeError(
        "Переменная окружения BOT_TOKEN не задана. "
        "На Railway: Project -> Variables -> добавить BOT_TOKEN."
    )
if not _owner_id_raw:
    raise RuntimeError(
        "Переменная окружения OWNER_ID не задана. "
        "На Railway: Project -> Variables -> добавить OWNER_ID (число)."
    )
try:
    OWNER_ID = int(_owner_id_raw)
except ValueError:
    raise RuntimeError("OWNER_ID должен быть числом (ваш Telegram user id).")

DATA_FILE = "bot_data.json"
KEY_FILE = "encryption_key.bin"

# --- ПОСТОЯННЫЙ КЛЮЧ ШИФРОВАНИЯ ---
def load_encryption_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

ENCRYPTION_KEY = load_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Состояния FSM ---
class InviteStates(StatesGroup):
    waiting_for_invite = State()
    waiting_for_pin = State()
    waiting_for_new_pin = State()

# --- Мусорные символы (пул A, "сырьё" для шума) ---
GARBAGE_POOL = [
    '⺀','⺁','⺂','⺃','⺄','⺅','⺆','⺇','⺈','⺉',
    '⺊','⺋','⺌','⺍','⺎','⺏','⺐','⺑','⺒','⺓',
    '⺔','⺕','⺖','⺗','⺘','⺙','⺛','⺜','⺝','⺞',
    '⺟','⺠','⺡','⺢','⺣','⺤','⺥','⺦','⺧','⺨',
    '⺩','⺪','⺫','⺬','⺭','⺮','⺯','⺰','⺱','⺲',
    '⺳','⺴','⺵','⺶','⺷','⺸','⺹','⺺','⺻','⺼',
    '⺽','⺾','⺿','⻀','⻁','⻂','⻃','⻄','⻅','⻆',
    '⻇','⻈','⻉','⻊','⻋','⻌','⻍','⻎','⻏','⻐',
    '⻑','⻒','⻓','⻔','⻕','⻖','⻗','⻘','⻙','⻚',
    '⻛','⻜','⻝','⻞','⻟','⻠','⻡','⻢','⻣','⻤',
    '⻥','⻦','⻧','⻨','⻩','⻪','⻫','⻬','⻭','⻮',
    '㐀','㐁','㐂','㐃','㐄','㐅','㐆','㐇','㐈','㐉',
    '㐊','㐋','㐌','㐍','㐎','㐏','㐐','㐑','㐒','㐓',
    '㐔','㐕','㐖','㐗','㐘','㐙','㐚','㐛','㐜','㐝',
    '㐞','㐟','㐠','㐡','㐢','㐣','㐤','㐥','㐦','㐧',
]

# --- Основной пул иероглифов (пул B, "сырьё" для шифра) ---
MAIN_GLYPHS = [
    'あ','い','う','え','お','か','き','く','け','こ',
    'さ','し','す','せ','そ','た','ち','つ','て','と',
    'な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ',
    'ま','み','む','め','も','や','ゆ','よ','ら','り',
    'る','れ','ろ','わ','を','ん','ア','イ','ウ','エ',
    'オ','カ','キ','ク','ケ','コ','サ','シ','ス','セ',
    'ソ','タ','チ','ツ','テ','ト','ナ','ニ','ヌ','ネ',
    'ノ','ハ','ヒ','フ','ヘ','ホ','マ','ミ','ム','メ',
    'モ','ヤ','ユ','ヨ','ラ','リ','ル','レ','ロ','ワ',
    'ヲ','ン','ァ','ィ','ゥ','ェ','ォ','ャ','ュ','ョ','ッ',
    '一','丁','七','万','丈','三','上','下','不','与',
    '丐','丑','专','且','世','丘','丙','业','丛','东',
    '丝','丞','丢','两','严','丧','个','中','丰','串',
    '临','丸','丹','为','主','丽','举','乃','久','么',
    '义','之','乌','乍','乎','乏','乐','乒','乓','乔',
    '乖','乘','乙','九','乞','也','习','乡','书','买',
    '乱','乳','了','予','争','事','二','于','云','互',
    '五','井','亚','些','亡','亢','交','亥','亦','产',
    '亨','亩','享','京','亭','亮','亲','人','亿','什',
    '仁','仅','仆','仇','今','介','仍','从','仑','仓',
    '仔','仕','他','仗','付','仙','代','令','以','们',
    '仪','仰','仲','件','价','任','份','企','伊','伍',
    '가','나','다','라','마','바','사','아','자','차',
    '카','타','파','하','거','너','더','러','머','버',
    '서','어','저','처','커','터','퍼','허','겨','녀',
    '뎌','려','며','벼','셔','여','져','쳐','켜','텨',
    '펴','혀','고','노','도','로','모','보','소','오',
    '조','초','코','토','포','호','구','누','두','루',
    '무','부','수','우','주','추','쿠','투','푸','후',
    '그','느','드','르','므','브','스','으','즈','츠',
    '크','트','프','흐','기','니','디','리','미','비',
    '시','이','지','치','키','티','피','히',
    'ا','ب','ت','ث','ج','ح','خ','د','ذ','ر',
    'ز','س','ش','ص','ض','ط','ظ','ع','غ','ف',
    'ق','ك','ل','م','ن','ه','و','ي','آ','أ',
    'ؤ','ئ','ة','ى','ء',
    '华','夏','国','民','共','和','党','军','队','族',
    '家','乡','土','天','地','日','月','星','光','明',
    '暗','黑','白','红','黄','蓝','绿','紫','金','银',
    '铜','铁','钢','木','林','森','水','火','山','石',
    '田','云','风','雨','雷','电','雪','霜','冰','冷',
    '热','温','暖','凉','寒','暑','秋','冬','春','年',
    '时','分','秒','世','界','宇','宙','银','河','花',
    '草','树','叶','果','实','米','饭','菜','肉','鱼',
    '鸟','兽','虫','龙','凤','虎','豹','狼','熊','猫',
    '狗','兔','马','牛','羊','鸡','鸭','鹅','鸽','燕',
    '雀','鹰','鹤','鹿','象','鲸','鲨','贝','龟','蛇',
    '蛙','蝶','蜂','蚁','蚊','蝇','蜘','蛛','蝎','蜈',
    '蚣','蜗','爱','恨','情','仇','喜','怒','哀','乐',
    '悲','欢','离','合','生','死','病','老','苦','难',
    '福','寿','康','宁','安','全','平','吉','祥','如',
    '意','招','财','进','宝','富','贵','荣','官','运',
    '亨','通','事','业','成','功','学','有','庭','幸',
    '身','体','健','心','想','万','永','恒','久','远',
    '长','青','春','驻','好','圆','团','圆',
]

# Явно задаём каждый символ отдельно, включая ё и Ё
ALL_CHARS_LIST = [
    'а','б','в','г','д','е','ё','ж','з','и','й','к','л','м','н','о','п','р','с','т','у','ф','х','ц','ч','ш','щ','ъ','ы','ь','э','ю','я',
    'А','Б','В','Г','Д','Е','Ё','Ж','З','И','Й','К','Л','М','Н','О','П','Р','С','Т','У','Ф','Х','Ц','Ч','Ш','Щ','Ъ','Ы','Ь','Э','Ю','Я',
    'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',
    'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
    '0','1','2','3','4','5','6','7','8','9',
    '.',',','!','?',':',';','(',')','[',']','{','}','\'','"','-','_','=','+','*','/','\\','|','@','#','$','%','^','&','~',
]

# =========================================================================
# ШИФР v3
# =========================================================================
MIX_SEED = 733221
CODEWORD_LENGTH = 4
VARIANTS_PER_CHAR = 20
CIPHER_SHARE = 0.60
OVERLAP_RATIO = 0.15

_map_rng = random.Random(MIX_SEED)
_combined_glyphs = list(dict.fromkeys(MAIN_GLYPHS + GARBAGE_POOL))
_map_rng.shuffle(_combined_glyphs)

_n = len(_combined_glyphs)
_cipher_end = int(_n * CIPHER_SHARE)
_overlap_len = int(_n * OVERLAP_RATIO)
_noise_start = max(_cipher_end - _overlap_len, 0)

CIPHER_POOL = _combined_glyphs[:_cipher_end]
NOISE_POOL = _combined_glyphs[_noise_start:]

# =========================================================================
# ЯКОРЯ ИЗ КИТАЙСКО-ЯПОНСКИХ ИЕРОГЛИФОВ
# =========================================================================
ANCHOR_SEED = 991137
ANCHOR_LENGTH = 3
ANCHOR_VARIANTS_COUNT = 20

_CJK_BLOCK_START = 0x4E00
_CJK_BLOCK_END = 0x9FFF

_anchor_rng = random.Random(ANCHOR_SEED)
_existing_glyphs = set(_combined_glyphs)

def _build_anchor_glyph_pool(size: int = 400) -> list:
    codepoints = list(range(_CJK_BLOCK_START, _CJK_BLOCK_END + 1))
    _anchor_rng.shuffle(codepoints)
    pool = []
    for cp in codepoints:
        glyph = chr(cp)
        if glyph not in _existing_glyphs:
            pool.append(glyph)
            if len(pool) >= size:
                break
    return pool

_ANCHOR_GLYPH_POOL = _build_anchor_glyph_pool()

_used_anchors = set()

def _generate_unique_anchor() -> str:
    while True:
        anchor = ''.join(_anchor_rng.choice(_ANCHOR_GLYPH_POOL) for _ in range(ANCHOR_LENGTH))
        if anchor not in _used_anchors:
            _used_anchors.add(anchor)
            return anchor

ANCHOR_START_VARIANTS = [_generate_unique_anchor() for _ in range(ANCHOR_VARIANTS_COUNT)]
ANCHOR_END_VARIANTS = [_generate_unique_anchor() for _ in range(ANCHOR_VARIANTS_COUNT)]

# Пробел шифруется наравне со всеми остальными символами
char_list = ALL_CHARS_LIST + [' ']

# Проверка наличия ё и Ё
assert 'ё' in char_list, "Символ 'ё' отсутствует в списке для шифрования!"
assert 'Ё' in char_list, "Символ 'Ё' отсутствует в списке для шифрования!"

ENCRYPTION_MAP = {}
DECRYPTION_MAP = {}
_used_codewords = set()

def _generate_unique_codeword():
    while True:
        codeword = tuple(_map_rng.choice(CIPHER_POOL) for _ in range(CODEWORD_LENGTH))
        if codeword not in _used_codewords:
            _used_codewords.add(codeword)
            return codeword

for _ch in char_list:
    _variants = [_generate_unique_codeword() for _ in range(VARIANTS_PER_CHAR)]
    ENCRYPTION_MAP[_ch] = _variants
    for _cw in _variants:
        DECRYPTION_MAP[_cw] = _ch

# Отладка
print(f"Символ 'ё' в ENCRYPTION_MAP: {'ё' in ENCRYPTION_MAP}")
print(f"Символ 'Ё' в ENCRYPTION_MAP: {'Ё' in ENCRYPTION_MAP}")
print(f"Количество вариантов для 'ё': {len(ENCRYPTION_MAP.get('ё', []))}")
print(f"Количество вариантов для 'Ё': {len(ENCRYPTION_MAP.get('Ё', []))}")
print(f"Пример кодового слова для 'ё': {ENCRYPTION_MAP.get('ё', [['НЕТ']])[0]}")
print(f"Пример кодового слова для 'Ё': {ENCRYPTION_MAP.get('Ё', [['НЕТ']])[0]}")

# --- Мусор между кодовыми словами ---
GARBAGE_MAX_RUN = 2
GARBAGE_INSERT_CHANCE = 0.45

def get_garbage_sequence():
    length = random.randint(1, GARBAGE_MAX_RUN)
    return ''.join(random.choice(NOISE_POOL) for _ in range(length))

def _maybe_garbage(result: list) -> None:
    if random.random() < GARBAGE_INSERT_CHANCE:
        result.append(get_garbage_sequence())

# --- Мусор ВНУТРИ кодового слова ---
INTRA_GARBAGE_MAX = 2
INTRA_GARBAGE_CHANCE = 0.35

def _maybe_intra_garbage(result: list) -> None:
    if random.random() < INTRA_GARBAGE_CHANCE:
        length = random.randint(1, INTRA_GARBAGE_MAX)
        result.append(''.join(random.choice(NOISE_POOL) for _ in range(length)))

# --- Функции шифрования/дешифрования ---
def encrypt_text(text: str) -> str:
    start_anchor = random.choice(ANCHOR_START_VARIANTS)
    end_anchor = random.choice(ANCHOR_END_VARIANTS)
    result = []
    _maybe_garbage(result)
    for char in text:
        if char in ENCRYPTION_MAP:
            codeword = random.choice(ENCRYPTION_MAP[char])
            for idx, glyph in enumerate(codeword):
                result.append(glyph)
                if idx < len(codeword) - 1:
                    _maybe_intra_garbage(result)
        else:
            # Символ не в таблице - шифруем принудительно через UNICODE
            print(f"⚠️ Символ '{char}' (U+{ord(char):04X}) не найден в таблице, шифруем как есть")
            result.append(char)
        _maybe_garbage(result)
    return start_anchor + ''.join(result) + end_anchor

def _try_match_codeword(body: str, i: int, n: int):
    g1 = body[i]
    for gap1 in range(0, INTRA_GARBAGE_MAX + 1):
        pos2 = i + 1 + gap1
        if pos2 >= n:
            break
        g2 = body[pos2]
        for gap2 in range(0, INTRA_GARBAGE_MAX + 1):
            pos3 = pos2 + 1 + gap2
            if pos3 >= n:
                break
            g3 = body[pos3]
            for gap3 in range(0, INTRA_GARBAGE_MAX + 1):
                pos4 = pos3 + 1 + gap3
                if pos4 >= n:
                    break
                g4 = body[pos4]
                candidate = (g1, g2, g3, g4)
                match = DECRYPTION_MAP.get(candidate)
                if match is not None:
                    return match, pos4 + 1
    return None

def decrypt_text(text: str) -> str:
    body = text[3:-3]
    result = []
    i = 0
    n = len(body)
    while i < n:
        # Проверяем, не является ли текущий символ "обычным"
        if body[i] not in CIPHER_POOL and body[i] not in NOISE_POOL:
            result.append(body[i])
            i += 1
            continue
        matched = _try_match_codeword(body, i, n)
        if matched is not None:
            char, next_i = matched
            result.append(char)
            i = next_i
            continue
        i += 1
    return ''.join(result)

def is_encrypted_text(text: str) -> bool:
    if len(text) < 6:
        return False
    return text[:3] in ANCHOR_START_VARIANTS and text[-3:] in ANCHOR_END_VARIANTS

# --- Работа с данными ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except:
            return {}
    return {}

def save_data(data):
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted_data = cipher_suite.encrypt(json_str.encode('utf-8'))
    with open(DATA_FILE, 'wb') as f:
        f.write(encrypted_data)

data = load_data()

def init_data():
    if "users" not in data:
        data["users"] = {}
    if "invites" not in data:
        data["invites"] = {}
    if "owner_invites" not in data:
        data["owner_invites"] = []
    save_data(data)

init_data()

def generate_invite_code():
    return ''.join(random.choices(string.digits, k=6))

def is_invite_valid(code: str) -> bool:
    if code not in data["invites"]:
        return False
    invite = data["invites"][code]
    if invite.get("used", False):
        return False
    created_at = datetime.fromisoformat(invite["created_at"])
    if datetime.now() - created_at > timedelta(hours=4):
        return False
    return True

def is_session_active(user_id: int) -> bool:
    user_id_str = str(user_id)
    if user_id_str not in data["users"]:
        return False
    session_end = datetime.fromisoformat(data["users"][user_id_str]["session_end"])
    return datetime.now() < session_end

def create_invite(user_id: int) -> str:
    user_id_str = str(user_id)
    code = generate_invite_code()
    while code in data["invites"]:
        code = generate_invite_code()
    data["invites"][code] = {
        "created_by": user_id_str,
        "created_at": datetime.now().isoformat(),
        "used": False
    }
    if user_id_str == str(OWNER_ID):
        data["owner_invites"].append(code)
    else:
        if user_id_str not in data["users"]:
            data["users"][user_id_str] = {}
        data["users"][user_id_str]["invite_code"] = code
    save_data(data)
    return code

# --- Обработчики команд ---
@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if user_id == str(OWNER_ID):
        if user_id not in data["users"]:
            session_end = datetime.now() + timedelta(hours=4)
            data["users"][user_id] = {
                "pin": "admin",
                "session_end": session_end.isoformat(),
                "invite_used": False,
                "invite_code": None
            }
            save_data(data)
            await message.answer(
                "👑 Добро пожаловать, Хозяин!\n\n"
                "📋 Доступные команды:\n"
                "/start - показать это сообщение\n"
                "/invite - создать инвайт-код для друга\n\n"
                "🔐 Сессия активна!\n"
                "Отправьте текст для шифрования или расшифровки."
            )
            return
        else:
            session_end = datetime.now() + timedelta(hours=4)
            data["users"][user_id]["session_end"] = session_end.isoformat()
            save_data(data)
            await message.answer(
                "👑 Хозяин, сессия обновлена!\n\n"
                "📋 Доступные команды:\n"
                "/start - показать это сообщение\n"
                "/invite - создать инвайт-код\n\n"
                "Отправьте текст для шифрования или расшифровки."
            )
            return

    if user_id not in data["users"]:
        await message.answer("🔐 Ты не из наших, пуск только по инвайт-коду.\nВведите 6-значный код приглашения:")
        await state.set_state(InviteStates.waiting_for_invite)
        return

    if is_session_active(message.from_user.id):
        await message.answer(
            "✅ Ваша сессия активна!\n\n"
            "📋 Доступные команды:\n"
            "/start - показать это сообщение\n"
            "/invite - создать инвайт-код для друга (1 раз)\n\n"
            "Отправьте текст для шифрования или расшифровки."
        )
        return

    await message.answer("⏰ Ваша сессия истекла.\nВведите ваш пин-код для восстановления сессии:")
    await state.set_state(InviteStates.waiting_for_pin)

@dp.message(InviteStates.waiting_for_invite)
async def process_invite(message: Message, state: FSMContext):
    invite_code = message.text.strip()
    user_id = str(message.from_user.id)

    if user_id == str(OWNER_ID):
        await message.answer("👑 Хозяин, вам не нужен инвайт. Просто напишите /start")
        await state.clear()
        return

    if not invite_code.isdigit() or len(invite_code) != 6:
        await message.answer("❌ Неверный формат. Инвайт-код должен состоять из 6 цифр. Попробуйте снова:")
        return

    if not is_invite_valid(invite_code):
        await message.answer("❌ Недействительный или использованный инвайт-код. Попробуйте снова:")
        return

    session_end = datetime.now() + timedelta(hours=4)
    data["users"][user_id] = {
        "pin": "",
        "session_end": session_end.isoformat(),
        "invite_used": False,
        "invite_code": None
    }
    data["invites"][invite_code]["used"] = True

    creator_id = data["invites"][invite_code]["created_by"]
    if creator_id != str(OWNER_ID) and creator_id in data["users"]:
        data["users"][creator_id]["invite_used"] = True

    save_data(data)
    await message.answer("✅ Инвайт-код принят!\nПридумайте пин-код от 4 до 8 символов (буквы/цифры):")
    await state.set_state(InviteStates.waiting_for_new_pin)

@dp.message(InviteStates.waiting_for_new_pin)
async def process_new_pin(message: Message, state: FSMContext):
    pin = message.text.strip()
    user_id = str(message.from_user.id)

    if user_id == str(OWNER_ID):
        await message.answer("👑 Хозяин, вы уже зарегистрированы.")
        await state.clear()
        return

    if len(pin) < 4 or len(pin) > 8:
        await message.answer("❌ Пин-код должен быть от 4 до 8 символов. Попробуйте снова:")
        return

    data["users"][user_id]["pin"] = pin
    save_data(data)

    await message.answer(
        "✅ Пин-код установлен! Сессия активна 4 часа.\n\n"
        "📋 Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/invite - создать инвайт-код для друга (1 раз)\n\n"
        "Отправьте текст для шифрования или расшифровки."
    )
    await state.clear()

@dp.message(InviteStates.waiting_for_pin)
async def process_pin(message: Message, state: FSMContext):
    pin = message.text.strip()
    user_id = str(message.from_user.id)

    if user_id == str(OWNER_ID):
        await message.answer("👑 Хозяин, вам не нужен пин-код. Просто напишите /start")
        await state.clear()
        return

    if user_id not in data["users"]:
        await message.answer("❌ Пользователь не найден. Напишите /start")
        await state.clear()
        return

    if data["users"][user_id]["pin"] != pin:
        await message.answer("❌ Неверный пин-код. Попробуйте снова:")
        return

    session_end = datetime.now() + timedelta(hours=4)
    data["users"][user_id]["session_end"] = session_end.isoformat()
    save_data(data)

    await message.answer(
        "✅ Сессия восстановлена!\n\n"
        "📋 Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/invite - создать инвайт-код для друга (1 раз)\n\n"
        "Отправьте текст для шифрования или расшифровки."
    )
    await state.clear()

@dp.message(Command("invite"))
async def create_invite_command(message: Message):
    user_id = str(message.from_user.id)

    if user_id == str(OWNER_ID):
        code = create_invite(int(user_id))
        await message.answer(f"👑 Хозяин, инвайт-код создан: {code}\nДействует 4 часа.", parse_mode="Markdown")
        return

    if user_id not in data["users"]:
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return

    if data["users"][user_id].get("invite_used", False):
        await message.answer("❌ Вы уже использовали свой шанс создать инвайт-код.")
        return

    if not is_session_active(int(user_id)):
        await message.answer("❌ Ваша сессия истекла. Напишите /start для восстановления.")
        return

    code = create_invite(int(user_id))
    await message.answer(f"✅ Инвайт-код создан: {code}\nДействует 4 часа.", parse_mode="Markdown")

@dp.message()
async def handle_text(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)

    if user_id not in data["users"] and user_id != str(OWNER_ID):
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return

    if user_id == str(OWNER_ID):
        pass
    elif not is_session_active(int(user_id)):
        await message.answer("⏰ Ваша сессия истекла. Напишите /start для восстановления.")
        return

    text = message.text
    if text.startswith('/'):
        return

    if is_encrypted_text(text):
        try:
            decrypted = decrypt_text(text)
            if not decrypted or not decrypted.strip():
                await message.answer("⚠️ Результат расшифровки пуст. Возможно, сообщение повреждено или не является зашифрованным.")
            else:
                await message.answer(decrypted)
        except Exception as e:
            await message.answer(f"❌ Ошибка расшифровки: {str(e)}")
    else:
        try:
            encrypted = encrypt_text(text)
            if not encrypted or not encrypted.strip():
                await message.answer("⚠️ Результат шифрования пуст.")
            else:
                await message.answer(encrypted)
        except Exception as e:
            await message.answer(f"❌ Ошибка шифрования: {str(e)}")

@dp.errors()
async def errors_handler(update, exception):
    print(f"Ошибка: {exception}")
    return True

async def main():
    print("🤖 Бот запущен!")
    print(f"👑 Хозяин: {OWNER_ID}")
    print(f"📊 CODEWORD_LENGTH: {CODEWORD_LENGTH}")
    print(f"📊 VARIANTS_PER_CHAR: {VARIANTS_PER_CHAR}")
    print(f"📊 Всего кодовых слов в шифре: {len(_used_codewords)}")
    print(f"📊 Размер шифровальной зоны: {len(CIPHER_POOL)} глифов")
    print(f"📊 Размер мусорной зоны: {len(NOISE_POOL)} глифов")
    print(f"👥 Зарегистрировано пользователей: {len(data.get('users', {}))}")
    print(f"🔍 Проверка 'ё': {len(ENCRYPTION_MAP.get('ё', []))} вариантов")
    print(f"🔍 Проверка 'Ё': {len(ENCRYPTION_MAP.get('Ё', []))} вариантов")
    print(f"🔍 'ё' есть в ALL_CHARS_LIST: {'ё' in ALL_CHARS_LIST}")
    print(f"🔍 'Ё' есть в ALL_CHARS_LIST: {'Ё' in ALL_CHARS_LIST}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
