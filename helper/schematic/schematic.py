# # import requests
# import json
# import re
# import os
import logging
from dataclasses import dataclass

# from KicadModTree import *
from .schematic_handlers import SCHEMATIC_HANDLER


logger = logging.getLogger("KICONV")


def mil2mm(x):
    x = round(int(x) * 0.0254, 4)
    return x


@dataclass
class KICADSchematic:

    def __init__(self, lcid: str):
        self.lcid = lcid
        self.drawing = []
        self.part = 0
        self.scale = 10
        self.c_x = 0
        self.c_y = 0
        self.wire_r = 0
        self.wire_l = 0
        self.wire_t = 0
        self.wire_b = 0


def create_schematic(
    lcid,
    schematic_title,
    schematic_shape,
    symmbolic_prefix,
    footprint_name,
    datasheet_link,
    x_offset=0,
    y_offset=0,
    x_size=0,
    y_size=0,
    scale=10,
    desc="",
    category=" - ",
    manufacturer=""
):

    kicad_schematic = KICADSchematic(lcid=lcid)
    kicad_schematic.part += 1
    kicad_schematic.scale = scale
    # kicad_schematic.c_x = x_offset + x_size / 2
    # kicad_schematic.c_y = y_offset + y_size / 2
    kicad_schematic.c_x = float(x_offset)
    kicad_schematic.c_y = float(y_offset)

    logger.info(f"Schematic: creating schematic...")

    for line in schematic_shape:
        # split and remove empty string in list
        args = [i for i in line.split("~") if i]
        model = args[0]
        logger.debug(f"Schematic: [{model}] args->{args}")

        if model not in SCHEMATIC_HANDLER:
            logger.warning(
                f"Schematic: parsing model not in handler -> {model}")
            continue

        build_func = SCHEMATIC_HANDLER.get(model)
        build_func(args[1:], kicad_schematic)   # type: ignore

    refname_x = -int(x_size / 2 * scale) + 60 + kicad_schematic.wire_l * 120
    refname_y = int(y_size / 2 * scale) + 60 - kicad_schematic.wire_t * 120
    compname_x = int(x_size / 2 * scale) + 40 - kicad_schematic.wire_r * 120
    compname_y = -int(y_size / 2 * scale) - 50 + kicad_schematic.wire_b * 120
    footprint_x = int(x_size / 2 * scale) + 200 - kicad_schematic.wire_r * 120
    footprint_y = int(y_size / 2 * scale) + 180 - kicad_schematic.wire_t * 120

    draw_cmds = "\n".join(kicad_schematic.drawing)

    component_describe = [
        f"  (symbol \"{schematic_title}\" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)",
        f"    (property \"Reference\" \"{symmbolic_prefix}\" (id 0) (at {mil2mm(refname_x)} {mil2mm(refname_y)} 0)",
        "      (effects (font (size 1.27 1.27)))",
        "    )",
        f"    (property \"Value\" \"{schematic_title}\" (id 1) (at {mil2mm(compname_x)} {mil2mm(compname_y)}  0)",
        "      (effects (font (size 1.27 1.27)) (justify left))",
        "    )",
        f"    (property \"Footprint\" \"{footprint_name}\" (id 2) (at {mil2mm(footprint_x)} {mil2mm(footprint_y)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f"    (property \"Datasheet\" \"{datasheet_link}\" (id 3) (at {mil2mm(footprint_x)} {mil2mm(footprint_y + 100)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f"    (property \"LC#\" \"{lcid}\" (id 4) (at {mil2mm(footprint_x)} {mil2mm(footprint_y + 200)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f"    (property \"Description\" \"{desc}\" (id 5) (at {mil2mm(footprint_x)} {mil2mm(footprint_y + 300)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f"    (property \"Category\" \"{category}\" (id 6) (at {mil2mm(footprint_x)} {mil2mm(footprint_y + 400)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f"    (property \"manufacturer\" \"{manufacturer}\" (id 7) (at {mil2mm(footprint_x)} {mil2mm(footprint_y + 500)} 0)",
        "      (effects (font (size 1.27 1.27)) (justify left) hide)",
        "    )",
        f'    (symbol "{schematic_title}_1_0"',
        draw_cmds,
        "    )",
        "  )"
    ]

    logger.info("Schematic: Schematic Generated.")
    return "\n".join(component_describe)