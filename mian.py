import sys
import pygame as pg
import numpy as np
from OpenGL.GL import *
import glm

from anime_girl import gen_terrain
from camera import Camera

WIN_SIZE = (1280, 720)
BG_COLOR = (0.1, 0.2, 0.3, 1.0)

def create_terrain_mesh(heightmap, scale=200.0, height_scale=30.0):
    H, W = heightmap.shape
    vertices = []
    colors = []
    
    def get_color(h):
        if h < 0.85:
            return (0.12, 0.29, 0.66)  # вода
        elif h < 0.88:
            return (0.95, 0.82, 0.42)  # пляж
        elif h < 0.93:
            return (0.43, 0.75, 0.29)  # трава
        elif h < 0.96:
            return (0.18, 0.49, 0.20)  # лес
        elif h < 0.98:
            return (0.55, 0.43, 0.39)  # горы
        else:
            return (1.0, 1.0, 1.0)     # снег
    
    for i in range(H):
        for j in range(W):
            x = (j / (W-1) - 0.5) * scale
            z = (i / (H-1) - 0.5) * scale
            y = heightmap[i, j] * height_scale
            vertices.append((x, y, z))
            colors.append(get_color(heightmap[i, j]))
    
    # Индексы треугольников (2 треугольника на ячейку)
    tri_indices = []
    for i in range(H-1):
        for j in range(W-1):
            tl = i * W + j
            tr = i * W + j + 1
            bl = (i+1) * W + j
            br = (i+1) * W + j + 1
            tri_indices.extend([tl, tr, bl, tr, br, bl])
    
    # Индексы линий (только горизонтальные и вертикальные рёбра)
    line_indices = []
    # горизонтальные рёбра
    for i in range(H):
        for j in range(W-1):
            idx1 = i * W + j
            idx2 = i * W + j + 1
            line_indices.extend([idx1, idx2])
    # вертикальные рёбра
    for i in range(H-1):
        for j in range(W):
            idx1 = i * W + j
            idx2 = (i+1) * W + j
            line_indices.extend([idx1, idx2])
    
    return (np.array(vertices, dtype=np.float32),
            np.array(tri_indices, dtype=np.uint32),
            np.array(colors, dtype=np.float32),
            np.array(line_indices, dtype=np.uint32))

