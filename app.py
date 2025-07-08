# Import os to interact with the file system (like saving uploads)
import os

# Import pandas to work with CSV files and data validation later
import pandas as pd

# Enable Flask sessions — this key signs and encrypts the session cookie
# In production, load this from an environment variable instead of hard-coding
import secrets

import io # Import io to handle file-like objects (if needed for advanced file handling)

# Import the necessary Flask tools to create a web server
from flask import Flask, request, render_template, redirect, url_for

# Import datetime to get today’s date for comparing against each agent’s ID expiry
from datetime import datetime

from flask import session # To store data across requests
from flask import send_file # To send files back to the user (if needed later)

from functools import wraps # For creating decorators to protect routes

# MVP user store: username { password, role }
USERS = {
    'admin':   {'password': 'AdminPass123',   'role': 'admin'},
    'officer': {'password': 'OfficerPass456', 'role': 'officer'}
}
# This is a simple in-memory user store for demonstration purposes
# In a real app, use a database or secure vault for user credentials

# Create an instance of the Flask app
app = Flask(__name__)

app.secret_key = secrets.token_hex(16)  # Generate a random secret key for session management
# This key is used to sign session cookies and should be kept secret in production

# Define the folder where uploaded files will be saved
UPLOAD_FOLDER: str = 'uploads'
# Tell Flask to use this folder for file uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the uploads folder if it doesn't already exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define a decorator to protect routes that require login
# This will check if the user is logged in before allowing access to certain routes
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user' not in session:
            # Not logged in? Send them to login page
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

# Define the login route that handles both GET and POST requests
# GET shows the login form, POST processes the login attempt
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = USERS.get(username)

        # Basic credential check
        if not user or user['password'] != password:
            error = "Invalid username or password."
        else:
            # Credentials OK - store user info in session
            session['user'] = username
            session['role'] = user['role']
            return redirect(url_for('home'))

    # GET (or bad POST) - show login form
    return render_template('login.html', error=error)

# Define a logout route to clear the session and redirect to login
# This will be used to log out the user and clear their session data
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# EPIC 1: File Upload & CSV Validation Task 1.1: Build Flask route for file upload
# This route will handle the file upload from the HTML form
# Define the home route ("/") that displays the upload form
@app.route('/')
@login_required  # Protect this route so only logged-in users can access it
def home():
    return render_template('upload.html') # Load the HTML form from the templates folder

