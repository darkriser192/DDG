""" DDG-Toolkit Types
Contains a list of allusefull DDG type aliases
"""
import numpy as np
import numpy.typing as npt
import scipy as sp

# Type Alliases

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]
SparseMatrix = sp.sparse.csr_matrix

# Constants

ERR_TOL = 1e-8 # Generic and Default tolerance for when error bounds are not known
