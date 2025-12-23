import os
import asyncio
import requests
import random
from asyncio import run as arun, Task
from highrise import BaseBot, User, Position
from highrise.__main__ import BotDefinition, main as run_bot
import json
from typing import Optional
from emotes_data import emotes

# استفاده از Replit AI Integrations برای OpenAI
# این سرویس OpenAI-compatible API access را بدون نیاز به API key فراهم می‌کند
AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

# Chat completions API endpoint (DISABLED - caused URL errors)
# BASE_URL = "http://127.0.0.1:3000/chat/completions"

class Emote:
    def __init__(self, name: str, id: str, duration: float, is_free: bool):
        self.name = name
        self.id = id
        self.duration = duration
        self.is_free = is_free

class RadioManager:
    """مدیر رادیو برای پخش موسیقی و رادیو آنلاین"""
    def __init__(self):
        self.current_station = None
        self.is_playing = False
        self.stations = {
            "1": {
                "name": "Rap Sad",
                "url": "https://goodmusic.musitraf.com/rap-sad/Bote-Tanha.mp3?src=goodmusic"
            },
            "2": {
                "name": "Chill Hop / Lofi Beats",
                "url": "https://ice5.somafm.com/chillits-128-mp3"
            },
            "3": {
                "name": "SomaFM n5MD (Electronic / Melodic)",
                "url": "https://ice5.somafm.com/n5md-128-mp3"
            },
            "4": {
                "name": "Frisky Radio (Dance)",
                "url": "http://stream2.friskyradio.com:8000/frisky_mp3_hi"
            }
        }
    
    async def set_radio(self, bot_instance, station_key: str) -> bool:
        """تنظیم رادیو و ارسال لینک"""
        if station_key in self.stations:
            self.current_station = self.stations[station_key]
            self.is_playing = True
            station = self.current_station
            
            message = f"""📻 {station['name']} فعال شد!

🔗 لینک رادیو:
{station['url']}

🎮 لینک رو کپی کن و داخل Radio Game بذار"""
            
            await bot_instance.highrise.chat(message)
            return True
        await bot_instance.highrise.chat(f"❌ رادیو {station_key} موجود نیست. دستورات: !radio 1/2/3")
        return False
    
    async def stop_radio(self, bot_instance):
        """متوقف کردن رادیو"""
        self.current_station = None
        self.is_playing = False
        await bot_instance.highrise.chat("🛑 رادیو متوقف شد!")
    
    async def list_stations(self, bot_instance):
        """نمایش لیست رادیو‌های موجود"""
        stations_list = "\n".join([f"{k}: {v['name']}" for k, v in self.stations.items()])
        await bot_instance.highrise.chat(f"""📻 رادیو‌های موجود:
{stations_list}

دستور: !radio [شماره]
مثال: !radio 1""")

class Spam24:
    """سیستم اسپم 24 ساعته برای پیام‌های تکراری"""
    def __init__(self, bot):
        self.bot = bot
        self.task: Optional[Task] = None
        self.active = False
        self.message = ""
        self.interval = 3600  # یک ساعت

    async def start(self, message: str, interval: int = 3600):
        """شروع اسپم 24 ساعته"""
        self.active = True
        self.message = message
        self.interval = interval
        print(f"🔄 اسپم 24 ساعته شروع شد: {message} (هر {interval} ثانیه)")
        try:
            while self.active:
                await self.bot.highrise.chat(message)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            print("🛑 اسپم 24 ساعته متوقف شد")
        except Exception as e:
            print(f"❌ خطا در اسپم 24 ساعته: {e}")

    def stop(self):
        """توقف اسپم 24 ساعته"""
        self.active = False
        if self.task:
            self.task.cancel()

def ask_bot(question):
    """پاسخ ثابت بدون درخواست به URL خارجی"""
    return "برای دریافت رایگان این بات به @king_4626 پیام دهید 🤍😆"

TRIGGER_MESSAGE = "1111"

