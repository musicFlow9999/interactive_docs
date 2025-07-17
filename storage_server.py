from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

DATA_FILE = Path('stored_links.json')

def read_store():
    if DATA_FILE.is_file():
        try:
            with DATA_FILE.open() as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def write_store(store):
    with DATA_FILE.open('w') as f:
        json.dump(store, f)

@app.route('/links/<path:url>', methods=['GET'])
def get_links(url):
    store = read_store()
    return jsonify(store.get(url, []))

@app.route('/links/<path:url>', methods=['POST'])
def save_links(url):
    store = read_store()
    store[url] = request.get_json(force=True, silent=True) or []
    write_store(store)
    return jsonify({'status': 'ok'})

@app.route('/links', methods=['GET'])
def get_all():
    return jsonify(read_store())

@app.route('/links', methods=['POST'])
def save_all():
    store = request.get_json(force=True, silent=True) or {}
    write_store(store)
    return jsonify({'status': 'ok'})

@app.route('/ping')
def ping():
    return 'pong'

if __name__ == '__main__':
    app.run(port=5000)
