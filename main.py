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

# Function to execute the generated Kubernetes command
def execute_generated_command(command):
    if not command:
        logging.error("No command to execute.")
        return "No command generated."

    local_vars = {}
    command = command.replace("```python", "").replace("```", "").strip()
    logging.debug(f"Executing command: {command}")

    try:
        exec(command, globals(), local_vars)
        result = local_vars.get('result', "No result returned")
        logging.debug(f"Execution result: {result}")
        return result
    except AttributeError as e:
        logging.error(f"Attribute error during command execution: {str(e)}")
        return "Kubernetes client method not supported on Minikube."
    except Exception as e:
        logging.error(f"Execution error: {str(e)}")
        return f"Error executing command: {str(e)}"

# Function to format the result using OpenAI
def format_result_with_gpt(query, result):
    if not openai:
        logging.error("OpenAI client is not initialized.")
        return "Error: OpenAI client not available."

    prompt = f"""
    You are an AI assistant skilled in summarizing technical data. Given the question: '{query}' and the raw result: '{result}',
    provide only the direct answer without any metadata, unique identifiers, or extra formatting. For example, return 'mongodb' instead of 'mongodb-56c598c8fc'.
    Return only the concise and relevant answer that directly addresses the question.
    """

    try:
        logging.info(f"Formatting result for query: {query}")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant skilled in summarizing technical data concisely."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=20,
            temperature=0.3,
        )
        answer = response.choices[0].message['content'].strip()
        logging.info(f"Formatted answer: {answer}")
        return answer
    except Exception as e:
        logging.error(f"Error formatting result with GPT: {str(e)}")
        return "Error formatting answer."

# Main endpoint to handle queries
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

        # Step 2: Execute the command
        raw_result = execute_generated_command(command)
        if "Error" in raw_result:
            logging.error("Error in command execution.")
            return jsonify({"error": raw_result}), 500

        # Step 3: Format the result
        answer = format_result_with_gpt(query, raw_result)
        if "Error" in answer:
            logging.error("Error in formatting result.")
            return jsonify({"error": answer}), 500

        response = QueryResponse(query=query, answer=answer)
        logging.info(f"Final response created: {response.dict()}")
        return jsonify(response.dict())
    
    except ValidationError as e:
        logging.error(f"Validation Error: {e.errors()}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Start Flask server
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=8000)
        logging.info("Flask application with Kubernetes and OpenAI integration is running on port 8000.")
    except Exception as e:
        logging.error(f"Failed to start Flask server: {str(e)}")
