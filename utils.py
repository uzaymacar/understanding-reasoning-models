import json
import re
from collections import Counter

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
]

correction_phrases = [
    "hmm, that's not", 
    "hmm, that doesn't", 
    "hmm, this doesn't", 
    "wait, that's not", 
    "wait, that doesn't", 
    "wait, this doesn't",
    "actually, that's not", 
    "actually, that doesn't", 
    "actually, this doesn't",
    "oh, that's not", 
    "oh, that doesn't", 
    "oh, this doesn't",
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
    "let me try a different approach"
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
        
        # Extract boxed answers
        def extract_boxed_answers(text):
            boxed_pattern = r"\\boxed{([^}]*)}"
            matches = re.findall(boxed_pattern, text)
            return [match.strip() for match in matches]
        
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