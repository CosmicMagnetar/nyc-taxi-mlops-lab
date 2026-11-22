# S5 recall check: my answers

**1. SLI, SLO, SLA**
- SLI: a measured number about the service. Example: the share of `/predict` requests answered in 250ms or less.
- SLO: the target I set for that number. Example: 95% of requests under 250ms over 30 days, and 99.5% of requests not 5xx.
- SLA: a promise to a customer with a consequence if I miss it. This app has none, because nobody pays for it. How strict an SLO is depends on how important the data and the app are: a stricter target means less downtime allowed, so recovery must be faster and costs more. I chose values in between that fit a taxi quote app.

**2. Why a histogram and a percentile for latency, not an average**
An average hides the slow tail: if 95 requests take 50ms and 5 take 2 seconds, the average looks fine but 1 rider in 20 waits 2 seconds. A histogram counts requests per latency bucket, so I can say "95% were under 250ms" exactly (250ms is a bucket edge in the contract). Histograms also add up across instances, which averages and percentiles do not.

**3. What makes a Prometheus series new, and two labels that blow up the count**
A series is one unique combination of a metric name and its label values, so any new label value creates a new series. Two labels that would blow it up: the raw request path (ids or query strings in it) and a user id or any user input. In this lab, `image` and the container `id` did it too, because they change on every deploy, so I dropped them in `budget.alloy`. The result: 242 series before three extra deploys and 277 after, against a budget of 10,000.

**4. Burn rate, and why page on a fast burn over two windows**
Burn rate is how fast I use up the error budget compared with the pace that would use it exactly by the end of the window. 1x means the budget is gone at the end of the month; 14.4x means gone in about 2 days. Paging on any single error would wake me for blips the budget absorbs easily. Two windows: the long one (1 hour) shows the problem is real and sustained, the short one (5 minutes) shows it is still happening, so the alert stops soon after the fix. In my drill, `ModelFallbackFastBurn` fired 5m22s after I stopped `serving-champion`.
