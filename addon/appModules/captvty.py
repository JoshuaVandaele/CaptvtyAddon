import time
from typing import Callable, List, Optional, Union

import api
import appModuleHandler
import controlTypes
import core
import speech
import ui
from gui import mainFrame
from logHandler import log
from NVDAObjects import NVDAObject
from scriptHandler import script
from speech.priorities import SpeechPriority
from wx import DateTime

from .modules.date_picker import DateRangeDialog
from .modules.helper_functions import (
    AppModes,
    click_element_with_mouse,
    click_position_with_mouse,
    fake_typing,
    find_element_by_size,
    scroll_and_click_on_element,
    scroll_to_element,
)
from .modules.list_elements import ElementsListDialog

# Constants
# Width of the channel list on the left side of the window, this constant is used to locate it on screen
CHANNEL_LIST_WIDTH = 263
# Offsets for the mouse when selecting an element
DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y = -20
DIRECT_CHANNEL_LIST_VIDEOPLAYER_BUTTON_OFFSET_X = 162
DIRECT_CHANNEL_LIST_RECORD_BUTTON_OFFSET_X = 185
# Amount of buttons at the top left with different modes for the app.
# There 3 modes at the time of writing are: Direct, Rattrapage, and Telechargement Manuel
MODE_BUTTONS_COUNT = 3


