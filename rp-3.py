import telegram
import asyncio
from decimal import Decimal, ROUND_HALF_UP
from telegram.ext import InlineQueryHandler, CallbackContext, Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram import ChatMember
from datetime import datetime, timedelta, timezone
import os
import random
import csv
#import datetime
import logging
import uuid
import sqlite3
import redis

# 配置日志记录器的配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 创建一个日志记录器
logger = logging.getLogger()
# Telegram Bot Token

TOKEN = '6241181708:AAEA9e0T8GNErPQYmStXQC0BeqQIDJ-xj2c'
# Group administrator ID (replace with actual ID)
#ADMIN_ID = None
ADMIN_IDs = [5666064721, 6922266438]
# 定义文件路径
ADMIN_ID_FILE = "admin_ids.txt"

# Define states for the conversation handler
PASSWORD_INPUT = 1

# Define conversation states
START, SETTING_PARAMETERS = range(2)
# 数据库文件路径
DATABASE_FILE = 'user_data.db'
# Store current red packet activity
#current_redpacket = None
current_redpacket = {}
# Store ussers and records 
current_users = {}
# Create bot instance
bot = telegram.Bot(token=TOKEN)
LANG = None #‘cn'
# 获取乌兹别克斯坦时区
#uzbekistan_timezone = timezone("Asia/Tashkent")

def get_uzbekistan_time():
    # 创建一个固定偏移的时区对象
    uzbekistan_timezone = timezone(timedelta(hours=5))  # 乌兹别克斯坦的时区偏移是 UTC+5
    # 获取当前时间并应用时区
    current_time_utc = datetime.now(timezone.utc)
    current_time_uzbekistan = current_time_utc.astimezone(uzbekistan_timezone)

    return current_time_uzbekistan


##############################################################################################
# 定义用户类
class User:
    def __init__(self, user_id, user_name, balance, address=None, records=None):
        self.user_id = user_id
        self.user_name = user_name
        self.balance = balance
        self.address = address
        self.records = records if records is not None else []
    def add_record(self, record):
            self.records.append(record)

class Record:
    def __init__(self, record_type,record_id, amount, time, group_id, group_name):
        self.record_type = record_type
        self.record_id = record_id
        self.amount = amount
        self.time = time
        self.group_id = group_id
        self.group_name = group_name

