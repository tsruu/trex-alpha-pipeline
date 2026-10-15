# Trexquant Alpha Generation Competition — Tutorial

> Transcribed from `Trexquant_Competition_Tutorial.pdf`. Diagrams and screenshots are omitted; where a figure appeared, a `> [Figure: ...]` note marks the spot and its caption/relevant numbers are preserved.

---

## Alpha Generation Competition

**Overview.** Participants will build quantitative alphas using a provided set of data variables and operators. A tutorial will be available to get you up to speed.

### Alpha Qualification

Each submitted alpha must pass the following criteria to count toward your scores:

- **Minimum IR:** Information Ratio (`ir`) > 0.07
- **Correlation:** ≤ 50% correlated to any other alpha already in your qualified pool
- **Override:** If correlation exceeds 50%, the new alpha must demonstrate at least 20% higher IR/√Turnover than the correlated alpha

Only alphas that clear these thresholds are included in both scoring dimensions below.

### Scoring

Your final rank is determined by combining two sub-scores:

1. **Alpha Count** — The total number of qualified, uncorrelated alphas in your pool.
2. **Combined Performance** — All qualified alphas are aggregated into a single combined alpha, which is evaluated on out-of-sample data and ranked by performance.

### Final Ranking

Your ranks from (1) and (2) are summed. Lowest total rank wins. Prizes are awarded to the top N participants.

---

## Cheat Sheet

Each alpha is a matrix, rows = stocks, columns = dates, e.g.

```python
alpha = (open - close) / open
```

### Links

- 🔧 Operator descriptions can be found in the operator documentation.
- 💾 Data descriptions can be found in the data documentation.
- 📈 Metrics to look out for.
- ✅ Good alpha habits.

### Fast Mode vs. Slow Mode

| Fast Mode | Slow Mode |
|-----------|-----------|
| Simulates whole history at once | Simulates day by day using only past data |
| Much faster | More accurate |
| Good for idea screening | Required for submission |
| Can differ from reality | |

### Common reasons fast != slow

- Insufficient lookback
- Forward bias
- Corporate action adjustments (splits, dividends, etc.)

### Common Mistakes

- Using `0` when you mean no position
- Too little lookback in slow mode
- Forward bias from future data leakage
- Mixing variables with different units/scales
- Ignoring splits/dividends
- Writing slow loops instead of vectorized expression

---

## Introduction to Trexsim

If you're interested in developing alphas, a good place to start is by learning about Trexsim (alternatively referred to as Trexsim). This tutorial will help you get started with Trexsim and introduce you to the alpha simulator, so you can begin iterating on alpha ideas.

### What is Trexsim?

Trexsim is a backtesting tool used by Trexquant to test trading ideas, or alphas. With Trexsim, you can express your trading ideas as Python code and see how they would have performed in the past. One benefit of using a standardized backtesting tool like Trexsim is that it allows researchers to focus on implementing their alpha ideas without having to worry about the backtesting implementation. Trexsim has built-in functions for many commonly used operations, which can save development time.

### Examples of Trexsim Expressions

In some cases, you can express trading ideas in just a single line of Trexsim code. For example, the following line represents the alpha idea where the position in a stock should be the opposite of the average intraday return over the past five trading days:

```python
alpha = -ts_mean((close - open)/open, 5)
```

This expression says "bet in proportion to the mean value of the log return from 3am to 11am over the past five days".

### What Trexsim is not

While Trexsim is a powerful tool, it's not an all-purpose Python development environment. Trexsim only lets you simulate alpha performance and plot time series data. Due to constraints on memory and runtime, it's not well-suited for implementing complicated machine learning models.

---

## Alpha Research Process

The goal of alpha research is to find profitable and reproducible trading strategies. Alpha research can be broken down into two parts:

1. Sourcing trading ideas
2. Testing ideas

> [Figure: Schematic of the research loop — Observations / Theory / Data / Articles / Experience / Intuition → Idea → f(x) Code → Simulation → Alpha, with a feedback arrow from Simulation back to Idea.]

The main ingredient for a good alpha is a good trading idea. Good trading ideas are not hidden or hard to find. There are many good ideas in academic journals, books, magazines, blogs, forums, and specialist texts.

The key is to set up a continual stream of good trading ideas that are also a good fit for your skills and interests.

### Where can I find alpha ideas?

Broadly speaking, researchers generate alpha ideas in one of three ways:

