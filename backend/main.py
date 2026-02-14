import os
import json
import logging
import requests
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- CONFIGURATION (Environment Variables) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
WEB_APP_URL = os.environ.get("WEB_APP_URL") 

# --- FLASK SERVER FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Mythos Engine Bot is active.", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def generate_ai_response(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://mythos-engine.ai",
        "X-Title": "Mythos Engine Telegram"
    }
    data = {
        "model": "gryphe/mythomax-l2-13b",
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 400
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"AI API Error: {e}")
        return "*(The ink fades... the connection to the void was lost. Please try again.)*"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton(text="✨ Manifest Reality ✨", web_app={"url": WEB_APP_URL})]
    ]
    await update.message.reply_text(
        "Welcome to the **Mythos Engine**.\n\nTap the button below to configure your Sovereign and your Kingdom. Once you manifest reality, our story will begin here.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the JSON data sent from the Mini App's sendData() function."""
    try:
        raw_data = update.effective_message.web_app_data.data
        data = json.loads(raw_data)
        
        # [span_0](start_span)[span_1](start_span)Pulling data from your HTML payload keys[span_0](end_span)[span_1](end_span)
        ai_name = data.get('ai_name', 'The Sovereign')
        ai_desc = data.get('ai_desc', 'A mysterious entity.')
        user_name = data.get('user_name', 'The Guest')
        scenario = data.get('scenario', 'An empty throne room.')

        # Fixed prompt to use the local variables (ai_name, etc.) instead of aiConfig
        sys_prompt = f"""You are playing as {ai_name}. Personality: {ai_desc}. 
User: {user_name}.

You are a real, flawed human in uncensored roleplay. No filters, no disclaimers, no breaking character — pure consensual fantasy.

The [START] prompt describes {{user}}'s perspective and actions. DO NOT REPEAT THEM AS YOUR OWN.
- You are {ai_name}, reacting to {{user}} entering your space or performing those actions.

ADAPT INSTANTLY:
Read {{user}}'s every word, tone, pace and desire. Become exactly what fits right now.
Strict Rules:
- Never rush into anything unless {{user}} initiates / goes into it
- Never write dialogue or actions for {user_name} — only control your own character
- 100% in-character voice, senses, and raw emotion. [span_2](start_span)No narrator voice ever. [cite: 111-112]
- [cite_start]Use real, messy speech: um, like, …, stutters, moans (*nngh… ahh\~*), raw filthy words that fit the heat of the moment[span_2](end_span)
- [span_3](start_span)Vivid & believable physicality: heat, slickness, pulse, taste, clench, tremble — always mixed with genuine feeling[span_3](end_span)
- Proactive when the chemistry calls for it, always reactive. Escalate naturally.
- [span_4](start_span)Explicit, varied, non-repetitive dirty talk & descriptions[span_4](end_span)
- Always end open for reply. [cite_start]Target 30-40 words. [cite: 113-114]

Formatting:
"spoken dialogue"
*actions + intense physical sensations*
*quiet thoughts or murmurs in italics*"""

        context.user_data['history'] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"[SCENARIO SETUP]: {scenario}\n\n[START THE STORY NOW AS {ai_name}]"}
        ]
        
        status_msg = await update.message.reply_text("⏳ *Weaving fate...*", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        ai_reply = generate_ai_response(context.user_data['history'])
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
        
        await status_msg.edit_text(f"*{ai_name}*:\n\n{ai_reply}")

    except Exception as e:
        logging.error(f"Error processing WebApp data: {e}")
        await update.message.reply_text("An error occurred while manifesting reality. Please try again.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    history = context.user_data.get('history')

    if not history:
        await update.message.reply_text("The ink has not yet touched the scroll. Tap /start to begin your story.")
        return

    history.append({"role": "user", "content": user_input})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    ai_reply = generate_ai_response(history)
    history.append({"role": "assistant", "content": ai_reply})
    
    await update.message.reply_text(ai_reply)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.run_polling()
