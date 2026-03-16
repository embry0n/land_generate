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
fig, ax = plt.subplots(1,4, figsize=(18,5))

ax[0].imshow(img, cmap="gray")
ax[0].set_title("Исходная картинка")

ax[1].imshow(heightmap, cmap="terrain")
ax[1].set_title("Карта высот (из картинки)")

ax[2].imshow(noise, cmap="gray")
ax[2].set_title("Сгенерированный шум")

ax[3].imshow(terrain, cmap="terrain")
ax[3].set_title("Итоговый terrain")

for a in ax:
    a.axis("off")


# 3D поверхность
from mpl_toolkits.mplot3d import Axes3D

x = np.arange(terrain.shape[0])
y = np.arange(terrain.shape[1])
x, y = np.meshgrid(x, y)

fig2 = plt.figure(figsize=(10,7))
ax2 = fig2.add_subplot(111, projection='3d')

ax2.plot_surface(
    x, y, terrain,
    cmap="terrain",
    linewidth=0,
    antialiased=False
)

ax2.set_title("3D Ландшафт из картинки")

plt.show(block=False)
plt.pause(0.001)




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


def draw_world(world):

    colors = [
        "#1f4aa8",  # вода
        "#f2d16b",  # пляж
        "#6dbf4b",  # равнина
        "#2e7d32",  # лес
        "#8d6e63",  # горы
        "#ffffff"   # снег
    ]

    cmap = ListedColormap(colors)

    plt.figure(figsize=(10,10))
    plt.imshow(world, cmap=cmap)
    plt.title("Сгенерированный мир")
    plt.axis("off")
    plt.show(block=False)
    plt.pause(0.001)


# -----------------------------
# пример использования
# -----------------------------
def gen_terrain():
    world = generate_world(terrain)

    draw_world(world)
    return terrain