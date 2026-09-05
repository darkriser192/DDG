""" DDG-Toolkit Types
Contains a list of allusefull DDG type aliases
"""
import numpy as np
import numpy.typing as npt
import scipy as sp

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]
SparseMatrix = sp.sparse.csr_matrix
