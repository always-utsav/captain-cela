# Algorithms

## Graph Construction
- **Purpose**: Map `ExecutionRun` to `ExecutionGraph`.
- **Implementation**: [builder.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/graph/builder.py)

## Provenance Extraction
- **Purpose**: Identify PRODUCED/CONSUMED/DERIVED relationships.
- **Implementation**: [extractor.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/provenance/extractor.py)

## Candidate Channel Generation
- **Purpose**: Identify failure-relevant evidence-flow edges.
- **Implementation**: `captain/failures/analyzer.py`

## Channel Intervention
- **Purpose**: Map channel block to underlying event override while preserving parallel channels.
- **Implementation**: [estimator.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/analysis/estimator.py)

## Counterfactual Replay
- **Purpose**: Re-execute the agent using a specific Intervention.
- **Implementation**: [engine.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/replay/engine.py)

## CEE Estimation
- **Purpose**: Calculate CEE(e) = P(Y=1) - P(Y=1 | do(C_e = empty)) via paired factual/counterfactual trials.
- **Implementation**: [estimator.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/analysis/estimator.py)

## Greedy Cascade Selection
- **Purpose**: Identify a set of interventions S to maximize CEE(S) subject to cost budget.
- **Complexity**: O(|Candidates| * MaxSetSize) replays.
- **Implementation**: [cascade.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/analysis/cascade.py)

## Statistical Validation
- **Purpose**: Compute paired comparisons, bootstrap CIs, and Holm-Bonferroni corrections.
- **Implementation**: [statistics.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/experiments/statistics.py)
