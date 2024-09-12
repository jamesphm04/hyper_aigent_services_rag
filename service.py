from flask import Flask, request, jsonify
from main import handle_qa

app = Flask(__name__)




@app.route('/services/rag/answer', methods=['POST'])
def getAnswer():
    json_data = request.get_json()
    answer = handle_qa(json_data['question'])

    return jsonify({
        "answer": answer
    }), 200

if __name__ == '__main__':
    app.run(port=5001, debug=True)
