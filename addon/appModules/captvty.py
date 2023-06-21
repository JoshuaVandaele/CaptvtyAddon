from typing import Callable, Dict, List, Optional, Union

import api
import appModuleHandler
import controlTypes
import core
import speech
import ui
from gui import mainFrame
from logHandler import log
from NVDAObjects import NVDAObject
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script
from speech.priorities import SpeechPriority
from wx import DateTime

from .modules.date_picker import DateRangeDialog
from .modules.exceptions import (
    ButtonListPaneNotAvailableError,
    ChannelListNotAvailableError,
    InvalidElementRoleError,
    WindowNotAvailableError,
)
from .modules.helper_functions import (
    AppModes,
    click_position_with_mouse,
    fake_typing,
    hover_element_with_mouse,
    left_click_element_with_mouse,
    right_click_element_with_mouse,
    scroll_and_click_on_element,
    scroll_to_element,
)
from .modules.list_elements import ElementsListDialog
from .modules.program import Program

# Constants
# Offsets for the mouse when selecting an element
DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y = -20
DIRECT_CHANNEL_LIST_VIDEOPLAYER_BUTTON_OFFSET_X = 162
DIRECT_CHANNEL_LIST_RECORD_BUTTON_OFFSET_X = 185
# Number of elements to skip from the program list
# due to them not being elements of the list but header controls for the list
RATTRAPAGE_PROGRAM_LIST_HEADER_CONTROL_COUNT = 7


