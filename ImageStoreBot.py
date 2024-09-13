import os
import sqlite3
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load API Key and Admin User ID from environment variables
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
ADMIN_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))

# Initialize SQLite Database
conn = sqlite3.connect('photos.db')
c = conn.cursor()

# Create table to store user photos
c.execute('''CREATE TABLE IF NOT EXISTS photos (user_id INT, file_id TEXT, tag TEXT, reviewed INT)''')
conn.commit()

# Start Command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome to ImageStoreBot! You can upload your photos, and I will keep them safe.")

# Help Command
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("You can upload photos to store them securely. Use /get <tag> to retrieve photos.")

# Handle Photo Upload
def handle_photo(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    file_id = photo_file.file_id
    
    # Save photo in database (marked as unreviewed)
    c.execute("INSERT INTO photos (user_id, file_id, tag, reviewed) VALUES (?, ?, ?, ?)", 
              (user.id, file_id, None, 0))
    conn.commit()

    update.message.reply_text("Photo uploaded! Please provide a tag using /tag <your_tag>.")

# Tag Photo
def tag_photo(update: Update, context: CallbackContext) -> None:
    tag = ' '.join(context.args)
    user_id = update.message.from_user.id
    
    # Update the most recent untagged photo with the provided tag
    c.execute("UPDATE photos SET tag = ? WHERE user_id = ? AND tag IS NULL ORDER BY rowid DESC LIMIT 1", 
              (tag, user_id))
    conn.commit()
    
    update.message.reply_text(f"Tag '{tag}' added to your most recent photo!")

# Retrieve Photo
def get_photo(update: Update, context: CallbackContext):
    tag = ' '.join(context.args)
    user_id = update.message.from_user.id
    
    # Get the approved photo for the user based on the tag
    c.execute("SELECT file_id FROM photos WHERE user_id = ? AND tag = ? AND reviewed = 1", (user_id, tag))
    result = c.fetchone()
    
    if result:
        file_id = result[0]
        context.bot.send_photo(chat_id=update.message.chat_id, photo=file_id)
    else:
        update.message.reply_text("No approved photo found with that tag.")

# Admin Review Photos
def review_photos(update: Update, context: CallbackContext):
    admin_id = update.message.from_user.id
    if admin_id == ADMIN_USER_ID:
        c.execute("SELECT file_id, user_id, tag FROM photos WHERE reviewed = 0")
        unreviewed_photos = c.fetchall()
        
        if unreviewed_photos:
            for file_id, user_id, tag in unreviewed_photos:
                context.bot.send_message(chat_id=admin_id, text=f'Photo from user {user_id} with tag "{tag}"')
                context.bot.send_photo(chat_id=admin_id, photo=file_id)
                context.bot.send_message(chat_id=admin_id, text=f'Approve or reject? /approve {file_id} /reject {file_id}')
        else:
            update.message.reply_text("No photos to review.")
    else:
        update.message.reply_text("You are not authorized to review photos.")

# Approve Photo
def approve_photo(update: Update, context: CallbackContext):
    admin_id = update.message.from_user.id
    if admin_id == ADMIN_USER_ID:
        file_id = context.args[0]
        c.execute("UPDATE photos SET reviewed = 1 WHERE file_id = ?", (file_id,))
        conn.commit()
        update.message.reply_text(f"Photo {file_id} approved.")
    else:
        update.message.reply_text("You are not authorized to approve photos.")

# Reject Photo
def reject_photo(update: Update, context: CallbackContext):
    admin_id = update.message.from_user.id
    if admin_id == ADMIN_USER_ID:
        file_id = context.args[0]
        c.execute("DELETE FROM photos WHERE file_id = ?", (file_id,))
        conn.commit()
        update.message.reply_text(f"Photo {file_id} rejected and deleted.")
    else:
        update.message.reply_text("You are not authorized to reject photos.")

# Main function to start the bot
def main():
    updater = Updater(TELEGRAM_API_KEY, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(CommandHandler("tag", tag_photo, pass_args=True))
    dp.add_handler(CommandHandler("get", get_photo, pass_args=True))
    dp.add_handler(CommandHandler("review", review_photos))
    dp.add_handler(CommandHandler("approve", approve_photo, pass_args=True))
    dp.add_handler(CommandHandler("reject", reject_photo, pass_args=True))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
              
