import os
import sys
import time
import json
from typing import List, Dict, Any

# Adjust paths to make sure Server imports work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(ROOT_DIR)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

# Import RAG pipeline
from Server.rag.pipeline import MITSQueryEngine

# --- STEP 1: Define evaluation test dataset ---
# A realistic set of questions, expected reference answers (ground truths), and expected sources
EVALUATION_DATASET = [
    {
        "question": "What courses are offered by the AI and ML department?",
        "ground_truth": "MITS offers B.Tech. in Computer Science and Engineering (Artificial Intelligence) and B.Tech. in Artificial Intelligence & Machine Learning (AI & ML).",
    },
    {
        "question": "Who is the Head of the AI & ML Department at MITS?",
        "ground_truth": "The Head of the AI & ML Department is Dr. [HOD Name] (Verify with current dataset files under mits_dataset/AI_ML/ or depts_hods/).",
    },
    {
        "question": "What is the library timing?",
        "ground_truth": "The library is open from 8:00 AM to 8:00 PM on all working days.",
    }
]

def run_evaluation():
    # Make sure we have the API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable is not set. Please set it in your .env file.")
        return

    print("Initializing RAG engine...")
    # Initialize query engine
    engine = MITSQueryEngine()
    engine.initialize_system()

    results = []
    
    print("\n--- Running Queries and Measuring Latency ---")
    for i, item in enumerate(EVALUATION_DATASET):
        q = item["question"]
        gt = item["ground_truth"]
        
        print(f"\n[{i+1}/{len(EVALUATION_DATASET)}] Query: {q}")
        
        # Measure Latency
        start_time = time.time()
        answer, contexts = engine.query(q)
        latency = time.time() - start_time
        
        print(f"Latency: {latency:.4f} seconds")
        
        # Extract source text blocks for context evaluation
        retrieved_contexts = [ctx["text"] for ctx in contexts]
        
        results.append({
            "question": q,
            "answer": answer,
            "contexts": retrieved_contexts,
            "ground_truth": gt,
            "latency": latency
        })

    # Save raw query results
    output_path = os.path.join(CURRENT_DIR, "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw query results and latency to: {output_path}")

    # --- STEP 2: Ragas Metrics Evaluation ---
    try:
        print("\nLoading Ragas and evaluating Faithfulness, Answer Relevancy, and Context Recall...")
        
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall
        # Ragas uses langchain chat models to evaluate. Using LangChain Gemini integrations:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        # Convert our results into Ragas format Dataset
        dataset_dict = {
            "question": [r["question"] for r in results],
            "answer": [r["answer"] for r in results],
            "contexts": [r["contexts"] for r in results],
            "ground_truth": [r["ground_truth"] for r in results]
        }
        dataset = Dataset.from_dict(dataset_dict)
        
        # Initialize Gemini model for evaluation (standard Gemini Pro/Flash)
        evaluator_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.environ.get("GEMINI_API_KEY")
        )
        
        # Configure metrics to use the custom LLM
        faithfulness.llm = evaluator_llm
        answer_relevancy.llm = evaluator_llm
        context_recall.llm = evaluator_llm
        
        # Evaluate
        eval_metrics = [faithfulness, answer_relevancy, context_recall]
        score = evaluate(dataset, metrics=eval_metrics)
        
        df = score.to_pandas()
        
        print("\n=== EVALUATION REPORT ===")
        print(df[["question", "faithfulness", "answer_relevancy", "context_recall"]])
        
        print("\n=== AVERAGE METRICS ===")
        print(f"Average Latency: {sum(r['latency'] for r in results)/len(results):.4f} seconds")
        for metric_name, val in score.items():
            print(f"Average {metric_name.capitalize()}: {val:.4f}")
            
    except ImportError:
        print("\n[INFO] Ragas/Pandas/Datasets packages not found.")
        print("To compute Faithfulness, Answer Relevancy, and Context Recall automatically, please run:")
        print("pip install ragas datasets pandas langchain-google-genai")
        print("\nRaw responses and latency have still been saved successfully.")

if __name__ == "__main__":
    run_evaluation()
