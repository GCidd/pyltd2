import os
from inspect import getframeinfo, stack


class Log:
    """
    Static class used to print objects with different priorities.
    Print structure is:
        [<priority>] <object> (<file:line>)
    """
    LAST_LOG_ID = None
    AUTO_FLUSH = True
    MESSAGE_END = ""
    NEWLINED = False

    @staticmethod
    def important(*args):
        """
        Print objects in highest priority.
        Also prints a divider before and after the message.
        """
        starting = '' if Log.NEWLINED else '\n'
        print (f"{starting}" + "*"*100)
        ending = "\n"
        message = " ".join(map(str, args))
        caller = getframeinfo(stack()[1][0])
        file_caller = os.path.basename(caller.filename)
        Log.LAST_LOG_ID = None
        print (f"\r[IMPORTANT] {message} ({file_caller}:{caller.lineno})", end=ending, flush=Log.AUTO_FLUSH)
        print ("*" * 100 + '\n')
        Log.NEWLINED = True

    @staticmethod
    def warning(*args):
        """
        Print object with a high priority (higher than info).
        """
        starting = "" if Log.NEWLINED else "\n"
        caller = getframeinfo(stack()[1][0])
        message = " ".join(map(str, args))
        file_caller = os.path.basename(caller.filename)
        Log.LAST_LOG_ID = None
        print (f"{starting}[WARNING] {message} ({file_caller}:{caller.lineno})", end="\n", flush=Log.AUTO_FLUSH)
        Log.NEWLINED = True

    @staticmethod
    def info(*args, log_id: int = None, append_last: bool = False) -> None:
        """
        Print objects in low priority.

        Args:
            log_id (int, optional): 
                ID of the message. Messages with the same id will overwrite each other.
                Defaults to None.
            append_last (bool, optional): 
                Whether to append to the last printing message or not, only if the previous id is the same.
                Defaults to False.
        """
        type_label = "[INFO]"
        if append_last and (log_id is not None and log_id == Log.LAST_LOG_ID):
            overrite_previous = " "
            type_label = ""
        elif log_id is not None and log_id == Log.LAST_LOG_ID:
            print("\r" + " " * 250, end=' ', flush=True)
            overrite_previous = "\r"
        else:
            overrite_previous = "\n"

        message = " ".join(map(str, args))
        ending = Log.MESSAGE_END
        caller = getframeinfo(stack()[1][0])
        file_caller = os.path.basename(caller.filename)

        print (f"{overrite_previous}{type_label} {message} ({file_caller}:{caller.lineno})", end=ending, flush=Log.AUTO_FLUSH)
        Log.NEWLINED = ending == "\n"
        Log.LAST_LOG_ID = log_id