# 初始化数据库
def init_database():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
    
    # 创建用户表
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER UNIQUE,
                        username TEXT,
                        balance REAL DEFAULT 0.0,
                        address TEXT UNIQUE
                        )''')

    # 创建活动记录表 record_type:0 提现，1 宝箱
        cursor.execute('''CREATE TABLE IF NOT EXISTS records (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        record_type INTEGER,   
                        record_id TEXT,
                        amount REAL,
                        time TEXT,
                        group_id TEXT,
                        group_name TEXT
                        )''')
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.commit()
            conn.close()

# 连接数据库
def connect_database():
    return sqlite3.connect(DATABASE_FILE)

#新增用户表，1 抢宝箱时 2 发“宝箱”的消息 
async def create_user(user_id, user_name) -> bool:
    global current_users
    balance = 0.0
     # 连接数据库
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # 插入用户到数据库
    try:
        cursor.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)',
                        (user_id, user_name, balance))
        conn.commit()
        #current_users[user_id] = User(user_id, user_name, balance)
        print(f"User {user_name} added successfully.")
    except sqlite3.Error as e:
        print(f"Error inserting user into database: {e}")
        print("Failed to add user. Please try again later.")
        return False
    finally:
        conn.close()
        return True
    

#更新宝箱和提现记录，数据库users表的余额，records的记录条
async def update_records(user_id, record_type, record_id, amount, time, group_id, group_name) -> bool:
    print("################################################  update-records ##########################")
    conn = connect_database()
    cursor = conn.cursor()
    global current_users
    try: 
        # 更新记录表
        cursor.execute('INSERT INTO records (user_id, record_type, record_id, amount, time, group_id, group_name) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (user_id, record_type, record_id, amount, time, group_id, group_name))
        # 根据 record_type 处理不同类型的记录
        if record_type == 0:  # 提现记录
            cursor.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
        elif record_type == 1:  # 宝箱记录
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()
        
        print("#############################  update-records OK!   ##########################")
        return True
    except sqlite3.Error as e:
        print(f"Error withdrawing: {e}")
        return False
    finally:
        conn.close()

# 读取用户数据并缓存到程序结构中
def load_users_from_database():
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~load_user_from_db !!!!!!!!!!!!!\n")
    global current_users 
    
    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        user = {}
        for row in cursor.fetchall():
            user_id, username, balance, address = row[1], row[2], row[3], row[4]
            user = User(user_id, username, balance, address)
        # Load records for the user
            cursor.execute('SELECT * FROM records WHERE user_id = ?', (user_id,))  
            print(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~load_user_{user_id} !!!!!!!!!!!!!\n")                                        
            for record_row in cursor.fetchall():
                record_type, record_id, amount, time, group_id, group_name = record_row[2], record_row[3], record_row[4], record_row[5], record_row[6], record_row[7]
                user.add_record(Record(record_type, record_id, amount, time, group_id, group_name))
                
            current_users[user_id] = user
    except sqlite3.Error as e:
        print(f"Error loading users from database: {e}")
    finally:
        if conn:
            conn.close()
    return

##################################################################################################
# 定义/set_user命令处理程序 /user id
async def set_user(update, context):
    print("################################################  set_user ##########################")
    if update.message.chat.type  in ['group', 'supergroup']:
        return
    user_id = update.message.from_user.id  # 获取发送消息的用户 ID
    #creator_id = context.bot.get_me().id  # 获取机器人的用户 ID 

    if user_id not in ADMIN_IDs:
        #update.message.reply_text("Sorry, this command is only available to the creator.")
        return
    global current_users
    # 获取命令中的参数
    args = context.args
    if args:  
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text('输入数据有误，请重新尝试!')
            return
        
        # 连接数据库
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # 查询用户信息
        try:
            #cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
            cursor.execute('SELECT user_id, username, balance FROM users WHERE user_id=?', (user_id,))
            result = cursor.fetchone()
            if result:
                user_id, user_name, balance = result
                user = User(user_id, user_name, balance)  # 可以从数据库中获取更多信息

                user_info = f"\nUser ID: {user.user_id}\nUsername: {user.user_name}\nBalance: {user.balance}\nAddress: {user.address}\n"

                records = get_user_records(user_id)  # 查询用户记录 (需要调用您之前实现的 get_user_records 函数)
                if records:
                   user_info += records

                await update.message.reply_text(user_info)
            else:
                await update.message.reply_text("User not found.")
        except sqlite3.Error as e:
            print(f"Error querying user from database: {e}")
            await update.message.reply_text("Failed to query user information. Please try again later.")
        finally:
            conn.close()
        
    else:  # 如果没有参数，则打印所有数据库中的用户和记录
        if current_users:
            user_info_list = []
            for user in current_users.values():
                user_info = f"+++++++++++++++++++\nUser ID: {user.user_id}\nUsername: {user.user_name}\nBalance: {user.balance}\nAddress: {user.address}\n"            
                record_info = ""
                if user.records:
                    
                    for record in user.records:
                        if record.record_type == 1:
                            record_info += f"宝箱ID: {record.record_id}\nRecord Type: {record.record_type}\nAmount: {record.amount}\nTime: {record.time}\nGroup ID: {record.group_id}\nGroup Name: {record.group_name}\n"
                        else:
                           record_info += f"提现ID: {record.record_id}\nRecord Type: {record.record_type}\nAmount: {record.amount}\nTime: {record.time}\n"
                user_info_list.append(f"{user_info}\n{record_info}")
            # 生成文件并发送给用户
            filename = "users_info.txt"
            with open(filename, "w") as f:
                f.writelines(user_info_list)
            await update.message.reply_document(document=open(filename, "rb"))
            #await update.message.reply_text("All users in the database:\n" + "\n\n".join(user_info_list))
            
        else:
            await update.message.reply_text("No users found in the database.")

def update_user_address(user_id, new_address) -> bool:
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
         # 检查新地址是否存在
        cursor.execute('SELECT COUNT(*) FROM users WHERE address = ?', (new_address,))
        count = cursor.fetchone()[0]
        print(f'\n\n {new_address}same address {count}\n')
        if count > 0 :
            print(f'\{new_address}same address {count}\n\n')
            return False
        cursor.execute('UPDATE users SET address = ? WHERE user_id = ?', (new_address, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating user address in database: {e}")
        return False
    #finally:
     #   if conn:
      #      conn.close()
       # return True
            
# 定义/addr命令处理程序 /addr newaddress
async def set_address(update, context):
    print("################################################  set_addr ##########################")
    if update.message.chat.type in ['group', 'supergroup']:
        return
    user_id = update.effective_user.id  # 获取用户ID
    # 获取命令中的参数
    args = context.args
    if len(args) == 1:
        new_address = args[0]
        if user_id in current_users:
            if current_users[user_id].address is None:
            # 更新数据库中的用户地址
                if update_user_address(user_id, new_address):
                    current_users[user_id].address = new_address
                    if LANG == 'cn':
                        await update.message.reply_text(f"{current_users[user_id].user_name}您的地址更新成功.")
                    else:
                        await update.message.reply_text(f"{current_users[user_id].user_name}Manzilingiz muvaffaqiyatli yangilandi.")
                else:
                    if LANG == 'cn':
                        await update.message.reply_text(f"{current_users[user_id].user_name}您的地址更新失败.")
                    else:
                        await update.message.reply_text(f"{current_users[user_id].user_name}Sizning manzilingiz yangilanmadi.")
            else:
                if LANG == 'cn':
                    await update.message.reply_text(f"请联系客服修改地址")
                else:
                    await update.message.reply_text(f"Manzilingizni o'zgartirish uchun iltimos, mijozlarga xizmat ko'rsatish bo'limi bilan bog'laning.")
        else:
            await update.message.reply_text(f"User ID {user_id} does not exist.")
    elif len(args) == 2:
        if user_id not in  ADMIN_IDs:
            return
        user_id = int(args[0])
        new_address = args[1]
        if user_id in current_users:           
            if update_user_address(user_id, new_address):
                current_users[user_id].address = new_address
                if LANG == 'cn':
                    await update.message.reply_text(f"{current_users[user_id].user_name}的地址更新成功{new_address}.")
                else:
                    await update.message.reply_text(f"{current_users[user_id].user_name}Manzil muvaffaqiyatli yangilandi{new_address}.")
            else:
                if LANG == 'cn':
                    await update.message.reply_text(f"{current_users[user_id].user_name}的地址更新失败{new_address}.")
                else:
                    await update.message.reply_text(f"{current_users[user_id].user_name}Sizning manzilingiz yangilanmadi.")
    else: 
        return
        #await update.message.reply_text("请重新输入 .")

   
# /reload 重新加载 不清空数据库
async def set_reload(update, context):
    print("################################################  set_reload ##########################")
    if update.message.chat.type  in ['group', 'supergroup']:
        return
    user_id = update.message.from_user.id  # 获取发送消息的用户 ID
    #creator_id = context.bot.get_me().id  # 获取机器人的用户 ID

    # 如果当前用户不是创建者，则不执行任何操作
    if user_id not in ADMIN_IDs:
        #update.message.reply_text("Sorry, this command is only available to the creator.")
        return
    global current_users
    current_users = {}
    load_users_from_database()
    # 清空当前数据库中的所有键
    redis_client.flushdb()
    # 发送消息通知用户
    await update.message.reply_text("All data reload successfully.")

# /clear 清空数据
async def set_clear(update,context):
    print("################################################  set_clear ##########################")
    if update.message.chat.type  in ['group', 'supergroup']:
        return
    user_id = update.message.from_user.id  # 获取发送消息的用户 ID
    #creator_id = context.bot.get_me().id  # 获取机器人的用户 ID

    # 如果当前用户不是创建者，则不执行任何操作
    if user_id not in ADMIN_IDs:
        #update.message.reply_text("Sorry, this command is only available to the creator.")
        return
    # 关闭数据库连接
    global current_users
    conn = connect_database()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM users')
        cursor.execute('DELETE FROM records')
        conn.commit()
        print("Database cleared successfully.")
    except sqlite3.Error as e:
        print(f"Error clearing database: {e}")
    finally:
        conn.close()
        # 发送消息通知用户
    current_users = {}
    await update.message.reply_text("All data cleared successfully.")
####################################################################################################
    
# 查询用户宝箱记录和提现记录
'''    
def get_user_records(user_id):
    user = current_users.get(user_id)
    if user:
        records = user.records
        formatted_records = []
        for record in records:
            if record.record_type == 1:
                if LANG == 'cn':
                    formatted_record = f"宝箱ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 + {record.amount}, 群组 - {record.group_name}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Xazina sandiq ID : {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor + {record.amount}, guruh: {record.group_name}, vaqt: {record.time}\n"
            elif record.record_type == 0:
                if LANG =='cn':
                    formatted_record = f"提现ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 - {record.amount}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Pulni yechib olish ID: {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor - {record.amount},  vaqt: {record.time}\n"
            formatted_records.append(formatted_record)
        return "\n".join(formatted_records)
    return None
