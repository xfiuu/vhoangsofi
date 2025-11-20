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
# Tăng nhẹ thời gian grab để tránh các bot tranh nhau gửi request cùng 1 mili giây
GRAB_TIMES = [3.7, 3.9, 4.1] 

running_bots = []

# --- Hàm xử lý chính ---

async def click_and_message(message, grab_index, delay, bot, account_info):
    await asyncio.sleep(delay)
    try:
        print(f"[{account_info['channel_id']}] → 🏁 {bot.user.name} đang tìm nút vị trí {grab_index+1}...")

        fetched_message = None
        found_buttons = []
        
        # Thử 5 lần, mỗi lần cách nhau 2s (giảm spam request so với 1s cũ)
        for i in range(5): 
            try:
                fetched_message = await message.channel.fetch_message(message.id)
                found_buttons = []
                for action_row in fetched_message.components:
                    for component in action_row.children:
                        if isinstance(component, discord.Button):
                             found_buttons.append(component)
                
                if len(found_buttons) >= 3:
                    break
            except Exception as e:
                # In lỗi nhỏ nếu fetch thất bại (có thể do rate limit nhẹ)
                print(f"[{bot.user.name}] Thử tìm nút thất bại (lần {i+1}): {e}")
                pass
            await asyncio.sleep(2) # Tăng thời gian nghỉ lên 2s

        if len(found_buttons) > grab_index:
            target_button = found_buttons[grab_index]
            await asyncio.sleep(0.5) # Nghỉ nhẹ trước khi click thật
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
                await target_channel.send("st z")
        except:
            pass

# Thêm tham số startup_delay để đăng nhập tuần tự
async def run_account(account, grab_index, grab_time, startup_delay):
    # Đợi trước khi bắt đầu phiên đăng nhập này
    if startup_delay > 0:
        print(f"⏳ Đang đợi {startup_delay}s trước khi đăng nhập tài khoản tiếp theo...")
        await asyncio.sleep(startup_delay)

    bot = commands.Bot(command_prefix="!", self_bot=True)

    @bot.event
    async def on_ready():
        print(f"[{account['channel_id']}] → ✅ Đăng nhập thành công: {bot.user}")
        running_bots.append(bot)

    @bot.event
    async def on_message(message):
        if message.author.id == SOFI_ID and str(message.channel.id) == account["channel_id"]:
            content = message.content.lower()
            if "dropping" in content or "thả" in content:
                print(f"[DEBUG] -> 🔎 Phát hiện drop! {bot.user.name} chuẩn bị click nút...")
                asyncio.create_task(click_and_message(message, grab_index, grab_time, bot, account))

    try:
        await bot.start(account["token"])
    except Exception as e:
        print(f"❌ Lỗi đăng nhập {account['token'][:6]}...: {e}")

async def drop_loop():
    print("⏳ Đang đợi TẤT CẢ các tài khoản đăng nhập xong...")
    while len(running_bots) < len(accounts):
        await asyncio.sleep(5) # Kiểm tra mỗi 5s
    
    print(f"🚀 Đã sẵn sàng {len(running_bots)}/{len(accounts)} tài khoản. Bắt đầu auto drop.")
    # Đợi thêm 10s cho ổn định hẳn
    await asyncio.sleep(10)

    i = 0
    while True:
        try:
            bot = running_bots[i % len(running_bots)]
            acc = accounts[i % len(accounts)]
            channel = bot.get_channel(int(acc["channel_id"]))
            if channel:
                await channel.send("sd")
                print(f"[{acc['channel_id']}] → 🤖 {bot.user.name} đã gửi 'sd'")
            
            i += 1
            await asyncio.sleep(250) 

        except Exception as e:
            print(f"Lỗi vòng lặp drop: {e}")
            await asyncio.sleep(60) # Nếu lỗi, nghỉ 1 phút rồi thử lại

async def main():
    threading.Thread(target=keep_alive, daemon=True).start()
    tasks = []
    for i, acc in enumerate(accounts):
        if acc.get("token"):
            grab_index = GRAB_INDICES[i % len(GRAB_INDICES)]
            grab_time = GRAB_TIMES[i % len(GRAB_TIMES)]
            
            # QUAN TRỌNG: Mỗi bot đăng nhập cách nhau 10 giây
            startup_delay = i * 10 
            
            tasks.append(run_account(acc, grab_index, grab_time, startup_delay))
    
    if tasks:
        # Chạy drop_loop song song với việc các bot đang đăng nhập từ từ
        tasks.append(drop_loop())
        await asyncio.gather(*tasks)
    else:
        print("Chưa cấu hình token nào trong file .env!")

if __name__ == "__main__":
    asyncio.run(main())


