def interpolate(p1, p2, x):
    """Compute y value at x for the linear function
    passing through two points.
    f(x) = kx + b
    Args:
        p1 (tuple): a pair of (x, y) coordinates
        p2 (tuple): a pair of (x, y) coordinates
        x (int): the observed x-value
    """
    k = (p2[1] - p1[1])/(p2[0] - p1[0])
    b = p1[1] - k * p1[0] # b = f(x) - kx
    return int(k*x + b)

def get_cpu_utilization_background_style(level):
    """Create stylesheet for cpu utilization widget background color;
    lighter value for low values and darker for high values.
    Uses HSL color codes with varying saturation and lightness values.
    Args:
        level (int): current cpu utilization level from 0 to 100
    Return:
        a style sheet string to apply to the widget.
    """ 

    # saturation: increase to 100 from a fixed 'low' value. 20 ↦ 42 and 100 ↦ 100
    saturation = interpolate((20, 42), (100, 100), level)
    
    # lightness: decrease to 30 from a bright value. 20 ↦ 79 and 100 ↦ 30
    lightness = interpolate((20, 79), (100, 30), level)

    # Fixed background color for low utilization values. 
    if level <= 20:
        saturation = 42
        lightness = 79

    return f"background-color: hsl(218, {saturation}%, {lightness}%)"
