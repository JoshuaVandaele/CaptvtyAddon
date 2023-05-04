import appModuleHandler
from logHandler import log
import ui
from scriptHandler import script
from NVDAObjects import NVDAObject
from typing import Union, List, Optional, Callable, Dict
from gui import mainFrame
import api

from .modules.helper_functions import find_element_by_size, scroll_and_click_on_element, find_element_by_name, AppModes, scroll_to_element
from .modules.list_elements import ElementsListDialog

# Constants
# Width of the channel list on the left side of the window, this constant is used to locate it on screen
CHANNEL_LIST_WIDTH = 263

class AppModule(appModuleHandler.AppModule):
    def __init__(self, processID, appName=None):
        super().__init__(processID, appName)
        self.current_channel_rattrapage = None
        
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
        ui.message("Chargement de la liste des chaines")
        channelList: Union[List[NVDAObject], None] = getChannelButtonList()
        log.debug(f"channelList: {channelList}")
        if channelList:
            app_mode: AppModes = getAppMode()
            def selectedChannelCallback(selectedElement: Union[None, NVDAObject]) -> None:
                nonlocal app_mode
                if not selectedElement:
                    return
                scroll_area = selectedElement.parent.parent.parent # type:ignore - Channels are assumed to always be in the channel list
                if app_mode == AppModes.RATTRAPAGE:
                    if self.current_channel_rattrapage:
                        # If the channel is already selectioned, ignore the request to select it
                        if self.current_channel_rattrapage == selectedElement:
                            return
                        scroll_and_click_on_element(self.current_channel_rattrapage, scrollable_container=scroll_area, y_offset=-20)
                    self.current_channel_rattrapage = selectedElement
                    scroll_and_click_on_element(selectedElement, max_attempts=30, scrollable_container=scroll_area, y_offset=-20)
                    # TODO: Open a list of programs with their name, time of diffusion, and description
                    raise NotImplementedError("We cannot list programs yet in Rattrapage mode")
                elif app_mode == AppModes.DIRECT:
                    scroll_to_element(selectedElement, max_attempts=30, scrollable_container=scroll_area)
                    # TODO: Prompt the user to know if they want to watch the channel, or record it
                    raise NotImplementedError("We cannot select a channel yet in Direct mode")
                else:
                    raise ValueError(f"{app_mode} is not a supported operation.\nThe only supported operations are AppModes.RATTRAPAGE et AppModes.DIRECT")

            log.debug("Channel list focused")
            ui.message("Liste des chaines sélectionnée")
            mainFrame.prePopup() # type: ignore - prePopup is known and defined
            dialog = ElementsListDialog(mainFrame, channelList, callback=selectedChannelCallback, title="Liste des chaines")
            dialog.Show()
            mainFrame.postPopup() # type: ignore - postPopup is known and defined
        else:
            ui.message("Une erreur fatale s'est produite lors du chargement de la liste des chaînes")
            log.error("Could not focus channel list: Channel list not found")

def getModeButtonList() -> Optional[List[NVDAObject]]:
    """
    Retrieves a list of mode buttons from the current foreground window.

    Returns:
        Optional[List[NVDAObject]]: A list of mode buttons as NVDAObjects,
        or None if the expected element hierarchy is not found.
    """
    window = api.getForegroundObject()
    
    elem = window.children[3].children[3]

    return list(elem.children)


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

def getAppMode() -> AppModes:
    """
    Determines the current application mode by examining the state of mode buttons.

    Returns:
        AppModes: An enum value representing the current application mode.
            - AppModes.DIRECT if the right-most button's name is "DIRECT"
            - AppModes.RATTRAPAGE if the right-most button's name is "RATTRAPAGE"
            - AppModes.OTHER if the right-most button has a different name or the list of buttons is not found
    """
    buttons = getModeButtonList()
    if not buttons:
        log.debugWarning("We couldn't find the mode buttons")
        return AppModes.OTHER

    right_most = buttons[0]
    for button in buttons[1:]:
        if button.location.left > right_most.location.left:
            right_most = button

    if right_most.name == "DIRECT":
        return AppModes.DIRECT
    elif right_most.name == "RATTRAPAGE":
        return AppModes.RATTRAPAGE
    
    log.debugWarning(f"We didn't find DIRECT or RATTRAPAGE but instead {right_most.name}")
    return AppModes.OTHER
