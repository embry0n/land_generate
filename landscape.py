import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import anime_girl

# -----------------------------
# heightmap
# -----------------------------
heightmap = anime_girl.gen_terrain()

# -----------------------------
# вычисление нормалей для освещения
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
            normals[x][y] = [nx/length, ny/length, nz/length]

    return normals

normals = compute_normals(heightmap)

# -----------------------------
# настройка освещения
# -----------------------------
def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)

    # Направление и цвет основного источника (солнце)
    glLightfv(GL_LIGHT0, GL_POSITION,  [1.0, 1.0, 0.5, 0.0])   # направленный
    glLightfv(GL_LIGHT0, GL_AMBIENT,   [0.15, 0.15, 0.20, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   [0.90, 0.85, 0.75, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR,  [0.40, 0.40, 0.40, 1.0])

    # Материал поверхности
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.3, 0.3, 0.3, 1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

# -----------------------------
# цвет высоты
# -----------------------------
def height_color(h, scale=20):
    t = h / scale          # 0..1 (приблизительно)
    if t < 0.15:           # вода
        glColor3f(0.10, 0.35, 0.70)
    elif t < 0.25:         # песок
        glColor3f(0.76, 0.70, 0.50)
    elif t < 0.55:         # трава
        glColor3f(0.25, 0.55, 0.20)
    elif t < 0.75:         # скалы
        glColor3f(0.50, 0.45, 0.38)
    else:                  # снег
        glColor3f(0.93, 0.93, 0.97)

# -----------------------------
# рисование terrain с нормалями
# -----------------------------
def draw_terrain(hmap, nmap, scale=20):
    rows, cols = hmap.shape
    glBegin(GL_TRIANGLES)
    for x in range(rows - 1):
        for y in range(cols - 1):
            # четыре вершины квадрата
            verts = [
                (x,   hmap[x  ][y  ] * scale, y  , nmap[x  ][y  ]),
                (x+1, hmap[x+1][y  ] * scale, y  , nmap[x+1][y  ]),
                (x,   hmap[x  ][y+1] * scale, y+1, nmap[x  ][y+1]),
                (x+1, hmap[x+1][y+1] * scale, y+1, nmap[x+1][y+1]),
            ]
            # треугольник 1
            for vx, vy, vz, n in [verts[0], verts[1], verts[2]]:
                height_color(vy, scale)
                glNormal3fv(n)
                glVertex3f(vx, vy, vz)
            # треугольник 2
            for vx, vy, vz, n in [verts[1], verts[3], verts[2]]:
                height_color(vy, scale)
                glNormal3fv(n)
                glVertex3f(vx, vy, vz)
    glEnd()

# -----------------------------
# pygame + OpenGL init
# -----------------------------
pygame.init()
display = (900, 600)
screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Terrain Viewer  |  WASD=move  Mouse=look  Scroll=zoom  R=reset")

glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(60, display[0] / display[1], 0.1, 2000.0)
glMatrixMode(GL_MODELVIEW)
glLoadIdentity()

setup_lighting()
glEnable(GL_DEPTH_TEST)
glClearColor(0.45, 0.65, 0.85, 1.0)   # цвет неба

# -----------------------------
# состояние камеры
# -----------------------------
cam_pos   = np.array([-50.0, 30.0, -60.0], dtype=np.float64)
cam_yaw   = 0.0      # горизонтальный угол (градусы)
cam_pitch = -20.0    # вертикальный угол

MOVE_SPEED  = 1.5
MOUSE_SENS  = 0.20
SCROLL_STEP = 5.0

pygame.event.set_grab(True)
pygame.mouse.set_visible(False)

# -----------------------------
# вспомогательные функции
# -----------------------------
def angles_to_direction(yaw, pitch):
    """Вектор «вперёд» из углов Эйлера."""
    y = np.radians(yaw)
    p = np.radians(pitch)
    return np.array([
        np.cos(p) * np.sin(y),
        np.sin(p),
        np.cos(p) * np.cos(y),
    ], dtype=np.float64)

def apply_camera():
    glLoadIdentity()
    fwd = angles_to_direction(cam_yaw, cam_pitch)
    right = np.cross(fwd, [0, 1, 0])
    # Солнечный свет пересчитываем в view space каждый кадр
    glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 0.5, 0.0])
    target = cam_pos + fwd
    gluLookAt(
        cam_pos[0], cam_pos[1], cam_pos[2],
        target[0],  target[1],  target[2],
        0, 1, 0
    )

# -----------------------------
# основной цикл
# -----------------------------
clock   = pygame.time.Clock()
running = True

while running:
    dt = clock.tick(60) / 1000.0   # секунды за кадр

    # ---- события ----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r:              # сброс камеры
                cam_pos   = np.array([-50.0, 30.0, -60.0])
                cam_yaw   = 0.0
                cam_pitch = -20.0

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:                    # колесо вверх = приблизить
                fwd = angles_to_direction(cam_yaw, cam_pitch)
                cam_pos += fwd * SCROLL_STEP
            if event.button == 5:                    # колесо вниз = отдалить
                fwd = angles_to_direction(cam_yaw, cam_pitch)
                cam_pos -= fwd * SCROLL_STEP

    # ---- мышь → вращение ----
    dx, dy    = pygame.mouse.get_rel()
    cam_yaw  += dx * MOUSE_SENS
    cam_pitch -= dy * MOUSE_SENS
    cam_pitch  = max(-89.0, min(89.0, cam_pitch))   # ограничение по вертикали

    # ---- клавиши → перемещение ----
    keys = pygame.key.get_pressed()
    fwd   = angles_to_direction(cam_yaw, cam_pitch)
    right = np.cross(fwd, [0, 1, 0])
    right = right / (np.linalg.norm(right) + 1e-9)

    speed = MOVE_SPEED * (3.0 if keys[pygame.K_LSHIFT] else 1.0)

    if keys[pygame.K_w]:     cam_pos += fwd   * speed
    if keys[pygame.K_s]:     cam_pos -= fwd   * speed
    if keys[pygame.K_a]:     cam_pos -= right * speed
    if keys[pygame.K_d]:     cam_pos += right * speed
    if keys[pygame.K_SPACE]: cam_pos[1] += speed
    if keys[pygame.K_LCTRL]: cam_pos[1] -= speed

    # ---- рендер ----
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    apply_camera()
    draw_terrain(heightmap, normals)

    pygame.display.flip()

pygame.event.set_grab(False)
pygame.mouse.set_visible(True)
pygame.quit()