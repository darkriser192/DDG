### Imports
import os
import sys
import time
from importlib import metadata
from pprint import pprint
import functools
import tracemalloc
import tkinter as tk
from tkinter import filedialog
from collections.abc import Callable
from typing import Any, TypeVar, cast
import psutil

### Type Aliases
# Bound to the decorated function itself, so `Callable[[F], F]` tells a type
# checker the wrapper keeps the original signature. Without it every decorated
# function degrades to (*args, **kwargs) and Pylance can no longer bind `self`
# or check a call site.
F = TypeVar("F", bound=Callable[..., Any])

### Global Variables
LOGGER: dict[str, float] = {}
_TK_ROOT: tk.Tk | None = None # module-level, one hidden root for the whole process

### Probing Functions
def timed(enabled: bool = True) -> Callable[[F], F]:
    """Time a function's execution and record the result in ``LOGGER``.

    Decorator factory. When ``enabled`` is True, wraps the target function so
    that its wall-clock execution time is measured with
    ``time.perf_counter``, printed to stdout, and stored in the module-level
    ``LOGGER`` dict keyed by function name. The timing runs in a ``finally``
    block, so it is recorded even if the wrapped function raises.

    TODO: [PRIORITY: Low] add a label argument so we can get correct printing inside classes

    Parameters
    ----------
    enabled : bool, optional
        If True (default), apply timing. If False, the wrapped function is
        called directly with no timing overhead.

    Returns
    -------
    callable
        A decorator that, applied to a function, returns a wrapper with the
        same signature and metadata (via ``functools.wraps``).

    Side Effects
    ------------
    Prints a ``[TIMER]`` line to stdout and writes ``LOGGER[func.__name__]``
    with the elapsed time in seconds.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)  # Preserve function metadata
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if enabled:
                start_time = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = time.perf_counter() - start_time
                    print(f"[TIMER] {func.__name__} took {elapsed:.6f} seconds")
                    if LOGGER is not None:
                        LOGGER[func.__name__] = elapsed
            else:
                # Just run the function without timing
                return func(*args, **kwargs)
        # cast, not a lie: the wrapper accepts (*args, **kwargs) and forwards
        # them unchanged, so it is call-compatible with `func` at runtime. The
        # cast is what tells the checker so.
        return cast(F, wrapper)
    return decorator

def debugged(enabled: bool = True) -> Callable[[F], F]:
    """Print a function's name and return value for quick debugging.

    Decorator factory. When ``enabled`` is True, wraps the target function so
    that its name is printed before the call and its return value is
    pretty-printed afterwards via ``pprint``.

    Parameters
    ----------
    enabled : bool, optional
        If True (default), apply debug printing. If False, the wrapped
        function is called directly with no extra output.

    Returns
    -------
    callable
        A decorator that, applied to a function, returns a wrapper with the
        same signature and metadata (via ``functools.wraps``).

    Side Effects
    ------------
    Prints the function name and a ``[DEBUGGER Return]`` block to stdout.

    Notes
    -----
    Unlike :func:`timed`, the return value is only printed on the ``enabled``
    branch; both branches return the wrapped function's result unchanged.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)  # Preserve function metadata
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if enabled:
                pprint(func.__name__)
                r = func(*args, **kwargs)
                print("[DEBUGGER Return]: \n")
                pprint(r)
                return r
            else:
                # Just run the function
                return func(*args, **kwargs)
        return cast(F, wrapper)
    return decorator

def memory(enabled: bool = True, peak: bool = False) -> Callable[[F], F]:
    """Report a function's resident-memory change, and optionally Python peak.

    Decorator factory. When ``enabled`` is True, wraps the target function so
    that the process resident set size (RSS) is sampled before and after the
    call and the delta printed. With ``peak`` True, ``tracemalloc`` is started
    around the call to also report the Python-object peak allocation. Sampling
    runs in a ``finally`` block, so it is reported even if the wrapped function
    raises.

    Parameters
    ----------
    enabled : bool, optional
        If True (default), apply memory probing. If False, the wrapped
        function is called directly with no overhead.
    peak : bool, optional
        If True, also start ``tracemalloc`` and report the Python-object peak
        allocation for the call. Defaults to False.

    Returns
    -------
    callable
        A decorator that, applied to a function, returns a wrapper with the
        same signature and metadata (via ``functools.wraps``).

    Side Effects
    ------------
    Prints a ``[MEMORY]`` line to stdout with the before/after RSS (in GB) and,
    when ``peak`` is set, the ``tracemalloc`` Python-object peak.

    Notes
    -----
    RSS is read via ``psutil.Process(...).memory_info().rss``; the process
    handle is captured once when the decorator is applied. Unlike
    :func:`timed`, the metric is printed only and not stored in ``LOGGER``.
    """
    _proc = psutil.Process(os.getpid())
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not enabled:
                return func(*args, **kwargs)
            if peak:
                tracemalloc.start()
            before = _proc.memory_info().rss / 1e9
            try:
                return func(*args, **kwargs)
            finally:
                after = _proc.memory_info().rss / 1e9
                msg = f"[MEMORY] {func.__name__}: {before:.2f} → {after:.2f} GB (Δ{after-before:+.2f})"
                if peak:
                    _, pk = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    msg += f"  py-peak {pk/1e9:.2f} GB"
                print(msg)
        return cast(F, wrapper)
    return decorator

def clear_terminal() -> None:
    """Clear the terminal screen, cross-platform.

    Issues the platform-appropriate clear command: ``cls`` on Windows
    (``os.name == 'nt'``) and ``clear`` elsewhere.

    Returns
    -------
    None

    Side Effects
    ------------
    Spawns a shell command via ``os.system`` that clears the console.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def python_version() -> dict[str, Any]:
    """
    Recovers python implementation and version information
    """
    python: dict[str, Any] = {"platform": sys.platform,
              "implementation": sys.implementation,
              "version information": sys.version_info,
              "version": sys.version}
    return python

### Read file string
def _get_tk_root() -> tk.Tk:
    """Return the process-wide hidden Tk root, creating it once on first use."""
    global _TK_ROOT
    if _TK_ROOT is None:
        _TK_ROOT = tk.Tk()
        _TK_ROOT.withdraw()
    return _TK_ROOT

def read_file() -> str | None:
    """Open a file-picker dialog and return the chosen path.

    Spins up a hidden Tk root window, shows a native "open file" dialog via
    ``tkinter.filedialog.askopenfilename``, then tears the root down. If the
    user cancels (no selection), the program is terminated.

    Returns
    -------
    str
        Absolute path to the file the user selected.

    Raises
    ------
    SystemExit
        If the dialog is cancelled or no file is selected.

    Notes
    -----
    ``askopenfilename`` returns an empty string on cancel; the falsy check
    converts that into a ``SystemExit`` so callers always receive a valid,
    non-empty path (or the program exits).
    """
    root = _get_tk_root()
    root.update()
    filepath = filedialog.askopenfilename(parent = root)
    if not filepath:
        print("No file selected. Exiting.")
    return filepath or None
