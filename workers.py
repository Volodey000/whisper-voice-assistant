import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from transcriber import whisper_engine
from config import config

class LiveTranscriptionWorker(QThread):
    finished_signal = pyqtSignal(str, str, float, str)  # text, language, duration, task
    error_signal = pyqtSignal(str)

    def __init__(self, audio_data: np.ndarray, duration: float, language: str = None, task: str = "transcribe"):
        super().__init__()
        self.audio_data = audio_data
        self.duration = duration
        self.language = language
        self.task = task

    def run(self):
        try:
            text, detected_lang, prob = whisper_engine.transcribe_audio(
                self.audio_data, 
                language=self.language,
                task=self.task
            )
            # Очистка от слов-паразитов, междометий и заиканий
            if config.get("clean_fillers", True):
                from text_cleaner import clean_speech_text
                eff_lang = "en" if self.task == "translate" else detected_lang
                text = clean_speech_text(text, language=eff_lang)

            self.finished_signal.emit(text, detected_lang, self.duration, self.task)
        except Exception as e:
            self.error_signal.emit(str(e))

class FileTranscriptionWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str, list, str)
    error_signal = pyqtSignal(str)

    def __init__(self, file_path: str, language: str = None):
        super().__init__()
        self.file_path = file_path
        self.language = language

    def run(self):
        try:
            def on_progress(percent, text):
                self.progress_signal.emit(percent, text)

            full_text, segments, lang = whisper_engine.transcribe_file(
                self.file_path,
                language=self.language,
                progress_callback=on_progress
            )
            self.finished_signal.emit(full_text, segments, lang)
        except Exception as e:
            self.error_signal.emit(str(e))
