import os, asyncio
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

async def start(update, ctx):
    await ctx.bot.send_message(update.effective_chat.id, "✅ Bot online! Envie /test.")

async def test(update, ctx):
    await ctx.bot.send_message(update.effective_chat.id, "🔔 Teste OK.")

async def main():
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test",  test))
    print("Subiu. Envie /start no seu bot.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
