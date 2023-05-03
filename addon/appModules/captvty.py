import appModuleHandler
from logHandler import log
import ui
from scriptHandler import script
from NVDAObjects import NVDAObject
from typing import Union, List, Optional, Callable
import api
from gui import mainFrame

from .modules.helper_functions import find_element_by_size, click_element_with_mouse, scroll_to_element
from .modules.list_elements import ElementsListDialog

CHANNEL_LIST_WIDTH = 263

class AppModule(appModuleHandler.AppModule):
    def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """Handles the gainFocus event."""
        log.debug("-=== Captvty Focused ===-")
        nextHandler()

    def event_loseFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """Handles the loseFocus event."""
        log.debug("-=== Captvty Unfocused ===-")
        nextHandler()

    @script(
        description="Liste les chaines.",
        gesture="kb:NVDA+L"
    )
    def script_ChannelList(self, gesture: Union[str, None]) -> None:
        """
        Displays a dialog with the channels to select from and selects it.

        Args:
            gesture: The gesture that triggered the script. Can be a string or None.

        Returns:
            None
        """
        channelList: Union[List[NVDAObject], None] = getChannelButtonList()
        log.debug(f"channelList: {channelList}")
        if channelList:
            def selectedChannelCallback(selectedElement: Union[None, NVDAObject]) -> None:
                if selectedElement:
                    scroll_to_element(selectedElement, api.getForegroundObject())
                    click_element_with_mouse(selectedElement, y_offset=-20)
            log.debug("Channel list focused")
            ui.message("Liste des chaines sélectionnée")
            mainFrame.prePopup() # type: ignore - prePopup is known and defined
            dialog = ElementsListDialog(mainFrame, channelList, callback=selectedChannelCallback, title="Liste des chaines")
            dialog.Show()
            mainFrame.postPopup() # type: ignore - postPopup is known and defined
        else:
            log.error("Could not focus channel list: Channel list not found")
            
def getChannelButtonList() -> Optional[List[NVDAObject]]:
    """
    Gets the list of channel buttons.

    Returns:
        A list of NVDAObjects representing the channel buttons or None if not found.
    """
    elem = find_element_by_size(target_width=CHANNEL_LIST_WIDTH)
    if elem:
        for child in elem.children:
            if child.childCount >= 18: # type: ignore - childCount is always defined for NVDAObject
                channel_list = child.children
                return [channel.children[3].children[1] for channel in channel_list]
    return None
