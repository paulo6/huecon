import atexit

class ReadlineWrapper(object):
    """
        Wraps readline module.

        Has the following functionality
          - Abstract away availability of readline, and set it up
            appropriately if it is available
          - Allow loading of a history file, and autosave on exit.

        """

    def __init__(self, delims):
        self._readline = self._setup(delims)
        self._history_file = None

    # ------------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------------
    def set_history_file(self, filename):
        if self._readline is None:
            return

        # Save current history and then clear, ready for new history
        if self._history_file:
            self._readline.write_history_file(self._history_file)
        self._readline.clear_history()

        # Load new one - it might not exist!
        try:
            self._readline.read_history_file(filename)
        except IOError:
            pass
        self._history_file = filename


    # ------------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------------
    def _setup(self, delims):
        try:
            import readline
        except ImportError:
            return None

        # Setup tab bind (which is done differently for libedit)
        if 'libedit' in readline.__doc__:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

        if delims:
            readline.set_completer_delims(delims)

        # Enable saving of history at exit
        atexit.register(self._save_at_exit)

        return readline

    def _save_at_exit(self):
        """
        Called when process exits, used to save history file

        """
        if self._history_file:
            self._readline.write_history_file(self._history_file)