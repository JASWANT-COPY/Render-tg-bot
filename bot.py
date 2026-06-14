#!/usr/bin/env python3
import asyncio,re,os,sys,time,json,shutil,signal,traceback,threading
from datetime import datetime
from urllib.parse import urlparse,parse_qs
from pathlib import Path
from collections import defaultdict
try:
    from pyrogram import Client,filters
    from pyrogram.types import *
    from pyrogram.errors import FloodWait
except: os.system("pip install pyrogram tgcrypto -q"); from pyrogram import Client,filters; from pyrogram.types import *; from pyrogram.errors import FloodWait
try: import yt_dlp
except: os.system("pip install yt-dlp -q"); import yt_dlp
try: import aiohttp
except: os.system("pip install aiohttp -q"); import aiohttp
API_ID=int(os.environ.get("API_ID","0"))
API_HASH=os.environ.get("API_HASH","")
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
OWNER_ID=int(os.environ.get("OWNER_ID","0"))
TEMP_DIR="/tmp/videos"
CACHE_FILE="/tmp/cache.json"
MAX_MB=1900
FLOOD=2.5
CACHE_TTL=3600
E={"dl":"📥","up":"📤","ok":"✅","no":"❌","wait":"⏳","speed":"⚡","stats":"📊","vid":"🎬","clock":"⏱","size":"📦","user":"👤","link":"🔗","web":"🌐","star":"⭐","fire":"🔥","cloud":"☁️","rocket":"🚀","phone":"📱","bulb":"💡","bar":"█","empty":"░","disk":"💾"}
stats={"p":0,"ok":0,"no":0,"mb":0.0,"st":datetime.now().isoformat(),"u":{},"pl":defaultdict(int),"ch":0,"cm":0}
cache={}
def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"); sys.stdout.flush()
def fs(b):
    if not b or b<=0: return "0 B"
    mb=b/1048576
    if mb>=1000: return f"{mb/1024:.1f} GB"
    if mb>=1: return f"{mb:.1f} MB"
    return f"{b/1024:.1f} KB"
