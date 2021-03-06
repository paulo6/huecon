#
# cli.py - CLI util classes
#
import cmd as pycmd
import io
import traceback
import subprocess
import shutil

from contextlib import redirect_stdout
from threading import Thread

import utils

READLINE_WRAP = utils.ReadlineWrapper(" ")


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

    def __init__(self, cli_def, arg_defs, history_filename=None):
        """
        Initialize the command prompt.

        Args:
            cli_def:
                Dictionary definition of the cli.

            arg_defs:
                Dictionary of "<arg-type>" to ArgumentDef instances, for
                variable arguments referred to by cli_def

        """
        self._arg_defs = arg_defs
        self._cmd = _Cmd(self._parse_cli(cli_def, arg_defs),
                         self.intro, self.prompt)

        # Load history file
        if history_filename:
            READLINE_WRAP.set_history_file(history_filename)

        self._cmd.cmdloop()

    def _parse_cli(self, cli_def, arg_defs):
        """
        Private helper to parse cli definition dictionary.

        Args:
            cli_def: Dictionary containing cli definition
            arg_defs: Argument definition dictionary

        Returns:
            The top level _CLIList

        """
        return self._parse_cli_elem("<root>", "Main commands", cli_def)

    def _parse_cli_elem(self, parent_name, helpstr, contents, apply_pipe=False):
        # Look for variable argument
        if (isinstance(contents, dict) and len(contents) == 1 and
                list(contents.keys())[0].startswith("<")):
            key, value = list(contents.items())[0]
            if ":" not in key:
                raise Error("Missing help string for {} in {}"
                            .format(key, parent_name))
            arg_type, ch_help = key.split(":")

            # Get arg def
            if arg_type not in self._arg_defs:
                raise Error("No arg def for {}".format(arg_type))

            return _CLIArgument(helpstr,
                                self._parse_cli_elem(arg_type, ch_help, value,
                                                     apply_pipe),
                                self._arg_defs[arg_type])

        # Look for keyword command list
        elif isinstance(contents, dict):
            # This is a command list! Should be a dictionary of:
            #   "keyword:help" : (((cli elem)))
            elems = {}
            for key, value in contents.items():
                if ":" not in key:
                    raise Error("Missing help string for {} in {}"
                                .format(key, parent_name))
                ch_name, ch_help = key.split(":")
                ch_apply_pipe = apply_pipe
                if ch_name == "None":
                    ch_name = None
                elif ch_name.endswith("|"):
                    ch_apply_pipe = True
                    ch_name = ch_name[:-1]
                elems[ch_name] = self._parse_cli_elem(ch_name, ch_help, value,
                                                      ch_apply_pipe)

            # If we have None as an option, and we have apply pipe, then add
            # a pipe option here
            if None in elems:
                elems["|"] = _CLIArgument(elems[None].helpstr +
                                          " (pipe output to shell command)",
                                          _PipeAction(elems[None]),
                                          _PipeArgDef())
            return _CLIList(helpstr, elems)

        # Look for
        elif isinstance(contents, str):
            # This is an action
            if not hasattr(self, contents):
                raise Error("Cannot find action function {}"
                            .format(contents))
            action = _CLIAction(helpstr, getattr(self, contents))

            # If we do not need to apply a Pipe, then stop here.
            if not apply_pipe:
                return action

            # Need to build a pipe option before the action
            pipe_arg = _CLIArgument(helpstr +
                                    " (pipe output to shell command)",
                                    _PipeAction(action), _PipeArgDef())
            pipe_list = _CLIList(helpstr,
                                 {None: action, "|": pipe_arg})
            return pipe_list

        else:
            raise Error("Unknown cli definition contents for {}"
                        .format(parent_name))



class Context:
    """
    Context representing information parsed from the command line.

    Attributes:
        kws: The keywords in the line executed
        args: Dictionary of argument name to value
        end: Set this to True to end the command prompt loop after this
            execution
        cmd_inst: The underlying Cmd instance.

    """
    def __init__(self, cmd_inst):
        self.kws = []
        self.args = {}
        self.end = False
        self.cmd_inst = cmd_inst


