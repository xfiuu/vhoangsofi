import discord
from discord.ext import commands
import asyncio
import os
import threading
from keep_alive import keep_alive

# --- Cấu hình ---
# CHÚ Ý QUAN TRỌNG: Nếu chỉ dùng 3 tài khoản, hãy xóa 3 dòng dưới đi.
# Số lượng dòng ở đây PHẢI KHỚP với số token thực tế bạn có trong file .env
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

# Vị trí cần nhặt (0, 1, 2 tương ứng với 3 thẻ từ trái qua phải)
GRAB_INDICES = [0, 1, 2] 
GRAB_TIMES = [1.3, 2.3, 3.2]

running_bots = []

# --- Hàm xử lý chính ---

async def react_and_message(message, grab_index, delay, bot, account_info):
    """Đợi reaction xuất hiện và nhặt theo vị trí, có cơ chế dự phòng."""
    await asyncio.sleep(delay)
    
    try:
        fetched_message = await message.channel.fetch_message(message.id)
        
        # Cố gắng đợi tối đa 2 giây để Sofi thả đủ 3 reaction (kiểm tra mỗi 0.5s)
        wait_count = 0
        while len(fetched_message.reactions) < 3 and wait_count < 4:
            await asyncio.sleep(0.5)
            fetched_message = await message.channel.fetch_message(message.id)
            wait_count += 1

        # --- Cố gắng nhặt theo vị trí (Ưu tiên 1) ---
        if len(fetched_message.reactions) > grab_index:
            target_reaction = fetched_message.reactions[grab_index]
            await fetched_message.add_reaction(target_reaction.emoji)
            print(f"[{account_info['channel_id']}] → ✅ {bot.user.name} đã nhặt vị trí {grab_index+1}")
            
        # --- Nếu không tìm thấy vị trí, dùng phương án dự phòng thả tim (Ưu tiên 2) ---
        else:
             print(f"[{account_info['channel_id']}] → ⚠️ Không thấy vị trí {grab_index+1}, {bot.user.name} thử thả '💖'...")
             await fetched_message.add_reaction("💖")

    except discord.Forbidden:
        print(f"[{account_info['channel_id']}] → ❌ {bot.user.name} bị chặn (không có quyền thả reaction).")
    except Exception as e:
        print(f"[{account_info['channel_id']}] → ❌ Lỗi khi {bot.user.name} nhặt: {e}")
    
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
        # Kiểm tra đúng bot Sofi và đúng nội dung drop (cả tiếng Anh và Việt)
        if message.author.id == SOFI_ID and \
           ("is dropping" in message.content or "đã thả thẻ" in message.content) and \
           str(message.channel.id) == account["channel_id"]:
            
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
                print(f"[{acc['channel_id']}] → 🤖 {bot.user.name} đã gửi 'sd'")
        except Exception as e:
            print(f"Lỗi vòng lặp drop: {e}")
        
        i += 1
        await asyncio.sleep(245) # 4 phút 5 giây

async def main():
    threading.Thread(target=keep_alive, daemon=True).start()
    tasks = []
    for i, acc in enumerate(accounts):
        if acc.get("token"):
            grab_index = GRAB_INDICES[i % len(GRAB_INDICES)]
            grab_time = GRAB_TIMES[i % len(GRAB_TIMES)]
            tasks.append(run_account(acc, grab_index, grab_time))
    
    if tasks:
        tasks.append(drop_loop())
        await asyncio.gather(*tasks)
    else:
        print("Chưa cấu hình token nào trong file .env!")

if __name__ == "__main__":
    asyncio.run(main())