def ft(s):
    if not s or s<=0: return "00:00"
    m,sec=divmod(int(s),60); h,m=divmod(m,60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
def bar(pct,length=16): return E["bar"]*int(length*min(100,max(0,pct))/100)+E["empty"]*(length-int(length*min(100,max(0,pct))/100))
def urls(text):
    if not text: return []
    us=re.findall(r'https?://[^\s<>\"\'{}\[\]\\|^`\n\r\t]+',text,re.IGNORECASE)
    cl,seen=[],set()
    for u in us:
        if not u.startswith('http'): u='https://'+u
        try:
            p=urlparse(u)
            if p.scheme in ['http','https'] and p.netloc and '.' in p.netloc:
                if u not in seen: seen.add(u); cl.append(u)
        except: pass
    return cl
def plat(url):
    d=urlparse(url).netloc.lower()
    if any(x in d for x in ['youtube.com','youtu.be']): return "🎬 YouTube"
    if 'instagram.com' in d: return "📸 Instagram"
    if any(x in d for x in ['facebook.com','fb.watch']): return "👤 Facebook"
    if any(x in d for x in ['twitter.com','x.com']): return "🐦 Twitter/X"
    if 'tiktok.com' in d: return "🎵 TikTok"
    if any(x in d for x in ['rumble.com','rumble.cloud']): return "🔴 Rumble"
    if any(x in d for x in ['.mp4','.webm','.mkv','cdn.','stream','/video/']): return "💿 CDN"
    return "🔗 Link"
async def se(msg,text,kb=None):
    try:
        if kb: await msg.edit_text(text,reply_markup=kb,disable_web_page_preview=True)
        else: await msg.edit_text(text,disable_web_page_preview=True)
    except: pass
def save():
    try:
        ct={k:v for k,v in cache.items() if time.time()-v.get("t",0)<CACHE_TTL}
        with open(CACHE_FILE,"w") as f: json.dump(ct,f)
    except: pass
def load():
    global cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                ct=json.load(f); now=time.time()
                cache={k:v for k,v in ct.items() if now-v.get("t",0)<CACHE_TTL}
    except: pass

async def proc(url,msg,client,idx=1,total=1):
    Path(TEMP_DIR).mkdir(parents=True,exist_ok=True)
    pf=plat(url)
    st=await msg.reply_text(f"{E['dl']} **Downloading** [{idx}/{total}]\n{E['link']} `{url[:50]}...`\n{E['web']} {pf}\n{bar(0)} 0%\n{E['cloud']} Render Cloud")
    try:
        if url in cache:
            c=cache[url]
            if time.time()-c.get("t",0)<CACHE_TTL:
                d=c.get("d",{})
                if d.get("fp") and os.path.exists(d["fp"]):
                    stats["ch"]+=1; fp=d["fp"]; fsv=os.path.getsize(fp); ti=d.get("ti","Cached")[:200]; du=d.get("du",0); up=d.get("up","Unknown")
                    await se(st,f"{E['up']} **Uploading...** [{idx}/{total}]\n{E['vid']} {ti[:80]}\n{E['size']} {fs(fsv)}\n{E['cloud']} Render → Telegram")
                    cap=f"{E['vid']} **{ti}**\n{E['clock']} {ft(du)} | {E['size']} {fs(fsv)}\n{E['user']} {up} | {E['web']} {pf}\n{E['cloud']} Cloud Bot | {E['phone']} Zero Data"
                    try: await client.send_video(chat_id=msg.chat.id,video=fp,caption=cap,supports_streaming=True,duration=du if du>0 else None,reply_to_message_id=msg.id)
                    except FloodWait as e: await asyncio.sleep(e.value+2); await client.send_video(chat_id=msg.chat.id,video=fp,caption=cap,supports_streaming=True,duration=du if du>0 else None,reply_to_message_id=msg.id)
                    await st.delete(); stats["p"]+=1; stats["ok"]+=1; stats["mb"]+=fsv/1048576
                    log(f"{E['ok']} Cached: {ti[:60]} ({fs(fsv)})"); return True
                else: del cache[url]
        stats["cm"]+=1
        yop={'outtmpl':f'{TEMP_DIR}/%(id)s.%(ext)s','format':'best[height<=720]/best[height<=480]/best','quiet':True,'no_warnings':True,'ignoreerrors':True,'max_filesize':MAX_MB*1024*1024,'noplaylist':True,'playlist_items':'1','retries':3,'fragment_retries':3,'socket_timeout':120,'nocheckcertificate':True}
        lp=[0]; _fp=[""]
        def ph(d):
            if d['status']=='downloading':
                tb=d.get('total_bytes') or d.get('total_bytes_estimate',0); dl=d.get('downloaded_bytes',0)
                if tb>0:
                    pct=(dl/tb)*100; spd=d.get('speed',0)
                    if pct-lp[0]>=15 or pct>=100:
                        lp[0]=pct; eta=""
                        if spd>0 and tb>dl: eta=f"\n{E['clock']} ETA: {ft(int((tb-dl)/spd))}"
                        asyncio.create_task(se(st,f"{E['dl']} **Downloading** [{idx}/{total}]\n{E['vid']} {d.get('filename','')[:40]}\n{bar(pct)} **{pct:.0f}%**\n{E['size']} {fs(dl)} / {fs(tb)}\n{E['speed']} {fs(int(spd))}/s{eta}\n{E['cloud']} Render Cloud"))
            elif d['status']=='finished': _fp[0]=d.get('filename','')
        yop['progress_hooks']=[ph]
        loop=asyncio.get_event_loop()
        def sd():
            with yt_dlp.YoutubeDL(yop) as ydl:
                info=ydl.extract_info(url,download=True)
                if not info: return None
                if 'entries' in info:
                    entries=[e for e in info['entries'] if e]
                    if not entries: return None
                    info=entries[0]
                fp=_fp[0] or ydl.prepare_filename(info)
                if not os.path.exists(fp):
                    base=fp.rsplit('.',1)[0]
                    for ext in ['.mp4','.webm','.mkv','.mov']:
                        if os.path.exists(base+ext): fp=base+ext; break
                if not os.path.exists(fp): return None
                return {'fp':fp,'ti':info.get('title','Video')[:200],'du':info.get('duration',0),'up':info.get('uploader','Unknown'),'fs':os.path.getsize(fp)}
        result=await loop.run_in_executor(None,sd)
        if not result or not os.path.exists(result.get('fp','')):
            await se(st,f"{E['no']} **Failed!** [{idx}/{total}]\n{E['link']} `{url[:80]}`\n{E['bulb']} Link may be private/expired.")
            stats["no"]+=1; stats["p"]+=1; return False
        fp=result['fp']; fsv=result['fs']; ti=result['ti']; du=result['du']; up=result['up']
        cache[url]={"t":time.time(),"d":{"fp":fp,"ti":ti,"du":du,"up":up,"fs":fsv}}
        await se(st,f"{E['up']} **Uploading...** [{idx}/{total}]\n{E['vid']} {ti[:80]}\n{E['size']} {fs(fsv)}\n{E['cloud']} Render → Telegram")
        cap=f"{E['vid']} **{ti}**\n{E['clock']} {ft(du)} | {E['size']} {fs(fsv)}\n{E['user']} {up} | {E['web']} {pf}\n{E['cloud']} Cloud Bot | {E['phone']} Zero Data"
        try: await client.send_video(chat_id=msg.chat.id,video=fp,caption=cap,supports_streaming=True,duration=du if du>0 else None,reply_to_message_id=msg.id)
        except FloodWait as e: await asyncio.sleep(e.value+2); await client.send_video(chat_id=msg.chat.id,video=fp,caption=cap,supports_streaming=True,duration=du if du>0 else None,reply_to_message_id=msg.id)
        await st.delete(); stats["p"]+=1; stats["ok"]+=1; stats["mb"]+=fsv/1048576
        log(f"{E['ok']} Sent: {ti[:60]} ({fs(fsv)})"); return True
    except Exception as e:
        em=str(e)[:200]; log(f"{E['no']} Error: {em}")
        await se(st,f"{E['no']} **Error!** [{idx}/{total}]\n{E['link']} `{url[:80]}`\n`{em[:150]}`")
        stats["no"]+=1; stats["p"]+=1; return False

app=Client("CBv12",api_id=API_ID,api_hash=API_HASH,bot_token=BOT_TOKEN,workers=16)

@app.on_message(filters.command("start"))
async def start_cmd(c,m):
    u=m.from_user; stats["u"][str(u.id)]=u.first_name
    txt=f"""{E['fire']}{E['fire']}{E['fire']} **CLOUD VIDEO BOT** {E['fire']}{E['fire']}{E['fire']}
{E['rocket']} **Zero Data on Your Phone!**
{E['crown']} Welcome **{u.first_name}**!
{E['cloud']} **How:** 📱→Link→☁️Cloud→📥DL→📤UL→📱Video
{E['shield']} **Phone: ZERO Data | ZERO Storage**
{E['star']} /help /stats /batch /cache
{E['fire']} **Send video link now!**"""
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['star']} Help",callback_data="help"),InlineKeyboardButton(f"{E['stats']} Stats",callback_data="stats")],[InlineKeyboardButton(f"{E['web']} Platforms",callback_data="plats"),InlineKeyboardButton(f"{E['cloud']} How?",callback_data="how")]])
    await m.reply_text(txt,reply_markup=kb,disable_web_page_preview=True)

