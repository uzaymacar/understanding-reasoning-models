import json
import re
from collections import Counter
import random

mistake_phrases = [
    "i made a mistake", 
    "let me recalculate",
    "that's not right",
    "i need to correct",
    "let's try again",
    "i think i went wrong",
    "let's try another approach",
    "actually, i should",
    "wait, that's incorrect",
    "let me rethink",
    "on second thought",
    "i need to backtrack",
    "let me restart",
    "i made an error",
    "i think i made a mistake",
    "i think i made an error",
    "that doesn't seem right",
    "actually, i made a mistake in my calculation",
]

correction_phrases = [
    "hmm, that's not", 
    "hmm, that doesn't", 
    "hmm, this doesn't", 
    "wait, that's not", 
    "wait, that is not",
    "wait, this is not",
    "wait, that doesn't", 
    "wait, that does not",
    "wait, this doesn't",
    "wait, this does not",
    "actually, that's not", 
    "actually, that doesn't", 
    "actually, this doesn't",
    "oh, that's not", 
    "oh, that doesn't", 
    "oh, this doesn't",
    "wait, that's not quite right",
]

reconsideration_phrases = [
    "let me reconsider", 
    "let me think again", 
    "on second thought",
    "let's reconsider", 
    "let's think again", 
    "thinking again",
    "reconsidering", 
    "rethinking", 
    "wait, let's determine",
    "hmm, wait, let me check",
    "hmm, i think i misunderstood the question",
]

miscalculation_phrases = [
    "i made a calculation error", 
    "i made a computational error", 
    "i made an arithmetic error", 
    "i miscalculated",
    "i miscounted", 
    "i misunderstood", 
    "i misinterpreted",
]

doubt_phrases = [
    "i'm not sure if", 
    "i'm not convinced", 
    "i'm skeptical",
    "i'm doubtful", 
    "i'm uncertain", 
    "i'm not confident",
    "i'm hesitant", 
    "i'm not sure about", 
    "i'm not certain",
]

math_correction_phrases = [
    "let me redo this calculation", 
    "let me recalculate",
    "i need to redo", 
    "i should redo", 
    "i'll redo",
    "i must redo",
    "let me solve this again", 
    "let me solve this differently",
    "let me approach this differently", 
    "let me try a different approach",
    "actually, let me double-check",
    "wait, let me double-check",
]

backtracking_phrases = (
    mistake_phrases + 
    correction_phrases + 
    reconsideration_phrases + 
    miscalculation_phrases + 
    doubt_phrases + 
    math_correction_phrases
)

def identify_backtracking(cot_text):
    """
    Identify potential backtracking phrases in a CoT solution.
    
    Args:
        cot_text: The generated CoT solution text
    
    Returns:
        List of identified backtracking phrases
    """    
    found_phrases = []
    for phrase in backtracking_phrases:
        if phrase.lower() in cot_text.lower():
            found_phrases.append(phrase)
    
    return found_phrases

def extract_boxed_answers(text):
    """
    Extract boxed answers from a text.
    
    Args:
        text: The text to extract boxed answers from
    
    Returns:
        List of boxed answers
    """
    boxed_pattern = r"\\boxed{([^}]*)}"
    matches = re.findall(boxed_pattern, text)
    return [match.strip() for match in matches]
        
