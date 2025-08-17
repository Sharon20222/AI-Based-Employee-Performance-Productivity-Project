from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, jsonify, redirect, url_for, request, session, flash
from flask_mail import Mail, Message
import re
import pandas as pd
import os
import plotly.express as px
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from multiprocessing import get_start_method
import matplotlib
matplotlib.use('Agg')
from sklearn.preprocessing import LabelEncoder
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import base64
from datetime import datetime
import pymysql  # Unused now; kept in case you revert back to MySQL
import requests
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

# Initialize start method
start_method = get_start_method()
print(f"Using start method: {start_method}")

# Load the pre-trained model
model_path = os.path.join(os.path.dirname(__file__), "random_forest_model.pkl")
try:
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        print("✅ Model loaded successfully!")
    else:
        print(f"❌ Model file not found at {model_path}")
        model = None
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")



# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


mail = Mail(app)


_first_request_handled = False

@app.before_request
def initialize_on_first_request():
    global _first_request_handled
    if not _first_request_handled:
        try:
            # Just check if tables exist rather than recreating
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users LIMIT 1")
            cursor.close()
            conn.close()
            _first_request_handled = True
        except:
            # Only create tables if they don't exist
            create_users_table()
            upload_csv_once()
            _first_request_handled = True

# PostgreSQL DB connection using Render URL
def get_db_connection():
    try:
        result = urlparse(os.getenv("DATABASE_URL"))
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        print("✅ Successfully connected to PostgreSQL!")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        raise

@app.route("/create-users-table")
def create_users_table():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if table exists first
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            cursor.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                );
            """)
            connection.commit()
            message = "✅ Users table created successfully!"
        else:
            message = "✅ Users table already exists"
            
        cursor.close()
        connection.close()
        return message
    except Exception as e:
        return f"❌ Error creating users table: {e}"

# Email notification
def send_hr_email(employee, status):
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        print("❌ Email config missing!")
        return False

    subject = f"Employee Performance Alert: {employee['Employee_ID']}"
    body = f"""
    HR Team,

    Employee {employee['Employee_ID']} - {employee.get('Job_Title', 'Unknown')} in {employee.get('Department', 'Unknown')} 
    has been classified as: {status}.

    Performance Score: {employee['Performance_Score']}

    Regards,
    AI Performance System
    """
    msg = Message(subject, recipients=["snitdan17@gmail.com"])
    msg.body = body
    mail.send(msg)
    print(f"✅ Email sent for {employee['Name']}")
    return True

# Performance check logic
def check_and_notify_low_performance():
    connection = get_db_connection()
    cursor = connection.cursor()
    low_threshold = 2.5
    cursor.execute("SELECT * FROM employees WHERE Performance_Score < %s", (low_threshold,))
    rows = cursor.fetchall()

    # Convert PostgreSQL tuples to dict (column names)
    colnames = [desc[0] for desc in cursor.description]
    low_performers = [dict(zip(colnames, row)) for row in rows]

    for emp in low_performers:
        send_hr_email(emp, "Low Performance")

    cursor.close()
    connection.close()
    print(f"✅ Low performance check completed at {datetime.now()}")

# Email test route
@app.route('/test-email')
def test_email():
    try:
        test_employee = {
            'Name': 'Test Employee',
            'Employee_ID': '123',
            'Performance_Score': 2.0,
            'Job_Title': 'Intern',
            'Department': 'Testing'
        }
        success = send_hr_email(test_employee, "Low Performance")
        return "✅ Email sent!" if success else "❌ Email failed."
    except Exception as e:
        return f"Error: {str(e)}"

# Flask-Login User class
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    if row:
        return User(*row)
    return None

# Helper to get employee info
def get_employee_data(employee_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM employees WHERE Employee_ID = %s", (employee_id,))
    row = cursor.fetchone()
    if not row:
        return None
    colnames = [desc[0] for desc in cursor.description]
    employee = dict(zip(colnames, row))
    cursor.close()
    connection.close()
    return employee

# Generic DB query
def query_db(query):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    result = [dict(zip(colnames, row)) for row in rows]
    cursor.close()
    connection.close()
    return result


@app.route('/upload-csv-once')  
def upload_csv_once():
    try:
        df = pd.read_csv("Extended_Employee_Performance_and_Productivity_Data.csv")
        engine = create_engine(os.getenv("DATABASE_URL"))
        df.to_sql("employees", engine, if_exists="replace", index=False)
        return "✅ CSV uploaded to PostgreSQL successfully!"
    except Exception as e:
        return f"❌ Error uploading CSV: {str(e)}"


# Step 1: Ask DeepSeek to generate SQL
def ask_deepseek_for_sql(question):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are a data analyst. Use the following table schema:
        Table: employees (
            Employee_ID, Department, Gender, Age, Job_Title, Hire_Date, Years_At_Company,
            Education_Level, Performance_Score, Monthly_Salary, Work_Hours_Per_Week,
            Projects_Handled, Overtime_Hours, Sick_Days, Remote_Work_Frequency,
            Team_Size, Training_Hours, Promotions, Employee_Satisfaction_Score, Resigned
        )

        Write an SQL query based on this question: {question}"""

    body = {
        "model": "deepseek-chat",  # or other available model
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }

    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body)
    return response.json()["choices"][0]["message"]["content"]


