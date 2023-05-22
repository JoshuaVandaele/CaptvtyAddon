from typing import Callable

import wx
from gui import guiHelper
from wx.adv import EVT_DATE_CHANGED, EVT_TIME_CHANGED, DatePickerCtrl, TimePickerCtrl


class DateRangePanel(wx.Panel):
    def __init__(self, parent):
        super(DateRangePanel, self).__init__(parent)
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)

    def onKeyPress(self, event: wx.KeyEvent) -> None:
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_RETURN:
            self.GetParent().onOk(event)
        elif keyCode == wx.WXK_ESCAPE:
            self.GetParent().Close()
        else:
            event.Skip()


class DateRangeDialog(wx.Frame):
    def __init__(
        self,
        parent: wx.Window,
        callback: Callable[[wx.DateTime, wx.DateTime], None],
        title: str = "Date Range Picker",
    ):
        super(DateRangeDialog, self).__init__(parent, title=title)

        self.callback = callback

        self._createLayout()

        screen_width, screen_height = wx.DisplaySize()
        dialog_width, dialog_height = self.GetSize()
        position_x = screen_width - dialog_width
        position_y = screen_height - dialog_height
        self.SetPosition((position_x, position_y))
        self.Bind(wx.EVT_ACTIVATE, self.onActivate)

    def _createLayout(self) -> None:
        mainPanel = DateRangePanel(self)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        startDateLabel = wx.StaticText(mainPanel, wx.ID_ANY, "Date et heure de début:")
        mainSizer.Add(startDateLabel, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        self.startDatePicker = DatePickerCtrl(mainPanel)
        mainSizer.Add(
            self.startDatePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )
        self.startDatePicker.Bind(EVT_DATE_CHANGED, self.onDateChanged)

        self.startTimePicker = TimePickerCtrl(mainPanel)
        mainSizer.Add(
            self.startTimePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )
        self.startTimePicker.Bind(EVT_TIME_CHANGED, self.onTimeChanged)

        today = wx.DateTime.Now()
        self.startDatePicker.SetRange(
            today, wx.DateTime.FromDMY(today.day, today.month, year=today.year + 1)
        )

        endDateLabel = wx.StaticText(mainPanel, wx.ID_ANY, "Date et heure de fin:")
        mainSizer.Add(endDateLabel, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)

        self.endDatePicker = DatePickerCtrl(mainPanel)
        mainSizer.Add(
            self.endDatePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )
        self.endDatePicker.Bind(EVT_DATE_CHANGED, self.onDateChanged)

        self.endTimePicker = TimePickerCtrl(mainPanel)
        mainSizer.Add(
            self.endTimePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )
        self.endTimePicker.Bind(EVT_TIME_CHANGED, self.onTimeChanged)

        buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
        okButton = buttons.addButton(mainPanel, wx.ID_OK, label="OK")
        okButton.Bind(wx.EVT_BUTTON, self.onOk)
        cancelButton = buttons.addButton(mainPanel, wx.ID_CANCEL, label="Annuler")
        cancelButton.Bind(wx.EVT_BUTTON, self.Close)
        mainSizer.Add(
            buttons.sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8
        )

        mainPanel.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainPanel.SetFocus()

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

    def onDateChanged(self, event: wx.Event) -> None:
        startDate = self.startDatePicker.GetValue()
        endDate = self.endDatePicker.GetValue()

        if endDate < startDate:
            self.endDatePicker.SetValue(startDate)

    def onTimeChanged(self, event: wx.Event) -> None:
        startDate = self.startDatePicker.GetValue()
        startTime = self.startTimePicker.GetValue()
        endDate = self.endDatePicker.GetValue()
        endTime = self.endTimePicker.GetValue()

        if startDate == endDate and endTime < startTime:
            self.endTimePicker.SetValue(startTime)

    def onOk(self, event: wx.Event) -> None:
        startDate = self.startDatePicker.GetValue()
        startTime = self.startTimePicker.GetValue()
        endDate = self.endDatePicker.GetValue()
        endTime = self.endTimePicker.GetValue()

        startDate.SetHour(startTime.GetHour())
        startDate.SetMinute(startTime.GetMinute())
        startDate.SetSecond(startTime.GetSecond())

        endDate.SetHour(endTime.GetHour())
        endDate.SetMinute(endTime.GetMinute())
        endDate.SetSecond(endTime.GetSecond())

        if self.callback:
            self.callback(startDate, endDate)

        self.Close()
