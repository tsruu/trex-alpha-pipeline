# Price / Volume  (16 vars)

**Status:** EXPLORED — all 101 alphas live here.
**Notes:** Use mainly to combine with another cluster, or as the base signal you transform (neutralize / condition / re-weight / re-horizon). Low lookahead risk.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `cashdvd` | the amount of cash dividend distributed to shareholders. | cross-sec | annual | `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `close` ⬤ | the adjusted closing price of stocks, which accounts for corporate actions su… | cross-sec | daily | corporate-action adjusted |
| `high` ⬤ | the adjusted high price of stocks, reflecting the highest price reached durin… | cross-sec | daily | corporate-action adjusted |
| `industry` ⬤ | an integer representation of industries, encompassing approximately 70 distin… | cross-sec | annual | `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `low` ⬤ | the adjusted low price of stocks, accounting for factors such as stock splits… | cross-sec | daily | corporate-action adjusted |
| `mktcap` ⬤ | the market capitalization of stocks, calculated by multiplying the stock's cu… | cross-sec | daily | `delay_0=0`: timing review; do not auto-delay |
| `open` ⬤ | the adjusted opening price of stocks, reflecting the price at which a stock b… | cross-sec | daily | corporate-action adjusted |
| `ret1` ⬤ | the 1-day return of a stock, calculated as the percentage change from the pre… | cross-sec | daily | derived |
| `ret10` ⬤ | the 10-day return, calculated as the percentage change in the stock's closing… | cross-sec | daily | derived |
| `ret20` ⬤ | the 20-day return, calculated as the percentage change in the stock's closing… | cross-sec | daily | derived |
| `ret5` ⬤ | the 5-day return of a stock, calculated as the percentage change between toda… | cross-sec | daily | derived |
| `sector` ⬤ | the integer representation of sectors as classified, encompassing approximate… | cross-sec | annual | `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `shsfloat` | the number of floating shares available for trading, expressed in millions. | cross-sec | monthly | `delay_0=0`: timing review; do not auto-delay; corporate-action adjusted |
| `shsout` | the total number of outstanding shares of a company, expressed in millions. | cross-sec | quarterly | `delay_0=0`: timing review; do not auto-delay; corporate-action adjusted |
| `subindustry` ⬤ | an integer representation of subindustries, categorizing companies into appro… | cross-sec | annual | `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `volume` ⬤ | the total composite trading volume, which includes all trading activity durin… | cross-sec | daily | corporate-action adjusted |
