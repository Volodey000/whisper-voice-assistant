import os
import json
import time
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
MAX_HISTORY_ENTRIES = 200

class HistoryManager:
    def __init__(self):
        self.entries = []
        self.load()

    def load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception as e:
                print(f"[History] Ошибка чтения {HISTORY_FILE}: {e}")
                self.entries = []

    def save(self):
        try:
            tmp_file = HISTORY_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, HISTORY_FILE)
        except Exception as e:
            print(f"[History] Ошибка сохранения {HISTORY_FILE}: {e}")

    def add_entry(self, text: str, language: str = "ru", duration: float = 0.0):
        if not text or not text.strip():
            return
        entry = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": text.strip(),
            "language": language.upper(),
            "duration": round(duration, 1)
        }
        self.entries.insert(0, entry)
        if len(self.entries) > MAX_HISTORY_ENTRIES:
            self.entries = self.entries[:MAX_HISTORY_ENTRIES]
        self.save()

    def get_all(self):
        return list(self.entries)

    def delete_entry(self, entry_id: int):
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        self.save()

    def clear(self):
        self.entries = []
        self.save()

history = HistoryManager()