@app.on_message(filters.command("help"))
async def help_cmd(c,m):
    await m.reply_text(f"""{E['star']} **HELP**
{E['cloud']} 📱→Link→☁️Cloud→📥DL→📤UL→📱Video
{E['ok']} Phone: ZERO Data | ZERO Storage
{E['web']} YT/IG/FB/X/TT/Rumble/+1000
{E['link']} Bulk: 50+ Links एक साथ
{E['disk']} Cache: Repeat = Instant (1hr)
{E['star']} /stats /batch /cache /report""")

@app.on_message(filters.command("stats"))
async def stats_cmd(c,m):
    s=stats; t=max(1,s['p']); r=(s['ok']/t)*100; st_t=datetime.fromisoformat(s['st']); up=datetime.now()-st_t
    h,rem=divmod(int(up.total_seconds()),3600); mi,se=divmod(rem,60)
    await m.reply_text(f"""{E['stats']} **STATS**
{E['clock']} Uptime: `{h}h {mi}m {se}s` | Users: `{len(s['u'])}`
{E['dl']} Processed: `{s['p']}` | {E['ok']} Success: `{s['ok']}` | {E['no']} Failed: `{s['no']}`
{E['star']} Rate: `{r:.1f}%` | {E['size']} Data: `{fs(int(s['mb']*1048576))}`
{E['disk']} Cache: `{len(cache)}` URLs | Hit Rate: `{(s['ch']/max(1,s['ch']+s['cm'])*100):.1f}%`
{E['cloud']} Server: Render.com""")

@app.on_message(filters.command("batch"))
async def batch_cmd(c,m):
    await m.reply_text(f"{E['fire']} **BULK MODE**\n{E['link']} 50+ Links एक Message में!\n{E['dl']} 1️⃣Paste 2️⃣Send 3️⃣Wait 4️⃣Videos Arrive\n{E['cloud']} 100% Cloud | {E['phone']} ZERO Data")

