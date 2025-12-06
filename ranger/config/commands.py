# -*- coding: utf-8 -*-
# This file is part of ranger, the console file manager.
# This configuration file is licensed under the same terms as ranger.
# ===================================================================
#
# NOTE: If you copied this file to /etc/ranger/commands_full.py or
# ~/.config/ranger/commands_full.py, then it will NOT be loaded by ranger,
# and only serve as a reference.
#
# ===================================================================
# This file contains ranger's commands.
# It's all in python; lines beginning with # are comments.
#
# Note that additional commands are automatically generated from the methods
# of the class ranger.core.actions.Actions.
#
# You can customize commands in the files /etc/ranger/commands.py (system-wide)
# and ~/.config/ranger/commands.py (per user).
# They have the same syntax as this file.  In fact, you can just copy this
# file to ~/.config/ranger/commands_full.py with
# `ranger --copy-config=commands_full' and make your modifications, don't
# forget to rename it to commands.py.  You can also use
# `ranger --copy-config=commands' to copy a short sample commands.py that
# has everything you need to get started.
# But make sure you update your configs when you update ranger.
#
# ===================================================================
# Every class defined here which is a subclass of `Command' will be used as a
# command in ranger.  Several methods are defined to interface with ranger:
#   execute():   called when the command is executed.
#   cancel():    called when closing the console.
#   tab(tabnum): called when <TAB> is pressed.
#   quick():     called after each keypress.
#
# tab() argument tabnum is 1 for <TAB> and -1 for <S-TAB> by default
#
# The return values for tab() can be either:
#   None: There is no tab completion
#   A string: Change the console to this string
#   A list/tuple/generator: cycle through every item in it
#
# The return value for quick() can be:
#   False: Nothing happens
#   True: Execute the command afterwards
#
# The return value for execute() and cancel() doesn't matter.
#
# ===================================================================
# Commands have certain attributes and methods that facilitate parsing of
# the arguments:
#
# self.line: The whole line that was written in the console.
# self.args: A list of all (space-separated) arguments to the command.
# self.quantifier: If this command was mapped to the key "X" and
#      the user pressed 6X, self.quantifier will be 6.
# self.arg(n): The n-th argument, or an empty string if it doesn't exist.
# self.rest(n): The n-th argument plus everything that followed.  For example,
#      if the command was "search foo bar a b c", rest(2) will be "bar a b c"
# self.start(n): Anything before the n-th argument.  For example, if the
#      command was "search foo bar a b c", start(2) will be "search foo"
#
# ===================================================================
# And this is a little reference for common ranger functions and objects:
#
# self.fm: A reference to the "fm" object which contains most information
#      about ranger.
# self.fm.notify(string): Print the given string on the screen.
# self.fm.notify(string, bad=True): Print the given string in RED.
# self.fm.reload_cwd(): Reload the current working directory.
# self.fm.thisdir: The current working directory. (A File object.)
# self.fm.thisfile: The current file. (A File object too.)
# self.fm.thistab.get_selection(): A list of all selected files.
# self.fm.execute_console(string): Execute the string as a ranger command.
# self.fm.open_console(string): Open the console with the given string
#      already typed in for you.
# self.fm.move(direction): Moves the cursor in the given direction, which
#      can be something like down=3, up=5, right=1, left=1, to=6, ...
#
# File objects (for example self.fm.thisfile) have these useful attributes and
# methods:
#
# tfile.path: The path to the file.
# tfile.basename: The base name only.
# tfile.load_content(): Force a loading of the directories content (which
#      obviously works with directories only)
# tfile.is_directory: True/False depending on whether it's a directory.
#
# For advanced commands it is unavoidable to dive a bit into the source code
# of ranger.
# ===================================================================

# pylint: disable=invalid-name,too-many-lines

from __future__ import (absolute_import, division, print_function)

from collections import deque
import os
import re
from io import open

from ranger import PY3
from ranger.api.commands import Command
try:
    from ranger.config.plugins.ssh_download import *
    from ranger.config.plugins.sort_file import *
    from ranger.config.plugins.ml_priority import *
except ImportError as e:
    # 這樣寫是為了防止某個模組壞掉導致整個 Ranger 開不起來
    # 可以在 debug 模式看到錯誤
    import sys
    sys.stderr.write(f"Failed to load custom plugin: {e}\n")

class alias(Command):
    """:alias <newcommand> <oldcommand>

    Copies the oldcommand as newcommand.
    """

    context = 'browser'
    resolve_macros = False

    def execute(self):
        if not self.arg(1) or not self.arg(2):
            self.fm.notify('Syntax: alias <newcommand> <oldcommand>', bad=True)
            return

        self.fm.commands.alias(self.arg(1), self.rest(2))


class echo(Command):
    """:echo <text>

    Display the text in the statusbar.
    """

    def execute(self):
        self.fm.notify(self.rest(1))


class cd(Command):
    """:cd [-r] <path>

    The cd command changes the directory.
    If the path is a file, selects that file.
    The command 'cd -' is equivalent to typing ``.
    Using the option "-r" will get you to the real path.
    """

    def execute(self):
        if self.arg(1) == '-r':
            self.shift()
            destination = os.path.realpath(self.rest(1))
            if os.path.isfile(destination):
                self.fm.select_file(destination)
                return
        elif self.arg(1) == '-e':
            self.shift()
            destination = os.path.realpath(os.path.expandvars(self.rest(1)))
            if os.path.isfile(destination):
                self.fm.select_file(destination)
                return
        else:
            destination = self.rest(1)

        if not destination:
            destination = '~'

        if destination == '-':
            self.fm.enter_bookmark('`')
        else:
            self.fm.cd(destination)

    def _tab_args(self):
        # dest must be rest because path could contain spaces
        if self.arg(1) == '-r':
            start = self.start(2)
            dest = self.rest(2)
        else:
            start = self.start(1)
            dest = self.rest(1)

        if dest:
            head, tail = os.path.split(os.path.expanduser(dest))
            if head:
                dest_exp = os.path.join(os.path.normpath(head), tail)
            else:
                dest_exp = tail
        else:
            dest_exp = ''
        return (start, dest_exp, os.path.join(self.fm.thisdir.path, dest_exp),
                dest.endswith(os.path.sep))

    @staticmethod
    def _tab_paths(dest, dest_abs, ends_with_sep):
        if not dest:
            try:
                return next(os.walk(dest_abs))[1], dest_abs
            except (OSError, StopIteration):
                return [], ''

        if ends_with_sep:
            try:
                return [os.path.join(dest, path) for path in next(os.walk(dest_abs))[1]], ''
            except (OSError, StopIteration):
                return [], ''

        return None, None

    def _tab_match(self, path_user, path_file):
        if self.fm.settings.cd_tab_case == 'insensitive':
            path_user = path_user.lower()
            path_file = path_file.lower()
        elif self.fm.settings.cd_tab_case == 'smart' and path_user.islower():
            path_file = path_file.lower()
        return path_file.startswith(path_user)

    def _tab_normal(self, dest, dest_abs):
        dest_dir = os.path.dirname(dest)
        dest_base = os.path.basename(dest)

        try:
            dirnames = next(os.walk(os.path.dirname(dest_abs)))[1]
        except (OSError, StopIteration):
            return [], ''

        return [os.path.join(dest_dir, d) for d in dirnames if self._tab_match(dest_base, d)], ''

    def _tab_fuzzy_match(self, basepath, tokens):
        """ Find directories matching tokens recursively """
        if not tokens:
            tokens = ['']
        paths = [basepath]
        while True:
            token = tokens.pop()
            matches = []
            for path in paths:
                try:
                    directories = next(os.walk(path))[1]
                except (OSError, StopIteration):
                    continue
                matches += [os.path.join(path, d) for d in directories
                            if self._tab_match(token, d)]
            if not tokens or not matches:
                return matches
            paths = matches

        return None

    def _tab_fuzzy(self, dest, dest_abs):
        tokens = []
        basepath = dest_abs
        while True:
            basepath_old = basepath
            basepath, token = os.path.split(basepath)
            if basepath == basepath_old:
                break
            if os.path.isdir(basepath_old) and not token.startswith('.'):
                basepath = basepath_old
                break
            tokens.append(token)

        paths = self._tab_fuzzy_match(basepath, tokens)
        if not os.path.isabs(dest):
            paths_rel = self.fm.thisdir.path
            paths = [os.path.relpath(os.path.join(basepath, path), paths_rel)
                     for path in paths]
        else:
            paths_rel = ''
        return paths, paths_rel

    def tab(self, tabnum):
        from os.path import sep

        start, dest, dest_abs, ends_with_sep = self._tab_args()

        paths, paths_rel = self._tab_paths(dest, dest_abs, ends_with_sep)
        if paths is None:
            if self.fm.settings.cd_tab_fuzzy:
                paths, paths_rel = self._tab_fuzzy(dest, dest_abs)
            else:
                paths, paths_rel = self._tab_normal(dest, dest_abs)

        paths.sort()

        if self.fm.settings.cd_bookmarks:
            paths[0:0] = [
                os.path.relpath(v.path, paths_rel) if paths_rel else v.path
                for v in self.fm.bookmarks.dct.values() for path in paths
                if v.path.startswith(os.path.join(paths_rel, path) + sep)
            ]

        if not paths:
            return None
        if len(paths) == 1:
            return start + paths[0] + sep
        return [start + dirname + sep for dirname in paths]


class chain(Command):
    """:chain <command1>; <command2>; ...

    Calls multiple commands at once, separated by semicolons.
    """
    resolve_macros = False

    def execute(self):
        if not self.rest(1).strip():
            self.fm.notify('Syntax: chain <command1>; <command2>; ...', bad=True)
            return
        for command in [s.strip() for s in self.rest(1).split(";")]:
            self.fm.execute_console(command)


