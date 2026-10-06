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

    saturation = interpolate((20, 30), (100, 50), level)
    
    lightness = interpolate((20, 32), (100, 22), level)

    # Fixed background color for low utilization values. 
    if level <= 20:
        saturation = 30
        lightness = 32

    return f"background-color: hsl(174, {saturation}%, {lightness}%); color: #dde4e0"