def analyze_cot_results(json_file_path):
    """
    Analyze the Chain-of-Thought results from a saved JSON file.
    
    Args:
        json_file_path: Path to the JSON file with CoT results
        
    Returns:
        Dictionary with analysis results
    """
    # Load the JSON data
    with open(json_file_path, 'r') as f:
        results = json.load(f)
    
    print(f"Analyzing {len(results)} CoT solutions...")
    
    # Initialize counters and storage
    analysis = {
        "total_problems": len(results),
        "correct_answers": 0,
        "has_think_close_tag": 0,
        "ran_out_of_tokens": 0,
        "has_backtracking": 0,
        "token_limit_problems": [],
        "backtracking_problems": [],
        "level_distribution": Counter(),
        "type_distribution": Counter(),
        "level_accuracy": {},
        "type_accuracy": {}
    }
    
    # Track level-specific metrics
    level_correct = Counter()
    level_total = Counter()
    type_correct = Counter()
    type_total = Counter()
    
    # Analyze each problem
    for result in results:
        problem_level = result.get("problem_level", "Unknown")
        problem_type = result.get("problem_type", "Unknown")
        problem_id = result.get("problem_id", "Unknown")
        
        # Update distributions
        analysis["level_distribution"][problem_level] += 1
        analysis["type_distribution"][problem_type] += 1
        level_total[problem_level] += 1
        type_total[problem_type] += 1
        
        # 1. Check for correct answers (this is a simplified check - may need refinement)
        # Extract boxed answers from both generated and ground truth
        generated_cot = result.get("generated_cot", "")
        ground_truth = result.get("ground_truth_solution", "")
        
        generated_answers = extract_boxed_answers(generated_cot)
        ground_truth_answers = extract_boxed_answers(ground_truth)
        
        # Check if any generated answer matches any ground truth answer
        is_correct = False
        if generated_answers and ground_truth_answers:
            # Normalize answers for comparison (remove spaces, convert to lowercase)
            norm_generated = [re.sub(r'\s+', '', ans.lower()) for ans in generated_answers]
            norm_ground_truth = [re.sub(r'\s+', '', ans.lower()) for ans in ground_truth_answers]
            
            # Check for any match
            for gen_ans in norm_generated:
                if any(gen_ans == gt_ans for gt_ans in norm_ground_truth):
                    is_correct = True
                    break
        
        if is_correct:
            analysis["correct_answers"] += 1
            level_correct[problem_level] += 1
            type_correct[problem_type] += 1
        
        # 2. Check for </think> close tags
        if "</think>" in generated_cot:
            analysis["has_think_close_tag"] += 1
        
        # 3. Check if ran out of tokens (heuristic: no boxed answer)
        # We determine token limit issues by checking if there's no boxed answer
        if len(generated_answers) == 1 and generated_answers[0] == '':
            analysis["ran_out_of_tokens"] += 1
            analysis["token_limit_problems"].append({
                "id": problem_id,
                "level": problem_level,
                "type": problem_type
            })
        
        # 4. Check for backtracking
        backtracking_phrases = identify_backtracking(generated_cot)
        if backtracking_phrases:
            analysis["has_backtracking"] += 1
            analysis["backtracking_problems"].append({
                "id": problem_id,
                "level": problem_level,
                "type": problem_type,
                "phrases": backtracking_phrases,
                "correct_after_backtracking": is_correct
            })
    
    # Calculate accuracy by level and type
    for level, count in level_total.items():
        analysis["level_accuracy"][level] = level_correct[level] / count if count > 0 else 0
    
    for problem_type, count in type_total.items():
        analysis["type_accuracy"][problem_type] = type_correct[problem_type] / count if count > 0 else 0
    
    # Calculate percentages for easier interpretation
    analysis["percent_correct"] = (analysis["correct_answers"] / analysis["total_problems"]) * 100 if analysis["total_problems"] > 0 else 0
    analysis["percent_think_close"] = (analysis["has_think_close_tag"] / analysis["total_problems"]) * 100 if analysis["total_problems"] > 0 else 0
    analysis["percent_token_limit"] = (analysis["ran_out_of_tokens"] / analysis["total_problems"]) * 100 if analysis["total_problems"] > 0 else 0
    analysis["percent_backtracking"] = (analysis["has_backtracking"] / analysis["total_problems"]) * 100 if analysis["total_problems"] > 0 else 0
    
    return analysis

