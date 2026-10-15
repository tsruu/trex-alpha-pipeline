# Trexsim Builtin Operators

> This is not exhaustive — custom operators can always be created.

32 builtin operators, grouped by prefix: element-wise (`at_`), cross-sectional (`cs_`), and time-series (`ts_`).

---

## Element-wise (`at_`)

### `at_nan2zero(A)`
Replace nonfinite values to zeros

Returns in place `np.nan_to_num(a)`, replacing `np.nan` and `np.inf` with zeros.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when adding two alphas to ensure nan values do not turn finite values into nans and cause loss of data. Also useful when slowing down sparse variables (taking the mean of nans gives nans).

**Example**
```
>>> input  = [[2, 3, np.nan, 3, np.inf],
              [3, 0,      4, 5,     -2]]
>>> at_nan2zero(input)
[[2, 3, 0, 3, 0],
 [3, 0, 4, 5, -2]]
```

---

### `at_signlog(A)`
Sign-preserving log1p transformation

Returns in place `np.sign(a) * np.log1p(np.abs(input))`

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
log1p(x) is equivalent to log(1+p). One is added so that zero maps to zero (log1p(0) = 0). Useful when taking logarithm of data that may contain both positive and negative values.

**Example**
```
>>> input  = [[2, 3, np.nan, 3, np.inf],
              [3, 0,      4, 5,     -2]]
>>> at_signlog(input)
[[ 1.0986, 1.3863, np.nan, 1.3863, np.nan],
 [ 1.3863,      0, 1.6094, 1.7918,-1.0986]]
```

---

### `at_signsqrt(A)`
Sign-preserving sqrt transformation

Returns in place `np.sign(a) * np.sqrt(np.abs(input)+1)`

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[2, 3, np.nan, 3, np.inf],
              [3, 0,      4, 5,     -2]]
>>> at_signsqrt(input)
[[1.7321, 2.0000, np.nan, 2.0000,  np.nan]
 [2.0000,      0, 2.2361, 2.4495, -1.7321]]
```

---

### `at_zero2nan(A)`
Replace zeros to nans

Returns `a[a==0] = np.nan`, replacing zeros with np.nan.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when you want to take a mean of non-zero values only, using nanmean, for example.

**Example**
```
>>> input  = [[2, 3, np.nan, 3, np.inf],
              [3, 0,      4, 5,     -2]]
>>> at_zero2nan(input)
[[2,      3, np.nan, 3, np.inf],
 [3, np.nan,      4, 5,     -2]]
