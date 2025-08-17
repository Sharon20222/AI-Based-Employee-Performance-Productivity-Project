# import pandas as pd
# import re
# from fuzzywuzzy import fuzz
# import numpy as np
# from datetime import datetime

# # Initialize DataFrame
# df = pd.read_csv('Extended_Employee_Performance_and_Productivity_Data.csv')

# # Convert date columns if they exist
# date_columns = ['Hire_Date', 'Termination_Date', 'Last_Review_Date']
# for col in date_columns:
#     if col in df.columns:
#         df[col] = pd.to_datetime(df[col], errors='coerce')

# def preprocess(text):
#     """Normalize text for matching"""
#     return re.sub(r'[^\w\s]', '', text.lower())

# def match_phrases(phrases, question, threshold=70):
#     """Fuzzy match with multiple phrases"""
#     question = preprocess(question)
#     for phrase in phrases:
#         if fuzz.partial_ratio(preprocess(phrase), question) >= threshold:
#             return True
#     return False

# def get_statistics(column, is_numeric=True):
#     """Generate statistics for a column"""
#     stats = {}
#     if is_numeric:
#         stats = {
#             'average': df[column].mean(),
#             'median': df[column].median(),
#             'min': df[column].min(),
#             'max': df[column].max(),
#             'std': df[column].std()
#         }
#     else:
#         stats = {
#             'counts': df[column].value_counts().to_dict(),
#             'mode': df[column].mode()[0]
#         }
#     return stats

# def analyze_trends(metric, time_column='Hire_Date'):
#     """Analyze trends over time"""
#     if time_column not in df.columns:
#         return "No time data available"
    
#     df['Year'] = df[time_column].dt.year
#     return df.groupby('Year')[metric].mean().to_dict()

# def process_contact_message(name, email, message):
#     """Process contact form messages"""
#     print(f"Received message from {name} ({email}): {message}")
#     return f"Thank you for your message, {name}. We'll respond within 24 hours."

# def answer_hr_question(question):
#     """Comprehensive HR question answering system"""
#     question_lower = preprocess(question)

#     # ========== GREETINGS & CONVERSATIONAL FLOW ==========
#     if match_phrases(["hi", "hello", "hey", "greetings"], question_lower):
#         return "Hello! I'm your HR assistant. How can I help you today?"
    
#     if match_phrases(["how are you", "how's it going"], question_lower):
#         return "I'm just a bot, but I'm functioning well! How can I assist with HR matters?"
    
#     if match_phrases(["thanks", "thank you", "appreciate"], question_lower):
#         return "You're welcome! Is there anything else you'd like to know?"
    
#     if match_phrases(["bye", "goodbye", "see you"], question_lower):
#         return "Goodbye! Feel free to ask more HR questions anytime."
    
#     # ========== GENERAL HR QUESTIONS ==========
#     if match_phrases(["hr policy", "policies", "rules", "guidelines"], question_lower):
#         policies = {
#             "Leave Policy": "15 days PTO + 10 holidays annually",
#             "Remote Work": "Up to 2 days WFH per week (manager approval)",
#             "Probation": "90-day probation period for new hires",
#             "Promotions": "Annual review cycle with promotion opportunities"
#         }
#         return "HR Policies:\n" + "\n".join([f"{k}: {v}" for k,v in policies.items()])
    
#     # ========== COMPENSATION & BENEFITS ==========
#     if match_phrases(["salary", "pay", "compensation"], question_lower):
#         salary_stats = get_statistics('Monthly_Salary')
        
#         # For general salary average questions
#         if match_phrases(["average", "mean", "typical"], question_lower):
#             return (f"The average monthly salary across all employees is ${salary_stats['average']:,.2f}.\n"
#                    f"Median salary: ${salary_stats['median']:,.2f}")
        
