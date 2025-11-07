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

# Vị trí cần nhặt (0 = thẻ đầu tiên bên trái, 1 = giữa, 2 = bên phải)
GRAB_INDICES = [0, 1, 2] 
GRAB_TIMES = [1.3, 2.3, 3.2]

running_bots = []

# --- Hàm xử lý chính ---

async def react_and_message(message, grab_index, delay, bot, account_info):
    """Đợi reaction xuất hiện và nhặt theo vị trí, có in debug chi tiết."""
    # Đợi thời gian delay đã cấu hình cho từng acc
    await asyncio.sleep(delay)
    
    try:
        # Vòng lặp thử tìm reaction trong 5 giây (mỗi lần thử cách nhau 1s)
        fetched_message = None
        for i in range(5):
            try:
                fetched_message = await message.channel.fetch_message(message.id)
                # Nếu đã thấy đủ 3 reaction thì thoát vòng lặp ngay
                if len(fetched_message.reactions) >= 3:
                    break
            except:
                pass # Bỏ qua lỗi mạng tạm thời nếu có
            print(f"[{account_info['channel_id']}] → ⏳ {bot.user.name} đang đợi Sofi load nút... (lần thử {i+1}/5)")
            await asyncio.sleep(1)

        # --- Bắt đầu nhặt ---
        if fetched_message and len(fetched_message.reactions) > grab_index:
            # Lấy chính xác emoji mà Sofi đang dùng
            target_reaction = fetched_message.reactions[grab_index]
            emoji_to_use = target_reaction.emoji
            
            # Bot thả reaction
            await fetched_message.add_reaction(emoji_to_use)
            print(f"[{account_info['channel_id']}] → ✅ {bot.user.name} ĐÃ NHẶT vị trí {grab_index+1} (Emoji: {emoji_to_use})")
            
        else:
            # In ra debug để biết tại sao không nhặt được
            seen_reactions = [str(r.emoji) for r in fetched_message.reactions] if fetched_message else "Không lấy được tin nhắn"
            print(f"[{account_info['channel_id']}] → ❌ {bot.user.name} KHÔNG TÌM THẤY NÚT tại vị trí {grab_index+1}!")
            print(f"   → Bot chỉ nhìn thấy các nút này: {seen_reactions}")

    except discord.Forbidden:
        print(f"[{account_info['channel_id']}] → 🚫 {bot.user.name} BỊ CHẶN (không có quyền thả reaction tại kênh này).")
    except Exception as e:
        print(f"[{account_info['channel_id']}] → ⚠️ Lỗi lạ khi {bot.user.name} nhặt: {e}")
    
    # Đợi thêm chút rồi gửi lệnh kiểm tra balance
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
        # Kiểm tra đúng bot Sofi và đúng nội dung drop
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
