from .ContinuousModel import ContinuousModel
from utils import binarize, to_dense, power, multiply, ignore_warnings
import numpy as np
from scipy.sparse import spmatrix


class BinaryMFPenalty(ContinuousModel):
    '''Binary matrix factorization, penalty function algorithm.

    Solving the problem with multiplicative update:

    min 1/2 * ||X - U @ V.T||_F^2 + 1/2 * reg * ||U^2 - U||_F^2 + 1/2 * reg * ||V^2 - V||_F^2
    
    Reference
    ---------
    Binary Matrix Factorization with Applications
    Algorithms for Non-negative Matrix Factorization
    '''
    def __init__(self, k, U=None, V=None, W='full', reg=2.0, beta_loss="frobenius", solver="mu", reg_growth=3, tol=0.01, min_diff=0.0, max_iter=100, init_method='custom', seed=None):
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
        self.check_params(k=k, U=U, V=V, W=W, reg=reg, beta_loss=beta_loss, solver=solver, reg_growth=reg_growth, tol=tol, min_diff=min_diff, max_iter=max_iter, init_method=init_method, seed=seed)
        

    def check_params(self, **kwargs):
        super().check_params(**kwargs)
        
        self.set_params(['beta_loss', 'solver', 'reg_growth'], **kwargs)
        assert self.beta_loss in ['frobenius']
        assert self.solver in ['mu']
        assert self.init_method in ['normal', 'uniform', 'custom']


    def fit(self, X_train, X_val=None, X_test=None, **kwargs):
        super().fit(X_train, X_val, X_test, **kwargs)

        self._fit()

        self.predict_X(boolean=False)
        self.finish()

    
    def init_model(self):
        '''Initialize factors and logging variables.
        '''
        super().init_model()

        self.init_UV()
        # self.normalize_UV(method="balance")
        self.normalize_UV(method="normalize")

        self._to_float()
        self._to_dense()


    def _fit(self):
        '''The alternative minimization algorithm.
        '''
        n_iter = 0
        is_improving = True

        # compute error
        error_old, rec_error_old, reg_error_old = self.error()

        # evaluate
        self.predict_X(boolean=False)
        self.evaluate(df_name='updates', head_info={'iter': n_iter, 'error': error_old, 'rec_error': rec_error_old, 'reg': float(self.reg), 'reg_error': reg_error_old}, metrics=['RMSE', 'MAE'])

        while is_improving:
            # update n_iter, U, V
            n_iter += 1
            self.update()

            # compute error, diff
            error_new, rec_error_new, reg_error_new = self.error()
            diff = abs(reg_error_old - reg_error_new)
            error_old, rec_error_old, reg_error_old = error_new, rec_error_new, reg_error_new

            # evaluate
            self.predict_X(boolean=False)
            self.evaluate(df_name='updates', head_info={'iter': n_iter, 'error': error_new, 'rec_error': rec_error_new, 'reg': float(self.reg), 'reg_error': reg_error_new}, metrics=['RMSE', 'MAE'])

            # display
            self.print_msg("iter: {}, error: {:.2e}, rec_error: {:.2e}, reg: {:.2e}, reg_error: {:.2e}".format(n_iter, error_new, rec_error_new, self.reg, reg_error_new))
            if self.verbose and self.display and n_iter % 10 == 0:
                self.show_matrix(boolean=False, colorbar=True, title=f"iter {n_iter}")

            # early stop detection
            is_improving = self.early_stop(error=reg_error_old, diff=diff, n_iter=n_iter)

            # update reg
            self.reg *= self.reg_growth


    @ignore_warnings
    def update(self):
        '''Multiplicative update.
        '''
        if self.beta_loss == 'frobenius':
            # update V
            num = multiply(self.W, self.X_train).T @ self.U
            num += 3 * self.reg * power(self.V, 2)

            denom = multiply(self.W, self.U @ self.V.T).T @ self.U
            denom += 2 * self.reg * power(self.V, 3) + self.reg * self.V
            denom[denom == 0] = np.finfo(np.float64).eps

            self.V = multiply(self.V, num / denom)

            # update U
            num = multiply(self.W, self.X_train) @ self.V
            num += 3 * self.reg * power(self.U, 2)
            denom = multiply(self.W, self.U @ self.V.T) @ self.V
            denom += 2 * self.reg * power(self.U, 3) + self.reg * self.U
            denom[denom == 0] = np.finfo(np.float64).eps

            self.U = multiply(self.U, num / denom)

            
    # @ignore_warnings
    # def update_U(self):
    #     '''Multiplicative update of U.
    #     '''
    #     num = multiply(self.W, self.X_train) @ self.V + 3 * self.reg * power(self.U, 2)
    #     denom = multiply(self.W, self.U @ self.V.T) @ self.V + 2 * self.reg * power(self.U, 3) + self.reg * self.U
    #     denom[denom == 0] = np.finfo(np.float64).eps
    #     self.U = multiply(self.U, num / denom)


    # @ignore_warnings
    # def update_V(self):
    #     '''Multiplicative update of V.
    #     '''
    #     num = multiply(self.W, self.X_train).T @ self.U + 3 * self.reg * power(self.V, 2)
    #     denom = multiply(self.W, self.U @ self.V.T).T @ self.U + 2 * self.reg * power(self.V, 3) + self.reg * self.V
    #     denom[denom == 0] = np.finfo(np.float64).eps
    #     self.V = multiply(self.V, num / denom)


    def error(self):
        '''Error for penalty function algorithm.

        In the paper, only reg_error is considered for early stop detection.
        '''
        X_gt = self.X_train
        X_pd = self.U @ self.V.T

        # X_gt[X_gt == 0] = np.finfo(np.float64).eps
        # X_pd[X_pd == 0] = np.finfo(np.float64).eps

        rec_error = 0.5 * np.sum(multiply(self.W, power(X_gt - X_pd, 2)))
        
        reg_error = 0.5 * np.sum(power(power(self.U, 2) - self.U, 2))
        reg_error += 0.5 * np.sum(power(power(self.V, 2) - self.V, 2))

        error = rec_error + self.reg * reg_error
        return error, rec_error, reg_error
