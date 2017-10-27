from enum import Enum


class LogLevel(Enum):
    TRACE = "T"
    INFO = "I"

    def prefix(self):
        return "[%s] " % self.name


_logs = []


def reset():
    global _logs
    _logs = []


def get_logs(is_reset: bool = False):
    if is_reset:
        reset()
    return _logs


def log(message: str, level: LogLevel = LogLevel.INFO):
    string = level.prefix() + message
    _logs.append(string)
    print(string)