"""
DooleyHelpz – Step 3 (ML Version): Per-Student Course Recommendations

This file replaces the hand-written scoring function in Recommended_Courses.py
with a small machine learning model that behaves the SAME way at first
(we train it to approximate the old formula), but is now trainable and extendable.

Pipeline:

  1) Use Courses_Qualified_new.build_qualified_courses_for_student(shared_id)
     to apply all rule-based filters (prereqs, GER, major, timeUnavailable, etc.).

  2) For each qualified course, extract 4 RMP-based features:
       [rating_norm, again_norm, easy_norm, popularity_norm]

  3) Train a regression model to approximate your old score_course() function.

  4) For a given student, use the trained model to score and rank their qualified courses.

Outputs:
  - MongoDB: DetailedCourses.RecommendedML (per-user records)
  - JSON backup: out/recommended_<shared_id>_ml.json
"""

import os
import json
import math
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression
import joblib

from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Import your existing qualification logic
from Courses_Qualified_new import (
    build_qualified_courses_for_student,
    SYN_PREF_BY_ID,   # to get list of synthetic shared_ids
)

# -------------------- MongoDB Setup --------------------

from dotenv import load_dotenv
load_dotenv()
DB_URI = os.getenv("DB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

client = MongoClient(DB_URI)
DB_DETAILED = client["DetailedCourses"]
COL_RECOMMENDED_ML = DB_DETAILED["RecommendedML"]  # new collection

OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

MODEL_PATH = OUT_DIR / "recommender_ml.joblib"


# -------------------- Helper Functions --------------------

def norm(val, lo, hi, invert=False):
    """
    Same normalization helper as in Recommended_Courses.py
    but usable both for rule-based teacher and ML features.
    """
    if val is None:
        return 0.0
    v = max(lo, min(hi, float(val)))
    x = (v - lo) / (hi - lo) if hi > lo else 0.0
    return 1.0 - x if invert else x
def safe_num_ratings(val):
    """
    Convert num_ratings to a float safely.
    Handles strings like '12', None, empty strings, etc.
    """
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0



def score_course_rule_based(doc, w_rating=0.55, w_again=0.15, w_easy=0.15, w_pop=0.15):
    rmp = doc.get("rmp") or {}
    rating = norm(rmp.get("rating"), 0, 5)
    again = norm(rmp.get("would_take_again_%"), 0, 100)
    easy = norm(rmp.get("difficulty"), 1, 5, invert=True)
    raw_num = rmp.get("num_ratings")
    num = safe_num_ratings(raw_num)
    pop = math.log1p(num) / math.log1p(100) if num > 0 else 0.0


    return (w_rating * rating) + (w_again * again) + (w_easy * easy) + (w_pop * pop)



def extract_features_from_doc(doc):
    """
    Build the feature vector used by the ML model.

    Right now we mirror the 4 components from the rule-based score:
      X = [rating_norm, again_norm, easy_norm, popularity_norm]

    Later you can extend this to include:
      - major_must flag
      - major_elec flag
      - GER urgency
      - interest match
      - time preference alignment
      etc.
    """
    rmp = doc.get("rmp") or {}
    rating = norm(rmp.get("rating"), 0, 5)
    again = norm(rmp.get("would_take_again_%"), 0, 100)
    easy = norm(rmp.get("difficulty"), 1, 5, invert=True)
    raw_num = rmp.get("num_ratings")
    num = safe_num_ratings(raw_num)
    pop = math.log1p(num) / math.log1p(100) if num > 0 else 0.0


    return np.array([rating, again, easy, pop], dtype=float)


# -------------------- Training Data Builder --------------------

def build_training_matrix_from_synthetic(min_rating=0.0,
                                         instruction_method=None):
    """
    Build (X, y) from all synthetic users.

    For each synthetic shared_id:
      - Get their qualified courses using the existing rule-based pipeline.
      - For each course:
          X_row = extract_features_from_doc(doc)
          y     = score_course_rule_based(doc)

    Returns:
      X: shape (n_samples, n_features)
      y: shape (n_samples,)
    """
    X_rows = []
    y_rows = []

    shared_ids = sorted(list(SYN_PREF_BY_ID.keys()))

    for shared_id in shared_ids:
        print(f"[TRAIN] Building examples for synthetic user {shared_id}...")

        try:
            qualified = build_qualified_courses_for_student(
                shared_id,
                min_rating=min_rating,
                instruction_method=instruction_method,
            )
        except Exception as e:
            print(f"[WARN] Skipping user {shared_id} due to error: {e}")
            continue

        for doc in qualified:
            x = extract_features_from_doc(doc)
            y = score_course_rule_based(doc)
            X_rows.append(x)
            y_rows.append(y)

    if not X_rows:
        raise RuntimeError("No training data built (X_rows is empty).")

    X = np.vstack(X_rows)
    y = np.array(y_rows, dtype=float)
    print(f"[TRAIN] Built training matrix X shape={X.shape}, y shape={y.shape}")
    return X, y


# -------------------- Training & Saving the Model --------------------

def train_recommender_model(min_rating=0.0, instruction_method=None):
    """
    Train a simple linear regression model on synthetic data.

    Since y = 'score_course_rule_based(doc)', the fitted model should
    behave almost exactly like the original rule-based formula, but is now
    a real ML model that you can retrain and extend.
    """
    X, y = build_training_matrix_from_synthetic(
        min_rating=min_rating,
        instruction_method=instruction_method,
    )

    model = LinearRegression()
    model.fit(X, y)

    joblib.dump(model, MODEL_PATH)
    print(f"[TRAIN] Saved trained recommender model → {MODEL_PATH}")
    return model


def load_recommender_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file {MODEL_PATH} not found – run train_recommender_model() first."
        )
    return joblib.load(MODEL_PATH)


