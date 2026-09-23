# 20: Benchmarks

The CAPTAIN/CELA benchmark suite contains 11 families evaluating distinct causal reasoning mechanisms. The total number of controlled instances is 275 (11 families × 5 seeds × 5 instances).

## Benchmark Families

| Family | Mechanism | Topology | Ground Truth |
|--------|-----------|----------|--------------|
| BF-A | Single channel | Single cause + distractor | Single causal artifact |
| BF-B | Redundant OR | Both cause failure independently | All failure-producing tools |
| BF-C | Complementary AND | Both required for failure | Any interacting tool |
| BF-D | Distractor | One cause + two distractors | The failing tool |
| BF-E | Cascade | Multi-hop propagation | Originating step |
| BF-F | Cost-asymmetric | AND logic with budget constraint | Both failing tools |
| BF-G | Shared source | Multi-artifact from single tool | Specific failing channel |
| BF-H | Convergent mixed | Mixed causal+benign inputs | Delayed failing input |
| BF-I | Convergent | Single causal among converging paths | The causal input |
| BF-J | Parallel sources | Independent causal sources | Parallel sources |
| BF-K | Downstream persistence| Ineffective repair attempt | Original failure |

### Known Issues and Clarifications

- **BF-H (Temporal Delay)**: Initially labeled as `BRANCHING`, the actual topology is convergent with mixed inputs.
- **BF-J (Circular)**: Initially labeled as `ROOT_VS_SYMPTOM`, the implementation actually tests parallel independent sources rather than a true root-vs-symptom cycle.
- **BF-K (Downstream Repair)**: Initially labeled as `DOWNSTREAM_REPAIR`, the actual implementation tests downstream persistence since the repair tool is ineffective and structurally inert.

## CausalMechanismSpec Structure

The scenarios are defined via a structured specification that explicitly captures:
- Origin of the failure
- Propagation mechanism
- Actuator/point of failure
- Evaluator behavior and prevention sets
