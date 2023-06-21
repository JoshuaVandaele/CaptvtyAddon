import threading
from typing import Any, Callable, List, Optional, Union

import wx
from gui import guiHelper
from logHandler import log
from NVDAObjects import NVDAObject
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.IAccessible.sysListView32 import ListItem

from .helper_functions import normalize_str, reacquire_element


class VirtualList(wx.ListCtrl):
    """
    A custom wx.ListCtrl that supports virtual mode.
    """

    def __init__(self, parent, data):
        """
        Initialize the VirtualList instance.

        Args:
            parent (wx.Window): The parent window for the list.
            data (List[Any]): A list of data to display in the list.
        """
        wx.ListCtrl.__init__(
            self, parent, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL
        )
        self.data = data
        self.SetItemCount(len(data))

        # Add columns
        self.InsertColumn(0, "Name")

    def OnGetItemText(self, item, col):
        """
        Get the text for a specific item and column.

        Args:
            item (int): The index of the item.
            col (int): The index of the column.

        Returns:
            str: The text for the specified item and column.
        """
        if col == 0:
            return self.data[item]


class ElementsListDialog(wx.Frame):
    """
    A custom wx.Frame dialog that displays a list of elements for the user to select from.
    """

    def __init__(
        self,
        parent: wx.Window,
        elements: List[Any],
        element_name_getter: Optional[Callable[[Any], Union[str, None]]] = None,
        callback: Optional[Callable[[Any], None]] = None,
        title: str = "Liste d'éléments",
        list_label: str = "Sélectionnez un élément",
        max_displayed_elements: int = 100,
        search_delay: int = 500,
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
            max_displayed_elements (int, optional): The maximum number of elements to display at once. Defaults to 100.
            search_delay (int, optional): The delay in milliseconds before the search is performed after the user stops typing. Defaults to 500.
        """
        super(ElementsListDialog, self).__init__(parent, title=title)

        self.lock = threading.Lock()
        self.is_closed = False

        self.list_label = list_label
        self.search_delay = search_delay
        self.empty_list = not elements
        self.elements = elements or ["Liste vide"]
        element_name_getter = (
            element_name_getter or ElementsListDialog._get_element_name
        )
        self.element_name_getter = lambda x: element_name_getter(x) or str(x)
        self.element_names = [
            self.element_name_getter(element) for element in self.elements
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
        self.Bind(wx.EVT_ACTIVATE, self.onActivate)

    @staticmethod
    def _get_element_name(element: Any) -> Union[str, None]:
        """Return the name of the element if it is an NVDAObject or an IAccessible.

        Args:
            element (Any): The element to get the name of.

        Returns:
            Union[str, None]: The name of the element or None if the element does not have a name.
        """
        if isinstance(element, (NVDAObject, IAccessible, ListItem)):
            return element._get_name()

    def _createLayout(self) -> None:
        """
        Create and set the layout for the dialog.
        """
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, self.list_label)
        mainSizer.Add(label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        self.searchCtrl = wx.SearchCtrl(self)

        self.searchTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onSearch, self.searchTimer)

        mainSizer.Add(
            self.searchCtrl, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )

        self.elementsListBox = VirtualList(self, self.element_names)
        self.elementsListBox.SetItemCount(len(self.element_names))
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

    def onActivate(self, event: wx.ActivateEvent) -> None:
        """
        Handles the EVT_ACTIVATE event when the window loses activation.

        Args:
            event (wx.ActivateEvent): The activate event.

        Returns:
            None
        """
        if not event.GetActive():
            self.Close()

    def onCharHook(self, event: wx.KeyEvent) -> None:
        """
        Handles the event when the user presses any key in the dialog.

        Args:
            event (wx.KeyEvent): The key press event.

        Returns:
            None
        """
        keycode = event.GetKeyCode()
        unicode_keycode = event.GetUnicodeKey()

        if keycode in [wx.WXK_BACK, wx.WXK_DELETE]:
            search = self.searchCtrl.GetValue()
            self.searchCtrl.ChangeValue(search[:-1])
        elif keycode == wx.WXK_ESCAPE:
            self.Close()
        elif keycode == wx.WXK_RETURN:
            self.onOk(event)
        elif unicode_keycode != wx.WXK_NONE:
            self.searchCtrl.AppendText(chr(unicode_keycode))
        else:
            event.Skip()
            return

        if self.searchTimer.IsRunning():
            self.searchTimer.Stop()
        self.searchTimer.Start(self.search_delay, oneShot=True)

    def onSearch(self, event: Union[wx.Event, None] = None) -> None:
        """
        Handles the event when the user types in the search box.

        Args:
            event (wx.Event | None): The event associated with the search box, if any.

        Returns:
            None
        """
        search_text = normalize_str(self.searchCtrl.GetValue().lower())

        matching_elements = []

        if search_text:
            self.element_indices.clear()
            for index, element_name in enumerate(self.element_names):
                normalized_element_name = normalize_str(element_name.lower())
                if search_text in normalized_element_name:
                    matching_elements.append(element_name)
                    self.element_indices.append(index)

                    if len(matching_elements) >= self.max_displayed_elements:
                        break
        else:
            self.element_indices = list(range(self.max_displayed_elements))
            matching_elements = self.element_names[: self.max_displayed_elements]

        self.elementsListBox.data = matching_elements
        self.elementsListBox.SetItemCount(len(matching_elements))

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
        if not self.callback or self.empty_list:
            return
        selectedIndex = self.elementsListBox.GetFirstSelected()
        if selectedIndex != -1:
            self.selectedElement = self.elements[self.element_indices[selectedIndex]]

        self.callback(self.selectedElement)

    def Close(self, event: Union[wx.Event, None] = None) -> None:
        """
        Handles the close event of the dialog.

        Args:
            event (wx.Event): The event associated with the close action. Defaults to None.

        Returns:
            None
        """
        self.is_closed = True
        if self.searchTimer.IsRunning():
            self.searchTimer.Stop()
        super().Close()

    def appendElement(self, element: Any) -> None:
        """
        Appends an element to the ListBox.

        Args:
            element (Any): The element to append.
        """
        self.elements.append(element)

        element_name = self.element_name_getter(element)

        self.element_names.append(element_name)

        if self.empty_list:
            self.empty_list = False
            self.elements.pop()
        self.onSearch()

    def appendElements(self, elements: List[Any]) -> None:
        """Appends a list of elements to the ElementsListDialog.

        Args:
            elements (List[Any]): The elements to append.
        """

        def worker(elements):
            """Worker thread to append elements to the ElementsListDialog."""
            with self.lock:
                new_element_names = []

                for element in elements:
                    if self.is_closed:
                        return
                    if isinstance(element, IAccessible):
                        element = reacquire_element(element)

                    self.element_names.append(self.element_name_getter(element))

                self.elements.extend(elements)

                if self.empty_list:
                    self.empty_list = False
                    self.removeElement(0)

            if self.is_closed:
                return
            wx.CallAfter(self.onSearch)

        threading.Thread(target=worker, args=(elements,)).start()

    def removeElement(self, index: int) -> None:
        """
        Remove an element from the ListBox at the given index.

        Args:
            index (int): The index of the element to remove.
        """
        self.elements.pop(index)
        self.element_names.pop(index)
        self.onSearch()