#         # For salary distribution questions
#         if match_phrases(["range", "distribution", "spread"], question_lower):
#             bands = pd.cut(df['Monthly_Salary'], 
#                          bins=5,
#                          labels=['$3,800-$4,900', '$4,900-$5,900', 
#                                  '$5,900-$6,900', '$6,900-$7,900', 
#                                  '$7,900-$9,000'])
#             distribution = bands.value_counts().sort_index()
            
#             response = "Salary distribution across ranges:\n"
#             for range_, count in distribution.items():
#                 response += f"{range_}: {count} employees ({count/len(df)*100:.1f}%)\n"
#             return response
        
#         # Default salary response
#         return (f"Here are key salary statistics:\n"
#                f"• Average: ${salary_stats['average']:,.2f}\n"
#                f"• Median: ${salary_stats['median']:,.2f}\n"
#                f"• Range: ${salary_stats['min']:,.2f} to ${salary_stats['max']:,.2f}")
    
#     # ========== PERFORMANCE MANAGEMENT ==========
#     if match_phrases(["performance", "productivity", "evaluation"], question_lower):
#         perf_stats = get_statistics('Performance_Score')
        
#         if match_phrases(["review", "cycle", "schedule"], question_lower):
#             return "Performance reviews are conducted quarterly with annual summaries"
            
#         if match_phrases(["improve", "low", "underperform"], question_lower):
#             low_perf = df[df['Performance_Score'] < 5].shape[0]
#             return (f"{low_perf} employees are underperforming (<5/10). "
#                    "Recommended actions: coaching, training, or PIP")
        
#         return (f"Performance Statistics (0-10 scale):\n"
#                f"Average: {perf_stats['average']:.1f}\n"
#                f"Median: {perf_stats['median']:.1f}\n"
#                f"{df[df['Performance_Score'] >= 8].shape[0]} top performers (8+)")
    
#     # ========== RECRUITMENT & STAFFING ==========
#     if match_phrases(["hiring", "recruit", "openings", "vacancies"], question_lower):
#         current_openings = {
#             "Engineering": ["Frontend Developer", "Data Engineer"],
#             "Marketing": ["Content Specialist"],
#             "HR": ["Recruiter"]
#         }
#         return "Current Openings:\n" + "\n".join(
#             [f"{dept}: {', '.join(roles)}" for dept, roles in current_openings.items()])
    
#     # ========== EMPLOYEE DEVELOPMENT ==========
#     if match_phrases(["training", "development", "learning"], question_lower):
#         train_stats = get_statistics('Training_Hours')
#         skills = {
#             "Most Requested": ["Leadership", "Python", "Project Management"],
#             "Upcoming Programs": ["DEI Workshop (Jun)", "Cloud Certification (Jul)"]
#         }
#         return (f"Training Statistics:\n"
#                f"Avg hours/employee: {train_stats['average']:.1f}\n"
#                f"Popular skills: {', '.join(skills['Most Requested'])}")
    
#     # ========== EMPLOYEE RELATIONS ==========
#     if match_phrases(["satisfaction", "engagement", "morale"], question_lower):
#         sat_stats = get_statistics('Employee_Satisfaction_Score')
#         return (f"Employee Satisfaction (1-10 scale):\n"
#                f"Average: {sat_stats['average']:.1f}\n"
#                f"Trend: {'↑' if sat_stats['average'] > 7 else '↓'} from last year")
    
#     # ========== WORKFORCE ANALYTICS ==========
#     if match_phrases(["workforce", "demographics", "composition"], question_lower):
#         gender = df['Gender'].value_counts(normalize=True) * 100
#         tenure = (datetime.now() - df['Hire_Date']).dt.days / 365 if 'Hire_Date' in df.columns else None
        
#         response = (f"Workforce Composition:\n"
#                    f"Gender: {gender.to_dict()}\n"
#                    f"Departments: {df['Department'].value_counts().to_dict()}")
        
#         if tenure is not None:
#             response += f"\nAvg Tenure: {tenure.mean():.1f} years"
#         return response
    
