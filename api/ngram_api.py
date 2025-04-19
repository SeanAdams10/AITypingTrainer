"""
API endpoints for n-gram analysis and results.
"""
from flask import Blueprint, request, jsonify, make_response
from models.ngram_analyzer import NGramAnalyzer

ngram_api = Blueprint('ngram_api', __name__)

@ngram_api.route('/api/ngrams', methods=['GET'])
def api_list_ngrams():
    """Get speed and error n-gram results for a session."""
    session_id = request.args.get('session_id')
    if not session_id:
        return make_response(jsonify({'error': 'Missing session_id parameter'}), 400)
    ngram_results = []
    for n in range(2, 9):
        analyzer = NGramAnalyzer(n)
        try:
            speed_results = analyzer.get_speed_results_for_session(session_id)
            error_results = analyzer.get_error_results_for_session(session_id)
            ngram_results.append({
                'ngram_size': n,
                'speed_results': speed_results,
                'error_results': error_results
            })
        except Exception as exc:
            # Log the exception for debugging (could be replaced with logging)
            print(f"Error in ngram API for n={n}: {exc}")
            continue
    return make_response(jsonify(ngram_results), 200)

@ngram_api.route('/api/analyze-ngrams', methods=['POST'])
def api_analyze_ngrams():
    """
    Analyze and update n-gram results for all n-gram sizes.

    Returns:
        A JSON response containing the results of the analysis.
    """
    try:
        results = []
        for n in range(2, 9):
            analyzer = NGramAnalyzer(n)
            success = analyzer.analyze_ngrams()
            label = {
                2: "Bigrams",
                3: "Trigrams",
                4: "4-grams",
                5: "5-grams",
                6: "6-grams",
                7: "7-grams",
                8: "8-grams",
            }[n]
            results.append({
                'n': n,
                'label': label,
                'success': success
            })
        if all(r["success"] for r in results):
            return jsonify({
                "success": True,
                "message": "All n-gram analyses completed successfully.",
                "results": results
            })
        else:
            failed = [r["label"] for r in results if not r["success"]]
            return (
                jsonify({
                    "success": False,
                    "message": f"Failed to analyze: {', '.join(failed)}",
                    "results": results
                }),
                500
            )
    except Exception as exc:
        print(f"Error analyzing n-grams: {exc}")
        return make_response(jsonify({'error': 'Failed to analyze n-grams'}), 500)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
