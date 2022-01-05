import json
import math
import logging

from KicadModTree import *
from .model3d import get_3Dmodel

from svg.path import parse_path
from svg.path import Arc as svg_ARC


logger = logging.getLogger("KICONV")


layer_correspondance = {
    "1": "F.Cu",
    "2": "B.Cu",
    "3": "F.SilkS",
    "4": "B.Silks",
    "5": "F.Paste",
    "6": "B.Paste",
    "7": "F.Mask",
    "8": "B.Mask",
    "10": "Edge.Cuts",
    "12": "F.Fab",
    "100": "F.SilkS",
    "101": "F.Courtyard",
    }


# def mil2mm(data):
#     return float(data) / 3.937

def mil2mm(x, y, footprint_info):
    nx = (float(x) - footprint_info.c_x) * 10 * 0.0254
    ny = (float(y) - footprint_info.c_y) * 10 * 0.0254

    return round(nx, 2), round(ny, 2)


def smil2mm(x, y):
    return round(float(x) * 10 * 0.0254, 2), round(float(y) * 10 * 0.0254, 2)


def pmil2mm(x):
    return round(float(x) * 10 * 0.0254, 2)


def h_TRACK(data, kicad_mod, footprint_info):
    width = pmil2mm(data[0])

    # points = [mil2mm(p) for p in data[2].split(" ")]
    points = data[2].split(" ")
    nodes = []

    for x, y in zip(*[iter(points)] * 2):
        nodes.append(mil2mm(x, y, footprint_info))

    for i in range(len(nodes) - 1):

        start = nodes[i]
        end = nodes[i + 1]

        try:
            layer = layer_correspondance[data[1]]
        except:
            logger.exception(
                "Footprint(h_TRACK): layer correspondance not found."
            )
            layer = "F.SilkS"

        # append line to kicad_mod
        kicad_mod.append(
            Line(
                start=start,
                end=end,
                width=width,
                layer=layer
            )
        )


def h_PAD(data, kicad_mod, footprint_info):
    shape_correspondance = {
        "OVAL": "SHAPE_OVAL",
        "RECT": "SHAPE_RECT",
        "ELLIPSE": "SHAPE_CIRCLE",
        "POLYGON": "SHAPE_CUSTOM",
    }

    rotation = 0
    primitives = ""
    pad_shape = "SHAPE_OVAL"
    pad_drill = None
    pad_type = Pad.TYPE_SMT
    pad_layer = Pad.LAYERS_SMT
    pad_number = data[6]

    hole_size = float(data[7])

    if hole_size > 0:
        pad_type = Pad.TYPE_THT
        pad_layer = Pad.LAYERS_THT
        pad_drill = pmil2mm(hole_size * 2)
        pad_drill_h = pmil2mm(float(data[11]))
        if pad_drill_h > 0:
            pad_drill = (pad_drill_h, pad_drill)

    pad_position = mil2mm(data[1], data[2], footprint_info)
    pad_size = smil2mm(data[3], data[4])

    if data[0] in shape_correspondance:
        pad_shape = shape_correspondance[data[0]]
    else:
        logger.error("Footprint(PAD): no correspondance found, using defualt SHAPE_OVAL.")

    if pad_shape == "SHAPE_OVAL":
        rotation = float(data[9])
    elif pad_shape == "SHAPE_CUSTOM":
        nodes = []
        ori_points = data[8].split(" ")
        for x, y in zip(*[iter(ori_points)] * 2):
            nodes.append(mil2mm(x, y, footprint_info))
        primitives = [Polygon(nodes=nodes)]
    elif pad_shape == "SHAPE_CIRCLE":
        pass
    elif pad_shape == "SHAPE_RECT":
        rotation = float(data[9])

    kicad_mod.append(
        Pad(
            number=pad_number,
            type=pad_type,
            shape=getattr(Pad, pad_shape),
            at=pad_position,
            size=pad_size,
            rotation=rotation,
            drill=pad_drill,
            layers=pad_layer,
            primitives=primitives
        )
    )


