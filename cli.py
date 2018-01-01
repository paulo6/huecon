#
# cli.py - CLI util classes
#
import cmd as pycmd
import traceback


class Error(Exception):
    """Base exception for this module."""
    pass


class CommandError(Error):
    """
    Special exception raised when a command execution fails.

    """
    pass


class Interface:
    """
    Implements a generic CLI command interface

    """
    intro = ""
    prompt = "> "

    def __init__(self, cli_def):
        """
        Initialize the command prompt.

        Args:
            cli_def:
                Dictionary definition of the cli.

            arg_types:
                Dictionary of <arg type> to CLIArg

        """
        self._cmd = _Cmd(self._parse_cli(cli_def), self.intro, self.prompt)
        self._cmd.cmdloop()

    def _parse_cli(self, cli_def):
        def process(parent_name, helpstr, contents):
            if isinstance(contents, dict):
                # This is a command list! Should be a dictionary of:
                #   "keyword:help" : (((cli elem)))
                elems = {}
                for key, value in contents.items():
                    if ":" not in key:
                        raise Error("Missing help string for {} in {}"
                                    .format(key, parent_name))
                    ch_name, ch_help = key.split(":")
                    if ch_name == "None":
                        ch_name = None
                    elems[ch_name] = process(ch_name, ch_help, value)
                return _CLIList(helpstr, elems)

            elif isinstance(contents, str):
                # This is an action
                if not hasattr(self, contents):
                    raise Error("Cannot find action function {}"
                                .format(contents))
                return _CLIAction(helpstr, getattr(self, contents))

            else:
                raise Error("Unknown cli definition contents for {}"
                            .format(parent_name))

        return process("<root>", "Main commands", cli_def)


class Context:
    """
    Context representing information parsed from the command line.

    """
    def __init__(self):
        self.kws = []
        self.args = {}
        self.end = False


# --------------------------------------------------------------------
# Private classes
# --------------------------------------------------------------------
class _Cmd(pycmd.Cmd):
    """
    Wraps cmd.Cmd to provide an extensible command prompt.

    """
    def __init__(self, cli_list, intro, prompt):
        super().__init__()
        self.intro = intro
        self.prompt = prompt
        self.cli_list = cli_list

        # Add special help command - this should never be called directly, as
        # we should hook and do the action ourselves.
        self.cli_list.add_keyword("help", _CLIAction("Display command help",
                                                     None))

    def completenames(self, text, line, begidx, endidx):
        return self.completedefault(text, line, begidx, endidx)

    def completedefault(self, text, line, begidx, endidx):
        ctx = None
        try:
            # If the command is help, then strip off the help then offer the
            # full cli tree as options.
            if line.startswith("help "):
                return self.cli_list.complete(ctx, line[5:])
            else:
                return self.cli_list.complete(ctx, line)
        except Exception as exc:
            print("Completion error!!")
            traceback.print_exc()

    def onecmd(self, line):
        if not line or not line.strip():
            return
        elif line.startswith("help"):
            self.do_help(line[4:].lstrip())
        else:
            ctx = Context()
            try:
                self.cli_list.execute(ctx, line)
            except CommandError as exc:
                print("Error: {!s}".format(exc))

            return ctx.end

    def do_help(self, arg):
        if not arg:
            self.onecmd("?")
        else:
            self.onecmd(arg + " ?")


class _CLIBase:
    """
    Base class for CLI elements.

    """
    def __init__(self, helpstr):
        self.helpstr = helpstr

    def execute(self, ctx, line):
        pass

    def complete(self, ctx, line):
        pass


class _CLIList(_CLIBase):
    def __init__(self, helpstr, elems):
        super().__init__(helpstr)

        self._elems = elems

    def add_keyword(self, kw, elem):
        self._elems[kw] = elem

    @staticmethod
    def splitline(line):
        if " " in line:
            cmd, remainder = line.split(" ", 1)
            remainder = remainder.lstrip()
        else:
            cmd, remainder = line, None

        return cmd, remainder

    def get_matches(self, text):
        if text is None and None in self._elems:
            return [None]
        else:
            return [c for c in self._elems
                      if c is not None and c.startswith(text)]

    def execute(self, ctx, line):
        if line is None:
            cmd, remainder = None, None
        else:
            # Split the line
            cmd, remainder = self.splitline(line)

        # Make sure we treat empty string as None command
        if not cmd:
            cmd = None

        def do_exec(name):
            ctx.kws.append(name)
            self._elems[name].execute(ctx, remainder)

        # If the command is ?, then do help
        if cmd == "?":
            self.display_help()
        # If we have the command, then great - execute it!
        elif cmd in self._elems:
            do_exec(cmd)
        elif cmd is None:
            print("!! Missing keyword")
        else:
            # Do we have a unique partial match?
            matches = self.get_matches(cmd)
            if not matches:
                print("!! Unknown keyword: {}".format(cmd))
            elif len(matches) > 1:
                print("!! Ambiguous keyword: {}".format(cmd))
            else:
                do_exec(matches[0])

    def complete(self, ctx, line):
        cmd, remainder = self.splitline(line)
        results = None

        # If there is a remainder then pass on to sub command
        if remainder is not None:
            matches = self.get_matches(cmd)
            if len(matches) == 1:
                 results = self._elems[matches[0]].complete(ctx, remainder)
        else:
            # Consume here - provide command completions
            results = [c + " " for c in self._elems
                       if c is not None and c.startswith(cmd)]

            # Add space for special None entry
            if not cmd and None in self._elems:
                results.append("")

        return results

    def display_help(self):
        maxlen = max(len(c) for c in self._elems if c is not None)
        print(self.helpstr)
        print("\nOptions:")
        for cmd, elem in self._elems.items():
            print("  {:{}} - {}".format(cmd, maxlen, elem.helpstr))


class _CLIAction(_CLIBase):
    def __init__(self, helpstr, function):
        super().__init__(helpstr)

        self._function = function

    def execute(self, ctx, line):
        if line and line.strip() == "?":
            print(self.helpstr)
        elif line:
            print("!! Unexpected input: {}".format(line))
        else:
            self._function(ctx)