class shell(Command):
    escape_macros_for_shell = True

    def execute(self):
        if self.arg(1) and self.arg(1)[0] == '-':
            flags = self.arg(1)[1:]
            command = self.rest(2)
        else:
            flags = ''
            command = self.rest(1)

        if command:
            self.fm.execute_command(command, flags=flags)

    def tab(self, tabnum):
        from ranger.ext.get_executables import get_executables
        if self.arg(1) and self.arg(1)[0] == '-':
            command = self.rest(2)
        else:
            command = self.rest(1)
        start = self.line[0:len(self.line) - len(command)]

        try:
            position_of_last_space = command.rindex(" ")
        except ValueError:
            return (start + program + ' ' for program
                    in get_executables() if program.startswith(command))
        if position_of_last_space == len(command) - 1:
            selection = self.fm.thistab.get_selection()
            if len(selection) == 1:
                return self.line + selection[0].shell_escaped_basename + ' '
            return self.line + '%s '

        before_word, start_of_word = self.line.rsplit(' ', 1)
        return (before_word + ' ' + file.shell_escaped_basename
                for file in self.fm.thisdir.files or []
                if file.shell_escaped_basename.startswith(start_of_word))


class open_with(Command):

    def execute(self):
        app, flags, mode = self._get_app_flags_mode(self.rest(1))
        self.fm.execute_file(
            files=self.fm.thistab.get_selection(),
            app=app,
            flags=flags,
            mode=mode)

    def tab(self, tabnum):
        return self._tab_through_executables()

    def _get_app_flags_mode(self, string):  # pylint: disable=too-many-branches,too-many-statements
        """Extracts the application, flags and mode from a string.

        examples:
        "mplayer f 1" => ("mplayer", "f", 1)
        "atool 4" => ("atool", "", 4)
        "p" => ("", "p", 0)
        "" => None
        """

        app = ''
        flags = ''
        mode = 0
        split = string.split()

        if len(split) == 1:
            part = split[0]
            if self._is_app(part):
                app = part
            elif self._is_flags(part):
                flags = part
            elif self._is_mode(part):
                mode = part

        elif len(split) == 2:
            part0 = split[0]
            part1 = split[1]

            if self._is_app(part0):
                app = part0
                if self._is_flags(part1):
                    flags = part1
                elif self._is_mode(part1):
                    mode = part1
            elif self._is_flags(part0):
                flags = part0
                if self._is_mode(part1):
                    mode = part1
            elif self._is_mode(part0):
                mode = part0
                if self._is_flags(part1):
                    flags = part1

        elif len(split) >= 3:
            part0 = split[0]
            part1 = split[1]
            part2 = split[2]

            if self._is_app(part0):
                app = part0
                if self._is_flags(part1):
                    flags = part1
                    if self._is_mode(part2):
                        mode = part2
                elif self._is_mode(part1):
                    mode = part1
                    if self._is_flags(part2):
                        flags = part2
            elif self._is_flags(part0):
                flags = part0
                if self._is_mode(part1):
                    mode = part1
            elif self._is_mode(part0):
                mode = part0
                if self._is_flags(part1):
                    flags = part1

        return app, flags, int(mode)

    def _is_app(self, arg):
        return not self._is_flags(arg) and not arg.isdigit()

    @staticmethod
    def _is_flags(arg):
        from ranger.core.runner import ALLOWED_FLAGS
        return all(x in ALLOWED_FLAGS for x in arg)

    @staticmethod
    def _is_mode(arg):
        return all(x in '0123456789' for x in arg)


class set_(Command):
    """:set <option name>=<python expression>

    Gives an option a new value.

    Use `:set <option>!` to toggle or cycle it, e.g. `:set flush_input!`
    """
    name = 'set'  # don't override the builtin set class

    def execute(self):
        name = self.arg(1)
        name, value, _, toggle = self.parse_setting_line_v2()
        if toggle:
            self.fm.toggle_option(name)
        else:
            self.fm.set_option_from_string(name, value)

    def tab(self, tabnum):  # pylint: disable=too-many-return-statements
        from ranger.gui.colorscheme import get_all_colorschemes
        name, value, name_done = self.parse_setting_line()
        settings = self.fm.settings
        if not name:
            return sorted(self.firstpart + setting for setting in settings)
        if not value and not name_done:
            return sorted(self.firstpart + setting for setting in settings
                          if setting.startswith(name))
        if not value:
            value_completers = {
                "colorscheme":
                # Cycle through colorschemes when name, but no value is specified
                lambda: sorted(self.firstpart + colorscheme for colorscheme
                               in get_all_colorschemes(self.fm)),

                "column_ratios":
                lambda: self.firstpart + ",".join(map(str, settings[name])),
            }

            def default_value_completer():
                return self.firstpart + str(settings[name])

            return value_completers.get(name, default_value_completer)()
        if bool in settings.types_of(name):
            if 'true'.startswith(value.lower()):
                return self.firstpart + 'True'
            if 'false'.startswith(value.lower()):
                return self.firstpart + 'False'
        # Tab complete colorscheme values if incomplete value is present
        if name == "colorscheme":
            return sorted(self.firstpart + colorscheme for colorscheme
                          in get_all_colorschemes(self.fm) if colorscheme.startswith(value))
        return None


class setlocal_(set_):
    """Shared class for setinpath and setinregex

    By implementing the _arg abstract properly you can affect what the name of
    the pattern/path/regex argument can be, this should be a regular expression
    without match groups.

    By implementing the _format_arg abstract method you can affect how the
    argument is formatted as a regular expression.
    """
    from abc import (ABCMeta, abstractmethod, abstractproperty)

    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def _arg(self):
        """The name of the option for the path/regex"""
        raise NotImplementedError

    def __init__(self, *args, **kwargs):
        super(setlocal_, self).__init__(*args, **kwargs)
        # We require quoting of paths with whitespace so we have to take care
        # not to match escaped quotes.
        self.path_re_dquoted = re.compile(
            r'^set.+?\s+{arg}="(.*?[^\\])"'.format(arg=self._arg)
        )
        self.path_re_squoted = re.compile(
            r"^set.+?\s+{arg}='(.*?[^\\])'".format(arg=self._arg)
        )
        self.path_re_unquoted = re.compile(
            r'^{arg}=(.+?)$'.format(arg=self._arg)
        )

    def _re_shift(self, match):
        if not match:
            return None
        path = match.group(1)
        # Prepend something that behaves like "path=" in case path starts with
        # whitespace
        for _ in "={0}".format(path).split():
            self.shift()
        return os.path.expanduser(path)

    @abstractmethod
    def _format_arg(self, arg):
        """How to format the argument as a regular expression"""
        raise NotImplementedError

    def execute(self):
        arg = self._re_shift(self.path_re_dquoted.match(self.line))
        if arg is None:
            arg = self._re_shift(self.path_re_squoted.match(self.line))
        if arg is None:
            arg = self._re_shift(self.path_re_unquoted.match(self.arg(1)))
        if arg is None and self.fm.thisdir:
            arg = self.fm.thisdir.path
        if arg is None:
            return
        else:
            arg = self._format_arg(arg)

        name, value, _ = self.parse_setting_line()
        self.fm.set_option_from_string(name, value, localpath=arg)


class setinpath(setlocal_):
    """:setinpath path=<path> <option name>=<python expression>

    Sets an option when in a directory that matches <path>, relative paths can
    match multiple directories, for example, ``path=build`` would match a build
    directory in any directory. If the <path> contains whitespace it needs to
    be quoted and nested quotes need to be backslash-escaped. The "path"
    argument can also be named "pattern" to allow for easier switching with
    ``setinregex``.
    """
    _arg = "(?:path|pattern)"

    def _format_arg(self, arg):
        return "{0}$".format(re.escape(arg))


class setlocal(setinpath):
    """:setlocal is an alias for :setinpath"""


class setinregex(setlocal_):
    """:setinregex re=<regex> <option name>=<python expression>

    Sets an option when in a specific directory. If the <regex> contains
    whitespace it needs to be quoted and nested quotes need to be
    backslash-escaped. Special characters need to be escaped if they are
    intended to match literally as documented in the ``re`` library
    documentation. The "re" argument can also be named "regex" or "pattern,"
    which allows for easier switching with ``setinpath``.
    """
    _arg = "(?:re(?:gex)?|pattern)"

    def _format_arg(self, arg):
        return arg


class setintag(set_):
    """:setintag <tag or tags> <option name>=<option value>

    Sets an option for directories that are tagged with a specific tag.
    """

    def execute(self):
        tags = self.arg(1)
        self.shift()
        name, value, _ = self.parse_setting_line()
        self.fm.set_option_from_string(name, value, tags=tags)


class default_linemode(Command):

    def execute(self):
        from ranger.container.fsobject import FileSystemObject

        if len(self.args) < 2:
            self.fm.notify(
                "Usage: default_linemode [path=<regexp> | tag=<tag(s)>] <linemode>", bad=True)

        # Extract options like "path=..." or "tag=..." from the command line
        arg1 = self.arg(1)
        method = "always"
        argument = None
        if arg1.startswith("path="):
            method = "path"
            argument = re.compile(arg1[5:])
            self.shift()
        elif arg1.startswith("tag="):
            method = "tag"
            argument = arg1[4:]
            self.shift()

        # Extract and validate the line mode from the command line
        lmode = self.rest(1)
        if lmode not in FileSystemObject.linemode_dict:
            self.fm.notify(
                "Invalid linemode: %s; should be %s" % (
                    lmode, "/".join(FileSystemObject.linemode_dict)),
                bad=True,
            )

        # Add the prepared entry to the fm.default_linemodes
        entry = [method, argument, lmode]
        self.fm.default_linemodes.appendleft(entry)

        # Redraw the columns
        if self.fm.ui.browser:
            for col in self.fm.ui.browser.columns:
                col.need_redraw = True

    def tab(self, tabnum):
        return (self.arg(0) + " " + lmode
                for lmode in self.fm.thisfile.linemode_dict.keys()
                if lmode.startswith(self.arg(1)))


