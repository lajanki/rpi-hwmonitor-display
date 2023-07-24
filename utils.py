def interpolate(p1, p2, x):
    """Compute value at x for the linear function
    passing through p1 and p2.
    f(x) = kx + b
    """
    k = (p2[1] - p1[1])/(p2[0] - p1[0])
    b = p1[1] - k * p1[0] # b = f(x) - kx
    return int(k*x + b)

def set_qlcd_color(qlcd):
    """Set QLCD background color based on its value. Lighter value for low values and
    darker for high values.
    Uses HSL color codes with varying lightness value.
    """ 
    value = qlcd.intValue()

    # saturation: 20 ↦ 42 and 100 ↦ 100
    saturation = interpolate((20, 42), (100, 100), value)
    
    # lightness: 20 ↦ 79 and 100 ↦ 30
    lightness = interpolate((20, 79), (100, 30), value)

    if value <= 20:
        saturation = 42
        lightness = 79
        
    qlcd.setStyleSheet(f"QLCDNumber {{ background-color: hsl(218, {saturation}%, {lightness}%) }}")