import glm
import pygame as pg
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

import anime_girl
from camera import Camera  # предполагается, что класс Camera находится в файле camera.py

# -----------------------------
# heightmap
# -----------------------------
heightmap = anime_girl.gen_terrain()
rows, cols = heightmap.shape
print(f"Карта: {rows} x {cols}, высоты от {heightmap.min():.3f} до {heightmap.max():.3f}")

# -----------------------------
# вычисление нормалей для освещения (оставляем, но пока не используем)
# -----------------------------
def compute_normals(hmap, scale=20):
    rows, cols = hmap.shape
    normals = np.zeros((rows, cols, 3), dtype=np.float32)
    for x in range(rows):
        for y in range(cols):
            xl = hmap[x-1][y] * scale if x > 0 else hmap[x][y] * scale
            xr = hmap[x+1][y] * scale if x < rows-1 else hmap[x][y] * scale
            yd = hmap[x][y-1] * scale if y > 0 else hmap[x][y] * scale
            yu = hmap[x][y+1] * scale if y < cols-1 else hmap[x][y] * scale
            nx = xl - xr
            ny = 2.0
            nz = yd - yu
            length = np.sqrt(nx*nx + ny*ny + nz*nz)
            if length > 0:
                normals[x][y] = [nx/length, ny/length, nz/length]
            else:
                normals[x][y] = [0, 1, 0]
    return normals

normals = compute_normals(heightmap)

# -----------------------------
# настройка освещения (пока отключена)
# -----------------------------
def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)
    glLightfv(GL_LIGHT0, GL_POSITION,  [1.0, 1.0, 0.5, 0.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT,   [0.15, 0.15, 0.20, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   [0.90, 0.85, 0.75, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR,  [0.40, 0.40, 0.40, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.3, 0.3, 0.3, 1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

# -----------------------------
# временная функция цвета (всегда зелёный для проверки)
# -----------------------------
def height_color(h, scale=20):
    # Игнорируем высоту, рисуем всё зелёным
    glColor3f(0.2, 0.8, 0.2)  # ярко-зелёный

# -----------------------------
# рисование terrain (без освещения)
# -----------------------------
def draw_terrain(hmap, nmap, scale=5):   # Уменьшил scale до 5, чтобы ландшафт был компактнее
    rows, cols = hmap.shape
    glBegin(GL_TRIANGLES)
    for x in range(rows - 1):
        for y in range(cols - 1):
            # Вершины: x, y, высота
            v00 = (x,   hmap[x  ][y  ] * scale, y)
            v10 = (x+1, hmap[x+1][y  ] * scale, y)
            v01 = (x,   hmap[x  ][y+1] * scale, y+1)
            v11 = (x+1, hmap[x+1][y+1] * scale, y+1)

            # Первый треугольник (v00, v10, v01)
            height_color(v00[1], scale)
            glNormal3fv(nmap[x][y])
            glVertex3f(*v00)

            height_color(v10[1], scale)
            glNormal3fv(nmap[x+1][y])
            glVertex3f(*v10)

            height_color(v01[1], scale)
            glNormal3fv(nmap[x][y+1])
            glVertex3f(*v01)

            # Второй треугольник (v10, v11, v01)
            height_color(v10[1], scale)
            glNormal3fv(nmap[x+1][y])
            glVertex3f(*v10)

            height_color(v11[1], scale)
            glNormal3fv(nmap[x+1][y+1])
            glVertex3f(*v11)

            height_color(v01[1], scale)
            glNormal3fv(nmap[x][y+1])
            glVertex3f(*v01)
    glEnd()

# -----------------------------
# класс App для камеры
# -----------------------------
class App:
    def __init__(self):
        self.WIN_SIZE = (900, 600)
        self.delta_time = 0

app = App()
pg.init()
display = (900, 600)
screen = pg.display.set_mode(display, DOUBLEBUF | OPENGL)

# -----------------------------
# камера — над центром карты
# -----------------------------
center_x = rows // 2
center_z = cols // 2
camera = Camera(app, position=(center_x, 30, center_z), yaw=135, pitch=-30)  # высота 30
camera.update_camera_vectors()

# Увеличиваем дальность отсечения (если в camera.py FAR мало)
camera.m_proj = glm.perspective(glm.radians(50), app.WIN_SIZE[0]/app.WIN_SIZE[1], 0.1, 1000)

# Устанавливаем матрицу проекции
glMatrixMode(GL_PROJECTION)
glLoadIdentity()
proj_matrix = np.array(camera.m_proj, dtype=np.float32).flatten()
glLoadMatrixf(proj_matrix)
glMatrixMode(GL_MODELVIEW)
glLoadIdentity()

# -----------------------------
# Настройки OpenGL (без освещения, без отсечения граней)
# -----------------------------
glDisable(GL_LIGHTING)       # отключаем освещение
glDisable(GL_CULL_FACE)       # отключаем отсечение граней — чтобы видеть треугольники с любой стороны
glEnable(GL_DEPTH_TEST)
glClearColor(0.45, 0.65, 0.85, 1.0)  # синее небо

pg.event.set_grab(True)
pg.mouse.set_visible(False)

# -----------------------------
# основной цикл
# -----------------------------
clock = pg.time.Clock()
running = True

while running:
    dt = clock.tick(60) / 100.0
    app.delta_time = dt

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running = False
            if event.key == pg.K_r:
                # сброс в центр
                camera.position = glm.vec3(center_x, 30, center_z)
                camera.yaw = 135.0
                camera.pitch = -30.0
                camera.update_camera_vectors()
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 4:   # колёсико вверх
                camera.position += camera.forward * 5.0
            if event.button == 5:   # колёсико вниз
                camera.position -= camera.forward * 5.0

    camera.update()

    # Для отладки выведем позицию и направление раз в 60 кадров
    if pg.time.get_ticks() % 1000 < 20:
        print(f"Cam pos: ({camera.position.x:.1f}, {camera.position.y:.1f}, {camera.position.z:.1f})  forward: ({camera.forward.x:.2f}, {camera.forward.y:.2f}, {camera.forward.z:.2f})")

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Загружаем видовую матрицу
    view_matrix = np.array(camera.m_view, dtype=np.float32).flatten()
    glLoadMatrixf(view_matrix)

    # Рисуем ландшафт (зелёным)
    draw_terrain(heightmap, normals, scale=5)

    pg.display.flip()

pg.event.set_grab(False)
pg.mouse.set_visible(True)
pg.quit()