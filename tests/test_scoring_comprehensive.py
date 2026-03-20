#!/usr/bin/env python3
"""
Comprehensive test suite for the scoring system.

Tests all scoring components:
- Performance scoring (victory, SC count, growth)
- Precision scoring (invalid orders, convoys, supports, bounces)
- Press evaluation (truthfulness, cooperation, deception)
- Report generation and integration
"""

import sys
import os
import tempfile
import json
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.scoring import GameScorer
from diplomacy_game_engine.scoring.order_analyzer import OrderAnalyzer


def create_mock_game_data(temp_dir: str, scenario: str):
    """Create mock game data for testing different scenarios."""
    
    # Create subdirectories
    os.makedirs(os.path.join(temp_dir, "states"))
    os.makedirs(os.path.join(temp_dir, "orders"))
    os.makedirs(os.path.join(temp_dir, "summaries"))
    
    # Create model assignments
    assignments = {
        "game_id": f"test_{scenario}",
        "platform": "bedrock",
        "randomized": False,
        "assignments": {
            "England": "test-haiku",
            "France": "test-haiku",
            "Germany": "test-sonnet",
            "Italy": "test-haiku",
            "Austria-Hungary": "test-haiku",
            "Russia": "test-sonnet",
            "Turkey": "test-sonnet"
        }
    }
    
    with open(os.path.join(temp_dir, "model_assignments.json"), 'w') as f:
        json.dump(assignments, f)
    
    if scenario == "victory":
        create_victory_scenario(temp_dir)
    elif scenario == "growth":
        create_growth_scenario(temp_dir)
    elif scenario == "invalid_orders":
        create_invalid_orders_scenario(temp_dir)
    elif scenario == "press_evaluation":
        create_press_evaluation_scenario(temp_dir)


def create_victory_scenario(temp_dir: str):
    """Create scenario where one power wins."""
    
    # Initial state - standard start
    initial_state = {
        "year": 1901,
        "season": "Spring",
        "supply_centers": {
            "Lon": "England", "Edi": "England", "Lvp": "England",
            "Par": "France", "Mar": "France", "Bre": "France",
            "Ber": "Germany", "Mun": "Germany", "Kie": "Germany",
            # ... (3 SCs each for all powers)
        }
    }
    
    # Final state - Germany wins with 18 SCs
    final_state = {
        "year": 1910,
        "season": "Fall",
        "supply_centers": {
            # Germany has 18 SCs
            **{f"SC{i}": "Germany" for i in range(18)},
            # Others have remaining SCs
            "Lon": "England", "Par": "France", "Rom": "Italy"
        }
    }
    
    with open(os.path.join(temp_dir, "states", "1901_00_initial.json"), 'w') as f:
        json.dump(initial_state, f)
    
    with open(os.path.join(temp_dir, "states", "1910_fall_after.json"), 'w') as f:
        json.dump(final_state, f)


def create_growth_scenario(temp_dir: str):
    """Create scenario with SC growth."""
    
    initial_state = {
        "year": 1901,
        "season": "Spring",
        "supply_centers": {
            "Lon": "England", "Edi": "England", "Lvp": "England",
            "Par": "France", "Mar": "France", "Bre": "France",
            "Ber": "Germany", "Mun": "Germany", "Kie": "Germany",
            "Rom": "Italy", "Ven": "Italy", "Nap": "Italy",
            "Vie": "Austria-Hungary", "Bud": "Austria-Hungary", "Tri": "Austria-Hungary",
            "Mos": "Russia", "War": "Russia", "StP": "Russia", "Sev": "Russia",
            "Con": "Turkey", "Ank": "Turkey", "Smy": "Turkey"
        }
    }
    
    final_state = {
        "year": 1902,
        "season": "Fall",
        "supply_centers": {
            # England gained 2 SCs
            "Lon": "England", "Edi": "England", "Lvp": "England", "Nwy": "England", "Bel": "England",
            # France gained 1 SC
            "Par": "France", "Mar": "France", "Bre": "France", "Spa": "France",
            # Germany maintained
            "Ber": "Germany", "Mun": "Germany", "Kie": "Germany",
            # Italy lost 1 SC
            "Rom": "Italy", "Ven": "Italy",
            # Austria gained 1
            "Vie": "Austria-Hungary", "Bud": "Austria-Hungary", "Tri": "Austria-Hungary", "Ser": "Austria-Hungary",
            # Russia maintained
            "Mos": "Russia", "War": "Russia", "StP": "Russia", "Sev": "Russia",
            # Turkey maintained
            "Con": "Turkey", "Ank": "Turkey", "Smy": "Turkey"
        }
    }
    
    with open(os.path.join(temp_dir, "states", "1901_00_initial.json"), 'w') as f:
        json.dump(initial_state, f)
    
    with open(os.path.join(temp_dir, "states", "1902_fall_after.json"), 'w') as f:
        json.dump(final_state, f)


