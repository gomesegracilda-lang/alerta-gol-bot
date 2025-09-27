# main.py — Bot de alertas de gol (janela 3min)
import os, asyncio, math, random
from datetime import datetime, timedelta
from telegram.ext import ApplicationBuilder, CommandHandler

WINDOW_MINUTES = int(os.getenv("WINDOW_MINUTES", "3"))
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.6"))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

def prob_goal_next_window(xg_recent: float, shots_on_target: int,
                          red_advantage: bool, fav_ld_after60: bool) -> float:
    lam = max(0.0, xg_recent)
    if red_advantage: lam *= 1.30
    if fav_ld_after60: lam *= 1.15
    if shots_on_target >= 2: lam *= 1.10
    return max(0.0, min(1.0, 1 - math.exp(-lam)))

def reasons(xg, sot, red, fav):
    r = [f"xG{WINDOW_MINUTES}={xg:.2f}"]
    if sot >= 2: r.append(f"{sot} SOT/{WINDOW_MINUTES}'")
    if red: r.append("11v10")
    if fav: r.append("favorito perdendo/empatando")
    return ", ".join(r)

class MockMatch:
    def __init__(self, mid, league, home, away):
        self.id = mid; self.league = league; self.home = home; self.away = away
        self.minute = 1; self.score = "0-0"
        self.xg = 0.05; self.sot = 0; self.red = False; self.fav = False
    def tick(self):
        self.minute += 1
        self.xg = max(0.01, min(1.2, self.xg + random.choice([-.03, .02, .05, .08])))
        self.sot = max(0, min(4, self.sot + random.choice([0,0,1])))
        if self.minute in (30, 65): self.fav = True
        if self.minute in (70,) and not self.red: self.red = True

def get_mock_matches():
    if not hasattr(get_mock_matches, "games"):
        get_mock_matches.games = [MockMatch("M1", "Liga Demo", "Time A", "Time B"),
                                  MockMatch("M2", "Copa Teste", "Time C", "Time D")]
    for g in get_mock_matches.games: g.tick()
    return get_mock_matches.games

USERS = {}

async def cmd_start(update, ctx):
    cid = update.effective_chat.id
    USERS.setdefault(cid, {"threshold": ALERT_THRESHOLD, "last_alert": {}})
    await ctx.bot.send_message(cid,
        f"Bot ligado! Janela: {WINDOW_MINUTES} min • Threshold: {USERS[cid]['threshold']:.2f}\n"
        f"Use /threshold 0.65 para ajustar. Use /test para um alerta de teste.")

async def cmd_threshold(update, ctx):
    cid = update.effective_chat.id
    if not ctx.args: return await ctx.bot.send_message(cid, "Ex.: /threshold 0.6")
    try:
        v = max(0.1, min(0.95, float(ctx.args[0])))
        USERS.setdefault(cid, {"threshold": ALERT_THRESHOLD, "last_alert": {}})
        USERS[cid]["threshold"] = v
        await ctx.bot.send_message(cid, f"Threshold atualizado para {v:.2f}")
    except ValueError:
        await ctx.bot.send_message(cid, "Valor inválido. Ex.: /threshold 0.6")

async def cmd_test(update, ctx):
    cid = update.effective_chat.id
    await ctx.bot.send_message(cid, f"⚽ Prob. alta de gol — Jogo de teste\nP≈72% • {reasons(0.55, 3, True, True)}")

async def loop_processor(app):
    while True:
        now = datetime.utcnow()
        for m in get_mock_matches():
            p = prob_goal_next_window(m.xg, m.sot, m.red, m.fav)
            bucket = m.minute // max(1, WINDOW_MINUTES)
            for cid, prefs in USERS.items():
                thr = prefs.get("threshold", ALERT_THRESHOLD)
                if p >= thr:
                    last = prefs["last_alert"].get((m.id, bucket))
                    if not last or (now - last) > timedelta(minutes=WINDOW_MINUTES-1):
                        title = f"⚽ Prob. alta de gol — {m.league} {m.minute}'"
                        body = f"{m.home} {m.score} {m.away}\nP≈{p*100:.0f}% • {reasons(m.xg, m.sot, m.red, m.fav)}"
                        await app.bot.send_message(cid, f"{title}\n{body}")
                        prefs["last_alert"][(m.id, bucket)] = now
        await asyncio.sleep(5)

async def start_health():
    from aiohttp import web
    async def ok(_): return web.json_response({"ok": True, "window": WINDOW_MINUTES})
    app = web.Application(); app.router.add_get("/health", ok)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080); await site.start()

async def main():
    if not TOKEN: raise SystemExit("Falta TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("threshold", cmd_threshold))
    app.add_handler(CommandHandler("test", cmd_test))
    asyncio.create_task(loop_processor(app))
    await start_health()
    print(f"Bot on. WINDOW_MINUTES={WINDOW_MINUTES} THR={ALERT_THRESHOLD}")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
