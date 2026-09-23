# Hypotheses

The CELA research method is guided by the following core hypotheses, subject to empirical evaluation within the CAPTAIN platform:

## H1: Granularity and Selectivity (Primary)
**Channel-level intervention provides more selective causal localization than source-event-level intervention.**
*Operationalization*: Measured by comparing the preserved evidence count and collateral modification rate when applying ARTIFACT_REPLACEMENT (channel) versus TOOL_RESULT_OVERRIDE (source-event) interventions.

## H2: Causal Differentiation (Supporting)
**CELA's evidence-flow attribution framework can correctly distinguish causal from non-causal evidence channels.**
*Operationalization*: Evaluated across controlled benchmark scenarios with known ground truth, analyzing whether the method successfully isolates the channels responsible for failures from benign or distractor channels.

## H3: Evidence Dependence (Sanity)
**A real LLM's output genuinely depends on the content of its evidence.**
*Operationalization*: A basic premise validation showing that intervening on specific evidence inputs to a real LLM (e.g., Gemini 3.6-flash) changes its output in expected ways, validating the underlying mechanism of CELA.

---

### Note on CEE
The primary causal estimand used to evaluate these hypotheses is the **Counterfactual Evidence-Flow Effect (CEE)**:
`CEE(e) = P(Y=1) - P(Y=1 | do(C_e = empty))`

**Important Limitation**: CEE is an *operationalization* of standard causal intervention (do-calculus) applied to the evidence-channel domain. It is NOT claimed to be a fundamentally novel mathematical causal estimand.
