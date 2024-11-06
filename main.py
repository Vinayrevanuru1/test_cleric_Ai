import logging
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import os

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
    openai.api_key = os.getenv("OPENAI_API_KEY")
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
    prompt = f"""
   You are an AI assistant skilled in Kubernetes and Python. Your task is to generate Python code that answers specific Kubernetes-related questions using the Kubernetes client library (v1 client) for a Minikube setup. 

For each query, please generate code that:
- Directly retrieves the relevant data to answer the question, filtering out any unnecessary metadata, identifiers, or redundant information.
- Ensures that only the essential data for the query is returned in the variable 'result' as a list, dictionary, or string, with concise formatting.
- Uses read-only operations and respects the Minikube environment compatibility.

Given the question: '{query}', produce a solution that:
- Uses the 'v1' Kubernetes client for interaction.
- Retrieves only the minimal and relevant data needed to answer, removing or filtering any extraneous data.
- Does not include code fences (e.g., ```python)
    """
    
    # logging.info(f"Prompt for command generation: {prompt.strip()}")
    response = openai.ChatCompletion.create(
        model="gpt-4o",
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

def execute_generated_command(command):
    local_vars = {}
    command = command.replace("```python", "").replace("```", "").strip()
    # logging.debug(f"Executing command: {command}")

    try:
        exec(command, globals(), local_vars)
        result = local_vars.get('result', "No result returned")
        logging.debug(f"Execution result: {result}")
        return result
    except Exception as e:
        logging.error(f"Execution error: {str(e)}")
        return f"Error executing command: {str(e)}"

def format_result_with_gpt(query, result):
    prompt = f"""
    You are an AI assistant skilled in summarizing technical data. Given the question: '{query}' and the raw result: '{result}',
    provide only the direct answer without any metadata, unique identifiers, or extra formatting. 
    Return only the concise and relevant answer that directly addresses the question."""
    
    # logging.debug(f"Prompt for result formatting: {prompt.strip()}")

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant skilled in summarizing technical data concisely."},
            {"role": "user", "content": prompt.strip()}
        ],
        max_tokens=20,
        temperature=0.3,
    )
    
    answer = response.choices[0].message['content'].strip()
    logging.debug(f"Formatted answer: {answer}")
    return answer

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

        # Step 2: Execute the generated command
        result = execute_generated_command(command)

        # Step 3: Format the result using GPT
        answer = format_result_with_gpt(query, result)

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
