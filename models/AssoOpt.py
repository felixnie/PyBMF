from .Asso import Asso
import numpy as np
import time
from utils import matmul, cover
from scipy.sparse import csr_matrix, lil_matrix
from p_tqdm import p_map
from typing import Union
from multiprocessing import Pool, cpu_count
from .BaseModel import BaseModel


class AssoOpt(Asso):
    '''The Asso algorithm with exhaustive search over each row of U.

    This implementation may be slow but is able to deal with large `k` or huge dimension of `X_train`.
    
    Reference
    ---------
    The discrete basis problem. Zhang et al. 2007.
    '''
    def __init__(self, model, w=None):
        self.check_params(model=model, w=w)


    def check_params(self, **kwargs):
        super().check_params(**kwargs)
        if 'model' in kwargs:
            model = kwargs.get('model')
            assert isinstance(model, BaseModel), "[E] Import a BaseModel."
            self.k = model.k
            self.U = model.U
            self.V = model.V
            self.logs = model.logs
            print("[I] k from model :", self.k)
        if 'w' in kwargs:
            w = kwargs.get('w')
            if w is None and hasattr(model, 'w'):
                self.w = model.w
                print("[I] w from model :", self.w)
            else:
                self.w = w
                print("[I] w            :", self.w)
    

    def fit(self, X_train, X_val=None, **kwargs):
        self.check_params(**kwargs)
        self.load_dataset(X_train=X_train, X_val=X_val)

        self.exhaustive_search()

        display(self.logs['refinements'])
        self.show_matrix(colorbar=True, discrete=True, clim=[0, 1], title="assoopt results")


    def exhaustive_search(self):
        '''Using exhaustive search to refine U.
        '''
        tic = time.perf_counter()

        # with Pool() as pool:
        #     pool.map(self.set_optimal_row, range(self.m))

        results = p_map(self.set_optimal_row, range(self.m))

        toc = time.perf_counter()
        print("[I] Exhaustive search finished in {}s.".format(toc-tic))

        for i in range(self.m):
            self.U[i] = self.int2bin(results[i], self.k)

        self.predict()
        score = cover(gt=self.X_train, pd=self.X_pd, w=self.w)
        self.evaluate(names=['score'], values=[score], df_name='refinements')


    def set_optimal_row(self, i):
        '''Update the i-th row in U.
        '''
        trials = 2 ** self.k
        scores = np.zeros(trials)
        X_gt = self.X_train[i, :]
        for j in range(trials):
            U = self.int2bin(j, self.k)
            X_pd = matmul(U, self.V.T, sparse=True, boolean=True)
            scores[j] = cover(gt=X_gt, pd=X_pd, w=self.w)
        idx = np.argmax(scores)
        return idx


    @staticmethod
    def int2bin(i, bits):
        '''Turn `i` into (1, `bits`) binary sparse matrix.
        '''
        return csr_matrix(list(bin(i)[2:].zfill(bits)), dtype=int)