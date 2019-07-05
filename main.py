import logging
import os
import re
import subprocess
from os.path import expanduser

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesUpdateEvent, PreferencesEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

logger = logging.getLogger(__name__)


class SshExtension(Extension):

    def __init__(self):
        super(SshExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())

    def parse_ssh_config(self):
        home = expanduser("~")
        hosts = []

        try:
            with open(home + "/.ssh/config", "r") as ssh_config:
                for line in ssh_config:
                    line_lc = line.lower()

                    if line_lc.startswith("host") and "*" not in line_lc and "keyalgorithms" not in line_lc:
                        hosts.append(line_lc.strip("host").strip("\n").strip())
        except:
            logger.debug("ssh config not found!")

        return hosts

    def parse_known_hosts(self):
        home = expanduser("~")
        hosts = []
        host_regex = re.compile("^[a-zA-Z0-9\\-\\.]*(?=(,.*)*\\s)")

        try:
            with open(home + "/.ssh/known_hosts", "r") as known_hosts:
                for line in known_hosts:
                    line_lc = line.lower()
                    match = host_regex.match(line_lc)

                    if match:
                        hosts.append(match.group().strip())
        except:
            logger.debug("known_hosts not found!")

        return hosts

    def launch_terminal(self, conn):
        logger.debug("Launching connection " + conn)
        shell = os.environ["SHELL"]
        home = expanduser("~")

        cmd = self.terminal_cmd.replace("%SHELL", shell).replace("%CONN", conn)

        if self.terminal:
            # ipdb.set_trace()
            subprocess.Popen([self.terminal, self.terminal_arg, cmd], cwd=home)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        extension.launch_terminal(data)


class PreferencesUpdateEventListener(EventListener):

    def on_event(self, event, extension):

        if event.id == "ssh_launcher_terminal":
            extension.terminal = event.new_value
        elif event.id == "ssh_launcher_terminal_arg":
            extension.terminal_arg = event.new_value
        elif event.id == "ssh_launcher_terminal_cmd":
            extension.terminal_cmd = event.new_value


class PreferencesEventListener(EventListener):

    def on_event(self, event, extension):
        extension.terminal = event.preferences["ssh_launcher_terminal"]
        extension.terminal_arg = event.preferences["ssh_launcher_terminal_arg"]
        extension.terminal_cmd = event.preferences["ssh_launcher_terminal_cmd"]


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        icon = "images/icon.png"
        items = []
        arg = event.get_argument()
        hosts = extension.parse_ssh_config()
        hosts += extension.parse_known_hosts()

        hosts.sort()
        if arg is not None:
            index = arg.find('@', 1)
            if index > 0:
                query = arg[index + 1:len(arg)]
                cmd_arg = arg[0: index + 1]
                if query is not None and len(query) > 0:
                    # ipdb.set_trace()
                    hosts = filter(lambda x: query in x, hosts)
                for host in hosts:
                    items.append(self.my_extension_result_item(icon, host, host, cmd_arg + host))
                # If there are no results, let the user connect to the specified server.
                if len(items) <= 0:
                    items.append(self.my_extension_result_item(icon, arg, arg, arg))
        return RenderResultListAction(items)

    def my_extension_result_item(self, icon, name, description, enter):
        return ExtensionResultItem(icon=icon,
                                   name=name,
                                   description="Connect to '{}' with SSH".format(description),
                                   on_enter=ExtensionCustomAction(enter,
                                                                  keep_app_open=False))


if __name__ == '__main__':
    SshExtension().run()
