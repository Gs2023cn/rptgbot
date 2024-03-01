import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ChatMember
#from dotenv import load_dotenv
import os
import random
import csv
import datetime
import logging
import uuid

# Load environment variables
#load_dotenv()
# 配置日志记录器的配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建一个日志记录器
logger = logging.getLogger()
# Telegram Bot Token
TOKEN = '7061360321:AAGIxtGGi2RCeXjSMifKHt71iGwkQ9Ek7Vk'

# Group administrator ID (replace with actual ID)
ADMIN_ID = 6945651433

# Define states for the conversation handler
PASSWORD_INPUT = 1

# Define conversation states
START, SETTING_PARAMETERS = range(2)

# Store current red packet activity
current_redpacket = None

# Create bot instance
bot = telegram.Bot(token=TOKEN)

# 生成红包ID的函数
def generate_redpacket_id():
    return str(uuid.uuid4())

# Handle command "/setrp"
async def set_redpacket(update, context):
    logger.debug('____SET_REDPACKET')
    global current_redpacket
     # Parse command arguments
    args = context.args
    if len(args) < 1:
        await update.message.reply_text('红包发布格式：/setrp <总金额> <个数> [<口令>]  请注意使用空格区分参数，口令是可选的!')
        #bot.send_message(chat_id = update.message.chat_id, message='红包发布格式：/setrp <总金额> <个数> [<口令>]  请注意使用空格区分参数，口令是可选的！')
        return ConversationHandler.END
    
    try:
        total_amount = float(args[0])
        if len(args) >= 2:
            num_packets = int(args[1])
    except ValueError:
        update.message.reply_text('输入数据有误，请重新尝试!')
        return ConversationHandler.END

       # 判断是否为关闭红包命令
    if  total_amount <= 0:
        if current_redpacket: 
            await publish_redpacket_results(ADMIN_ID)
            await update.message.reply_text('当前红包已关闭!')
        else:
            await update.message.reply_text('当前无红包!')
        return ConversationHandler.END
    
    if current_redpacket:
        await update.message.reply_text('之前红包还没抢完，别急!')
        return
    # Check if sender is a group administrator
    if update.message.chat.type not in ['group', 'supergroup']:
        bot.send_message(chat_id = update.message.chat_id, message='请直接在群中发布红包！')
        return ConversationHandler.END
#    chat_member = update.message.chat.get_member(update.message.from_user.id)
#    if not chat_member.status == ChatMember.ADMINISTRATOR:
        #update.message.reply_text('只有管理员可以发红包哦!')
