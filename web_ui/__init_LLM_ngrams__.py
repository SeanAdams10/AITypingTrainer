
import openai
from flask import Blueprint, jsonify, render_template, request

web_ui = Blueprint("web_ui", __name__)


@web_ui.route("/ngram-words", methods=["GET"])
def ngram_words_page():
    return render_template("ngram_words.html")


@web_ui.route("/api/ngram-words", methods=["POST"])
def api_ngram_words():
    data = request.get_json()
    snippets = data.get("snippets", [])
    if not snippets or not isinstance(snippets, list):
        return jsonify({"error": "No snippets provided"}), 400

    prompt = "Return a series of words that include these ngrams: " + ", ".join(
        snippets
    )

    # Load OpenAI API key from file
    try:
        with open(
            os.path.join(os.path.dirname(__file__), "../Keys/OpenAPI_Key.txt"), "r"
        ) as f:
            openai.api_key = f.read().strip()
    except Exception as e:
        return jsonify({"error": f"Failed to load OpenAI API key: {e}"}), 500

    ngrams = '"ada"; "Fish"; "gan"'
    max_length = 250

    # Construct the prompt
    prompt = f"""
    You are an expert on words and lexicography. Please can you give me a list of words that include the following 
    ngrams {ngrams}. Can you please assemble this list in random order into a space delimited string, with a maximum 
    length of {max_length} characters. I'm OK if you repeat certain words, and also if you include the actual ngram.
    """

    # Make the API call to OpenAI using the "text-ada-001" model
    response = openai.Completion.create(
        model="text-ada-001",
        prompt=prompt,
        max_tokens=100,  # adjust the token count if needed
        n=1,
        stop=None,
        temperature=0.7,
    )

    generated_text = response.choices[0].text.strip()

    # --- Replace this with your OpenAI API key and call if available ---
    # For now, just echo the prompt for demo purposes
    # response = openai.ChatCompletion.create(...)
    # result = response['choices'][0]['message']['content']
    # ---
    # Placeholder/demo response:
    result = f"[DEMO] Would call LLM with prompt: {prompt}"
    return jsonify({"result": result})
