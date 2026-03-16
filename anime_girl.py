import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# -----------------------------
# Функция нормализации
# -----------------------------
import numpy as np
plt.ion()
def normalize(arr, method="linear", gamma=0.4):
    """
    Приводим значения массива к диапазону 0..1 с разными методами сглаживания.
    
    method:
        "linear"   — обычная нормализация
        "sqrt"     — сглаживает большие пики
        "tanh"     — мягкая компрессия
        "lift_min" — поднимает минимумы к ~0.5, высокие значения меняются мягко
    
    gamma — параметр кривизны для lift_min
    """
    
    arr = np.array(arr, dtype=float)
    arr_min, arr_max = arr.min(), arr.max()
    
    if arr_max - arr_min == 0:
        return np.zeros_like(arr)

    # базовая нормализация
    norm = (arr - arr_min) / (arr_max - arr_min)

    if method == "sqrt":
        norm = np.sqrt(norm)

    elif method == "tanh":
        norm = np.tanh(norm * 2)
        norm = (norm - norm.min()) / (norm.max() - norm.min())

    elif method == "lift_min":
        norm = norm ** gamma      # усиливаем маленькие значения
        norm = 0.5 + 0.5 * norm   # сдвигаем диапазон к 0.5..1
        norm = np.clip(norm, 0, 1)

    return norm

# -----------------------------
# 1. Загрузка изображения
# -----------------------------
img = Image.open("anime.jpeg").convert("L")  # grayscale
img = img.resize((200, 200))                # уменьшаем для скорости

heightmap = np.array(img) / 255.0
print(heightmap.shape)
heightmap = normalize(heightmap, method="lift_min")  # сглаживаем перепады

# -----------------------------
# 2. Генерация простого шума
# -----------------------------
noise = np.random.rand(*heightmap.shape) * 0.3

# сглаживание шума
for _ in range(3):
    noise = (
        np.roll(noise, 1, axis=0) +
        np.roll(noise, -1, axis=0) +
        np.roll(noise, 1, axis=1) +
        np.roll(noise, -1, axis=1) +
        noise
    ) / 5

noise = normalize(noise, method="lift_min")  # мягкая нормализация шума

# -----------------------------
# 3. Итоговый terrain
# -----------------------------
terrain = heightmap * 0.7 + noise * 0.3
terrain = normalize(terrain, method="lift_min")  # окончательная нормализация
print(terrain)
# -----------------------------
# 4. Визуализация
# -----------------------------


from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import ListedColormap


def generate_world(heightmap):

    h = np.array(heightmap)

    world = np.zeros_like(h)

    # уровни высоты
    water = h < 0.85
    beach = (h >= 0.85) & (h < 0.88)
    grass = (h >= 0.88) & (h < 0.93)
    forest = (h >= 0.93) & (h < 0.96)
    mountain = (h >= 0.96) & (h < 0.98)
    snow = h >= 0.98

    world[water] = 0
    world[beach] = 1
    world[grass] = 2
    world[forest] = 3
    world[mountain] = 4
    world[snow] = 5

    return world

def gen_terrain():
    # Создаём общую фигуру
    fig = plt.figure(figsize=(15, 10))

    # 1. Исходное изображение (2D)
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.imshow(img, cmap="gray")
    ax1.set_title("Исходная картинка")
    ax1.axis("off")

    # 2. Карта высот
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.imshow(heightmap, cmap="terrain")
    ax2.set_title("Карта высот")
    ax2.axis("off")

    # 3. Шум
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.imshow(noise, cmap="gray")
    ax3.set_title("Сгенерированный шум")
    ax3.axis("off")

    # 4. Итоговый terrain (2D)
    ax4 = fig.add_subplot(2, 3, 4)
    ax4.imshow(terrain, cmap="terrain")
    ax4.set_title("Итоговый terrain")
    ax4.axis("off")

    # 5. 3D поверхность
    ax5 = fig.add_subplot(2, 3, 5, projection='3d')
    x = np.arange(terrain.shape[0])
    y = np.arange(terrain.shape[1])
    x, y = np.meshgrid(x, y)
    ax5.plot_surface(x, y, terrain, cmap="terrain", linewidth=0, antialiased=False)
    ax5.set_title("3D Ландшафт")

    # 6. Сгенерированный мир
    ax6 = fig.add_subplot(2, 3, 6)
    world = generate_world(terrain)
    colors = ["#1f4aa8", "#f2d16b", "#6dbf4b", "#2e7d32", "#8d6e63", "#ffffff"]
    cmap = ListedColormap(colors)
    ax6.imshow(world, cmap=cmap)
    ax6.set_title("Сгенерированный мир")
    ax6.axis("off")

    plt.tight_layout()  # чтобы подписи не налезали друг на друга
    plt.show(block=False)
    plt.pause(2)
    return terrain

#gen_terrain()