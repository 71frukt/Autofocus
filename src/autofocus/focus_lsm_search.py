import numpy as np

def choose_pivot_points(points: np.ndarray) -> np.ndarray:
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f"Expected a matrix of shape (N, 2), got {points.shape}")

    if points.shape[0] < 3:
        raise ValueError(f"At least 3 points are required, got {points.shape[0]}")

    # Извлекаем вектор y (второй столбец)
    y_values = points[:, 1]

    # np.argsort sorts in ascending order, takes the last 3 indices, and expands them
    top_3_indices = np.argsort(y_values)[-3:][::-1]

    return points[top_3_indices]


def find_parabola_maximum(points: np.ndarray) -> float:
    # temporarily: in my understanding, we can test the system by approximating N points with a parabola
    # if points.shape != (3, 2):
    #     raise ValueError(f"Expected a matrix of shape (3, 2), got {points.shape}")

    x = points[:, 0]
    y = points[:, 1]

    a, b, c = np.polyfit(x, y, 2)

    if a >= 0:
        raise ValueError(f"The fitted parabola does not have a maximum (a = {a:.4f} >= 0)")

    x_max: float = -b / (2.0 * a)
    return float(x_max)