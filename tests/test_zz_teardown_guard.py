"""Fail the run on exceptions nobody could catch.

An exception raised in a ``__del__`` or a finaliser, such as a Tk variable
collected in a worker thread ("main thread is not in main loop"), is only
printed as "Exception ignored in ..." and the run still passes; so is a Tcl
interpreter leaked because it was released outside its thread. Discovery
imports every test module before running any and runs them in name order,
so the hooks installed here see the whole run and this module checks last.
Each case is still printed by the previous hook: recorded, never silenced.
"""
import sys
import threading
import unittest
import warnings

TCL_LEAK = "Tcl interpreter is leaked"


class Recorder:
    def __init__(self, previous_hook, previous_showwarning):
        self.seen: list[str] = []
        self._previous_hook = previous_hook
        self._previous_showwarning = previous_showwarning

    def unraisable(self, args) -> None:
        self.seen.append(f"{args.err_msg or 'Exception ignored in'}: {args.object!r}: "
                         f"{args.exc_type.__name__}: {args.exc_value} "
                         f"(thread {threading.current_thread().name})")
        self._previous_hook(args)

    def showwarning(self, message, category, filename, lineno, file=None, line=None):
        if issubclass(category, RuntimeWarning) and TCL_LEAK in str(message):
            self.seen.append(f"{category.__name__}: {message} "
                             f"(thread {threading.current_thread().name})")
        self._previous_showwarning(message, category, filename, lineno, file, line)


RUN = Recorder(sys.unraisablehook, warnings.showwarning)
sys.unraisablehook = RUN.unraisable
warnings.showwarning = RUN.showwarning


class RecorderTests(unittest.TestCase):
    def test_records_and_still_reports_an_ignored_exception(self):
        printed = []
        rec = Recorder(printed.append, None)
        try:
            raise RuntimeError("main thread is not in main loop")
        except RuntimeError as exc:
            args = type("Args", (), {"err_msg": None, "object": "Variable.__del__",
                                     "exc_type": RuntimeError, "exc_value": exc})()
        rec.unraisable(args)
        self.assertEqual(printed, [args])
        self.assertIn("main thread is not in main loop", rec.seen[0])

    def test_records_only_the_tcl_leak_warning(self):
        shown = []
        rec = Recorder(None, lambda *a: shown.append(a))
        rec.showwarning(RuntimeWarning("the Tcl interpreter is leaked because it was "
                                       "deallocated in a thread other than the one it was "
                                       "created in"), RuntimeWarning, "f.py", 1)
        rec.showwarning(DeprecationWarning("old"), DeprecationWarning, "f.py", 2)
        self.assertEqual(len(shown), 2)
        self.assertEqual(len(rec.seen), 1)


class TeardownGuardTests(unittest.TestCase):
    def test_nothing_was_ignored_during_the_run(self):
        self.assertEqual(RUN.seen, [], "\n" + "\n".join(RUN.seen))


if __name__ == "__main__":
    unittest.main()
