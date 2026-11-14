import os
import sys

def setup_cuda_env():
    """
    Обеспечивает доступ CTranslate2 к библиотекам CUDA (cuBLAS, cuDNN),
    установленным вместе с PyTorch в Windows.
    """
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
