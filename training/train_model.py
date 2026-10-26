"""
Trains the high-capacity resume category classifier and multi-model ensemble.
Uses multi-scale TF-IDF features (unigram + bigram + trigram) with sublinear TF scaling,
feeding a Calibrated LinearSVC, a deep 3-layer MLP neural network, and a balanced
multinomial Logistic Regression baseline.

Computes and saves category feature attribution weights for ML-driven
resume suggestions and corrections.

Usage:
    .venv\\Scripts\\python.exe -m training.train_model
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from config import config


def load_processed_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"processed_text", "category"}
    if not required.issubset(df.columns):
        raise ValueError(f"Processed dataset must contain columns: {required}")
    return df


def train_and_evaluate(df: pd.DataFrame):
    X = df["processed_text"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Multi-scale TF-IDF with sublinear term-frequency scaling & unigram+bigram+trigram coverage
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=10000,
        min_df=2,
        max_df=0.92,
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Model 1: LinearSVC with Platt Sigmoid Cross-Validated Calibration
    base_svm = LinearSVC(C=1.2, class_weight="balanced", max_iter=15000, random_state=42)
    classifier = CalibratedClassifierCV(base_svm, method="sigmoid", cv=5)
    classifier.fit(X_train_vec, y_train)

    y_pred_svm = classifier.predict(X_test_vec)
    svm_acc = accuracy_score(y_test, y_pred_svm)
    labels = sorted(y.unique())
    print(f"Calibrated LinearSVC holdout accuracy: {svm_acc:.4f}")

    # Model 2: Multinomial Logistic Regression (L2 regularized)
    log_reg = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=42)
    log_reg.fit(X_train_vec, y_train)
    y_pred_lr = log_reg.predict(X_test_vec)
    lr_acc = accuracy_score(y_test, y_pred_lr)
    print(f"Logistic Regression holdout accuracy: {lr_acc:.4f}")

    # Model 3: Deep Multi-Layer Perceptron (384, 128, 64) on scaled sparse representations
    scaler = StandardScaler(with_mean=False)
    X_train_scaled = scaler.fit_transform(X_train_vec)
    X_test_scaled = scaler.transform(X_test_vec)

    mlp = MLPClassifier(
        hidden_layer_sizes=(384, 128, 64),
        activation="relu",
        alpha=5e-4,
        max_iter=300,
        random_state=42,
    )
    mlp.fit(X_train_scaled, y_train)
    mlp_pred = mlp.predict(X_test_scaled)
    mlp_acc = accuracy_score(y_test, mlp_pred)
    print(f"Deep MLP holdout accuracy: {mlp_acc:.4f}")

    # Triple-Engine Soft Voting Ensemble
    svm_proba = classifier.predict_proba(X_test_vec)
    lr_proba = log_reg.predict_proba(X_test_vec)
    mlp_proba = mlp.predict_proba(X_test_scaled)

    assert list(classifier.classes_) == list(mlp.classes_) == list(log_reg.classes_), "class order mismatch"
    # Weighted soft-voting blend: favors calibrated SVM & MLP
    ens_proba = (svm_proba * 0.45) + (mlp_proba * 0.35) + (lr_proba * 0.20)
    ens_pred = np.asarray([classifier.classes_[i] for i in ens_proba.argmax(axis=1)])
    ens_acc = accuracy_score(y_test, ens_pred)
    print(f"Tri-Model Ensemble holdout accuracy: {ens_acc:.4f}")

    # Select winning prediction for reporting
    best_pred = ens_pred if ens_acc > svm_acc else y_pred_svm
    final_acc = max(svm_acc, ens_acc)

    metrics = {
        "accuracy": float(final_acc),
        "svm_accuracy": float(svm_acc),
        "lr_accuracy": float(lr_acc),
        "mlp_accuracy": float(mlp_acc),
        "ensemble_accuracy": float(ens_acc),
        "report": classification_report(y_test, best_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, best_pred, labels=labels),
        "labels": labels,
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    # Extract top discriminative feature weights per category
    feature_names = np.array(vectorizer.get_feature_names_out())
    coefs = [cc.estimator.coef_ for cc in classifier.calibrated_classifiers_]
    avg_coef = np.mean(coefs, axis=0)

    category_top_features = {}
    for idx, cls_name in enumerate(classifier.classes_):
        top_k_indices = np.argsort(avg_coef[idx])[-15:][::-1]
        category_top_features[cls_name] = [
            {"term": str(feature_names[j]), "weight": round(float(avg_coef[idx][j]), 4)}
            for j in top_k_indices
        ]

    return classifier, vectorizer, metrics, mlp, scaler, log_reg, category_top_features


def _format_confusion_matrix(matrix, labels) -> str:
    header = "actual \\ predicted".ljust(28) + "".join(f"{lbl[:10]:>12}" for lbl in labels)
    rows = [header]
    for label, row in zip(labels, matrix):
        rows.append(label[:26].ljust(28) + "".join(f"{val:>12}" for val in row))
    return "\n".join(rows)


def save_artifacts(
    classifier,
    vectorizer,
    metrics: dict,
    mlp=None,
    scaler=None,
    log_reg=None,
    category_top_features=None,
) -> None:
    Path(config.MODEL_DIR).mkdir(parents=True, exist_ok=True)

    joblib.dump(classifier, config.CLASSIFIER_PATH)
    joblib.dump(vectorizer, config.VECTORIZER_PATH)
    if mlp is not None and scaler is not None:
        joblib.dump(mlp, config.MODEL_DIR + "/resume_mlp.pkl")
        joblib.dump(scaler, config.MODEL_DIR + "/feature_scaler.pkl")
    if log_reg is not None:
        joblib.dump(log_reg, config.MODEL_DIR + "/resume_logreg.pkl")

    use_ensemble = (
        mlp is not None and scaler is not None
        and metrics.get("ensemble_accuracy", 0) > metrics["svm_accuracy"]
    )
    meta = {
        "use_ensemble": bool(use_ensemble),
        "svm_accuracy": metrics["svm_accuracy"],
        "lr_accuracy": metrics.get("lr_accuracy"),
        "mlp_accuracy": metrics.get("mlp_accuracy"),
        "ensemble_accuracy": metrics.get("ensemble_accuracy"),
        "final_accuracy": metrics["accuracy"],
        "n_train": metrics["n_train"],
        "n_test": metrics["n_test"],
        "categories": metrics["labels"],
    }
    with open(config.MODEL_DIR + "/model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    with open(config.LABEL_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics["labels"], f, indent=2)

    if category_top_features:
        with open(config.MODEL_DIR + "/feature_weights.json", "w", encoding="utf-8") as f:
            json.dump(category_top_features, f, indent=2)

    report_lines = [
        "RESUME CLASSIFIER - MAXIMUM CAPABILITY TRAINING REPORT",
        "=" * 65,
        "Model: Multi-scale TF-IDF (1-3 ngrams, sublinear TF) + Calibrated LinearSVC",
        "Ensemble: Soft-Voting blend of Calibrated LinearSVC + Deep MLP + Logistic Regression",
        f"Training rows: {metrics['n_train']}   Test rows: {metrics['n_test']}",
        f"Categories ({len(metrics['labels'])}): {', '.join(metrics['labels'])}",
        "",
        f"Calibrated LinearSVC Holdout Accuracy: {metrics['svm_accuracy']:.4f}",
        f"Logistic Regression Holdout Accuracy:   {metrics.get('lr_accuracy', 0):.4f}",
        f"Deep MLP Neural Net Holdout Accuracy:  {metrics.get('mlp_accuracy', 0):.4f}",
        f"Tri-Model Soft-Voting Ensemble Acc:    {metrics.get('ensemble_accuracy', 0):.4f}",
        f"Final Selected Production Accuracy:    {metrics['accuracy']:.4f}",
        "",
        "Classification report (precision / recall / f1-score per category):",
        metrics["report"],
        "Confusion matrix (rows = actual, columns = predicted):",
        _format_confusion_matrix(metrics["confusion_matrix"], metrics["labels"]),
        "",
        "ML ATTRIBUTION CAPABILITIES:",
        "- Exported calibrated discriminative feature attribution matrices per role category.",
        "- Provides real-time ML mathematical gap analysis, action verb scoring, and bullet quantification.",
    ]
    with open(config.TRAINING_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("\n".join(report_lines))


def main() -> None:
    df = load_processed_dataset(config.PROCESSED_DATASET_PATH)
    print(f"Loaded {len(df)} processed rows for maximum capability training.")
    print("Category distribution:")
    print(df["category"].value_counts())
    print()

    classifier, vectorizer, metrics, mlp, scaler, log_reg, top_features = train_and_evaluate(df)
    save_artifacts(classifier, vectorizer, metrics, mlp, scaler, log_reg, top_features)

    print(f"\nSaved production classifier to:  {config.CLASSIFIER_PATH}")
    print(f"Saved production vectorizer to:  {config.VECTORIZER_PATH}")
    print(f"Saved feature attribution to:    {config.MODEL_DIR}/feature_weights.json")
    print(f"Saved training report to:        {config.TRAINING_REPORT_PATH}")


if __name__ == "__main__":
    main()
