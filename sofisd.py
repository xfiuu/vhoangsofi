import discord
from discord.ext import commands
import asyncio
import os
import threading
from keep_alive import keep_alive

# --- Cấu hình ---
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

# --- Hàm xử lý chính (ĐÃ NÂNG CẤP LÊN BUTTON) ---

async def click_and_message(message, grab_index, delay, bot, account_info):
    await asyncio.sleep(delay)
    try:
        print(f"[{account_info['channel_id']}] → 🏁 {bot.user.name} đang tìm nút vị trí {grab_index+1}...")

        # 1. Tìm tin nhắn và đợi Button xuất hiện
        fetched_message = None
        found_buttons = []
        
        for i in range(5): # Thử 5 lần, mỗi lần 1s
            try:
                fetched_message = await message.channel.fetch_message(message.id)
                
                # Lọc ra tất cả các Button từ tin nhắn
                found_buttons = []
                for action_row in fetched_message.components:
                    for component in action_row.children:
                        # Chỉ lấy component là Button (loại trừ menu, link...)
                        if isinstance(component, discord.Button):
                             found_buttons.append(component)
                
                # Nếu tìm thấy ít nhất 3 nút (3 thẻ), thì dừng tìm kiếm
                if len(found_buttons) >= 3:
                    break
            except:
                pass
            await asyncio.sleep(1)

        # 2. Bấm nút theo vị trí
        if len(found_buttons) > grab_index:
            target_button = found_buttons[grab_index]
            # --- LỆNH QUAN TRỌNG NHẤT: CLICK ---
            await target_button.click() 
            print(f"[{account_info['channel_id']}] → 🖱️ {bot.user.name} ĐÃ CLICK nút vị trí {grab_index+1}!")
        else:
            print(f"[{account_info['channel_id']}] → ❌ {bot.user.name} KHÔNG TÌM THẤY NÚT (Tìm thấy {len(found_buttons)} nút).")

    except Exception as e:
        print(f"[{account_info['channel_id']}] → ⚠️ Lỗi CLICK của {bot.user.name}: {e}")
    
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
        if message.author.id == SOFI_ID and str(message.channel.id) == account["channel_id"]:
            content = message.content.lower()
            if "dropping" in content or "thả" in content:
                print(f"[DEBUG] -> ✅ Phát hiện drop! {bot.user.name} chuẩn bị click nút...")
                # Gọi hàm CLICK mới thay vì hàm REACT cũ
                asyncio.create_task(click_and_message(message, grab_index, grab_time, bot, account))

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
