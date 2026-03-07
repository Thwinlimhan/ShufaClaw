import logging
import aiohttp
import os
from gtts import gTTS
from telegram import Update
from telegram.ext import ContextTypes
from io import BytesIO

from crypto_agent import config
from crypto_agent.bot import middleware
from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent.storage import database
from crypto_agent.core.context_builder import build_full_context
from crypto_agent.core import prompts

logger = logging.getLogger(__name__)

VOICE_STATE = {"enabled": False}

@middleware.require_auth
async def toggle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /voice command"""
    if not context.args:
        status = "ON" if VOICE_STATE['enabled'] else "OFF"
        await update.message.reply_text(f"Voice Mode is currently: **{status}**\nType `/voice on` or `/voice off`", parse_mode="Markdown")
        return
        
    arg = context.args[0].lower()
    if arg == "on":
        VOICE_STATE["enabled"] = True
        await update.message.reply_text("🗣️ **Voice Mode: ON**\n\nI will now transcribe your voice notes using Whisper and reply to you with AI-generated speech via gTTS.", parse_mode="Markdown")
    elif arg == "off":
        VOICE_STATE["enabled"] = False
        await update.message.reply_text("🔇 **Voice Mode: OFF**\n\nYou can still send me voice notes to transcribe, but I will reply in text only.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Unknown command. Use `/voice on` or `/voice off`.")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercepts Voice Notes, transcripts them with Whisper, and replies."""
    # Ensure they are authorized
    if str(update.effective_user.id) != str(config.MY_TELEGRAM_ID):
        logger.warning(f"Unauthorized Voice Attempt from {update.effective_user.id}")
        return
        
    if not config.GROQ_API_KEY:
        await update.message.reply_text("❌ **Whisper API Error**\n\nTo process voice notes, you need a free Groq API key. Please add `GROQ_API_KEY=your_key_here` to your `.env` file.", parse_mode="Markdown")
        return

    # 1. Download Telegram OGG file
    voice = update.message.voice
    if not voice:
        return
        
    file_id = voice.file_id
    new_file = await context.bot.get_file(file_id)
    
    temp_ogg = "temp_voice.ogg"
    await new_file.download_to_drive(temp_ogg)
    
    # 2. Transcribe using Groq API
    msg = await update.message.reply_text("⏳ `Running Whisper locally via Groq...`", parse_mode="Markdown")
    transcription = ""
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {config.GROQ_API_KEY}"
        }
        
        with open(temp_ogg, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("file", f, filename="temp_voice.ogg", content_type="audio/ogg")
            data.add_field("model", "whisper-large-v3")
            data.add_field("response_format", "json")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status == 200:
                        res_data = await resp.json()
                        transcription = res_data.get("text", "")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Groq API Error: {error_text}")
    except Exception as e:
        logger.error(f"Error transcribing voice: {e}")
        
    # Clean up temp file
    if os.path.exists(temp_ogg):
        os.remove(temp_ogg)
        
    if not transcription:
        await msg.edit_text("❌ Failed to transcribe your voice message. Try again.")
        return
        
    # Inform user of what we heard
    await msg.edit_text(f"🎤 *You asked:* \"{transcription}\"\n`Synthesizing response...`", parse_mode="Markdown")
    
    # 3. Process transcription like normal text via AI
    history = database.get_last_n_messages(10)
    context_data = await build_full_context()
    
    prompt = f"{prompts.get_system_prompt('default')}\n\nThe user spoke to you. Give a helpful but conversational and concise answer.\n\nContext:\n{context_data}"
    ai_payload = [{"role": "system", "content": prompt}] + history + [{"role": "user", "content": transcription}]
    
    ai_response = await get_ai_response(ai_payload)
    
    if not ai_response:
        await msg.edit_text("❌ AI API Error while generating response.")
        return
        
    # 4. Save to database
    database.save_message("user", transcription)
    database.save_message("assistant", ai_response)
    
    # 5. Reply with Text or Voice
    if VOICE_STATE["enabled"]:
        # Clean up Markdown for text-to-speech to prevent robot saying "asterisk asterisk"
        tts_text = ai_response.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
        # Limit voice output to prevent massive audio payloads
        if len(tts_text) > 500:
            tts_text = tts_text[:500] + " ... I've truncated the audio. You can read the rest in the text below."
        
        try:
            tts = gTTS(text=tts_text, lang='en', tld='com') # using US English
            audio_io = BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            
            await msg.delete() # delete the "thinking" message
            # Send voice message back
            await update.message.reply_voice(voice=audio_io, caption=ai_response)
        except Exception as e:
            logger.error(f"gTTS Error: {e}")
            await msg.edit_text(ai_response) # fallback to text
    else:
        # Just text
        await msg.edit_text(ai_response)