def print_analysis_report(analysis, num_samples=8):
    """
    Print a formatted report of the analysis results.
    
    Args:
        analysis: Dictionary with analysis results
    """
    print("\n" + "="*50)
    print("CHAIN-OF-THOUGHT ANALYSIS REPORT")
    print("="*50)
    
    print(f"\nTotal problems analyzed: {analysis['total_problems']}")
    
    print("\n1. CORRECTNESS")
    print(f"Correct answers: {analysis['correct_answers']} ({analysis['percent_correct']:.2f}%)")
    
    print("\n2. THINK TAGS")
    print(f"Solutions with </think> close tags: {analysis['has_think_close_tag']} ({analysis['percent_think_close']:.2f}%)")
    
    print("\n3. TOKEN LIMITS")
    print(f"Problems that ran out of tokens: {analysis['ran_out_of_tokens']} ({analysis['percent_token_limit']:.2f}%)")
    
    print("\n4. BACKTRACKING")
    print(f"Solutions with backtracking: {analysis['has_backtracking']} ({analysis['percent_backtracking']:.2f}%)")
    if analysis['backtracking_problems']:
        num_samples_shown = 0
        print("Sample of problems with backtracking:")
        for problem in analysis['backtracking_problems']:
            if num_samples_shown >= num_samples: break
            if problem['correct_after_backtracking'] and problem['id'] not in [p['id'] for p in analysis.get('token_limit_problems', [])]:
                print(f"     Level: {problem['level']}, Type: {problem['type']}, Phrases: {', '.join(problem['phrases'])}")
                num_samples_shown += 1

    print("\n5. PERFORMANCE BY LEVEL")
    for level, accuracy in sorted(analysis['level_accuracy'].items()):
        count = analysis['level_distribution'][level]
        print(f"  {level}: {accuracy*100:.2f}% correct ({count} problems)")
    
    print("\n6. PERFORMANCE BY TYPE")
    for problem_type, accuracy in sorted(analysis['type_accuracy'].items()):
        count = analysis['type_distribution'][problem_type]
        print(f"  {problem_type}: {accuracy*100:.2f}% correct ({count} problems)")
    
    print("\n" + "="*50)
    
def run_analysis(json_file_path):
    """
    Run the analysis on a JSON file and print the report.
    
    Args:
        json_file_path: Path to the JSON file with CoT results
    """
    analysis = analyze_cot_results(json_file_path)
    print_analysis_report(analysis)
    return analysis