# -------------------- Per-Student Recommendation --------------------

def recommend_for_student_ml(shared_id: str,
                             top_n: int = 10,
                             min_rating: float = 0.0,
                             instruction_method: str | None = None,
                             use_trained_model: bool = True):
    """
    Main entry point, analogous to Recommended_Courses.run but per-student and ML-based.

    Steps:
      1) Get qualified courses for this student (rule-based).
      2) For each qualified course, compute X_row features.
      3) Apply ML model to get 'score_ml'.
      4) Sort by 'score_ml' descending, take top_n.
      5) Write to MongoDB and JSON backup.

    Returns: list of top_n recommended course docs (with 'score_ml' added).
    """
    # 1) Build qualified set exactly as your current system does
    qualified = build_qualified_courses_for_student(
        shared_id,
        min_rating=min_rating,
        instruction_method=instruction_method,
    )

    if not qualified:
        print(f"[INFO] No qualified courses for student {shared_id}.")
        return []

    # 2) Load or construct model
    if use_trained_model:
        model = load_recommender_model()
    else:
        # fall back to rule-based scoring if desired
        model = None

    # 3) Score each course
    scored = []
    for doc in qualified:
        x = extract_features_from_doc(doc)

        if model is not None:
            # ML prediction
            score_ml = float(model.predict(x.reshape(1, -1))[0])
        else:
            # Fallback: pure rule-based
            score_ml = float(score_course_rule_based(doc))

        doc_with_score = dict(doc)
        doc_with_score["score_ml"] = score_ml
        scored.append(doc_with_score)

        # ---------- GER-first, then major, then CS, then others ----------

    def is_cs_course(d):
        code = d.get("code")
        return isinstance(code, str) and code.upper().startswith("CS")

    # Buckets:
    #  1) GERs due now
    #  2) Major must courses
    #  3) CS electives (remaining CS / major_elec)
    #  4) Everything else
    bucket_ger_due = []
    bucket_major_must = []
    bucket_cs_electives = []
    bucket_other = []

    for d in scored:
        # Bucket 1: courses with GERs due (reason_ger_due non-empty)
        if d.get("reason_ger_due"):
            bucket_ger_due.append(d)

        # Bucket 2: major must courses
        elif d.get("reason_major_must"):
            bucket_major_must.append(d)

        # Bucket 3: CS electives remaining
        # (either flagged as major_elec or simply any CS course)
        elif d.get("reason_major_elec") or is_cs_course(d):
            bucket_cs_electives.append(d)

        # Bucket 4: pure electives
        else:
            bucket_other.append(d)

    # Keep ML ordering within each bucket (highest score_ml first)
    for bucket in (bucket_ger_due, bucket_major_must, bucket_cs_electives, bucket_other):
        bucket.sort(key=lambda d: d["score_ml"], reverse=True)

    # Final prioritized list: 1 → 2 → 3 → 4
    prioritized = (
        bucket_ger_due +
        bucket_major_must +
        bucket_cs_electives +
        bucket_other
    )

    top = prioritized[:top_n]


    # 4) Save to MongoDB (per-student)
    try:
        COL_RECOMMENDED_ML.delete_many({"shared_id": str(shared_id)})
        if top:
            COL_RECOMMENDED_ML.insert_many(top)
        print(f"[INFO] Wrote {len(top)} ML recommendations → DetailedCourses.RecommendedML.")
    except PyMongoError as e:
        print(f"[WARN] Mongo write failed: {e}")

    # 5) Save JSON backup
    out_path = OUT_DIR / f"recommended_{shared_id}_ml.json"
    with out_path.open("w", encoding="utf-8") as f:
        for d in top:
            d.pop("_id", None)
        json.dump(top, f, indent=2)
    print(f"[INFO] Saved backup → {out_path}")

    return top


# -------------------- CLI --------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--shared_id", type=str, default="000025")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--train", action="store_true",
                        help="If set, train model first on synthetic data.")
    parser.add_argument("--min_rating", type=float, default=0.0)
    parser.add_argument("--instruction_method", type=str, default=None)
    args = parser.parse_args()

    if args.train:
        train_recommender_model(
            min_rating=args.min_rating,
            instruction_method=args.instruction_method,
        )

    recommend_for_student_ml(
        shared_id=args.shared_id,
        top_n=args.top,
        min_rating=args.min_rating,
        instruction_method=args.instruction_method,
    )