import re

def extract_sql(text):
    # Try to extract SQL code from markdown-style code block first
    code_blocks = re.findall(r"```sql(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if code_blocks:
        return code_blocks[0].strip()

    # Fallback: get the last line starting with SELECT/INSERT/UPDATE/DELETE
    lines = text.strip().splitlines()
    sql_lines = [line.strip() for line in lines if re.match(r"^(SELECT|INSERT|UPDATE|DELETE)", line.strip(), re.IGNORECASE)]
    return sql_lines[-1] if sql_lines else text.strip()



# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')





@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            connection = get_db_connection()
            cursor = connection.cursor()  # Remove dictionary=True
            
            # Get user data
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if user_data:
                # Convert tuple to dictionary
                columns = [desc[0] for desc in cursor.description]
                user = dict(zip(columns, user_data))
                
                if bcrypt.check_password_hash(user['password'], password):
                    login_user(User(user["id"], user["username"], user["email"]))
                    return redirect(url_for('home'))
            
            flash('Invalid email or password', 'danger')
            
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')




@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already exists! Please use a different email.', 'danger')
                return redirect(url_for('signup'))
            
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                         (username, email, hashed_password))
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')



@app.route('/logout')
def logout():
    # Flash message BEFORE clearing session
    flash('You have been logged out successfully.', 'info')
    
    # Then perform logout operations
    logout_user()
    session.clear()
    
    # Redirect to login page
    return redirect(url_for('login'))


