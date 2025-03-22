from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    # Read sample text
    with open('static/sample.txt', 'r', encoding='utf-8') as f:
        sample_text = f.read()
    return render_template('index.html', sample_text=sample_text)

if __name__ == '__main__':
    app.run(debug=True)
