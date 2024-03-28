from .BinaryMF import BinaryMF
from utils import binarize, to_dense, power, multiply
import numpy as np
from scipy.sparse import spmatrix


class BinaryMFPenalty(BinaryMF):
    '''Binary matrix factorization, Penalty algorithm
    
    Reference
    ---------
    Binary Matrix Factorization with Applications
    Algorithms for Non-negative Matrix Factorization
    '''
    def __init__(self, k, W='mask', reg=2, reg_growth=3, tol=0.01, min_diff=0.0, max_iter=100, init_method='nmf_sklearn', seed=None):
        '''
        Parameters
        ----------
        reg : float
            The regularization weight 'lambda' in the paper.
        reg_growth : float
            The growing rate of regularization weight.
        tol : float
            The error tolerance 'epsilon' in the paper.
        '''
        self.check_params(k=k, W=W, reg=reg, reg_growth=reg_growth, tol=tol, min_diff=min_diff, max_iter=max_iter, init_method=init_method, seed=seed)
        

    def check_params(self, **kwargs):
        super().check_params(**kwargs)
        self.set_params(['reg_growth', 'init_method'], **kwargs)
        assert self.init_method in ['nmf_sklearn', 'nmf', 'normal', 'uniform']
        assert isinstance(self.W, spmatrix) or self.W in ['mask', 'full']


    def _fit(self):
        '''The alternative minimization algorithm.
        '''
        n_iter = 0
        should_continue = True
        error_old, rec_error, reg_error = self.error()
        self.logs['errors'] = [error_old]

        while should_continue:

            import warnings
            warnings.filterwarnings('ignore') 
            self.update_V()
            self.update_U()

            error_new, rec_error, reg_error = self.error()
            self.logs['errors'].append(error_new)
            diff = abs(error_old - error_new)

            # evaluate
            self.predict_X(u=0.5, v=0.5, boolean=True)
            self.evaluate(df_name='updates', head_info={'iter': n_iter, 'reg': self.reg, 'error': error_new, 'rec_error': rec_error, 'reg_error': reg_error})

            # display
            self.print_msg("iter: {}, reg: {:.2e}, err: {:.2e}, rec_err: {:.2e}, reg_err: {:.2e}".format(n_iter, self.reg, error_new, rec_error, reg_error))
            if n_iter % 10 == 0:
                self.show_matrix(u=0.5, v=0.5, title=f"iter {n_iter}")

            # early stop detection
            should_continue = self.early_stop(error=reg_error, diff=diff, n_iter=n_iter)

            # update reg
            self.reg *= self.reg_growth
            n_iter += 1

        self.show_matrix(u=0.5, v=0.5, title="result")


    def update_U(self):
        '''Multiplicative update of U
        '''
        num = multiply(self.W, self.X_train) @ self.V + 3 * self.reg * power(self.U, 2)
        denom = multiply(self.W, self.U @ self.V.T) @ self.V + 2 * self.reg * power(self.U, 3) + self.reg * self.U
        denom[denom == 0] = np.finfo(np.float64).eps
        self.U = multiply(self.U, num / denom)


    def update_V(self):
        '''Multiplicative update of V
        '''
        num = multiply(self.W, self.X_train).T @ self.U + 3 * self.reg * power(self.V, 2)
        denom = multiply(self.W, self.U @ self.V.T).T @ self.U + 2 * self.reg * power(self.V, 3) + self.reg * self.V
        denom[denom == 0] = np.finfo(np.float64).eps
        self.V = multiply(self.V, num / denom)


    def error(self):
        '''Error for penalty function algorithm.

        In the paper, only reg_error is considered.
        '''
        diff = self.X_train - self.U @ self.V.T
        rec_error = np.sum(power(multiply(self.W, diff), 2))
        reg_error = np.sum(power(power(self.U, 2) - self.U, 2)) + np.sum(power(power(self.V, 2) - self.V, 2))

        error = 0 * rec_error + 0.5 * self.reg * reg_error
        return error, rec_error, reg_error
