# NumPy-Style Docstring Template

Reference for documenting functions/classes in this project. Follows the
[NumPy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html),
which `pydocstyle` (convention `numpy`) and most IDEs understand.

> Note: this is **pydocstyle** (a docstring-style linter), not **pydantic**
> (runtime data validation). To check these docstrings:
> `pydocstyle --convention=numpy scratchpad.py AuxFunctions.py`

---

## Function template

```python
def function_name(param1, param2=None):
    """One-line summary in the imperative mood, ending with a period.

    Optional extended description. Explain *what* it does and any
    important behavior (vectorization, edge cases, assumptions). Keep it
    to a few sentences; details go in Notes.

    Parameters
    ----------
    param1 : numpy.ndarray, shape (N, 3)
        What it is and how it's indexed. State the shape and dtype when it
        matters. Use V (vertices), F (faces), N (generic count) consistently.
    param2 : bool, optional
        Describe the default behavior. Mark optional params with ``optional``.

    Returns
    -------
    name : type, shape (...)
        Named returns read well when there are several. Describe each.

    Raises
    ------
    SystemExit
        When and why the function raises (omit section if it never does).

    Side Effects
    ------------
    Non-standard but useful here: note stdout prints, global/Polyscope state
    mutation, file I/O, etc. (Standard NumPy uses Notes for this.)

    Notes
    -----
    Math, references to module globals (``ERR``), gotchas, related functions
    via :func:`other_function`.

    Examples
    --------
    >>> function_name(np.zeros((4, 3)))
    (array([0., 0., 0., 0.]), array([[0., 0., 0.], ...]))
    """
```

## Class template

```python
class ClassName():
    """One-line summary of what the class represents.

    Extended description of purpose and behavior.

    Parameters
    ----------
    arg : type
        Constructor argument (document __init__ args here, on the class).

    Attributes
    ----------
    attr : type, shape (...)
        Public attributes set on the instance.

    Notes
    -----
    Anything else worth knowing (eager vs lazy computation, invariants).
    """
```

---

## Conventions used in this project

- **Summary line**: imperative ("Compute...", "Open...", "Register..."), one
  line, ends with a period.
- **Shapes**: written as `shape (F, 3)`. Symbols: `V` = vertices,
  `F` = faces, `N` = generic batch size.
- **Optional sections**: include only the sections that apply. Order is
  Summary → Extended → Parameters → Returns → Raises → Side Effects → Notes →
  Examples.
- **Cross-references**: `:func:\`name\`` for functions, `:class:\`Name\`` for
  classes.
- **`Side Effects`** is a non-standard section we use deliberately because a
  lot of these functions print or mutate global Polyscope/LOGGER state.

## Common sections cheat-sheet

| Section        | Use when…                                            |
|----------------|------------------------------------------------------|
| Parameters     | the function takes arguments                          |
| Returns        | it returns something (name them if >1)                |
| Yields         | it's a generator                                      |
| Raises         | it can raise an exception the caller should know of   |
| Side Effects   | it prints, writes files, or mutates global state      |
| Notes          | math, references to globals, caveats                  |
| Examples       | a short doctest-style usage helps                     |