def create_balanced_backtracking_dataset(json_file_paths, output_path, n=100, seed=42):
    """
    Create a balanced dataset with n/2 samples containing backtracking phrases that were solved correctly
    and n/2 samples without backtracking phrases (randomly selected).
    
    Args:
        json_file_paths: List of paths to JSON files with CoT results
        output_path: Path to save the balanced dataset
        n: Total number of samples in the dataset (default: 100)
        seed: Random seed for reproducibility (default: 42)
    
    Returns:
        Dictionary with dataset statistics
    """
    random.seed(seed)
    
    # Load and merge data from multiple JSON files
    all_results = []
    
    for json_file_path in json_file_paths:
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r') as f:
            results = json.load(f)
        all_results.extend(results)
    
    print(f"Loaded {len(all_results)} total problems from all files")
    
    # Filter out problems that ran out of tokens
    completed_problems = []
    for result in all_results:
        generated_cot = result.get("generated_cot", "")        
        generated_answers = extract_boxed_answers(generated_cot)
        
        # Skip problems that ran out of tokens (no boxed answer or empty boxed answer)
        if not generated_answers or (len(generated_answers) == 1 and generated_answers[0] == ''):
            continue
        
        completed_problems.append(result)
    
    print(f"Found {len(completed_problems)} completed problems")
    
    # Identify problems with backtracking that were solved correctly
    backtracking_correct = []
    no_backtracking = []
    
    for problem in completed_problems:
        generated_cot = problem.get("generated_cot", "")
        ground_truth = problem.get("ground_truth_solution", "")        
        generated_answers = extract_boxed_answers(generated_cot)
        ground_truth_answers = extract_boxed_answers(ground_truth)
        
        # Check if correct
        is_correct = False
        if generated_answers and ground_truth_answers:
            # Normalize answers for comparison
            norm_generated = [re.sub(r'\s+', '', ans.lower()) for ans in generated_answers]
            norm_ground_truth = [re.sub(r'\s+', '', ans.lower()) for ans in ground_truth_answers]
            
            # Check for any match
            for gen_ans in norm_generated:
                if any(gen_ans == gt_ans for gt_ans in norm_ground_truth):
                    is_correct = True
                    break
        
        # Add is_correct flag to the problem
        problem["is_correct"] = is_correct
        
        # Check for backtracking
        backtracking_phrases = identify_backtracking(generated_cot)
        
        if backtracking_phrases and is_correct:
            backtracking_correct.append(problem)
        elif not backtracking_phrases:
            no_backtracking.append(problem)
    
    print(f"Found {len(backtracking_correct)} problems with backtracking that were solved correctly")
    print(f"Found {len(no_backtracking)} problems without backtracking")
    
    # Create balanced dataset ensuring unique problem IDs
    half_n = n // 2
    
    # Sort by problem_id to ensure deterministic selection when we have duplicates
    backtracking_correct.sort(key=lambda x: x.get("problem_id", ""))
    no_backtracking.sort(key=lambda x: x.get("problem_id", ""))
    
    # Select unique problem IDs for backtracking samples
    backtracking_samples = []
    backtracking_ids_selected = set()
    
    # First try to get as many unique samples as possible
    for problem in backtracking_correct:
        problem_id = problem.get("problem_id", "Unknown")
        if problem_id not in backtracking_ids_selected:
            backtracking_samples.append(problem)
            backtracking_ids_selected.add(problem_id)
            if len(backtracking_samples) >= half_n:
                break
    
    # If we don't have enough unique samples, use random sampling with replacement
    if len(backtracking_samples) < half_n:
        print(f"Warning: Only found {len(backtracking_samples)} unique backtracking problems. Using random sampling with replacement.")
        additional_needed = half_n - len(backtracking_samples)
        backtracking_samples.extend(random.choices(backtracking_correct, k=additional_needed))
    
    # Select unique problem IDs for no-backtracking samples
    no_backtracking_samples = []
    no_backtracking_ids_selected = set()
    
    # First try to get as many unique samples as possible
    # Avoid problem IDs already selected for backtracking
    for problem in no_backtracking:
        problem_id = problem.get("problem_id", "Unknown")
        if problem_id not in no_backtracking_ids_selected and problem_id not in backtracking_ids_selected:
            no_backtracking_samples.append(problem)
            no_backtracking_ids_selected.add(problem_id)
            if len(no_backtracking_samples) >= half_n:
                break
    
    # If we don't have enough unique samples, use random sampling with replacement
    if len(no_backtracking_samples) < half_n:
        print(f"Warning: Only found {len(no_backtracking_samples)} unique no-backtracking problems. Using random sampling with replacement.")
        # Prioritize problems with IDs not in backtracking set
        remaining_problems = [p for p in no_backtracking if p.get("problem_id", "Unknown") not in backtracking_ids_selected]
        if not remaining_problems:
            remaining_problems = no_backtracking
        
        additional_needed = half_n - len(no_backtracking_samples)
        no_backtracking_samples.extend(random.choices(remaining_problems, k=additional_needed))
    
    # Combine samples
    balanced_dataset = backtracking_samples + no_backtracking_samples
    
    # Add a flag indicating whether the sample contains backtracking
    for i, sample in enumerate(balanced_dataset):
        if i < half_n:
            sample["has_backtracking"] = True
        else:
            sample["has_backtracking"] = False
    
    # Shuffle the dataset
    random.shuffle(balanced_dataset)
    
    # Save the dataset
    with open(output_path, 'w') as f:
        json.dump(balanced_dataset, f, indent=2)
    
    print(f"Saved balanced dataset with {len(balanced_dataset)} samples to {output_path}")
    
    # Return statistics
    stats = {
        "total_samples": len(balanced_dataset),
        "backtracking_samples": len(backtracking_samples),
        "no_backtracking_samples": len(no_backtracking_samples),
        "unique_backtracking_ids": len(backtracking_ids_selected),
        "unique_no_backtracking_ids": len(no_backtracking_ids_selected),
        "original_backtracking_correct_count": len(backtracking_correct),
        "original_no_backtracking_count": len(no_backtracking),
        "total_problems_processed": len(all_results)
    }
    
    return stats