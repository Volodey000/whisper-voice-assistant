import os
import sys

def detect_hardware():
    """
    Определяет доступное оборудование (GPU / CPU) и подбирает
    оптимальные настройки для ПК с видеокартой или ноутбука.
    """
    has_cuda = False
    gpu_name = ""
    vram_gb = 0.0

    try:
        import torch
        if torch.cuda.is_available():
            has_cuda = True
            gpu_name = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = vram_bytes / (1024 ** 3)
    except Exception:
        has_cuda = False

    cpu_threads = os.cpu_count() or 4

    if has_cuda and vram_gb >= 2.0:
        recommended_device = "cuda"
        recommended_compute_type = "float16"
        # Если 6GB+ видеопамяти — ставим крупную турбо-модель, иначе small
        recommended_model = "large-v3-turbo" if vram_gb >= 5.5 else "small"
        badge_text = f"🟢 {gpu_name} ({vram_gb:.0f} ГБ) • CUDA Ускорение"
        mode_desc = "Режим ПК с дискретной видеокартой NVIDIA"
    else:
        # Режим ноутбука без видеокарты
        recommended_device = "cpu"
        recommended_compute_type = "int8" # Квантование INT8: в 3-4 раза быстрее и в 4 раза меньше RAM
        recommended_model = "small" if cpu_threads >= 4 else "base"
        badge_text = f"💻 Режим ноутбука: CPU ({cpu_threads} потоков) • INT8"
        mode_desc = "Режим ноутбука / офисного ПК (процессор CPU с INT8 оптимизацией)"

    return {
        "has_cuda": has_cuda,
        "gpu_name": gpu_name,
        "vram_gb": round(vram_gb, 1),
        "cpu_threads": cpu_threads,
        "recommended_device": recommended_device,
        "recommended_compute_type": recommended_compute_type,
        "recommended_model": recommended_model,
        "badge_text": badge_text,
        "mode_desc": mode_desc
    }

def resolve_settings(config_device: str, config_model: str, config_compute_type: str = "auto"):
    """
    Разрешает параметры 'auto' в конкретные настройки под текущее железо.
    """
    hw = detect_hardware()

    # Разрешение устройства
    if not config_device or config_device == "auto":
        resolved_device = hw["recommended_device"]
    elif config_device == "cuda" and not hw["has_cuda"]:
        # Защита от сбоя: если в конфиге был указан cuda, но запущен на ноутбуке без GPU
        resolved_device = "cpu"
    else:
        resolved_device = config_device

    # Разрешение типа вычислений
    if not config_compute_type or config_compute_type == "auto":
        resolved_compute_type = "float16" if resolved_device == "cuda" else "int8"
    else:
        resolved_compute_type = config_compute_type

    # Защита от сбоя: CTranslate2 не поддерживает float16 на процессоре (CPU)
    if resolved_device == "cpu" and resolved_compute_type == "float16":
        resolved_compute_type = "int8"

    # Разрешение модели
    if not config_model or config_model == "auto":
        resolved_model = hw["recommended_model"]
    else:
        resolved_model = config_model

    return {
        "device": resolved_device,
        "compute_type": resolved_compute_type,
        "model_name": resolved_model,
        "hardware": hw
    }
