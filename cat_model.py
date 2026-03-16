# cat_model.py
import moderngl as mgl
import numpy as np
import glm
from PIL import Image
from model import load_obj_with_mtl
class CatModel:
    def __init__(self, ctx, camera, obj_path, tex_path=None, pos=(0,0,0), rot=(0,0,0), scale=(1,1,1)):
        self.ctx = ctx
        self.camera = camera
        self.pos = glm.vec3(pos)
        self.rot = glm.vec3([glm.radians(a) for a in rot])
        self.scale = glm.vec3(scale)
        self.m_model = self.get_model_matrix()

        # Загружаем геометрию
        vertices, normals, texcoords, tex_file = load_obj_with_mtl(obj_path)
        if vertices is None:
            raise ValueError(f"Не удалось загрузить модель {obj_path}")

        # Если текстура не указана, используем найденную из MTL
        if tex_path is None and tex_file:
            tex_path = tex_file

        # Создаём VBO
        self.vbo_vertices = ctx.buffer(vertices)
        self.vbo_normals = ctx.buffer(normals)
        self.vbo_texcoords = ctx.buffer(texcoords) if texcoords is not None else None

        # Шейдеры (можно вынести в отдельный файл, но для простоты здесь)
        vert_shader = """
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
        frag_shader = """
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
        self.program = ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

        # Формируем список атрибутов
        attributes = [(self.vbo_vertices, '3f', 'in_position'),
                      (self.vbo_normals, '3f', 'in_normal')]
        if self.vbo_texcoords is not None:
            attributes.append((self.vbo_texcoords, '2f', 'in_texcoord'))
        self.vao = ctx.vertex_array(self.program, attributes)
        self.num_vertices = len(vertices) // 3

        # Загружаем текстуру, если есть
        self.use_texture = tex_path is not None
        if self.use_texture:
            img = Image.open(tex_path).convert('RGB')
            img_data = np.array(img, dtype=np.uint8)
            self.texture = ctx.texture(img.size, 3, img_data.tobytes())
            self.texture.use(0)
            self.program['model_texture'] = 0
        else:
            self.texture = None

        # Параметры освещения (можно задать извне)
        self.program['light_dir'] = glm.vec3(0.2, -1.0, 0.3)
        self.program['light_color'] = glm.vec3(1.0, 1.0, 1.0)
        self.program['object_color'] = glm.vec3(0.8, 0.8, 0.8)  # серый, если нет текстуры
        self.program['use_texture'] = self.use_texture

    def get_model_matrix(self):
        m = glm.mat4()
        m = glm.translate(m, self.pos)
        m = glm.rotate(m, self.rot.z, glm.vec3(0,0,1))
        m = glm.rotate(m, self.rot.y, glm.vec3(0,1,0))
        m = glm.rotate(m, self.rot.x, glm.vec3(1,0,0))
        m = glm.scale(m, self.scale)
        return m

    def update(self):
        # Обновляем uniform-переменные (можно вызывать каждый кадр)
        self.program['model'].write(self.m_model)
        self.program['view'].write(self.camera.view_matrix())
        self.program['projection'].write(self.camera.projection_matrix(self.camera.aspect_ratio))

    def render(self):
        self.update()
        self.vao.render(mgl.TRIANGLES)