class HighriseBot(BaseBot):
    """A feature-rich Highrise bot with Persian language support"""
    
    def __init__(self):
        super().__init__()
        self.ghost_mode = False
        self.spam_system = {
            'active': False,
            'task': None,
            'message': '',
            'interval': 5.0
        }
        self.spam24 = Spam24(self)  # سیستم اسپم 24 ساعته
        self.player_positions = {}  # ذخیره مختصات بازیکن‌ها
        self.radio_manager = RadioManager()  # مدیر رادیو
        self.balance = {}  # سیستم تیپ و موجودی گلد
        self.current_outfit = None
        self.outfit_api_url = os.getenv("OUTFIT_API_URL")
        self.outfit_api_token = os.getenv("OUTFIT_API_TOKEN")
        self.outfits = {
            1: {"id": "outfit_id_1", "name": "لباس اول"},
            2: {"id": "outfit_id_2", "name": "لباس دوم"},
            3: {"id": "outfit_id_3", "name": "لباس سوم"}
        }
        self.auto_replies = {
            "سلام": "سلام خوش اومدی 🤍",
            "چطوری": "خوبم قربانت 😄",
            "چه خبر": "سلامتی 😎",
            "دنس": "برای دنس عدد 1 تا 225 رو بفرست 🎭",
            "فلوس": "فلوس در حال اجراست 😎",
            "بات رایگان": "برای دریافت رایگان این بات به @king_4626 پیام بده 🤍",
            "خدانگهدار": "خدانگهدار، روز خوبی داشته باشی! 😇",
            "خوابیدی": "نه هنوز بیدارم 😴",
            "چی کار می‌کنی": "دارم با تو گپ می‌زنم 😎",
            "خسته شدم": "یه استراحت کن، بعد دوباره ادامه بده 💪",
            "دوستت دارم": "منم دوستت دارم ❤️",
            "میای بازی کنیم": "حتماً! چه بازی می‌خوای انجام بدیم؟ 🎮",
            "کی میای": "به زودی 😄",
            "کی رفتی": "هنوز نرفتم 😅",
            "نظر تو چیه": "نظر من همیشه مثبت 😎",
            "داداش": "چیه داداش؟ 😎",
            "داداش خوبی": "خوبم مرسی تو چطوری؟ 😄",
            "چی خبر": "همه چی عالیه 😎",
            "چه کار کنیم": "هرچی تو بخوای 😄",
            "دلم برات تنگ شده": "منم دلم برات تنگ شده 😢",
            "جواب بده": "من همیشه جواب می‌دم 😎",
            "فلان": "چی؟ 😅",
            "کی هستی": "من باتت هستم 🤖",
            "کی ساخته": "@king_4626 ساخته منو 😎",
            "ایران": "میهن عزیز ما 🇮🇷",
            "تهران": "پایتخت ایران 🌆",
            "مشهد": "شهری مقدس 🌸",
            "اصفهان": "زیبا و تاریخی 🏛️",
            "شیراز": "شهر شعر و ادب 🌹",
            "تبریز": "شهری با فرهنگ و تاریخ 🏙️",
            "بزن بریم": "آره بزن بریم 😎",
            "فلوس کن": "در حال فلوس زدن 😎",
            "دنبال کن": "من دنبال می‌کنم 👀",
            "موزیک بزن": "آهنگ در حال پخش 🎶",
            "رقص": "برای رقص عدد 1 تا 225 رو بفرست 💃",
            "سوال": "هر سوالی داری بپرس، من جواب می‌دم 🤖",
            "چیکار کنیم": "هرچی تو بخوای 😎",
            "کی اومد": "هنوز نیومده 😅",
            "کی رفت": "هنوز نرفته 😅",
            "حالت چطوره": "عالی 😄",
            "چی میخوای": "هرچی تو بخوای 😎",
            "بفرست": "ارسال شد 😎",
            "پینگ": "پونگ! 🏓",
            "چی شد": "همه چی خوبه 😎",
            "ممنون": "خواهش میکنم 🤍",
            "مرسی": "قربانت 😄",
            "اوکی": "اوکی 😎",
            "باشه": "باشه 😎",
            "همه چی خوبه": "عالی 😎",
            "نه": "نه 😅",
            "اره": "اره 😄",
            "آره": "آره 😎",
            "سلامتی": "به سلامتی! 🥂",
            "خوبم": "خوبم قربانت 😄",
            "عالی": "عالیه 😎",
            "خوشحال": "منم خوشحالم 😄",
            "ناراحت": "چرا ناراحتی؟ 😢",
            "کی میره": "هنوز کسی نرفته 😅",
            "کی میاد": "به زودی 😎",
            "منتظرتم": "منم منتظرتم 😄",
            "کجایی": "من همیشه اینجام 🤖",
            "چی میگی": "همه چی خوبه 😎",
            "دریافت ربات": "برای دریافت رایگان این ربات به آیدی @prHR488 در روبیکا پیام دهید.\nسازنده ربات @king_4626 است.",
            "فلان کار": "باشه انجام می‌دم 😎",
            "چی کار کردی": "هنوز کاری نکردم 😅",
            "چه خبر تازه": "هیچی خاص 😎",
            "دستت درد نکنه": "قربانت 😄",
            "آفرین": "مرسی 😎",
            "دمت گرم": "قربانت 😄",
            "مرسی داداش": "قربانت 😎",
            "داداش خوبی": "خوبم مرسی 😄",
            "چه کار کنیم": "هرچی تو بخوای 😎",
            "فلوس بزن": "در حال فلوس زدن 😎",
            "رقص شروع": "برای رقص عدد 1 تا 225 رو بفرست 💃",
            "رقص کن": "رقص شروع شد 💃",
            "سلام بات": "سلام 😎",
            "ربات": "من باتت هستم 🤖",
            "هوش مصنوعی": "آره، من یه هوش مصنوعی هستم 🤖",
            "چی بگم": "هرچی دوست داری 😎",
            "پیام بده": "پیام ارسال شد 😎",
            "ارسال": "ارسال شد 😎",
            "فالو کن": "دنبال کردم 👀",
            "فلوس فعال": "فلوس در حال اجراست 😎",
            "فلوس دائم": "فلوس بدون توقف 😎",
            "برای دنس": "عدد 1 تا 225 رو بفرست 🎭",
            "پی وی": "برای دریافت بات رایگان به @king_4626 پیام بده 🤍",
            "رایگان": "برای دریافت رایگان به @king_4626 پیام بده 🤍",
            "بریم": "بزن بریم 😎",
            "شروع": "شروع شد 😎",
            "خاموش": "خاموش شد 😴",
            "روشن": "روشن شد 😎",
        }
        self.emotes = emotes
        self.emotes_list = [emote.name for emote in emotes]
        self.emotes_dict = {
            "Kawaii Go Go": {"id": "dance-kawai", "duration": 10.85, "is_free": True},
            "Hyped": {"id": "emote-hyped", "duration": 7.62, "is_free": True},
            "Levitate": {"id": "emoji-halo", "duration": 6.52, "is_free": True},
            "Rest": {"id": "sit-idle-cute", "duration": 17.73, "is_free": False},
            "Hero Pose": {"id": "idle-hero", "duration": 22.33, "is_free": True},
            "Uhmmm": {"id": "emote-thought", "duration": 27.43, "is_free": False},
            "Crouch": {"id": "idle-crouched", "duration": 28.27, "is_free": False},
            "Zero Gravity": {"id": "emote-astronaut", "duration": 13.93, "is_free": True},
            "Zombie Run": {"id": "emote-zombierun", "duration": 10.05, "is_free": True},
            "Wait": {"id": "dance-wait", "duration": 9.92, "is_free": False},
            "Dab": {"id": "emote-dab", "duration": 3.75, "is_free": True},
            "Ignition Boost": {"id": "hcc-jetpack", "duration": 27.45, "is_free": False},
            "Do The Worm": {"id": "emote-snake", "duration": 6.63, "is_free": True},
            "Bummed": {"id": "idle-loop-sad", "duration": 21.80, "is_free": True},
            "Chillin'": {"id": "idle-loop-happy", "duration": 19.80, "is_free": True},
            "Sweet Smooch": {"id": "emote-kissing", "duration": 6.69, "is_free": True},
            "emoji-shush": {"id": "emoji-shush", "duration": 3.40, "is_free": True},
            "idle_tough": {"id": "idle_tough", "duration": 28.64, "is_free": True},
            "emote-fail3": {"id": "emote-fail3", "duration": 7.06, "is_free": True},
            "emote-shocked": {"id": "emote-shocked", "duration": 5.59, "is_free": True},
            "emote-theatrical-test": {"id": "emote-theatrical-test", "duration": 10.86, "is_free": True},
            "emote-fireworks": {"id": "emote-fireworks", "duration": 13.15, "is_free": True},
            "emote-electrified": {"id": "emote-electrified", "duration": 5.29, "is_free": True},
            "idle-headless": {"id": "idle-headless", "duration": 41.80, "is_free": True},
            "emote-armcannon": {"id": "emote-armcannon", "duration": 8.67, "is_free": True},
            "dance-tiktok4": {"id": "dance-tiktok4", "duration": 15.00, "is_free": True},
            "dance-tiktok7": {"id": "dance-tiktok7", "duration": 13.89, "is_free": True},
            "Don't Touch Dance": {"id": "dance-tiktok13", "duration": 9.24, "is_free": True},
            "Hip Hop Dance": {"id": "dance-hiphop", "duration": 27.59, "is_free": True},
            "emote-hopscotch": {"id": "emote-hopscotch", "duration": 5.84, "is_free": True},
            "emote-outfit2": {"id": "emote-outfit2", "duration": 11.94, "is_free": True},
            "emote-pose12": {"id": "emote-pose12", "duration": 5.81, "is_free": True},
            "emote-fading": {"id": "emote-fading", "duration": 14.05, "is_free": True},
            "emote-pose13": {"id": "emote-pose13", "duration": 6.39, "is_free": True},
            "profile-breakscreen": {"id": "profile-breakscreen", "duration": 10.70, "is_free": True},
            "emote-surf": {"id": "emote-surf", "duration": 19.01, "is_free": True},
            "emote-cartwheel": {"id": "emote-cartwheel", "duration": 7.94, "is_free": True},
            "emote-kissing-passionate": {"id": "emote-kissing-passionate", "duration": 10.47, "is_free": True},
            "dance-tiktok1": {"id": "dance-tiktok1", "duration": 12.42, "is_free": True},
            "run-vertical": {"id": "run-vertical", "duration": 3.86, "is_free": False},
            "emote-flirt": {"id": "emote-flirt", "duration": 7.95, "is_free": True},
            "emote-receive-disappointed": {"id": "emote-receive-disappointed", "duration": 7.14, "is_free": True},
            "emote-gooey": {"id": "emote-gooey", "duration": 5.82, "is_free": True},
            "emote-oops": {"id": "emote-oops", "duration": 8.02, "is_free": True},
            "walk-vertical": {"id": "walk-vertical", "duration": 4.18, "is_free": False},
            "emote-thief": {"id": "emote-thief", "duration": 6.89, "is_free": True},
            "emote-sheephop": {"id": "emote-sheephop", "duration": 3.78, "is_free": True},
            "emote-runhop": {"id": "emote-runhop", "duration": 8.72, "is_free": True},
            "dance-tiktok15": {"id": "dance-tiktok15", "duration": 16.11, "is_free": True},
            "emote-receive-happy": {"id": "emote-receive-happy", "duration": 5.94, "is_free": True},
            "dance-tiktok6": {"id": "dance-tiktok6", "duration": 11.99, "is_free": True},
            "emote-confused2": {"id": "emote-confused2", "duration": 10.06, "is_free": True},
            "Muscle pose": {"id": "emote-pose4", "duration": 6.08, "is_free": True},
            "emote-dinner": {"id": "emote-dinner", "duration": 14.25, "is_free": True},
            "emote-wavey": {"id": "emote-wavey", "duration": 12.60, "is_free": True},
            "emote-pose2": {"id": "emote-pose2", "duration": 7.20, "is_free": True},
            "dance-shuffle": {"id": "dance-shuffle", "duration": 9.05, "is_free": True},
            "emote-twitched": {"id": "emote-twitched", "duration": 9.61, "is_free": True},
            "emote-juggling": {"id": "emote-juggling", "duration": 5.83, "is_free": True},
            "idle-dance-tiktok6": {"id": "idle-dance-tiktok6", "duration": 9.73, "is_free": True},
            "emote-opera": {"id": "emote-opera", "duration": 5.76, "is_free": True},
            "dance-tiktok3": {"id": "dance-tiktok3", "duration": 10.40, "is_free": True},
            "dance-kid": {"id": "dance-kid", "duration": 10.30, "is_free": True},
            "dance-anime3": {"id": "dance-anime3", "duration": 12.37, "is_free": True},
            "dance-tiktok16": {"id": "dance-tiktok16", "duration": 11.02, "is_free": True},
            "Poke dance": {"id": "dance-tiktok12", "duration": 14.85, "is_free": True},
            "dance-tiktok5": {"id": "dance-tiktok5", "duration": 12.20, "is_free": True},
            "idle-cold": {"id": "idle-cold", "duration": 17.71, "is_free": True},
            "emote-pose11": {"id": "emote-pose11", "duration": 5.11, "is_free": True},
            "emote-handwalk": {"id": "emote-handwalk", "duration": 7.77, "is_free": True},
            "emote-dramatic": {"id": "emote-dramatic", "duration": 9.10, "is_free": True},
            "emote-outfit": {"id": "emote-outfit", "duration": 13.20, "is_free": True},
            "idle-phone": {"id": "idle-phone", "duration": 31.36, "is_free": False},
            "sit-chair": {"id": "sit-chair", "duration": 3.30, "is_free": True},
            "idle-space": {"id": "idle-space", "duration": 37.78, "is_free": True},
            "mining-mine": {"id": "mining-mine", "duration": 5.02, "is_free": True},
            "mining-success": {"id": "mining-success", "duration": 3.11, "is_free": True},
            "mining-fail": {"id": "mining-fail", "duration": 3.41, "is_free": True},
            "Landing a Fish!": {"id": "fishing-pull", "duration": 2.81, "is_free": True},
            "Now We Wait...": {"id": "fishing-idle", "duration": 17.87, "is_free": True},
            "Casting!": {"id": "fishing-cast", "duration": 2.82, "is_free": True},
            "We Have a Strike!": {"id": "fishing-pull-small", "duration": 3.67, "is_free": True},
            "Hip Shake": {"id": "dance-hipshake", "duration": 13.38, "is_free": True},
            "Fruity Dance": {"id": "dance-fruity", "duration": 18.25, "is_free": True},
            "Cheer": {"id": "dance-cheerleader", "duration": 17.93, "is_free": True},
            "Magnetic": {"id": "dance-tiktok14", "duration": 11.20, "is_free": True},
            "Blowing Kisses": {"id": "emote-blowkisses", "duration": 5.98, "is_free": False},
            "Fairy Twirl": {"id": "emote-looping", "duration": 9.89, "is_free": True},
            "Fairy Float": {"id": "idle-floating", "duration": 27.60, "is_free": True},
            "Karma Dance": {"id": "dance-wild", "duration": 16.25, "is_free": True},
            "Moonlit Howl": {"id": "emote-howl", "duration": 8.10, "is_free": True},
            "Nocturnal Howl": {"id": "idle-howl", "duration": 48.62, "is_free": True},
            "Trampoline": {"id": "emote-trampoline", "duration": 6.11, "is_free": True},
            "Launch": {"id": "emote-launch", "duration": 10.88, "is_free": True},
            "Cute Salute": {"id": "emote-cutesalute", "duration": 3.79, "is_free": True},
            "At Attention": {"id": "emote-salute", "duration": 4.79, "is_free": True},
            "Wop Dance": {"id": "dance-tiktok11", "duration": 11.37, "is_free": True},
            "Push It": {"id": "dance-employee", "duration": 8.55, "is_free": True},
            "This Is For You!": {"id": "emote-gift", "duration": 6.09, "is_free": True},
            "Sweet Little Moves": {"id": "dance-touch", "duration": 13.15, "is_free": True},
            "Repose": {"id": "sit-relaxed", "duration": 31.21, "is_free": True},
            "Sleigh Ride": {"id": "emote-sleigh", "duration": 12.51, "is_free": True},
            "Gimme Attention!": {"id": "emote-attention", "duration": 5.65, "is_free": True},
            "Jingle Hop": {"id": "dance-jinglebell", "duration": 12.09, "is_free": True},
            "Timejump": {"id": "emote-timejump", "duration": 5.51, "is_free": True},
            "Gotta Go!": {"id": "idle-toilet", "duration": 33.48, "is_free": True},
            "Bit Nervous": {"id": "idle-nervous", "duration": 22.81, "is_free": True},
            "Scritchy": {"id": "idle-wild", "duration": 27.35, "is_free": True},
            "Ice Skating": {"id": "emote-iceskating", "duration": 8.41, "is_free": True},
            "Laid Back": {"id": "sit-open", "duration": 27.28, "is_free": True},
            "Party Time!": {"id": "emote-celebrate", "duration": 4.35, "is_free": True},
            "Shrink": {"id": "emote-shrink", "duration": 9.99, "is_free": True},
            "Arabesque": {"id": "emote-pose10", "duration": 5.00, "is_free": True},
            "Bashful Blush": {"id": "emote-shy2", "duration": 6.34, "is_free": True},
            "Possessed Puppet": {"id": "emote-puppet", "duration": 17.89, "is_free": True},
            "Revelations": {"id": "emote-headblowup", "duration": 13.66, "is_free": True},
            "Watch Your Back": {"id": "emote-creepycute", "duration": 9.01, "is_free": True},
            "Creepy Puppet": {"id": "dance-creepypuppet", "duration": 7.79, "is_free": True},
            "Saunter Sway": {"id": "dance-anime", "duration": 9.60, "is_free": True},
            "Groovy Penguin": {"id": "dance-pinguin", "duration": 12.81, "is_free": True},
            "Air Guitar": {"id": "idle-guitar", "duration": 14.15, "is_free": True},
            "Ready To Rumble": {"id": "emote-boxer", "duration": 6.75, "is_free": True},
            "Celebration Step": {"id": "emote-celeb