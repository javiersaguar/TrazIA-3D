import math


def head_mesh(radius: float, depth: float, z: float, up: int, segments=64, rings=12):
    """Semielipsoide macizo cerrado; aproximación de la envolvente exterior en metros."""
    vertices, triangles = [], []
    for row in range(rings):
        angle = math.pi * row / (2 * rings)
        r = radius * math.cos(angle)
        for col in range(segments):
            theta = 2 * math.pi * col / segments
            vertices.append(
                (r * math.cos(theta), r * math.sin(theta), z + up * depth * math.sin(angle))
            )
    pole = len(vertices) + 1
    vertices.append((0.0, 0.0, z + up * depth))
    center = len(vertices) + 1
    vertices.append((0.0, 0.0, z))
    for row in range(rings - 1):
        for col in range(segments):
            a = row * segments + col + 1
            b = row * segments + (col + 1) % segments + 1
            triangles.extend(((a, b, b + segments), (a, b + segments, a + segments)))
    for col in range(segments):
        nxt = (col + 1) % segments
        triangles.append(((rings - 1) * segments + col + 1, (rings - 1) * segments + nxt + 1, pole))
        triangles.append((center, nxt + 1, col + 1))
    if up < 0:
        triangles = [tuple(reversed(t)) for t in triangles]
    return vertices, triangles
