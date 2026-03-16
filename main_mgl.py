import sys
import pygame as pg
import moderngl as mgl
import numpy as np
import glm

from anime_girl import gen_terrain
from camera import Camera
from terrain import build_textured_mesh
from textures import create_atlas, load_texture_from_pil
from model import load_obj

# Константы
WIN_SIZE = (1280, 720)
BG_COLOR = (0.1, 0.2, 0.3, 1.0)

def create_cube_mesh(ctx):
    """Создаёт VAO для куба (заглушка модели)."""
    vertices = np.array([
        -1, -1,  1,  1, -1,  1,  1,  1,  1, -1,  1,  1,  # перед
        -1, -1, -1,  1, -1, -1,  1,  1, -1, -1,  1, -1,  # зад
        -1,  1,  1, -1,  1, -1, -1, -1, -1, -1, -1,  1,  # лево
         1,  1,  1,  1,  1, -1,  1, -1, -1,  1, -1,  1,  # право
        -1,  1,  1,  1,  1,  1,  1,  1, -1, -1,  1, -1,  # верх
        -1, -1,  1,  1, -1,  1,  1, -1, -1, -1, -1, -1,  # низ
    ], dtype=np.float32)

    normals = np.array([
        0,0,1, 0,0,1, 0,0,1, 0,0,1,
        0,0,-1, 0,0,-1, 0,0,-1, 0,0,-1,
        -1,0,0, -1,0,0, -1,0,0, -1,0,0,
        1,0,0, 1,0,0, 1,0,0, 1,0,0,
        0,1,0, 0,1,0, 0,1,0, 0,1,0,
        0,-1,0, 0,-1,0, 0,-1,0, 0,-1,0,
    ], dtype=np.float32)

    vbo_vertices = ctx.buffer(vertices)
    vbo_normals = ctx.buffer(normals)
    vao = ctx.vertex_array([
        (vbo_vertices, '3f', 'in_position'),
        (vbo_normals, '3f', 'in_normal'),
    ])
    return vao, len(vertices) // 3

