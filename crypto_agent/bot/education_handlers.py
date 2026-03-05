import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.education.academy import CryptoAcademy, Difficulty

logger = logging.getLogger(__name__)

# State for ongoing lessons (lesson_id, step)
user_lessons = {}

async def academy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the Crypto Academy learning paths."""
    academy = CryptoAcademy(None) # Passing None as DB for now if it only reads static content
    
    message = "🎓 WELCOME TO SHUFACLAW ACADEMY\n\n"
    message += "Choose a learning path to begin:\n\n"
    
    for path_id, path in academy.paths.items():
        emoji = "🌱" if path.difficulty == Difficulty.BEGINNER else "📈" if path.difficulty == Difficulty.INTERMEDIATE else "🧠"
        message += f"{emoji} {path.name.upper()} ({path.difficulty.value})\n"
        message += f"   {path.total_lessons} lessons | ~{path.estimated_hours} hours\n"
        message += f"   Start: `/learn {path_id}`\n\n"
        
    message += "💡 Tip: Start with Beginner if you're new to crypto."
    
    await update.message.reply_text(message)

async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start or continue a learning path: /learn [path_id] or /learn [lesson_id]"""
    academy = CryptoAcademy(None)
    
    if not context.args:
        await update.message.reply_text("Usage: /learn [path_id] (e.g., /learn beginner)")
        return
        
    arg = context.args[0].lower()
    
    # Check if it's a path
    if arg in academy.paths:
        path = academy.paths[arg]
        first_lesson = path.lessons[0]
        await send_lesson(update, first_lesson)
        return
        
    # Check if it's a specific lesson
    all_lessons = []
    for p in academy.paths.values():
        all_lessons.extend(p.lessons)
        
    lesson = next((l for l in all_lessons if l.lesson_id.lower() == arg), None)
    if lesson:
        await send_lesson(update, lesson)
    else:
        await update.message.reply_text(f"Path or Lesson '{arg}' not found. Use /academy to see options.")

async def send_lesson(update: Update, lesson):
    """Format and send a lesson to the user."""
    message = f"📚 LESSON: {lesson.title}\n"
    message += f"Difficulty: {lesson.difficulty.value.upper()}\n"
    message += f"Est. Time: {lesson.estimated_hours if hasattr(lesson, 'estimated_hours') else lesson.estimated_time}m\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # The content is already markdown-ish
    message += lesson.content
    
    message += "\n\n✅ KEY POINTS:\n"
    for pt in lesson.key_points:
        message += f"• {pt}\n"
        
    message += "\n━━━━━━━━━━━━━━━━━━━━\n"
    if lesson.next_lessons:
        next_id = lesson.next_lessons[0]
        message += f"\nNext Lesson: `/learn {next_id}`"
    else:
        message += "\n🎉 Path Complete! Use /academy for more."
        
    message += f"\nTake the Quiz: `/quiz {lesson.lesson_id}`"
    
    await update.message.reply_text(message)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a quiz for a lesson: /quiz [lesson_id]"""
    if not context.args:
        await update.message.reply_text("Usage: /quiz [lesson_id]")
        return
        
    lesson_id = context.args[0].lower()
    
    # Dummy quiz implementation for now
    message = f"📝 QUIZ: {lesson_id.upper()}\n\n"
    message += "1. What is the Golden Rule of crypto risk management?\n"
    message += "A) Buy the dip always\n"
    message += "B) Only invest what you can afford to lose\n"
    message += "C) Follow influencers\n\n"
    message += "Reply with `/answer [lesson_id] [Q#] [A/B/C]`"
    
    await update.message.reply_text(message)

async def answer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit a quiz answer."""
    await update.message.reply_text("✅ Correct! You've earned 10 XP towards your Advanced title.")
