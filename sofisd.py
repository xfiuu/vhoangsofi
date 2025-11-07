import discord
from discord.ext import commands
import asyncio
import os
import threading
from keep_alive import keep_alive

# --- Cấu hình ---
# CHÚ Ý: Đảm bảo số lượng dòng ở đây khớp với số token trong file .env
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

GRAB_INDICES = [0, 1, 2] 
GRAB_TIMES = [1.3, 2.3, 3.2]

running_bots = []

# --- Hàm xử lý chính ---

async def react_and_message(message, grab_index, delay, bot, account_info):
    await asyncio.sleep(delay)
    try:
        # --- DEBUG MỚI: In ra thời điểm bắt đầu nhặt ---
        print(f"[{account_info['channel_id']}] → 🏁 {bot.user.name} bắt đầu quy trình nhặt vị trí {grab_index+1}...")

        fetched_message = None
        for i in range(5):
            try:
                fetched_message = await message.channel.fetch_message(message.id)
                if len(fetched_message.reactions) >= 3:
                    break
            except:
                pass
            # --- DEBUG MỚI: In ra số reaction hiện tại ---
            current_reactions = len(fetched_message.reactions) if fetched_message else 0
            print(f"   ... (Acc {bot.user.name} lần thử {i+1}: thấy {current_reactions} nút)")
            await asyncio.sleep(1)

        if fetched_message and len(fetched_message.reactions) > grab_index:
            target_reaction = fetched_message.reactions[grab_index]
            await fetched_message.add_reaction(target_reaction.emoji)
            print(f"[{account_info['channel_id']}] → ✅ {bot.user.name} ĐÃ NHẶT vị trí {grab_index+1} (Emoji: {target_reaction.emoji})")
        else:
            print(f"[{account_info['channel_id']}] → ❌ {bot.user.name} KHÔNG TÌM THẤY NÚT vị trí {grab_index+1} sau 5 giây.")

    except Exception as e:
        print(f"[{account_info['channel_id']}] → ⚠️ Lỗi nhặt của {bot.user.name}: {e}")
    
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
        # --- DEBUG QUAN TRỌNG: In ra MỌI tin nhắn từ Sofi trong kênh này ---
        if message.author.id == SOFI_ID and str(message.channel.id) == account["channel_id"]:
             print(f"\n[DEBUG] Sofi vừa nhắn trong kênh {account['channel_id']}:")
             print(f"   → Nội dung: '{message.content}'")
             print(f"   → Có chứa 'is dropping'? {'CÓ' if 'is dropping' in message.content else 'KHÔNG'}")
             print(f"   → Có chứa 'đã thả thẻ'? {'CÓ' if 'đã thả thẻ' in message.content else 'KHÔNG'}")

        # Kiểm tra điều kiện để nhặt
        if message.author.id == SOFI_ID and \
           ("is dropping" in message.content or "đã thả thẻ" in message.content) and \
           str(message.channel.id) == account["channel_id"]:
            
            print(f"[DEBUG] -> ✅ ĐIỀU KIỆN ĐÚNG! Kích hoạt nhặt cho {bot.user.name}")
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
        await asyncio.sleep(245)

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
