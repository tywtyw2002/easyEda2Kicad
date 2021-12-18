import wx
import wx.dataview

import logging
import requests


logger = logging.getLogger("ADVSEARCH")


class AdvSearchFrame(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyDialog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetSize((700, 350))
        self.SetTitle("Adv. Search")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)

        self.txt_search = wx.TextCtrl(self, wx.ID_ANY, "")
        self.txt_search.SetMinSize((200, 25))
        sizer_2.Add(self.txt_search, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_search = wx.Button(self, wx.ID_ANY, "Search")
        sizer_2.Add(self.btn_search, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_2.Add((125, 25), 1, wx.EXPAND, 0)

        self.btn_close = wx.Button(self, wx.ID_ANY, "Close")
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close_press)
        sizer_2.Add(self.btn_close, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_3 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Search Results"), wx.VERTICAL)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)

        self.list_search_resutls = wx.dataview.DataViewListCtrl(
            self,
            wx.ID_ANY,
            style=wx.dataview.DV_ROW_LINES | wx.dataview.DV_SINGLE | wx.dataview.DV_HORIZ_RULES | wx.dataview.DV_VERT_RULES
        )
        self.list_search_resutls.AppendTextColumn("LCID", mode=wx.dataview.DATAVIEW_CELL_INERT, width=80)
        self.list_search_resutls.AppendTextColumn("Part No.", mode=wx.dataview.DATAVIEW_CELL_INERT, width=100)
        self.list_search_resutls.AppendTextColumn("Manufacturer", mode=wx.dataview.DATAVIEW_CELL_INERT, width=100)
        # self.list_search_resutls.AppendColumn("SMT", format=wx.LIST_FORMAT_LEFT, width=50)
        self.list_search_resutls.AppendToggleColumn("SMT", mode=wx.dataview.DATAVIEW_CELL_INERT, width=50)
        self.list_search_resutls.AppendTextColumn("Footprint", mode=wx.dataview.DATAVIEW_CELL_INERT, width=150)
        self.list_search_resutls.AppendTextColumn("Description", mode=wx.dataview.DATAVIEW_CELL_INERT, width=200)
        sizer_3.Add(self.list_search_resutls, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_1)

        self.Layout()

    def on_btn_close_press(self, e):
        self.EndModal(wx.CANCEL)


class AdvSearchControl:

    def __init__(self, wx_parent):
        self.wx_parent = wx_parent
        self.frame = None
        self.lcsc_part = None
        self.ret_status = None
        self.last_result =None

    def request_part_from_eda(self, value):
        payload = {
            'type': 3,
            'doctype[]': 2,
            'returnListStyle': 'classifyarr',
            'wd': value
        }
        r = requests.post(
            "https://easyeda.com/api/components/search",
            data=payload
        )
        data = r.json()

        if data['code'] != 0:
            wx.MessageBox(
                f"Error: API code {data['code']}.\n Msg: {data['message']}", 'Error', wx.OK | wx.ICON_ERROR
            )
            return None

        return data['result']['lists']['lcsc']

    def do_part_search(self, e):
        value = self.frame.txt_search.GetValue().strip()

        if value == "":
            wx.MessageBox(
                "Cannot search empty.", 'Error', wx.OK | wx.ICON_ERROR
            )
            return

        self.frame.list_search_resutls.DeleteAllItems()
        results = self.request_part_from_eda(value)

        if results is None:
            return

        if len(results) == 0:
            wx.MessageBox(
                "No Result.", 'Info', wx.OK | wx.ICON_INFORMATION
            )
            return

        self.last_result = results
        for record in results:
            c_para = record['dataStr']['head']['c_para']
            data = [
                c_para['BOM_Supplier Part'],
                c_para['name'],
                c_para.get('BOM_Manufacturer', ""),
                record.get('SMT', False),
                c_para['package'],
                record['description'] or record.get('tags', [""])[0]
            ]
            self.frame.list_search_resutls.AppendItem(data)

    def on_item_double_click(self, e):
        item = e.GetItem()
        model = e.GetModel()
        if item and model:
            part = model.GetValue(item, 0)
            status = wx.MessageBox(
                f"Search {part}?", 'Info', wx.YES_NO
            )
            if status != wx.YES:
                return
            self.lcsc_part = part
            # print(self.lcsc_part)
            self.frame.EndModal(wx.OK)

    def show(self):
        if self.frame is None:
            self.frame = AdvSearchFrame(self.wx_parent, wx.ID_ANY, "")
            self.frame.btn_search.Bind(wx.EVT_BUTTON, self.do_part_search)
            self.frame.list_search_resutls.Bind(
                wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED,
                self.on_item_double_click
            )

        self.lcsc_part = None
        t = self.frame.ShowModal()

        # self.frame.Destroy()
        # self.frame = None
        return t