def main():
    pg.init()
    pg.display.set_mode(WIN_SIZE, pg.OPENGL | pg.DOUBLEBUF)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)
    
    print("Генерация карты высот...")
    terrain = gen_terrain()
    print("Карта готова, размер:", terrain.shape)
    
    vertices, tri_indices, colors, line_indices = create_terrain_mesh(terrain)
    num_tri = len(tri_indices)
    num_line = len(line_indices)
    
    # Настройка OpenGL
    glClearColor(*BG_COLOR)
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)  # чтобы видеть ландшафт с любой стороны
    
    # --- Создание VAO для треугольников (с цветом) ---
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)
    
    vbo = glGenBuffers(2)          # 0: позиции, 1: цвета
    ebo_tri = glGenBuffers(1)
    
    # VBO для позиций
    glBindBuffer(GL_ARRAY_BUFFER, vbo[0])
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)
    
    # VBO для цветов
    glBindBuffer(GL_ARRAY_BUFFER, vbo[1])
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(1)
    
    # EBO для треугольников
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_tri)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, tri_indices.nbytes, tri_indices, GL_STATIC_DRAW)
    
    glBindVertexArray(0)  # отвязали VAO треугольников
    
    # --- Создание VAO для линий (только позиция) ---
    line_vao = glGenVertexArrays(1)
    glBindVertexArray(line_vao)
    
    # Используем тот же VBO позиций (vbo[0])
    glBindBuffer(GL_ARRAY_BUFFER, vbo[0])
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)
    
    # Отдельный EBO для линий
    ebo_line = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_line)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, line_indices.nbytes, line_indices, GL_STATIC_DRAW)
    
    glBindVertexArray(0)
    
    # --- Шейдер для треугольников (с цветом) ---
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec3 aColor;
        out vec3 Color;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            Color = aColor;
            gl_Position = projection * view * model * vec4(aPos, 1.0);
        }
    """)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        print("Ошибка компиляции вершинного шейдера (треугольники)")
        sys.exit()
    
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, """
        #version 330 core
        in vec3 Color;
        out vec4 FragColor;
        void main() {
            FragColor = vec4(Color, 1.0);
        }
    """)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        print("Ошибка компиляции фрагментного шейдера (треугольники)")
        sys.exit()
    
    shader_prog = glCreateProgram()
    glAttachShader(shader_prog, vertex_shader)
    glAttachShader(shader_prog, fragment_shader)
    glLinkProgram(shader_prog)
    if not glGetProgramiv(shader_prog, GL_LINK_STATUS):
        print("Ошибка линковки шейдерной программы (треугольники)")
        sys.exit()
    
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)
    
    model_loc = glGetUniformLocation(shader_prog, "model")
    view_loc = glGetUniformLocation(shader_prog, "view")
    proj_loc = glGetUniformLocation(shader_prog, "projection")
    
    # --- Шейдер для линий (чёрный) ---
    line_vertex = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(line_vertex, """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            gl_Position = projection * view * model * vec4(aPos, 1.0);
        }
    """)
    glCompileShader(line_vertex)
    if not glGetShaderiv(line_vertex, GL_COMPILE_STATUS):
        print("Ошибка компиляции вершинного шейдера (линии)")
        sys.exit()
    
    line_fragment = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(line_fragment, """
        #version 330 core
        out vec4 FragColor;
        void main() {
            FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
    """)
    glCompileShader(line_fragment)
    if not glGetShaderiv(line_fragment, GL_COMPILE_STATUS):
        print("Ошибка компиляции фрагментного шейдера (линии)")
        sys.exit()
    
    line_prog = glCreateProgram()
    glAttachShader(line_prog, line_vertex)
    glAttachShader(line_prog, line_fragment)
    glLinkProgram(line_prog)
    if not glGetProgramiv(line_prog, GL_LINK_STATUS):
        print("Ошибка линковки шейдерной программы (линии)")
        sys.exit()
    
    glDeleteShader(line_vertex)
    glDeleteShader(line_fragment)
    
    line_model_loc = glGetUniformLocation(line_prog, "model")
    line_view_loc = glGetUniformLocation(line_prog, "view")
    line_proj_loc = glGetUniformLocation(line_prog, "projection")
    
    # --- Камера ---
    camera = Camera(type('App', (), {'WIN_SIZE': WIN_SIZE, 'delta_time': 0.0})())
    # Рекомендуется поднять камеру выше для лучшего обзора:
    # camera.position = glm.vec3(0, 50, 150)
    # camera.pitch = -30
    
    clock = pg.time.Clock()
    running = True
    model = glm.mat4(1.0)  # матрица модели (единичная)
    
    while running:
        delta_time = clock.tick(60) / 1000.0
        camera.app.delta_time = delta_time
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                running = False
        
        camera.update()
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # --- Рисуем треугольники (цветной ландшафт) ---
        glUseProgram(shader_prog)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(camera.m_view))
        glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm.value_ptr(camera.m_proj))
        
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, num_tri, GL_UNSIGNED_INT, None)
        
        # --- Рисуем чёрные линии поверх ---
        glEnable(GL_POLYGON_OFFSET_LINE)
        glPolygonOffset(-1, -1)  # смещаем линии ближе к камере, чтобы избежать z-борьбы
        glLineWidth(1.5)
        
        glUseProgram(line_prog)
        glUniformMatrix4fv(line_model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glUniformMatrix4fv(line_view_loc, 1, GL_FALSE, glm.value_ptr(camera.m_view))
        glUniformMatrix4fv(line_proj_loc, 1, GL_FALSE, glm.value_ptr(camera.m_proj))
        
        glBindVertexArray(line_vao)
        glDrawElements(GL_LINES, num_line, GL_UNSIGNED_INT, None)
        
        glDisable(GL_POLYGON_OFFSET_LINE)
        
        # Не забываем отвязать VAO (необязательно, но для порядка)
        glBindVertexArray(0)
        
        pg.display.flip()
    
    pg.quit()
    sys.exit()

if __name__ == "__main__":
    main()