```

---

## Cross-sectional (`cs_`)

### `cs_booksize(input, booksize)`
Normalize positions of input portfolio such that the sum of all positive and negative positions sum to the same number everyday

**Parameters**
- `input: ndarray, shape (n, d)`
- `booksize: target booksize of long and short book, scalar`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
In case the original alpha has all negative or all positive values, the output portfolio will be unbalanced with 0 booksize on the side that didn't have any values in the input.

**Example**
```
>>> alpha = cs_booksize(-ret1, 1e6)
```

---

### `cs_factorneut(input, [factor1, factor2], int_factors=[int_factor1, int_factor2])`
Neutralize the input variable to style factors (e.g. size, value, momentum)

**Parameters**
- `input: ndarray, shape (n, d)`
- `factor1, factor2, etc: analog value factors (e.g. barra_momentum) against which to neutralize the signal, ndarray, shape (n,d)`
- `int_factor1, int_factor2, etc: integer value factors (e.g. industry) against which to neutralize the signal, ndarray, shape (n,d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
This operator will compute and return everyday the portion of the input data variable that is orthogonal to all of the factors passed.

**Example**
```
>>> alpha = cs_factorneut(-ret1, [barra_size, barra_momentum, barra_beta, barra_value], int_factors=[industry])
```

---

### `cs_harmonic_mean(A)`
Compute harmonic mean across all stocks every day

Compute the cross-sectional harmonic mean each day: `A[:,day] = 1 / np.nanmean(1 / A[:,day])`.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Harmonic mean is equivalent to the reciprocal of the arithmetic mean of the reciprocals of the values. This harmonic mean is copied to all elements in the column. The output will therefore have the same values for all stocks on each day, and will need to be modified further to produce a signal. For example, `cs_harmonic_mean(input) - ts_harmonic_mean(input,10)`.

**Example**
```
>>> input  = [[1,   3,      2,   3,   4],
              [3,   0, np.nan,   5,  -2]]
>>> cs_harmonic_mean(input)
[[1.5,  0,   2,   3.75,  -8],
 [1.5,  0,   2,   3.75,  -8]]
```

---

### `cs_indneut(input, grouping)`
Returns a neutralized version of input data variable to grouping data variable.

**Parameters**
- `input: ndarray, shape (n, d)`
- `grouping: grouping data variable (e.g. industry or subindustry, integer values are expected), ndarray, shape (n,d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
This operator will compute and subtract out the group mean value each day for each group. This will return a transformed version of the input data variable that will be neutralized to the grouping variable.

**Example**
```
>>> alpha = cs_indneut(-ret1, industry)
```

---

### `cs_poslimit(input, pos_limit)`
This operator places an upper bound on the limit of the portfolio that can be allocated to any single stock

**Parameters**
- `input: ndarray, shape (n, d)`
- `pos_limit: how much can be allocated to a single stock, scalar (between 0-1)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Simply computes booksize of portfolio on that day and then thresholds stock positions to below pos_limit * portfolio booksize.

**Example**
```
>>> alpha = cs_poslimit(-ret1, 0.01)
```

---

### `cs_rank(A)`
Assign rank to stock values every day

Compute ranks and scale uniformly between 1 and 2 for convenience.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when you want to isolate a certain fraction of all the data, for example `(cs_rank(ret1)>1.9)` is a matrix of 1's for the top 10% of stocks each day, when sorted by ret1.

This method is an efficient way of doing `A[:,day] = scipy.stats.rankdata(A[:,day], 'dense')` and scaling the result to be between 1 and 2 each day.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> cs_rank(input)
[[1.0000, 2.0000, np.nan, 1.0000, np.nan],
 [1.5000, 1.0000, 1.5000, 2.0000, 1.0000],
 [2.0000, 1.5000, np.nan, np.nan, 2.0000]]
```

---

### `cs_remove_middle(A, filter_percentile)`
Keep only the extreme cross-sectional values by removing the middle values

Remove the `filter_percentile` of middle values among stocks each day.

**Parameters**
- `A: ndarray, shape (n, d)`
- `filter_percentile: float in [0,1)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Sometimes the extreme values in an alpha will have stronger predictive power than the middle values, so trading only on the tails of values can produce higher returns but at the cost of higher turnover and higher volatility of pnl.

For example, `filter_percentile = 0.80` means we will remove the middle 80% of the data and keep 10% of each tail.

**Example**
```
>>> input = [0.81, 0.91, 0.13, 0.91, 0.63, 0.10, 0.28]
>>> cs_remove_middle(input, 0.5)
[np.nan, np.nan, np.nan, 0.91, np.nan, 0.10, np.nan]
```

---

### `cs_scale(A)`
Scale the data between 1 and 2

Applies min-max scaling to the data each day and scales to 1 and 2: `A[:,day] = 1 + (A[:,day] - np.nanmin(A[:,day])) / (np.nanmax(A[:,day]) - np.nanmin(A[:,day]))`.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when adding two data sets of different magnitudes, return and volume, for example. Apply to both to rescale but preserve relative magnitudes inside each variable.

Different from `cs_rank` in that it'll preserve relative distances between values.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> cs_scale(input)
[[1.0000, 2.0000, np.nan, 1.0000, np.nan],
 [1.5000, 1.0000, 1.5000, 2.0000, 1.0000],
 [2.0000, 1.3333, np.nan, np.nan, 2.0000]]
```

---

### `cs_shrink_balance(input)`
Compute and compare the sum of all long positions to the sum of all short positions in a portfolio everyday. Shrink the size of the larger book such that it equals the smaller book size so that the portfolio is balanced.

**Parameters**
- `input: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Generally used in place of `cs_booksize` to ensure a balanced portfolio without violating constraints applied previously (i.e. volume constraints or locates).

**Example**
```
>>> alpha = cs_shrink_balance(-ret1)
```

---

### `cs_winsor(A, filter_percentile, remove_extreme)`
Winsorizes or removes extreme values

Sets extreme values to `filter_percentile` values or zeros.

**Parameters**
- `A: ndarray, shape (n, d)`
- `filter_percentile: float in [0,1)`
- `remove_extreme: boolean`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when dealing with outliers. For example, ret1 data has many extreme outlier values that may be difficult to predict.

See https://en.wikipedia.org/wiki/Winsorizing.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> cs_winsor(input, 0.35, remove_extreme=False)
[[3,   1, np.nan,      3, np.nan],
 [3,   1,      4,      5,    -2],
 [3,   1, np.nan, np.nan,     1]]
```

---

### `cs_zscore(A)`
Normalize the data by centering and standardizing

Computes the z-score of each stock data each day: `A[:,day] = (A[:,day] - np.nanmean(A[:,day])) / np.nanstd(A[:,day])`.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Apart from calculating z-scores, the operator can be used when adding two data sets of different magnitudes, return and volume, for example. Apply to both to rescale while preserving relative magnitudes inside each variable.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> cs_zscore(input)
[[ -1.2247,  1.3363,  np.nan, -1.0000,  np.nan],
 [       0, -1.0690,  np.nan,  1.0000,  np.nan],
 [  1.2247, -0.2673,  np.nan,  np.nan,  np.nan]]
```

---

## Time-series (`ts_`)

### `ts_corr_binary(A, B, days)`
Computes stock level correlation between two data variables

Computes correlation between two data variables in the past `days` time points for each stock.

**Parameters**
- `A: ndarray, shape (n, d)`
- `B: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Correlation can be used to calculate beta between stock and market returns using `close_SPX` variable, which is the S&P500 close price.

**Example**
```
>>> input_1 = [[ 1,   3,   2,   3,   4],
               [ 3,   0,   4,   5,  -2]]
>>> input_2 = [[ 2,   3,   3,   4,   3],
               [ 2,   1,   5,   4,  -2]]
>>> ts_corr_binary(input_1, input_2, 3)
[[np.nan, np.nan, 0.8660, 0.5000,      0],
 [np.nan, np.nan, 0.8462, 0.9078, 0.9651]]
```

---

### `ts_delay(A, days)`
Sets value today to the value `days` ago.

Set each `A[:,day]` to `A[:,day-days]`. i.e. rolls the matrix along the time dimension: `np.roll(A,days,1)`

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when comparing past data to present data.

The days without appropriate past data `A[:, :days]` is set to `np.nan`.

**Example**
```
>>> input = [[ 1,   3,   2,   3,   4],
             [ 3,   0,   4,   5,  -2]]
>>> ts_delay(input, 2)
[[np.nan, np.nan,   1,   3,   2],
 [np.nan, np.nan,   3,   0,   4]]
```

---

### `ts_diff(A, n)`
Computes the `n`-th discrete difference along the time dimension

The first difference is given by `out[n] = A[n+1] - A[n]` along the time axis, higher differences are calculated by using diff recursively e.g. `ts_diff(input,2) = ts_diff(ts_diff(input,1),1)`.

**Parameters**
- `A: ndarray, shape (n, d)`
- `n: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when you want to slow or accelerate the trading of an alpha, `ret5 = ts_delay(ret5,1) + ts_diff(ret5,1)`.

**Example**
```
>>> input = [[ 1,   3,   2,   3,   4],
             [ 3,   0,   4,   5,  -2]]
>>> ts_diff(input, 1)
[[np.nan,  2,  -1,  1,  1],
 [np.nan, -3,   4,  1, -7]]
```

---

### `ts_fill(A)`
Forward fill the data

Iterate through all days and replace nans today with previous day's values.

**Parameters**
- `A: ndarray, shape (n, d)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when dealing with sparse data.

For example, quarterly earnings data may have a new entry every 63 days. `ts_fill` allows you to populate the matrix with constant values of most recent earnings release.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> ts_fill(input)
[[2,   3,   3,   3, np.inf],
 [3,   0,   4,   5,     -2],
 [4,   1,   1,   1,      1]]
```

---

### `ts_harmonic_mean(A, days)`
Harmonic mean of the data in the last `days`

Compute the harmonic mean in the past `days` each day.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when dealing with outliers or ratios.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> ts_harmonic_mean(input)
[[np.nan,   2.400,  3.429,  2.667, 1.333],
 [np.nan,   3.429, np.nan, np.nan, 4.000],
 [np.nan,   1.600, np.inf, -3.000, 3.429]]
```

---

### `ts_max(A, days)`
Maximum in the past `days`

Compute the maximum value in the past `days` each day.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> ts_max(input, 2)
[[ 2,   3, np.nan,      3, np.inf],
 [ 3,   3,      4,      5,      5],
 [ 4,   4, np.nan, np.nan,      1]]
```

---

### `ts_mean(A, days)`
Mean in the past `days`

Compute the mean value in the past `days` each day.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
The most straightforward way to slow trading of a signal is to apply a simple moving average.

Another way to think about `ts_mean(A, days)` is holding onto a position for `days`.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> ts_mean(input, 2)
[[ np.nan, 2.5000, np.nan, 3.0000, np.nan],
 [ np.nan, 1.5000, 2.0000, 4.5000, 1.5000],
 [ np.nan, 2.5000, np.nan, np.nan, 1.0000]]
```

---

### `ts_mean_exp(A, days, exp_factor)`
Exponentially weighted average in the past `days` with `exp_factor`

Compute the exponentially weighted average value in the past `days` each day.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`
- `exp_factor: float in (0,1)`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
`exp_factor` of 0.1 is like dividing the change each day by 10: `a[n] = 0.1 * (a[n] - a[n-1]) + a[n-1]`.

It usually takes about `2 / exp_factor` days for a change to dissipate. As such, `exp_factor` should be set to about `2 / days`.

Common combinations are: `ts_mean_exp(A, 20, 0.1)`, `ts_mean_exp(A, 10, 0.2)`, and `ts_mean_exp(A, 5, 0.4)`.

**Example**
```
>>> input  = [[ 2,   3, np.nan,      3, np.inf],
              [3,   0,      4,      5,     -2],
              [4,   1, np.nan, np.nan,      1]]
>>> ts_mean(input, 3, 0.2)
[[ 2.0000,  2.5556,  np.nan,  3.0000,  np.nan],
 [ 3.0000,  1.3333,  2.4262,  3.3607,  1.8689],
 [ 4.0000,  2.3333,  np.nan,  np.nan,  1.0000]]
```

---

### `ts_median(A, days)`
Nanmedian of values in the past `days`

Compute the median in the past `days` each day, ignoring nans.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Median is less sensitive to outliers than mean.

**Example**
```
>>> input  = [[ 1, 2, 3,      4],
              [ 4, 5, 6, np.nan]]
>>> ts_median(input, 2)
[[ np.nan,  1.5000,  2.5000,  3.5000],
 [ np.nan,  4.5000,  5.5000,  np.nan]]
```

---

### `ts_min(A, days)`
Nanmin of values in the past `days`

Compute the min in the past `days` each day, ignoring nans.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 1, 2, 3,      4],
              [ 4, 5, 6, np.nan]]
