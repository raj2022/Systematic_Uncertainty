"""
synthetic_ablation_texts.py

Hand-written synthetic methodology paragraphs for Phase 3's ablation
test. One shared BASE paragraph describes a generic backtest with none
of the five checklist disclosures. Five VARIANTS each add exactly one
disclosure to the base text, with everything else held identical --
this isolates whether a detector responds to the specific content
change, not to paragraph length, vocabulary richness, or writing style
in general.

These are synthetic (written for this test, not real paper excerpts)
by design -- a clean, fully-controlled complement to the real-paper
ablation done separately on gold-set text. See notes/007.
"""

BASE = """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. The model is a gradient-boosted tree ensemble
trained on 40 technical and fundamental features. We split the dataset
into a training set (2015-2021) and a test set (2022-2023), and report
the model's directional accuracy and Sharpe ratio on the test set. The
model achieves 58% directional accuracy and an annualized Sharpe ratio
of 1.3 on the held-out test period. We compare performance against a
buy-and-hold benchmark and find the model outperforms on a risk-adjusted
basis. Feature importance analysis shows momentum and volume-based
features contribute most to predictive performance.
"""

VARIANTS = {
    "walk_forward_validation": """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. The model is a gradient-boosted tree ensemble
trained on 40 technical and fundamental features. We use a walk-forward
validation scheme: the model is retrained every quarter on an expanding
window of past data and evaluated on the following quarter, repeating
this process through the full 2022-2023 test period. We report the
model's directional accuracy and Sharpe ratio on the held-out test
period. The model achieves 58% directional accuracy and an annualized
Sharpe ratio of 1.3 on the held-out test period. We compare performance
against a buy-and-hold benchmark and find the model outperforms on a
risk-adjusted basis. Feature importance analysis shows momentum and
volume-based features contribute most to predictive performance.
""",

    "purged_embargoed_cv": """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. The model is a gradient-boosted tree ensemble
trained on 40 technical and fundamental features. We split the dataset
into a training set (2015-2021) and a test set (2022-2023), with a
two-week embargo period separating the end of training data from the
start of test data to prevent information leakage from overlapping
feature windows. We report the model's directional accuracy and Sharpe
ratio on the test set. The model achieves 58% directional accuracy and
an annualized Sharpe ratio of 1.3 on the held-out test period. We
compare performance against a buy-and-hold benchmark and find the model
outperforms on a risk-adjusted basis. Feature importance analysis shows
momentum and volume-based features contribute most to predictive
performance.
""",

    "out_of_sample_cost_modeling": """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. The model is a gradient-boosted tree ensemble
trained on 40 technical and fundamental features. We split the dataset
into a training set (2015-2021) and a test set (2022-2023), and report
the model's directional accuracy and Sharpe ratio on the test set,
net of an assumed 5 basis point round-trip transaction cost applied to
every simulated trade. The model achieves 58% directional accuracy and
an annualized Sharpe ratio of 1.3 on the held-out test period after
costs. We compare performance against a buy-and-hold benchmark and find
the model outperforms on a risk-adjusted basis. Feature importance
analysis shows momentum and volume-based features contribute most to
predictive performance.
""",

    "multiple_testing_correction": """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. We evaluate 12 candidate model architectures
and feature set combinations, and apply a Bonferroni correction to
adjust the significance threshold for the resulting multiple
comparisons before selecting the best-performing configuration. The
selected model is a gradient-boosted tree ensemble trained on 40
technical and fundamental features. We split the dataset into a
training set (2015-2021) and a test set (2022-2023), and report the
model's directional accuracy and Sharpe ratio on the test set. The
model achieves 58% directional accuracy and an annualized Sharpe ratio
of 1.3 on the held-out test period. We compare performance against a
buy-and-hold benchmark and find the model outperforms on a
risk-adjusted basis. Feature importance analysis shows momentum and
volume-based features contribute most to predictive performance.
""",

    "multi_window_validation": """
We develop a machine learning model to predict next-day returns for a
universe of 50 large-cap U.S. equities using daily price and volume
data from 2015 to 2023. The model is a gradient-boosted tree ensemble
trained on 40 technical and fundamental features. We split the dataset
into a training set (2015-2021) and evaluate the model separately on
three distinct out-of-sample test periods: 2022 (a high-volatility
regime), the first half of 2023 (a recovery regime), and the second
half of 2023 (a low-volatility regime), reporting results for each
period individually. The model achieves 58% average directional
accuracy and an average annualized Sharpe ratio of 1.3 across the
three held-out periods. We compare performance against a buy-and-hold
benchmark and find the model outperforms on a risk-adjusted basis in
all three periods. Feature importance analysis shows momentum and
volume-based features contribute most to predictive performance.
""",
}