class quit(Command):  # pylint: disable=redefined-builtin
    """:quit

    Closes the current tab, if there's more than one tab.
    Otherwise quits if there are no tasks in progress.
    """
    def _exit_no_work(self):
        if self.fm.loader.has_work():
            self.fm.notify('Not quitting: Tasks in progress: Use `quit!` to force quit')
        else:
            self.fm.exit()

    def execute(self):
        if len(self.fm.tabs) >= 2:
            self.fm.tab_close()
        else:
            self._exit_no_work()


class quit_bang(Command):
    """:quit!

    Closes the current tab, if there's more than one tab.
    Otherwise force quits immediately.
    """
    name = 'quit!'
    allow_abbrev = False

    def execute(self):
        if len(self.fm.tabs) >= 2:
            self.fm.tab_close()
        else:
            self.fm.exit()


class quitall(Command):
    """:quitall

    Quits if there are no tasks in progress.
    """
    def _exit_no_work(self):
        if self.fm.loader.has_work():
            self.fm.notify('Not quitting: Tasks in progress: Use `quitall!` to force quit')
        else:
            self.fm.exit()

    def execute(self):
        self._exit_no_work()


class quitall_bang(Command):
    """:quitall!

    Force quits immediately.
    """
    name = 'quitall!'
    allow_abbrev = False

    def execute(self):
        self.fm.exit()


class terminal(Command):
    """:terminal

    Spawns an "x-terminal-emulator" starting in the current directory.
    """

    def execute(self):
        from ranger.ext.get_executables import get_term
        self.fm.run(get_term(), flags='f')


class delete(Command):
    """:delete

    Tries to delete the selection or the files passed in arguments (if any).
    The arguments use a shell-like escaping.

    "Selection" is defined as all the "marked files" (by default, you
    can mark files with space or v). If there are no marked files,
    use the "current file" (where the cursor is)

    When attempting to delete non-empty directories or multiple
    marked files, it will require a confirmation.
    """

    allow_abbrev = False
    escape_macros_for_shell = True

    def execute(self):
        import shlex
        from functools import partial

        def is_directory_with_files(path):
            return os.path.isdir(path) and not os.path.islink(path) and len(os.listdir(path)) > 0

        if self.rest(1):
            files = shlex.split(self.rest(1))
            many_files = (len(files) > 1 or is_directory_with_files(files[0]))
        else:
            cwd = self.fm.thisdir
            tfile = self.fm.thisfile
            if not cwd or not tfile:
                self.fm.notify("Error: no file selected for deletion!", bad=True)
                return

            # relative_path used for a user-friendly output in the confirmation.
            files = [f.relative_path for f in self.fm.thistab.get_selection()]
            many_files = (cwd.marked_items or is_directory_with_files(tfile.path))

        confirm = self.fm.settings.confirm_on_delete
        if confirm != 'never' and (confirm != 'multiple' or many_files):
            self.fm.ui.console.ask(
                "Confirm deletion of: %s (y/N)" % ', '.join(files),
                partial(self._question_callback, files),
                ('n', 'N', 'y', 'Y'),
            )
        else:
            # no need for a confirmation, just delete
            self.fm.delete(files)

    def tab(self, tabnum):
        return self._tab_directory_content()

    def _question_callback(self, files, answer):
        if answer.lower() == 'y':
            self.fm.delete(files)


class trash(Command):
    """:trash

    Tries to move the selection or the files passed in arguments (if any) to
    the trash, using rifle rules with label "trash".
    The arguments use a shell-like escaping.

    "Selection" is defined as all the "marked files" (by default, you
    can mark files with space or v). If there are no marked files,
    use the "current file" (where the cursor is)

    When attempting to trash non-empty directories or multiple
    marked files, it will require a confirmation.
    """

    allow_abbrev = False
    escape_macros_for_shell = True

    def execute(self):
        import shlex
        from functools import partial

        def is_directory_with_files(path):
            return os.path.isdir(path) and not os.path.islink(path) and len(os.listdir(path)) > 0

        if self.rest(1):
            file_names = shlex.split(self.rest(1))
            files = self.fm.get_filesystem_objects(file_names)
            if files is None:
                return
            many_files = (len(files) > 1 or is_directory_with_files(files[0].path))
        else:
            cwd = self.fm.thisdir
            tfile = self.fm.thisfile
            if not cwd or not tfile:
                self.fm.notify("Error: no file selected for deletion!", bad=True)
                return

            files = self.fm.thistab.get_selection()
            # relative_path used for a user-friendly output in the confirmation.
            file_names = [f.relative_path for f in files]
            many_files = (cwd.marked_items or is_directory_with_files(tfile.path))

        confirm = self.fm.settings.confirm_on_trash

        if confirm == 'like_delete':
            confirm = self.fm.settings.confirm_on_delete

        if confirm != 'never' and (confirm != 'multiple' or many_files):
            self.fm.ui.console.ask(
                "Confirm deletion of: %s (y/N)" % ', '.join(file_names),
                partial(self._question_callback, files),
                ('n', 'N', 'y', 'Y'),
            )
        else:
            # no need for a confirmation, just delete
            self._trash_files_catch_arg_list_error(files)

    def tab(self, tabnum):
        return self._tab_directory_content()

    def _question_callback(self, files, answer):
        if answer.lower() == 'y':
            self._trash_files_catch_arg_list_error(files)

    def _trash_files_catch_arg_list_error(self, files):
        """
        Executes the fm.execute_file method but catches the OSError ("Argument list too long")
        that occurs when moving too many files to trash (and would otherwise crash ranger).
        """
        try:
            self.fm.execute_file(files, label='trash')
        except OSError as err:
            if err.errno == 7:
                self.fm.notify("Error: Command too long (try passing less files at once)",
                               bad=True)
            else:
                raise


class jump_non(Command):
    """:jump_non [-FLAGS...]

    Jumps to first non-directory if highlighted file is a directory and vice versa.

    Flags:
     -r    Jump in reverse order
     -w    Wrap around if reaching end of filelist
    """
    def __init__(self, *args, **kwargs):
        super(jump_non, self).__init__(*args, **kwargs)

        flags, _ = self.parse_flags()
        self._flag_reverse = 'r' in flags
        self._flag_wrap = 'w' in flags

    @staticmethod
    def _non(fobj, is_directory):
        return fobj.is_directory if not is_directory else not fobj.is_directory

    def execute(self):
        tfile = self.fm.thisfile
        passed = False
        found_before = None
        found_after = None
        for fobj in self.fm.thisdir.files[::-1] if self._flag_reverse else self.fm.thisdir.files:
            if fobj.path == tfile.path:
                passed = True
                continue

            if passed:
                if self._non(fobj, tfile.is_directory):
                    found_after = fobj.path
                    break
            elif not found_before and self._non(fobj, tfile.is_directory):
                found_before = fobj.path

        if found_after:
            self.fm.select_file(found_after)
        elif self._flag_wrap and found_before:
            self.fm.select_file(found_before)


class mark_tag(Command):
    """:mark_tag [<tags>]

    Mark all tags that are tagged with either of the given tags.
    When leaving out the tag argument, all tagged files are marked.
    """
    do_mark = True

    def execute(self):
        cwd = self.fm.thisdir
        tags = self.rest(1).replace(" ", "")
        if not self.fm.tags or not cwd.files:
            return
        for fileobj in cwd.files:
            try:
                tag = self.fm.tags.tags[fileobj.realpath]
            except KeyError:
                continue
            if not tags or tag in tags:
                cwd.mark_item(fileobj, val=self.do_mark)
        self.fm.ui.status.need_redraw = True
        self.fm.ui.need_redraw = True


class console(Command):
    """:console [-p N | -s sep] <command>

    Flags:
     -p N   Set position at N index
     -s sep Set position at separator(any char[s] sequence), example '#'
    Open the console with the given command.
    """

    def execute(self):
        position = None
        command = self.rest(1)
        if self.arg(1)[0:2] == '-p':
            command = self.rest(2)
            try:
                position = int(self.arg(1)[2:])
            except ValueError:
                pass
        elif self.arg(1)[0:2] == '-s':
            command = self.rest(3)
            sentinel = self.arg(2)
            pos = command.find(sentinel)
            if pos != -1:
                command = command.replace(sentinel, '', 1)
                position = pos
        self.fm.open_console(command, position=position)


class load_copy_buffer(Command):
    """:load_copy_buffer

    Load the copy buffer from datadir/copy_buffer
    """
    copy_buffer_filename = 'copy_buffer'

    def execute(self):
        from os.path import exists
        from ranger.container.file import File
        fname = self.fm.datapath(self.copy_buffer_filename)
        unreadable = OSError if PY3 else IOError
        try:
            with open(fname, "r", encoding="utf-8") as fobj:
                self.fm.copy_buffer = set(
                    File(g) for g in fobj.read().split("\n") if exists(g)
                )
        except unreadable:
            return self.fm.notify(
                "Cannot open %s" % (fname or self.copy_buffer_filename), bad=True)

        self.fm.ui.redraw_main_column()
        return None


class save_copy_buffer(Command):
    """:save_copy_buffer

    Save the copy buffer to datadir/copy_buffer
    """
    copy_buffer_filename = 'copy_buffer'

    def execute(self):
        fname = None
        fname = self.fm.datapath(self.copy_buffer_filename)
        unwritable = OSError if PY3 else IOError
        try:
            with open(fname, "w", encoding="utf-8") as fobj:
                fobj.write("\n".join(fobj.path for fobj in self.fm.copy_buffer))
        except unwritable:
            return self.fm.notify("Cannot open %s" %
                                  (fname or self.copy_buffer_filename), bad=True)
        return None


