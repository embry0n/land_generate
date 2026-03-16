import glm

class Camera:
    def __init__(self, fov=50, near=0.1, far=500, position=(0, 50, 150), yaw=-90, pitch=-30):
        self.position = glm.vec3(position)
        self.yaw = yaw
        self.pitch = pitch
        self.up = glm.vec3(0, 1, 0)
        self.fov = fov
        self.near = near
        self.far = far
        self.aspect_ratio = 1.0  # будет обновляться из окна
        self.update_vectors()

    def update_vectors(self):
        yaw_rad = glm.radians(self.yaw)
        pitch_rad = glm.radians(self.pitch)
        self.forward = glm.vec3(
            glm.cos(yaw_rad) * glm.cos(pitch_rad),
            glm.sin(pitch_rad),
            glm.sin(yaw_rad) * glm.cos(pitch_rad)
        )
        self.forward = glm.normalize(self.forward)
        self.right = glm.normalize(glm.cross(self.forward, glm.vec3(0, 1, 0)))
        self.up = glm.normalize(glm.cross(self.right, self.forward))

    def rotate(self, dx, dy):
        self.yaw += dx * 0.1
        self.pitch -= dy * 0.1
        self.pitch = max(-89, min(89, self.pitch))
        self.update_vectors()

    def move(self, keys, velocity):
        if keys['w']: self.position += self.forward * velocity
        if keys['s']: self.position -= self.forward * velocity
        if keys['a']: self.position -= self.right * velocity
        if keys['d']: self.position += self.right * velocity
        if keys['q']: self.position += self.up * velocity
        if keys['e']: self.position -= self.up * velocity

    def view_matrix(self):
        return glm.lookAt(self.position, self.position + self.forward, self.up)

    def projection_matrix(self, aspect):
        return glm.perspective(glm.radians(self.fov), aspect, self.near, self.far)