import inspect
import types

# Backport the getargspec function from Python 3.9 to Python 3.10+
if inspect.isbuiltin(inspect.getfullargspec):
    def getargspec(func):
        return inspect.getfullargspec(func)[:4]
else:
    getargspec = inspect.getargspec
    