class unmark_tag(mark_tag):
    """:unmark_tag [<tags>]

    Unmark all tags that are tagged with either of the given tags.
    When leaving out the tag argument, all tagged files are unmarked.
    """
    do_mark = False


class mkdir(Command):
    """:mkdir <dirname>

    Creates a directory with the name <dirname>.
    """

    def execute(self):
        from os.path import join, expanduser, lexists
        from os import makedirs

        dirname = join(self.fm.thisdir.path, expanduser(self.rest(1)))
        if not lexists(dirname):
            makedirs(dirname)
        else:
            self.fm.notify("file/directory exists!", bad=True)

    def tab(self, tabnum):
        return self._tab_directory_content()


class touch(Command):
    """:touch <fname>

    Creates a file with the name <fname>.
    """

    def execute(self):
        from os.path import join, expanduser, lexists, dirname
        from os import makedirs

        fname = join(self.fm.thisdir.path, expanduser(self.rest(1)))
        dirname = dirname(fname)
        if not lexists(fname):
            if not lexists(dirname):
                makedirs(dirname)
            with open(fname, 'a', encoding="utf-8"):
                pass  # Just create the file
        else:
            self.fm.notify("file/directory exists!", bad=True)

    def tab(self, tabnum):
        return self._tab_directory_content()


class edit(Command):
    """:edit <filename>

    Opens the specified file in vim
    """

    def execute(self):
        if not self.arg(1):
            self.fm.edit_file(self.fm.thisfile.path)
        else:
            self.fm.edit_file(self.rest(1))

    def tab(self, tabnum):
        return self._tab_directory_content()


class eval_(Command):
    """:eval [-q] <python code>

    Evaluates the python code.
    `fm' is a reference to the FM instance.
    To display text, use the function `p'.

    Examples:
    :eval fm
    :eval len(fm.directories)
    :eval p("Hello World!")
    """
    name = 'eval'
    resolve_macros = False

    def execute(self):
        # The import is needed so eval() can access the ranger module
        import ranger  # NOQA pylint: disable=unused-import,unused-variable
        if self.arg(1) == '-q':
            code = self.rest(2)
            quiet = True
        else:
            code = self.rest(1)
            quiet = False
        global cmd, fm, p, quantifier  # pylint: disable=invalid-name,global-variable-undefined
        fm = self.fm
        cmd = self.fm.execute_console
        p = fm.notify
        quantifier = self.quantifier
        try:
            try:
                result = eval(code)  # pylint: disable=eval-used
            except SyntaxError:
                exec(code)  # pylint: disable=exec-used
            else:
                if result and not quiet:
                    p(result)
        except Exception as err:  # pylint: disable=broad-except
            fm.notify("The error `%s` was caused by evaluating the "
                      "following code: `%s`" % (err, code), bad=True)


class rename(Command):
    """:rename <newname>

    Changes the name of the currently highlighted file to <newname>
    """

    def execute(self):
        from ranger.container.file import File
        from os import access

        new_name = self.rest(1)

        if not new_name:
            return self.fm.notify('Syntax: rename <newname>', bad=True)

        if new_name == self.fm.thisfile.relative_path:
            return None

        if access(new_name, os.F_OK):
            return self.fm.notify("Can't rename: file already exists!", bad=True)

        if self.fm.rename(self.fm.thisfile, new_name):
            file_new = File(new_name)
            self.fm.bookmarks.update_path(self.fm.thisfile.path, file_new)
            self.fm.tags.update_path(self.fm.thisfile.path, file_new.path)
            self.fm.thisdir.pointed_obj = file_new
            self.fm.thisfile = file_new

        return None

    def tab(self, tabnum):
        return self._tab_directory_content()


class rename_append(Command):
    """:rename_append [-FLAGS...]

    Opens the console with ":rename <current file>" with the cursor positioned
    before the file extension.

    Flags:
     -a    Position before all extensions
     -r    Remove everything before extensions
    """
    def __init__(self, *args, **kwargs):
        super(rename_append, self).__init__(*args, **kwargs)

        flags, _ = self.parse_flags()
        self._flag_ext_all = 'a' in flags
        self._flag_remove = 'r' in flags

    def execute(self):
        from ranger import MACRO_DELIMITER, MACRO_DELIMITER_ESC

        tfile = self.fm.thisfile
        relpath = tfile.relative_path.replace(MACRO_DELIMITER, MACRO_DELIMITER_ESC)
        basename = tfile.basename.replace(MACRO_DELIMITER, MACRO_DELIMITER_ESC)

        if basename.find('.') <= 0 or os.path.isdir(relpath):
            self.fm.open_console('rename ' + relpath)
            return

        if self._flag_ext_all:
            pos_ext = re.search(r'[^.]+', basename).end(0)
        else:
            pos_ext = basename.rindex('.')
        pos = len(relpath) - len(basename) + pos_ext

        if self._flag_remove:
            relpath = relpath[:-len(basename)] + basename[pos_ext:]
            pos -= pos_ext

        self.fm.open_console('rename ' + relpath, position=(7 + pos))


class chmod(Command):
    """:chmod <octal number>

    Sets the permissions of the selection to the octal number.

    The octal number is between 0 and 777. The digits specify the
    permissions for the user, the group and others.

    A 1 permits execution, a 2 permits writing, a 4 permits reading.
    Add those numbers to combine them. So a 7 permits everything.
    """

    def execute(self):
        mode_str = self.rest(1)
        if not mode_str:
            if self.quantifier is None:
                self.fm.notify("Syntax: chmod <octal number> "
                               "or specify a quantifier", bad=True)
                return
            mode_str = str(self.quantifier)

        try:
            mode = int(mode_str, 8)
            if mode < 0 or mode > 0o777:
                raise ValueError
        except ValueError:
            self.fm.notify("Need an octal number between 0 and 777!", bad=True)
            return

        for fobj in self.fm.thistab.get_selection():
            try:
                os.chmod(fobj.path, mode)
            except OSError as ex:
                self.fm.notify(ex)

        # reloading directory.  maybe its better to reload the selected
        # files only.
        self.fm.thisdir.content_outdated = True


class bulkrename(Command):
    """:bulkrename

    This command opens a list of selected files in an external editor.
    After you edit and save the file, it will generate a shell script
    which does bulk renaming according to the changes you did in the file.

    This shell script is opened in an editor for you to review.
    After you close it, it will be executed.
    """

    def __init__(self, *args, **kwargs):
        super(bulkrename, self).__init__(*args, **kwargs)
        self.flags, _ = self.parse_flags()
        if not self.flags:
            self.flags = "w"

    def execute(self):
        # pylint: disable=too-many-locals,too-many-statements,too-many-branches
        import tempfile
        from ranger.container.file import File
        from ranger.ext.shell_escape import shell_escape as esc

        # Create and edit the file list
        filenames = [f.relative_path for f in self.fm.thistab.get_selection()]
        with tempfile.NamedTemporaryFile(delete=False) as listfile:
            listpath = listfile.name
            if PY3:
                listfile.write("\n".join(filenames).encode(
                    encoding="utf-8", errors="surrogateescape"))
            else:
                listfile.write("\n".join(filenames))
        self.fm.execute_file([File(listpath)], app='editor')
        with open(
            listpath, "r", encoding="utf-8", errors="surrogateescape"
        ) as listfile:
            new_filenames = listfile.read().split("\n")
        os.unlink(listpath)
        if all(a == b for a, b in zip(filenames, new_filenames)):
            self.fm.notify("No renaming to be done!")
            return

        # Generate script
        with tempfile.NamedTemporaryFile() as cmdfile:
            script_lines = []
            script_lines.append("# This file will be executed when you close"
                                " the editor.")
            script_lines.append("# Please double-check everything, clear the"
                                " file to abort.")
            new_dirs = []
            for old, new in zip(filenames, new_filenames):
                if old != new:
                    basepath, _ = os.path.split(new)
                    if (basepath and basepath not in new_dirs
                            and not os.path.isdir(basepath)):
                        script_lines.append("mkdir -vp -- {dir}".format(
                            dir=esc(basepath)))
                        new_dirs.append(basepath)
                    script_lines.append("mv -vi -- {old} {new}".format(
                        old=esc(old), new=esc(new)))
            # Make sure not to forget the ending newline
            script_content = "\n".join(script_lines) + "\n"
            if PY3:
                cmdfile.write(script_content.encode(encoding="utf-8",
                                                    errors="surrogateescape"))
            else:
                cmdfile.write(script_content)
            cmdfile.flush()

            # Open the script and let the user review it, then check if the
            # script was modified by the user
            self.fm.execute_file([File(cmdfile.name)], app='editor')
            cmdfile.seek(0)
            script_was_edited = (script_content != cmdfile.read())

            # Do the renaming
            self.fm.run(['/bin/sh', cmdfile.name], flags=self.flags)

        # Retag the files, but only if the script wasn't changed during review,
        # because only then we know which are the source and destination files.
        if not script_was_edited:
            tags_changed = False
            for old, new in zip(filenames, new_filenames):
                if old != new:
                    oldpath = self.fm.thisdir.path + '/' + old
                    newpath = self.fm.thisdir.path + '/' + new
                    if oldpath in self.fm.tags:
                        old_tag = self.fm.tags.tags[oldpath]
                        self.fm.tags.remove(oldpath)
                        self.fm.tags.tags[newpath] = old_tag
                        tags_changed = True
            if tags_changed:
                self.fm.tags.dump()
        else:
            fm.notify("files have not been retagged")


