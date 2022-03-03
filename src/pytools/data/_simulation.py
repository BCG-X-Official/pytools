"""
Utilities for creating simulated data sets.
"""
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.linalg import toeplitz

from ..api import AllTracker

__all__ = ["sim_data"]


__tracker = AllTracker(globals())


def sim_data(
    n: int = 100,
    intercept: float = -5,
    two_way_coef: Optional[Tuple[float, float, float]] = None,
    linear_vars: int = 10,
    linear_var_coef: Optional[Sequence[float]] = None,
    noise_vars: int = 0,
    corr_vars: int = 0,
    corr_type: str = "AR1",
    corr_value: float = 0,
    surg_err: float = 0.05,
    bin_var_p: float = 0,
    bin_coef: float = 0,
    outcome: str = "classification",
    regression_err: Optional[float] = None,
    seed_val: int = 4763546,
) -> pd.DataFrame:
    """
    Simulate data for classification or regression that includes an interaction between
    two linear features, and some non-linear and linear features.

    Noise variables, correlated variables that are not predictive and surrogate features
    which are just derived from features that are predictive are also added.

    This function is for the most part a direct translation of the ``twoClassSim``
    function from the R package caret -- the option for an ordinal outcome and binary
    outcome mis-labelling were omitted. Full credit for the approach used for simulating
    binary classification data goes to the authors and contributors of caret
    [`Kuhn, M. (2008). Caret package. Journal of Statistical Software, 28(5).
    <https://rdrr.io/cran/caret/man/twoClassSim.html>`_]

    Key modifications compared to the *R* implementation:

    1.  The ordinal outcome option has not been translated
    2.  Mis-labelling of the binary outcome has not been translated
    3.  The addition of a linear feature that is a copy of another used in the linear
        predictor with a small amount of noise has been added to allow for the study
        of variable surrogacy
    4.  Option for a binary predictor and surrogate has been added
    5.  Toggle option for regression versus classification has been added
    6.  Arguments for the coefficients of primary predictors of interest has been added

    :param n: number of observations
    :param intercept: value for the intercept which can be modified to generate class
        imbalance
    :param two_way_coef: tuple of three coefficients: two linear terms and an
        interaction effect
    :param linear_vars: number of linear features
    :param linear_var_coef: an optional list of coefficients for linear features if
        the default is not desired
    :param noise_vars: number of unrelated independent noise features (do not
        contribute to the linear predictor)
    :param corr_vars: number of unrelated correlated noise features (do not contribute
        to the linear predictor)
    :param corr_type: type of correlation (exchangeable or auto-regressive) for
        correlated noise features
    :param corr_value: correlation for correlated noise features
    :param surg_err: degree of noise added to first linear predictor
    :param bin_var_p: prevalence for a binary feature to include in linear predictor
    :param bin_coef: coefficient for the impact of binary feature on linear predictor
    :param outcome: can be either classification for a binary outcome or regression
        for a continuous outcome
    :param regression_err: the error to be used in simulating a regression outcome
    :param seed_val: set a seed for reproducibility
    :return: data frame containing the simulated features and target for classification
    """

    # set seed
    np.random.seed(seed=seed_val)

    # add two correlated normal features for use in creating an interaction term in the
    # linear predictor
    sigma = np.array([[2, 1.3], [1.3, 2]])
    mu = [0, 0]
    tmp_data = pd.DataFrame(
        np.random.multivariate_normal(mu, sigma, size=n),
        columns=["TwoFactor1", "TwoFactor2"],
    )

    # add independent linear features that contribute to the linear predictor
    if linear_vars > 0:
        lin_cols = ["Linear" + str(x) for x in range(1, linear_vars + 1)]
        tmp_data = pd.concat(
            [
                tmp_data,
                pd.DataFrame(np.random.normal(size=(n, linear_vars)), columns=lin_cols),
            ],
            axis=1,
        )
    else:
        lin_cols = None

    # add non-linear features that contribute to the linear predictor
    tmp_data["Nonlinear1"] = pd.Series(np.random.uniform(low=-1.0, high=1.0, size=n))
    tmp_data = pd.concat(
        [
            tmp_data,
            pd.DataFrame(
                np.random.uniform(size=(n, 2)), columns=["Nonlinear2", "Nonlinear3"]
            ),
        ],
        axis=1,
    )

    # add independent noise features that do not contribute to the linear predictor
    if noise_vars > 0:
        noise_cols = ["Noise" + str(x) for x in range(1, noise_vars + 1)]
        tmp_data = pd.concat(
            [
                tmp_data,
                pd.DataFrame(
                    np.random.normal(size=(n, noise_vars)), columns=noise_cols
                ),
            ],
            axis=1,
        )

    # add correlated noise features that do not contribute to the linear predictor
    if corr_vars > 0:
        if corr_type == "exch":
            vc = corr_value * np.ones((corr_vars, corr_vars))
            np.fill_diagonal(vc, 1)

        elif corr_type == "AR1":
            vc_values = corr_value ** np.arange(corr_vars)
            vc = toeplitz(vc_values)

        else:
            raise ValueError(
                f'arg corr_type must be "exch" or "AR1", but got {repr(corr_type)}'
            )

        corr_cols = ["Corr" + str(x) for x in range(1, corr_vars + 1)]
        tmp_data = pd.concat(
            [
                tmp_data,
                pd.DataFrame(
                    np.random.multivariate_normal(np.zeros(corr_vars), vc, size=n),
                    columns=corr_cols,
                ),
            ],
            axis=1,
        )

    # add a surrogate linear feature that does not contribute to the linear predictor
    if linear_vars > 0:
        tmp_data["Linear1_prime"] = tmp_data["Linear1"] + np.random.normal(
            0, surg_err, size=n
        )

    # add a binary feature that contributes to the linear predictor
    if bin_var_p > 0:
        tmp_data["Binary1"] = np.where(np.random.uniform(size=n) <= bin_var_p, 0, 1)

    # generate linear predictor
    if two_way_coef is None:
        two_way_coef = (4.0, 4.0, 2.0)

    lp = (
        intercept
        - two_way_coef[0] * tmp_data.TwoFactor1
        + two_way_coef[1] * tmp_data.TwoFactor2
        + two_way_coef[2] * tmp_data.TwoFactor1 * tmp_data.TwoFactor2
        + tmp_data.Nonlinear1**3
        + 2 * np.exp(-6 * (tmp_data.Nonlinear1 - 0.3) ** 2)
        + 2 * np.sin(np.pi * tmp_data.Nonlinear2 * tmp_data.Nonlinear3)
    )

    # add independent linear features to the linear predictor if required
    if linear_vars > 0:
        if linear_var_coef is None:
            lin_coef = np.linspace(linear_vars, 1, num=linear_vars) / 4
            neg_idx = list(range(1, linear_vars, 2))
            lin_coef[neg_idx] *= -1
            lp += tmp_data[lin_cols].dot(lin_coef)

        elif linear_var_coef is not None:
            if linear_vars != len(linear_var_coef):
                raise ValueError(
                    "User defined linear feature coefficient list must be of length "
                    f"{linear_vars}"
                )
            lp += tmp_data[lin_cols].dot(linear_var_coef)

    # add binary feature to the linear predictor if required
    if bin_var_p > 0:
        lp += bin_coef * tmp_data["Binary1"]
        tmp_data["Binary1_prime"] = 1 - tmp_data["Binary1"]

    # create classification outcome from linear predictor
    if outcome == "classification":

        # convert to a probability
        prob = 1 / (1 + np.exp(-lp))

        # generate target
        tmp_data["target"] = np.where(prob <= np.random.uniform(size=n), 0, 1)

    # create regression outcome
    elif outcome == "regression":

        # continuous outcome based on linear predictor
        tmp_data["target"] = (
            np.random.normal(lp, size=n)
            if regression_err is None
            else np.random.normal(lp, regression_err, size=n)
        )

    return tmp_data


__tracker.validate()
