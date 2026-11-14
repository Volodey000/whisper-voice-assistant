# -*- coding: utf-8 -*-
"""
vocabulary.py: Управление пользовательским словарем, подсказками горячих слов (Hotwords)
и словарем точных автозамен для Faster-Whisper.
"""

import re
from config import config

DEFAULT_HOTWORDS = "Kubernetes, PostgreSQL, Docker, FastAPI, Python, PyQt6, Faster-Whisper, Antigravity, Figma, GitHub, Битрикс24"

DEFAULT_REPLACEMENTS = {
    "кубер": "Kubernetes",
    "кубернетес": "Kubernetes",
    "постгрес": "PostgreSQL",
    "постгрис": "PostgreSQL",
    "фастапи": "FastAPI",
    "гпт": "GPT-4o",
    "питон": "Python",
    "пайтон": "Python",
    "докер": "Docker",
    "вискарь": "Whisper"
}

def get_hotwords_list() -> list[str]:
    """Возвращает список горячих слов из конфигурации."""
    raw = config.get("hotwords", DEFAULT_HOTWORDS)
    if isinstance(raw, list):
        return [w.strip() for w in raw if w.strip()]
    return [w.strip() for w in re.split(r'[,;\n]+', str(raw)) if w.strip()]

def get_hotwords_prompt() -> tuple[str, str]:
    """
    Формирует строку hotwords и строку initial_prompt для передачи в Faster-Whisper.
    """
    words = get_hotwords_list()
    if not words:
        return "", ""
    hotwords_str = " ".join(words)
    prompt_str = f"Словарь терминов, названий и имен: {', '.join(words)}."
    return hotwords_str, prompt_str

def apply_custom_vocabulary(text: str) -> str:
    """
    Применяет пользовательские автозамены и выравнивает регистр горячих слов.
    """
    if not text or not text.strip():
        return ""

    if not config.get("custom_vocabulary_enabled", True):
        return text

    res = text
    replacements = config.get("replacements", DEFAULT_REPLACEMENTS)
    if isinstance(replacements, dict):
        # 1. Применяем автозамены (сначала более длинные фразы, чтобы избежать частичных наложений)
        sorted_replacements = sorted(replacements.items(), key=lambda x: len(str(x[0])), reverse=True)
        for src, tgt in sorted_replacements:
            s = str(src).strip()
            t = str(tgt).strip()
            if not s or not t:
                continue
            pat = rf'(?<!\w){re.escape(s)}(?!\w)'
            res = re.sub(pat, t, res, flags=re.IGNORECASE)

    # 2. Выравнивание точного регистра символов для горячих слов (Hotwords exact casing)
    hotwords = get_hotwords_list()
    sorted_hw = sorted(hotwords, key=len, reverse=True)
    for hw in sorted_hw:
        if not hw:
            continue
        pat = rf'(?<!\w){re.escape(hw)}(?!\w)'
        res = re.sub(pat, hw, res, flags=re.IGNORECASE)

    return res
