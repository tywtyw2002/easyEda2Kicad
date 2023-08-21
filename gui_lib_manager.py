import wx
from helper.footprint import FootprintManager, create_footprint
from helper.schematic import create_schematic, SchematicManager
from helper.schematic import SchematicExist, SchematicNotFound

import logging
import requests

from KicadModTree import Model
from logging import Handler, Formatter
from pathlib import Path


logger = logging.getLogger("KICONV")


class CMHandler(Handler):
    def __init__(self, func):
        Handler.__init__(self)
        self.status_write_func = func
        self.formatter = Formatter(
            fmt='%(asctime)s [%(levelname)s] %(message)s\n',
            datefmt='%H:%M:%S'
        )

    def emit(self, record):
        msg = self.format(record)
        self.status_write_func(msg)


class LCComponent:

    def __init__(self, lcid, lc_data=None):
        self.lcid = lcid
        self.lc_data = lc_data
        self.raw_data = None
        self.footprint = None
        self.symbol = None

    @property
    def model3d_name(self):
        if self.footprint is None:
            logger.warning("3DModel Name not avaliable.")
            return ""

        return self.footprint['dataStr']['head']['c_para'].get('3DModel', "")

    @property
    def footprint_name(self):
        if self.footprint is None:
            logger.warning("Footprint Name not avaliable.")
            return ""

        # title = self.raw_data.get('title', self.lcid)
        return self.footprint['title']

    @property
    def symbol_name(self):
        if self.symbol is None:
            logger.warning("Symbol Name not avaliable.")
            return ""

        return self.symbol['head']['c_para']['name']

    def load_componnt(self):
        logger.info("Load Component -> %s", self.lcid)

        req = requests.get(
            f"https://easyeda.com/api/products/{self.lcid}/components"
        )

        data = req.json()

        if data['code'] != 0:
            logger.critical(
                "Unable to load component %s. Code: %s",
                self.lcid,
                data['message']
            )
            return False

        self.raw_data = data['result']

        self.symbol = self.raw_data['dataStr']
        self.footprint = self.raw_data['packageDetail']

        return True

    def calc_symbol_size(self, scale=10):
        if self.symbol is None:
            return "Symbol not Avalible."

        box = self.symbol['BBox']
        bh = box['height'] * scale * 0.00254
        bw = box['width'] * scale * 0.00254
        ret = f"{bw:.2f} mm * {bh:.2f} mm"

        return ret

    def gen_footprint_data(self, footprint_name):
        if self.footprint is None:
            logger.critical("Cannot Generate Footprint. Data Not Avalible.")
            return None

        assembly_process = self.raw_data.get('SMT', False)
        box = self.footprint['dataStr']['BBox']
        canvas = self.footprint['dataStr']['canvas']
        canvas = canvas.split("~")

        data = create_footprint(
            footprint_name,
            self.footprint['dataStr']['shape'],
            assembly_process,
            c_x=float(canvas[16]),
            c_y=float(canvas[17]),
            size_x=float(box['width']),
            size_y=float(box['height'])
        )

        data.setDescription(f"{footprint_name} footprint")
        # data.setTags(f"{footprint_name} footprint")

        return data

    def get_datasheet(self):
        datasheet = self.footprint['dataStr']['head']['c_para']['link']    # type: ignore
        if self.lc_data:
            datasheet = self.lc_data['pdfUrl']

        return datasheet

    def gen_symbol_data(
        self,
        symbol_name,
        footprint_name,
        scale=10
    ):
        if self.symbol is None:
            logger.critical("Cannot Generate Symbol Data. No Symbol Avalible.")
            return None

        box = self.symbol['BBox']
        symmbolic_prefix = self.symbol['head']['c_para']['pre']
        manufacturer = self.symbol['head']['c_para']['Manufacturer']
        datasheet_link = self.get_datasheet()
        category = " - "
        desc = self.raw_data['description']     # type: ignore
        if desc == "" and self.lc_data:
            lc_desc = self.lc_data.get('productIntroEn', "")
            if lc_desc:
                desc = lc_desc

        # get datasheet
        if self.lc_data is not None:
            category = f"{self.lc_data['parentCatalogName']} - {self.lc_data['catalogName']}"

        canvas = self.symbol['canvas']
        canvas = canvas.split("~")

        return create_schematic(
            lcid=self.lcid,
            schematic_title=symbol_name,
            schematic_shape=self.symbol['shape'],
            symmbolic_prefix=symmbolic_prefix,
            footprint_name=footprint_name,
            datasheet_link=datasheet_link,
            # x_offset=box['x'],
            # y_offset=box['y'],
            x_offset=canvas[13],
            y_offset=canvas[14],
            x_size=box['width'],
            y_size=box['height'],
            scale=scale,
            desc=desc,
            category=category,
            manufacturer=manufacturer
        )