1. Read academic research and implement the idea or extensions of the idea
2. Find ideas through news articles or the internet
3. Observe something about the behavior of the market or particular securities and formulate a hypothesis about what causes this behavior and how you can profit from it

Here are a few sources to review:

- Google Scholar
- SSRN
- Investopedia
- News websites like Bloomberg and MarketWatch
- Quantpedia

Perusing academic research is the most straightforward way of getting alpha ideas. Academic papers tend to explain their ideas, methods, and results more clearly than other sources. This makes them especially suitable for new researchers. Additionally, peer-reviewed papers in prestigious journals, in particular, tend to be higher in signal-to-noise than other sources. You can start with any paper that you find interesting.

While academic papers may initially seem complex and hard to read, their primary thesis is usually easily explainable and can be understood from the abstract itself. Here is an example:

> [Figure: Abstract of "The Trend in Firm Profitability and the Cross Section of Stock Returns." Key highlighted claim: firms with a higher profit trend have higher expected profits, and should thus command higher expected returns. Key Words: Gross profitability, trend in profitability, expected returns, asset pricing. JEL Classification: G12, G14.]

The main idea of this paper is that a firm's current profitability is a strong predictor of future profitability.

### Translating ideas into alphas

Once you have an alpha idea, you need to start testing it to create a tradeable alpha. This involves:

1. Make sure your idea can be formulated as a testable hypothesis. You should understand what tests are needed to confirm or disprove your hypothesis.
2. Find the data variables to implement your alpha idea. If it isn't in the allowed variables, then you'll need to go back to step 1.
3. Find or create operators that you will need to manipulate the input data into your desired alpha.
4. Iterate and improve on your alpha.

---

## Equity Alphas — A Brief Overview

An alpha refers to anything that can be used to predict future stock returns. It is a trading algorithm or program that takes financial data as input and generates a portfolio of stock positions as output. The term alpha can refer to the trading idea, the algorithm that implements the idea, or the portfolio that results from running this algorithm.

Every alpha in Trexsim is represented as a matrix, with each row corresponding to an asset being traded and each column corresponding to a date. Therefore, the alpha expresses a vector of desired positions across all assets in the trading universe for every day.

### Example Alpha Idea

As an example, consider the alpha idea "buy stocks that have decreased in price and sell (short) stocks that have increased in price." This idea is based on the concept of mean reversion, which states that returns tend to oscillate around a mean value. To test this idea, we can translate it into a mathematical expression using financial data variables. One simple implementation of this idea is:

```python
alpha = open - close
```

The `open` variable represents the price of different stocks at the beginning of the trading day, whereas the `close` variable represents the price of the same stocks at the end of the trading day. If a stock opened at $10 and closed at $12 today, our `open - close` alpha expression will generate a -2 value for tomorrow's desired position (i.e., 10 - 12 = -2) for this stock.

Negative amounts indicate that we want to short that stock. If you are not familiar with short selling, please refer to an introductory article on Investopedia.

This expression is evaluated for all days and all stocks by subtracting all the values in the `close` matrix data variable from the `open` matrix data variable. The resulting matrix is the basis for evaluating the performance of this alpha. The portfolio that we ultimately simulate will bet on stocks that have higher values of `open - close` and will bet against stocks that have lower values of `open - close`. It is a good idea to normalize alphas so that they represent dimensionless quantities. The `open - close` alpha expression has units of dollars per share, so it can be normalized by dividing by the price, which gives us:

```python
alpha = (open - close) / open
```

This expression now represents the return from the market open to market close for the stock. To simulate the alpha in Trexsim, we type the above formula and hit the "Simulate" button. The resulting plot shows us the performance of the alpha over time.

The output you are viewing shows the historical backtesting results for how this alpha would have performed if it had been applied consistently every day. We will delve into a detailed explanation of the numbers in the plot in the following chapters. You might notice that the alpha's booksize in the figure is 1.00 x 1.00, which means that the long shares held total to 1 million dollars and the short shares held similarly total to 1 million dollars. To achieve this, the alpha's long and short positions will be scaled such that they add up to 1 million. In the context of the toy example above, this means that stock A will have a position of -$666,667, stock B will have +$1,000,000 and stock C will have -$333,333.

---

## Operators

An operator is a function in Trexsim that can be used to apply a series of transformations to a data variable or an alpha.

Trexsim has operators for frequently used transformations available for use which we call built-in operators. You are free to use any of these operators to create alphas. Detailed documentation for all operators can be found in the operator reference.

