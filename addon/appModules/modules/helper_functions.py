from enum import IntEnum, auto
from typing import TYPE_CHECKING, Optional, Union

import api
import controlTypes
import winUser
from logHandler import log
from NVDAObjects import NVDAObject
from NVDAObjects.IAccessible import IAccessible


class AppModes(IntEnum):
    DIRECT = auto()
    RATTRAPAGE = auto()
    OTHER = auto()


if TYPE_CHECKING:
    from locationHelper import RectLTWH


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
    for obj in fg.recursiveDescendants:  # type: ignore - recursiveDescendants is defined for fg
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
    location = element.location  # type: ignore - location is defined for IAccessible
    x = location.left + (location.width // 2) + x_offset
    y = location.top + (location.height // 2) + y_offset

    winUser.setCursorPos(x, y)

    winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def scroll_element_with_mouse(
    element: Union[IAccessible, NVDAObject],
    delta: Optional[int] = 120,
    x: Optional[int] = None,  # type: ignore - x is not obscured by a redefinition
    y: Optional[int] = None,  # type: ignore - y is not obscured by a redefinition
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
    location = element.location  # type: ignore - location is defined for IAccessible
    x: int = x or location.left + (location.width // 2)
    y: int = y or location.top + (location.height // 2)
    x += x_offset  # type: ignore - at this step, x is never None or Unknown
    y += y_offset  # type: ignore - at this step, y is never None or Unknown

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
    # We are using _get_location because the `location` attribute gets cached,
    # which would break this function if it's being called after an element has been moved
    element_location: Union[RectLTWH, None] = element._get_location()
    window_location: Union[RectLTWH, None] = window._get_location()

    if not element_location:
        log.error("element.location is unbound")
        return
    if not window_location:
        log.error("window.location is unbound")
        return

    element_right = element_location.left + element_location.width
    element_bottom = element_location.top + element_location.height
    window_right = window_location.left + window_location.width
    window_bottom = window_location.top + window_location.height

    log.info(f"element {element_location}, bottom {element_bottom}, right {element_right}")
    log.info(f"window {window_location}, bottom {window_bottom}, right {window_right}")
    is_inside_horizontal = element_location.left >= window_location.left and element_right <= window_right
    is_inside_vertical = element_location.top >= window_location.top and element_bottom <= window_bottom

    if is_inside_horizontal and is_inside_vertical:
        return None
    elif element_location.top > window_bottom:
        return "below"
    elif element_bottom < window_location.top:
        return "above"
    elif element_location.left > window_right:
        return "right"
    elif element_right < window_location.left:
        return "left"
    raise AssertionError("Bounds must be within two dimensions")


def scroll_to_element(element: Union[IAccessible, NVDAObject], scroll_delta: int = 120, max_attempts: int = 10, scrollable_container: Optional[Union[IAccessible, NVDAObject]] = None) -> None:
    """
    Scrolls the current foreground window to bring the specified element into view.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to scroll into view.
        scroll_delta (int, optional): The delta for the mouse wheel scrolling. Defaults to 120.
        max_attempts (int, optional): The maximum number of scroll attempts. Defaults to 10.
        scrollable_container: (Union[IAccessible, NVDAObject], optional): Container in which we will scroll.

    Returns:
        None
    """
    window = api.getForegroundObject()

    scrollable_container = scrollable_container or find_scrollable_container(element)

    if not scrollable_container:
        log.debugWarning("Could not find a scrollable container")
        return

    for _ in range(max_attempts):
        trespassing_side = where_is_element_trespassing(element, window)

        log.info(f"trespassing: {trespassing_side}")

        if trespassing_side == "above":
            scroll_element_with_mouse(scrollable_container, delta=scroll_delta)
        elif trespassing_side == "below":
            scroll_element_with_mouse(scrollable_container, delta=-scroll_delta)


def find_scrollable_container(element: Union[IAccessible, NVDAObject]) -> Optional[Union[IAccessible, NVDAObject]]:
    """
    Finds the nearest scrollable container that contains the given element.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to find the scrollable container for.

    Returns:
        The scrollable container (Union[IAccessible, NVDAObject]) or None if not found.
    """
    container = element.parent

    while container:
        if container.role in [
            controlTypes.ROLE_SCROLLPANE,
            controlTypes.ROLE_SCROLLBAR,
        ]:
            return container
        if container.role == controlTypes.ROLE_PANE:
            for container_child in container.children:
                if container_child.role in [
                    controlTypes.ROLE_SCROLLPANE,
                    controlTypes.ROLE_SCROLLBAR,
                ]:
                    return container_child
        container = container.parent

    return None


def find_element_by_name(root: Union[IAccessible, NVDAObject], name: str) -> Optional[NVDAObject]:
    """
    Find an element with a specific name in the UI tree starting from the given root.

    Args:
        root (Union[IAccessible, NVDAObject]): The root object to start the search from.
        name (str): The name of the element to find.

    Returns:
        NVDAObject: The found element, or None if the element is not found.
    """
    if root.name == name:
        return root

    for child in root.children:
        found_element = find_element_by_name(child, name)
        if found_element:
            return found_element

    return None


def scroll_and_click_on_element(element: Union[IAccessible, NVDAObject], scroll_delta: int = 120, max_attempts: int = 10, scrollable_container: Optional[Union[IAccessible, NVDAObject]] = None, x_offset: int = 0, y_offset: int = 0) -> None:
    """
    Scrolls the current foreground window to bring the specified element into view and then clicks on it.

    Args:
        element (Union[IAccessible, NVDAObject]): The element to scroll into view and click.
        scroll_delta (int, optional): The delta for the mouse wheel scrolling. Defaults to 120.
        max_attempts (int, optional): The maximum number of scroll attempts. Defaults to 10.
        scrollable_container: (Union[IAccessible, NVDAObject], optional): Container in which we will scroll.
        x_offset (int, optional): The x offset to add to the center of the element. Defaults to 0.
        y_offset (int, optional): The y offset to add to the center of the element. Defaults to 0.

    Returns:
        None
    """
    scroll_to_element(element, scroll_delta, max_attempts, scrollable_container)
    click_element_with_mouse(element, x_offset, y_offset)