#        bot.send_message(chat_id = update.message.chat_id, message='只有管理员可以发红包哦!感谢热心参与!')
#        return ConversationHandler.END
   
    # Extract password (if any)
    password = ' '.join(args[2:])
    #password_message = f'口令红包：{password}' if password else '点我抢红包'
    password_message = f'找客服寻财富密码' if password else '点我抢红包'
    # Create red packet activity
    current_redpacket_id = str(uuid.uuid4())  # 生成唯一标识符，可以是随机数或其他方式
    current_redpacket = {
        'id': current_redpacket_id,
        'total_amount': total_amount,
        'num_packets': num_packets,
        'password': password,
        'remaining_amount': total_amount,
        'participants': [],
        'start_time': datetime.datetime.now()
    }
    print(current_redpacket)

    # Generate red packet activity message
    message = f'来抢红包咯:\n总额: {total_amount}\n个数: {num_packets}'
    logger.debug('++++++++++++____SET_REDPACKET--------------------' + message)
    #if password:
        #message += f'\n财富密码: {password}'
    logger.debug('++++++++++++____SET_REDPACKET--------------------')
    # Create button
    
    keyboard = [[InlineKeyboardButton(password_message, callback_data = current_redpacket_id)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send red packet activity message to the group
    await update.message.reply_photo(photo=open('./rp.png', 'rb'), caption=message, reply_markup=reply_markup)
    
    return ConversationHandler.END

# Handle button click events
async def button_callback(update, context):
    query = update.callback_query
    query.answer()
    global current_redpacket
    if current_redpacket is None:
        await query.message.reply_text('红包被抢完啦，下次再来!')
        return

    if current_redpacket['password']:
        await query.message.reply_text('这是口令红包，请发送财富密码!')
        return
    #user = update.effective_user
    #user_id = user.id

    # 获取当前红包活动的标识符
    current_redpacket_id = current_redpacket.get('id')
    # 获取按钮点击事件中的红包活动标识符
    clicked_redpacket_id = query.data
    logger.debug('@@@@@@@@@@@@@@@@@   currid%s clickid%s##############', str(current_redpacket_id), str(clicked_redpacket_id))
        # 检查按钮点击的红包活动标识符是否与当前活动的红包标识符匹配
    if current_redpacket_id != clicked_redpacket_id:
        await query.message.reply_text('您点击的红包活动已结束或不存在!')
        return
    
    user =  query.from_user
    user_id = user.id
    
    user_name = user.username or (user.first_name + ' ' + user.last_name)
    chat_member = query.message.chat.get_member(user.id)

#    #限制只有普通用户才能抢红包
#    if not chat_member.status == ChatMember.MEMBER:
#        query.message.reply_text('Only regular group members can participate in the red packet activity!')
#        return

    # 检查当前用户是否已经参加过红包活动
    already_participated = any(participant['userid'] == user_id for participant in current_redpacket['participants'])
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Already Participated:", already_participated) 
    if already_participated:
        await query.message.reply_text(f'您 ({user_name})已经参加过啦，机会留给其他朋友吧!')
        #bot.send_message(chat_id = update.message.chat_id, text='您 ({user_name})已经参加过啦，机会留给其他朋友吧!')
        return
    
   # if query.data == "grab_redpacket":
        # Check if all packets are grabbed
    if len(current_redpacket['participants']) >= current_redpacket['num_packets']:
        await query.message.reply_text('所有红包被抢完咯!')
        return

        # Check if password is set
    if current_redpacket['password']:
        await query.message.reply_text('请输入财富密码:')
        return
    logger.debug('++++++++++++grab_redpacket--------------------')
        # Grab the red packet
        #await grab_redpacket(query)
    await grab_redpacket(update)

# Handle password input events
async def handle_password_input(update, context):
    logger.debug('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%handle_password_input--------------------')
    logger.debug('Received password input: %s', update.message.text.strip())  # 添加
    global current_redpacket
    if current_redpacket is None:
        return
    if not current_redpacket['password']:
        return
    
    user_input = update.message.text.strip()
    
    
    if user_input == current_redpacket['password']:
        user = update.effective_user
        user_id =  user.id
        user_name = user.username or (user.first_name + ' ' + user.last_name)
        already_participated = any(participant['userid'] == user_id for participant in current_redpacket['participants'])
        if already_participated:
            return
        else:
            if len(current_redpacket['participants']) >= current_redpacket['num_packets']:
                return
            await grab_redpacket(update)
    else:
        return
        #update.message.reply_text('口令不对，请重新输入！')

# Logic for grabbing red packets
async def grab_redpacket(update):
    global current_redpacket

    # Randomly allocate red packet amount
    remaining_amount = current_redpacket['remaining_amount']
    
    if len(current_redpacket["participants"]) < (current_redpacket["num_packets"] - 1):
        amount = round(random.uniform(0, remaining_amount),2)
    else:
        amount = remaining_amount
    if current_redpacket['password']:
        user = update.effective_user
    else:
        user = update.callback_query.from_user
        
    current_redpacket['participants'].append({
        'userid': user.id,
        'username': user.username or (user.first_name + ' ' + user.last_name),
        'amount': amount,
        'time': datetime.datetime.now()
    })
    #print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~who:", current_redpacket['participants'])
    current_redpacket['remaining_amount'] = round((remaining_amount - amount),2)
 
    # Update red packet activity message
    await update_redpacket_message(update)

    # Publish updated red packet information   
    if len(current_redpacket['participants']) == current_redpacket['num_packets']:
        logger.debug('^^^^^^^^^^^^^^^^----------------publish_redpacket_results+++++++++++----')
        await publish_redpacket_results(ADMIN_ID)

# Update red packet activity message
async def update_redpacket_message(update):
    global current_redpacket

    total_amount = current_redpacket["total_amount"]
    num_packets = current_redpacket["num_packets"]
    participants = current_redpacket["participants"]

    message_text = f'抢红包咯:\n总   额: {total_amount}\n幸运儿: {len(participants)}/{num_packets}\n'

    # 遍历参与者列表，将用户名和抢到的金额添加到消息中
    for participant in participants:
        username = participant["username"]
        amount = participant["amount"]
        message_text += f'{username.ljust(20)}{amount:>10}\n'
        
    if current_redpacket['password']:
        await update.message.reply_text(message_text)
    else:
        await update.callback_query.message.reply_text(message_text)

    #new_message = f'抢红包咯:\n总  额: {current_redpacket["total_amount"]}\n余  额: {current_redpacket["remaining_amount"]}\n幸运儿: {len(current_redpacket["participants"])}/{current_redpacket["num_packets"]}\n '
    #new_message = f'抢红包咯:\n总  额: {current_redpacket["total_amount"]}\n幸运儿: {len(current_redpacket["participants"])}/{current_redpacket["num_packets"]}\n '
    #await message.reply_text(new_message)
    #await bot.send_message(chat_id = message.chat_id, text = new_message)

# Publish red packet grab results
async def publish_redpacket_results(chat_id):
    global current_redpacket
    
    if (len(current_redpacket['participants']) == 0):
        current_redpacket = None
        return
    
    # Write to file
    filename = f'redpacket_results_{current_redpacket["start_time"].strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    print(filename)
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['ID', 'Username', 'Amount', 'Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in current_redpacket['participants']:
            writer.writerow({'ID': participant['userid'], 'Username': participant['username'], 'Amount': participant['amount'], 'Time': participant['time']})

    # Send file to group administrator
    await bot.send_document(chat_id=ADMIN_ID, document=open(filename, 'rb'), caption=f'Red Packet Grab Results ({current_redpacket["start_time"]})')
    current_redpacket = None

if __name__ == '__main__':
    logger.debug('MAIN')
    application = Application.builder().token("7061360321:AAGIxtGGi2RCeXjSMifKHt71iGwkQ9Ek7Vk").build()
    logger.debug('build OK')
# Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setrp', set_redpacket)],
        states={},
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input))
    logger.debug('ADDHANDLER OK')
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.debug('POLLING')
# Start polling
#bot.polling()

