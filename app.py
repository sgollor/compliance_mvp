from flask import Flask, request, render_template, redirect, url_for
import os
import pandas as pd

# Create an instance of the Flask app
app = Flask(__name__)
# Define the folder where uploaded files will be saved
UPLOAD_FOLDER: str = 'uploads'
# Tell Flask to use this folder for file uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the uploads folder if it doesn't already exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define the home route ("/") that displays the upload form
@app.route('/')
def home():
    return render_template('upload.html') # Load the HTML form from the templates folder

@app.route('/upload', methods=['POST'])  # This route only responds to POST requests from the form
def upload_file():
    # Check if the form actually included a file
    if 'file' not in request.files:
        return "No file part", 400 # 400 = Bad Request
    
    # Grab the file from the form submission
    file = request.files['file']
    # Check if file is empty or missing a filename
    if not file or not file.filename:
        return "No selected file", 400
    
    # Safer filename validation    # Ensure the file is a CSV
    # Check if the filename is a string and ends with .csv
    if isinstance(file.filename, str) and file.filename.lower().endswith('.csv'):
         # Build a safe filepath in the "uploads" directory
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)

        # Save the file to disk
        file.save(filepath)
        # Optional: print the path to console for debugging
        print(f"Saved to: {filepath}")

        # START CSV VALIDATION BLOCK
        try:
            # Load CSV file into a Pandas DataFrame
            df = pd.read_csv(filepath)

            # Define expected columns
            REQUIRED_COLUMNS = [
                'agent_id',
                'agent_name',
                'kyc_status',
                'id_expiry',
                'txn_amount',
                'txn_time'
            ]

            # Check for missing required columns
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                return f"Missing required columns: {', '.join(missing_cols)}", 400

            # Check for any missing values
            if df.isnull().any().any():
                return "CSV contains missing values", 400
            
            # Try converting txn_amount to numeric 
            # # Clean commas out of txn_amount before converting
            df['txn_amount'] = pd.to_numeric(df['txn_amount'].astype(str).str.replace(',', ''), errors='coerce')

            # Try converting txn_time and id_expiry to datetime
            df['txn_time'] = pd.to_datetime(df['txn_time'], errors='coerce')
            df['id_expiry'] = pd.to_datetime(df['id_expiry'], errors='coerce')

            # Check each field individually for NaN/NaT issues and build error message
            invalid_columns = []

            if df['txn_amount'].isnull().any():
                invalid_columns.append('txn_amount')

            if df['txn_time'].isnull().any():
                invalid_columns.append('txn_time')

            if df['id_expiry'].isnull().any():
                invalid_columns.append('id_expiry')

            # If any invalid columns found, return specific message
            if invalid_columns:
                return f"Invalid data types in column(s): {', '.join(invalid_columns)}", 400


        except Exception as e:
            return f"Error reading file: {str(e)}", 400
        # END CSV VALIDATION BLOCK

        return f"File {file.filename} uploaded successfully!"
    
    # If the file is not a CSV, return an error
    return "Invalid file type", 400

if __name__ == '__main__':
    app.run(debug=True)
