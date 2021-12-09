# import requests
# import json
import logging

from KicadModTree import Footprint, Text, Translation
from .footprint_handlers import FOOTPRINT_HANDLER


logger = logging.getLogger("KICONV")


class FootprintInfo():
    def __init__(
        self,
        footprint_name,
        assembly_process
    ):
        # # I will be using these to calculate the bounding box
        # because the node.calculateBoundingBox() methode does not
        # seems to work for me
        self.max_X = -10000
        self.max_Y = -10000
        self.min_X = 10000
        self.min_Y = 10000
        self.assembly_process = assembly_process
        self.footprint_name = footprint_name


def create_footprint(
    footprint_name,
    footprint_shape,
    assembly_process
):
    logger.info("Footprint: creating footprint ...")

    # fetch the compoennt data for easyeda library
    # data = json.loads(requests.get(f"https://easyeda.com/api/components/{footprint_component_uuid}").content.decode())
    # footprint_shape = data["result"]["dataStr"]["shape"]

    # footprint_name, datasheet_link, assembly_process = get_footprint_info(component_id)

    # init kicad footprint
    kicad_mod = Footprint(footprint_name)
    # assign tmp node to store footprint 3d info.
    kicad_mod.c_3d_model = None     # type: ignore
    kicad_mod.c_3d_model_rotation = None     # type: ignore
    # TODO Set real description
    # kicad_mod.setDescription(f"{footprint_name} footprint")
    # kicad_mod.setTags(f"{footprint_name} footprint")

    footprint_info = FootprintInfo(
        footprint_name=footprint_name,
        assembly_process=assembly_process
    )

    # for each line in data : use the appropriate handler
    for line in footprint_shape:
        # split and remove empty string in list
        args = [i for i in line.split("~") if i]
        model = args[0]
        logger.debug("Footprint: args->%s", args)
        if model not in FOOTPRINT_HANDLER:
            logger.warning("Footprint: model not in handler->%s", model)
            continue

        if model == "SVGNODE":
            func = FOOTPRINT_HANDLER.get("SVGNODE")
            kicad_mod.c_3d_model, kicad_mod.c_3d_model_rotation = func(args[1:], kicad_mod, footprint_info)    # type: ignore
        else:
            build_func = FOOTPRINT_HANDLER.get(model)
            build_func(args[1:], kicad_mod, footprint_info)     # type: ignore

    # set general values
    kicad_mod.append(
        Text(
            type='reference',
            text='REF**',
            at=[
                (footprint_info.min_X + footprint_info.max_X)/2,
                footprint_info.min_Y - 2
            ],
            layer='F.SilkS'
        )
    )
    kicad_mod.append(
        Text(
            type='user',
            text='REF**',
            at=[
                (footprint_info.min_X + footprint_info.max_X)/2,
                footprint_info.max_Y + 4
            ],
            layer='F.Fab'
        )
    )
    kicad_mod.append(
        Text(
            type='value',
            text=footprint_name,
            at=[
                (footprint_info.min_X + footprint_info.max_X)/2,
                footprint_info.max_Y + 2
            ],
            layer='F.Fab'
            )
        )

    # translate the footprint to be centered around 0,0
    kicad_mod.insert(Translation(-(footprint_info.min_X + footprint_info.max_X)/2, -(footprint_info.min_Y + footprint_info.max_Y)/2))
    logger.info("Footprint: Footprint Generated.")

    # if not os.path.exists(f"{output_dir}/{footprint_lib}"):
    #     os.makedirs(f"{output_dir}/{footprint_lib}")

    # output kicad model
    # file_handler = KicadFileHandler(kicad_mod)
    # file_handler.writeFile(f'{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod')
    # logger.info(f"created '{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod'")

    # return and datasheet link footprint name to be linked with the schematic
    # return(f'{footprint_lib}:{footprint_name}', datasheet_link)
    return kicad_mod


# def get_footprint_info(component_id):
#     # send request to get assembly process and datasheet_link
#     request_data = '''{}\"currentPage\":1,\"pageSize\":100,
#                 \"keyword\":\"{}\",
#                 \"searchSource\":\"search\",
#                 \"componentAttributes\":[]{}"
#                 '''.format("{", component_id, "}")

#     response = json.loads(requests.post(url = "https://jlcpcb.com/shoppingCart/smtGood/selectSmtComponentList",
#                 headers = {"Content-Type" : "application/json;charset=utf-8"},
#                 data = request_data
#                 ).content.decode())

#     footprint_name = response['data']['componentPageInfo']['list'][0]['componentModelEn'].replace(' ', '_').replace('/', '_')

#     component_list = response['data']['componentPageInfo']['list']
#     for component in component_list:
#         if component['componentCode'] == component_id:
#             component_lcscid = component['componentId']

#             component_data = json.loads(requests.get(f"https://jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentLcscId={component_lcscid}").content.decode())["data"]
#             datasheet_link = component_data['dataManualUrl']
#             assembly_process = component_data["assemblyProcess"]
#             break

#     return(footprint_name, datasheet_link, assembly_process)