import logging
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

logging.info("Starting Flask application with Kubernetes and OpenAI integration...")

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

# Attempt to import OpenAI and check API key
try:
    import openai
    import os
    # Ensure the OpenAI API key is available
    openai.api_key = os.getenv("OPENAI_API_KEY") # Replace with actual API key or environment variable
    logging.info("OpenAI client initialized successfully.")
except ImportError:
    openai = None
    logging.error("OpenAI module not found. Ensure 'openai' package is installed.")
except Exception as e:
    openai = None
    logging.error(f"Failed to initialize OpenAI client: {str(e)}")

# Define response model
class QueryResponse(BaseModel):
    query: str
    answer: str

# Function to generate Kubernetes command using OpenAI
def generate_kubernetes_command(query):
    if not openai:
        logging.error("OpenAI client is not initialized.")
        return None
      

    prompt = f"""
    You are an AI assistant skilled in Kubernetes and Python. Your task is to generate a single line of Python code
    to answer specific Kubernetes-related questions for a Minikube setup using the Kubernetes client library (v1 client).
    Given the question: '{query}', generate a single line of code that uses the pre-defined Kubernetes client 'v1'
    and directly answers the question, storing the output in a variable 'result'.
    """

    try:
        logging.info(f"Generating Kubernetes command for query: {query}")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant skilled in Kubernetes and Python."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=150,
            temperature=0.3,
        )
        command = response.choices[0].message['content'].strip()
        logging.info(f"Generated command: {command}")
        return command
    except Exception as e:
        logging.error(f"Error generating Kubernetes command: {str(e)}")
        return None

# Endpoint to test command generation and execution
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

        # Step 1: Generate Kubernetes command
        command = generate_kubernetes_command(query)
        if not command:
            logging.error("Failed to generate command.")
            return jsonify({"error": "Failed to generate command"}), 500

        # Log the generated command (for debugging)
        logging.info(f"Generated command: {command}")

        # Placeholder answer until we add execution
        answer = f"Command generated: {command}"

        # Create and return the response
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
        logging.info("Flask application with Kubernetes and OpenAI integration is running on port 8000.")
    except Exception as e:
        logging.error(f"Failed to start Flask server: {str(e)}")
