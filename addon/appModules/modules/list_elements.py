from typing import Any, Callable, List, Optional, Union

import wx
from gui import guiHelper
from NVDAObjects import NVDAObject
from NVDAObjects.IAccessible import IAccessible


class ElementsListDialog(wx.Frame):
    """A custom wx.Frame dialog that displays a list of elements for the user to select from."""

    def __init__(
        self,
        parent: wx.Window,
        elements: List[Any],
        element_name_getter: Optional[Callable[[Any], Union[str, None]]] = None,
        callback: Optional[Callable[[Any], None]] = None,
        title: str = "Liste d'éléments",
        list_label: str = "Sélectionnez un élément",
        max_displayed_elements: int = 100,
    ) -> None:
        """
        Initialize the ElementsListDialog instance.

        Args:
            parent (wx.Window): The parent window for the dialog.
            elements (List[Any]): A list of elements to display in the dialog.
            element_name_getter (Callable[[Any], Union[str, None]], optional): A function which returns a string representation for a given element. Defaults to None.
            callback (Callable[[Any], None], optional): A callback function to be called when the user selects an element. Defaults to None.
            title (str, optional): The title of the dialog. Defaults to "Liste d'éléments".
            list_label (str, optional): The label of the list. Defaults to "Sélectionnez un élément".
            max_displayed_elements (int, optional): The maximum number of elements to display.
        """
        super(ElementsListDialog, self).__init__(parent, title=title)

        self.list_label = list_label

        self.empty_list = not elements
        self.elements = elements or ["Liste vide"]
        self.element_name_getter = (
            element_name_getter or ElementsListDialog._get_element_name
        )

        self.element_names = [
            self.element_name_getter(element) or str(element)
            for element in self.elements
        ]
        self.element_indices = list(range(len(self.element_names)))
        self.callback = callback

        self.max_displayed_elements = max_displayed_elements

        self.selectedElement = None

        self._createLayout()

        screen_width, screen_height = wx.DisplaySize()
        dialog_width, dialog_height = self.GetSize()
        position_x = screen_width - dialog_width
        position_y = screen_height - dialog_height
        self.SetPosition((position_x, position_y))

    @staticmethod
    def _get_element_name(element: Any) -> Union[str, None]:
        """Return the name of the element if it is an NVDAObject or an IAccessible.

        Args:
            element (Any): The element to get the name of.

        Returns:
            Union[str, None]: The name of the element or None if the element does not have a name.
        """
        if isinstance(element, (NVDAObject, IAccessible)):
            return element.name

    def _createLayout(self) -> None:
        """Create and set the layout for the dialog."""
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, self.list_label)
        mainSizer.Add(label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        self.searchCtrl = wx.SearchCtrl(self)
        self.searchCtrl.Bind(wx.EVT_TEXT, self.onSearch)
        mainSizer.Add(
            self.searchCtrl, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )

        self.elementsListBox = wx.ListBox(
            self, choices=self.element_names, style=wx.LB_SINGLE
        )
        self.elementsListBox.SetSelection(
            0
        )  # Set the default selection as the first one in the list
        mainSizer.Add(
            self.elementsListBox,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            border=8,
        )

        buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
        okButton = buttons.addButton(self, wx.ID_OK, label="OK")
        okButton.Bind(wx.EVT_BUTTON, self.onOk)
        cancelButton = buttons.addButton(self, wx.ID_CANCEL, label="Annuler")
        cancelButton.Bind(wx.EVT_BUTTON, self.Close)
        mainSizer.Add(
            buttons.sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8
        )

        self.elementsListBox.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)
        self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        self.elementsListBox.SetFocus()

    def onCharHook(self, event: wx.KeyEvent) -> None:
        """
        Handles the event when the user presses any key in the dialog.

        Args:
            event (wx.KeyEvent): The key press event.

        Returns:
            None
        """
        keycode = event.GetKeyCode()

        if keycode in range(32, 127):
            self.searchCtrl.AppendText(chr(keycode))
        elif keycode in range(wx.WXK_NUMPAD0, wx.WXK_NUMPAD9 + 1):
            self.searchCtrl.AppendText(str(keycode - wx.WXK_NUMPAD0))
        elif keycode in [wx.WXK_BACK, wx.WXK_DELETE]:
            search = self.searchCtrl.GetValue()
            self.searchCtrl.ChangeValue(search[:-1])
        else:
            event.Skip()
            return
        self.onSearch(event)

    def onSearch(self, event: Union[wx.Event, None] = None) -> None:
        """
        Handles the event when the user types in the search box.

        Args:
            event (wx.Event | None): The event associated with the search box, if any.

        Returns:
            None
        """
        search_text = self.searchCtrl.GetValue().lower()

        matching_elements = []

        if search_text:
            self.element_indices.clear()
            for index, element_name in enumerate(self.element_names):
                if search_text in element_name.lower():
                    matching_elements.append(element_name)
                    self.element_indices.append(index)

                    if len(matching_elements) >= self.max_displayed_elements:
                        break
        else:
            self.element_indices = list(range(self.max_displayed_elements))
            matching_elements = self.element_names[: self.max_displayed_elements]

        self.elementsListBox.Set(matching_elements)

    def onKeyPress(self, event: wx.KeyEvent) -> None:
        """
        Handles key press events in the dialog.

        Args:
            event (wx.KeyEvent): The key press event.

        Returns:
            None
        """
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_RETURN:
            self.onOk(event)
        elif keyCode == wx.WXK_ESCAPE:
            self.Close()
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
        self.Close()
        if not self.callback:
            return
        selectedIndex = self.elementsListBox.GetSelection()
        if selectedIndex != -1:
            self.selectedElement = self.elements[self.element_indices[selectedIndex]]

        self.callback(self.selectedElement)

    def appendElement(self, element: Any) -> None:
        """Appends an element to the ListBox.

        Args:
            element (Any): The element to append.
        """
        self.elements.append(element)

        element_name = self.element_name_getter(element) or str(element)

        self.element_names.append(element_name)

        if self.empty_list:
            self.empty_list = False
            self.removeElement(0)
        self.onSearch()

    def appendElements(self, elements: List[Any]) -> None:
        """Appends a list of element to the ListBox.

        Args:
            elements (List[Any]): The element to append.
        """
        new_element_names = [
            self.element_name_getter(element) or str(element) for element in elements
        ]

        self.elements.extend(elements)
        self.element_names.extend(new_element_names)

        if self.empty_list:
            self.empty_list = False
            self.removeElement(0)
        self.onSearch()

    def removeElement(self, index: int) -> None:
        """Remove an element from the ListBox at the given index.

        Args:
            index (int): The index of the element to remove.
        """
        self.elementsListBox.Delete(index)
        self.elements.pop(index)
        self.element_names.pop(index)