def h_ARC(data, kicad_mod, footprint_info):
    # append an Arc to the footprint
    try:
        # parse the data
        if data[2][0] == "M":
            # startX, startY, midX, midY, _, _, _, endX, endY = [val for val in data[2].replace("M", "").replace("A", "").replace(",", " ").split(" ") if val]
            path = parse_path(data[2])
        elif data[3][0] == "M":
            path = parse_path(data[3])
            # startX, startY, midX, midY, _, _, _, endX, endY = [val for val in data[3].replace("M", "").replace("A", "").replace(",", " ").split(" ") if val]
        else:
            logger.warning("Footprint: failed to parse footprint ARC data")

        width = pmil2mm(data[0])
        sarc = path[1]
        if not isinstance(sarc, svg_ARC):
            logger.warning("Footprint: Path ARC DATA ERR. %s", path)
            return

        try:
            layer = layer_correspondance[data[1]]
        except KeyError:
            logger.warning('Footprint(Arc): layer correspondance not found')
            layer = "F.SilkS"

        kicad_mod.append(
            Arc(
                center=mil2mm(sarc.center.real, sarc.center.imag, footprint_info),
                end=mil2mm(sarc.start.real, sarc.start.imag, footprint_info),
                start=mil2mm(sarc.end.real, sarc.end.imag, footprint_info),
                width=width,
                layer=layer
            )
        )
    except:
        logger.exception("Footprint(Arc): failed to add ARC")


def h_CIRCLE(data, kicad_mod, footprint_info):
    # append a Circle to the footprint

    # they want to draw a circle on pads, we don't want that.
    # This is an empirical deduction, no idea if this is correct,
    # but it seems to work on my tests
    if data[4] == "100":
        return

    center = mil2mm(data[0], data[1], footprint_info)
    radius = pmil2mm(data[2])
    width = pmil2mm(data[3])

    try:
        layer = layer_correspondance[data[4]]
    except KeyError:
        logger.exception('Footprint(Circle): footprint layer correspondance not found')
        layer = "F.SilkS"

    kicad_mod.append(
        Circle(
            center=center,
            radius=radius,
            width=width,
            layer=layer
        )
    )


def h_RECT(data, kicad_mod, footprint_info):
    # append a Circle to the footprint

    # they want to draw a circle on pads, we don't want that.
    # This is an empirical deduction, no idea if this is correct,
    # but it seems to work on my tests

    start = mil2mm(data[0], data[1], footprint_info)
    width = pmil2mm(data[2])
    height = pmil2mm(data[3])

    try:
        layer = layer_correspondance[data[4]]
    except KeyError:
        logger.exception('Footprint(Circle): footprint layer correspondance not found')
        layer = "F.SilkS"

    kicad_mod.append(
        RectLine(
            start=start,
            end=[start[0] + width, start[1] + height],
            # width=0.2,
            layer=layer
        )
    )


def h_SOLIDREGION(data, kicad_mod, footprint_info):
    pass


def h_SVGNODE(data, kicad_mod, footprint_info):
    # create 3D model as a WRL file
    model_data = get_3Dmodel(
        component_uuid=json.loads(data[0])["attrs"]["uuid"],
        footprint_info=footprint_info,
        kicad_mod=kicad_mod,
        translationZ=json.loads(data[0])["attrs"]["z"],
        rotation=json.loads(data[0])["attrs"]["c_rotation"]
    )
    return model_data


def h_VIA(data, kicad_mod, footprint_info):
    logger.warning("Footprint: VIA not supported.")
    logger.info("      Via are often added for better heat dissipation.")
    logger.info("      Be careful and read datasheet if needed.")


FOOTPRINT_HANDLER = {
    "TRACK": h_TRACK,
    "PAD": h_PAD,
    "ARC": h_ARC,
    "CIRCLE": h_CIRCLE,
    "SOLIDREGION": h_SOLIDREGION,
    "SVGNODE": h_SVGNODE,
    "RECT": h_RECT,
    "VIA": h_VIA,
}