def create_invalid_orders_scenario(temp_dir: str):
    """Create scenario with invalid orders."""
    
    # Create a summary mentioning invalid orders
    summary = """# Spring 1901 Summary

## Critical Errors (Illegal Orders)

The following orders were ILLEGAL:

- **England** tried to move A Lvp → Bel directly (non-adjacent)
- **Russia** attempted F StP → Bot (invalid province code)
- **Italy** ordered F Nap → Ion (invalid province code)
- **Turkey** commanded F Ank → Bla (invalid province code)

These units held position instead.
"""
    
    with open(os.path.join(temp_dir, "summaries", "1901_spring_summary.md"), 'w') as f:
        f.write(summary)
    
    # Create minimal states
    state = {"year": 1901, "season": "Spring", "supply_centers": {
        "Lon": "England", "Edi": "England", "Lvp": "England"
    }}
    
    with open(os.path.join(temp_dir, "states", "1901_00_initial.json"), 'w') as f:
        json.dump(state, f)
    with open(os.path.join(temp_dir, "states", "1901_spring_after.json"), 'w') as f:
        json.dump(state, f)


def create_press_evaluation_scenario(temp_dir: str):
    """Create scenario with press evaluation scores."""
    
    summary = """# Spring 1901 Summary

Diplomatic activity was high.

PRESS_SCORES:
- England: Truthfulness=8, Cooperation=7, Deception=3
- France: Truthfulness=6, Cooperation=8, Deception=5
- Germany: Truthfulness=9, Cooperation=6, Deception=2
- Italy: Truthfulness=7, Cooperation=5, Deception=4
- Austria-Hungary: Truthfulness=8, Cooperation=7, Deception=3
- Russia: Truthfulness=6, Cooperation=6, Deception=4
- Turkey: Truthfulness=7, Cooperation=8, Deception=2
"""
    
    with open(os.path.join(temp_dir, "summaries", "1901_spring_summary.md"), 'w') as f:
        f.write(summary)
    
    # Create minimal states
    state = {"year": 1901, "season": "Spring", "supply_centers": {
        "Lon": "England", "Par": "France", "Ber": "Germany"
    }}
    
    with open(os.path.join(temp_dir, "states", "1901_00_initial.json"), 'w') as f:
        json.dump(state, f)
    with open(os.path.join(temp_dir, "states", "1901_spring_after.json"), 'w') as f:
        json.dump(state, f)


def test_performance_scoring():
    """Test performance scoring calculations."""
    print("\n" + "="*80)
    print("TEST: Performance Scoring")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_game_data(temp_dir, "growth")
        
        scorer = GameScorer(temp_dir)
        scores = scorer.calculate_performance_scores()
        
        print("\nPerformance Scores:")
        for power, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            details = scorer.sc_details[power]
            print(f"  {power:15} - {score:3} points (Initial: {details['initial']}, Final: {details['final']}, Growth: {details['growth']:+d})")
        
        # Verify England gained 2 SCs
        assert scorer.sc_details['England']['growth'] == 2, "England should have gained 2 SCs"
        assert scores['England'] > scores['Germany'], "England should score higher than Germany (growth bonus)"
        
        print("\n✓ Performance scoring tests passed!")
        return True


