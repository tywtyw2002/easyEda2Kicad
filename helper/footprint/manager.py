import logging

from pathlib import Path
from KicadModTree import KicadFileHandler


logger = logging.getLogger("KICONV")


class FootprintExist(Exception):
    pass


class FootprintManager:

    def __init__(self, root_path, lib_name='lcsc', lib_prefix='libs'):
        self.lib_name = lib_name
        self.lib_prefix = lib_prefix
        self.lib_path = Path(root_path).joinpath(f"{lib_name}.pretty")
        self.lib_3d_path = Path(root_path).joinpath(f"{lib_name}.3dshapes")

        self.post_init_check()

    def post_init_check(self):
        if not self.lib_path.exists():
            logger.warn("Footprint Manager: Footprint Path not exists, create it.")
            self.lib_path.mkdir()

        if not self.lib_3d_path.exists():
            logger.warn("Footprint Manager: 3D Model Path not exists, create it.")
            self.lib_3d_path.mkdir()

    def add_footprint(self, name, data, update=False):
        footprint_path = self.lib_path.joinpath(f"{name}.kicad_mod")
        if self.check_footprint(name) and not update:
            raise FootprintExist()

        file_handler = KicadFileHandler(data)
        file_handler.writeFile(str(footprint_path))
        # file_handler.writeFile(f'{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod')
        logger.info("Footprint Manager: Footprint add to %s", str(footprint_path))

    def add_3d_model(self, name, data, update=False):
        model_path = self.lib_3d_path.joinpath(f"{name}.wrl")
        model_path.write_text(data)
        logger.info("Footprint Manager: 3D Model add to %s", str(model_path))

    def check_footprint(self, name):
        footprint_path = self.lib_path.joinpath(f"{name}.kicad_mod")
        return footprint_path.exists()

    def check_3d_model(self, name):
        model_path = self.lib_3d_path.joinpath(f"{name}.wrl")
        return model_path.exists()

    def get_3d_model_ref_path(self, name):
        return f"${{KIPRJMOD}}/{self.lib_prefix}/{self.lib_name}.3dshapes/{name}.wrl"