def main():
    pg.init()
    pg.display.set_mode(WIN_SIZE, pg.OPENGL | pg.DOUBLEBUF)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

    # Создаём контекст ModernGL
    ctx = mgl.create_context()

    # Генерация карты высот
    print("Генерация карты высот...")
    terrain = gen_terrain()
    print("Карта готова, размер:", terrain.shape)

    # Построение меша ландшафта
    print("Построение меша с текстурами...")
    vertices, texcoords = build_textured_mesh(terrain)
    num_vertices = len(vertices) // 3
    print(f"Вершин ландшафта: {num_vertices}")

    # Создаём VBO для ландшафта
    vbo_land_vertices = ctx.buffer(vertices)
    vbo_land_texcoords = ctx.buffer(texcoords)

    # Шейдеры для ландшафта
    vert_land = """
    #version 330
    in vec3 in_position;
    in vec2 in_texcoord;
    out vec2 v_texcoord;
    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;
    void main() {
        v_texcoord = in_texcoord;
        gl_Position = projection * view * model * vec4(in_position, 1.0);
    }
    """
    frag_land = """
    #version 330
    in vec2 v_texcoord;
    out vec4 f_color;
    uniform sampler2D texture_atlas;
    void main() {
        f_color = texture(texture_atlas, v_texcoord);
    }
    """
    prog_land = ctx.program(vertex_shader=vert_land, fragment_shader=frag_land)
    vao_land = ctx.vertex_array(prog_land, [
        (vbo_land_vertices, '3f', 'in_position'),
        (vbo_land_texcoords, '2f', 'in_texcoord'),
    ])

    # Текстурный атлас
    print("Создание текстурного атласа...")
    atlas_img, _ = create_atlas()
    # Конвертируем PIL Image в bytes (RGB)
    img_data = np.array(atlas_img.convert('RGB'), dtype=np.uint8)
    texture = ctx.texture(atlas_img.size, 3, img_data.tobytes())
    texture.use(0)
    prog_land['texture_atlas'] = 0

    # Модель (пытаемся загрузить OBJ, если нет - куб)
    print("Загрузка модели...")
    model_data = load_obj("cat.obj")  # замените на ваш файл
    if model_data is None:
        print("OBJ не найден, использую куб.")
        vao_model, num_model_vertices = create_cube_mesh(ctx)
        model_has_tex = False
    else:
        model_vertices, model_normals, model_texcoords = model_data
        num_model_vertices = len(model_vertices) // 3
        vbo_model_vertices = ctx.buffer(model_vertices)
        vbo_model_normals = ctx.buffer(model_normals)
        vbo_model_texcoords = ctx.buffer(model_texcoords) if model_texcoords is not None else None
        model_has_tex = model_texcoords is not None

        # Шейдер для модели (с освещением)
        vert_model = """
        #version 330
        in vec3 in_position;
        in vec3 in_normal;
        in vec2 in_texcoord;
        out vec3 v_normal;
        out vec3 v_fragpos;
        out vec2 v_texcoord;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            v_fragpos = vec3(model * vec4(in_position, 1.0));
            v_normal = mat3(transpose(inverse(model))) * in_normal;
            v_texcoord = in_texcoord;
            gl_Position = projection * view * vec4(v_fragpos, 1.0);
        }
        """
        frag_model = """
        #version 330
        in vec3 v_normal;
        in vec3 v_fragpos;
        in vec2 v_texcoord;
        out vec4 f_color;
        uniform vec3 light_dir;
        uniform vec3 light_color;
        uniform vec3 object_color;
        uniform sampler2D model_texture;
        uniform bool use_texture;
        void main() {
            vec3 norm = normalize(v_normal);
            float diff = max(dot(norm, normalize(-light_dir)), 0.0);
            vec3 diffuse = diff * light_color;
            vec3 ambient = 0.1 * light_color;
            vec3 result = (ambient + diffuse) * object_color;
            if (use_texture) {
                vec4 tex = texture(model_texture, v_texcoord);
                result *= tex.rgb;
            }
            f_color = vec4(result, 1.0);
        }
        """
        prog_model = ctx.program(vertex_shader=vert_model, fragment_shader=frag_model)
        attributes = [(vbo_model_vertices, '3f', 'in_position'),
                      (vbo_model_normals, '3f', 'in_normal')]
        if model_has_tex:
            attributes.append((vbo_model_texcoords, '2f', 'in_texcoord'))
        vao_model = ctx.vertex_array(prog_model, attributes)

        # Параметры освещения
        prog_model['light_dir'] = glm.vec3(0.2, -1.0, 0.3)
        prog_model['light_color'] = glm.vec3(1.0, 1.0, 1.0)
        prog_model['object_color'] = glm.vec3(0.2, 0.8, 0.2)
        prog_model['use_texture'] = model_has_tex
        if model_has_tex:
            # Создаём отдельную текстуру для модели (пока заглушка)
            model_tex = ctx.texture((2,2), 3, np.array([255,255,255]*4, dtype=np.uint8).tobytes())
            model_tex.use(1)
            prog_model['model_texture'] = 1

    # Камера
    camera = Camera(position=(0, 50, 150), yaw=-90, pitch=-30)

    # Матрица модели для ландшафта (единичная)
    model_land = glm.mat4(1.0)

    # Позиция модели (центр ландшафта)
    def get_height_at_center(hmap):
        H, W = hmap.shape
        return hmap[H//2, W//2] * 30.0
    model_height = get_height_at_center(terrain)
    model_pos = glm.vec3(0.0, model_height, 0.0)
    model_mat = glm.translate(glm.mat4(1.0), model_pos)
    model_mat = glm.scale(model_mat, glm.vec3(2.0))
    model_mat = glm.rotate(model_mat, glm.radians(-90.0), glm.vec3(1, 0, 0))


    clock = pg.time.Clock()
    running = True

    # Словарь для состояний клавиш
    keys = {'w': False, 's': False, 'a': False, 'd': False, 'q': False, 'e': False}

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_w:
                    keys['w'] = True
                elif event.key == pg.K_s:
                    keys['s'] = True
                elif event.key == pg.K_a:
                    keys['a'] = True
                elif event.key == pg.K_d:
                    keys['d'] = True
                elif event.key == pg.K_q:
                    keys['q'] = True
                elif event.key == pg.K_e:
                    keys['e'] = True
            elif event.type == pg.KEYUP:
                if event.key == pg.K_w:
                    keys['w'] = False
                elif event.key == pg.K_s:
                    keys['s'] = False
                elif event.key == pg.K_a:
                    keys['a'] = False
                elif event.key == pg.K_d:
                    keys['d'] = False
                elif event.key == pg.K_q:
                    keys['q'] = False
                elif event.key == pg.K_e:
                    keys['e'] = False
            elif event.type == pg.MOUSEMOTION:
                dx, dy = event.rel
                camera.rotate(dx, dy)

        camera.move(keys, velocity=0.02 * dt * 1000)  # примерно постоянная скорость
        camera.aspect_ratio = WIN_SIZE[0] / WIN_SIZE[1]

        # Очистка экрана
        ctx.clear(*BG_COLOR)
        ctx.enable(mgl.DEPTH_TEST)

        # Рендеринг ландшафта
        prog_land['model'].write(model_land)
        prog_land['view'].write(camera.view_matrix())
        prog_land['projection'].write(camera.projection_matrix(camera.aspect_ratio))
        vao_land.render(mgl.TRIANGLES)

        # Рендеринг модели
        if model_data is None:
            # Для куба используем простой шейдер без текстуры (можно добавить позже)
            # Пока пропускаем, но лучше создать шейдер для куба
            pass
        else:
            prog_model['model'].write(model_mat)
            prog_model['view'].write(camera.view_matrix())
            prog_model['projection'].write(camera.projection_matrix(camera.aspect_ratio))
            vao_model.render(mgl.TRIANGLES)

        pg.display.flip()

    pg.quit()
    sys.exit()

if __name__ == "__main__":
    main()