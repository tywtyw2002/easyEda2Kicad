import logging
from svg.path import parse_path, Move, Line, Close

logger = logging.getLogger("KICONV")


def h_R(data, kicad_schematic):
    """
    S X1 Y1 X2 Y2 part dmg pen fill

    Rectangle, from X1,Y1 to X2,Y2.
    """

    if len(data) == 12:
        X1 = int((float(data[0]) - kicad_schematic.c_x) * kicad_schematic.scale)
        Y1 = int((float(data[1]) - kicad_schematic.c_y) * kicad_schematic.scale)
        X2 = int((float(data[0]) + float(data[4]) - kicad_schematic.c_x) * kicad_schematic.scale)
        Y2 = int((float(data[1]) + float(data[5]) - kicad_schematic.c_y) * kicad_schematic.scale)
    else:
        X1 = int((float(data[0]) - kicad_schematic.c_x) * kicad_schematic.scale)
        Y1 = int((float(data[1]) - kicad_schematic.c_y) * kicad_schematic.scale)
        X2 = int((float(data[0]) + float(data[2]) - kicad_schematic.c_x) * kicad_schematic.scale)
        Y2 = int((float(data[1]) + float(data[3]) - kicad_schematic.c_y) * kicad_schematic.scale)

    part = kicad_schematic.part
    dmg = "0"
    pen = "0"
    fill = ""

    cmd = f"S {X1} {-Y1} {X2} {-Y2} {part} {dmg} {pen} {fill}"
    kicad_schematic.drawing.append(cmd)


def h_E(data, kicad_schematic):
    """
    C X Y radius part dmg pen fill

    Circle
    """
    try:
        X1 = int(((float(data[0]) - kicad_schematic.c_x)*kicad_schematic.scale))
        Y1 = -int(((float(data[1]) - kicad_schematic.c_y)*kicad_schematic.scale))
        radius = int(float(data[2]) * kicad_schematic.scale)
        dmg = "0"
        pen = "0"
        fill = "N"
        cmd = f"C {X1} {Y1} {radius} {kicad_schematic.part} {dmg} {pen} {fill}"
        kicad_schematic.drawing.append(cmd)
    except:
        logger.exception("Schematic: schematic Circle")


def h_P(data, kicad_schematic):
    """
    Add Pin to the schematic

    X name pin X Y length orientation sizenum sizename part dmg type shape

    Pin description. The pin name is not in double quotes. When a pin has no
    name, parameter name is a “~”, but when a “~” is followed by a name,
    the name has an overbar. The pin parameter is the pin number (it need
    not be numeric and may be a “~”). Parameter orientation is a single letter,
    U(p), D(own), L(eft) or R(ight). The sizenum and sizename parameters
    give the text sizes for the pin number and the pin name respectively. The
    type is a single letter: I(nput), O(utout), B(idirectional), T(ristate),
    P(assive), (open) C(ollector), (open) E(mitter), N(on-connected),
    U(nspecified), or W for power input or w of power output. If the shape is
    absent, the shape is a line, otherwise it is one of the letters I(nverted),
    C(lock), L for input-low, V for output-low (there are more shapes...). If the
    shape is prefixed with an “N”, the pin is invisible.

    """
    pin_name = data[13].replace(" ", "_")
    pin_number = data[2]
    X = int((float(data[3]) - kicad_schematic.c_x) * kicad_schematic.scale)
    Y = -int((float(data[4]) - kicad_schematic.c_y) * kicad_schematic.scale)

    length_raw = data[8].split("^^")[-1]
    svgs = parse_path(length_raw)

    length = int(svgs[-1].length() * 10)
    # length = 200
    if data[5] == '0':
        orientation = 'L'
        # X += int(length/2)
        # X += length
        kicad_schematic.wire_r = 1
    elif data[5] == '180':
        orientation = 'R'
        kicad_schematic.wire_l = 1
        # X -= int(length/2)
        # X -= length
    elif data[5] == '90':
        orientation = 'D'
        kicad_schematic.wire_t = 1
        # Y += int(length/2)
        # Y += length
    elif data[5] == '270':
        orientation = 'U'
        kicad_schematic.wire_b = 1
        # Y -= int(length/2)
        # Y -= length
    else:
        orientation = 'L'
        logger.warning(f"Schematic: pin {pin_name} number {pin_number} failed to find orientation. Using Default orientation 'Left' ")

    sizenum = "40"
    sizename = "40"
    dmg = "0"
    shape = ""

    if data[1] == '0':
        electrical_type = "U"   # Unspecified
    elif data[1] == '1':
        electrical_type = "I"   # Input
    elif data[1] == '2':
        electrical_type = "O"   # Output
    elif data[1] == '3':
        electrical_type = "B"   # Bidirectionnal
    elif data[1] == '4':
        electrical_type = "W"   # Power input
    else:
        electrical_type = "U"    # Unspecified

    cmd = f"X {pin_name} {pin_number} {X} {Y} {length} {orientation} {sizenum} {sizename} {kicad_schematic.part} {dmg} {electrical_type} {shape}"
    kicad_schematic.drawing.append(cmd)


