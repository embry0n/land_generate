import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random

def create_atlas(size=1024):
    atlas = Image.new('RGB', (size, size))
    tile_w = size // 6
    tile_h = size

    # Базовые цвета (R,G,B)
    base_colors = [
        (30, 74, 168),   # вода
        (242, 209, 107), # пляж
        (109, 191, 75),  # трава
        (46, 125, 50),   # лес
        (141, 110, 99),  # горы
        (255, 255, 255)  # снег
    ]

    for i, base in enumerate(base_colors):
        # Создаём плитку
        tile = Image.new('RGB', (tile_w, tile_h), base)
        pixels = np.array(tile, dtype=np.uint8)

        # Добавляем шум (случайные отклонения)
        noise = np.random.randint(-15, 15, pixels.shape, dtype=np.int16)
        noisy = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        tile = Image.fromarray(noisy)

        # Можно добавить горизонтальный градиент (осветление к одному краю)
        grad = np.linspace(0.8, 1.2, tile_w)  # коэффициент для каждого столбца
        grad = grad.reshape(1, -1, 1)         # (1, w, 1) для broadcasting
        arr = np.array(tile, dtype=float)
        arr = arr * grad
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        tile = Image.fromarray(arr)

        # Применить небольшое размытие для сглаживания
        tile = tile.filter(ImageFilter.GaussianBlur(radius=1))

        atlas.paste(tile, (i * tile_w, 0))

    return atlas, np.array(atlas)

def load_texture_from_pil(img):
    """Загружает PIL Image в OpenGL текстуру."""
    from OpenGL.GL import glGenTextures, glBindTexture, GL_TEXTURE_2D, GL_RGB, GL_UNSIGNED_BYTE, glTexImage2D, glTexParameteri, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR
    img_data = np.array(img.convert('RGB'), dtype=np.uint8)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return texture_id