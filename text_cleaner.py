# -*- coding: utf-8 -*-
"""
text_cleaner.py: Интеллектуальная очистка надиктованного и переведенного текста.
Удаляет слова-паразиты, звуки колебания (э-э-э, ммм, uh, um), заикания и повторы слов.
"""

import re

PROTECTED_HYPHEN_WORDS = {
    "чуть-чуть", "еле-еле", "точь-в-точь", "волей-неволей",
    "мало-помалу", "давным-давно", "перво-наперво", "крест-накрест"
}

def clean_speech_text(text: str, language: str = "ru") -> str:
    """
    Интеллектуальная очистка надиктованного текста от слов-паразитов,
    междометий (э-э-э, ммм, uh, um) и заиканий/повторов одного и того же слова подряд.
    Нормализует пунктуацию, пробелы и регистр первой буквы.
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()

    # 1. Вокальные паузы и звуки колебания (э-э-э, ммм, а-а-а, uh, um, etc.)
    hesitation_patterns = [
        # Русские звуки
        r'\b[эе][\-\s]*[эе]+(?:\-[эе]+)*\b',  # эээ, э-э, э-э-э
        r'\b[аa][\-\s]*[аa]+(?:\-[аa]+)*\b',  # ааа, а-а, а-а-а
        r'\b[мm]{2,}\b',                      # ммм, мм
        r'\b[хx][мm]+\b',                     # хм, хмм, хммм
        r'\b[гg][мm]+\b',                     # гм, гмм
        r'\b[уy][\-\s]*[уy]+(?:\-[уy]+)*\b',  # ууу, у-у
        r'\b[оo][\-\s]*[оo]+(?:\-[оo]+)*\b',  # ооо, о-о
        # Английские звуки
        r'\buh+\b',                           # uh, uhh
        r'\bum+\b',                           # um, umm
        r'\buhm+\b',                          # uhm
        r'\ber+\b',                           # er, err
        r'\bah+\b',                           # ah, ahh
    ]
    for pat in hesitation_patterns:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)

    # 2. Слова-паразиты и речевые сорняки
    filler_phrases = [
        r'\bкак бы\b',
        r'\bтак сказать\b',
        r'\bв общем-то\b',
        r'\bв общем\b',
        r'\bсобственно говоря\b',
        r'\bну вот\b',
        r'\bтипа того\b',
        r'\bкороче говоря\b',
        r'\byou know\b',
        r'\bkind of\b',
        r'\bsort of\b',
    ]
    for fp in filler_phrases:
        cleaned = re.sub(fp, '', cleaned, flags=re.IGNORECASE)

    # Удаление паразитного "Ну," / "Ну " в начале фразы или после знаков препинания
    cleaned = re.sub(r'^(?:ну|nu)(?:,\s*|\s+)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'([.!?]\s*)(?:ну|nu)(?:,\s*|\s+)', r'\1', cleaned, flags=re.IGNORECASE)

    # Предварительная зачистка знаков препинания перед поиском повторов
    cleaned = re.sub(r'\s+([,.:;?!])', r'\1', cleaned)
    cleaned = re.sub(r',(?:\s*,)+', ',', cleaned)
    cleaned = re.sub(r'^[,;:\s]+', '', cleaned)

    # 3. Удаление заиканий и случайных повторов одного и того же слова подряд ("я я", "the the", "мы, мы")
    def _remove_dup_word(match):
        w = match.group(1)
        if f"{w.lower()}-{w.lower()}" in PROTECTED_HYPHEN_WORDS:
            return match.group(0)
        return w

    # Двойной проход для устранения как одиночных, так и многократных повторов
    cleaned = re.sub(r'\b([а-яёa-z]+)(?:,\s*|\s+)\1\b', _remove_dup_word, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b([а-яёa-z]+)(?:,\s*|\s+)\1\b', _remove_dup_word, cleaned, flags=re.IGNORECASE)

    # 4. Нормализация пунктуации и пробелов
    cleaned = re.sub(r'\s+([,.:;?!])', r'\1', cleaned)
    cleaned = re.sub(r',(?:\s*,)+', ',', cleaned)
    cleaned = re.sub(r',\s*([.!?])', r'\1', cleaned)
    cleaned = re.sub(r'^[,;:\s]+', '', cleaned)
    cleaned = re.sub(r'([.!?]\s*)[,;:]\s*', r'\1', cleaned)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

    # 5. Восстановление заглавных букв после удаления начального слова
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    # Заглавные буквы в начале новых предложений: ". слово" -> ". Слово"
    cleaned = re.sub(r'([.!?]\s+)([а-яёa-z])', lambda m: m.group(1) + m.group(2).upper(), cleaned)

    # Защита: если фильтрация вычистила фразу полностью (например состояла из "Ну, эээ"),
    # возвращаем исходный текст, чтобы не потерять надиктованное сообщение
    if not cleaned.strip() and text.strip():
        return text.strip()

    return cleaned.strip()
