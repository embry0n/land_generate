import pyassimp
import sys
import pygame as pg
import numpy as np
from OpenGL.GL import *
import glm

from anime_girl import gen_terrain
from camera import Camera
from terrain import build_textured_mesh
from textures import create_atlas, load_texture_from_pil

# Попытка импортировать pyassimp для загрузки моделей
try:
    import pyassimp
    HAS_ASSIMP = True
except ImportError:
    HAS_ASSIMP = False
    print("pyassimp не установлен. Будет использована модель-заглушка (куб).")

WIN_SIZE = (1280, 720)
BG_COLOR = (0.1, 0.2, 0.3, 1.0)

# ----------------------------------------------------------------------
# Функции для работы с моделью
# ----------------------------------------------------------------------
def load_model_obj(filepath):
    """Загружает OBJ модель через pyassimp и возвращает (vertices, normals, texcoords)."""
    if not HAS_ASSIMP:
        return None
    try:
        scene = pyassimp.load(filepath)
        if not scene.meshes:
            pyassimp.release(scene)
            return None
        mesh = scene.meshes[0]  # берём первую меш-сетку
        vertices = np.array(mesh.vertices, dtype=np.float32).flatten()
        normals = np.array(mesh.normals, dtype=np.float32).flatten() if mesh.normals else None
        texcoords = np.array(mesh.texturecoords[0], dtype=np.float32).flatten() if mesh.texturecoords else None
        pyassimp.release(scene)
        return vertices, normals, texcoords
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        return None

def create_cube_model():
    """Создаёт простой куб с нормалями (зелёный)."""
    # Вершины куба (8 углов)
    v = [
        -1, -1,  1,   # 0
         1, -1,  1,   # 1
         1,  1,  1,   # 2
        -1,  1,  1,   # 3
        -1, -1, -1,   # 4
         1, -1, -1,   # 5
         1,  1, -1,   # 6
        -1,  1, -1    # 7
    ]
    # Индексы треугольников (12 треугольников)
    indices = [
        0,1,2, 0,2,3,  # передняя
        5,4,7, 5,7,6,  # задняя
        4,0,3, 4,3,7,  # левая
        1,5,6, 1,6,2,  # правая
        3,2,6, 3,6,7,  # верхняя
        4,5,1, 4,1,0   # нижняя
    ]
    # Нормали для каждой грани (по 6 вершин на грань)
    face_normals = [
        (0,0,1), (0,0,1), (0,0,1), (0,0,1), (0,0,1), (0,0,1),  # передняя
        (0,0,-1), (0,0,-1), (0,0,-1), (0,0,-1), (0,0,-1), (0,0,-1), # задняя
        (-1,0,0), (-1,0,0), (-1,0,0), (-1,0,0), (-1,0,0), (-1,0,0), # левая
        (1,0,0), (1,0,0), (1,0,0), (1,0,0), (1,0,0), (1,0,0),  # правая
        (0,1,0), (0,1,0), (0,1,0), (0,1,0), (0,1,0), (0,1,0),  # верхняя
        (0,-1,0), (0,-1,0), (0,-1,0), (0,-1,0), (0,-1,0), (0,-1,0) # нижняя
    ]
    # Собираем вершины в порядке индексов
    vertices = []
    for idx in indices:
        vertices.extend(v[idx*3:(idx+1)*3])
    # Собираем нормали
    normals = []
    for n in face_normals:
        normals.extend(n)
    return np.array(vertices, dtype=np.float32), np.array(normals, dtype=np.float32), None

def get_height_at_center(heightmap, scale=200.0):
    """Возвращает мировую высоту в центре карты (x=0, z=0)."""
    H, W = heightmap.shape
    i_center = H // 2
    j_center = W // 2
    return heightmap[i_center, j_center] * 30.0  # height_scale = 30.0

