<!-- Sync Impact Report
Version change: 1.0.0 → 1.1.0
Modified principles: IV. Evidence-Based Model Evaluation (specific architectures, evaluation dimensions, and interpretation limits)
Added sections: product scope, model explanation and calibration requirements, assistant safeguards, and cross-component interface consistency
Removed sections: none
Templates requiring review: feature spec, implementation plan, and task templates should reflect the three classes, model comparison, mobile integration, Grad-CAM++, calibration, and assistant scope.
Follow-up TODOs: Confirm the ratification date; select deployment format, target metrics, confidence thresholds, and approved sources for assistant responses during specification and planning.
-->
# AvocadoIA Constitution

## Core Principles

### I. Research Traceability
Every dataset, preprocessing step, model configuration, and reported result MUST be traceable to its source and recorded parameters. Claims in project documentation MUST distinguish measured results from assumptions. This keeps thesis conclusions auditable and reproducible.

### II. Data Integrity and Responsible Use
Raw datasets MUST be preserved unchanged. Derived data MUST be reproducible from documented transformations, and data sources, licenses, and applicable usage conditions MUST be recorded before redistribution or publication. This protects the evidence base and respects dataset provenance.

### III. Reproducible Experiments
Training and evaluation MUST record the dataset split, preprocessing, model settings, random seeds when applicable, software dependencies, and evaluation procedure. Changes that can affect results MUST be documented alongside the resulting metrics.

### IV. Evidence-Based Model Evaluation
Model quality MUST be assessed on data kept separate from training and tuning. Reports MUST identify the evaluation dataset and metrics, include relevant limitations, and avoid claims that exceed the evidence. When comparisons are made, methods and data conditions MUST be comparable. MobileNetV3 and EfficientNet-B0 MUST be compared under documented, comparable conditions. Evaluation MUST address classification performance, calibration, generalization, and computational efficiency; the selected architecture MUST be justified by measured results rather than assumed in advance.

### V. Maintainable and Reviewable Changes
Code and configuration changes MUST have a clear purpose, use the simplest implementation that meets the project need, and be documented sufficiently for another contributor to reproduce the workflow. Changes to data processing or model behavior MUST include an appropriate verification method and its observed outcome.

## Additional Constraints

The project comprises a mobile application in `AvocadoIA.V2/` and model development in `Modelo/`. Implementation choices MUST preserve the ability to identify the origin, labels, and transformation history of data used in experiments. Dataset-specific restrictions and the approved thesis methodology take precedence over convenience.

The classification scope MUST remain limited to three categories: healthy avocado fruit, anthracnose, and symptoms compatible with peduncle ring rot (anillado del pedúnculo). The application MUST present outputs as image-based model predictions, not definitive phytosanitary diagnoses. It MUST communicate uncertainty and MUST NOT imply detection of conditions outside the validated dataset.

The model comparison MUST include MobileNetV3 and EfficientNet-B0 using documented data splits and comparable evaluation conditions. The project MUST evaluate classification performance, calibration, generalization, and computational efficiency. Deployment format (including TensorFlow Lite or ONNX) MUST be selected and justified during planning based on target-device evidence; this constitution does not prescribe one format.

Grad-CAM++ MUST be treated as a visualization of image regions associated with the model output, not as proof of causal reasoning or diagnostic correctness. Calibration methods, including Temperature Scaling where appropriate, and calibration measures such as Expected Calibration Error MUST be documented and interpreted with their limitations.

The conversational assistant MUST distinguish model predictions from general educational information. Its responses MUST use reviewed project or agricultural sources, communicate uncertainty, and MUST NOT present unverified treatment instructions as authoritative advice. The sources and safeguards MUST be defined before implementation.

The application, exported model, and assistant MUST use consistent class names and documented interfaces. Changes to labels, preprocessing, model versions, confidence presentation, or explanation outputs MUST be reviewed across affected components.

## Development Workflow

Work that changes experimental results MUST record the affected data or model workflow and the evidence used to verify the change. Reviews MUST check consistency between code, configuration, recorded experiment details, and any thesis claims affected by the change. Model reports MUST include per-class results, the selected aggregate metrics, calibration findings, and limitations. Mobile inference performance MUST be measured on the target device when available; otherwise, the limitation MUST be stated. User testing MUST document its method and participant context. Verification results MUST be reported accurately; unperformed checks MUST NOT be described as passing.

## Governance

This constitution governs project work. Amendments MUST be reviewed by the project owner, documented in version control, and reflected in the constitution version and amendment date. A change that removes or redefines a principle requires a MAJOR version increment; a new principle or materially expanded requirement requires a MINOR increment; clarifications and non-semantic corrections require a PATCH increment. Version numbers use MAJOR.MINOR.PATCH.

Contributors MUST review changes for compliance with these principles. Any exception MUST be documented with its reason, scope, and duration, and approved by the project owner. Reviews of experimental work MUST verify traceability, data integrity, and consistency of reported evidence.

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date unknown | **Last Amended**: 2026-10-19
