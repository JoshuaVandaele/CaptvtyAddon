import api
from NVDAObjects import NVDAObject
from typing import Optional, Union
from NVDAObjects.IAccessible import IAccessible
import winUser
from logHandler import log
import controlTypes

def setFocus(obj: NVDAObject) -> None:
    """
    Sets the focus to the given object and processes any pending events.

    Args:
        obj (NVDAObject): The object to set focus to.

    Returns:
        None
    """
    obj.setFocus()
    api.setFocusObject(obj)
    api.processPendingEvents()

def find_element_by_size(target_width: Optional[int] = None, target_height: Optional[int] = None) -> Optional[Union[IAccessible, NVDAObject]]:
    """
    Finds and returns an object with the specified width and/or height from the current foreground object's descendants.

    Args:
        target_width (int, optional): The target width to search for.
        target_height (int, optional): The target height to search for.

    Returns:
        An object with the specified width and/or height, or None if not found.
    """
    fg = api.getForegroundObject()
    for obj in fg.recursiveDescendants: # type: ignore - recursiveDescendants is defined for fg
        left, top, width, height = obj.location
        if (not target_width or width == target_width) and (not target_height or height == target_height):
            return obj
    return None

def click_element_with_mouse(element: Union[NVDAObject, IAccessible], x_offset: int = 0, y_offset: int = 0) -> None:
    """
    Clicks the specified element using the mouse with the specified x and y offset.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to click.
        x_offset (int, optional): The x offset to add to the center of the element. Defaults to 0.
        y_offset (int, optional): The y offset to add to the center of the element. Defaults to 0.

    Returns:
        None
    """
    location = element.location # type: ignore - location is defined for IAccessible
    x = location.left + (location.width // 2) + x_offset
    y = location.top + (location.height // 2) + y_offset

    winUser.setCursorPos(x, y)

    winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

def scroll_element_with_mouse(
        element: Union[IAccessible, NVDAObject],
        delta: Optional[int] = 120,
        x: Optional[int] = None, # type: ignore - x is not obscured by a redefinition
        y: Optional[int] = None, # type: ignore - y is not obscured by a redefinition
        x_offset: Optional[int] = 0,
        y_offset: Optional[int] = 0
    ) -> None: 
    """
    Scrolls the specified element using the mouse wheel with the specified delta and x, y offsets.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to scroll.
        delta (int, optional): The delta for the mouse wheel scrolling. Defaults to 120.
        x (int, optional): The x coordinate of the mouse cursor. Defaults to the center of the element.
        y (int, optional): The y coordinate of the mouse cursor. Defaults to the center of the element.
        x_offset (int, optional): The x offset to add to the center of the element. Defaults to 0.
        y_offset (int, optional): The y offset to add to the center of the element. Defaults to 0.

    Returns:
        None
    """
    location = element.location # type: ignore - location is defined for IAccessible 
    x: int = x or location.left + (location.width // 2)
    y: int = y or location.top + (location.height // 2)
    x += x_offset # type: ignore - at this step, x is never None or Unknown
    y += y_offset # type: ignore - at this step, y is never None or Unknown
    
    winUser.setCursorPos(x, y)

    winUser.mouse_event(winUser.MOUSEEVENTF_WHEEL, x, y, delta, 0)


def where_is_element_trespassing(element: Union[IAccessible, NVDAObject], window: Union[IAccessible, NVDAObject]) -> Optional[str]:
    """
    Determines which side of a window an element is trespassing on, if any.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to check.
        window (Union[IAccessible, NVDAObject]): The window to check.

    Returns:
        A string indicating the side of the window the element is trespassing on (i.e. "above", "below", "left", "right"),
        or None if the element is inside the window.
    """
    element_location = element.location # type: ignore - location is defined for IAccessible 
    window_location = window.location   # type: ignore - location is defined for IAccessible 

    if element_location.bottom < window_location.top:
        return "above"
    elif element_location.top > window_location.bottom:
        return "below"
    elif element_location.right < window_location.left:
        return "left"
    elif element_location.left > window_location.right:
        return "right"
    return None


def scroll_to_element(element: Union[IAccessible, NVDAObject], window: Union[IAccessible, NVDAObject]) -> None:
    """
    Scrolls the window containing the element until the element is visible.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to scroll to.
        window (Union[IAccessible, NVDAObject]): The window containing the element.

    Returns:
        None
    """
    while True:
        trespassing_side = where_is_element_trespassing(element, window)

        if not trespassing_side:
            break

        scrollable_container = find_scrollable_container(element)

        if not scrollable_container:
            log.error("Couldn't find a scrollable container.")
            break

        if trespassing_side == "above":
            scroll_element_with_mouse(scrollable_container, delta=120)  # Scroll up
        elif trespassing_side == "below":
            scroll_element_with_mouse(scrollable_container, delta=-120)  # Scroll down

def find_scrollable_container(element: Union[IAccessible, NVDAObject]) -> Optional[Union[IAccessible, NVDAObject]]:
    """
    Finds the nearest scrollable container that contains the given element.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to find the scrollable container for.

    Returns:
        The scrollable container (Union[IAccessible, NVDAObject]) or None if not found.
    """
    # TODO: This doesn't exactly work for now, but I do not know why
    container = element.parent

    while container:
        if container.role == controlTypes.ROLE_SCROLLPANE:
            return container
        container = container.parent

    return None
