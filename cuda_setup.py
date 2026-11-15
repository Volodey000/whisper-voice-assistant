import os
import sys
import ctypes
from ctypes import wintypes

def preload_system_msvc():
    """
    Принудительно загружает системные библиотеки Microsoft Visual C++ Runtime (14.4x/14.5x)
    из C:\Windows\System32 ДО импорта PyQt6.
    Это предотвращает подгрузку устаревшей библиотеки PyQt6\Qt6\bin\msvcp140.dll (версии 14.26 от 2020 г.),
    которая вызывает сбой (0xc0000005) в многопоточных вычислениях CTranslate2 и PyTorch.
    """
    if sys.platform != "win32":
        return

    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS", "4")
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    kernel32 = ctypes.windll.kernel32
    kernel32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]
    kernel32.LoadLibraryW.restype = wintypes.HMODULE

    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    for dll_name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll"):
        dll_path = os.path.join(system32, dll_name)
        if os.path.exists(dll_path):
            try:
                kernel32.LoadLibraryW(dll_path)
            except Exception:
                pass

def setup_cuda_env():
    """
    Обеспечивает доступ CTranslate2 к библиотекам CUDA (cuBLAS, cuDNN),
    установленным вместе с PyTorch в Windows, и загружает системный MSVC runtime.
    """
    preload_system_msvc()
    try:
        import torch
        torch_lib = os.path.join(os.path.dirname(torch.__file__), 'lib')
        if os.path.exists(torch_lib):
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(torch_lib)
                except Exception:
                    pass
            os.environ['PATH'] = torch_lib + os.pathsep + os.environ.get('PATH', '')
    except Exception as e:
        print(f"[CUDA Setup] Замечание: {e}")

# Выполняем настройку при импорте модуля
setup_cuda_env()
