def interpolate(p1, p2, x):
    """Compute value at x for the linear function
    passing through p1 and p2.
    f(x) = kx + b
    """
    k = (p2[1] - p1[1])/(p2[0] - p1[0])
    b = p1[1] - k * p1[0] # b = f(x) - kx
    return int(k*x + b)
