# Cascade Analysis

To prevent failure propagation, interventions can be grouped into sets.

- **CascadeEstimator**: Estimates set-level CEE(S) by applying all interventions simultaneously in a joint paired replay.
- **GreedyCascadeSelector**: Uses marginal gain $D(e|S) = CEE(S \cup \{e\}) - CEE(S)$ to greedily build intervention sets.
- **Optimization**: Supports budget-constrained maximization or unconstrained utility maximization using the cost model $U(S) = CEE(S) - \lambda \cdot Cost(S)$.
- **Global Optimality**: Not guaranteed; it returns the best statistically supported set found within evaluation budgets.

See [cascade.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/analysis/cascade.py).
