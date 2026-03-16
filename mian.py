import sys
import pygame as pg
import numpy as np
from OpenGL.GL import *
import glm

from anime_girl import gen_terrain
from camera import Camera
from terrain import build_textured_mesh
from textures import create_atlas, load_texture_from_pil

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

    print("Построение меша с текстурами...")
    vertices, texcoords = build_textured_mesh(terrain)
    num_vertices = len(vertices) // 3  # количество вершин
    print(f"Вершин: {num_vertices}")

    # Настройка OpenGL
    glClearColor(*BG_COLOR)
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)

    # Создание VAO и VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(2)  # 0 - позиции, 1 - текстурные координаты

    # VBO для позиций
    glBindBuffer(GL_ARRAY_BUFFER, vbo[0])
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)

    # VBO для текстурных координат
    glBindBuffer(GL_ARRAY_BUFFER, vbo[1])
    glBufferData(GL_ARRAY_BUFFER, texcoords.nbytes, texcoords, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    # Создание текстурного атласа
    print("Создание текстурного атласа...")
    atlas_img, _ = create_atlas()
    texture_id = load_texture_from_pil(atlas_img)

    # Шейдеры
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec2 aTexCoord;
        out vec2 TexCoord;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            TexCoord = aTexCoord;
            gl_Position = projection * view * model * vec4(aPos, 1.0);
        }
    """)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        print("Ошибка компиляции вершинного шейдера")
        sys.exit()

    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        uniform sampler2D textureAtlas;
        void main() {
            FragColor = texture(textureAtlas, TexCoord);
        }
    """)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        print("Ошибка компиляции фрагментного шейдера")
        sys.exit()

    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        print("Ошибка линковки шейдерной программы")
        sys.exit()

    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    model_loc = glGetUniformLocation(shader_program, "model")
    view_loc = glGetUniformLocation(shader_program, "view")
    proj_loc = glGetUniformLocation(shader_program, "projection")
    tex_loc = glGetUniformLocation(shader_program, "textureAtlas")

    # Камера
    class AppDummy:
        def __init__(self):
            self.WIN_SIZE = WIN_SIZE
            self.delta_time = 0.0
    camera = Camera(AppDummy(), position=(0, 50, 150), yaw=-90, pitch=-30)

    clock = pg.time.Clock()
    running = True
    model = glm.mat4(1.0)

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

        # Активация текстуры
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        glUseProgram(shader_program)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(camera.m_view))
        glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm.value_ptr(camera.m_proj))
        glUniform1i(tex_loc, 0)  # текстурный юнит 0

        glBindVertexArray(vao)
        glDrawArrays(GL_TRIANGLES, 0, num_vertices)

        pg.display.flip()

    pg.quit()
    sys.exit()

if __name__ == "__main__":
    main()