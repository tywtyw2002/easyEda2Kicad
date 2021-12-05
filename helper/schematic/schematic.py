# # import requests
# import json
# import re
# import os
import logging
from dataclasses import dataclass

# from KicadModTree import *
from .schematic_handlers import SCHEMATIC_HANDLER


logger = logging.getLogger("KICONV")


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
    kicad_schematic.c_x = x_offset + x_size / 2
    kicad_schematic.c_y = y_offset + y_size / 2

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
        f"#\n# {schematic_title}\n#",
        f"DEF {schematic_title} {symmbolic_prefix} 0 40 Y Y {kicad_schematic.part} F N",
        f'F0 "{symmbolic_prefix}" {refname_x} {refname_y} 50 H V C CNN',
        f'F1 "{schematic_title}" {compname_x} {compname_y} 50 H V L CNN',
        f'F2 "{footprint_name}" {footprint_x} {footprint_y} 50 H I L CNN',
        f'F3 "{datasheet_link}" {footprint_x} {footprint_y + 100} 50 H I L C N N',
        f'F4 "{lcid}" {footprint_x} {footprint_y + 200} 50 H I L CNN "LC#"',
        f'F5 "{desc}" {footprint_x} {footprint_y + 300} 50 H I L CNN "Description"',
        f'F6 "{category}" {footprint_x} {footprint_y + 400} 50 H I L CNN "Category"',
        f'F7 "{manufacturer}" {footprint_x} {footprint_y + 500} 50 H I L CNN "manufacturer"',
        'DRAW',
        draw_cmds,
        'ENDDRAW',
        'ENDDEF'
    ]

    logger.info("Schematic: Schematic Generated.")
    return "\n".join(component_describe)