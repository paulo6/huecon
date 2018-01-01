#
# cli.py - CLI util classes
#
import cmd as pycmd
import traceback

try:
    import readline
    readline.set_completer_delims(" ")
except ImportError:
    pass


class Error(Exception):
    """Base exception for this module."""
    pass


class CommandError(Error):
    """
    Special exception raised when a command execution fails.

    """
    pass


class ArgumentError(Error):
    """
    Special exception raised when there is a bad argument value.

    """
    def __init__(self, msg, arg_val=None):
        super().__init__(msg)
        self.arg_val = arg_val


class Interface:
    """
    Implements a generic CLI command interface

    """
    intro = ""
    prompt = "> "

    def __init__(self, cli_def, arg_defs):
        """
        Initialize the command prompt.

        Args:
            cli_def:
                Dictionary definition of the cli.

            arg_defs:
                Dictionary of "<arg-type>" to ArgumentDef instances, for
                variable arguments referred to by cli_def

        """
        self._cmd = _Cmd(self._parse_cli(cli_def, arg_defs),
                         self.intro, self.prompt)
        self._cmd.cmdloop()

    def _parse_cli(self, cli_def, arg_defs):
        def process(parent_name, helpstr, contents):
            if (isinstance(contents, dict) and
                len(contents) == 1 and
                list(contents.keys())[0].startswith("<")):

                key, value = list(contents.items())[0]
                if ":" not in key:
                    raise Error("Missing help string for {} in {}"
                                .format(key, parent_name))
                arg_type, ch_help = key.split(":")

                # Get arg def
                if arg_type not in arg_defs:
                    raise Error("No arg def for {}".format(arg_type))

                return _CLIArgument(helpstr, process(arg_type, ch_help, value),
                                    arg_defs[arg_type])

            elif isinstance(contents, dict):
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
    def __init__(self, base):
        self.kws = []
        self.args = {}
        self.end = False
        self.base = base


class ArgumentDef:
    """
    CLI argument definition.

    """
    def __init__(self, name):
        self.name = name

    def splitline(self, ctx, line):
        """
        Called to split a line into argument part and remainder.

        Args:
            ctx: The command Context for CLI elements processes thus far
            line: The line to split

        Returns: (line, remainder) tuple

        """
        if line and " " in line:
            return line.split(" ", 1)
        else:
            return (line, None)

    def process(self, ctx, arg):
        """
        Called to process an argument.

        Args:
            ctx: The command Context for CLI elements processes thus far
            arg: The argument value

        Returns: Processed argument value (can be the same as input)

        Raises: ArgumentError when there is an issue with the argument.

        """
        return arg

    def complete(self, ctx, arg):
        """
        Return completions for a partially started argument value.

        Args:
            ctx: The command Context for CLI elements processes thus far
            arg: The partial argument value

        Returns: List of possible completions

        """
        return []

    def help_options(self, ctx):
        """
        Returns list of possible options for help.

        Can either be a list of values or a list of (value, help) tuples.

        """
        return self.complete(ctx, "")


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
        ctx = Context(self)
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
            ctx = Context(self)
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
                ctx.kws.append(cmd)
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


class _CLIArgument(_CLIBase):
    def __init__(self, helpstr, elem, arg_def):
        super().__init__(helpstr)
        self._elem = elem
        self._def = arg_def

    def execute(self, ctx, line):
        if line and line.strip() == "?":
            return self.display_help(ctx)

        arg, remainder = self._def.splitline(ctx, line)
        try:
            ctx.args[self._def.name] = self._def.process(ctx, arg)
        except ArgumentError as exc:
            val = exc.arg_val if exc.arg_val is not None else arg
            raise CommandError("Invalid {} argument '{}': {}"
                               .format(self._def.name, val, str(exc)))
        self._elem.execute(ctx, remainder)

    def complete(self, ctx, line):
        arg, remainder = self._def.splitline(ctx, line)
        # If there is a remainder, then pass it on
        if remainder is not None:
            # Process arg in case it is needed by later args
            try:
                ctx.args[self._def.name] = self._def.process(ctx, arg)
            except ArgumentError:
                pass
            return self._elem.complete(ctx, remainder)
        else:
            def fixup(txt):
                if " " in line:
                    return txt[line.rindex(" ") + 1:] + " "
                else:
                    return txt + " "

            return [fixup(x) for x in self._def.complete(ctx, line)]

    def display_help(self, ctx):
        print(self.helpstr)

        options = self._def.help_options(ctx)
        if options:
            print("\nOptions:")
            if isinstance(options[0], tuple):
                maxlen = max(len(v) for v, _ in options)
                for value, help in options:
                    print("  {:{}} - {}".format(value, maxlen, help))
            else:
                ctx.base.columnize(options)