class AppModule(appModuleHandler.AppModule):
    def __init__(self, processID, appName=None):
        super().__init__(processID, appName)
        self.current_channel_rattrapage = None
        self.window = None

    def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """Handles the gainFocus event."""
        self.window = api.getForegroundObject()
        app_mode: AppModes = getAppMode()
        if app_mode == AppModes.DIRECT:
            ui.message("Menu direct sélectionné")
        elif app_mode == AppModes.RATTRAPAGE:
            ui.message("Menu rattrapage sélectionné")
        else:
            ui.message(
                "Sélectionnez un menu entre direct (CTRL+D) et rattrapage (CTRL+R)"
            )

        log.debug("-=== Captvty Focused ===-")
        nextHandler()

    def event_loseFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """Handles the loseFocus event."""
        log.debug("-=== Captvty Unfocused ===-")
        nextHandler()

    @script(gesture="kb:control+d")
    def script_CTRL_D_Override(self, gesture):
        """
        Overrides the default behavior of the CTRL+D keyboard shortcut
        with custom functionality.
        """
        buttons = getModeButtonList()
        if not buttons:
            log.error("We couldn't fetch the mode buttons!")
            return
        for button in buttons:
            if button.name == "DIRECT":
                button.doAction()
                ui.message("Menu direct sélectionné")
                break

    @script(gesture="kb:control+r")
    def script_CTRL_R_Override(self, gesture):
        """
        Overrides the default behavior of the CTRL+R keyboard shortcut
        with custom functionality.
        """
        buttons = getModeButtonList()
        if not buttons:
            log.error("We couldn't fetch the mode buttons!")
            return
        for button in buttons:
            if button.name == "RATTRAPAGE":
                button.doAction()
                ui.message("Menu rattrapage sélectionné")
                break

    @script(description="Liste les chaines.", gesture="kb:NVDA+L")
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
        if channelList and mainFrame:
            app_mode: AppModes = getAppMode()

            def selectedChannelCallback(
                selectedElement: Union[None, NVDAObject]
            ) -> None:
                nonlocal app_mode
                if not selectedElement:
                    return
                if app_mode == AppModes.RATTRAPAGE:
                    self._rattrapageSelectedChannelCallback(selectedElement)
                elif app_mode == AppModes.DIRECT:
                    self._directSelectedChannelCallback(selectedElement)
                else:
                    raise ValueError(
                        f"{app_mode} is not a supported operation.\n"
                        "The only supported operations are AppModes.RATTRAPAGE et AppModes.DIRECT"
                    )

            log.debug("Channel list focused")
            ui.message("Liste des chaines sélectionnée")
            mainFrame.prePopup()
            dialog = ElementsListDialog(
                mainFrame,
                channelList,
                callback=selectedChannelCallback,
                title="Liste des chaines",
            )
            dialog.Show()
            mainFrame.postPopup()
        else:
            ui.message(
                "Une erreur fatale s'est produite lors du chargement de la liste des chaînes"
            )
            log.error("Could not focus channel list: Channel list not found")

    def _directProgrammerEnregistrement(self, selectedElement):
        def _datepick_callback(start_date: DateTime, end_date: DateTime) -> None:
            start_date_str = start_date.Format("%Y-%m-%d %H:%M:%S")
            end_date_str = end_date.Format("%Y-%m-%d %H:%M:%S")

            log.debug(f"Start Date and Time: {start_date_str}")
            log.debug(f"End Date and Time: {end_date_str}")

            click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
                x_offset=DIRECT_CHANNEL_LIST_RECORD_BUTTON_OFFSET_X,
            )

            if not self.window:
                log.error("Could not find self.window")
                return

            window_location = self.window._get_location()

            window_horizontal_center = window_location.left + window_location.width // 2

            window_vertical_center = window_location.top + window_location.height // 2

            pos_ok_button = (
                window_horizontal_center - 80,
                window_vertical_center + 160,
            )

            pos_button_enregistrer = (
                window_horizontal_center,
                window_vertical_center - 90,
            )

            datepicker_field_positions = (
                window_horizontal_center - 70,
                window_horizontal_center - 45,
                window_horizontal_center - 15,
                window_horizontal_center + 10,
                window_horizontal_center + 50,
            )  # Format: HH:MM dd/mm/yyyy
            from_datepicker_vertical_center = window_vertical_center - 50
            from_dates = (
                f"{start_date.hour:02}",
                f"{start_date.minute:02}",
                f"{start_date.day:02}",
                f"{start_date.month:02}",
                f"{start_date.year:04}",
            )

            enregistrement_dialog_datepicker_vertical_center = (
                window_vertical_center + 30
            )
            to_dates = (
                f"{end_date.hour:02}",
                f"{end_date.minute:02}",
                f"{end_date.day:02}",
                f"{end_date.month:02}",
                f"{end_date.year:04}",
            )

            def _interact_with_enregistrement_dialog():
                click_position_with_mouse(pos_button_enregistrer)
                for i in range(len(from_dates)):
                    click_position_with_mouse(
                        (
                            datepicker_field_positions[i],
                            from_datepicker_vertical_center,
                        )
                    )
                    fake_typing(list(from_dates[i]))

                    click_position_with_mouse(
                        (
                            datepicker_field_positions[i],
                            enregistrement_dialog_datepicker_vertical_center,
                        )
                    )
                    fake_typing(list(to_dates[i]))
                click_position_with_mouse(pos_ok_button)

                def _onCompletion():
                    speech.cancelSpeech()
                    ui.message(
                        "Enregistrement programmé", speechPriority=SpeechPriority.NOW
                    )

                # There is a delay between doing actions and them being said out loud
                core.callLater(100, _onCompletion)

            # We need to wait for the short fade-in animation to be over
            core.callLater(100, _interact_with_enregistrement_dialog)

        if mainFrame:
            mainFrame.prePopup()
            dialog = DateRangeDialog(
                mainFrame,
                callback=_datepick_callback,
                title="Paramêtrer l'enregistrement",
            )
            dialog.Show()
            mainFrame.postPopup()

    def _directSelectViewOptionCallback(
        self, selectedElement: NVDAObject, selectedOption: str
    ):
        if selectedOption == "Programmer l'enregistrement":
            self._directProgrammerEnregistrement(selectedElement)
        elif selectedOption == "Visionner en direct avec le lecteur interne":
            click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
            )
        elif selectedOption == "Visionner en direct avec un lecteur externe":
            click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
                x_offset=DIRECT_CHANNEL_LIST_VIDEOPLAYER_BUTTON_OFFSET_X,
            )
        else:
            raise NotImplementedError

    def _directSelectedChannelCallback(self, selectedElement: NVDAObject):
        scroll_area = (
            selectedElement.parent.parent.parent  # type:ignore - Channels are assumed to always be in the channel list
        )
        scroll_to_element(
            element=selectedElement,
            max_attempts=30,
            scrollable_container=scroll_area,
        )
        if mainFrame:
            mainFrame.prePopup()
            dialog = ElementsListDialog(
                parent=mainFrame,
                elements=[
                    "Visionner en direct avec le lecteur interne",
                    "Visionner en direct avec un lecteur externe",
                    "Programmer l'enregistrement",
                ],
                callback=lambda option: self._directSelectViewOptionCallback(
                    selectedElement, option
                ),
                title="Choisissez une option",
                list_label="",
            )
            dialog.Show()
            mainFrame.postPopup()
        else:
            raise NotImplementedError

    def _rattrapageSelectedChannelCallback(self, selectedElement: NVDAObject):
        scroll_area = (
            selectedElement.parent.parent.parent  # type:ignore - Channels are assumed to always be in the channel list
        )

        if self.current_channel_rattrapage:
            # If the channel is already selectioned, ignore the request to select it
            if self.current_channel_rattrapage == selectedElement:
                return
            scroll_and_click_on_element(
                element=self.current_channel_rattrapage,
                scrollable_container=scroll_area,
                y_offset=-20,
            )
        self.current_channel_rattrapage = selectedElement
        scroll_and_click_on_element(
            element=selectedElement,
            max_attempts=30,
            scrollable_container=scroll_area,
            y_offset=-20,
        )
        # TODO: Open a list of programs with their name, time of diffusion, and description
        raise NotImplementedError("We cannot list programs yet in Rattrapage mode")


