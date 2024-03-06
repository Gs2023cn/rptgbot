import telegram
from telegram.ext import InlineQueryHandler, CallbackContext, Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram import ChatMember
import datetime
import threading
import os
import random
import csv
import datetime
import logging
import uuid
import sqlite3
# 配置日志记录器的配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 创建一个日志记录器
logger = logging.getLogger()
# Telegram Bot Token
TOKEN = '7061360321:AAGIxtGGi2RCeXjSMifKHt71iGwkQ9Ek7Vk'
ADMIN_ID = 6945651433
# 数据库文件路径
DATABASE_FILE = 'user_data.db'
current_redpacket = {}
current_users = {}
# 使用RLock锁，支持读写互斥
users_lock = threading.RLock()

# Create bot instance
bot = telegram.Bot(token=TOKEN)

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

    # 创建活动记录表 record_type:0 提现，1 红包
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

# 获取当前时间
def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 查询用户余额
def get_user_balance(user_id):
    user = current_users.get(user_id)
    if user:
        return user.balance
    return 0.0

# 查询用户红包记录和提现记录
def get_user_records(user_id):
    user = current_users.get(user_id)
    if user:
        records = user.records
        formatted_records = []
        for record in records:
            if record.record_type == 1:
                formatted_record = f"红包记录：红包ID - {record.record_id}, 金额 - {record.amount}, 群组 - {record.group_name}, 时间 - {record.time}\n"
            elif record.record_type == 0:
                formatted_record = f"提现记录：提现ID - {record.record_id}, 金额 - {record.amount}, 时间 - {record.time}\n"
            formatted_records.append(formatted_record)
        return formatted_records
    return None

# 查询用户地址
def get_user_address(user_id):
    user = current_users.get(user_id)
    if user:
        return user.address
    return None

# 更新用户余额和记录
def update_user_balance_and_records(user_id, amount, record_type):
    user = current_users.get(user_id)
    if user:
        user.add_record(Record(record_type, str(uuid.uuid4()), amount, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ""))

async def set_addr(update, context):
    return