class relink(Command):
    """:relink <newpath>

    Changes the linked path of the currently highlighted symlink to <newpath>
    """

    def execute(self):
        new_path = self.rest(1)
        tfile = self.fm.thisfile

        if not new_path:
            return self.fm.notify('Syntax: relink <newpath>', bad=True)

        if not tfile.is_link:
            return self.fm.notify('%s is not a symlink!' % tfile.relative_path, bad=True)

        if new_path == os.readlink(tfile.path):
            return None

        try:
            os.remove(tfile.path)
            os.symlink(new_path, tfile.path)
        except OSError as err:
            self.fm.notify(err)

        self.fm.reset()
        self.fm.thisdir.pointed_obj = tfile
        self.fm.thisfile = tfile

        return None

    def tab(self, tabnum):
        if not self.rest(1):
            return self.line + os.readlink(self.fm.thisfile.path)
        return self._tab_directory_content()


class help_(Command):
    """:help

    Display ranger's manual page.
    """
    name = 'help'

    def execute(self):
        def callback(answer):
            if answer == "q":
                return
            elif answer == "m":
                self.fm.display_help()
            elif answer == "c":
                self.fm.dump_commands()
            elif answer == "k":
                self.fm.dump_keybindings()
            elif answer == "s":
                self.fm.dump_settings()

        self.fm.ui.console.ask(
            "View [m]an page, [k]ey bindings, [c]ommands or [s]ettings? (press q to abort)",
            callback,
            list("mqkcs")
        )


class copymap(Command):
    """:copymap <keys> <newkeys1> [<newkeys2>...]

    Copies a "browser" keybinding from <keys> to <newkeys>
    """
    context = 'browser'

    def execute(self):
        if not self.arg(1) or not self.arg(2):
            return self.fm.notify("Not enough arguments", bad=True)

        for arg in self.args[2:]:
            self.fm.ui.keymaps.copy(self.context, self.arg(1), arg)

        return None


class copypmap(copymap):
    """:copypmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "pager" keybinding from <keys> to <newkeys>
    """
    context = 'pager'


class copycmap(copymap):
    """:copycmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "console" keybinding from <keys> to <newkeys>
    """
    context = 'console'


class copytmap(copymap):
    """:copytmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "taskview" keybinding from <keys> to <newkeys>
    """
    context = 'taskview'


class unmap(Command):
    """:unmap <keys> [<keys2>, ...]

    Remove the given "browser" mappings
    """
    context = 'browser'

    def execute(self):
        for arg in self.args[1:]:
            self.fm.ui.keymaps.unbind(self.context, arg)


class uncmap(unmap):
    """:uncmap <keys> [<keys2>, ...]

    Remove the given "console" mappings
    """
    context = 'console'


class cunmap(uncmap):
    """:cunmap <keys> [<keys2>, ...]

    Remove the given "console" mappings

    DEPRECATED in favor of uncmap.
    """

    def execute(self):
        self.fm.notify("cunmap is deprecated in favor of uncmap!")
        super(cunmap, self).execute()


class unpmap(unmap):
    """:unpmap <keys> [<keys2>, ...]

    Remove the given "pager" mappings
    """
    context = 'pager'


class punmap(unpmap):
    """:punmap <keys> [<keys2>, ...]

    Remove the given "pager" mappings

    DEPRECATED in favor of unpmap.
    """

    def execute(self):
        self.fm.notify("punmap is deprecated in favor of unpmap!")
        super(punmap, self).execute()


class untmap(unmap):
    """:untmap <keys> [<keys2>, ...]

    Remove the given "taskview" mappings
    """
    context = 'taskview'


class tunmap(untmap):
    """:tunmap <keys> [<keys2>, ...]

    Remove the given "taskview" mappings

    DEPRECATED in favor of untmap.
    """

    def execute(self):
        self.fm.notify("tunmap is deprecated in favor of untmap!")
        super(tunmap, self).execute()


class map_(Command):
    """:map <keysequence> <command>

    Maps a command to a keysequence in the "browser" context.

    Example:
    map j move down
    map J move down 10
    """
    name = 'map'
    context = 'browser'
    resolve_macros = False

    def execute(self):
        if not self.arg(1) or not self.arg(2):
            self.fm.notify("Syntax: {0} <keysequence> <command>".format(self.get_name()), bad=True)
            return

        self.fm.ui.keymaps.bind(self.context, self.arg(1), self.rest(2))


class cmap(map_):
    """:cmap <keysequence> <command>

    Maps a command to a keysequence in the "console" context.

    Example:
    cmap <ESC> console_close
    cmap <C-x> console_type test
    """
    context = 'console'


class tmap(map_):
    """:tmap <keysequence> <command>

    Maps a command to a keysequence in the "taskview" context.
    """
    context = 'taskview'


class pmap(map_):
    """:pmap <keysequence> <command>

    Maps a command to a keysequence in the "pager" context.
    """
    context = 'pager'


class scout(Command):
    """:scout [-FLAGS...] <pattern>

    Swiss army knife command for searching, traveling and filtering files.

    Flags:
     -a    Automatically open a file on unambiguous match
     -e    Open the selected file when pressing enter
     -f    Filter files that match the current search pattern
     -g    Interpret pattern as a glob pattern
     -i    Ignore the letter case of the files
     -k    Keep the console open when changing a directory with the command
     -l    Letter skipping; e.g. allow "rdme" to match the file "readme"
     -m    Mark the matching files after pressing enter
     -M    Unmark the matching files after pressing enter
     -p    Permanent filter: hide non-matching files after pressing enter
     -r    Interpret pattern as a regular expression pattern
     -s    Smart case; like -i unless pattern contains upper case letters
     -t    Apply filter and search pattern as you type
     -v    Inverts the match

    Multiple flags can be combined.  For example, ":scout -gpt" would create
    a :filter-like command using globbing.
    """

    AUTO_OPEN = "a"
    OPEN_ON_ENTER = "e"
    FILTER = "f"
    SM_GLOB = "g"
    IGNORE_CASE = "i"
    KEEP_OPEN = "k"
    SM_LETTERSKIP = "l"
    MARK = "m"
    UNMARK = "M"
    PERM_FILTER = "p"
    SM_REGEX = "r"
    SMART_CASE = "s"
    AS_YOU_TYPE = "t"
    INVERT = "v"

    def __init__(self, *args, **kwargs):
        super(scout, self).__init__(*args, **kwargs)
        self._regex = None
        self.flags, self.pattern = self.parse_flags()

    def execute(self):  # pylint: disable=too-many-branches
        thisdir = self.fm.thisdir
        flags = self.flags
        pattern = self.pattern
        regex = self._build_regex()
        count = self._count(move=True)

        self.fm.thistab.last_search = regex
        self.fm.set_search_method(order="search")

        if (self.MARK in flags or self.UNMARK in flags) and thisdir.files:
            value = flags.find(self.MARK) > flags.find(self.UNMARK)
            if self.FILTER in flags:
                for fobj in thisdir.files:
                    thisdir.mark_item(fobj, value)
            else:
                for fobj in thisdir.files:
                    if regex.search(fobj.relative_path):
                        thisdir.mark_item(fobj, value)

        if self.PERM_FILTER in flags:
            thisdir.filter = regex if pattern else None

        # clean up:
        self.cancel()

        if self.OPEN_ON_ENTER in flags or \
                (self.AUTO_OPEN in flags and count == 1):
            if pattern == '..':
                self.fm.cd(pattern)
            else:
                self.fm.move(right=1)
                if self.quickly_executed:
                    self.fm.block_input(0.5)

        if self.KEEP_OPEN in flags and thisdir != self.fm.thisdir:
            # reopen the console:
            if not pattern:
                self.fm.open_console(self.line)
            else:
                self.fm.open_console(self.line[0:-len(pattern)])

        if self.quickly_executed and thisdir != self.fm.thisdir and pattern != "..":
            self.fm.block_input(0.5)

    def cancel(self):
        self.fm.thisdir.temporary_filter = None
        self.fm.thisdir.refilter()

    def quick(self):
        asyoutype = self.AS_YOU_TYPE in self.flags
        if self.FILTER in self.flags:
            self.fm.thisdir.temporary_filter = self._build_regex()
        if self.PERM_FILTER in self.flags and asyoutype:
            self.fm.thisdir.filter = self._build_regex()
        if self.FILTER in self.flags or self.PERM_FILTER in self.flags:
            self.fm.thisdir.refilter()
        if self._count(move=asyoutype) == 1 and self.AUTO_OPEN in self.flags:
            return True
        return False

    def tab(self, tabnum):
        self._count(move=True, offset=tabnum)

    def _build_regex(self):
        if self._regex is not None:
            return self._regex

        frmat = "%s"
        flags = self.flags
        pattern = self.pattern

        if pattern == ".":
            return re.compile("")

        # Handle carets at start and dollar signs at end separately
        if pattern.startswith('^'):
            pattern = pattern[1:]
            frmat = "^" + frmat
        if pattern.endswith('$'):
            pattern = pattern[:-1]
            frmat += "$"

        # Apply one of the search methods
        if self.SM_REGEX in flags:
            regex = pattern
        elif self.SM_GLOB in flags:
            regex = re.escape(pattern).replace("\\*", ".*").replace("\\?", ".")
        elif self.SM_LETTERSKIP in flags:
            regex = ".*".join(re.escape(c) for c in pattern)
        else:
            regex = re.escape(pattern)

        regex = frmat % regex

        # Invert regular expression if necessary
        if self.INVERT in flags:
            regex = "^(?:(?!%s).)*$" % regex

        # Compile Regular Expression
        # pylint: disable=no-member
        options = re.UNICODE
        if self.IGNORE_CASE in flags or self.SMART_CASE in flags and \
                pattern.islower():
            options |= re.IGNORECASE
        # pylint: enable=no-member
        try:
            self._regex = re.compile(regex, options)
        except re.error:
            self._regex = re.compile("")
        return self._regex

    def _count(self, move=False, offset=0):
        count = 0
        cwd = self.fm.thisdir
        pattern = self.pattern

        if not pattern or not cwd.files:
            return 0
        if pattern == '.':
            return 0
        if pattern == '..':
            return 1

        deq = deque(cwd.files)
        deq.rotate(-cwd.pointer - offset)
        i = offset
        regex = self._build_regex()
        for fsobj in deq:
            if regex.search(fsobj.relative_path):
                count += 1
                if move and count == 1:
                    cwd.move(to=(cwd.pointer + i) % len(cwd.files))
                    self.fm.thisfile = cwd.pointed_obj
            if count > 1:
                return count
            i += 1

        return count == 1


