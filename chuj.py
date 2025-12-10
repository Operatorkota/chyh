import asyncio
import discord
from discord.ext import tasks
from twitchio.ext import commands

# ================= KONFIGURACJA =================



# ================= KOD BOTA =================

# Zmienna globalna (na początku pusta, wypełnimy ją w main)
twitch_bot = None
is_stream_live = False

# Konfiguracja Discorda
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# Konfiguracja Twitcha
class MyTwitchBot(commands.Bot):
    def __init__(self):
        # Tutaj nastąpiła zmiana dla wersji 2.9.0
        super().__init__(token=TWITCH_TOKEN, prefix='!', initial_channels=[TWITCH_CHANNEL_NAME])

    async def event_ready(self):
        print(f'✅ Twitch Bot gotowy: {self.nick}')

    async def event_message(self, message):
        if message.echo:
            return

        print(f'[Twitch] {message.author.name}: {message.content}')

        # Wysyłanie na Discorda
        discord_channel = discord_client.get_channel(DISCORD_CHAT_CHANNEL_ID)
        if discord_channel:
            clean_msg = message.content.replace('@', '')
            await discord_channel.send(f"🟣 **{message.author.name}**: {clean_msg}")

        await self.handle_commands(message)

# --- FUNKCJA 1: AUTOMATYCZNE POWIADOMIENIA O LIVE ---
@tasks.loop(seconds=60)
async def check_live_status():
    global is_stream_live
    global twitch_bot
    
    # Jeśli bot jeszcze nie powstał, czekamy
    if twitch_bot is None:
        return

    try:
        # Fetch streams wymaga listy nazw kanałów
        streams = await twitch_bot.fetch_streams(user_logins=[TWITCH_CHANNEL_NAME])
        
        if streams:
            stream_info = streams[0]
            
            if not is_stream_live:
                is_stream_live = True
                print("🔴 Stream wystartował! Wysyłam info na Discorda.")
                
                channel = discord_client.get_channel(DISCORD_LIVE_CHANNEL_ID)
                if channel:
                    await channel.send(
                        f"@everyone 🔴 **Wbijajcie na stream!**\n"
                        f"Tytuł: {stream_info.title}\n"
                        f"Gra: {stream_info.game_name}\n"
                        f"Link: https://twitch.tv/{TWITCH_CHANNEL_NAME}"
                    )
        else:
            if is_stream_live:
                print("⚫ Stream zakończony.")
            is_stream_live = False

    except Exception as e:
        print(f"Błąd statusu live: {e}")

# --- FUNKCJA 2: DISCORD -> TWITCH (RELAY) ---
@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    if message.channel.id == DISCORD_CHAT_CHANNEL_ID:
        global twitch_bot
        if twitch_bot is None: return

        twitch_chan = twitch_bot.get_channel(TWITCH_CHANNEL_NAME)
        
        if twitch_chan:
            print(f'[Discord] {message.author.name}: {message.content}')
            await twitch_chan.send(f"[Discord] {message.author.display_name}: {message.content}")

@discord_client.event
async def on_ready():
    print(f'✅ Discord Bot gotowy: {discord_client.user}')
    if not check_live_status.is_running():
        check_live_status.start()

# --- URUCHAMIANIE ---
async def main():
    global twitch_bot
    
    # TU BYŁ BŁĄD: Tworzymy bota dopiero TERAZ, wewnątrz pętli
    twitch_bot = MyTwitchBot()

    loop = asyncio.get_running_loop()
    
    # Startujemy Discorda w tle
    loop.create_task(discord_client.start(DISCORD_TOKEN))
    
    # Startujemy Twitcha
    await twitch_bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Zamykanie botów...")