You can also write your own operators in Trexsim. We will go over this later in this section.

Most operators fall into one of four categories depending on the type of transformation they apply to a 2D matrix:

- **Element-wise:** These apply to each element of the array and use the prefix `at_`. Examples include `at_nan2zero(A)` and `at_zero2nan(A)`.
- **Time series:** These apply to a single stock across time. They use the prefix `ts_`. A simple example is `ts_mean(A, days)` which calculates the rolling mean of stocks across the number of days specified.
- **Cross sectional:** These apply across stocks for a single day and use the prefix `cs_`. For example `cs_zscore` calculates the mean and standard deviation across the stocks for each day and calculates the Z-score for each stock.

### When should I write my own operator?

You should consider writing your own operator if the following two conditions are met:

1. You cannot find a relevant operator in the built-in operators. These operators are well-documented and have passed quality control checks for forward bias and bugs. Using these directly will save you development time.
2. You will use this operator multiple times. You can define functions that you will use on a one-off basis in Trexsim itself. See example below.

```python
def yearly_return(close):
    trading_days_per_year = 252
    out = np.full(close.shape, np.nan)
    past_close = ts_delay(close, 252)
    out = (close - past_close) / past_close
    return out

alpha = yearly_return(close)
```

An operator is written as a Python function. Simply add it using the Operator tab on Trexsim, and you can use it as you would any Python function.

For example, we can write the following operator to calculate the return over some time period. Notice that we can use existing operators like `ts_delay` to define new operators.

```python
def n_days_return(close, days):
    out = np.full(close.shape, np.nan)
    past_close = ts_delay(close, days)
    out = (close - past_close) / past_close
    return out
```

You can see any operators you have added previously on the Operator list page.

---

## Case Study: The High Volume Return Premium