class LCUUIDComponent(LCComponent):
    def __init__(self, part_uuid, source_easyeda=True):
        self.lcid = part_uuid
        self.lc_data = None
        self.raw_data = None
        self.footprint = None
        self.symbol = None
        self.source_easyeda = source_easyeda

    def load_componnt(self):
        logger.info("Load Component -> %s", self.lcid)

        url = f"https://easyeda.com/api/components/{self.lcid}"

        if not self.source_easyeda:
            url = f"https://lceda.cn/api/components/{self.lcid}"

        req = requests.get(url)

        data = req.json()

        if data['code'] != 0:
            logger.critical(
                "Unable to load component %s. Code: %s",
                self.lcid,
                data['message']
            )
            return False

        self.raw_data = data['result']

        if self.raw_data['docType'] == 2:
            self.symbol = self.raw_data['dataStr']
            self.footprint = self.raw_data['packageDetail']
        elif self.raw_data['docType'] == 4:
            self.footprint = self.raw_data

        return True


class LibManagerFrame(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: LibManager.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetSize((600, 480))
        self.SetTitle("Symbol & Footprint Export")

        self.panel_1 = wx.Panel(self, wx.ID_ANY)

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)

        sizer_left_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_left_panel, 1, wx.EXPAND, 0)

        sizer_lib_path = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, "Library Path"), wx.VERTICAL)
        sizer_left_panel.Add(sizer_lib_path, 0, wx.EXPAND, 0)

        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lib_path.Add(sizer_4, 0, wx.EXPAND, 0)

        label_path = wx.StaticText(self.panel_1, wx.ID_ANY, "Directory:")
        label_path.SetMinSize((100, 16))
        sizer_4.Add(label_path, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        # self.txt_lib_path = wx.TextCtrl(self.panel_1, wx.ID_ANY, "")
        # sizer_4.Add(self.txt_lib_path, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.lib_path_picker = wx.DirPickerCtrl(
            self.panel_1,
            wx.ID_ANY,
            wx.EmptyString,
            u"Select Library folder",
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.DIRP_SMALL | wx.DIRP_USE_TEXTCTRL | wx.BORDER_SIMPLE
        )
        sizer_4.Add(self.lib_path_picker, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_4.Add((10, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lib_path.Add(sizer_5, 0, wx.EXPAND, 0)

        label_1 = wx.StaticText(self.panel_1, wx.ID_ANY, "Library Name:")
        label_1.SetMinSize((100, 16))
        sizer_5.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_lib_name = wx.TextCtrl(self.panel_1, wx.ID_ANY, "lcsc")
        sizer_5.Add(self.txt_lib_name, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_5.Add((50, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_6 = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, "Symbol & Footprint"), wx.VERTICAL)
        self.symbol_footprint_sizer = sizer_6
        sizer_left_panel.Add(sizer_6, 1, wx.EXPAND, 0)

        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6.Add(sizer_7, 0, wx.EXPAND, 0)

        label_2 = wx.StaticText(self.panel_1, wx.ID_ANY, "Export:")
        label_2.SetMinSize((100, 25))
        sizer_7.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.cb_symbol = wx.CheckBox(self.panel_1, wx.ID_ANY, "Symbol")
        self.cb_symbol.SetMinSize((100, 18))
        self.cb_symbol.SetValue(1)
        # self.cb_symbol.Disable()
        sizer_7.Add(self.cb_symbol, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.cb_footprint = wx.CheckBox(self.panel_1, wx.ID_ANY, "Footprint")
        self.cb_footprint.SetMinSize((100, 18))
        self.cb_footprint.SetValue(1)
        # self.cb_footprint.Disable()
        sizer_7.Add(self.cb_footprint, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.cb_3dmodal = wx.CheckBox(self.panel_1, wx.ID_ANY, "3D Model")
        self.cb_3dmodal.SetMinSize((100, 18))
        self.cb_3dmodal.SetValue(1)
        # self.cb_3dmodal.Disable()
        sizer_7.Add(self.cb_3dmodal, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        symbol_conf_sizer = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, "Symbol Settings"), wx.VERTICAL)
        self.symbol_conf_sizer = symbol_conf_sizer
        sizer_6.Add(symbol_conf_sizer, 0, wx.EXPAND, 0)

        sizer_symbol_name = wx.BoxSizer(wx.HORIZONTAL)
        symbol_conf_sizer.Add(sizer_symbol_name, 0, wx.EXPAND, 0)

        label_5 = wx.StaticText(self.panel_1, wx.ID_ANY, "Symbol Name:")
        label_5.SetMinSize((120, 16))
        sizer_symbol_name.Add(label_5, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_symbol_name = wx.TextCtrl(self.panel_1, wx.ID_ANY, "")
        self.txt_symbol_name.SetMinSize((-1, 22))
        # self.txt_symbol_name.Disable()
        sizer_symbol_name.Add(self.txt_symbol_name, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_symbol_name.Add((10, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        symbol_conf_sizer.Add(sizer_8, 0, wx.EXPAND, 0)

        label_3 = wx.StaticText(self.panel_1, wx.ID_ANY, "Scale:")
        label_3.SetMinSize((120, 16))
        sizer_8.Add(label_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.select_symbol_scale = wx.ComboBox(
            self.panel_1,
            wx.ID_ANY,
            choices=[str(x) for x in range(1, 21)],
            style=wx.CB_DROPDOWN)
        self.select_symbol_scale.SetMinSize((50, 25))
        self.select_symbol_scale.SetSelection(9)
        # self.select_symbol_scale.Disable()
        sizer_8.Add(self.select_symbol_scale, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_8.Add((30, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_4 = wx.StaticText(self.panel_1, wx.ID_ANY, "Symbol Size:")
        label_4.SetMinSize((80, 16))
        sizer_8.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_symbol_size = wx.StaticText(self.panel_1, wx.ID_ANY, "")
        self.txt_symbol_size.SetMinSize((-1, 16))
        sizer_8.Add(self.txt_symbol_size, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        # footprint
        footprint_conf_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.panel_1, wx.ID_ANY, "Footprint Settings"),
            wx.VERTICAL
        )
        self.footprint_conf_sizer = footprint_conf_sizer
        sizer_6.Add(footprint_conf_sizer, 0, wx.EXPAND, 0)

        sizer_footprint_name = wx.BoxSizer(wx.HORIZONTAL)
        footprint_conf_sizer.Add(sizer_footprint_name, 0, wx.EXPAND, 0)

        label_6 = wx.StaticText(self.panel_1, wx.ID_ANY, "Footprint Name:")
        label_6.SetMinSize((120, 16))
        sizer_footprint_name.Add(label_6, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_footprint_name = wx.TextCtrl(self.panel_1, wx.ID_ANY, "")
        self.txt_footprint_name.SetMinSize((-1, 22))
        # self.txt_footprint_name.Disable()
        sizer_footprint_name.Add(
            self.txt_footprint_name, 1, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_footprint_name.Add((10, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        # 3d
        model3d_conf_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.panel_1, wx.ID_ANY, "3D Model Settings"),
            wx.VERTICAL
        )
        self.model3d_conf_sizer = model3d_conf_sizer
        sizer_6.Add(model3d_conf_sizer, 0, wx.EXPAND, 0)

        sizer_3dmodel_name = wx.BoxSizer(wx.HORIZONTAL)
        model3d_conf_sizer.Add(sizer_3dmodel_name, 0, wx.EXPAND, 0)

        label_16 = wx.StaticText(self.panel_1, wx.ID_ANY, "3D Model Name:")
        label_16.SetMinSize((120, 16))
        sizer_3dmodel_name.Add(label_16, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_3dmodel_name = wx.TextCtrl(self.panel_1, wx.ID_ANY, "")
        self.txt_3dmodel_name.SetMinSize((-1, 22))
        # self.txt_footprint_name.Disable()
        sizer_3dmodel_name.Add(
            self.txt_3dmodel_name, 1, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_3dmodel_name.Add((10, 25), 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_log = wx.StaticBoxSizer(
            wx.StaticBox(self.panel_1, wx.ID_ANY, "Logs"), wx.HORIZONTAL
        )
        sizer_left_panel.Add(sizer_log, 1, wx.EXPAND, 0)

        self.txt_ctl_log = wx.TextCtrl(
            self.panel_1,
            wx.ID_ANY,
            "",
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        sizer_log.Add(self.txt_ctl_log, 1, wx.EXPAND, 0)

        sizer_1.Add((10, 20), 0, 0, 0)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_2, 0, 0, 0)

        sizer_2.Add((100, 10), 0, 0, 0)
        self.btn_load = wx.Button(self.panel_1, wx.ID_ANY, "Load Part")
        sizer_2.Add(self.btn_load, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        sizer_2.AddSpacer(10)

        self.btn_gen = wx.Button(self.panel_1, wx.ID_ANY, "Generate")
        self.btn_gen.Disable()
        sizer_2.Add(self.btn_gen, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        sizer_2.Add((100, 100), 0, 0, 0)

        self.btn_close = wx.Button(self.panel_1, wx.ID_ANY, "Close")
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close_press)
        sizer_2.Add(self.btn_close, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.panel_1.SetSizer(sizer_1)

        self.Layout()

    def on_btn_close_press(self, e):
        self.EndModal(wx.OK)


class LibManagerControl:

    def __init__(self, wx_parent, lib_root=None, lib_name=None):
        # LibManagerFrame.__init__(self, None)
        self.wx_parent = wx_parent
        self.lib_root = lib_root
        self.lib_name = lib_name
        self.footprint_manager = None
        self.schematic_manager = None
        self.frame = None
        self.component = None
        self.cx_handler = None

    def disable_all_children(self, parent):
        for children in parent.GetChildren():
            if children.IsWindow():
                children.GetWindow().Disable()
            elif children.IsSizer():
                self.disable_all_children(children.GetSizer())

    def enable_all_children(self, parent):
        for children in parent.GetChildren():
            if children.IsWindow():
                children.GetWindow().Enable()
            elif children.IsSizer():
                self.enable_all_children(children.GetSizer())

    def gen_symbol(self, symbol_name, footprint_name):
        symbol_enabled = self.frame.cb_symbol.GetValue()
        if not symbol_enabled:
            logger.info("Skip Symbol Generate.")
            return

        if self.schematic_manager is None:
            logger.info(
                "Init Schematic Manager. Name: %s, Path: %s.",
                self.lib_name,
                self.lib_root)
            self.schematic_manager = SchematicManager(
                self.lib_root,
                self.lib_name
            )
            self.schematic_manager.build_schematic_db()

        scale = int(self.frame.select_symbol_scale.GetStringSelection())
        symbol_data = self.component.gen_symbol_data(
            symbol_name, footprint_name, scale)

        if symbol_data is None:
            return

        try:
            self.schematic_manager.add_schematic(symbol_name, symbol_data)
        except SchematicExist:
            answer = wx.MessageBox(
                "Schematic Already Exist.\nDo you want to Update?",
                "Confirm",
                wx.YES_NO | wx.CANCEL,
                self.frame
            )
            if answer == wx.YES:
                self.schematic_manager.add_schematic(
                    symbol_name, symbol_data, update=True
                )

    def gen_footprint(self, footprint_name, model3d_name):
        footprint_enabled = self.frame.cb_footprint.GetValue()
        model3d_enabled = self.frame.cb_3dmodal.GetValue()

        if not footprint_enabled:
            logger.info("Skip Footprint & 3D Model Generate.")
            return

        if self.footprint_manager is None:
            logger.info(
                "Init Footprint Manager. Name: %s, Path: %s.",
                self.lib_name,
                self.lib_root)
            self.footprint_manager = FootprintManager(
                self.lib_root,
                self.lib_name
            )

        # check footprint exist or not
        t = self.footprint_manager.check_footprint(footprint_name)
        if t:
            logger.info("Found Footprint %s", footprint_name)
            answer = wx.MessageBox(
                "Footprint Already Exist.\nDo you want to Update?",
                "Confirm",
                wx.YES_NO | wx.CANCEL,
                self.frame
            )
            if answer != wx.YES:
                return

        footprint_data = self.component.gen_footprint_data(footprint_name)

        # 3d model
        if not model3d_enabled:
            logger.info("Skip 3D Model Generate.")
            # return

        model3d_data = footprint_data.c_3d_model    # type: ignore
        t = self.footprint_manager.check_3d_model(model3d_name)
        if t and model3d_data:
            logger.info("Found 3D Model %s", model3d_name)
            answer = wx.MessageBox(
                "3D Model Already Exist.\nDo you want to Update?",
                "Confirm",
                wx.YES_NO | wx.CANCEL,
                self.frame
            )
            if answer != wx.YES:
                model3d_data = None

        if model3d_data:
            self.footprint_manager.add_3d_model(
                model3d_name, model3d_data, True
            )
            model_path = self.footprint_manager.get_3d_model_ref_path(model3d_name)
            footprint_data.append(
                Model(
                    filename=model_path,
                    rotate=footprint_data.c_3d_model_rotation   # type: ignore
                )
            )

        self.footprint_manager.add_footprint(
            footprint_name, footprint_data, update=True
        )

    def check_lib_path(self):
        lib_name = self.frame.txt_lib_name.GetValue()

        if self.lib_name == "":
            wx.MessageBox(
                "Library name is empty", 'Error', wx.OK | wx.ICON_ERROR
            )
            return

        if lib_name != self.lib_name and lib_name != 'lcsc':
            self.save_lib_name(lib_name)
        self.lib_name = lib_name

        self.lib_root = self.frame.lib_path_picker.GetPath()
        if self.lib_root == "":
            wx.MessageBox(
                "Library path is empty", 'Error', wx.OK | wx.ICON_ERROR
            )
            return

    def do_component_gen(self, e):
        self.check_lib_path()

        symbol_name = self.frame.txt_symbol_name.GetValue()
        footprint_name = self.frame.txt_footprint_name.GetValue()
        model3d_name = self.frame.txt_3dmodel_name.GetValue()

        self.gen_symbol(symbol_name, footprint_name)
        self.gen_footprint(footprint_name, model3d_name)
        wx.MessageBox(
            "Component Generated.", 'Info', wx.OK | wx.ICON_INFORMATION
        )

    def do_load_component(self, e):
        ret = self.component.load_componnt()      # type: ignore
        if not ret:
            return

        self.enable_all_children(self.frame.symbol_footprint_sizer)
        self.calc_symbol_size()

        # footprint name
        self.frame.txt_footprint_name.SetValue(self.component.footprint_name)
        # symbol name
        self.frame.txt_symbol_name.SetValue(self.component.symbol_name)
        # 3d
        self.frame.txt_3dmodel_name.SetValue(self.component.model3d_name)

        # enable generate BTN
        self.frame.btn_gen.Enable()

    def check_box_clicked(self, parent, e):
        if e.IsChecked():
            self.enable_all_children(parent)
        else:
            self.disable_all_children(parent)

    def calc_symbol_size(self, e=None):
        scale = int(self.frame.select_symbol_scale.GetStringSelection())
        label_size = self.component.calc_symbol_size(scale)
        logger.debug("Symbol Size: %s, Scale: %s", label_size, scale)
        self.frame.txt_symbol_size.SetLabel(label_size)

    def hanndle_lib_path_changed(self, e):
        new_path = e.GetPath()
        if new_path == "":
            return

        if new_path != self.lib_root:
            logger.info("Change Library Root Path to <%s>", new_path)
            self.lib_root = new_path
            self.footprint_manager = None
            self.schematic_manager = None
            self.load_lib_name()

    def save_lib_name(self, name):
        lib_name_path = Path(self.lib_root).joinpath(".KLPM.conf")   # type: ignore
        lib_name_path.write_text(name)

    def load_lib_name(self):
        lib_name_path = Path(self.lib_root).joinpath(".KLPM.conf")   # type: ignore
        if lib_name_path.is_file():
            ctx = lib_name_path.read_text().strip()

            if ctx:
                self.frame.txt_lib_name.SetValue(ctx)

    def log_handler(self, msg):
        if not self.frame:
            return

        self.frame.txt_ctl_log.AppendText(msg)

    def load_part(self, lcid, lc_data=None, direct_part=False, source_easyeda=True):
        if direct_part:
            self.component = LCUUIDComponent(lcid, source_easyeda)
        else:
            self.component = LCComponent(lcid, lc_data)

        self.frame = LibManagerFrame(self.wx_parent, wx.ID_ANY, "")

        # Init Binds
        self.frame.btn_gen.Bind(wx.EVT_BUTTON, self.do_component_gen)
        self.frame.btn_load.Bind(wx.EVT_BUTTON, self.do_load_component)
        self.frame.select_symbol_scale.Bind(
            wx.EVT_COMBOBOX, self.calc_symbol_size
        )
        self.frame.cb_symbol.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.check_box_clicked(self.frame.symbol_conf_sizer, e)
        )
        self.frame.cb_footprint.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.check_box_clicked(self.frame.footprint_conf_sizer, e)
        )
        self.frame.cb_3dmodal.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.check_box_clicked(self.frame.model3d_conf_sizer, e)
        )

        self.frame.lib_path_picker.Bind(
            wx.EVT_DIRPICKER_CHANGED,
            self.hanndle_lib_path_changed)

        # init
        if self.lib_name is not None:
            self.frame.txt_lib_name.SetValue(self.lib_name)

        if self.lib_root is not None:
            self.frame.lib_path_picker.SetPath(self.lib_root)

        self.frame.SetTitle(f"Symbol & Footprint Export - {lcid}")

        # init log.
        if self.cx_handler is None:
            self.cx_handler = CMHandler(self.log_handler)
            self.cx_handler.setLevel(logging.INFO)
            logger.addHandler(self.cx_handler)

        logger.info("Symbol & Footprint Export")
        logger.info("Currnet Component: %s", lcid)

        self.disable_all_children(self.frame.symbol_footprint_sizer)

        t = self.frame.ShowModal()
        self.frame.Destroy()
        self.frame = None