#     # ========== TIME & ATTENDANCE ==========
#     if match_phrases(["attendance", "absenteeism", "late"], question_lower):
#         if 'Absences' in df.columns:
#             abs_stats = get_statistics('Absences')
#             return (f"Absenteeism:\n"
#                    f"Avg days/year: {abs_stats['average']:.1f}\n"
#                    f"Most common reason: {df['Absence_Reason'].mode()[0]}")
#         return "Attendance data not available"
    
#     # ========== COMPLIANCE ==========
#     if match_phrases(["compliance", "regulation", "law"], question_lower):
#         return ("Compliance Status:\n"
#                "- All mandatory trainings completed\n"
#                "- 100% of employees certified in workplace safety\n"
#                "- Next audit scheduled for Q3")
    
#     # ========== EMPLOYEE SEARCH ==========
#     if match_phrases(["who is", "find employee", "look up"], question_lower):
#         name_match = re.search(r'(who is|find|look up) (\w+)', question_lower, re.IGNORECASE)
#         if name_match:
#             name = name_match.group(2)
#             matches = df[df['Employee_Name'].str.contains(name, case=False)]
#             if not matches.empty:
#                 emp = matches.iloc[0]
#                 return (f"{emp['Employee_Name']}\n"
#                        f"Position: {emp['Job_Title']}\n"
#                        f"Department: {emp['Department']}\n"
#                        f"Tenure: {((datetime.now() - emp['Hire_Date']).days/365):.1f} years")
#             return f"No employee found matching '{name}'"
    
#     # ========== TREND ANALYSIS ==========
#     if match_phrases(["trend", "over time", "historical"], question_lower):
#         if match_phrases(["performance"], question_lower):
#             trends = analyze_trends('Performance_Score')
#             return "Performance Trends:\n" + "\n".join([f"{k}: {v:.1f}" for k,v in trends.items()])
        
#         if match_phrases(["salary", "compensation"], question_lower):
#             trends = analyze_trends('Monthly_Salary')
#             return "Salary Trends:\n" + "\n".join([f"{k}: ${v:,.2f}" for k,v in trends.items()])
    
#     # ========== BENCHMARKING ==========
#     if match_phrases(["compare", "vs", "benchmark"], question_lower):
#         if match_phrases(["department", "team"], question_lower):
#             dept_stats = df.groupby('Department').agg({
#                 'Monthly_Salary': 'mean',
#                 'Performance_Score': 'mean',
#                 'Employee_Satisfaction_Score': 'mean'
#             })
#             return "Department Benchmarks:\n" + dept_stats.to_string()
    
#     # ========== PREDICTIVE ANALYTICS ==========
#     if match_phrases(["predict", "forecast", "likely"], question_lower):
#         if match_phrases(["turnover", "attrition"], question_lower):
#             risk = df[df['Employee_Satisfaction_Score'] < 5].shape[0]
#             return (f"{risk} employees at high risk of turnover (satisfaction <5/10)\n"
#                    "Factors: low satisfaction, high overtime, no recent promotions")
    
#     # ========== CUSTOM REPORTS ==========
#     if match_phrases(["report", "analysis", "breakdown"], question_lower):
#         if match_phrases(["diversity"], question_lower):
#             diversity = df.groupby(['Department', 'Gender']).size().unstack()
#             return "Diversity Report:\n" + diversity.to_string()
        
#         if match_phrases(["compensation"], question_lower):
#             return "Compensation Report:\n" + df.groupby(['Department', 'Job_Title'])['Monthly_Salary'].describe().to_string()
    
#     # ========== FALLBACK ==========
#     suggestions = [
#         "Try asking about compensation, performance, or workforce analytics",
#         "I can provide reports on diversity, turnover, or department metrics",
#         "Ask about specific employees, open positions, or HR policies",
#         "Need trend analysis? Ask about changes over time in any metric"
#     ]
#     return (f"I couldn't find an answer for that specific question. {np.random.choice(suggestions)}")