import numpy as np

def get_biom_index(h):
    if h < 0.85:
        return 0  # вода
    elif h < 0.88:
        return 1  # пляж
    elif h < 0.93:
        return 2  # трава
    elif h < 0.96:
        return 3  # лес
    elif h < 0.98:
        return 4  # горы
    else:
        return 5  # снег

def build_textured_mesh(heightmap, scale=200.0, height_scale=30.0):
    """
    Создаёт массивы вершин и текстурных координат для ландшафта.
    Каждый треугольник получает свой набор из 3 вершин (дублирование вершин).
    Возвращает (vertices, texcoords) как np.float32 массивы.
    vertices: (N, 3) координаты x,y,z
    texcoords: (N, 2) координаты u,v в атласе (каждая вершина)
    """
    H, W = heightmap.shape
    vertices = []
    texcoords = []

    # Размер одной ячейки атласа (6 биомов в ряд по горизонтали)
    # Атлас 1024x1024, 6 плиток 170x1024 (примерно)
    tile_width = 1.0 / 6.0  # 0.1666...
    tile_height = 1.0        # одна строка

    for i in range(H-1):
        for j in range(W-1):
            # Получаем высоты четырёх углов ячейки
            h_tl = heightmap[i, j]
            h_tr = heightmap[i, j+1]
            h_bl = heightmap[i+1, j]
            h_br = heightmap[i+1, j+1]

            # Вычисляем среднюю высоту для двух треугольников
            avg1 = (h_tl + h_tr + h_bl) / 3.0
            avg2 = (h_tr + h_br + h_bl) / 3.0

            biom1 = get_biom_index(avg1)
            biom2 = get_biom_index(avg2)

            # Базовые координаты вершин (мировые)
            x_tl = (j / (W-1) - 0.5) * scale
            z_tl = (i / (H-1) - 0.5) * scale
            y_tl = h_tl * height_scale

            x_tr = ((j+1) / (W-1) - 0.5) * scale
            z_tr = (i / (H-1) - 0.5) * scale
            y_tr = h_tr * height_scale

            x_bl = (j / (W-1) - 0.5) * scale
            z_bl = ((i+1) / (H-1) - 0.5) * scale
            y_bl = h_bl * height_scale

            x_br = ((j+1) / (W-1) - 0.5) * scale
            z_br = ((i+1) / (H-1) - 0.5) * scale
            y_br = h_br * height_scale

            # --- Первый треугольник (tl, tr, bl) ---
            u0 = biom1 * tile_width
            v0 = 0.0

            # Вершина tl
            vertices.extend([x_tl, y_tl, z_tl])
            texcoords.extend([u0, v0])
            # Вершина tr
            vertices.extend([x_tr, y_tr, z_tr])
            texcoords.extend([u0 + tile_width, v0])
            # Вершина bl
            vertices.extend([x_bl, y_bl, z_bl])
            texcoords.extend([u0, v0 + tile_height])

            # --- Второй треугольник (tr, br, bl) ---
            u1 = biom2 * tile_width
            v1 = 0.0

            # Вершина tr (дублируется)
            vertices.extend([x_tr, y_tr, z_tr])
            texcoords.extend([u1 + tile_width, v1])
            # Вершина br
            vertices.extend([x_br, y_br, z_br])
            texcoords.extend([u1 + tile_width, v1 + tile_height])
            # Вершина bl (дублируется)
            vertices.extend([x_bl, y_bl, z_bl])
            texcoords.extend([u1, v1 + tile_height])

    return np.array(vertices, dtype=np.float32), np.array(texcoords, dtype=np.float32)