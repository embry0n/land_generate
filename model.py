import numpy as np

def load_obj(filepath):
    """Загружает OBJ файл и возвращает вершины, нормали, текстурные координаты."""
    vertices = []
    normals = []
    texcoords = []
    faces = []

    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.strip().split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('vt '):
                parts = line.strip().split()
                texcoords.append([float(parts[1]), float(parts[2])])
            elif line.startswith('vn '):
                parts = line.strip().split()
                normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.strip().split()[1:]
                for part in parts:
                    v, vt, vn = (part.split('/') + ['0', '0'])[:3]
                    faces.append([int(v)-1, int(vt)-1 if vt else -1, int(vn)-1 if vn else -1])

    if not faces:
        return None

    # Разворачиваем в плоские массивы (дублируем вершины по необходимости)
    out_vertices = []
    out_normals = []
    out_texcoords = []
    for f in faces:
        v_idx = f[0]
        vt_idx = f[1]
        vn_idx = f[2]
        out_vertices.extend(vertices[v_idx])
        if vt_idx >= 0 and texcoords:
            out_texcoords.extend(texcoords[vt_idx])
        else:
            out_texcoords.extend([0, 0])
        if vn_idx >= 0 and normals:
            out_normals.extend(normals[vn_idx])
        else:
            out_normals.extend([0, 1, 0])  # заглушка

    return (np.array(out_vertices, dtype=np.float32),
            np.array(out_normals, dtype=np.float32),
            np.array(out_texcoords, dtype=np.float32))