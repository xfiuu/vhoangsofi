import discord
from discord.ext import commands
import asyncio
import os
import threading
from keep_alive import keep_alive

# --- Cấu hình ---
# CHÚ Ý: Chỉ điền đúng số lượng tài khoản bạn thực sự dùng.
# Nếu dùng 3 acc, chỉ để 3 dòng này.
accounts = [
    {"token": os.getenv("TOKEN1"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN2"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN3"), "channel_id": os.getenv("CHANNEL_ID")},
]

SOFI_ID = 853629533855809596
try:
    KTB_CHANNEL_ID = int(os.getenv("KTB_CHANNEL_ID")) 
except (ValueError, TypeError):
    KTB_CHANNEL_ID = None

# Thay vì emoji cố định, ta dùng INDEX (vị trí).
# 0 = Reaction đầu tiên (trái tim 1)
# 1 = Reaction thứ hai (trái tim 2)
# 2 = Reaction thứ ba (trái tim 3)
GRAB_INDICES = [0, 1, 2] 
GRAB_TIMES = [2, 2.3, 3.2]

running_bots = []

# --- Hàm xử lý chính ---

async def react_and_message(message, grab_index, delay, bot, account_info):
    """Đợi, sau đó nhặt reaction TẠI VỊ TRÍ chỉ định."""
    await asyncio.sleep(delay)
    
    try:
        # Cực kỳ quan trọng: Phải fetch lại tin nhắn để thấy các reaction mà Sofi vừa thả
        fetched_message = await message.channel.fetch_message(message.id)
        
        if fetched_message.reactions and len(fetched_message.reactions) > grab_index:
            # Lấy đúng reaction mà Sofi đã dùng
            target_reaction = fetched_message.reactions[grab_index]
            
            # Bot thả reaction đó
            await fetched_message.add_reaction(target_reaction.emoji)
            print(f"[{account_info['channel_id']}] → Acc {bot.user} đã nhặt vị trí {grab_index+1} (Emoji: {target_reaction.emoji})")
        else:
             print(f"[{account_info['channel_id']}] → Acc {bot.user} không thấy reaction số {grab_index+1} để nhặt.")

    except Exception as e:
        print(f"[{account_info['channel_id']}] → Lỗi khi nhặt: {e}")
    
    await asyncio.sleep(2)
    
    if KTB_CHANNEL_ID:
        try:
            target_channel = bot.get_channel(KTB_CHANNEL_ID)
            if target_channel:
                await target_channel.send("sb")
        except:
            pass

async def run_account(account, grab_index, grab_time):
    bot = commands.Bot(command_prefix="!", self_bot=True)

    @bot.event
    async def on_ready():
        print(f"[{account['channel_id']}] → Đăng nhập thành công: {bot.user}")
        running_bots.append(bot)

    @bot.event
    async def on_message(message):
        if message.author.id == SOFI_ID and \
           ("is dropping" in message.content or "đã thả thẻ" in message.content) and \
           str(message.channel.id) == account["channel_id"]:
            
            # Truyền grab_index thay vì emoji cố định
            asyncio.create_task(react_and_message(message, grab_index, grab_time, bot, account))

    try:
        await bot.start(account["token"])
    except Exception as e:
        print(f"Lỗi đăng nhập {account['token'][:6]}...: {e}")

async def drop_loop():
    print("Đang đợi các tài khoản đăng nhập...")
    while len(running_bots) < len(accounts):
        await asyncio.sleep(1)
    print(f"Đã sẵn sàng {len(running_bots)}/{len(accounts)} tài khoản. Bắt đầu auto drop.")

    i = 0
    while True:
        try:
            bot = running_bots[i % len(running_bots)]
            acc = accounts[i % len(accounts)]
            channel = bot.get_channel(int(acc["channel_id"]))
            if channel:
                await channel.send("sd")
                print(f"[{acc['channel_id']}] → {bot.user} đã gửi 'sd'")
        except Exception as e:
            print(f"Lỗi drop: {e}")
        
        i += 1
        await asyncio.sleep(245) # 4 phút 5 giây

async def main():
    threading.Thread(target=keep_alive, daemon=True).start()
    tasks = []
    for i, acc in enumerate(accounts):
        if acc.get("token"):
            # Lấy index tương ứng cho acc này
            grab_index = GRAB_INDICES[i % len(GRAB_INDICES)]
            grab_time = GRAB_TIMES[i % len(GRAB_TIMES)]
            tasks.append(run_account(acc, grab_index, grab_time))
    
    if tasks:
        tasks.append(drop_loop())
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