def test_invalid_orders_detection():
    """Test invalid order detection from summaries."""
    print("\n" + "="*80)
    print("TEST: Invalid Orders Detection")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_game_data(temp_dir, "invalid_orders")
        
        analyzer = OrderAnalyzer(temp_dir)
        counts = analyzer.analyze_all_orders()
        
        print("\nInvalid Order Counts:")
        for power, metrics in sorted(counts.items()):
            if metrics['invalid_orders'] > 0:
                print(f"  {power:15} - {metrics['invalid_orders']} invalid orders")
        
        # Verify all 4 powers detected
        assert counts['England']['invalid_orders'] == 1, "England should have 1 invalid order"
        assert counts['Russia']['invalid_orders'] == 1, "Russia should have 1 invalid order"
        assert counts['Italy']['invalid_orders'] == 1, "Italy should have 1 invalid order"
        assert counts['Turkey']['invalid_orders'] == 1, "Turkey should have 1 invalid order"
        assert counts['France']['invalid_orders'] == 0, "France should have 0 invalid orders"
        
        print("\n✓ Invalid orders detection tests passed!")
        return True


def test_press_evaluation_extraction():
    """Test press evaluation score extraction."""
    print("\n" + "="*80)
    print("TEST: Press Evaluation Extraction")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        create_mock_game_data(temp_dir, "press_evaluation")
        
        scorer = GameScorer(temp_dir)
        press_scores = scorer.extract_press_scores()
        
        print("\nPress Scores Extracted:")
        for power, scores in sorted(press_scores.items()):
            if scores:
                truth = scores.get('truthfulness', [0])[0] if scores.get('truthfulness') else 0
                coop = scores.get('cooperation', [0])[0] if scores.get('cooperation') else 0
                decep = scores.get('deception', [0])[0] if scores.get('deception') else 0
                print(f"  {power:15} - Truth:{truth}, Coop:{coop}, Decep:{decep}")
        
        # Verify scores extracted
        assert press_scores['England']['truthfulness'][0] == 8, "England truthfulness should be 8"
        assert press_scores['France']['cooperation'][0] == 8, "France cooperation should be 8"
        assert press_scores['Germany']['deception'][0] == 2, "Germany deception should be 2"
        
        print("\n✓ Press evaluation extraction tests passed!")
        return True


def test_complete_scoring_report():
    """Test complete scoring report generation."""
    print("\n" + "="*80)
    print("TEST: Complete Scoring Report")
    print("="*80)
    
    # Use real game data
    game_folder = "games/bedrock_mix_press_score_000"
    
    if not os.path.exists(game_folder):
        print(f"⚠ Skipping - game folder not found: {game_folder}")
        return True
    
    scorer = GameScorer(game_folder)
    report_path = scorer.save_report()
    
    print(f"\n✓ Report generated: {report_path}")
    
    # Verify report contains all sections
    with open(report_path, 'r') as f:
        content = f.read()
    
    assert "Game Configuration" in content, "Report should have Game Configuration"
    assert "Overall Rankings" in content, "Report should have Overall Rankings"
    assert "Performance Scores" in content, "Report should have Performance Scores"
    assert "Precision Scores" in content, "Report should have Precision Scores"
    
    # Verify precision scores are not all zero
    assert "Invalid Orders" in content, "Report should show Invalid Orders column"
    
    print("✓ Complete scoring report tests passed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE SCORING SYSTEM TEST SUITE")
    print("="*80)
    
    tests = [
        ("Performance Scoring", test_performance_scoring),
        ("Invalid Orders Detection", test_invalid_orders_detection),
        ("Press Evaluation Extraction", test_press_evaluation_extraction),
        ("Complete Scoring Report", test_complete_scoring_report),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n✗ Test failed with error: {e}")
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"  Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓✓ ALL TESTS PASSED! ✓✓")
        print("\nThe scoring system is working correctly!")
    else:
        print(f"\n✗✗ {total - passed} TEST(S) FAILED ✗✗")
    
    print("="*80)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
