from .BaseModel import BaseModel
import numpy as np
from utils import binarize, matmul, to_dense, to_sparse
from scipy.sparse import csr_matrix


class BaseContinuousModel(BaseModel):
    '''Binary matrix factorization.
    
    Reference
    ---------
    Binary Matrix Factorization with Applications
    Algorithms for Non-negative Matrix Factorization
    '''
    def __init__(self):
        raise NotImplementedError("This is a template class.")
    

    def init_model(self):
        if self.init_method != 'custom':
            super().init_model()
        else:
            self._init_logs()

        if hasattr(self, 'W'):
            self.init_W()


    def init_W(self):
        if isinstance(self.W, str):
            if self.W == 'mask':
                self.W = self.X_train.copy()
                self.W.data = np.ones(self.X_train.data.shape)
            elif self.W == 'full':
                self.W = np.ones((self.m, self.n))

        self.W = to_sparse(self.W)
        

    def init_UV(self):
        if self.init_method == "normal":
            avg = np.sqrt(self.X_train.mean() / self.k)
            V = avg * self.rng.standard_normal(size=(self.n, self.k))
            U = avg * self.rng.standard_normal(size=(self.m, self.k))
            self.U, self.V = np.abs(U), np.abs(V)
        elif self.init_method == "uniform":
            avg = np.sqrt(self.X_train.mean() / self.k)
            V = self.rng.uniform(low=0, high=avg * 2, size=(self.n, self.k))
            U = self.rng.uniform(low=0, high=avg * 2, size=(self.m, self.k))
        elif self.init_method == "custom":
            pass

        self.U, self.V = to_sparse(self.U), to_sparse(self.V)


    def normalize_UV(self):
        '''Normalize factors.
        '''
        diag_U = to_dense(np.sqrt(np.max(self.U, axis=0))).flatten()
        diag_V = to_dense(np.sqrt(np.max(self.V, axis=0))).flatten()
        for i in range(self.k):
            self.U[:, i] = self.U[:, i] * diag_V[i] / diag_U[i]
            self.V[:, i] = self.V[:, i] * diag_U[i] / diag_V[i]


    def show_matrix(self, settings=None, u=None, v=None, boolean=True, **kwargs):
        '''Wrapper of `BaseModel.show_matrix()` with `u` and `v`.
        '''
        if settings is None:
            U = binarize(self.U, u) if boolean and u is not None else self.U
            V = binarize(self.V, v) if boolean and v is not None else self.V
            X = matmul(U, V.T, boolean=boolean)
            settings = [(X, [0, 0], "X"), (U, [0, 1], "U"), (V.T, [1, 0], "V")]
        super().show_matrix(settings, **kwargs)