>>> ts_min(input, 3)
[[ 1, 1, 1,      2],
 [ 4, 4, 4, np.nan]]
```

---

### `ts_norm(A, days)`
Center data with the average value in the past `days`

Scales the data by dividing by the average value: `A[:,day] /= np.nanmean(A[:,day-days:day])`.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input = [[ 1,   3,   2,   3,   4],
             [ 3,   0,   4,   5,  -2]]
>>> ts_norm(input, 3)
[[np.nan, np.nan, 1.0000, 0.3750,  0.5556],
 [np.nan, np.nan, 0.5714, 0.5556, -0.2857]]
```

---

### `ts_rank(A, days)`
Assign rank to today's value within past `days`

Compute ranks across the time series and scale uniformly between 1 and 2 for convenience.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 1, 2, 3,      4],
              [ 4, 5, 6, np.nan]]
>>> ts_rank(input, 3)
[[ 1.500, 2.000, 2.000,  2.000],
 [ 1.500, 2.000, 2.000, np.nan]]
```

---

### `ts_skew(A, days)`
Compute the skewness of the finite values in the last `days`

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 1, 2, 2, 3],
              [ 2, 3, 3, 2]]
>>> ts_skew(input, 3)
[[ np.nan, np.nan, -0.7071,  0.7071],
 [ np.nan, np.nan, -0.7071, -0.7071]]
```