@app.on_message(filters.command("cache"))
async def cache_cmd(c,m):
    await m.reply_text(f"{E['disk']} **Cache:** `{len(cache)}` URLs | TTL: `{CACHE_TTL//60}min`\n{E['speed']} Hit Rate: `{(stats['ch']/max(1,stats['ch']+stats['cm'])*100):.1f}%`")

@app.on_message(filters.command("report"))
async def report_cmd(c,m):
    await m.reply_text(f"{E['info']} **Report Issue**\nSend: Link + Error + Time\nOr contact admin",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['user']} Admin",url=f"tg://user?id={OWNER_ID}")]]))

@app.on_message(filters.text&~filters.command(["start","help","stats","batch","cache","report"]))
async def handle(c,m):
    u=m.from_user; uid=str(u.id)
    if uid not in stats["u"]: stats["u"][uid]=u.first_name
    us=urls(m.text or m.caption or "")
    if not us:
        await m.reply_text(f"{E['no']} **No Links!**\nSend YouTube/IG/FB/X/TikTok/Rumble links.\n/batch for Bulk Guide!",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['web']} Sites",callback_data="plats"),InlineKeyboardButton(f"{E['bulb']} How?",callback_data="how")]]))
        return
    tl=len(us); pls=list(set(plat(u) for u in us))
    hd=await m.reply_text(f"{E['fire']} **{tl} LINKS** {E['fire']}\n{E['link']} Links: **{tl}**\n{E['web']} {', '.join(pls[:5])}{'...' if len(pls)>5 else ''}\n{E['cloud']} Render Cloud | {E['phone']} Phone: ZERO\n{E['wait']} Starting...")
    ok,fail=0,0
    for i,u in enumerate(us,1):
        r=await proc(u,m,c,i,tl)
        if r: ok+=1
        else: fail+=1
        if i<tl: await asyncio.sleep(FLOOD)
        if i%10==0: save()
    rt=(ok/max(1,tl))*100
    try: await hd.edit_text(f"{E['ok']} **DONE!** {ok}/{tl} ({rt:.0f}%)\n{E['cloud']} Cloud | {E['phone']} Phone Data: ~{tl*0.5:.0f}KB | {E['disk']} Storage: 0MB\n{E['fire']} /stats | /help",disable_web_page_preview=True)
    except: await m.reply_text(f"{E['ok']} **DONE!** {ok}/{tl} ({rt:.0f}%)\n{E['fire']} /stats | /help")

@app.on_callback_query()
async def cb_h(c,cb):
    d=cb.data
    if d=="help": await help_cmd(c,cb.message)
    elif d=="stats": await stats_cmd(c,cb.message)
    elif d=="how": await cb.message.reply_text(f"{E['bulb']} **HOW**\n1️⃣You→Link\n2️⃣Cloud→Download\n3️⃣Cloud→Upload\n4️⃣You→Video\n{E['phone']} Phone: 0 Data, 0 Storage")
    elif d=="plats": await cb.message.reply_text(f"{E['web']} **SITES**\n{E['ok']} YT/IG/FB/X/TT/Rumble/Vimeo/Dailymotion/Reddit/CDN/+1000")
    try: await cb.answer()
    except: pass

async def cleanup():
    while True:
        await asyncio.sleep(300)
        try:
            now=time.time()
            exp=[k for k,v in cache.items() if now-v.get("t",0)>CACHE_TTL]
            for k in exp:
                fp=cache[k].get("d",{}).get("fp","")
                if fp and os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass
                del cache[k]
            if exp: log(f"Cleanup: {len(exp)} expired")
            save()
        except: pass

def main():
    Path(TEMP_DIR).mkdir(parents=True,exist_ok=True)
    load()
    print(f"\n{E['cloud']} CLOUD BOT STARTING {E['cloud']}\n")
    log(f"{E['rocket']} Bot online — Render Cloud")
    signal.signal(signal.SIGINT,lambda s,f:(save(),sys.exit(0)))
    signal.signal(signal.SIGTERM,lambda s,f:(save(),sys.exit(0)))
    try: asyncio.run(_run())
    except KeyboardInterrupt: pass
    finally: save()

async def _run():
    await app.start()
    me=await app.get_me()
    log(f"{E['ok']} @{me.username} ready!")
    if OWNER_ID:
        try: await app.send_message(OWNER_ID,f"{E['ok']} **Bot Started!**\nRender Cloud")
        except: pass
    ct=asyncio.create_task(cleanup())
    try: await asyncio.Event().wait()
    except: pass
    finally: ct.cancel(); await app.stop(); save()

if __name__=="__main__": main()