class ArgumentDef:
    """
    CLI argument definition.

    """
    def __init__(self, name, ctx_name=None):
        """

        Args:
            name: The name of the argument, used in help strings.
            ctx_name: The name to use when saving the result in Context args
                      dictionary. If None then name will be used.
        """
        self.name = name
        self.ctx_name = name if ctx_name is None else ctx_name

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
            return line, None

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
        self.identchars += "|"

        # Add special help command - this should never be called directly, as
        # we should hook and do the action ourselves.
        self.cli_list.add_keyword("help", _CLIAction("Display command help",
                                                     None))

    def cmdloop(self, intro=None):
        """
        Main command loop function.

        We override the cmdloop to provide ctrl+c and exception handling

        """
        # Print intro and subintro only when entering the loop (not when it
        # is restarted due to ctrl+c)
        if intro is None:
            intro = self.intro
        if intro is not None:
            print(self.intro)

        loop = True
        while loop:
            try:
                # Reset intro to ensure it isn't printed again
                self.intro = None
                super().cmdloop()
                loop = False
            except KeyboardInterrupt:
                print("^C")
            finally:
                # Restore intro
                self.intro = intro

    def completenames(self, text, line, begidx, endidx):
        return self.completedefault(text, line, begidx, endidx)

    def completedefault(self, text, line, begidx, endidx):
        ctx = Context(self)
        try:
            return self.cli_list.complete(ctx, line)
        except Exception:
            print("Completion error!!")
            traceback.print_exc()

    def onecmd(self, line):
        # Parse and process the line, checking for ? and checking whether
        # the command matches any of our 'hidden' do_<cmd>s
        cmd, arg, _ = self.parseline(line)

        if not line or not line.strip():
            return
        elif cmd is not None and hasattr(self, "do_" + cmd):
            getattr(self, 'do_' + cmd)(arg)
        else:
            ctx = Context(self)
            try:
                self.cli_list.execute(ctx, line)
            except CommandError as exc:
                print("Error: {!s}".format(exc))

            return ctx.end

    def do_help(self, arg):
        ctx = Context(self)
        if not arg or not arg.strip():
            self.cli_list.execute(ctx, "?")
        elif arg == "help":
            self.cli_list.execute(ctx, "help ?")
        else:
            self.cli_list.execute(ctx, arg + " ?")

    def complete_help(self, _text, line, _begidx, _endidx):
        arg = line[5:]
        return self.completedefault(arg, arg, 0, len(arg))

    def do_EOF(self, arg):
        print("")


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

        if None in self._elems:
            maxlen = max(maxlen, len("<br>"))
            print("  {:{}} - {}".format("<br>", maxlen,
                                        self._elems[None].helpstr))

        elems = (i for i in self._elems.items() if i[0] is not None)
        for cmd, elem in sorted(elems, key=lambda i: i[0]):
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
        if not line:
            print("!! Missing <{}> argument".format(self._def.name))
            return

        if line.strip() == "?":
            return self.display_help(ctx)

        arg, remainder = self._def.splitline(ctx, line)
        try:
            ctx.args[self._def.ctx_name] = self._def.process(ctx, arg)
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
                ctx.args[self._def.ctx_name] = self._def.process(ctx, arg)
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
        print("<{}> - {}".format(self._def.name, self._elem.helpstr))

        options = self._def.help_options(ctx)
        if options:
            print("\nOptions:")
            if isinstance(options[0], tuple):
                maxlen = max(len(v) for v, _ in options)
                for value, helpstr in options:
                    print("  {:{}} - {}".format(value, maxlen, helpstr))
            else:
                ctx.cmd_inst.columnize(options)


class _PipeAction(_CLIAction):
    """
    Special Pipe action class for pipe command.

    """
    def __init__(self, cli_action):
        self._cli_action = cli_action
        super().__init__("Pipe output to this command", self._run_pipe)

    def _run_pipe(self, ctx):
        # Run command as normal capturing stdout. Need to redirect both
        # sys.stdout and the prompt's stdout.
        buf = io.StringIO()
        with redirect_stdout(buf):
            self._cli_action.execute(ctx, None)

        # Check the command exists. We need to do this in advance, else
        # sometimes we get broken pipe errors from proc.communicate() when an
        # invalid command is passed (Popen does not check for us because we
        # use 'shell=True').
        cmd = ctx.args['shell-cmd']
        if shutil.which(cmd.split()[0]) is None:
            raise CommandError("Shell command '{}' not found"
                               .format(cmd.split()[0]))

        # Run command with stdin ready to receive data. Use shell=True, so
        # that the user can do things such as: "show blah | cat > out.txt"
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)

        # Spawn separate thread to pipe data in and wait for process to exit.
        # This is to ensure that if the user presses ctrl+c, then it won't
        # prematurely kill the subprocess (which can leave the terminal in a
        # bad state if it was 'less' that was spawned). This also allows the
        # subprocess to handle ctrl+c as it sees fit.
        thread_exc = None

        def do_pipe():
            """
            Pipe handler.

            """
            nonlocal thread_exc
            try:
                proc.communicate(input=buf.getvalue().encode('ASCII'))
                _ = proc.wait()
            except BrokenPipeError as exc:
                thread_exc = exc

        thr = Thread(target=do_pipe)
        thr.start()

        done = False
        while not done:
            try:
                thr.join()
                done = True
            except KeyboardInterrupt:
                pass

        # Raise any thread exceptions now
        if thread_exc is not None:
            raise CommandError(str(thread_exc)) from thread_exc


class _PipeArgDef(ArgumentDef):
    """
    External shell command argument for the pipe command.

    """

    def __init__(self):
        super().__init__("shell-cmd")

    def splitline(self, ctx, line):
        return (line, None)
