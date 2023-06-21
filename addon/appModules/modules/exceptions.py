class WindowNotAvailableError(Exception):
    """Raised when the window is not available."""

    def __init__(self, message="The window is not available."):
        self.message = message
        super().__init__(self.message)


class ButtonListPaneNotAvailableError(Exception):
    """Raised when the button list pane is not available."""

    def __init__(self, message="The button list pane is not available."):
        self.message = message
        super().__init__(self.message)


class ChannelListNotAvailableError(Exception):
    """Raised when the channel list is not available."""

    def __init__(self, message="The channel list is not available."):
        self.message = message
        super().__init__(self.message)


class InvalidElementRoleError(Exception):
    """Raised when an element with an unexpected role is encountered."""

    def __init__(self, message="An element with an unexpected role was encountered."):
        self.message = message
        super().__init__(self.message)
