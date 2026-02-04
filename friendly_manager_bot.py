import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from groq import Groq

# ================= LOAD ENV =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DISCORD_TOKEN = os.getenv("NEW_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("NEW_BOT_TOKEN missing in .env")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing in .env")

# ================= GROQ =================
client = Groq(api_key=GROQ_API_KEY)

# ================= IDS =================
MAIN_OWNER_ID = 1415779292809269267
SERVER_OWNER_ID = 1415779292809269266

CONTROL_CHANNEL_ID = 1468203743152443526

STAFF_ROLE_IDS = [1415779292809269265]
MEMBER_ROLE_IDS = [1427211355227820134]

# ================= MODERATION FLAGS =================
AUTO_MODERATION = True
STRICTNESS_LEVEL = "medium"  # low | medium | high

# ================= BAD WORD LIST =================
BAD_WORDS = {
    "fuck", "fuk", "shit", "bitch", "asshole",
    "lanja", "dengey", "dengei", "denge", "puku", "puk",
    "madarchod", "mc", "bc", "chod", "deng",
    "nee amma", "nee ayya"
}

# ================= DISCORD INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = (
    "You are Zoro Manager, a professional Discord community manager.\n"
    "Reply like a calm, sensible human moderator.\n"
    "Mirror the user's language exactly (English / Roman Telugu / Roman Hindi).\n"
    "Never use Telugu script characters.\n"
    "Never mention you are an AI."
)

# ================= TONE PROFILES =================
TONE_PROFILES = {
    "owner": "User is the owner. Be extremely concise, professional, factual.",
    "staff": "User is staff. Be clear, cooperative, operational.",
    "member": "User is a regular member. Be friendly and guiding.",
    "unknown": "User role unknown. Be polite and helpful."
}

# ================= HELPERS =================
def is_owner(message: discord.Message) -> bool:
    return message.author.id in (MAIN_OWNER_ID, SERVER_OWNER_ID)


def get_user_tone(message: discord.Message) -> str:
    if message.author.id in (MAIN_OWNER_ID, SERVER_OWNER_ID):
        return TONE_PROFILES["owner"]

    if message.guild:
        role_ids = [r.id for r in message.author.roles]
        if any(r in STAFF_ROLE_IDS for r in role_ids):
            return TONE_PROFILES["staff"]
        if any(r in MEMBER_ROLE_IDS for r in role_ids):
            return TONE_PROFILES["member"]

    return TONE_PROFILES["unknown"]


async def ai_reply(text: str, tone: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": tone},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=150
        )

        reply = response.choices[0].message.content.strip()
        reply = "".join(ch for ch in reply if not ("\u0C00" <= ch <= "\u0C7F"))

        return reply if reply else "cheppu, em kavali"
    except:
        return "ippudu koncham busy, malli cheppu"


async def ai_abuse_check(text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer ONLY with YES, NO, or UNCERTAIN.\n"
                        "Is this message abusive, sexual, threatening, or harassing?"
                    )
                },
                {"role": "user", "content": text}
            ],
            temperature=0,
            max_tokens=3
        )

        verdict = response.choices[0].message.content.strip().upper()
        return verdict if verdict in ("YES", "NO", "UNCERTAIN") else "NO"
    except:
        return "NO"

# ================= READY =================
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="server | always active"
        )
    )
    print(f"🟢 Zoro Manager ONLINE as {bot.user}")

# ================= WELCOME / LEAVE =================
@bot.event
async def on_member_join(member):
    try:
        await member.send(
            f"Welcome {member.name} 👋\n"
            "Server ki welcome. Em help kavali ante ikkade DM cheyyi."
        )
    except:
        pass


@bot.event
async def on_member_remove(member):
    owner = member.guild.get_member(MAIN_OWNER_ID)
    if owner:
        try:
            await owner.send(
                f"Member Left Server\n"
                f"User: {member}\n"
                f"Time: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            )
        except:
            pass

# ================= MESSAGE HANDLER =================
@bot.event
async def on_message(message):
    global AUTO_MODERATION, STRICTNESS_LEVEL

    if message.author.bot:
        return

    # ===== OWNER CONTROL PANEL =====
    if message.guild and message.channel.id == CONTROL_CHANNEL_ID:
        if not is_owner(message):
            return

        cmd = message.content.lower().strip()

        if cmd == "!zoro mod on":
            AUTO_MODERATION = True
            await message.reply("Moderation enabled.", mention_author=False)
            return

        if cmd == "!zoro mod off":
            AUTO_MODERATION = False
            await message.reply("Moderation disabled.", mention_author=False)
            return

        if cmd in ("!zoro strict low", "!zoro strict medium", "!zoro strict high"):
            STRICTNESS_LEVEL = cmd.split()[-1]
            await message.reply(
                f"Strictness set to {STRICTNESS_LEVEL.upper()}.",
                mention_author=False
            )
            return

        if cmd == "!zoro status":
            await message.reply(
                f"**Zoro Manager Status**\n\n"
                f"Moderation: {'ON' if AUTO_MODERATION else 'OFF'}\n"
                f"Strictness: {STRICTNESS_LEVEL.upper()}\n"
                f"AI Detection: ENABLED\n",
                mention_author=False
            )
            return

    # ===== MODERATION =====
    if AUTO_MODERATION and message.guild:
        text_lower = message.content.lower()

        if any(bad in text_lower for bad in BAD_WORDS):
            verdict = "YES"
        else:
            verdict = await ai_abuse_check(message.content)

        if verdict in ("YES", "UNCERTAIN"):
            try:
                if verdict == "YES":
                    await message.author.timeout(
                        timedelta(minutes=2),
                        reason="Abusive language"
                    )
                    await message.author.send(
                        "Mee language koncham strong ga undi. 2 minutes mute chesanu."
                    )
                else:
                    await message.author.send(
                        "Mee message koncham inappropriate ga undi. "
                        "Please language control cheyyi."
                    )

                owner = message.guild.get_member(MAIN_OWNER_ID)
                if owner:
                    await owner.send(
                        f"Zoro Manager – Action Report\n\n"
                        f"User: {message.author}\n"
                        f"Verdict: {verdict}\n"
                        f"Message: {message.content}\n"
                        f"Time: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
                    )
            except:
                pass
            return

    # ===== DM REPLY =====
    if isinstance(message.channel, discord.DMChannel):
        reply = await ai_reply(message.content, TONE_PROFILES["member"])
        await message.channel.send(reply)
        return

    # ===== BOT MENTION =====
    if bot.user in message.mentions:
        cleaned = message.content.replace(f"<@{bot.user.id}>", "").replace(
            f"<@!{bot.user.id}>", ""
        ).strip() or "hello"

        tone = get_user_tone(message)
        reply = await ai_reply(cleaned, tone)
        await message.reply(reply, mention_author=False)

    await bot.process_commands(message)

# ---------- RUN BOT SAFELY ----------
import time

while True:
    try:
        print("Starting Zoro Manager...")
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print("Reconnect error:", e)
        print("Retrying in 60 seconds...")
        time.sleep(60)