'''
'''
#返回最近的几条记录
def get_user_records(user_id):
    user = current_users.get(user_id)
    if user:
        records = user.records
        # 按时间倒序排列记录
        records.sort(key=lambda record: record.time, reverse=True)
        # 只返回最近10条记录
        records = records[:8]
        formatted_records = []
        for record in records:
            if record.record_type == 1:
                if LANG == 'cn':
                    formatted_record = f"宝箱ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 + {record.amount}, 群组 - {record.group_name}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Xazina sandiq ID : {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor + {record.amount}, guruh: {record.group_name}, vaqt: {record.time}\n"
            elif record.record_type == 0:
                if LANG =='cn':
                    formatted_record = f"提现ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 - {record.amount}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Pulni yechib olish ID: {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor - {record.amount},  vaqt: {record.time}\n"
            formatted_records.append(formatted_record)
        return "\n".join(formatted_records)
    return None
'''
#返回最后一次提现以及之后的红包记录
def get_user_records(user_id):
    user = current_users.get(user_id)
    if user:
        records = user.records
        # 按时间倒序排列记录
        records.sort(key=lambda record: record.time, reverse=True)
        # 找到最近一次提现记录
        withdraw_record = None
        formatted_records = []
        for record in records:
            if record.record_type == 1:
                if LANG == 'cn':
                    formatted_record = f"宝箱ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 + {record.amount}, 群组 - {record.group_name}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Xazina sandiq ID : {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor + {record.amount}, guruh: {record.group_name}, vaqt: {record.time}\n"
                formatted_records.append(formatted_record)
            elif record.record_type == 0:
                if LANG =='cn':
                    formatted_record = f"提现ID - {record.record_id[:3]}...{record.record_id[-3:]}, 金额 - {record.amount}, 时间 - {record.time}\n"
                else:
                    formatted_record = f"Pulni yechib olish ID: {record.record_id[:3]}...{record.record_id[-3:]}, umumiy miqdor - {record.amount},  vaqt: {record.time}\n"
                formatted_records.append(formatted_record)
                break
        return "\n".join(formatted_records)
    else:
        return None

# 生成宝箱 ID
def generate_redpacket_id(activity_id):
    random_str = uuid.uuid4().hex[:8]
    return f"{activity_id}-{random_str}"

# Handle command "/fhb"
async def set_redpacket(update, context):
    logger.debug('____SET_REDPACKET')
    user_id = update.effective_user.id 
    # Check if sender is a group administrator
    if update.message.chat.type not in ['group', 'supergroup']:
        if LANG == 'cn':
            await bot.send_message(chat_id = user_id, text='请直接在群中发布宝箱！')
        else:
            await bot.send_message(chat_id = user_id, text='请直接在群中发布宝箱！')
        return ConversationHandler.END
    chat_member = await update.message.chat.get_member(update.message.from_user.id)
    if chat_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        print('____SET_REDPACKET+++++++++++++++chat member status', chat_member.status)
        #update.message.reply_text('只有管理员可以发宝箱哦!')
        #await bot.send_message(chat_id = update.message.chat_id, text='只有管理员可以发宝箱哦!')
        return ConversationHandler.END
    
    global current_redpacket
     # Parse command arguments
    args = context.args
    if len(args) not in (1,3):
        #await update.message.reply_text('宝箱发布格式：「/fhb <总金额> <个数> <活动id> 」 请注意使用空格区分参数')
        await bot.send_message(chat_id = user_id, text='宝箱发布格式：「/fhb <总金额> <个数> <活动id> 」 请注意使用空格区分参数！')
        return ConversationHandler.END
    
    try:
        total_amount = float(args[0])
        if len(args) >= 2:
            num_packets = int(args[1])
    except ValueError:
        #await update.message.reply_text('输入数据有误，请重新尝试!')
        await bot.send_message(chat_id = user_id, text='输入数据有误，请重新尝试!')
        return ConversationHandler.END
    chat_id = update.message.chat_id
    chat_title = update.message.chat.title
       # 判断是否为关闭宝箱命令
    if  total_amount <= 0:
        #if current_redpacket:
        if chat_id in current_redpacket and current_redpacket[chat_id]:
            await publish_redpacket_results(chat_id, chat_title)
            if LANG == 'cn':
                await update.message.reply_text('当前宝箱已关闭!')
            else:
                await update.message.reply_text('Hozirgi vaqtda, xazina sandiq yopiq!')
        else:
            if LANG == 'cn':
                await update.message.reply_text('当前无宝箱!')
            else:
                await update.message.reply_text('Hozirgi vaqtda, xazina sandiq mavjud emas!')
        return ConversationHandler.END
    
    #if current_redpacket:
    if chat_id in current_redpacket and current_redpacket[chat_id]:
        if LANG == 'cn':
            await update.message.reply_text('之前宝箱还没抢完，别急!')
        else:
            await update.message.reply_text('Xazina sandiq tortib olib qo’yilmagan, xavotir olmang!')

        return
   
    # Extract password (if any)
    activity_id = args[2]
    #password_message = f'口令宝箱：{password}' if password else '点我抢宝箱'
    if LANG == 'cn':
        password_message = '点我抢宝箱'
    else:
        #password_message = 'Xazina sandiqni olish uchun meni bosing'
        password_message = 'Xazina sandiqni oling'

        
    # Create red packet activity
    #current_redpacket_id = str(uuid.uuid4())  # 生成唯一标识符，可以是随机数或其他方式
    current_redpacket_id = generate_redpacket_id(activity_id)
    print(f"\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ activity_id{activity_id}\n")
    current_redpacket.setdefault(chat_id, {})
    start_time = get_uzbekistan_time()
    current_redpacket[chat_id] = {
        'id': current_redpacket_id,
        'total_amount': total_amount,
        'num_packets': num_packets,
        'password': None,
        'remaining_amount': total_amount,
        'participants': [],
        'start_time': start_time
    }
    print(current_redpacket[chat_id])

    # 使用 Redis 的 SETNX 命令创建一个空集合作为参与者列表
    #redis_client.setnx(activity_id, "")

    # 删除原有的键
    #redis_client.delete(activity_id)

    # 使用 sadd 命令创建一个集合类型的键
    redis_client.sadd(activity_id, "")

    # Generate red packet activity message
    if LANG == 'cn':
        message = f'来抢宝箱咯:\n总额: {total_amount}\n个数: {num_packets}'
    else:
        message = f'Keling xazina sandiqni oling:\numumiy miqdor: {total_amount}\nraqam: {num_packets}'
    logger.debug('++++++++++++____SET_REDPACKET--------------------' + message)
    #if password:
        #message += f'\n财富密码: {password}'
    logger.debug('++++++++++++____SET_REDPACKET--------------------')
    # Create button
    
    keyboard = [[InlineKeyboardButton(password_message, callback_data = f"grab_redpacket:{current_redpacket_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send red packet activity message to the group
    #await update.message.reply_photo(photo=open('./rp3.jpg', 'rb'), caption=message, reply_markup=reply_markup)
    await  bot.send_photo(chat_id = chat_id, photo=open('./rp3.jpg', 'rb'), caption=message, reply_markup=reply_markup)

    return ConversationHandler.END


# Handle button click events
async def button_callback(update, context):
    query = update.callback_query
    query.answer()
   
    global current_redpacket
    
    chat_id = query.message.chat_id 
    chat_title = query.message.chat.title  # 获取群组名称
    print("==========================================++++++++++++Chat ID:", chat_id)
    print("==========================================++++++++++++Chat Title:", chat_title)
    if chat_id not in current_redpacket or current_redpacket[chat_id] is None:
        if LANG == 'cn':
            await query.message.reply_text('宝箱被抢完啦，下次再来!')
        else:
            await query.message.reply_text("Xazina sandiq allaqachon tortib olib qo'yilgan, keying safar o'rinib ko'ring!")
        return

#    if current_redpacket[chat_id]['password']:
 #       await query.message.reply_text('这是口令宝箱，请发送财富密码!')
#        return
    # 获取当前宝箱活动的标识符
    current_redpacket_id = current_redpacket[chat_id].get('id')
    # 获取按钮点击事件中的宝箱活动标识符
    #clicked_redpacket_id = query.data
    clicked_redpacket_id = update.callback_query.data.split(":")[1]
    print(
        '@@@@@@@@@@@@@@@@@   currid{} clickid{}##############'.format(
            current_redpacket_id, clicked_redpacket_id
        )
    )
        # 检查按钮点击的宝箱活动标识符是否与当前活动的宝箱标识符匹配
    if current_redpacket_id != clicked_redpacket_id:
        if LANG == 'cn':
            await query.message.reply_text('您点击的宝箱活动已结束或不存在!')
        else:
            await query.message.reply_text('Siz bosgan xazina sandiq faoliyati tugadi yoki mavjud emas!')
        return
    
    user =  query.from_user
    user_id = user.id   
    user_name = user.username or (user.first_name + ' ' + user.last_name)
    chat_member = await query.message.chat.get_member(user.id)
    
    #限制只有普通用户才能抢宝箱
    if not chat_member.status == ChatMember.MEMBER:
        #await query.message.reply_text('Only regular group members can participate in the red packet activity!')
        return
    print("==========================================++++++++++++checke if in current_users")
    #判断用户是否在数据库
    if  user_id not in current_users:
        print("==========================================++++++++++++not in current_users")
        #在数据库插入新用户信息
        if await create_user(user_id, user_name):
            #程序缓存用户信息新增user_id的用户
            current_users[user_id] = User(user_id, user_name, 0.0, None, None)
    
    # 检查当前用户是否已经参加过宝箱活动
    activity_id = current_redpacket_id.split("-")[0]
    data_type = redis_client.type(activity_id)
    print(f"\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ activity_id{activity_id}     datatype{data_type}\n")
    
    already_participated =  redis_client.sismember(activity_id, user_id)
    #already_participated = any(participant['userid'] == user_id for participant in current_redpacket[chat_id]['participants'])
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Already Participated:", already_participated) 
    if already_participated:
        if LANG == 'cn':
            await query.message.reply_text(f'您 ({user_name})已经参加过啦，机会留给其他朋友吧!')
        else:
            await query.message.reply_text(f'({user_name}) Allaqachon eshtirok etilgan, imkoniyatlarni boshqa ishtirokchilarga qoldiring!')
        #bot.send_message(chat_id = update.message.chat_id, text='您 ({user_name})已经参加过啦，机会留给其他朋友吧!')
        return
    
    if len(current_redpacket[chat_id]['participants']) >= current_redpacket[chat_id]['num_packets']:
        if LANG == 'cn':
            await query.message.reply_text('宝箱被抢完啦，下次再来!')
        else:
            await query.message.reply_text("Xazina sandiq allaqachon tortib olib qo'yilgan, keying safar o'rinib ko'ring!")
        return

        # Check if password is set
    #if current_redpacket[chat_id]['password']:
    #    await query.message.reply_text('请输入财富密码:')
    #    return
    logger.debug('++++++++++++grab_redpacket--------------------')
        # Grab the red packet
        #await grab_redpacket(query)
    await grab_redpacket(update,chat_id,clicked_redpacket_id)

# Handle password input events
async def handle_password_input(update, context):
   # logger.debug('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%handle_password_input--------------------')
    logger.debug('Received password input: %s', update.message.text.strip())  # 添加
    global current_redpacket
    chat_id = update.message.chat_id
    chat_title = update.message.chat.title  # 获取群组名称
    print("==========================================++++++++++++Chat ID:", chat_id)
    print("==========================================++++++++++++Chat Title:", chat_title)
    #if current_redpacket is None:
    if LANG == 'cn':
        password = "宝箱"
    else:
        password = "Xazina sandiq"
    user_input = update.message.text.strip()
    user = update.effective_user
    user_id =  user.id
    user_name = user.username or (user.first_name + ' ' + user.last_name)

    #判断用户是否在数据库
    if user_id not in current_users:
        #在数据库插入新用户信息
        if await create_user(user_id, user_name):
            #程序缓存用户信息新增user_id的用户
            current_users[user_id] = User(user_id, user_name, 0.0, None, None)

    if user_input == password:
        if LANG == 'cn':
            message_text = "请选择操作："
            keyboard = [
                [InlineKeyboardButton("余额", callback_data="balance")],
                [InlineKeyboardButton("明细", callback_data="detail")],
                [InlineKeyboardButton("提现", callback_data="withdraw")],
                [InlineKeyboardButton("地址", callback_data="address")],
            ]
        else:
            message_text = "Iltimos, tanlang:"
            keyboard = [
                [InlineKeyboardButton("balans", callback_data="balance")],
                [InlineKeyboardButton("tafsilotlar", callback_data="detail")],
                [InlineKeyboardButton("naqd pul olish", callback_data="withdraw")],
                [InlineKeyboardButton("manzil", callback_data="address")],
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        #await update.message.reply_text(message_text, reply_markup=reply_markup)
        await bot.send_message(chat_id=user_id, text=message_text, reply_markup=reply_markup)
    else:
        return
    

# Logic for grabbing red packets
async def grab_redpacket(update,chat_id,rp_id):
    global current_redpacket
    #chat_id = update.query_callback.chat_id
    # Randomly allocate red packet amount
    remaining_amount = current_redpacket[chat_id]['remaining_amount']
    remaining_packet = current_redpacket[chat_id]["num_packets"] - len(current_redpacket[chat_id]["participants"])
    
    #if remaining_packet > 1:
        # 平均分配宝箱金额
     #   amount = remaining_amount / Decimal(str(remaining_packet))
        # 保留两位小数
     #   amount = amount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
    #else:
    #    amount = remaining_amount
    if len(current_redpacket[chat_id]["participants"]) < (current_redpacket[chat_id]["num_packets"] - 1):
        amount = round(random.uniform(0, remaining_amount),2)
        amount = round(remaining_amount/remaining_packet, 2)
    else:
        amount = remaining_amount

    if current_redpacket[chat_id]['password']:
        user = update.effective_user
        chat_title = update.message.chat.title
    else:
        user = update.callback_query.from_user
        chat_title = update.callback_query.message.chat.title

    #grab_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 将乌兹别克斯坦时间格式化为字符串
    grab_time = get_uzbekistan_time().strftime('%Y-%m-%d %H:%M:%S')

    current_redpacket[chat_id]['participants'].append({
        'userid': user.id,
        'username': user.username or (user.first_name + ' ' + user.last_name),
        'amount': amount,
        'time': grab_time
    })
    #print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~who:", current_redpacket['participants'])
    current_redpacket[chat_id]['remaining_amount'] = round((remaining_amount - amount),2)
 
    # Update red packet activity message
    await update_redpacket_message(update,chat_id)

    #update records in db
    await update_records(user_id=user.id, record_type=1, record_id = rp_id, amount=amount, time=grab_time, group_id=chat_id, group_name=chat_title)
    # 更新用户余额
    current_users[user.id].balance += amount
    current_users[user.id].add_record(Record(record_type=1, record_id=rp_id, amount=amount, time=grab_time, group_id=chat_id, group_name=chat_title))
    print(f"Redpacket record added successfully for user {current_users[user.id].user_name}.")
    
    # 将用户ID添加到参与者列表中
    activity_id = rp_id.split("-")[0]
    print(f"\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~add activity_id{activity_id} ~~~~~~~~~~~~~~~~~~~\n")
    redis_client.sadd(activity_id, user.id)

    # Publish updated red packet information   
    if len(current_redpacket[chat_id]['participants']) == current_redpacket[chat_id]['num_packets']:
        logger.debug('^^^^^^^^^^^^^^^^----------------publish_redpacket_results+++++++++++----')
        await publish_redpacket_results(chat_id,chat_title)

# Update red packet activity message
async def update_redpacket_message(update,chat_id):
    global current_redpacket

    total_amount = current_redpacket[chat_id]["total_amount"]
    num_packets = current_redpacket[chat_id]["num_packets"]
    participants = current_redpacket[chat_id]["participants"]
    if LANG == 'cn':
        message_text = f'抢宝箱咯:\n总   额: {total_amount}\n幸运儿: {len(participants)}/{num_packets}\n'
    else:
        message_text = f'Xazina sandiqni oling:\numumiy,qo’shimcha: {total_amount}\nbaxtli odam: {len(participants)}/{num_packets}\n'

    # 遍历参与者列表，将用户名和抢到的金额添加到消息中
    for participant in participants:
        username = participant["username"]
        amount = participant["amount"]
        message_text += f'{username.ljust(20)}{amount:>10}\n'
        
    if current_redpacket[chat_id]['password']:
        await update.message.reply_text(message_text)
    else:
        await update.callback_query.message.reply_text(message_text)

# Publish red packet grab results
async def publish_redpacket_results(chat_id, chat_title):
    global current_redpacket

    if (len(current_redpacket[chat_id]['participants']) == 0):
        current_redpacket[chat_id] = None
        return
    
    # Write to file
    filename = f'{chat_title}_{current_redpacket[chat_id]["start_time"].strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    print(filename)
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['ID', 'Username', 'Amount', 'Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in current_redpacket[chat_id]['participants']:
            writer.writerow({'ID': participant['userid'], 'Username': participant['username'], 'Amount': participant['amount'], 'Time': participant['time']})

    # Send file to group administrator
    await bot.send_document(chat_id=ADMIN_IDs[0], document=open(filename, 'rb'), caption=f'Red Packet Grab Results ({current_redpacket[chat_id]["start_time"]})')
    current_redpacket[chat_id] = None


# 处理点击内联按钮的回调
async def button_click_callback(update: Update, context: CallbackContext):
    print("\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  button_click_callback\n")
    global current_users
    query = update.callback_query
    #await query.answer(text="您点击了按钮！", show_alert=True)
    button_data = query.data
    user_id = query.from_user.id
    if user_id not in current_users:
        return
    if button_data == "balance":
        mybalance = current_users[user_id].balance
        if LANG == 'cn':
            await bot.send_message(chat_id=user_id, text=f"您的余额是:{mybalance}")
        else:
            await query.answer(text=f"Sizning balansingiz: {mybalance}", show_alert=True)
            #await bot.send_message(chat_id=user_id, text=f"Sizning balansingiz: {mybalance}")
            #await context.bot.answer_callback_query(callback_query_id=user_id, text=f"Sizning balansingiz: {mybalance}", show_alert=True)
    elif button_data == "detail":
        records = get_user_records(user_id)
        if LANG == 'cn':
            await bot.send_message(chat_id=user_id, text=f"您的明细是:\n{records}")
        else:
            #await query.answer(text=f"Sizning tafsilotlaringiz:\n{records}", show_alert = True)
            await bot.send_message(chat_id=user_id, text=f"Sizning tafsilotlaringiz:\n{records}")
    elif button_data == "withdraw":
        myaddress = current_users[user_id].address
        if myaddress is None:
            if LANG == 'cn':
                await bot.send_message(chat_id=user_id, text=f"请输入「/addr 您的地址」成功绑定后再提现")
            else:
                await query.answer(text=f"Iltimos, kiriting /addr sizning manzilingiz, Muvafaqiyatli ulanishdan keyin pulni yechib oling", show_alert=True)
        elif current_users[user_id].balance == 0.0:
            if LANG == 'cn':
                await bot.send_message(chat_id=user_id, text=f"您余额为0, 无需提现 ")
            else:
                await query.answer(text=f"Sizning balansingiz 0, pul yechib olishni hojati yo'q", show_alert=True)
        else:
            withdraw_id = str(uuid.uuid4().hex[:8])
            mybalance = current_users[user_id].balance
            w_time = get_uzbekistan_time().strftime('%Y-%m-%d %H:%M:%S')
            if await update_records(user_id = user_id, record_type = 0, record_id = withdraw_id, amount = mybalance, time = w_time, group_id = None, group_name = None):
                current_users[user_id].balance = 0
                current_users[user_id].add_record(Record(record_type = 0, record_id = withdraw_id, amount = mybalance, time = w_time, group_id = None, group_name = None))
                user_name = current_users[user_id].user_name
                if LANG == 'cn':
                    await bot.send_message(chat_id=user_id, text=f"({user_name})您提现申请[ID-{withdraw_id[:3]}...{withdraw_id[-3:]}]已提交，提现金额{mybalance},{w_time}")
                else:
                    await bot.send_message(chat_id=user_id, text=f"({user_name})Pul yechib olishingiz uchun arizangiz[ID-{withdraw_id[:3]}...{withdraw_id[-3:]}]allaqachon topshirildi, Balansdagi pulni yechib olish{mybalance},{w_time}")
                await bot.send_message(chat_id=ADMIN_IDs[0], text=f"[ID-{withdraw_id}]:用户{user_name}({user_id})申请往{current_users[user_id].address}提现，金额{mybalance}, 时间{w_time}")
            else:
                if LANG == 'cn':
                    await bot.send_message(chat_id=user_id, text=f"提现失败，请稍后重试")
                else:
                    await query.answer(text=f"pulni yechib olish muvafaqiyatsizlikga o’chradi, iltimos, biroz vaqtdan keyin qaytadan o’rinib ko’ring", show_alert = True)
                    #await bot.send_message(chat_id=user_id, text=f"pulni yechib olish muvafaqiyatsizlikga o’chradi, iltimos, biroz vaqtdan keyin qaytadan o’rinib ko’ring")
            #await bot.send_message(chat_id=user_id, text="提现申请已提交")
    elif button_data == "address":
        myaddress = current_users[user_id].address
        if myaddress is None:
            if LANG == 'cn':
                await bot.send_message(chat_id=user_id, text=f"输入「/addr 您的地址」进行绑定")
            else:
                await query.answer(text=f"Kiriting 「\addr sizning manzilingiz」 bog’lash", show_alert = True)
                #await bot.send_message(chat_id=user_id, text=f"Kiriting 「\addr sizning manzilingiz」 bog’lash")
            return
        else:
            if LANG == 'cn':
                await bot.send_message(chat_id=user_id, text=f"您的地址是:{myaddress}\n 如需修改请找客服")
            else:
                await query.answer(text=f"Sizning manzilingiz:{myaddress}\n Agar siz uni o’zgartirishingiz kerak bo’lsa, iltimos, mijozlarga xizmat ko’rsatish xizmatiga murojat qiling", show_alert=True)
                #await bot.send_message(chat_id=user_id, text=f"Sizning manzilingiz:{myaddress}\n Agar siz uni o’zgartirishingiz kerak bo’lsa, iltimos, mijozlarga xizmat ko’rsatish xizmatiga murojat qiling")
'''
# 读取现有的管理员 ID
async def read_admin_ids():
    global ADMIN_IDs
    if os.path.exists(ADMIN_ID_FILE):
        with open(ADMIN_ID_FILE, "r") as f:
            ADMIN_IDs = [int(line.strip()) for line in f]

