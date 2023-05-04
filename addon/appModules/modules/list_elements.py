import wx
from gui import guiHelper
from typing import List, Callable, Optional
from NVDAObjects import NVDAObject

class ElementsListDialog(wx.Frame):
    def __init__(self, parent: wx.Window, elements: List[NVDAObject], callback: Optional[Callable[[Optional[NVDAObject]], None]] = None, title: str = "Elements List"):
        """
        A custom wx.Frame dialog that displays a list of elements for the user to select from.

        Args:
            parent (wx.Window): The parent window for the dialog.
            elements (List[NVDAObject]): A list of elements (NVDAObjects) to display in the dialog.
            callback (Optional[Callable[[NVDAObject], None]], optional): A callback function to be called when the user selects an element. Defaults to None.
            title (str, optional): The title of the dialog. Defaults to "Elements List".
        """
        super(ElementsListDialog, self).__init__(parent, title=title)

        self.elements = elements
        self.elements_names = [e.name for e in self.elements]
        self.callback = callback
        
        self.selectedElement = None

        self._createLayout()
        
        screen_width, screen_height = wx.DisplaySize()
        dialog_width, dialog_height = self.GetSize()
        position_x = screen_width - dialog_width
        position_y = screen_height - dialog_height
        self.SetPosition((position_x, position_y))

    def _createLayout(self) -> None:
        """Creates the dialog layout."""
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, "Sélectionnez un élément")
        mainSizer.Add(label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        self.elementsListBox = wx.ListBox(self, choices=self.elements_names, style=wx.LB_SINGLE)
        self.elementsListBox.SetSelection(0) # Set the default selection as the first one in the list
        mainSizer.Add(self.elementsListBox, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
        okButton = buttons.addButton(self, wx.ID_OK, label="OK")
        okButton.Bind(wx.EVT_BUTTON, self.onOk)
        buttons.addButton(self, wx.ID_CANCEL, label="Annuler")
        mainSizer.Add(buttons.sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        
        self.elementsListBox.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)

        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        self.elementsListBox.SetFocus()

    def onKeyPress(self, event: wx.KeyEvent) -> None:
        """
        Handles key press events in the dialog.

        Args:
            event (wx.KeyEvent): The key press event.

        Returns:
            None
        """
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.onOk(event)
        else:
            event.Skip()
            
    def onOk(self, event: wx.Event) -> None:
        """
        Handles the OK button click event.

        Args:
            event (wx.Event): The event associated with the OK button click.

        Returns:
            None
        """
        selectedIndex = self.elementsListBox.GetSelection()
        if selectedIndex != -1:
            self.selectedElement = self.elements[selectedIndex]
        self.Close()
        
        if self.callback:
            self.callback(self.selectedElement)
