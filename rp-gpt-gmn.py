import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
#from dotenv import load_dotenv
import os
import random
import csv
import datetime
import logging

# Load environment variables
#load_dotenv()
# 配置日志记录器的配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建一个日志记录器
logger = logging.getLogger()
# Telegram Bot Token
TOKEN = '7061360321:AAGIxtGGi2RCeXjSMifKHt71iGwkQ9Ek7Vk'

# Group administrator ID (replace with actual ID)
ADMIN_ID = 123456

# Define conversation states
START, SETTING_PARAMETERS = range(2)

# Store current red packet activity
current_redpacket = None

# Create bot instance
bot = telegram.Bot(token=TOKEN)

# Handle command "/setrp"
async def set_redpacket(update, context):
    logger.debug('____SET_REDPACKET')
    # Check if sender is a group administrator
    if not update.message.chat.type == 'group':
        update.message.reply_text('Please use this command in a group chat!')
        return ConversationHandler.END

    if not update.message.chat.get_member(update.message.from_user.id).status == 'administrator':
        update.message.reply_text('Only group administrators can set red packet parameters!')
        return ConversationHandler.END
    logger.debug('____SET_REDPACKET--------------------R U admin?')
    # Parse command arguments
    args = context.args
    if len(args) < 2:
        update.message.reply_text('Please enter total amount and number of packets!')
        return ConversationHandler.END

    try:
        total_amount = float(args[0])
        num_packets = int(args[1])
    except ValueError:
        update.message.reply_text('Please enter valid total amount and number of packets!')
        return ConversationHandler.END

    # Extract password (if any)
    password = ' '.join(args[2:])

    # Create red packet activity
    global current_redpacket
    current_redpacket = {
        'total_amount': total_amount,
        'num_packets': num_packets,
        'password': password,
        'remaining_amount': total_amount,
        'participants': [],
        'start_time': datetime.datetime.now()
    }

    # Generate red packet activity message
    message = f'Red Packet Activity:\nTotal Amount: {total_amount}\nNumber of Packets: {num_packets}'
    if password:
        message += f'\nPassword: {password}'

    # Create button
    keyboard = [[InlineKeyboardButton("Grab Red Packet", callback_data="grab_redpacket")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send red packet activity message to the group
    update.message.reply_text(message, reply_markup=reply_markup)

    return ConversationHandler.END

# Handle button click events
def button_callback(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "grab_redpacket":
        # Check if all packets are grabbed
        if len(current_redpacket['participants']) >= current_redpacket['num_packets']:
            query.message.reply_text('All packets are grabbed!')
            return

        # Check if password is set
        if current_redpacket['password']:
            query.message.reply_text('Please enter the password to grab the red packet:')
            return

        # Grab the red packet
        grab_redpacket(query.message)

# Handle password input events
def handle_password_input(update, context):
    user_input = update.message.text.strip()

    if user_input == current_redpacket['password']:
        grab_redpacket(update.message)
    else:
        update.message.reply_text('Incorrect password, please try again:')

# Logic for grabbing red packets
def grab_redpacket(message):
    global current_redpacket

    # Randomly allocate red packet amount
    remaining_amount = current_redpacket['remaining_amount']
    amount = random.uniform(0, remaining_amount)

    current_redpacket['participants'].append({
        'username': message.from_user.username,
        'amount': amount,
        'time': datetime.datetime.now()
    })

    current_redpacket['remaining_amount'] -= amount

    # Update red packet activity message
    update_redpacket_message(message.chat_id)

    # Publish updated red packet information
    if len(current_redpacket['participants']) == current_redpacket['num_packets']:
        publish_redpacket_results(message.chat_id)

# Update red packet activity message
def update_redpacket_message(chat_id):
    global current_redpacket

    message = f'Red Packet Activity:\nTotal Amount: {current_redpacket["total_amount"]}\nRemaining Amount: {current_redpacket["remaining_amount"]}\nNumber Grabbed: {len(current_redpacket["participants"])}/{current_redpacket["num_packets"]}'
    bot.send_message(chat_id=chat_id, text=message)

# Publish red packet grab results
def publish_redpacket_results(chat_id):
    global current_redpacket

    # Write to file
    filename = f'redpacket_results_{current_redpacket["start_time"].strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Username', 'Amount', 'Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in current_redpacket['participants']:
            writer.writerow({'Username': participant['username'], 'Amount': participant['amount'], 'Time': participant['time']})

    # Send file to group administrator
    bot.send_document(chat_id=ADMIN_ID, document=open(filename, 'rb'), caption=f'Red Packet Grab Results ({current_redpacket["start_time"]})')

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