# Handle password input events
async def handle_password_input(update, context):
    #logger.debug('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%handle_password_input--------------------')
    #logger.debug('Received password input: %s', update.message.text.strip())  # 添加
    #global current_redpacket
    #chat_id = update.message.chat_id
    #chat_title = update.message.chat.title  # 获取群组名称
    #print("==========================================++++++++++++Chat ID:", chat_id)
    #print("==========================================++++++++++++Chat Title:", chat_title)
    #if current_redpacket is None:
    password = "宝箱"
    user_input = update.message.text.strip()
  
    if user_input == password:
        user = update.effective_user
        user_id =  user.id
        #user_name = user.username or (user.first_name + ' ' + user.last_name)
        message_text = "我的宝箱："
        keyboard = [
            [InlineKeyboardButton("余额", callback_data="balance")],
            [InlineKeyboardButton("明细", callback_data="detail")],
            [InlineKeyboardButton("提现", callback_data="withdraw")],
            [InlineKeyboardButton("地址", callback_data="address")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        #await update.message.reply_text(message_text, reply_markup=reply_markup)
        await bot.send_message(chat_id=user_id, text=message_text,reply_markup=reply_markup)
    else:
        return
    
#更新红包和提现记录，数据库users表的余额，records的记录条，以及数据结构current_users的余额和记录
def update_records(user_id, record_type, record_id, amount, time, group_id, group_name) -> bool:
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
        elif record_type == 1:  # 红包记录
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()
        # 更新 current_users 中的数据
        #if user_id in current_users:
        #user = current_users[user_id]
        #if record_type == 0:
        #    user.balance = 0
        #elif record_type == 1:
         #   user.balance += amount
          #  user.add_record(Record(record_type, record_id, amount, time, group_id, group_name))
        print("################################################  update-records OK!   ##########################")
        return True
    except sqlite3.Error as e:
        print(f"Error withdrawing: {e}")
        return False
    finally:
        conn.close()

# Handle button click events
async def button_callback(update, context):
    query = update.callback_query
    query.answer()

    #user = update.effective_user
    #user_id = user.id
    clicked_id = query.data
    if clicked_id in ["balance","detail","withdraw","address"]:
        user_id = query.from_user.id
        user_name = query.from_user.username or (query.from_user.first_name + ' ' + query.from_user.last_name)
        if  clicked_id== "balance":
            balance = get_user_balance(user_id)
            await bot.send_message(chat_id=user_id, text=f"({user_name})您的余额是{balance}")
        elif clicked_id == "detail":
            records = get_user_records(user_id)
            #await bot.send_message(chat_id=user_id, text=f"({user_name})您的明细是{records}")
            await bot.send_message(chat_id=user_id, text=records)
        elif clicked_id == "withdraw":
            addr = get_user_address()
            if addr is None:
                await bot.send_message(chat_id=user_id, text=f"请先提交地址，此时输入「/add 您的地址」成功绑定后再提现")
                return
            withdraw_id = str(uuid.uuid4())
            balance = get_user_balance(user_id)
            withdraw_time = get_current_time()
            if update_records(user_id, record_type=0, record_id=withdraw_id, amount=balance, time=withdraw_time):
                await bot.send_message(chat_id=user_id, text=f"({user_name})您提现申请[ID-{withdraw_id}]已提交，提现金额{balance},{withdraw_time}")
                await bot.send_message(chat_id=ADMIN_ID, text=f"(用户{user_name}-{user_id})提现申请[ID-{withdraw_id}]已提交，提现金额{balance},{withdraw_time}")
            else:
                await bot.send_message(chat_id=user_id, text=f"提现失败，请稍后重试")
        elif clicked_id == "address":
            addr = get_user_address()
            if addr is None:
                await bot.send_message(chat_id=user_id, text=f"请输入「/add 您的地址」进行绑定")
            await bot.send_message(chat_id=user_id, text=f"(id: {user_id})您的地址是{addr}")
        return

 #处理点击内联按钮的回调
async def button_click_callback(update: Update, context: CallbackContext):
    print("\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  button_click_callback\n")

    query = update.callback_query
    query.answer()

    #user = update.effective_user
    #user_id = user.id
    clicked_id = query.data
    if clicked_id in ["balance","detail","withdraw","address"]:
        user_id = query.from_user.id
        user_name = query.from_user.username or (query.from_user.first_name + ' ' + query.from_user.last_name)
        if  clicked_id== "balance":
            balance = get_user_balance(user_id)
            await bot.send_message(chat_id=user_id, text=f"({user_name})您的余额是{balance}")
        elif clicked_id == "detail":
            records = get_user_records(user_id)
            #await bot.send_message(chat_id=user_id, text=f"({user_name})您的明细是{records}")
            await bot.send_message(chat_id=user_id, text=records)
        elif clicked_id == "withdraw":
            addr = get_user_address()
            if addr is None:
                await bot.send_message(chat_id=user_id, text=f"请先提交地址，此时输入「/add 您的地址」成功绑定后再提现")
                return
            withdraw_id = str(uuid.uuid4())
            balance = get_user_balance(user_id)
            withdraw_time = get_current_time()
            if update_records(user_id, record_type=0, record_id=withdraw_id, amount=balance, time=withdraw_time):
                await bot.send_message(chat_id=user_id, text=f"({user_name})您提现申请[ID-{withdraw_id}]已提交，提现金额{balance},{withdraw_time}")
                await bot.send_message(chat_id=ADMIN_ID, text=f"(用户{user_name}-{user_id})提现申请[ID-{withdraw_id}]已提交，提现金额{balance},{withdraw_time}")
            else:
                await bot.send_message(chat_id=user_id, text=f"提现失败，请稍后重试")
        elif clicked_id == "address":
            addr = get_user_address()
            if addr is None:
                await bot.send_message(chat_id=user_id, text=f"请输入「/add 您的地址」进行绑定")
            await bot.send_message(chat_id=user_id, text=f"(id: {user_id})您的地址是{addr}")
        return
    
################################################  模拟数据 ##########################
# 定义/set_user命令处理程序 /user id
async def set_user(update, context):
    print("################################################  set_user ##########################")
    global current_users
    # 获取命令中的参数
    args = context.args
    if args:  # 如果有参数，则生成用户并插入数据库
        try:
            user_id = int(args[0])
        except ValueError:
            await update.message.reply_text('输入数据有误，请重新尝试!')
            return ConversationHandler.END
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!        {user_id}:{current_users[user_id].user_name}  \n")
        user_name = f"{user_id}-name"
        #address = f"{user_id}-address"
        balance = 0.0
        if user_id in current_users:
            print(f"##################oldid{user_id}\n")
            await update.message.reply_text(f"User {user_name} already exist.")
            return 
        
        # 连接数据库
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # 插入用户到数据库
        try:
            cursor.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)',
                           (user_id, user_name, balance))
            conn.commit()
            current_users[user_id] = User(user_id, user_name, balance)
            await update.message.reply_text(f"User {user_name} added successfully.")
        except sqlite3.Error as e:
            print(f"Error inserting user into database: {e}")
            await update.message.reply_text("Failed to add user. Please try again later.")
        
    else:  # 如果没有参数，则打印所有数据库中的用户和记录
        if current_users:
            user_info_list = []
            for user in current_users.values():
                user_info = f"\nUser ID: {user.user_id}\nUsername: {user.user_name}\nBalance: {user.balance}\nAddress: {user.address}\n"
                record_info = ""
                if user.records:
                    
                    for record in user.records:
                        if record.record_type == 1:
                            record_info += f"Record ID: {record.record_id}\nRecord Type: {record.record_type}\nAmount: {record.amount}\nTime: {record.time}\nGroup ID: {record.group_id}\nGroup Name: {record.group_name}\n"
                        else:
                           record_info += f"Record ID: {record.record_id}\nRecord Type: {record.record_type}\nAmount: {record.amount}\nTime: {record.time}\n"
                user_info_list.append(f"{user_info}\n{record_info}")
            await update.message.reply_text("All users in the database:\n" + "\n\n".join(user_info_list))
            
        else:
            await update.message.reply_text("No users found in the database.")
        

