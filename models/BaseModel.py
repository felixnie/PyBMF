import numpy as np
from utils import show_matrix, matmul, to_sparse
import time
from scipy.sparse import lil_matrix


class BaseModel():
    def __init__(self):
        raise NotImplementedError("Missing init method.")
    

    def check_params(self, **kwargs):
        '''Check parameters.

        Used in model initialization, fitting and evaluation.

        Parameters
        ----------
        k : int
        seed : int
        task : str, {'prediction', 'reconstruction'}
        display : bool, default: False
        verbose : bool, default: False
        scaling : float, default: 1.0
        pixels : int, default: 2
        '''
        # trigger when it's mentioned in kwargs
        if "task" in kwargs:
            task = kwargs.get("task")
            assert task in ['prediction', 'reconstruction'], "Eval task is either 'prediction' or 'reconstruction'."
            self.task = task
            print("[I] task         :", self.task)
        if "k" in kwargs:
            k = kwargs.get("k")
            if k is None:
                print("[I] Running without k.")
            self.k = k
            print("[I] k            :", self.k)
        if "seed" in kwargs:
            seed = kwargs.get("seed")
            if seed is None and not hasattr(self,'seed'): # use time as self.seed
                seed = int(time.time())
                self.seed = seed
                self.rng = np.random.RandomState(seed)
                print("[I] seed         :", self.seed)
            elif seed is not None: # overwrite self.seed
                self.seed = seed
                self.rng = np.random.RandomState(seed)
                print("[I] seed         :", self.seed)
            else: # self.rng remains unchanged
                pass
        # trigger during initialization
        if not hasattr(self, 'verbose'):
            self.verbose = False
            print("[I] verbose      :", self.verbose)
        if not hasattr(self, 'display'):
            self.display = False
            print("[I] display      :", self.display)
        # trigger when it's getting changed
        if "verbose" in kwargs:
            verbose = kwargs.get("verbose")
            if verbose != self.verbose:
                self.verbose = verbose
                print("[I] verbose      :", self.verbose)
        if "display" in kwargs:
            display = kwargs.get("display")
            if display != self.display:
                self.display = display
                print("[I] display      :", self.display)
        # trigger no matter if it's mantioned or not
        if "scaling" in kwargs and self.display:
            self.scaling = kwargs.get("scaling")
            print("[I]   scaling    :", self.scaling)
        else:
            self.scaling = 1.0
        if "pixels" in kwargs and self.display:
            self.pixels = kwargs.get("pixels")
            print("[I]   pixels     :", self.pixels)
        else:
            self.pixels = 2


    def fit(self, X_train, X_val=None, **kwargs):
        """Fit the model to observations, with validation if necessary.

        Please implement your own fit method.
        
        X_train : array, spmatrix
            Data for matrix factorization.
        X_val : array, spmatrix
            Data for model selection.
        kwargs :
            Common parameters that are checked and set in `BaseModel.check_params()` and the model-specific parameters included in `self.check_params()`.
        """
        raise NotImplementedError("Missing fit method.")
    

    def load_dataset(self, X_train, X_val=None):
        """Load train and validation data.

        For matrices that are modified frequently, lil (LIst of List) or coo is preferred.
        For matrices that are not getting modified, csr or csc is preferred.

        X_train : array, spmatrix
        X_val : array, spmatrix
        """
        if X_train is None:
            raise TypeError("Missing training data.")
        if X_val is None:
            print("[I] Missing validation data.")
        self.X_train = to_sparse(X_train, 'csr')
        self.X_val = None if X_val is None else to_sparse(X_val, 'csr')

        self.m, self.n = self.X_train.shape


    def init_model(self):
        """Initialize factors and logging variables.

        U : spmatrix
        V : spmatrix
        logs : dict
            The dict containing dataframes, arrays and lists.
        """
        self.U = lil_matrix(np.zeros((self.m, self.k)))
        self.V = lil_matrix(np.zeros((self.n, self.k)))
        self.logs = {}


    def early_stop(self, msg: str, k: int=None):
        print("[W] Stopped in advance: " + msg)
        if k is not None:
            print("[W]   got {} factor(s).".format(k))
            self.U = self.U[:, :k]
            self.V = self.V[:, :k]
    
    
    def print_msg(self, msg, type='I'):
        if self.verbose:
            print("[{}] {}".format(type, msg))


    def predict(self):
        self.X_pd = matmul(self.U, self.V.T, boolean=True, sparse=True)


    def show_matrix(self, settings=None, scaling=None, pixels=None, **kwargs):
        """The show_matrix() wrapper for BMF models.

        If `settings` is missing, show the factors and their boolean product.
        """
        scaling = self.scaling if scaling is None else scaling
        pixels = self.pixels if pixels is None else pixels

        if settings is None:
            self.predict()
            settings = [(self.X_pd, [0, 0], "X"), 
                        (self.U, [0, 1], "U"), 
                        (self.V.T, [1, 0], "V")]

        show_matrix(settings=settings, scaling=scaling, pixels=pixels, **kwargs)


    # def cover(self, X=None, Y=None, w=None, axis=None):
    #     '''Measure the coverage of X using Y.

    #     Parameters
    #     ----------
    #     X : spmatrix, optional
    #         Ground-truth matrix. If not explicitly assigned, `X` is `self.X_train`.
    #     Y : spmatrix, optional
    #         Predicted matrix. If not explicitly assigned, `Y` is the Boolean product of `self.U` and `self.V`.
    #     w : float in [0, 1], optional
    #         The weights [1 - `w`, `w`] are the reward for coverage and the penalty for over-coverage. It can also be considered as the lower-bound of true positive ratio when `cover` is used as a factorization criteria.
    #     axis : int in {0, 1}, default: None
    #         To return the overall or the row/column-wise coverage score.

    #     Returns
    #     -------
    #     result : float, array
    #         The overall or the row/column-wise coverage score.
    #     '''
    #     if X is None:
    #         X = self.X_train
    #     if Y is None:
    #         Y = matmul(self.U, self.V.T, sparse=True, boolean=True)
    #     if w is None:
    #         w = self.w
    #     return cover(X, Y, w, axis)


    # def error(self, X=None, Y=None, axis=None):
    #     '''Measure the coverage error of X using Y.

    #     Returns
    #     -------
    #     result : float, array
    #         The overall or the row/column-wise error.
    #     '''
    #     if X is None:
    #         X = self.X_train
    #     if Y is None:
    #         Y = matmul(self.U, self.V.T, sparse=True, boolean=True)
        # return ERR(X, Y, axis)
    

    # def evaluate(self, X_gt, df_name, task, metrics=[], extra_metrics=[], extra_results=[], **kwargs):
    #     """Evaluate metrics with given ground-truth data and save results to a dataframe.

    #     X_gt : array, spmatrix
    #     df_name : str
    #         Name of the dataframe that the results are going to be saved under.
    #     task : str
    #     matrics : list of str
    #         List of metric names to be evaluated.
    #     extra_metrics : list of str
    #         List of extra metric names.
    #     extra_results : list of int and float
    #         List of results of extra metrics.
    #     kwargs :
    #         Common parameters that are checked and set in `BaseModel.check_params()`.
    #     """
    #     self.check_params(**kwargs)

    #     if X_gt is None:
    #         return

    #     extra_metrics = ['time'] + extra_metrics
    #     extra_results = [pd.Timestamp.now().strftime("%d/%m/%y %I:%M:%S")] + extra_results

    #     if not df_name in self.logs:
    #         self.logs[df_name] = pd.DataFrame(columns=extra_metrics+metrics)

    #     results = self.eval(X_gt, metrics=metrics, task=task)

    #     add_log(df=self.logs[df_name], line=extra_results+results, verbose=self.verbose, caption=df_name)