class narrow(Command):
    """
    :narrow

    Show only the files selected right now. If no files are selected,
    disable narrowing.

    To disable narrow mode when selection is still active, use the
    :unnarrow command.
    """

    def execute(self):
        # Calling :narrow enables narrow mode unless it is called with a
        # case-insensitive `false` argument
        narrow_mode = self.arg(1).lower() != "false"

        if narrow_mode and self.fm.thisdir.marked_items:
            selection = [f.basename for f in self.fm.thistab.get_selection()]
            self.fm.thisdir.narrow_filter = selection
        else:
            self.fm.thisdir.narrow_filter = None

        self.fm.thisdir.refilter()


class filter_inode_type(Command):
    """
    :filter_inode_type [dfl]

    Displays only the files of specified inode type. Parameters
    can be combined.

        d display directories
        f display files
        l display links
    """

    def execute(self):
        if not self.arg(1):
            self.fm.thisdir.inode_type_filter = ""
        else:
            self.fm.thisdir.inode_type_filter = self.arg(1)
        self.fm.thisdir.refilter()


class filter_stack(Command):
    """
    :filter_stack ...

    Manages the filter stack.

        filter_stack add FILTER_TYPE ARGS...
        filter_stack pop
        filter_stack decompose
        filter_stack rotate [N=1]
        filter_stack clear
        filter_stack show
    """
    def execute(self):
        from ranger.core.filter_stack import SIMPLE_FILTERS, FILTER_COMBINATORS

        subcommand = self.arg(1)

        if subcommand == "add":
            try:
                self.fm.thisdir.filter_stack.append(
                    SIMPLE_FILTERS[self.arg(2)](self.rest(3))
                )
            except KeyError:
                FILTER_COMBINATORS[self.arg(2)](self.fm.thisdir.filter_stack)
        elif subcommand == "pop":
            self.fm.thisdir.filter_stack.pop()
        elif subcommand == "decompose":
            inner_filters = self.fm.thisdir.filter_stack.pop().decompose()
            if inner_filters:
                self.fm.thisdir.filter_stack.extend(inner_filters)
        elif subcommand == "clear":
            self.fm.thisdir.filter_stack = []
        elif subcommand == "rotate":
            rotate_by = int(self.arg(2) or self.quantifier or 1)
            self.fm.thisdir.filter_stack = (
                self.fm.thisdir.filter_stack[-rotate_by:]
                + self.fm.thisdir.filter_stack[:-rotate_by]
            )
        elif subcommand == "show":
            stack = list(map(str, self.fm.thisdir.filter_stack))
            pager = self.fm.ui.open_pager()
            pager.set_source(["Filter stack: "] + stack)
            pager.move(to=100, percentage=True)
            return
        else:
            self.fm.notify(
                "Unknown subcommand: {sub}".format(sub=subcommand),
                bad=True
            )
            return

        # Cleanup.
        self.cancel()

    def quick(self):
        if self.rest(1).startswith("add name "):
            try:
                regex = re.compile(self.rest(3))
            except re.error:
                regex = re.compile("")
            self.fm.thisdir.temporary_filter = regex
            self.fm.thisdir.refilter()

        return False

    def cancel(self):
        self.fm.thisdir.temporary_filter = None
        self.fm.thisdir.refilter()


class grep(Command):
    """:grep <string>

    Looks for a string in all marked files or directories
    """

    def execute(self):
        if self.rest(1):
            action = ['grep', '-n']
            action.extend(['-e', self.rest(1), '-r'])
            action.extend(f.path for f in self.fm.thistab.get_selection())
            self.fm.execute_command(action, flags='p')


class flat(Command):
    """
    :flat <level>

    Flattens the directory view up to the specified level.

        -1 fully flattened
         0 remove flattened view
    """

    def execute(self):
        try:
            level_str = self.rest(1)
            level = int(level_str)
        except ValueError:
            level = self.quantifier
        if level is None:
            self.fm.notify("Syntax: flat <level>", bad=True)
            return
        if level < -1:
            self.fm.notify("Need an integer number (-1, 0, 1, ...)", bad=True)
        self.fm.thisdir.unload()
        self.fm.thisdir.flat = level
        self.fm.thisdir.load_content()


class reset_previews(Command):
    """:reset_previews

    Reset the file previews.
    """
    def execute(self):
        self.fm.previews = {}
        self.fm.ui.need_redraw = True


# Version control commands
# --------------------------------


class stage(Command):
    """
    :stage

    Stage selected files for the corresponding version control system
    """

    def execute(self):
        from ranger.ext.vcs import VcsError

        if self.fm.thisdir.vcs and self.fm.thisdir.vcs.track:
            filelist = [f.path for f in self.fm.thistab.get_selection()]
            try:
                self.fm.thisdir.vcs.action_add(filelist)
            except VcsError as ex:
                self.fm.notify('Unable to stage files: {0}'.format(ex))
            self.fm.ui.vcsthread.process(self.fm.thisdir)
        else:
            self.fm.notify('Unable to stage files: Not in repository')


class unstage(Command):
    """
    :unstage

    Unstage selected files for the corresponding version control system
    """

    def execute(self):
        from ranger.ext.vcs import VcsError

        if self.fm.thisdir.vcs and self.fm.thisdir.vcs.track:
            filelist = [f.path for f in self.fm.thistab.get_selection()]
            try:
                self.fm.thisdir.vcs.action_reset(filelist)
            except VcsError as ex:
                self.fm.notify('Unable to unstage files: {0}'.format(ex))
            self.fm.ui.vcsthread.process(self.fm.thisdir)
        else:
            self.fm.notify('Unable to unstage files: Not in repository')

# Metadata commands
# --------------------------------


class prompt_metadata(Command):
    """
    :prompt_metadata <key1> [<key2> [<key3> ...]]

    Prompt the user to input metadata for multiple keys in a row.
    """

    _command_name = "meta"
    _console_chain = None

    def execute(self):
        prompt_metadata._console_chain = self.args[1:]
        self._process_command_stack()

    def _process_command_stack(self):
        if prompt_metadata._console_chain:
            key = prompt_metadata._console_chain.pop()
            self._fill_console(key)
        else:
            for col in self.fm.ui.browser.columns:
                col.need_redraw = True

    def _fill_console(self, key):
        metadata = self.fm.metadata.get_metadata(self.fm.thisfile.path)
        if key in metadata and metadata[key]:
            existing_value = metadata[key]
        else:
            existing_value = ""
        text = "%s %s %s" % (self._command_name, key, existing_value)
        self.fm.open_console(text, position=len(text))


class meta(prompt_metadata):
    """
    :meta <key> [<value>]

    Change metadata of a file.  Deletes the key if value is empty.
    """

    def execute(self):
        key = self.arg(1)
        update_dict = {}
        update_dict[key] = self.rest(2)
        selection = self.fm.thistab.get_selection()
        for fobj in selection:
            self.fm.metadata.set_metadata(fobj.path, update_dict)
        self._process_command_stack()

    def tab(self, tabnum):
        key = self.arg(1)
        metadata = self.fm.metadata.get_metadata(self.fm.thisfile.path)
        if key in metadata and metadata[key]:
            return [" ".join([self.arg(0), self.arg(1), metadata[key]])]
        return [self.arg(0) + " " + k for k in sorted(metadata)
                if k.startswith(self.arg(1))]


class linemode(default_linemode):
    """
    :linemode <mode>

    Change what is displayed as a filename.

    - "mode" may be any of the defined linemodes (see: ranger.core.linemode).
      "normal" is mapped to "filename".
    """

    def execute(self):
        mode = self.arg(1)

        if mode == "normal":
            from ranger.core.linemode import DEFAULT_LINEMODE
            mode = DEFAULT_LINEMODE

        if mode not in self.fm.thisfile.linemode_dict:
            self.fm.notify("Unhandled linemode: `%s'" % mode, bad=True)
            return

        self.fm.thisdir.set_linemode_of_children(mode)

        # Ask the browsercolumns to redraw
        for col in self.fm.ui.browser.columns:
            col.need_redraw = True


