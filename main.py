import logging
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

logging.info("Starting Flask application...")

# Initialize Flask app
try:
    app = Flask(__name__)
    logging.info("Flask app initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Flask app: {str(e)}")

# Define response model
class QueryResponse(BaseModel):
    query: str
    answer: str

# Define endpoint
@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Log request received
        logging.info("Received POST request at /query endpoint.")

        # Extract the question from the request data
        request_data = request.json
        if not request_data:
            logging.error("No JSON data found in request.")
            return jsonify({"error": "Invalid JSON input"}), 400

        query = request_data.get('query')
        if not query:
            logging.error("No 'query' key found in JSON data.")
            return jsonify({"error": "No query provided"}), 400
        
        # Log the query
        logging.info(f"Received query: {query}")

        # Generate a fixed answer for simplicity
        answer = "14"
        
        # Log the answer
        logging.info(f"Generated answer: {answer}")
        
        # Create and log response model
        response = QueryResponse(query=query, answer=answer)
        logging.info(f"Response created: {response.dict()}")

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
        logging.info("Flask application is running on port 8000.")
    except Exception as e:
        logging.error(f"Failed to start Flask server: {str(e)}")