class AppModule(appModuleHandler.AppModule):
    """Application module for Captvty."""

    def __init__(self, processID, appName=None) -> None:
        """
        Initialize the AppModule.

        Args:
            processID (int): The ID of the process.
            appName (str): The name of the application.
        """
        super().__init__(processID, appName)
        self.current_channel_rattrapage = None
        self.window = None

    def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """
        Handles the gainFocus event.

        Args:
            obj (NVDAObject): The NVDAObject that gained focus.
            nextHandler (Callable): The next event handler to call.
        """
        self.window = api.getForegroundObject()

        log.debug("-=== Captvty Focused ===-")
        nextHandler()

    def event_loseFocus(self, obj: NVDAObject, nextHandler: Callable) -> None:
        """
        Handles the loseFocus event.

        Args:
            obj (NVDAObject): The NVDAObject that gained focus.
            nextHandler (Callable): The next event handler to call.
        """
        log.debug("-=== Captvty Unfocused ===-")
        nextHandler()

    def doModeButtonAction(self, button_name: str):
        """
        Tries to find and activate a button from the mode button list.

        Args:
            button_name (str): The name of the button to activate.
        """
        try:
            buttons = self.getModeButtonList()
            button = buttons.get(button_name)
            if button is not None:
                button.doAction()
                ui.message(f"Menu {button_name} sélectionné")
            else:
                ui.message(
                    f"Nous n'avons pas pu sélectionner le menu {button_name.lower()}"
                )
                log.error(f"We couldn't fetch the {button_name.lower()} button!")
        except Exception as e:
            ui.message(
                f"Nous n'avons pas pu sélectionner le menu {button_name.lower()}"
            )
            log.error(f"We couldn't fetch the mode buttons: {e}")

    @script(gesture="kb:control+d")
    def script_CTRL_D_Override(self, gesture):
        """
        Overrides the default behavior of the CTRL+D keyboard shortcut
        to select the Direct mode.

        Args:
            gesture (str): The gesture that triggered the script.
        """
        self.doModeButtonAction("DIRECT")

    @script(gesture="kb:control+r")
    def script_CTRL_R_Override(self, gesture):
        """
        Overrides the default behavior of the CTRL+R keyboard shortcut
        to select the Rattrapage mode.

        Args:
            gesture (str): The gesture that triggered the script.
        """
        self.doModeButtonAction("RATTRAPAGE")

    @script(gesture="kb:control+t")
    def script_CTRL_T_Override(self, gesture):
        """
        Creates a new CTRL+T keyboard shortcut which opens the Telechargement menu.

        Args:
            gesture (str): The gesture that triggered the script.
        """
        self.doModeButtonAction("TÉLÉCHARGEMENT\nMANUEL")

    @script(description="Liste les chaines.", gesture="kb:NVDA+L")
    def script_ChannelList(self, gesture: str) -> None:
        """
        Displays a dialog with the channels to select from and selects it.

        Args:
            gesture (str): The gesture that triggered the script.
        """
        ui.message("Chargement de la liste des chaines")
        try:
            channelList: Union[List[NVDAObject], None] = self.getChannelButtonList()
        except Exception as e:
            ui.message(
                "Une erreur s'est produite lors du chargement de la liste des chaînes"
            )
            log.error(f"Could not load channel list: {e}")
            return
        if not channelList:
            ui.message(
                "Une erreur fatale s'est produite lors du chargement de la liste des chaînes"
            )
            log.error("Could not focus channel list: Channel list not found")
            return
        if not mainFrame:
            ui.message("Une erreur fatale s'est produite: mainFrame n'a pas été trouvé")
            log.error("Could not focus channel list: mainFrame not found")
            return
        app_mode: AppModes = self.getAppMode()

        def selectedChannelCallback(selectedElement: Union[None, NVDAObject]) -> None:
            """
            Callback function for the selected channel.

            Args:
                selectedElement (NVDAObject or None): The selected NVDAObject representing the channel.
            """
            nonlocal app_mode
            if not selectedElement:
                return
            if app_mode == AppModes.RATTRAPAGE:
                self._rattrapageSelectedChannelCallback(selectedElement)
            elif app_mode == AppModes.DIRECT:
                self._directSelectedChannelCallback(selectedElement)
            else:
                ui.message(
                    "Une erreur fatale s'est produite: Vous pouvez seulement sélectionner une chaine en mode direct ou rattrapage."
                )
                raise ValueError(
                    f"{app_mode} is not a supported operation.\n"
                    "The only supported operations are AppModes.RATTRAPAGE et AppModes.DIRECT"
                )

        mainFrame.prePopup()
        dialog = ElementsListDialog(
            mainFrame,
            channelList,
            callback=selectedChannelCallback,
            title="Liste des chaines",
        )
        dialog.Show()
        log.debug("Channel list focused")
        ui.message("Liste des chaines sélectionnée")
        mainFrame.postPopup()

    def _directProgrammerEnregistrement(self, selectedElement):
        """
        Handles the process of programming an Enregistrement in Direct mode.

        Args:
            selectedElement: The selected NVDAObject representing the element.
        """

        def _datepick_callback(start_date: DateTime, end_date: DateTime) -> None:
            """
            Callback function for the selected start and end dates.

            Args:
                start_date: The selected start date and time.
                end_date: The selected end date and time.
            """
            start_date_str = start_date.Format("%Y-%m-%d %H:%M:%S")
            end_date_str = end_date.Format("%Y-%m-%d %H:%M:%S")

            log.debug(f"Start Date and Time: {start_date_str}")
            log.debug(f"End Date and Time: {end_date_str}")

            left_click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
                x_offset=DIRECT_CHANNEL_LIST_RECORD_BUTTON_OFFSET_X,
            )

            if not self.window:
                ui.message(
                    "Une erreur fatale s'est produite: La fenêtre captvty n'a pas été trouvée"
                )
                raise WindowNotAvailableError

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
                """
                Performs the interactions with the enregistrement dialog.
                """
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
        """
        Callback for once the user has selected a view option in Direct mode.

        Args:
            selectedElement: The selected NVDAObject representing the element.
            selectedOption: The selected option.
        """
        if selectedOption == "Programmer l'enregistrement":
            self._directProgrammerEnregistrement(selectedElement)
        elif selectedOption == "Visionner en direct avec le lecteur interne":
            left_click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
            )
        elif selectedOption == "Visionner en direct avec un lecteur externe":
            left_click_element_with_mouse(
                element=selectedElement,
                y_offset=DIRECT_CHANNEL_LIST_VIEW_BUTTON_OFFSET_Y,
                x_offset=DIRECT_CHANNEL_LIST_VIDEOPLAYER_BUTTON_OFFSET_X,
            )
        else:
            ui.message("Une erreur fatale s'est produite: option invalide sélectionnée")
            raise NotImplementedError

    def _directSelectedChannelCallback(self, selectedElement: NVDAObject):
        """
        Callback for when the user has selected a channel in Direct mode.

        Args:
            selectedElement: The selected NVDAObject representing the element.
        """
        scroll_area = (
            selectedElement.parent.parent.parent  # type:ignore - Channels are assumed to always be in the channel list
        )
        scroll_to_element(
            element=selectedElement,
            max_attempts=30,
            scrollable_container=scroll_area,
            bounds_offset=(0, 0, 250, 250),
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
            ui.message("Une erreur fatale s'est produite: mainFrame n'est pas définie")
            raise NotImplementedError

    def _rattrapageSelectViewOptionCallback(
        self, selectedProgramElement: NVDAObject, selectedOption: str
    ):
        """
        Callback for once the user has selected a view option in Rattrapage mode.

        Args:
            selectedProgramElement: The selected NVDAObject representing the program element.
            selectedOption: The selected option.
        """
        if not self.window:
            ui.message(
                "Une erreur fatale s'est produite: La fenêtre captvty n'a pas été trouvée"
            )
            raise WindowNotAvailableError
        window_height = self.window._get_location().height
        selectedProgramElement_width = selectedProgramElement.location.width

        x_hover_offset = -(selectedProgramElement_width // 2) + 50

        scroll_to_element(
            element=selectedProgramElement,
            scrollable_container=selectedProgramElement.parent,
            max_attempts=10000,
            bounds_offset=(0, 0, window_height // 2, window_height // 2),
            x_offset=0,  # x_hover_offset,
        )

        selectedProgramElement.invalidateCache()
        selectedProgramElement.invalidateCaches()

        right_click_element_with_mouse(
            element=selectedProgramElement,
            x_offset=x_hover_offset,
        )
        ui.message(f"Selection: {selectedProgramElement.name} - {selectedOption}")
        if selectedOption == "Télécharger":
            left_click_element_with_mouse(
                element=selectedProgramElement,
                x_offset=x_hover_offset + 10,
                y_offset=20,
            )
        elif selectedOption == "Visionner avec le lecteur intégré":
            left_click_element_with_mouse(
                element=selectedProgramElement,
                x_offset=x_hover_offset + 10,
                y_offset=60,
            )
        elif selectedOption == "Visionner sur le site web":
            left_click_element_with_mouse(
                element=selectedProgramElement,
                x_offset=x_hover_offset + 10,
                y_offset=100,
            )
        elif selectedOption == "Copier l'adresse de l'émission":
            left_click_element_with_mouse(
                element=selectedProgramElement,
                x_offset=x_hover_offset + 10,
                y_offset=120,
            )
        else:
            ui.message(
                f"Une erreur fatale s'est produite: option invalide sélectionnée ({selectedOption})"
            )
            raise NotImplementedError
        selectedProgramElement.setFocus()
        api.setFocusObject(selectedProgramElement)

    def _rattrapageSelectedChannelCallback(self, selectedElement: NVDAObject):
        """
        Callback for when the user has selected a channel in Rattrapage mode.

        Args:
            selectedElement: The selected NVDAObject representing the element.
        """
        scroll_area = (
            selectedElement.parent.parent.parent  # type:ignore - Channels are assumed to always be in the channel list
        )

        if self.current_channel_rattrapage:
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
        if not self.window:
            ui.message(
                "Une erreur fatale s'est produite: La fenêtre captvty n'a pas été trouvée"
            )
            raise WindowNotAvailableError

        left_click_element_with_mouse(self.window)

        def _program_list() -> None:
            """
            Handles displaying the program list.

            Raises:
                NotImplementedError: If the mainFrame is not available.
            """
            if not mainFrame:
                ui.message(
                    "Une erreur fatale s'est produite: mainFrame n'est pas définie"
                )
                raise NotImplementedError
            programList = api.getFocusObject()
            programsCount = RATTRAPAGE_PROGRAM_LIST_HEADER_CONTROL_COUNT

            def update_program_list(dialog: ElementsListDialog):
                """
                Updates the program list whenever a new program is added.

                Args:
                    dialog (ElementsListDialog): The dialog to update.
                """
                nonlocal programsCount
                if not dialog.IsActive():
                    return
                childCount = programList._get_childCount()
                if childCount > programsCount:
                    speech.cancelSpeech()
                    ui.message(
                        "Mise à jour de la liste des programmes",
                        speechPriority=SpeechPriority.NOW,
                    )
                    dialog.appendElements(
                        programList.children[programsCount:childCount]
                    )
                    programsCount = childCount
                    speech.cancelSpeech()
                    ui.message(
                        "Liste des programmes mise à jour.",
                        speechPriority=SpeechPriority.NOW,
                    )
                core.callLater(20, lambda: update_program_list(dialog))

            def get_program_info(
                element: Union[NVDAObject, IAccessible]
            ) -> Union[str, None]:
                """
                Gathers the program information from the element.

                Args:
                    element (Union[NVDAObject, IAccessible]): The element to get the info from.

                Returns:
                    Union[str, None]: The program info or None if the element is not a program.
                """
                if not isinstance(element, (IAccessible, NVDAObject)):
                    return None

                try:
                    program = Program(element.name)
                    program_info = f"{program.name}{f' | Durée: {program.duration}' if program.duration else ''}{f' | Sommaire : {program.summary}' if program.summary else ''}"
                    return program_info
                except (
                    AttributeError,
                    IndexError,
                ):  # The element is not a program
                    return None

            def selected_program_callback(
                selectedProgramElement: Union[IAccessible, NVDAObject]
            ) -> None:
                """
                Callback for when the user has selected a program.

                Args:
                    selectedProgramElement (Union[IAccessible, NVDAObject]): The selected program element.
                """
                if mainFrame:
                    mainFrame.prePopup()
                    dialog = ElementsListDialog(
                        parent=mainFrame,
                        elements=[
                            "Télécharger",
                            "Visionner avec le lecteur intégré",
                            "Visionner sur le site web",
                            "Copier l'adresse de l'émission",
                        ],
                        callback=lambda option: self._rattrapageSelectViewOptionCallback(
                            selectedProgramElement, option
                        ),
                        title="Choisissez une option",
                        list_label="",
                    )
                    dialog.Show()
                    mainFrame.postPopup()

            mainFrame.prePopup()
            dialog = ElementsListDialog(
                parent=mainFrame,
                elements=[],
                element_name_getter=get_program_info,
                callback=selected_program_callback,
                title="Liste des programmes",
                max_displayed_elements=50,
            )
            dialog.Show()
            ui.message(
                "Chargement de la liste des programmes",
                speechPriority=SpeechPriority.NEXT,
            )
            update_program_list(dialog)
            mainFrame.postPopup()

        speech.cancelSpeech()
        ui.message("Chargement des programmes", speechPriority=SpeechPriority.NOW)
        # Wait for the focus to be passed on to the program list
        core.callLater(100, _program_list)

    def getModeButtonList(self, depth: int = 0) -> Dict[str, NVDAObject]:
        """
        Retrieves a list of mode buttons.

        Raises:
            WindowUnavailableError: If the window is not available.
            ButtonListPaneNotAvailableError: If the button list pane is not available.

        Returns:
            Dict[NVDAObject]: A dict of mode buttons as NVDAObjects, in the format "BUTTON_NAME": NVDAObject.
        """

        if not hasattr(self, "buttonListPane"):
            if not self.window:
                ui.message(
                    "Une erreur fatale s'est produite: La fenêtre captvty n'a pas été trouvée"
                )
                raise WindowNotAvailableError
            window_location = self.window._get_location()

            x = window_location.left + 10
            y = window_location.top + 10

            self.buttonListPane = self.window.objectFromPoint(x, y)
            if not self.buttonListPane:
                raise ButtonListPaneNotAvailableError

        mode_buttons = {
            button.name: button
            for pane_child in self.buttonListPane.children  # type: ignore
            for button in pane_child.children
            if button and button.role == controlTypes.ROLE_BUTTON
        }

        return mode_buttons

    def getAppMode(self) -> AppModes:
        """
        Determines the current application mode by examining the state of mode buttons.

        Returns:
            AppModes: An enum value representing the current application mode.
                - AppModes.DIRECT if the right-most button's name is "DIRECT"
                - AppModes.RATTRAPAGE if the right-most button's name is "RATTRAPAGE"
                - AppModes.TELECHARGEMENT if the right-most button's name is "TÉLÉCHARGEMENT\nMANUEL"
                - AppModes.OTHER if the right-most button's name is not one of the above.
        """
        buttons = self.getModeButtonList()
        if not buttons:
            log.debugWarning("We couldn't find the mode buttons")
            return AppModes.OTHER

        right_most = None
        for button in buttons.values():
            if not right_most or button.location.left > right_most.location.left:  # type: ignore
                right_most = button

        if not right_most:
            raise ButtonListPaneNotAvailableError

        if right_most.name == "DIRECT":
            return AppModes.DIRECT
        elif right_most.name == "RATTRAPAGE":
            return AppModes.RATTRAPAGE
        elif right_most.name == "TÉLÉCHARGEMENT\nMANUEL":
            return AppModes.TELECHARGEMENT

        log.debugWarning(f"We didn't find DIRECT or RATTRAPAGE but {right_most.name}")
        return AppModes.OTHER

    def getChannelButtonList(self) -> Optional[List[NVDAObject]]:
        """
        Gets the list of channel buttons.

        Raises:
            WindowNotAvailableError: If the Captvty window could not be found.
            ChannelListNotAvailableError: If the channel list could not be located.
            InvalidElementRoleError: If an unexpected type of element is found where a channel list is expected.
            NotImplementedError: If the application mode is not supported, i.e. not DIRECT or RATTRAPAGE.

        Returns:
            A list of NVDAObjects representing the channel buttons or None if not found.
        """
        if not self.window:
            ui.message(
                "Une erreur fatale s'est produite: La fenêtre captvty n'a pas été trouvée"
            )
            raise WindowNotAvailableError
        window_location = self.window._get_location()

        x = window_location.left + 50
        y = window_location.top + (window_location.height // 2)

        channel_list = self.window.objectFromPoint(x, y)
        if not channel_list:
            raise ChannelListNotAvailableError

        appMode = self.getAppMode()
        if appMode == AppModes.RATTRAPAGE:
            if channel_list.role == controlTypes.ROLE_CHECKBOX:
                channel_list = channel_list.parent.parent.parent.parent  # type: ignore
            else:
                raise InvalidElementRoleError(
                    f"Expected a checkbox, but found a {channel_list.role}"
                )
        elif appMode == AppModes.DIRECT:
            if channel_list.role == controlTypes.ROLE_BUTTON:
                channel_list = (
                    channel_list.parent.parent.parent.parent.parent.parent.parent.parent  # type: ignore
                )
            elif channel_list.role == controlTypes.ROLE_PANE:
                channel_list = channel_list.parent.parent.parent.parent.parent.parent  # type: ignore
            else:
                raise InvalidElementRoleError(
                    f"Expected a button or a pane, but found a {channel_list.role}"
                )
        elif appMode in (AppModes.TELECHARGEMENT, AppModes.OTHER):
            raise NotImplementedError(
                f"Function not yet implemented for the app mode: {appMode}"
            )

        return [channel.children[3].children[1] for channel in channel_list.children]  # type: ignore
