import discord
from discord.ext import commands
import asyncio
import os
import threading
from keep_alive import keep_alive

# --- Cấu hình ---
# Lấy thông tin tài khoản từ biến môi trường
accounts = [
    {"token": os.getenv("TOKEN1"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN2"), "channel_id": os.getenv("CHANNEL_ID")},
    {"token": os.getenv("TOKEN3"), "channel_id": os.getenv("CHANNEL_ID")},
]

# ID của bot Sofi và kênh để gửi lệnh "sb"
SOFI_ID = 853629533855809596
try:
    # discord.py-self yêu cầu ID là số nguyên (integer)
    KTB_CHANNEL_ID = int(os.getenv("KTB_CHANNEL_ID")) 
except (ValueError, TypeError):
    print("Lỗi: KTB_CHANNEL_ID không hợp lệ hoặc chưa được thiết lập trong biến môi trường.")
    KTB_CHANNEL_ID = None


# Emoji theo đúng vị trí của Sofi: ❤️ (1), ❤️ (2), ❤️ (3)
FIXED_EMOJIS = ["❤️", "❤️", "❤️", "❤️", "❤️", "❤️"]
GRAB_TIMES = [1.3, 2.3, 3.2, 1.3, 2.3, 3.2]

# Danh sách để lưu các bot đã đăng nhập thành công
running_bots = []

# --- Hàm xử lý chính ---

async def react_and_message(message, emoji, delay, bot, account_info):
    """Đợi một khoảng thời gian, sau đó thả reaction và gửi tin nhắn."""
    await asyncio.sleep(delay)
    
    # Thả reaction vào tin nhắn drop
    try:
        await message.add_reaction(emoji)
        print(f"[{account_info['channel_id']}] → Đã thả reaction {emoji} cho user {bot.user}")
    except Exception as e:
        print(f"[{account_info['channel_id']}] → Lỗi khi thả reaction: {e}")
    
    await asyncio.sleep(2) # Đợi 2 giây trước khi gửi lệnh
    
    # Gửi lệnh "sb" vào kênh riêng
    if KTB_CHANNEL_ID:
        try:
            target_channel = bot.get_channel(KTB_CHANNEL_ID)
            if target_channel:
                await target_channel.send("sb")
                print(f"[{account_info['channel_id']}] → Đã gửi 'sb' từ user {bot.user}")
            else:
                print(f"[{account_info['channel_id']}] → Không tìm thấy kênh với ID: {KTB_CHANNEL_ID}")
        except Exception as e:
            print(f"[{account_info['channel_id']}] → Lỗi khi gửi 'sb': {e}")

async def run_account(account, emoji, grab_time):
    """Khởi tạo, định nghĩa sự kiện và chạy một instance bot."""
    bot = commands.Bot(command_prefix="!", self_bot=True)

    @bot.event
    async def on_ready():
        """Sự kiện được kích hoạt khi bot đã đăng nhập và sẵn sàng."""
        print(f"[{account['channel_id']}] → Đăng nhập thành công với user: {bot.user} (ID: {bot.user.id})")
        running_bots.append(bot) # Thêm bot vào danh sách đang chạy

    @bot.event
    async def on_message(message):
        """Sự kiện được kích hoạt mỗi khi có tin nhắn mới."""
        # Chỉ xử lý tin nhắn từ Sofi, trong đúng kênh và có nội dung drop (ĐÃ SỬA)
        if message.author.id == SOFI_ID and \
           ("is dropping" in message.content or "đã thả thẻ" in message.content) and \
           str(message.channel.id) == account["channel_id"]:
            
            # Tạo một task mới để xử lý reaction và tin nhắn mà không làm block bot
            asyncio.create_task(react_and_message(message, emoji, grab_time, bot, account))

    try:
        await bot.start(account["token"])
    except discord.errors.LoginFailure:
        print(f"Lỗi đăng nhập với token bắt đầu bằng: {account['token'][:6]}... Token không hợp lệ.")
    except Exception as e:
        print(f"Một lỗi không xác định đã xảy ra với bot {account['token'][:6]}...: {e}")

async def drop_loop():
    """Vòng lặp vô hạn để gửi lệnh 'sd' tuần tự qua các tài khoản."""
    # Đợi cho đến khi tất cả các bot đã sẵn sàng
    print("Đang đợi tất cả các tài khoản đăng nhập...")
    while len(running_bots) < len(accounts):
        await asyncio.sleep(1)
    print("Tất cả các tài khoản đã sẵn sàng. Bắt đầu vòng lặp drop.")

    i = 0
    while True:
        try:
            # Chọn bot và thông tin tài khoản tương ứng
            bot = running_bots[i % len(running_bots)]
            acc = accounts[i % len(accounts)]
            channel_id = int(acc["channel_id"])
            
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send("sd")
                print(f"[{channel_id}] → Đã gửi lệnh 'sd' từ user {bot.user} (Acc thứ {i % len(accounts) + 1})")
            else:
                print(f"[{channel_id}] → Không tìm thấy kênh để gửi lệnh 'sd' cho user {bot.user}.")
                
        except Exception as e:
            print(f"[{acc['channel_id']}] → Lỗi trong vòng lặp drop: {e}")
        
        i += 1
        # Đợi 4 phút 5 giây (245 giây) trước khi gửi lệnh tiếp theo (ĐÃ SỬA)
        await asyncio.sleep(245)

async def main():
    """Hàm chính để chạy tất cả các bot và vòng lặp drop đồng thời."""
    # Chạy keep_alive trong một luồng riêng để không chặn asyncio
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()

    # Tạo danh sách các task cần chạy
    tasks = []
    for i, acc in enumerate(accounts):
        # Kiểm tra token có tồn tại không trước khi tạo task
        if acc.get("token"):
            emoji = FIXED_EMOJIS[i % len(FIXED_EMOJIS)]
            grab_time = GRAB_TIMES[i]
            tasks.append(run_account(acc, emoji, grab_time))
        else:
            print(f"Cảnh báo: Token thứ {i+1} chưa được thiết lập. Bỏ qua tài khoản này.")

    # Thêm task của vòng lặp drop vào danh sách
    if tasks: # Chỉ chạy drop_loop nếu có ít nhất một tài khoản hợp lệ
        tasks.append(drop_loop())
        # Chạy tất cả các task cùng lúc
        await asyncio.gather(*tasks)
    else:
        print("Không có tài khoản nào được cấu hình để chạy.")


if __name__ == "__main__":
    # Chạy hàm main của asyncio
    asyncio.run(main())