> [Figure: Abstract of "The High-Volume Return Premium" by Simon Gervais, Ron Kaniel, and Dan H. Mingelgrin. The Journal of Finance, Vol. LVI, No. 3, June 2001. The abstract argues that stocks experiencing unusually high (low) trading volume over a day or a week tend to appreciate (depreciate) over the following month, consistent with the idea that shocks in trading activity affect a stock's visibility and subsequent demand/price.]

In this case study, we will study a paper on a volume alpha called "The High-Volume Return Premium", published in Journal of Finance in 2001 by Gervais, Kaniel, and Mingelgrin. Take a minute to read the abstract.

This paper claims that stocks with unusually high trading volume tend to outperform while those with unusually low trading volume tend to underperform. They first classified stocks into three groups -- high, low, and normal -- based on whether or not the stock has had a top 10% most or least volume in its last day (formation period) compared to its volume in the last 50 days (reference period).

> [Figure: Histogram dividing stocks into three groups by volume. The three groups are: low (0-20k daily volume, 100 stocks), normal (20k-2M, 800 stocks), and high (2M+, 100 stocks).]

After grouping stocks, they long the high volume stocks and short the low volume stocks during a trading period of 20 days. Using this strategy on small and medium stocks trading on NYSE in 1963-1996, the authors report annual excess returns of 11.0% and 10.4% after transaction costs.

Let's start by taking an inventory of ideas that are important in this paper:

- **Classifying stocks based on volume:** volume in formation period in top 10% of reference period
- **Trading rule**
  - Simple trading rule: short low volume stocks $1, long high volume stocks $1, held for 1, 10, 20, 50, or 100 days
  - Limit-order trading rule: send limit orders at the prevailing price; if not hit within one or two days, place market-on-close orders

The paper conducts additional tests and analysis using the following ideas:

- **Preselecting a universe of stocks:** exclude low-price stocks (< $5), new stocks (< one-year old), and unstable stocks (those that had merger/delisting/partial liquidation/seasoned equity offering)
- **Classifying stocks based on size:** market cap in 10-50 percentile (small), 50-80 percentile (medium), and 80-100 percentile (large)
- **Classifying stocks based on returns:** return in formation period in middle 40% or middle 20% of reference period
- **Classifying stocks based on momentum:** returns in top and bottom halves of reference period
- **Classifying stocks based on spread:** average bid-ask spread in test period below or above median
- **Classifying stocks based on short interest:** whether or not stock appeared in any of the monthly NYSE short interest data files

This might all seem daunting at first, but when we cut through all the smoke, the idea is simple: long high volume stocks and short low volume stocks.

Let's try implementing the basic idea of the paper first in Trexsim. We'll implement the simple trading rule based on unusual volume:

```python
# Long stocks whose volume today is in the top 10% of volumes in the past 50 days
# Short stocks whose volume today is in the bottom 10% of volumes in the past 50 days
# Hold for 20 days
lookback = 50
holding = 20
alpha = np.zeros(volume.shape)
for day in range(lookback, alpha.shape[1]):
    reference_volume = volume[:, day-lookback:day]
    today_volume = volume[:, day]
    high_volume = today_volume > np.nanpercentile(reference_volume, 90, 1)
    low_volume = today_volume < np.nanpercentile(reference_volume, 10, 1)
    portfolio = high_volume.astype('float') - low_volume.astype('float')
    alpha[:, day:np.maximum(day+holding, alpha.shape[1])] += portfolio[:, np.newaxis]
```

> [Figure: Simulation results for the loop-based version. ir 0.063, ret 0.056, tvr 1.584, stk 298-288, slow lb60 (20060329-20171130); ir 0.021, ret 0.017, tvr 1.563 for the later period (20130328-20171130). OS Test Results — Performance Test: ir since 2006: 0.063 (>0.07 threshold), ir since 2011: 0.072, ir since 2013: 0.021; tvr 1.584 (<0.5); numstk 585 (>100). Correlation Test: max corr(yours) 0.20 (<0.50), max corr(others) 0.60 (<0.90).]

Now let's try improving this idea. First, we can vectorize our code using built-in functions to speed up the simulation.

```python
# Long stocks whose volume today is in the top 10% of volumes in the past 50 days
# Short stocks whose volume today is in the bottom 10% of volumes in the past 50 days
# Hold for 20 days
lookback = 50
holding = 20
alpha = (ts_rank(volume, 50) > 1.9).astype('float') - (ts_rank(volume, 50) < 1.1).astype('float')
```

This speeds up the runtime by several orders of magnitude. Speed is important in research because it lets you iterate on your ideas quickly.

Second, let's try to make this more dynamic. We don't have to limit ourselves to equal-weight portfolios based on deciles. We also don't have to hold onto a stock for a set amount of time.

```python
# Bet based on how large or small the volume was in the past 50 days
alpha = ts_norm(volume, 50)
```

> [Figure: Simulation performance for `ts_norm(volume, 50)`. IR 0.013, TVR 1.003, DD 45.0, Ret 0.011, IR/sqrt(TVR) 0.013, Booksize 1.00x1.00, NumStks 741x808, Liq 459, LiqN 192, Region us.]

This treats volume ratio as a signal and places weights according to the strength of the signal. The low signals will be short and the high signals will be long. Because it bets more frequently and on more stocks, it has a stronger performance. However, its turnover is too high. We can try using `ts_mean_exp`, which will weigh recent information exponentially more than older information.

```python
alpha = ts_mean_exp(ts_norm(volume, 50), 20, 0.1)
```

> [Figure: Simulation performance for the exponential-moving-average version. IR -0.000, TVR 0.214, DD 37.3, Ret -0.000, IR/sqrt(TVR) -0.000, Booksize 1.00x1.00, NumStks 750x799, Liq 1873, LiqN 704, Region us. Caption: An exponential moving average of 20 days is like holding an exponentially decreasing amount of stock for 20 days.]

While the turnover is below the limit, its performance does not meet the thresholds for a trophy alpha. Specifically, this alpha starts to deteriorate in 2016 and makes losses in 2017. This could be due to a structural change in the market (increased competition among investors in the same time frame, new entrants like high frequency funds, change in regulation). Can we find another alpha from this? Here are some ideas:

- Bet on the long or short side only (e.g. `np.clip`)
- Bet on the outliers or inliers only (e.g. `cs_remove_middle` and `cs_winsor`)
- Bet using a different weighting scheme (e.g. `cs_rank`, `np.log`, `np.exp`)
- Bet using a condition (the paper suggests size, returns, momentum, spread, and short interest)

> [Figure: Alpha Editor showing `alpha = ts_mean_exp(ts_norm(volume,20) * (cs_rank(ts_std(volume, 10)) < 1.8), 3, 0.5)`. Simulation performance: IR 0.015, TVR 0.753, DD 36.4, Ret 0.010, IR/sqrt(TVR) 0.018, Booksize 1.00x1.00, NumStks 618x650, Liq 515, LiqN 212, Region us. Caption: We can strengthen the signal by conditioning it on its volatility.]

We can see that taking the original study -- which uses 49 day reference period, 1 day formation period, 20 day trading period -- and modifying it to trade more often, more safely, and on more stocks improved the results. This is also more in line with what we do here at Trexquant -- we use medium-frequency statistical arbitrage to profit from a large number of favorable bets.

We can go further using the ideas from this paper. For example:

- Do other trading-volume data have predictive power? (e.g. intraday volume, option volume, buy volume / sell volume)
- What other variables would exhibit the attention effect responsible for high volume return premium? (e.g. returns, news, time of day)
- Can we combine this with other classification strategies? (e.g. industry classification)
- What about a different trading rule? (e.g. different weights, different holding times)

### Conclusion

This case study demonstrates a typical research process: sourcing ideas and testing ideas. We started by drawing ideas from the paper. We then tested those ideas (using Trexsim) and iterated upon it to get a profitable signal.

We want to emphasize that method matters most. A productive research system consists of a consistent stream of ideas, a pipeline of organized, promising ideas, and a thorough filter for testing these ideas. This is especially important for new researchers.

After this tutorial, we recommend reading a few papers and trying out some of the ideas by yourself in Trexsim.

---

## Alpha Metrics

In this section, we will discuss the definitions of the performance metrics that are displayed in the alpha simulation plot. Initially, the abundance of numbers may seem overwhelming and difficult to comprehend. However, it is crucial to meticulously examine each number and attempt to comprehend its intended measurement. The following table provides a list of abbreviations and their corresponding metric names and descriptions.

| Abbr | Name | Description |
|------|------|-------------|
| `ir` | Information Ratio | mean(daily return) / std(daily return), ratio of mean returns to the volatility of those returns |
| `ret` | Annualized Return | cumulative_pnl / ((longbook + shortbook)/2) * (252/simulation_days) |
| `tvr` | Turnover | It is the ratio of mean(dollars_traded) to (longbook + shortbook)/2. |
| `dd` | Drawdown | ([peak to trough of highest cumulative pnl to subsequent lowest cumulative pnl]) / ((longbook + shortbook)/2) |
| `ir/sqrt(tvr)` | IR/sqrt(TVR) | It is the Information Ratio divided by the square root of the Turnover. |
| `liq` | Liquidity | It is the capital that may be allocated to the alpha while still resulting in minimal market impact. The liquidity value is not absolute but should be used as a relative gauge of how liquid alphas are with respect to each other. |
| `liqn` | Liquidity (New) | It is another measure of liquidity. It is the book size at which the average daily stock volume traded by the alpha is 1% of the total volume traded in the market. |
| `bk` | Booksize | It is the long x short size of the alpha in millions of dollars. |
| `stk` | Number of Stocks | It is the number of stocks with long positions and the number of stocks with short positions. The stk number displayed on the plot is an average of the last 120 trading days. |
| `fast` | Simulation Mode | Trexsim has two simulation modes - fast, which is an approximation but quick to simulate, and slow, which is the true simulation where the alpha is calculated one day at a time. Alphas can only be submitted to production after simulating in slow mode. |

---

## Simulation Modes — Fast and Slow

Trexsim has two simulation modes: Fast and Slow. In this section, we will explain the reasons for having both modes and provide guidance on when to use each mode.

### Fast mode

Fast mode simulates the entire history of the alpha in one shot. This mode is less accurate than the Slow mode, but is quicker to compute. Researchers use the Fast mode to test their ideas quickly.

### Slow mode

Slow mode simulates one day at a time with a given lookback. This mode runs a loop over the dates axis, computing the positions for day `i` by only running the alpha code on days `i - lookback` to `i`. Slow mode is used to generate a chunk of data matrix at once.

**Alphas can only be submitted through Slow mode.**

### What causes differences in fast and slow modes?

Often researchers find that the simulations in Fast and Slow mode are substantially different from each other. Differences between the fast and slow mode simulations can be caused by several factors. Below we discuss some of the most common ones - insufficient lookback, forward bias and corporate adjustments.

#### Insufficient lookback

It is important to give sufficient lookback for Slow mode simulations. The lookback should be enough so that your operator can find the last day's alpha value correctly. Giving insufficient lookback can cause the alpha to be incorrectly computed or give an invalid result, as shown in the example below. Here the expression `alpha = ts_mean(-ret1, 30)` requires at least 31 days of lookback to compute correctly but is given only 5 days, resulting in an invalid output.

> [Figure: Alpha Editor with `alpha = ts_mean(ret1, 30)` run in Slow mode with lookback of 5. All performance metrics read N/A (IR N/A, TVR N/A, DD 0.0, Ret N/A, Booksize x, NumStks 0x0, Liq 0, LiqN N/A). The PnL plot is empty/flat.]

#### Forward bias

Fast mode has access to future data which can leak into the past, rendering the simulation unrealistic. We call this effect Forward Bias or Future Bias. The most extreme example of forward bias is looking at the next day's returns to make your bet. Obviously, this will not work in Slow mode. Expression: `ts_delay(close, -1)`. Delay is -1 or "look forward 1 day".

> [Figure: Side-by-side comparison of `ts_delay(close, -1)`. In Fast mode the PnL climbs smoothly upward (an unrealistically perfect result); in Slow mode the PnL is flat/broken because future data is not available day-to-day.]

While the above example is for illustrative purposes, in reality Forward bias can be hard to catch. Bias can be introduced due to corporate adjustments such as stock splits and dividends (see next subsection).

#### Corporate Adjustments

Adjustments for corporate actions like stock splits, reverse splits and dividend payments are applied retrospectively. The adjustment procedure introduces a bias because stocks that undergo splits are more likely to be those that have increased in price. For example, consider `alpha = -close`.

The Fast mode performance and the Slow mode performance will be different due to the price and volume adjustments that are applied retrospectively. Making alphas dimensionless quantities reduces the difference between Fast and Slow mode that arises due to adjustments.

> [Figure: Side-by-side Fast vs. Slow comparison for `alpha = -close`, showing differing PnL curves due to retrospective corporate-action adjustments.]

---

## Viewing and Managing Alphas

All simulated alphas can be seen on the alpha list page. You can filter using the "Filter" options at the top of the page. We also recommend you keep track of your favorite simulations in a personal google sheet. Here you can keep the link to the alpha, the alpha expression, and the hypothesis behind it. This will allow you to quickly find those well performing simulations.

### Calculating Correlations

Trexsim also allows you to calculate correlations between simulated alphas. For example, the figure below shows the correlation between three reversion alphas. To calculate the correlation, select the required alphas using the check box on the left, and select compute correlation at the bottom action bar.

> [Figure: Action bar showing "3 alpha(s) selected", with "Remove Alphas" and "Compute Correlation" buttons.]

> [Figure: Alpha Metrics table and correlation matrix for three reversion alphas (-ret1, -ret5, -ret20).
> Alpha metrics — id 48 (-ret1): IR 0.025, Ret 0.044, TVR 1.442, DD 48.4, IR/TVR 0.021, CS 0.00; id 49 (-ret5): IR 0.043, Ret 0.090, TVR 0.635, DD 48.5, IR/TVR 0.053, CS 0.00; id 50 (-ret20): IR 0.026, Ret 0.056, TVR 0.313, DD 41.6, IR/TVR 0.047, CS 0.00. All: Region us, Universe top1000, Neut industry, L BK 1.0.
> Correlation matrix (20200108–20211230): -ret1↔-ret5 = 0.65, -ret1↔-ret20 = 0.46, -ret5↔-ret20 = 0.77 (diagonal = 1.00).]

---

## Common Errors in Alpha Development

Here is a list of things to keep in mind while developing alphas:

- **`0` value does not mean no position in a stock**, since the median value will be subtracted from all the values in the alpha matrix. This could lead to long/short positions in stocks which initially had zero position. Use `np.nan` if you don't want a position in a stock.
- **Use `np.nan` based functions** like `np.nanmean`, `np.nansum`, etc. Normal operations like `np.mean` will give you NaN values if `np.nan` is present in your alpha. The built-in operators already take care of this.
- **Be consistent with the units and scale of values.** Adding terms of different units and scale would lead to results which are uninterpretable.
- **Be careful with corporate adjustments.** Making alpha expressions dimensionless can mitigate the effect of corporate adjustments, since adjustments generally affect data variables with units of dollars per share or number of shares.
- **Be careful when adding alphas.** Use `at_nan2zero` while adding alphas together to ensure that the stock position for the combined signal does not become NaN when one of the alphas has a NaN position. If you want the final alpha to have NaN where no stock has a position, you can call `at_zero2nan` at the end. For example:

```python
alpha = at_zero2nan(at_nan2zero(alpha1) + at_nan2zero(alpha2))
```