@app.route('/visualization')
def visualization():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()  # Removed dictionary=True
        
        # Execute query and convert results to dictionary format
        cursor.execute("SELECT * FROM employees")
        columns = [desc[0] for desc in cursor.description]  # Get column names
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]  # Convert to dict
        
        df = pd.DataFrame(data)

        # Ensure columns are of the correct type
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
        df['Performance_Score'] = pd.to_numeric(df['Performance_Score'], errors='coerce')
        df['Monthly_Salary'] = pd.to_numeric(df['Monthly_Salary'], errors='coerce')
        df['Projects_Handled'] = pd.to_numeric(df['Projects_Handled'], errors='coerce')
        df['Years_At_Company'] = pd.to_numeric(df['Years_At_Company'], errors='coerce')

        # Drop rows with NaN values
        df = df.dropna(subset=['Age', 'Performance_Score', 'Monthly_Salary', 'Years_At_Company'])

        # Create the scatter plot for Performance Score vs Salary
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.scatter(df['Monthly_Salary'], df['Performance_Score'], alpha=0.5, color='blue')
        ax1.set_xlabel("Monthly Salary")
        ax1.set_ylabel("Performance Score")
        ax1.set_title("Performance Score vs Monthly Salary")
        
        # Save the scatter plot
        img1 = BytesIO()
        fig1.savefig(img1, format='png')
        img1.seek(0)
        scatter_plot_url = base64.b64encode(img1.getvalue()).decode('utf8')

        # Create the count plot for Projects Handled by Age
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        sns.countplot(x='Age', data=df[df['Projects_Handled'] == 1], palette="magma", ax=ax2)
        ax2.set_title("Projects Handled by Age")
        ax2.set_xlabel('Age')
        ax2.set_ylabel('Number of Projects Handled')
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')

        # Save the count plot
        img2 = BytesIO()
        fig2.savefig(img2, format='png')
        img2.seek(0)
        count_plot_url = base64.b64encode(img2.getvalue()).decode('utf8')

        # Create the pie chart for Department Distribution
        department_counts = df['Department'].value_counts()
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        ax3.pie(department_counts, labels=department_counts.index, autopct='%1.1f%%', 
               startangle=90, colors=sns.color_palette("Set3", len(department_counts)))
        ax3.axis('equal')
        ax3.set_title("Employee Distribution by Department")

        # Save the pie chart
        img3 = BytesIO()
        fig3.savefig(img3, format='png')
        img3.seek(0)
        pie_chart_url = base64.b64encode(img3.getvalue()).decode('utf8')

        # Create the line plot for Performance Score vs Years at the Company
        df_grouped = df.groupby('Years_At_Company').agg({'Performance_Score': 'mean'}).reset_index()
        fig5, ax5 = plt.subplots(figsize=(10, 6))
        ax5.plot(df_grouped['Years_At_Company'], df_grouped['Performance_Score'], marker='o', color='purple')
        ax5.set_xlabel("Years at Company")
        ax5.set_ylabel("Average Performance Score")
        ax5.set_title("Performance Score vs Years at the Company")

        # Save the line plot
        img5 = BytesIO()
        fig5.savefig(img5, format='png')
        img5.seek(0)
        line_chart_url = base64.b64encode(img5.getvalue()).decode('utf8')

        return render_template('visualization.html', 
                            scatter_plot_url=scatter_plot_url, 
                            count_plot_url=count_plot_url, 
                            pie_chart_url=pie_chart_url,
                            line_chart_url=line_chart_url)

    except Exception as e:
        # Proper error handling with resource cleanup
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
        return f"Error: {e}"
    finally:
        # Ensure resources are always closed
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    # Send email with all low performers when page is loaded (GET request)
    if request.method == 'GET':
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()  # Removed dictionary=True
            
            # Get all employees with performance < 2
            cursor.execute("SELECT * FROM employees WHERE Performance_Score < 2")
            
            # Convert results to dictionary format
            columns = [desc[0] for desc in cursor.description]
            low_performers = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if low_performers:
                # Prepare email content
                subject = f"Low Performers Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                body = "The following employees have performance scores below 2:\n\n"
                
                for employee in low_performers:
                    body += (f"ID: {employee['Employee_ID']}, "
                            f"Score: {employee['Performance_Score']}, "
                            f"Department: {employee['Department']}\n")
                
                body += "\nPlease review their performance."
                
                # Send email
                msg = Message(
                    subject=subject,
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=["snitdan17@gmail.com"]  # Your email
                )
                msg.body = body
                mail.send(msg)
                
                flash('Low performers report sent to HR', 'info')
            
        except Exception as e:
            print(f"Error sending low performers email: {str(e)}")
            flash('Failed to send low performers report', 'error')
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    if request.method == 'POST':
        # Handle existing employee search
        if 'employee_id' in request.form:
            employee_id = request.form['employee_id']
            employee = get_employee_data(employee_id)

            if not employee:
                return render_template('prediction.html', error="Employee not found!")

            performance_score = employee.get('Performance_Score')

            if performance_score is None:
                return render_template('prediction.html', error="Performance score not available for this employee!")

            # Determine employee status
            if performance_score < 2:
                status = "At Risk of Layoff"
                recommendation = "Consider retraining or performance improvement plan."
            elif performance_score >= 4:
                status = "Promotion Recommended"
                recommendation = "Eligible for promotion based on performance."
            else:
                status = "Needs Motivation"
                recommendation = "Provide additional incentives or training."

            return render_template('prediction.html', employee=employee, 
                                   score=performance_score, status=status, 
                                   recommendation=recommendation)

        # Handle new employee prediction
        elif 'monthly_salary' in request.form:
            # Get form data
            form_data = request.form.to_dict()

            # Encode categorical features
            categorical_features = ['job_title', 'department', 'education', 'gender']
            le = LabelEncoder()
            for col in categorical_features:
                form_data[col] = le.fit_transform([form_data[col]])[0]

            # Map form data to the feature names used during training
            input_data = {
                "Monthly_Salary": float(form_data["monthly_salary"]),
                "Job_Title": form_data["job_title"],
                "Department": form_data["department"],
                "Sick_Days": int(form_data["sick_days"]),
                "Employee_Satisfaction_Score": float(form_data["employee_satisfaction_score"]),
                "Promotions": int(form_data["promotions"]),
                "Training_Hours": int(form_data["training_hours"]),
                "Team_Size": int(form_data["team_size"]),
                "Remote_Work_Frequency": float(form_data["remote_work_frequency"]),
                "Projects_Handled": int(form_data.get("projects_handled", 0)),
                "Overtime_Hours": int(form_data.get("overtime_hours", 0)),
                "Gender": form_data["gender"],
                "Work_Hours_Per_Week": int(form_data.get("work_hours_per_week", 40)),
                "Education_Level": form_data["education"],
                "Years_At_Company": int(form_data.get("years_at_company", 0))
            }

            # Convert input data to DataFrame
            input_df = pd.DataFrame([input_data])

            # Ensure the columns are in the correct order
            feature_columns = [
                "Monthly_Salary", "Job_Title", "Department", "Sick_Days",
                "Employee_Satisfaction_Score", "Promotions", "Training_Hours", "Team_Size",
                "Remote_Work_Frequency", "Projects_Handled", "Overtime_Hours", "Gender",
                "Work_Hours_Per_Week", "Education_Level", "Years_At_Company"
            ]
            input_df = input_df[feature_columns]

            # Make prediction
            prediction = model.predict(input_df)

            # Determine employee status and recommendation
            if prediction[0] < 2:
                status = "At Risk of Layoff"
                recommendation = "Consider retraining or performance improvement plan."
            elif prediction[0] >= 4:
                status = "Promotion Recommended"
                recommendation = "Eligible for promotion based on performance."
            else:
                status = "Needs Motivation"
                recommendation = "Provide additional incentives or training."

            print(f"Prediction: {prediction[0]}, Status: {status}, Recommendation: {recommendation}")

            return render_template('prediction.html', prediction=prediction[0], 
                                   status=status, recommendation=recommendation)

    return render_template('prediction.html')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    success = None
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
                                                    
        try:
            # Process the message using chat.py logic
            chat_response = process_contact_message(name, email, message)

            # Send email to the designated recipient
            msg = Message(f"New message from {name}", 
                         sender=app.config['MAIL_USERNAME'], 
                         recipients=["recipient-email@example.com"])
            msg.body = f"Message: {message}\nFrom: {name} ({email})"
            mail.send(msg)

            # Set success message
            success = "Your message has been sent successfully."
        except Exception as e:
            # Set error message
            error = f"An error occurred: {str(e)}"

    return render_template('contact.html', success=success, error=error)


# Step 2: Flask route for chatbot
@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_question = request.json.get('message')

    try:
        sql = ask_deepseek_for_sql(user_question)

        final_sql = extract_sql(sql)

        # Optional: log for debugging
        print("🧠 SQL generated by DeepSeek:", final_sql)

        if ";" in final_sql.strip().rstrip(";"):
            raise Exception("Invalid SQL: multiple statements are not allowed.")

        results = query_db(final_sql)
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        # Optionally: summarize results with DeepSeek
        summary_prompt = f"""
            You are a helpful HR data analyst assistant.

            User's question: "{user_question}"

            Query result: {results}

            Instructions:
            1. First, give a **direct, factual answer** based only on the query result. Be specific and concise.
            2. Then, provide any **insights or patterns** you observe. Mention extremes or noteworthy trends if they exist.
            3. Keep the response clear and professional. Avoid repeating the user's question.
            4. Use bullet points only in the second part if needed. No emojis.
            """



        body = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": summary_prompt}],
            "max_tokens": 300
        }
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body)
        reply = response.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Sorry, I couldn't process that. Error: {str(e)}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Get port from Render's environment
    app.run(host='0.0.0.0', port=port)
