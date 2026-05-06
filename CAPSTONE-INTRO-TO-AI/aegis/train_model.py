from pathlib import Path

import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, precision_score, recall_score, confusion_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.naive_bayes import MultinomialNB


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "aegis_kaggle_style_incident_dataset.csv"
MODEL_PATH = BASE_DIR / "incident_model.pkl"
VECTORIZER_PATH = BASE_DIR / "vectorizer.pkl"


def main():
    df = pd.read_csv(DATASET_PATH)

    required_columns = {"text", "incident_label"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing_list}")

    df = df[["text", "incident_label"]].dropna()
    df["text"] = df["text"].astype(str).str.strip()
    df["incident_label"] = df["incident_label"].astype(str).str.strip().str.lower()
    df = df[(df["text"] != "") & (df["incident_label"] != "")]

    X = df["text"]
    y = df["incident_label"]

    print("=" * 60)
    print("AEGIS: Incident Classification Model Training")
    print("=" * 60)
    print(f"Dataset size: {len(df)} samples")
    print(f"Classes: {sorted(y.unique())}")
    print(f"Class distribution:\n{y.value_counts().to_string()}\n")

    # --- STRATIFIED K-FOLD CROSS-VALIDATION ---
    print("Running 5-fold stratified cross-validation...\n")
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics = {"accuracy": [], "precision": [], "recall": []}
    all_y_true = []
    all_y_pred = []
    
    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), start=1):
        X_train_fold = X.iloc[train_idx]
        X_test_fold = X.iloc[test_idx]
        y_train_fold = y.iloc[train_idx]
        y_test_fold = y.iloc[test_idx]
        
        # TF-IDF vectorization
        vectorizer_fold = TfidfVectorizer(stop_words="english")
        X_train_tfidf = vectorizer_fold.fit_transform(X_train_fold)
        X_test_tfidf = vectorizer_fold.transform(X_test_fold)
        
        # Train model
        model_fold = MultinomialNB()
        model_fold.fit(X_train_tfidf, y_train_fold)
        
        # Evaluate
        y_pred_fold = model_fold.predict(X_test_tfidf)
        
        acc = accuracy_score(y_test_fold, y_pred_fold)
        prec = precision_score(y_test_fold, y_pred_fold, average="weighted", zero_division=0)
        rec = recall_score(y_test_fold, y_pred_fold, average="weighted", zero_division=0)
        
        fold_metrics["accuracy"].append(acc)
        fold_metrics["precision"].append(prec)
        fold_metrics["recall"].append(rec)
        
        all_y_true.extend(y_test_fold.tolist())
        all_y_pred.extend(y_pred_fold.tolist())
        
        print(f"Fold {fold}: Acc={acc:.4f} Prec={prec:.4f} Rec={rec:.4f}")
    
    # --- REPORT K-FOLD STATISTICS ---
    print("\n" + "=" * 60)
    print("K-FOLD CROSS-VALIDATION RESULTS (5-fold)")
    print("=" * 60)
    
    for metric in ["accuracy", "precision", "recall"]:
        scores = fold_metrics[metric]
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        print(f"{metric.capitalize():12s}: {mean_score:.4f} ± {std_score:.4f}")
    
    # --- FINAL TRAINING ON FULL DATASET ---
    print("\n" + "=" * 60)
    print("FINAL TRAINING ON FULL DATASET")
    print("=" * 60)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    vectorizer = TfidfVectorizer(stop_words="english")
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    model = MultinomialNB()
    model.fit(X_train_tfidf, y_train)

    y_pred = model.predict(X_test_tfidf)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"Test Set Accuracy:  {accuracy:.4f}")
    print(f"Test Set Precision: {precision:.4f}")
    print(f"Test Set Recall:    {recall:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # --- SAVE MODEL ARTIFACTS ---
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    print("\n" + "=" * 60)
    print("MODEL ARTIFACTS SAVED")
    print("=" * 60)
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Vectorizer saved to: {VECTORIZER_PATH}")
    
    # --- GENERATE CONFUSION MATRIX ---
    print("\nGenerating confusion matrix...")
    cm = confusion_matrix(y_test, y_pred, labels=sorted(model.classes_))
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=sorted(model.classes_),
        yticklabels=sorted(model.classes_),
        cbar_kws={"label": "Count"}
    )
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix: Incident Classification")
    plt.tight_layout()
    
    cm_path = Path(__file__).with_name("confusion_matrix.png")
    plt.savefig(cm_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Confusion matrix saved to: {cm_path}")
    
    # --- SAVE DETAILED REPORT ---
    report_path = Path(__file__).with_name("classification_report.txt")
    with open(report_path, "w") as f:
        f.write("AEGIS: Incident Classification Model - Detailed Report\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Dataset Size: {len(df)} samples\n")
        f.write(f"Training Set: {len(X_train)} samples\n")
        f.write(f"Test Set: {len(X_test)} samples\n\n")
        f.write("Test Set Metrics:\n")
        f.write(f"  Accuracy:  {accuracy:.4f}\n")
        f.write(f"  Precision: {precision:.4f}\n")
        f.write(f"  Recall:    {recall:.4f}\n\n")
        f.write("5-Fold CV Results (mean ± std):\n")
        for metric in ["accuracy", "precision", "recall"]:
            scores = fold_metrics[metric]
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            f.write(f"  {metric.capitalize():12s}: {mean_score:.4f} ± {std_score:.4f}\n")
        f.write("\n" + "=" * 60 + "\n")
        f.write("Classification Report:\n")
        f.write("=" * 60 + "\n")
        f.write(classification_report(y_test, y_pred, zero_division=0))
    
    print(f"Detailed report saved to: {report_path}")


if __name__ == "__main__":
    main()