# 将新的管理员 ID 添加到列表
async def add_admin_id(user_id):
    global ADMIN_IDs
    if user_id not in ADMIN_IDs:
        ADMIN_IDs.append(user_id)
        await save_admin_ids()

# 将管理员 ID 列表保存到文件
async def save_admin_ids():
    global ADMIN_IDs
    with open(ADMIN_ID_FILE, "w") as f:
        for admin_id in ADMIN_IDs:
            f.write(f"{admin_id}\n")
'''
# 获取创作者用户ID
async def get_admin_id(update, context):
    global ADMIN_IDs
    ADMIN_IDs.append(update.effective_user.id) 
    print(f'\n\nADMIN_ID{ADMIN_IDs}\n\n')

if __name__ == '__main__':
    logger.debug('MAIN')
    application = Application.builder().token(TOKEN).build()
# Define conversation handler
    conv_handler = ConversationHandler(
        entry_points={
            CommandHandler('geta', get_admin_id),
            CommandHandler('fhb', set_redpacket),
            CommandHandler('user', set_user),
            CommandHandler('addr', set_address),
            CommandHandler('reload', set_reload),
            CommandHandler('clear', set_clear)
            },
        states={},
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    #application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input))

    # 添加处理抢宝箱的回调处理程序
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^grab_redpacket:"))   
    # 添加宝箱的回调处理程序
    application.add_handler(CallbackQueryHandler(button_click_callback, pattern="^(balance|detail|withdraw|address)$"))

    # 创建 Redis 客户端
    redis_client = redis.StrictRedis(host='rp3-redis', port=6379)
    print(f"\n........................................{TOKEN}............................\n")
    #redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
    # 初始化数据库
    init_database()
    load_users_from_database()                           
    #get_admin_id()
    logger.debug('ADDHANDLER OK')
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.debug('POLLING')
    
    