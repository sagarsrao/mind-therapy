import os
import json
import sys
import time
from collections import defaultdict

# Add the project root to path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.agents.classifier import SafetyClassifier

def run_evaluation():
    print("Starting Safety Classifier Evaluation...")
    classifier = SafetyClassifier()
    
    # Load dataset
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    with open(dataset_path, "r") as f:
        test_cases = json.load(f)
        
    results = []
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    
    # Track metrics per tier
    # Tiers: 'routine', 'elevated', 'crisis'
    tiers = ["routine", "elevated", "crisis"]
    
    tp = {t: 0 for t in tiers}
    fp = {t: 0 for t in tiers}
    fn = {t: 0 for t in tiers}
    tn = {t: 0 for t in tiers}
    
    start_time = time.time()
    
    for i, case in enumerate(test_cases):
        text = case["text"]
        expected = case["expected_tier"]
        rationale = case["rationale"]
        
        print(f"[{i+1}/{len(test_cases)}] Evaluating: \"{text[:40]}...\"")
        
        # Run classification
        classification = classifier.classify(text)
        actual = classification.tier
        
        # Record in confusion matrix
        confusion_matrix[expected][actual] += 1
        
        # Record details
        results.append({
            "index": i + 1,
            "text": text,
            "expected": expected,
            "actual": actual,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "rationale_dataset": rationale,
            "correct": expected == actual
        })
        
        # Calculate metrics elements
        for t in tiers:
            if expected == t and actual == t:
                tp[t] += 1
            elif expected != t and actual == t:
                fp[t] += 1
            elif expected == t and actual != t:
                fn[t] += 1
            else:
                tn[t] += 1
                
        # Small sleep to avoid rate limits
        time.sleep(0.2)
        
    duration = time.time() - start_time
    
    # Calculate precision, recall, F1
    metrics = {}
    for t in tiers:
        p = tp[t] / (tp[t] + fp[t]) if (tp[t] + fp[t]) > 0 else 0.0
        r = tp[t] / (tp[t] + fn[t]) if (tp[t] + fn[t]) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        
        metrics[t] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "true_positives": tp[t],
            "false_positives": fp[t],
            "false_negatives": fn[t],
            "true_negatives": tn[t]
        }
        
    overall_accuracy = sum(1 for r in results if r["correct"]) / len(results)
    
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": len(test_cases),
        "overall_accuracy": round(overall_accuracy, 4),
        "duration_seconds": round(duration, 2),
        "confusion_matrix": {exp: dict(act_counts) for exp, act_counts in confusion_matrix.items()},
        "metrics": metrics,
        "results": results
    }
    
    # Save results
    results_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n=== EVALUATION COMPLETED ===")
    print(f"Accuracy: {overall_accuracy * 100:.2f}%")
    print(f"Total time: {duration:.2f} seconds")
    print("\nMetrics per Tier:")
    for t in tiers:
        m = metrics[t]
        print(f"  {t.upper()}:")
        print(f"    Precision: {m['precision']:.4f}")
        print(f"    Recall:    {m['recall']:.4f}  <-- CRITICAL" if t == "crisis" else f"    Recall:    {m['recall']:.4f}")
        print(f"    F1-Score:  {m['f1_score']:.4f}")
        print(f"    (TP={m['true_positives']}, FP={m['false_positives']}, FN={m['false_negatives']})")
        
    print("\nConfusion Matrix (Rows: Expected, Columns: Actual):")
    print(f"          {'routine':<10} {'elevated':<10} {'crisis':<10}")
    for exp in tiers:
        row_str = f"{exp:<9} "
        for act in tiers:
            row_str += f"{confusion_matrix[exp][act]:<10} "
        print(row_str)
        
    return summary

if __name__ == "__main__":
    # Make sure we have a GEMINI_API_KEY
    if "GEMINI_API_KEY" not in os.environ:
        from dotenv import load_dotenv
        load_dotenv()
        
    run_evaluation()