@app.route('/upload', methods=['POST'])  # This route only responds to POST requests from the form
@login_required  # Protect this route so only logged-in users can access it
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
            # MVP Task 1.2: Validate CSV structure and content (headers, data types)
            # Load CSV file into a Pandas DataFrame
            df = pd.read_csv(filepath)

            # Task 1.3: Save parsed data to in-memory Pandas DataFrame or DB
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

            print("Parsed CSV:")
            print(df.head()) # For debug
            print("Column Types:")
            print(df.dtypes) # For debug

            # Task 2.1: Implement KYC completeness checker
            # Get today’s date for expiry comparison
            today = pd.to_datetime(datetime.today().date())

            # Define a function to apply per‐row
            def check_kyc(row):
                # 1. If the status isn’t 'complete', mark INCOMPLETE
                if row['kyc_status'].lower() != 'complete':
                    return 'INCOMPLETE'
                # 2. If expiry is before today, mark EXPIRED
                if pd.isna(row['id_expiry']) or row['id_expiry'] < today:
                    return 'EXPIRED'
                # 3. Otherwise, it’s good
                return 'OK'

            # Apply the function row-by-row to create a new column
            df['kyc_flag'] = df.apply(check_kyc, axis=1)

            # View results for debug
            print("KYC Flags:")
            print(df[['agent_id', 'kyc_status', 'id_expiry', 'kyc_flag']])

            # Task 2.2: Implement AML rule: flag txn > threshold
            # Define your high-value threshold
            HIGH_VALUE_THRESHOLD = 1000  # e.g., ₦1,000

            # Create a new column 'aml_flag' based on txn_amount
            # If amount > threshold → "ALERT", else → "OK"
            df['aml_flag'] = df['txn_amount'].apply(
            lambda amt: 'ALERT' if amt > HIGH_VALUE_THRESHOLD else 'OK'
            )

            # For debug print
            print("AML Flags (High-Value Transactions):")
            print(df[['agent_id', 'txn_amount', 'aml_flag']])

            # Task 2.3: Implement AML rule: flag >3 txns/hour per agent
            # Sort by agent and time so rolling windows work correctly
            df = df.sort_values(['agent_id', 'txn_time'])

            # Use txn_time as index for time-based rolling
            df.set_index('txn_time', inplace=True)

            # For each agent, count how many txns in the past 1 hour
            df['txns_last_hour'] = (
                df.groupby('agent_id')['agent_id']  # group by agent
                    .rolling('1h')                    # look back 1 hour
                    .count()                          # count rows
                .reset_index(level=0, drop=True)  # align result back to df
            )

            # Flag as ALERT if count ≥3, else OK
            df['frequency_flag'] = df['txns_last_hour'].apply(
                lambda cnt: 'ALERT' if cnt >= 3 else 'OK'
            )

            # Restore txn_time from index (if needed later as a column)
            df.reset_index(inplace=True)

            # For debug print
            print("Frequency-based flags:")
            print(df[['agent_id','txn_time','txns_last_hour','frequency_flag']])

            # Task 2.4: Aggregate Overall Risk per Agent
            # Define a helper that takes a DataFrame slice for one agent
            def compute_agent_risk(group):
                # If any red-level flags, immediate RED
                if (group['kyc_flag'] == 'EXPIRED').any() \
                    or (group['aml_flag'] == 'ALERT').any() \
                    or (group['frequency_flag'] == 'ALERT').any():
                    return 'RED'
                # If no RED but some INCOMPLETE KYCs, YELLOW
                if (group['kyc_flag'] == 'INCOMPLETE').any():
                    return 'YELLOW'
                # Otherwise, all clear → GREEN
                return 'GREEN'

            # Group by agent_id and apply the helper to produce a Series of statuses
            agent_risk = df.groupby('agent_id').apply(compute_agent_risk)

            # Convert to a clean DataFrame for reporting
            agent_summary = agent_risk.reset_index(name='risk_status')

            # Print the summary for debug
            print("Agent Risk Summary:")
            print(agent_summary)

            # Convert summary DF to list-of-dicts and store in session
            session['agent_summary'] = agent_summary.to_dict(orient='records')
            # This allows us to access it later in the dashboard route

            # Proceed to next route or render template with DataFrame
            #return f"File {file.filename} uploaded, validated, and KYC, AML checks & agent risk summary generated successfully!"

            # …then send them straight to the dashboard
            return redirect(url_for('dashboard'))

        except Exception as e:
             # Handle errors during CSV parsing
            return f"Error reading and parsing file: {str(e)}", 400
        # END CSV VALIDATION BLOCK
                 
    # If the file is not a CSV, return an error
    return "Invalid file type", 400

# EPIC 3: Dashboard & Report UI Task 3.1: Build Flask route for compliance officer dashboard
# Task 3.2: Display flagged agents in table with color-coded statuses Task 3.3: Enable download of TXT/PDF summary report

@app.route('/dashboard')
@login_required  # Protect this route so only logged-in users can access it
def dashboard():
    # Retrieve the agent_summary DataFrame we stored in session
    data = session.get('agent_summary', [])
    # Render the dashboard template, passing in the list of dicts
    return render_template('dashboard.html', agents=data)

@app.route('/download_report')
def download_report():
    # 1) Get the summary data from session
    data = session.get('agent_summary', [])
    
    # 2) Turn it back into a DataFrame
    df = pd.DataFrame(data)
    
    # 3) Use a StringIO buffer to hold CSV data in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # 4) Send it as a file download
    return send_file(
        io.BytesIO(output.getvalue().encode()),   # file content
        mimetype='text/csv',                      # CSV mime type
        as_attachment=True,                       # download instead of render
        download_name='agent_summary.csv'         # suggested filename
    )

if __name__ == '__main__':
    app.run(debug=True)