---

### `ts_std(A, days)`
Compute the standard deviation of the finite values in the last `days`

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 1, 3,      2, 3,  4],
              [ 3, 0, np.nan, 5, -2]]
>>> ts_std(input, 3)
[[ np.nan, np.nan, 1.0000, 0.5774, 1.0000],
 [ np.nan, np.nan, np.nan, 3.5355, 4.9497]]
```

---

### `ts_std_normalized(A, days)`
Standardize today's values

Divides today's value by the standard deviation of the finite values in the last `days`.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 1, 3,      2, 3,  4],
              [ 3, 0, np.nan, 5, -2]]
>>> ts_std_normalized(input, 3)
[[ np.nan, np.nan, 2.0000, 5.1962,  4.0000],
 [ np.nan, np.nan, np.nan, 1.4142, -0.4041]]
```

---

### `ts_sum(A, days)`
Cumulative sum in the past `days`

Compute the sum of all finite values in the past `days`.

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Notes**
Useful when accumulating signals. Nans are converted into zeros.

**Example**
```
>>> input  = [[ 1, 3,      2, 3,  4],
              [ 3, 0, np.nan, 5, -2]]
>>> ts_sum(input, 3)
[[ 1, 4, 6, 8, 9],
 [ 3, 3, 3, 5, 3]]
```

---

### `ts_zscore(A, days)`
Normalize today's values by centering and standardizing

**Parameters**
- `A: ndarray, shape (n, d)`
- `days: int`

**Returns**
- `V: ndarray, shape (n, d)`

**Example**
```
>>> input  = [[ 0.6557, 0.8491, 0.6787, 0.7431, 0.6555],
              [ 0.0357, 0.9340, 0.7577, 0.3922, 0.1712]]
>>> ts_zscore(input, 3)
[[ np.nan, np.nan, np.nan,  0.1322, -0.8782],
 [ np.nan, np.nan, np.nan, -0.3448, -1.1361]]
```