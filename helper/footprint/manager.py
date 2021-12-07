import logging

from pathlib import Path


logger = logging.getLogger("KICONV")


class FootprintManager:

    def __init__(self, root_path, lib_name='lcsc'):
        self.lib_name = lib_name
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

    def add_3d_model(self, name, data, update=False):
        footprint_path = self.lib_path.joinpath(f"{name}.kicad_mod")
        pass

    def add_footprint(self, name, data, update=False):
        model_path = self.lib_path.joinpath(f"{name}.step")
        pass

    def check_footprint(self, name):
        footprint_path = self.lib_path.joinpath(f"{name}.kicad_mod")
        return footprint_path.exists()

    def check_3d_model(self, name):
        model_path = self.lib_path.joinpath(f"{name}.step")
        return model_path.exists()


