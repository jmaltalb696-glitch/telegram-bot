import os, time, json, shutil, requests, subprocess
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CONFIG = json.load(open('config.json', 'r', encoding='utf-8'))
BOT_TOKEN = CONFIG['bot_token']
OWNER_CHAT_ID = CONFIG['owner_chat_id']
RESTAURANT_NAME = CONFIG['restaurant_name']
SAVE_PATH = r'C:\الفواتير'
QUEUE_FILE = 'queue.json'
SPOOL_FOLDER = r'C:\Windows\System32\spool\PRINTERS'
os.makedirs(SAVE_PATH, exist_ok=True)

def load_queue():
    return json.load(open(QUEUE_FILE, 'r')) if os.path.exists(QUEUE_FILE) else []

def save_queue(q):
    json.dump(q, open(QUEUE_FILE, 'w'))

def spl_to_pdf(spl_path, pdf_path):
    try:
        subprocess.run(['spl2pdf.exe', spl_path, pdf_path], check=True, capture_output=True, timeout=15)
        return os.path.exists(pdf_path)
    except: return False

def send_to_telegram(file_path):
    if CONFIG['status']!= 'active': return False
    try:
        with open(file_path, 'rb') as f:
            r = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument',
                files={'document': f},
                data={'chat_id': OWNER_CHAT_ID, 'caption': f'{RESTAURANT_NAME} - {datetime.now().strftime("%H:%M")}'},
                timeout=30)
            return r.status_code == 200
    except: return False

def update_bot_amount(amount=0):
    try:
        requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            params={'chat_id': OWNER_CHAT_ID, 'text': f'/update {RESTAURANT_NAME} {amount}'}, timeout=5)
    except: pass

def process_queue():
    q = load_queue()
    new_q = []
    for f in q:
        if not send_to_telegram(f): new_q.append(f)
    save_queue(new_q)

class SpoolHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.src_path.lower().endswith('.spl'): return
        time.sleep(3)
        pdf_name = f"{RESTAURANT_NAME}_{os.environ.get('COMPUTERNAME')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(SAVE_PATH, pdf_name)
        if spl_to_pdf(event.src_path, pdf_path):
            q = load_queue(); q.append(pdf_path); save_queue(q)
            process_queue()
            update_bot_amount(0)
            try: os.remove(event.src_path)
            except: pass

if __name__ == "__main__":
    process_queue()
    obs = Observer()
    obs.schedule(SpoolHandler(), path=SPOOL_FOLDER, recursive=False)
    obs.start()
    try:
        while True: time.sleep(60); process_queue()
    except KeyboardInterrupt: obs.stop()
    obs.join()
