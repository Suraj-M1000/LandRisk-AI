# LandRisk AI — Problem Specification

## 1. Problem

LandRisk AI is a personal portfolio and learning project inspired by SIH 2026 problem statement **SIH26017 — Predictive Analytics System for Early Detection of Land Acquisition Delays**.

The goal is to build an intelligent decision-support system that can identify land-acquisition projects that may be at risk of significant delay based on information available during the project's progress.

The system is intended to demonstrate an end-to-end Machine Learning application rather than serve as a production government decision-making system.

---

## 2. ML Objective

Can we learn the relationship between the current project condition and whether the project is likely to experience significant delay?

The first version of the system will treat delay prediction as a **binary classification problem**.

The model will estimate:

> **Given the information available about a project at a particular stage, is the project likely to experience significant delay?**

The model will produce a probability of delay and a corresponding risk category.

Example:

```text
Delay probability: 0.82
Risk score: 82/100
Risk level: High
```

---

## 3. Target Variable

The initial target will be:

```text
delayed
```

with:

```text
0 = No significant delay
1 = Significant delay
```

The initial working definition is:

```text
delayed = 1
if delay_days > 20% of planned_duration
```

The 20% threshold is a **provisional project decision**, not an official SIH definition. It may be changed if investigation of the available data suggests a more defensible definition. Any change will be recorded in `DECISIONS.md`.

---

## 4. Unit of Observation

The primary unit of observation will be a **project-stage snapshot**.

Each project may have three snapshots:

```text
Early stage
Mid stage
Late stage
```

For example:

```text
Project A
├── Early snapshot
├── Mid snapshot
└── Late snapshot
```

A snapshot represents the information that would have been available at that particular point in the project's lifecycle.

The purpose of this design is to model an **early-warning problem**, rather than simply predicting an outcome after most of the relevant events have already occurred.

---

## 5. Three Project Stages

The initial project design uses:

- **Early** — information available during the early phase of land acquisition.
- **Mid** — information available after the project has progressed further.
- **Late** — information available during the later stage before final completion.

The exact timing and definition of these stages will depend on the available dataset. They must be defined consistently before modelling.

---

## 6. Feature Timing Rule

A feature may only be used if that information would have been available **at or before the snapshot time**.

For example, if a prediction is made at the mid-stage:

```text
Allowed:
Information known by mid-stage
```

```text
Not allowed:
Information that became known after mid-stage
```

The final project outcome may be used to create the training label, but it must not be used as an input feature.

---

## 7. Leakage Rules

The following information must not leak into the model:

### Future information

A feature must not contain information that became available after the prediction snapshot.

### Final outcome information

The actual final delay, completion date, or other final outcome must not be used as an input feature when predicting that outcome.

### Historical delay rate

`historical_delay_rate` must only use information from **other projects that were already completed before the relevant prediction time**.

The current project's future outcome must never contribute to its own historical rate.

### Project-level train/test leakage

Snapshots from the same project must never be split between training and testing sets.

Therefore:

```text
Project A → Train
Project B → Train
Project C → Test
```

is valid, while:

```text
Project A Early → Train
Project A Mid   → Test
```

is not valid.

The train/test split will therefore be performed **by project**, not by individual snapshot row.

---

## 8. Initial Models

The first modelling stage will compare:

1. Logistic Regression — baseline
2. Decision Tree
3. Random Forest
4. Gradient Boosting

The purpose is to understand model behaviour and compare approaches rather than assuming that the most complex model is automatically the best.

---

## 9. Evaluation

For the classification task, the primary evaluation metrics will include:

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC
- Confusion Matrix

Recall will receive particular attention because the system is intended as an early-warning tool where missing a genuinely delayed project can be important.

A future regression extension may estimate the number of delay days and will then use:

- MAE
- MSE
- RMSE
- R² Score

---

## 10. Explainability

The system should provide an explanation for each prediction.

The initial implementation will use interpretable Logistic Regression contributions and feature importance.

SHAP-based explanations may be added later if they provide useful additional value.

The intended output is:

```text
Prediction
Delay probability
Risk category
Top contributing factors
Suggested actions
```

---

## 11. Data Strategy

Real-world data will be investigated first.

The project will not assume that a suitable labelled dataset exists simply because the problem statement is based on a real-world problem.

The data strategy is:

```text
Investigate suitable real-world data
        ↓
Use it if sufficiently suitable and legally usable
        ↓
Otherwise investigate proxy/derived data
        ↓
If no suitable option exists
        ↓
Use clearly documented synthetic data
```

Synthetic data, if required, will be used to demonstrate the ML engineering pipeline and will not be presented as evidence of real-world predictive accuracy.

---

## 12. Project Scope

LandRisk AI is a personal portfolio and learning project.

It is not intended to:

- make official government decisions;
- replace domain experts;
- provide legally binding recommendations;
- claim validated real-world prediction accuracy without suitable real-world data.

The project focuses on demonstrating the complete workflow:

```text
Problem
→ Data
→ Preprocessing
→ EDA
→ Feature Engineering
→ ML
→ Evaluation
→ Explainability
→ Django
→ Database
→ Dashboard
```