# ----------------------------------------------------------------------
# Главная функция
# ----------------------------------------------------------------------
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
    num_vertices = len(vertices) // 3
    print(f"Вершин ландшафта: {num_vertices}")

    # Настройка OpenGL
    glClearColor(*BG_COLOR)
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)

    # ------------------------------------------------------------------
    # Ландшафт
    # ------------------------------------------------------------------
    vao_land = glGenVertexArrays(1)
    glBindVertexArray(vao_land)

    vbo_land = glGenBuffers(2)  # 0 - позиции, 1 - текстурные координаты

    glBindBuffer(GL_ARRAY_BUFFER, vbo_land[0])
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)

    glBindBuffer(GL_ARRAY_BUFFER, vbo_land[1])
    glBufferData(GL_ARRAY_BUFFER, texcoords.nbytes, texcoords, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    # Текстурный атлас для ландшафта
    print("Создание текстурного атласа...")
    atlas_img, _ = create_atlas()
    texture_id = load_texture_from_pil(atlas_img)

    # Шейдер для ландшафта (только текстура)
    vertex_shader_land = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader_land, """
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
    glCompileShader(vertex_shader_land)
    if not glGetShaderiv(vertex_shader_land, GL_COMPILE_STATUS):
        print("Ошибка компиляции вершинного шейдера ландшафта")
        sys.exit()

    fragment_shader_land = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader_land, """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        uniform sampler2D textureAtlas;
        void main() {
            FragColor = texture(textureAtlas, TexCoord);
        }
    """)
    glCompileShader(fragment_shader_land)
    if not glGetShaderiv(fragment_shader_land, GL_COMPILE_STATUS):
        print("Ошибка компиляции фрагментного шейдера ландшафта")
        sys.exit()

    shader_land = glCreateProgram()
    glAttachShader(shader_land, vertex_shader_land)
    glAttachShader(shader_land, fragment_shader_land)
    glLinkProgram(shader_land)
    if not glGetProgramiv(shader_land, GL_LINK_STATUS):
        print("Ошибка линковки шейдера ландшафта")
        sys.exit()

    glDeleteShader(vertex_shader_land)
    glDeleteShader(fragment_shader_land)

    model_loc_land = glGetUniformLocation(shader_land, "model")
    view_loc_land = glGetUniformLocation(shader_land, "view")
    proj_loc_land = glGetUniformLocation(shader_land, "projection")
    tex_loc_land = glGetUniformLocation(shader_land, "textureAtlas")

    # ------------------------------------------------------------------
    # Модель
    # ------------------------------------------------------------------
    print("Загрузка модели...")
    # Попытка загрузить модель из OBJ
    model_data = None
    if HAS_ASSIMP:
        model_data = load_model_obj("tree.obj")  # замените на путь к вашей модели
    if model_data is None:
        # Создаём куб-заглушку
        model_data = create_cube_model()
        print("Используется модель-куб.")

    model_vertices, model_normals, model_texcoords = model_data
    num_model_vertices = len(model_vertices) // 3

    # Создаём VAO для модели
    vao_model = glGenVertexArrays(1)
    glBindVertexArray(vao_model)

    vbo_model = glGenBuffers(3 if model_texcoords is not None else 2)  # позиции, нормали, текстурные координаты

    # Позиции
    glBindBuffer(GL_ARRAY_BUFFER, vbo_model[0])
    glBufferData(GL_ARRAY_BUFFER, model_vertices.nbytes, model_vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)

    # Нормали
    glBindBuffer(GL_ARRAY_BUFFER, vbo_model[1])
    glBufferData(GL_ARRAY_BUFFER, model_normals.nbytes, model_normals, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(1)

    # Текстурные координаты (если есть)
    if model_texcoords is not None:
        glBindBuffer(GL_ARRAY_BUFFER, vbo_model[2])
        glBufferData(GL_ARRAY_BUFFER, model_texcoords.nbytes, model_texcoords, GL_STATIC_DRAW)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(2)

    glBindVertexArray(0)

    # Шейдер для модели (с простым освещением)
    vertex_shader_model = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader_model, """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec3 aNormal;
        layout (location = 2) in vec2 aTexCoord; // опционально
        out vec3 Normal;
        out vec3 FragPos;
        out vec2 TexCoord;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            FragPos = vec3(model * vec4(aPos, 1.0));
            Normal = mat3(transpose(inverse(model))) * aNormal;
            TexCoord = aTexCoord;
            gl_Position = projection * view * vec4(FragPos, 1.0);
        }
    """)
    glCompileShader(vertex_shader_model)
    if not glGetShaderiv(vertex_shader_model, GL_COMPILE_STATUS):
        print("Ошибка компиляции вершинного шейдера модели")
        sys.exit()

    fragment_shader_model = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader_model, """
        #version 330 core
        in vec3 Normal;
        in vec3 FragPos;
        in vec2 TexCoord;
        out vec4 FragColor;
        uniform vec3 lightDir;
        uniform vec3 lightColor;
        uniform vec3 objectColor;
        uniform sampler2D modelTexture;
        uniform bool useTexture;
        void main() {
            vec3 norm = normalize(Normal);
            float diff = max(dot(norm, normalize(-lightDir)), 0.0);
            vec3 diffuse = diff * lightColor;
            vec3 ambient = 0.1 * lightColor;
            vec3 result = (ambient + diffuse) * objectColor;
            if (useTexture) {
                vec4 texColor = texture(modelTexture, TexCoord);
                result *= texColor.rgb;
            }
            FragColor = vec4(result, 1.0);
        }
    """)
    glCompileShader(fragment_shader_model)
    if not glGetShaderiv(fragment_shader_model, GL_COMPILE_STATUS):
        print("Ошибка компиляции фрагментного шейдера модели")
        sys.exit()

    shader_model = glCreateProgram()
    glAttachShader(shader_model, vertex_shader_model)
    glAttachShader(shader_model, fragment_shader_model)
    glLinkProgram(shader_model)
    if not glGetProgramiv(shader_model, GL_LINK_STATUS):
        print("Ошибка линковки шейдера модели")
        sys.exit()

    glDeleteShader(vertex_shader_model)
    glDeleteShader(fragment_shader_model)

    model_loc_model = glGetUniformLocation(shader_model, "model")
    view_loc_model = glGetUniformLocation(shader_model, "view")
    proj_loc_model = glGetUniformLocation(shader_model, "projection")
    lightDir_loc = glGetUniformLocation(shader_model, "lightDir")
    lightColor_loc = glGetUniformLocation(shader_model, "lightColor")
    objectColor_loc = glGetUniformLocation(shader_model, "objectColor")
    useTexture_loc = glGetUniformLocation(shader_model, "useTexture")
    modelTexture_loc = glGetUniformLocation(shader_model, "modelTexture")

    # Параметры освещения
    light_dir = glm.vec3(0.2, -1.0, 0.3)
    light_color = glm.vec3(1.0, 1.0, 1.0)
    object_color = glm.vec3(0.2, 0.8, 0.2)  # зелёный для куба

    # Позиция модели (центр ландшафта)
    model_height = get_height_at_center(terrain)
    model_pos = glm.vec3(0.0, model_height, 0.0)
    model_scale = 2.0
    model_mat = glm.translate(glm.mat4(1.0), model_pos)
    model_mat = glm.scale(model_mat, glm.vec3(model_scale))

    # ------------------------------------------------------------------
    # Камера и главный цикл
    # ------------------------------------------------------------------
    class AppDummy:
        def __init__(self):
            self.WIN_SIZE = WIN_SIZE
            self.delta_time = 0.0
    camera = Camera(AppDummy(), position=(0, 50, 150), yaw=-90, pitch=-30)

    clock = pg.time.Clock()
    running = True

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

        # --- Рендеринг ландшафта ---
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        glUseProgram(shader_land)
        glUniformMatrix4fv(model_loc_land, 1, GL_FALSE, glm.value_ptr(glm.mat4(1.0)))
        glUniformMatrix4fv(view_loc_land, 1, GL_FALSE, glm.value_ptr(camera.m_view))
        glUniformMatrix4fv(proj_loc_land, 1, GL_FALSE, glm.value_ptr(camera.m_proj))
        glUniform1i(tex_loc_land, 0)

        glBindVertexArray(vao_land)
        glDrawArrays(GL_TRIANGLES, 0, num_vertices)

        # --- Рендеринг модели ---
        glUseProgram(shader_model)
        glUniformMatrix4fv(model_loc_model, 1, GL_FALSE, glm.value_ptr(model_mat))
        glUniformMatrix4fv(view_loc_model, 1, GL_FALSE, glm.value_ptr(camera.m_view))
        glUniformMatrix4fv(proj_loc_model, 1, GL_FALSE, glm.value_ptr(camera.m_proj))
        glUniform3fv(lightDir_loc, 1, glm.value_ptr(light_dir))
        glUniform3fv(lightColor_loc, 1, glm.value_ptr(light_color))
        glUniform3fv(objectColor_loc, 1, glm.value_ptr(object_color))
        glUniform1i(useTexture_loc, 1 if model_texcoords is not None else 0)
        if model_texcoords is not None:
            # Если у модели есть текстурные координаты, можно загрузить отдельную текстуру
            # Пока просто используем ту же (но для куба их нет)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glUniform1i(modelTexture_loc, 1)

        glBindVertexArray(vao_model)
        glDrawArrays(GL_TRIANGLES, 0, num_model_vertices)

        pg.display.flip()

    pg.quit()
    sys.exit()

if __name__ == "__main__":
    main()