from ranger.api.commands import Command

class hello(Command):
    def execute(self):
        self.fm.notify("Hello from plugin!")
