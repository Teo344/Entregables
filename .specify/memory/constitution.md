<!-- Sync Impact Report
Version change: 1.1.0 to 1.2.0
Modified principles: II. Data Integrity and Responsible Use; III. Reproducible Experiments; IV. Evidence-Based Model Evaluation; V. Maintainable and Reviewable Changes
Added sections: offline operation, Android target, held-out test split, expanded evaluation measures, and bounded offline assistant behavior
Removed sections: none
Templates requiring review: spec, plan, and task templates should carry the offline requirement, dataset provenance and split rules, evaluation measures, and heatmap/assistant limits into feature artifacts.
Follow-up TODOs: Confirm the constitution's original ratification date; define the metric and protocol for the proposed 90-95% target; verify the label mapping of each external dataset before assigning thesis classes; define the accepted assistant knowledge base and predefined guidance.
-->
# AvocadoIA Constitution

## Core Principles

### I. Research Traceability
Every dataset, preprocessing step, model configuration, and reported result MUST be traceable to its source and recorded parameters. Project documentation MUST distinguish measured results from assumptions and proposed targets. This keeps thesis conclusions auditable and reproducible.

### II. Data Integrity and Responsible Use
Raw datasets MUST be preserved unchanged. Derived data MUST be reproducible from documented transformations. Each source's provenance, license, usage conditions, assigned labels, and label-mapping rationale MUST be recorded before its images are used in experiments or redistributed. Images from public repositories and project collection MUST NOT be assigned to a thesis class solely by filename or an unverified assumption. Dataset-specific restrictions and participant permissions MUST be respected.

### III. Reproducible Experiments
Training, validation, and test data MUST have documented, reproducible membership. Test data MUST remain separate from training and model selection. Experiments MUST record preprocessing, model settings, random seeds when applicable, software dependencies, and evaluation procedures. Data augmentation MUST NOT create leakage between the underlying source images assigned to different splits. Changes that can affect results MUST be documented alongside their evidence.

### IV. Evidence-Based Model Evaluation
MobileNetV3 and EfficientNet-B0 MUST be compared under documented, comparable conditions. Reports MUST include accuracy, per-class and macro-averaged precision, recall and F1-score, a confusion matrix, and multiclass ROC-AUC using a documented one-vs-rest macro strategy. Evaluation MUST also address calibration, generalization, and computational efficiency for the Android target. Calibration measures and any applied calibration method MUST be documented with their limitations. The selected architecture MUST be justified by measured results rather than assumed in advance. Quantitative acceptance thresholds MUST identify the metric, dataset, and evaluation protocol; an unspecified 90-95% target MUST NOT be treated as an established pass criterion.

### V. Maintainable and Reviewable Changes
Code and configuration changes MUST have a clear purpose, use the simplest implementation that meets the project need, and be documented sufficiently for another contributor to reproduce the workflow. Changes to data processing, labels, model behavior, exported model, or mobile integration MUST include an appropriate verification method and its observed outcome. Unperformed checks MUST NOT be reported as passing.

## Additional Constraints

The project comprises model development in `Modelo/` followed by integration into the Android application in `AvocadoIA.V2/`. The model and application MUST use consistent class names, preprocessing, and documented interfaces. The classification scope is limited to healthy avocado fruit, anthracnose, and symptoms compatible with peduncle ring rot (anillado del pedúnculo). The application MUST present image-based model predictions as support for monitoring, not as definitive phytosanitary diagnoses, and MUST NOT imply coverage of conditions outside the validated data.

The application MUST provide its core functions without an internet connection, including image classification, result presentation, Grad-CAM++ visualization, history, and the assistant. A network connection MUST NOT be a prerequisite for these functions. The implementation technology and model export format MUST be selected and justified during planning based on the target Android device; this constitution does not prescribe TensorFlow Lite, ONNX, or a particular mobile framework.

Evaluation data MUST be split into training, validation, and a held-out test/acceptance set, with membership and rationale recorded. The test set MUST NOT be used to tune or select models. Images derived from the same original specimen or capture session MUST be grouped consistently where needed to prevent leakage. Any external dataset label mapping to the three project classes MUST be verified and documented before use; an existing label such as `Scab` MUST NOT be assumed to mean anillado del pedúnculo without supporting evidence.

Grad-CAM++ MUST be presented as a visualization of image regions associated with a model output. It MAY help users inspect which region influenced a prediction, but MUST NOT be described as proof of causality, disease presence, diagnostic correctness, or improved classification precision. The application MUST preserve the uncertainty and non-definitive nature of the prediction when showing a heatmap.

The assistant MUST work offline and MUST distinguish its informational output from the classifier's prediction. It MUST describe visible symptoms and offer only predefined, reviewed general guidance from the project's approved local knowledge base. It MUST communicate when that material does not support an answer and MUST NOT invent treatment advice or present its output as an authoritative diagnosis or phytosanitary recommendation. The approved content and safeguards MUST be documented before implementation.

## Development Workflow

Work that changes experimental results MUST record the affected data or model workflow and the evidence used to verify the change. Reviews MUST check consistency between code, configuration, dataset labels and splits, recorded experiment details, mobile behavior, and any thesis claims affected by the change. Model reports MUST include per-class results, the selected aggregate metrics, calibration findings, computational measures, and limitations. Mobile inference performance MUST be measured on the target Android device when available; otherwise, the limitation MUST be stated. User testing MUST document its method and participant context. Verification results MUST be reported accurately.

## Governance

This constitution governs project work. Amendments MUST be reviewed by the project owner, documented in version control, and reflected in the constitution version and amendment date. A change that removes or redefines a principle requires a MAJOR version increment; a new principle or materially expanded requirement requires a MINOR increment; clarifications and non-semantic corrections require a PATCH increment. Version numbers use MAJOR.MINOR.PATCH.

Contributors MUST review changes for compliance with these principles. Any exception MUST be documented with its reason, scope, and duration, and approved by the project owner. Reviews of experimental work MUST verify traceability, data integrity, split integrity, and consistency of reported evidence.

**Version**: 1.2.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date unknown | **Last Amended**: 2026-10-20