class yank(Command):
    """:yank [name|dir|path|name_without_extension]

    Copies the file's name (default), directory or path into both the primary X
    selection and the clipboard.
    """

    modes = {
        '': 'basename',
        'name_without_extension': 'basename_without_extension',
        'name': 'basename',
        'dir': 'dirname',
        'path': 'path',
    }

    def execute(self):
        import subprocess

        def clipboards():
            from ranger.ext.get_executables import get_executables
            clipboard_managers = {
                'xclip': [
                    ['xclip'],
                    ['xclip', '-selection', 'clipboard'],
                ],
                'xsel': [
                    ['xsel'],
                    ['xsel', '-b'],
                ],
                'wl-copy': [
                    ['wl-copy'],
                ],
                'pbcopy': [
                    ['pbcopy'],
                ],
            }
            ordered_managers = ['pbcopy', 'xclip', 'xsel', 'wl-copy']
            executables = get_executables()
            for manager in ordered_managers:
                if manager in executables:
                    return clipboard_managers[manager]
            return []

        clipboard_commands = clipboards()

        mode = self.modes[self.arg(1)]
        selection = self.get_selection_attr(mode)

        new_clipboard_contents = "\n".join(selection)
        for command in clipboard_commands:
            with subprocess.Popen(
                command, universal_newlines=True, stdin=subprocess.PIPE
            ) as process:
                process.communicate(input=new_clipboard_contents)

    def get_selection_attr(self, attr):
        return [getattr(item, attr) for item in
                self.fm.thistab.get_selection()]

    def tab(self, tabnum):
        return (
            self.start(1) + mode for mode
            in sorted(self.modes.keys())
            if mode
        )


class paste_ext(Command):
    """
    :paste_ext

    Like paste but tries to rename conflicting files so that the
    file extension stays intact (e.g. file_.ext).
    """

    @staticmethod
    def make_safe_path(dst):
        if not os.path.exists(dst):
            return dst

        dst_name, dst_ext = os.path.splitext(dst)

        if not dst_name.endswith("_"):
            dst_name += "_"
            if not os.path.exists(dst_name + dst_ext):
                return dst_name + dst_ext
        n = 0
        test_dst = dst_name + str(n)
        while os.path.exists(test_dst + dst_ext):
            n += 1
            test_dst = dst_name + str(n)

        return test_dst + dst_ext

    def execute(self):
        return self.fm.paste(make_safe_path=paste_ext.make_safe_path)

# ===================================================================
# AI Research Student Custom Commands
# ===================================================================

class dataset_number(Command):
    """:dataset_number [directory]
    
    Rename all files in the specified directory with sequential numbers.
    Format: 00000001.ext, 00000002.ext, etc.
    Returns error if directory contains subdirectories.
    """
    
    def execute(self):
        import os
        from datetime import datetime
        
        # Get target directory
        if self.arg(1):
            target_dir = os.path.expanduser(self.arg(1))
        else:
            # Use current selected directory
            if self.fm.thisfile.is_directory:
                target_dir = self.fm.thisfile.path
            else:
                self.fm.notify("Please specify a directory or select one", bad=True)
                return
        
        if not os.path.isdir(target_dir):
            self.fm.notify("Not a valid directory", bad=True)
            return
        
        # Check for subdirectories
        items = os.listdir(target_dir)
        for item in items:
            item_path = os.path.join(target_dir, item)
            if os.path.isdir(item_path):
                self.fm.notify("Error: Directory contains subdirectories", bad=True)
                return
        
        # Get all files and sort them
        files = [f for f in items if os.path.isfile(os.path.join(target_dir, f))]
        files.sort()
        
        if not files:
            self.fm.notify("No files found in directory", bad=True)
            return
        
        # Rename files
        temp_names = []
        for idx, filename in enumerate(files, start=1):
            old_path = os.path.join(target_dir, filename)
            ext = os.path.splitext(filename)[1]
            new_name = "{:08d}{}".format(idx, ext)
            temp_name = "temp_{}".format(new_name)
            temp_path = os.path.join(target_dir, temp_name)
            
            os.rename(old_path, temp_path)
            temp_names.append((temp_path, os.path.join(target_dir, new_name)))
        
        # Final rename
        for temp_path, final_path in temp_names:
            os.rename(temp_path, final_path)
        
        self.fm.notify("Successfully numbered {} files".format(len(files)))
        self.fm.reload_cwd()
    
    def tab(self, tabnum):
        return self._tab_directory_content()


class dataset_split(Command):
    """:dataset_split <directory> <x:y:z> [-c|-o|-s] [-d true|false] [-n <name>]
    
    Split dataset into train/val/test sets according to YOLO format.
    
    Arguments:
    - directory: path to original dataset
    - x:y:z: ratio for train:val:test (e.g., 7:2:1 or 8:2:0)
    - -c: classification task
    - -o: object detection task
    - -s: instance segmentation task
    - -d: add date prefix (default: false)
    - -n: specify custom dataset name (default: use original name)
    
    Examples:
    :dataset_split ~/dataset 7:2:1 -c
    :dataset_split ~/dataset 8:2:0 -o -d false
    :dataset_split ~/dataset 7:2:1 -c -n my_custom_dataset
    :dataset_split ~/dataset 8:2:0 -o -d true -n experiment_v2
    """
    
    def execute(self):
        import os
        import shutil
        import random
        from datetime import datetime
        
        # Parse arguments
        if len(self.args) < 3:
            self.fm.notify("Usage: dataset_split <directory> <x:y:z> [-c|-o|-s] [-d true|false] [-n <name>]", bad=True)
            return
        
        src_dir = os.path.expanduser(self.arg(1))
        ratio_str = self.arg(2)
        
        # Parse ratio
        try:
            ratios = [int(x) for x in ratio_str.split(':')]
            if len(ratios) != 3 or any(r < 0 for r in ratios):
                raise ValueError
            train_ratio, val_ratio, test_ratio = ratios
            total = sum(ratios)
            if total == 0:
                raise ValueError("Ratios cannot all be zero")
        except:
            self.fm.notify("Invalid ratio format. Use x:y:z (e.g., 7:2:1 or 8:2:0)", bad=True)
            return
        
        # Parse task type, date option, and custom name
        task_type = None
        add_date = False
        custom_name = None
        
        i = 3
        while i < len(self.args):
            arg = self.args[i]
            if arg in ['-c', '-o', '-s']:
                task_type = arg[1:]  # 'c', 'o', or 's'
                i += 1
            elif arg == '-d':
                # Check next argument
                if i + 1 < len(self.args):
                    add_date = self.args[i + 1].lower() == 'true'
                    i += 2
                else:
                    i += 1
            elif arg == '-n':
                # Get custom name from next argument
                if i + 1 < len(self.args):
                    custom_name = self.args[i + 1]
                    i += 2
                else:
                    self.fm.notify("Please provide a name after -n", bad=True)
                    return
            else:
                i += 1
        
        if not task_type:
            self.fm.notify("Please specify task type: -c, -o, or -s", bad=True)
            return
        
        if not os.path.isdir(src_dir):
            self.fm.notify("Source directory does not exist", bad=True)
            return
        
        # Create new dataset name
        date_prefix = datetime.now().strftime("%Y%m%d") + "_" if add_date else ""
        
        # Use custom name if provided, otherwise use original directory name
        if custom_name:
            dataset_name = custom_name
        else:
            dataset_name = os.path.basename(src_dir.rstrip('/'))
        
        new_dataset_name = date_prefix + dataset_name
        parent_dir = os.path.dirname(src_dir.rstrip('/'))
        dst_dir = os.path.join(parent_dir, new_dataset_name)
        
        if os.path.exists(dst_dir):
            self.fm.notify("Destination directory already exists", bad=True)
            return
        
        try:
            if task_type == 'c':
                self._split_classification(src_dir, dst_dir, train_ratio, val_ratio, test_ratio, total)
            elif task_type in ['o', 's']:
                self._split_detection_segmentation(src_dir, dst_dir, train_ratio, val_ratio, test_ratio, total)
            
            self.fm.notify("Dataset split successfully: {}".format(new_dataset_name))
            self.fm.reload_cwd()
        except Exception as e:
            self.fm.notify("Error: {}".format(str(e)), bad=True)
    
    def _split_classification(self, src_dir, dst_dir, train_r, val_r, test_r, total):
        import os
        import shutil
        import random
        
        # Get all class directories
        classes = [d for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d))]
        
        if not classes:
            raise ValueError("No class directories found")
        
        # Determine which splits to create
        splits_to_create = ['train']
        if val_r > 0:
            splits_to_create.append('val')
        if test_r > 0:
            splits_to_create.append('test')
        
        # Create destination structure
        for split in splits_to_create:
            for class_name in classes:
                os.makedirs(os.path.join(dst_dir, split, class_name), exist_ok=True)
        
        # Split each class
        for class_name in classes:
            class_path = os.path.join(src_dir, class_name)
            files = [f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))]
            
            random.shuffle(files)
            
            # Calculate split indices
            n_train = int(len(files) * train_r / total)
            n_val = int(len(files) * val_r / total)
            # n_test will be the remainder
            
            train_files = files[:n_train]
            val_files = files[n_train:n_train + n_val]
            test_files = files[n_train + n_val:]
            
            # Copy files
            for f in train_files:
                shutil.copy2(os.path.join(class_path, f), os.path.join(dst_dir, 'train', class_name, f))
            
            if val_r > 0:
                for f in val_files:
                    shutil.copy2(os.path.join(class_path, f), os.path.join(dst_dir, 'val', class_name, f))
            
            if test_r > 0:
                for f in test_files:
                    shutil.copy2(os.path.join(class_path, f), os.path.join(dst_dir, 'test', class_name, f))
    
    def _split_detection_segmentation(self, src_dir, dst_dir, train_r, val_r, test_r, total):
        import os
        import shutil
        import random
        
        # Check for image and label directories
        image_dir = os.path.join(src_dir, 'images')
        label_dir = os.path.join(src_dir, 'labels')
        
        if not os.path.isdir(image_dir) or not os.path.isdir(label_dir):
            raise ValueError("Dataset must contain 'images' and 'labels' directories")
        
        # Get all image files
        image_files = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
        
        # Match images with labels (by base name)
        matched_pairs = []
        for img_file in image_files:
            base_name = os.path.splitext(img_file)[0]
            # Find corresponding label file
            label_files = [f for f in os.listdir(label_dir) if os.path.splitext(f)[0] == base_name]
            if label_files:
                matched_pairs.append((img_file, label_files[0]))
        
        if not matched_pairs:
            raise ValueError("No matching image-label pairs found")
        
        random.shuffle(matched_pairs)
        
        # Calculate split indices
        n_train = int(len(matched_pairs) * train_r / total)
        n_val = int(len(matched_pairs) * val_r / total)
        # n_test will be the remainder
        
        train_pairs = matched_pairs[:n_train]
        val_pairs = matched_pairs[n_train:n_train + n_val]
        test_pairs = matched_pairs[n_train + n_val:]
        
        # Determine which splits to create
        splits_to_create = ['train']
        if val_r > 0:
            splits_to_create.append('val')
        if test_r > 0:
            splits_to_create.append('test')
        
        # Create destination structure
        for split in splits_to_create:
            os.makedirs(os.path.join(dst_dir, 'images', split), exist_ok=True)
            os.makedirs(os.path.join(dst_dir, 'labels', split), exist_ok=True)
        
        # Copy files
        for img, lbl in train_pairs:
            shutil.copy2(os.path.join(image_dir, img), os.path.join(dst_dir, 'images', 'train', img))
            shutil.copy2(os.path.join(label_dir, lbl), os.path.join(dst_dir, 'labels', 'train', lbl))
        
        if val_r > 0:
            for img, lbl in val_pairs:
                shutil.copy2(os.path.join(image_dir, img), os.path.join(dst_dir, 'images', 'val', img))
                shutil.copy2(os.path.join(label_dir, lbl), os.path.join(dst_dir, 'labels', 'val', lbl))
        
        if test_r > 0:
            for img, lbl in test_pairs:
                shutil.copy2(os.path.join(image_dir, img), os.path.join(dst_dir, 'images', 'test', img))
                shutil.copy2(os.path.join(label_dir, lbl), os.path.join(dst_dir, 'labels', 'test', lbl))
    
    def tab(self, tabnum):
        return self._tab_directory_content()