def h_T(data, kicad_schematic):
    """
    T angle X Y size hidden part dmg text italic bold Halign Valign

    Text (which is not in a field). Parameter angle is in 0.1 degrees. Parameter
    hidden is 0 for visible text and 1 for hidden text. The text can be in double
    quotes, or it can be unquoted, but with the ~ character replacing spaces.
    Parameter italic is the word “Italic” for italic text, or “Normal” for upright
    text. Parameter bold is 1 for bold and 0 for normal. Parameters Halign
    and Valign are for the text alignment: C(entred), L(eft), R(ight), T(op) or
    B(ottom).
    """
    try:
        angle = int(data[3])*10
        X = int((float(data[1]) - kicad_schematic.c_x)*kicad_schematic.scale)
        Y = int((float(data[2]) - kicad_schematic.c_y)*kicad_schematic.scale)
        if data[10] == "comment" or data[5] == "comment":
            size = 80
        else:
            size = int(data[5].replace('pt', ''))*10
        hidden = "0"
        part = kicad_schematic.part
        dmg = "0"
        text = data[6].replace(' ', '~')
        italic = "Normal"
        bold = "0"
        Halign = "C"
        Valign = "C"

        cmd= f"T {angle} {X} {Y} {size} {hidden} {part} {dmg} {text} {italic} {bold} {Halign} {Valign}"
        kicad_schematic.drawing.append(cmd)
    except:
        logger.exception("Schematic: failed to add text to schematic")


def h_PL(data, kicad_schematic):
    """
    P count part dmg pen X Y

    fill Polygon with count vertices, and an X,Y position for each vertex. A filled
    polygon is implicitly closed, other polygons are open.
    """

    try:
        count = int(len(data[0].split(" "))/2)
        dmg = 0
        pen = 0
        points = []
        ori_points = data[0].split(' ')
        for px, py in zip(*[iter(ori_points)] * 2):
            x = int((float(px) - kicad_schematic.c_x) * kicad_schematic.scale)
            y = -int((float(py) - kicad_schematic.c_y) * kicad_schematic.scale)
            points.append(str(x))
            points.append(str(y))
        cmd = f"P {count} {kicad_schematic.part} {dmg} {pen} {' '.join(points)}"
        kicad_schematic.drawing.append(cmd)
    except:
        logger.exception("Schematic: failed to add a polygone")


def h_PG(data, kicad_schematic):
    """
    closed polygone handler
    """

    try:
        count = int(len(data[0].split(" "))/2)
        dmg = 0
        pen = 0
        fill = 'f'
        points = []

        ori_points = data[0].split(' ') + data[0].split(' ')[:2]
        for px, py in zip(*[iter(ori_points)] * 2):
            x = int((float(px) - kicad_schematic.c_x) * kicad_schematic.scale)
            y = -int((float(py) - kicad_schematic.c_y) * kicad_schematic.scale)
            points.append(str(x))
            points.append(str(y))

        cmd = f"P {count + 1} {kicad_schematic.part} {dmg} {pen} {' '.join(points)} {fill}"
        kicad_schematic.drawing.append(cmd)
    except:
        logger.exception("Schematic: failed to add a polygone")


def h_PT(data, kicad_schematic):
    """
    Path element handler
    """
    try:
        path = parse_path(data[0])
        count = 0
        dmg = 0
        pen = 0
        points = []
        for element in path:
            if isinstance(element, Move):
                continue

            process_points = []
            if isinstance(element, Line):
                process_points.append(element.start)
            elif isinstance(element, Close):
                process_points.append(element.start)
                process_points.append(element.end)
            else:
                logger.warning("Schematic: unknown type of element. %s", element)

            for point in process_points:
                count += 1
                px = point.real
                py = point.imag

                x = int((float(px) - kicad_schematic.c_x) * kicad_schematic.scale)
                y = -int((float(py) - kicad_schematic.c_y) * kicad_schematic.scale)
                points.append(str(x))
                points.append(str(y))

        cmd = f"P {count} {kicad_schematic.part} {dmg} {pen} {' '.join(points)}"
        kicad_schematic.drawing.append(cmd)
    except:
        logger.exception("Schematic: failed to add a Path element")


SCHEMATIC_HANDLER = {
    "R": h_R,
    "E": h_E,
    "P": h_P,
    "T": h_T,
    "PL": h_PL,
    "PG": h_PG,
    "PT": h_PT,
}