# /reload 重新加载 不清空数据库
async def set_reload(update, context):
    print("################################################  set_reload ##########################")
    global current_users
    current_users = {}
    load_users_from_database()
    # 发送消息通知用户
    await update.message.reply_text("All data reload successfully.")

# /clear 清空数据
async def set_clear(update,context):
    print("################################################  set_clear ##########################")
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

# 更新用户地址的函数
def update_user_address(user_id, new_address):
    global current_users
    conn = connect_database()
    cursor = conn.cursor()
    try:
       # if user_id in current_users:
       #     current_users[user_id].address = new_address
       # else:
       #     return
        cursor.execute('UPDATE users SET address = ? WHERE user_id = ?', (new_address, user_id))
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"Error updating user address: {e}")
        
    finally:
        conn.close()

# 更新数据库用户余额的函数
def update_user_balance(user_id, new_balance):
    conn = connect_database()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating user balance: {e}")
    finally:
        conn.close()

# 定义/addr命令处理程序 /addr id newaddress
async def set_address(update, context):
    print("################################################  set_addr ##########################")
    # 获取命令中的参数
    args = context.args
    global current_users
    if len(args) == 2:
        new_address = args[1] 
        try:
            user_id = int(args[0])
        except:
            await update.message.reply_text(f"Address Wrong.")
            return
        if user_id  in current_users:
            current_users[user_id].address = new_address
            # 更新数据库中的用户地址
            update_user_address(user_id, new_address)
            await update.message.reply_text(f"Address updated successfully for user {user_id}.")
        else:
            await update.message.reply_text(f"user ID {user_id} not exist ")
            balance = 0.0
            user_name = f"{user_id}-name"
            # 连接数据库
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (user_id, username, balance, address) VALUES (?, ?, ?, ?)',
                           (user_id, user_name, balance, new_address))
                conn.commit()
                
                current_users[user_id] = User(user_id, user_name, balance, new_address)
                await update.message.reply_text(f"User {user_name} added successfully.")
            except sqlite3.Error as e:
                print(f"Error inserting user into database: {e}")
                await update.message.reply_text("Failed to add user. Please try again later.")
    else:
        await update.message.reply_text("Please provide user ID and new address.")

# 定义/balance命令处理程序 /balance id nb
async def set_balance(update, context):
    print("################################################  set_balance ##########################")
    global current_users
    # 获取命令中的参数
    args = context.args
    if len(args) == 2:
        user_id, new_balance = int(args[0]), float(args[1])
        if user_id  in current_users:
            current_users[user_id].balance += new_balance
            # 更新数据库中的用户余额
            update_user_balance(user_id, current_users[user_id].balance)
            await update.message.reply_text(f"Balance{new_balance} updated successfully for user {current_users[user_id].user_name}.")
        else:
            await update.message.reply_text(f"user ID {user_id} not exist ")
    else:
        await update.message.reply_text("Please provide user ID and new balance.")

