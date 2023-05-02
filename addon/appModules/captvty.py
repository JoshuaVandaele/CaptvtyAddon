import appModuleHandler
from logHandler import log

class AppModule(appModuleHandler.AppModule):
    def event_gainFocus(self, obj, nextHandler):
        log.debug("-=== Captvty Focused ===-")
        nextHandler()

    def event_loseFocus(self, obj, nextHandler):
        log.debug("-=== Captvty Unfocused ===-")
        nextHandler()
