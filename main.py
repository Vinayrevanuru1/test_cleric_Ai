import logging
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

logging.info("Starting Flask application with Kubernetes integration...")

# Initialize Flask app
app = Flask(__name__)

# Import and initialize Kubernetes client
try:
    from kubernetes import client, config
    config.load_kube_config(config_file="~/.kube/config")
    v1 = client.CoreV1Api()
    logging.info("Kubernetes client initialized successfully.")
except ImportError:
    v1 = None
    logging.error("Kubernetes module not found. Ensure 'kubernetes' package is installed.")
except Exception as e:
    v1 = None
    logging.error(f"Failed to load Kubernetes configuration: {str(e)}")

# Define response model
class QueryResponse(BaseModel):
    query: str
    answer: str

# Query endpoint (same as before)
@app.route('/query', methods=['POST'])
def create_query():
    try:
        logging.info("Received POST request at /query endpoint.")
        request_data = request.json
        if not request_data:
            logging.error("No JSON data found in request.")
            return jsonify({"error": "Invalid JSON input"}), 400

        query = request_data.get('query')
        if not query:
            logging.error("No 'query' key found in JSON data.")
            return jsonify({"error": "No query provided"}), 400
        
        logging.info(f"Received query: {query}")
        answer = "14"  # Placeholder answer
        logging.info(f"Generated answer: {answer}")
        
        response = QueryResponse(query=query, answer=answer)
        logging.info(f"Response created: {response.dict()}")
        return jsonify(response.dict())
    
    except ValidationError as e:
        logging.error(f"Validation Error: {e.errors()}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Test Kubernetes connection endpoint
@app.route('/test_kube_connection', methods=['GET'])
def test_kube_connection():
    if not v1:
        logging.error("Kubernetes client is not initialized.")
        return jsonify({"error": "Kubernetes client not initialized"}), 500

    try:
        # Attempt to list namespaces to verify connectivity
        namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
        logging.info("Successfully retrieved namespaces from Kubernetes.")
        return jsonify({"namespaces": namespaces})
    except Exception as e:
        logging.error(f"Failed to retrieve namespaces: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Start Flask server
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=8000)
        logging.info("Flask application with Kubernetes integration is running on port 8000.")
    except Exception as e:
        logging.error(f"Failed to start Flask server: {str(e)}")
