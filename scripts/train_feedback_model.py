import re
import logging
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from collections import Counter
from actions.logging.logging_helpers import log_info_text
from actions.utils.embedding_loader import get_embedder

log = logging.getLogger("rasa-actions")

# 📂 Load CSV
df = pd.read_csv("scripts/data/bot_feedback.csv")

# 🧮 Check vote distribution
log.info("🔍 Feedback distribution:")
log.info(df["vote"].value_counts())

# 😅 Remove emojis
def remove_emojis(text):
    return re.sub(r"[^\w\s,.?!-]", "", str(text))  # safe for non-str

df["clean_answer"] = df["answer"].apply(remove_emojis)

# 🧹 Remove unwanted logs
df = df[~df["question"].str.contains("LOG|Semantic score|Feedback sent", case=False, na=False)]

# 🧽 Remove duplicates
df = df.drop_duplicates(subset=["answer"])
df = df.drop_duplicates(subset=["question", "answer"])

# ✨ Clean and normalize questions
df["clean_question"] = (
    df["question"]
    .astype(str)
    .str.replace(r"[^\w\s]", "", regex=True)
    .str.lower()
)

# 🏷️ Encode labels
df["label"] = df["vote"].map({"yes": 1, "no": 0})
X_raw = df["clean_question"]
y = df["label"]

# 🔠 Sentence embedding
log_info_text("🔍 ", "Generating sentence embeddings...")
X_vec = get_embedder().encode(X_raw.tolist())

# 🤖 Model
model = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)

# 📊 Dynamic Stratified K-Fold CV
class_counts = Counter(y)
min_class_samples = min(class_counts.values())
n_splits = min(5, min_class_samples)

log_info_text("\n🚀 ", f"Running {n_splits}-fold cross-validation...")
cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
scores = cross_val_score(model, X_vec, y, cv=cv, scoring='f1_weighted')
log_info_text("✅ ", f"Average weighted F1-score: {scores.mean():.2f} (CV scores: {scores})")

# 🧪 Split test set
X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, stratify=y, random_state=42
)

# 🏋️ Train
model.fit(X_train, y_train)

# 🧾 Evaluate
y_pred = model.predict(X_test)
log_info_text("\n📋 ", "Test Set Classification Report:")
if len(y_test) < 10:
    log_info_text("⚠️ Warning: ", "Test set is very small. Metrics may not be stable.\n")
log_info_text("", classification_report(y_test, y_pred, zero_division=0))

# 💾 Save
joblib.dump(model, "samples/feedback_classifier.pkl")
joblib.dump(get_embedder(), "samples/feedback_embedder.pkl")
log_info_text("✅ ", "Model and embedder saved successfully.")