class package_training(Command):
    """:package_training <train_script> <test_script> <runs_dir> <env_file> [-c|--compress]
    
    Package the latest training results with training and testing scripts.
    Creates a zip file named with current date (YYYYMMDD.zip).
    Use -c or --compress for smaller file size (slower compression).
    
    Arguments:
    - train_script: path to training script (.py)
    - test_script: path to testing script (.py)
    - runs_dir: path to runs directory
    - env_file: path to environment file (e.g., requirements.txt, environment.yml)
    - -c, --compress: use compression for smaller file size (default: no compression, faster)
    
    Examples:
    :package_training ~/train.py ~/test.py ~/runs ~/requirements.txt
    :package_training ~/train.py ~/test.py ~/runs ~/requirements.txt -c
    :package_training ~/train.py ~/test.py ~/runs ~/environment.yml --compress
    """
    
    def execute(self):
        import os
        import zipfile
        from datetime import datetime
        
        # Parse arguments
        compress_mode = False
        args_list = []
        
        for arg in self.args[1:]:
            if arg in ['-c', '--compress']:
                compress_mode = True
            else:
                args_list.append(arg)
        
        if len(args_list) < 4:
            self.fm.notify("Usage: package_training <train_script> <test_script> <runs_dir> <env_file> [-c]", bad=True)
            return
        
        train_script = os.path.expanduser(args_list[0])
        test_script = os.path.expanduser(args_list[1])
        runs_dir = os.path.expanduser(args_list[2])
        env_file = os.path.expanduser(args_list[3])
        
        # Validate inputs
        if not os.path.isfile(train_script):
            self.fm.notify("Training script not found", bad=True)
            return
        
        if not os.path.isfile(test_script):
            self.fm.notify("Testing script not found", bad=True)
            return
        
        if not os.path.isdir(runs_dir):
            self.fm.notify("Runs directory not found", bad=True)
            return
        
        if not os.path.isfile(env_file):
            self.fm.notify("Environment file not found", bad=True)
            return
        
        # Find the most recent directory in runs
        subdirs = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
        
        if not subdirs:
            self.fm.notify("No training results found in runs directory", bad=True)
            return
        
        # Get the most recently created directory
        subdirs_with_time = [(d, os.path.getctime(os.path.join(runs_dir, d))) for d in subdirs]
        subdirs_with_time.sort(key=lambda x: x[1], reverse=True)
        latest_run = subdirs_with_time[0][0]
        latest_run_path = os.path.join(runs_dir, latest_run)
        
        # Create zip file name
        zip_name = datetime.now().strftime("%Y%m%d") + ".zip"
        zip_path = os.path.join(os.path.dirname(train_script), zip_name)
        
        if os.path.exists(zip_path):
            self.fm.notify("Zip file already exists: {}".format(zip_name), bad=True)
            return
        
        # Choose compression method (預設為快速模式，不壓縮)
        compression = zipfile.ZIP_DEFLATED if compress_mode else zipfile.ZIP_STORED
        compress_level = 6 if compress_mode else 0  # 6=balanced compression, 0=no compression
        
        try:
            # Show start message
            mode_msg = "compressed mode" if compress_mode else "fast mode (no compression)"
            self.fm.notify("Creating archive ({})...".format(mode_msg))
            
            # Count total files for progress
            total_files = 3  # train_script + test_script + env_file
            for root, dirs, files in os.walk(latest_run_path):
                total_files += len(files)
            
            processed_files = 0
            
            # Create zip file
            with zipfile.ZipFile(zip_path, 'w', compression, compresslevel=compress_level) as zipf:
                # Add training script
                zipf.write(train_script, os.path.basename(train_script))
                processed_files += 1
                
                # Add testing script
                zipf.write(test_script, os.path.basename(test_script))
                processed_files += 1
                
                # Add environment file
                zipf.write(env_file, os.path.basename(env_file))
                processed_files += 1
                
                # Add latest run directory
                for root, dirs, files in os.walk(latest_run_path):
                    # Filter out large unnecessary files
                    files_to_add = []
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        
                        # Skip very large files (>100MB) - optional
                        # if file_size > 100 * 1024 * 1024:
                        #     continue
                        
                        files_to_add.append(file)
                    
                    for file in files_to_add:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(latest_run, os.path.relpath(file_path, latest_run_path))
                        zipf.write(file_path, arcname)
                        
                        processed_files += 1
                        
                        # Show progress every 10 files
                        if processed_files % 10 == 0:
                            progress = int(processed_files * 100 / total_files)
                            self.fm.notify("Packing... {}% ({}/{})".format(
                                progress, processed_files, total_files))
            
            # Get final file size
            zip_size = os.path.getsize(zip_path)
            size_mb = zip_size / (1024 * 1024)
            
            # Show summary
            self.fm.notify("Successfully created: {} ({:.1f} MB) - {}".format(
                zip_name, size_mb, mode_msg))
            self.fm.reload_cwd()
            
        except Exception as e:
            self.fm.notify("Error creating zip: {}".format(str(e)), bad=True)
            # Clean up partial zip file
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass
    
    def tab(self, tabnum):
        return self._tab_directory_content()


class add_date_prefix(Command):
    """:add_date_prefix [directory] [-r|--recursive]
    
    Add date prefix (YYYYMMDD_) to all files in the specified directory.
    Use -r or --recursive to recursively rename files in subdirectories.
    
    Examples:
    :add_date_prefix ~/my_folder
    :add_date_prefix ~/my_folder -r
    :add_date_prefix -r  (use current selected directory)
    """
    
    def execute(self):
        import os
        from datetime import datetime
        
        # Parse arguments
        recursive = False
        target_dir = None
        
        for arg in self.args[1:]:
            if arg in ['-r', '--recursive']:
                recursive = True
            else:
                target_dir = os.path.expanduser(arg)
        
        # Get target directory
        if not target_dir:
            # Use current selected directory
            if self.fm.thisfile.is_directory:
                target_dir = self.fm.thisfile.path
            else:
                self.fm.notify("Please specify a directory or select one", bad=True)
                return
        
        if not os.path.isdir(target_dir):
            self.fm.notify("Not a valid directory", bad=True)
            return
        
        # Get date prefix
        date_prefix = datetime.now().strftime("%Y%m%d") + "_"
        
        renamed_count = 0
        skipped_count = 0
        error_count = 0
        
        if recursive:
            # Recursively process all subdirectories
            for root, dirs, files in os.walk(target_dir, topdown=False):
                for filename in files:
                    result = self._rename_file(root, filename, date_prefix)
                    if result == "renamed":
                        renamed_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                    elif result == "error":
                        error_count += 1
        else:
            # Only process files in the target directory (not subdirectories)
            files = [f for f in os.listdir(target_dir) 
                    if os.path.isfile(os.path.join(target_dir, f))]
            
            for filename in files:
                result = self._rename_file(target_dir, filename, date_prefix)
                if result == "renamed":
                    renamed_count += 1
                elif result == "skipped":
                    skipped_count += 1
                elif result == "error":
                    error_count += 1
        
        # Show summary
        msg = "Renamed: {}, Skipped: {}, Errors: {}".format(
            renamed_count, skipped_count, error_count)
        self.fm.notify(msg)
        self.fm.reload_cwd()
    
    def _rename_file(self, directory, filename, date_prefix):
        """
        Rename a single file with date prefix.
        Returns: "renamed", "skipped", or "error"
        """
        import os
        
        # Skip if already has date prefix
        if filename.startswith(date_prefix):
            return "skipped"
        
        old_path = os.path.join(directory, filename)
        new_path = os.path.join(directory, date_prefix + filename)
        
        if os.path.exists(new_path):
            return "skipped"
        
        try:
            os.rename(old_path, new_path)
            return "renamed"
        except Exception as e:
            return "error"
    
    def tab(self, tabnum):
        return self._tab_directory_content()