def getModeButtonList() -> Optional[List[NVDAObject]]:
    """
    Retrieves a list of mode buttons from the current foreground window.

    Returns:
        Optional[List[NVDAObject]]: A list of mode buttons as NVDAObjects,
        or None if the expected element hierarchy is not found.
    """
    window = api.getForegroundObject()

    if not hasattr(getModeButtonList, "_index_cache"):
        getModeButtonList._index_cache = 3

    # This is probably not the most efficient approach, however,
    # on computer restart the index changes at random,
    # and there is no other way that I know of to identify this element.
    for i in range(getModeButtonList._index_cache, len(window.children)):
        genericWindow = window.children[i]
        # The buttons are on top of the channel list,
        # And although they don't share a GenericWindow, they do share their width
        if genericWindow._get_location().width != CHANNEL_LIST_WIDTH:
            continue

        try:
            pane = genericWindow.children[3]
        except IndexError:
            continue

        mode_buttons = [
            button
            for pane_child in pane.children
            for button in pane_child.children
            if button.role == controlTypes.ROLE_BUTTON
        ]

        if len(mode_buttons) == MODE_BUTTONS_COUNT:
            getModeButtonList._index_cache = i
            log.debug(f"> Mode Button Index: {i}")  # Known range: 3, 4,
            return mode_buttons

    del getModeButtonList._index_cache
    return None


def getChannelButtonList() -> Optional[List[NVDAObject]]:
    """
    Gets the list of channel buttons.

    Returns:
        A list of NVDAObjects representing the channel buttons or None if not found.
    """
    elem = find_element_by_size(target_width=CHANNEL_LIST_WIDTH)
    if elem:
        for child in elem.children:
            if child.childCount >= 18:  # type: ignore - childCount is always defined for NVDAObject
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
        if button.location.left > right_most.location.left:  # type: ignore
            right_most = button

    if right_most.name == "DIRECT":
        return AppModes.DIRECT
    elif right_most.name == "RATTRAPAGE":
        return AppModes.RATTRAPAGE

    log.debugWarning(f"We didn't find DIRECT or RATTRAPAGE but {right_most.name}")
    return AppModes.OTHER