# 定义/rp命令处理程序 /rp uid amount gid
async def set_rp(update, context):
    print("################################################  set_rp ##########################")
    global current_users
    args = context.args
    if len(args) == 3:  # 确保命令参数的数量正确
        user_id, amount, group_id = int(args[0]), args[1], args[2]
        user_name = f"{user_id}-name"
        group_name = f"{group_id}-name"
        amount = float(amount)
        address = None
        # 检查用户是否存在，如果不存在则生成新用户
        if user_id not in current_users:
            print(f"############ ###########  ########### newuser: {user_id}\n")
            #current_users[user_id] = User(user_id, user_name, 0.0)  # 初始化余额为0
            balance = 0.0
            # 连接数据库
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            try:
                address = None
                cursor.execute('INSERT INTO users (user_id, username, balance, address) VALUES (?, ?, ?, ?)',
                           (user_id, user_name, balance, address))
                conn.commit()
                
                current_users[user_id] = User(user_id, user_name, balance, address)
                await update.message.reply_text(f"User {user_name} added successfully.")
            except sqlite3.Error as e:
                print(f"Error inserting user into database: {e}")
                await update.message.reply_text("Failed to add user. Please try again later.")

        # 更新记录表
        record_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if update_records(user_id=user_id, record_type=1, record_id=record_id, amount=amount, time=current_time, group_id=group_id, group_name=group_name):
            print("################################################  update-current_user ##########################")
            # 更新用户余额
            current_users[user_id].balance += amount  
            current_users[user_id].add_record(Record(record_type=1, record_id=record_id, amount=amount, time=current_time, group_id=group_id, group_name=group_name))
            await update.message.reply_text(f"Redpacket record added successfully for user {user_name}.")
        else:
            await update.message.reply_text(f"Redpacket record added Fail for user {user_name}.")
    else:
        await update.message.reply_text("Invalid number of arguments. Usage: /rp user_id  amount group_id")

# 定义/draw命令处理程序 /draw id 提现所有余额
async def set_draw(update, context):
    print("################################################  set_draw ##########################")
    global current_users
    args = context.args
    if args:
        user_id = int(args[0])
        # 检查用户是否存在
        if user_id not in current_users:
            await update.message.reply_text(f"User {user_id} does not exist.")
            return
        elif current_users[user_id].balance == 0:
            await update.message.reply_text(f"User {user_id} no need to wtihdraw.")
            return
        elif current_users[user_id].address is None:
            await update.message.reply_text(f"User {user_id} has no address.")
            return
        # 模拟用户ID的提现
        withdraw_id = str(uuid.uuid4())  # 生成提现ID
        withdraw_time = get_current_time()  # 获取当前时间
        amount = get_user_balance(user_id)  # 获取用户余额
        
        # 更新记录
        if update_records(user_id=user_id, record_type=0, record_id=withdraw_id, amount=amount, time=withdraw_time, group_id=None, group_name=None):
            # 更新current_users中的数据
            print("################################################  update-current_user ##########################")
            current_users[user_id].balance = 0
            current_users[user_id].add_record(Record(record_type=0, record_id=withdraw_id, amount=amount, time=withdraw_time, group_id=None, group_name=None))
        
            await update.message.reply_text(f"User {user_id} simulated withdrawal successfully.")
        else:
            await update.message.reply_text(f"User {user_id} simulated withdrawal failed.")
    else:
        await update.message.reply_text("Please provide a user ID.")

############################################################################################
if __name__ == '__main__':
    logger.debug('MAIN')
    application = Application.builder().token(TOKEN).build()
    logger.debug('build OK')
# Define conversation handler
    conv_handler = ConversationHandler(
       entry_points={
           CommandHandler('user', set_user), 
           CommandHandler('addr', set_address), 
           CommandHandler('balance', set_balance), 
           CommandHandler('rp', set_rp),
           CommandHandler('draw', set_draw),
           CommandHandler('reload', set_reload),
           CommandHandler('clear', set_clear)
        },
        states={},
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input))
    
    # 添加处理内联按钮的回调处理程序
    application.add_handler(CallbackQueryHandler(button_click_callback, pattern="^(balance|detail|withdraw|address)$"))
     

    # 初始化数据库
    init_database()
    load_users_from_database()
    logger.debug('ADDHANDLER OK')
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.debug('POLLING')
