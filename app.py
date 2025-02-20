import streamlit as st
import json
import os
import datetime
import uuid
import google.generativeai as genai
from dotenv import load_dotenv
import base64
from fpdf import FPDF
import io

# Load environment variables
load_dotenv()

# Configuration
if "GEMINI_API_KEY" not in os.environ:
    st.error("Please set your GEMINI_API_KEY in .env file or environment variables.")
    api_key = "YOUR_API_KEY_HERE"  # Placeholder - replace with actual key later
else:
    api_key = os.environ["GEMINI_API_KEY"]

# Setup Gemini AI
genai.configure(api_key=api_key)

# Initialize Gemini model
def get_gemini_model():
    # Use the correct model name format
    return genai.GenerativeModel('gemini-1.5-flash')

# File paths
USERS_DATA_FILE = "users_data.json"
CHATS_DATA_FILE = "chats_data.json"

# User authentication
USERS = {
    "Zach": {"password": "ZML", "workouts": []},
    "Mal": {"password": "MMM", "workouts": []}
}

# File operations
def save_users_data():
    """Save user data to a JSON file"""
    with open(USERS_DATA_FILE, "w") as f:
        json.dump(USERS, f, indent=4)

def load_users_data():
    """Load user data from a JSON file"""
    global USERS
    try:
        with open(USERS_DATA_FILE, "r") as f:
            USERS = json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, save the current data
        save_users_data()

def save_chat_history():
    """Save chat history to a JSON file"""
    chat_data = {}
    for username in USERS:
        if f"chat_history_{username}" in st.session_state:
            chat_data[username] = st.session_state[f"chat_history_{username}"]
    
    with open(CHATS_DATA_FILE, "w") as f:
        json.dump(chat_data, f, indent=4)

def load_chat_history():
    """Load chat history from a JSON file"""
    try:
        with open(CHATS_DATA_FILE, "r") as f:
            chat_data = json.load(f)
            
        # Set the chat history for each user
        for username, history in chat_data.items():
            st.session_state[f"chat_history_{username}"] = history
    except FileNotFoundError:
        # If file doesn't exist, create empty chat histories
        for username in USERS:
            if f"chat_history_{username}" not in st.session_state:
                st.session_state[f"chat_history_{username}"] = []
        save_chat_history()

# Load data on startup
try:
    load_users_data()
    load_chat_history()
except Exception as e:
    st.error(f"Error loading data: {e}")

# Initialize session state
def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"
    if "generate_clicked" not in st.session_state:
        st.session_state.generate_clicked = False
    
    # Initialize chat history for each user if not already done
    for username in USERS:
        if f"chat_history_{username}" not in st.session_state:
            st.session_state[f"chat_history_{username}"] = []

def create_workout_pdf(workout_data):
    """Create a PDF with the workout details"""
    pdf = FPDF()
    pdf.add_page()
    
    # Set up the PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Personalized Workout Plan", ln=True, align="C")
    pdf.line(10, 22, 200, 22)
    pdf.ln(5)
    
    # Add metadata
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Type: {workout_data['workout_type']}", ln=True)
    pdf.cell(0, 10, f"Muscle Groups: {', '.join(workout_data['muscle_group'])}", ln=True)
    pdf.cell(0, 10, f"Duration: {workout_data['duration']} minutes", ln=True)
    pdf.ln(5)
    
    # Additional notes
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Additional Notes:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 10, workout_data['notes'])
    pdf.ln(5)
    
    # Main workout content
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Workout Details", ln=True)
    pdf.ln(2)
    
    # We need to process the markdown content for the PDF
    content_lines = workout_data['content'].split('\n')
    current_font = ""
    
    for line in content_lines:
        # Handle headers
        if line.startswith('# '):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, line[2:], ln=True)
        elif line.startswith('## '):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, line[3:], ln=True)
        elif line.startswith('### '):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, line[4:], ln=True)
        # Handle bold text
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 10, line.strip('*'), ln=True)
        # Handle list items
        elif line.startswith('- ') or line.startswith('* '):
            pdf.set_font("Arial", "", 10)
            pdf.cell(5, 10, "•", ln=0)
            pdf.cell(0, 10, line[2:], ln=True)
        # Handle normal text
        elif line.strip():
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 10, line)
        # Add spacing for empty lines
        else:
            pdf.ln(5)
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.cell(0, 10, "AI Fitness Trainer", ln=True, align="C")
    
    return pdf.output(dest="S").encode("latin1")

def get_pdf_download_link(pdf_bytes, filename="workout.pdf"):
    """Generate a download link for the PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Download PDF</a>'
    return href

def generate_workout(workout_type, muscle_group, workout_duration, additional_notes):
    """Generate workout using Gemini AI"""
    model = get_gemini_model()
    
    prompt = f"""
    Act as a professional fitness trainer. Generate a detailed workout plan with the following specifications:
    - Workout Type: {workout_type}
    - Target Muscle Group: {muscle_group}
    - Duration: {workout_duration} minutes

- Additional Notes: {additional_notes}
    
    Structure the workout with:
    1. A brief warm-up (2-5 minutes)
    2. Main workout section with specific exercises (sets, reps, rest periods)
    3. Cool down/stretching (2-3 minutes)
    
    Format each exercise as:
    - Exercise Name: [name]
    - Sets: [number]
    - Reps: [number] or Duration: [time]
    - Rest: [time]
    - Notes: [form tips, intensity recommendations]
    
    Include information on proper form and provide modifications for different fitness levels.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating workout: {str(e)}"

def chat_with_fitness_coach(user_query, chat_history):
    """Chat with AI fitness coach using Gemini"""
    model = get_gemini_model()
    
    # Format the chat history for context
    formatted_history = "\n".join([f"{'User' if i % 2 == 0 else 'Coach'}: {msg}" 
                                    for i, msg in enumerate(chat_history)])
    
    prompt = f"""
    You are a knowledgeable and supportive fitness coach named Coach Alex. 
    You provide scientifically accurate fitness and nutrition advice while being encouraging and motivating.
    
    Previous conversation:
    {formatted_history}
    
    User's new question: {user_query}
    
    Respond in a friendly, professional manner. Include relevant scientific information when appropriate,
    but explain concepts in accessible language. If you don't know something, admit it rather than providing
    potentially harmful advice. If asked about specific medical conditions, recommend consulting a healthcare provider.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error communicating with fitness coach: {str(e)}"

def save_workout(username, workout_data):
    """Save workout to user's history"""
    workout_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    workout_entry = {
        "id": workout_id,
        "timestamp": timestamp,
        "data": workout_data
    }
    
    USERS[username]["workouts"].append(workout_entry)
    save_users_data()
    return workout_id

def login_page():
    st.title("AI Fitness Trainer Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.current_page = "home"
                st.rerun()
            else:
                st.error("Invalid username or password")

def navigation():
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Home"):
            st.session_state.current_page = "home"
            st.session_state.generate_clicked = False
            st.rerun()
    
    with col2:
        if st.button("Generate Workout"):
            st.session_state.current_page = "generate_workout"
            st.session_state.generate_clicked = False
            st.rerun()
    
    with col3:
        if st.button("Workout History"):
            st.session_state.current_page = "workout_history"
            st.session_state.generate_clicked = False
            st.rerun()
    
    with col4:
        if st.button("Fitness Coach"):
            st.session_state.current_page = "fitness_coach"
            st.session_state.generate_clicked = False
            st.rerun()
    
    st.divider()

def home_page():
    st.title(f"Welcome, {st.session_state.username}!")
    
    st.write("### AI Fitness Trainer Dashboard")
    st.write("""
    This app helps you create personalized workouts and provides fitness guidance.
    
    - **Generate Workout**: Create a custom workout based on your preferences
    - **Workout History**: View your saved workout routines
    - **Fitness Coach**: Chat with our AI fitness coach for advice and tips
    
    Select an option from the navigation menu above to get started.
    """)
    
    # Display some workout stats
    if len(USERS[st.session_state.username]["workouts"]) > 0:
        st.write(f"You have {len(USERS[st.session_state.username]['workouts'])} saved workouts.")
        
        last_workout = USERS[st.session_state.username]["workouts"][-1]
        st.write(f"Your last workout was on {last_workout['timestamp']}.")

def generate_workout_page():
    st.title("Generate Custom Workout")
    
    with st.form("workout_form"):
        workout_type = st.selectbox(
            "Workout Type",
            ["Strength Training", "Cardio", "HIIT", "Yoga", "Calisthenics", "Pilates", "Circuit Training"]
        )
        
        muscle_group = st.multiselect(
            "Target Muscle Groups",
            ["Full Body", "Upper Body", "Lower Body", "Core", "Back", "Chest", "Arms", "Shoulders", "Legs", "Glutes"]
        )
        
        workout_duration = st.slider("Workout Duration (minutes)", 10, 120, 30, 5)
        
        additional_notes = st.text_area(
            "Additional Notes",
            "Include any injuries, equipment available, fitness level, or goals."
        )
        
        generate_button = st.form_submit_button("Generate Workout")
    
    # Handle generate button click
    if generate_button and not st.session_state.generate_clicked:
        st.session_state.generate_clicked = True
        
        with st.spinner("Generating your personalized workout..."):
            muscle_group_str = ", ".join(muscle_group) if muscle_group else "Full Body"
            workout_content = generate_workout(
                workout_type, muscle_group_str, workout_duration, additional_notes
            )
            
            # Save workout data in session state
            st.session_state.current_workout = {
                "workout_type": workout_type,
                "muscle_group": muscle_group,
                "duration": workout_duration,
                "notes": additional_notes,
                "content": workout_content
            }

    # Display the workout if available
    if st.session_state.get("current_workout"):
        workout_data = st.session_state.current_workout
        
        st.subheader("Your Personalized Workout")
        st.markdown(workout_data["content"])
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Save to History"):
                workout_id = save_workout(st.session_state.username, workout_data)
                st.success(f"Workout saved to your history! ID: {workout_id[:8]}")
        
        with col2:
            # Create PDF for download
            try:
                pdf_bytes = create_workout_pdf(workout_data)
                st.markdown(
                    get_pdf_download_link(pdf_bytes, f"workout_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"),
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Error creating PDF: {str(e)}")
             
            # Text download button
            workout_text = workout_data["content"]  # Get the workout content
            st.download_button(
                label="Download as Text",
                data=workout_text,
                file_name=f"workout_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
            
def workout_history_page():
    st.title("Your Workout History")
    
    user_workouts = USERS[st.session_state.username]["workouts"]
    
    if not user_workouts:
        st.info("You haven't saved any workouts yet. Generate a workout to get started!")
        return
    
    # Display workouts in reverse chronological order
    for i, workout in enumerate(reversed(user_workouts)):
        with st.expander(f"Workout from {workout['timestamp']}"):
            workout_data = workout["data"]
            
            st.write(f"**Type:** {workout_data['workout_type']}")
            st.write(f"**Muscle Groups:** {', '.join(workout_data['muscle_group'])}")
            st.write(f"**Duration:** {workout_data['duration']} minutes")
            
            st.markdown("### Workout Details")
            st.markdown(workout_data['content'])
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                # Create PDF for download
                try:
                    pdf_bytes = create_workout_pdf(workout_data)
                    st.markdown(
                        get_pdf_download_link(pdf_bytes, f"workout_{workout['id'][:8]}.pdf"),
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.error(f"Error creating PDF: {str(e)}")
                
            with col2:
                # Text download button
                workout_text = workout_data["content"]  # Get the workout content
                st.download_button(
                    label="Download as Text",
                    data=workout_text,
                    file_name=f"workout_{workout['id'][:8]}.txt",
                    mime="text/plain"
                )

def fitness_coach_page():
    st.title("AI Fitness Coach")
    st.write("Ask me anything about fitness, nutrition, or workout techniques!")
    
    # Get the current user's chat history
    chat_history_key = f"chat_history_{st.session_state.username}"
    
    # Display chat history with better formatting
    st.container(height=400, border=True)
    with st.container():
        for i, message in enumerate(st.session_state[chat_history_key]):
            if i % 2 == 0:  # User message
                st.markdown(f"<div style='background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:10px;'><strong>You:</strong> {message}</div>", unsafe_allow_html=True)
            else:  # Coach response
                st.markdown(f"<div style='background-color:#e6f7ff; padding:10px; border-radius:5px; margin-bottom:10px;'><strong>Coach Alex:</strong> {message}</div>", unsafe_allow_html=True)
    
    # Chat input
    with st.form(key="chat_form"):
        user_query = st.text_input("Your question:", key="fitness_query")
        submit_chat = st.form_submit_button("Ask Coach")
    
    if submit_chat and user_query:
        # Add user query to chat history
        st.session_state[chat_history_key].append(user_query)
        
        with st.spinner("Coach Alex is thinking..."):
            # Get response from AI
            coach_response = chat_with_fitness_coach(
                user_query, 
                st.session_state[chat_history_key][:-1]  # Exclude current query
            )
            
            # Add coach response to chat history
            st.session_state[chat_history_key].append(coach_response)
            
            # Save updated chat history
            save_chat_history()
        
        # Clear input and refresh to show new messages
        st.rerun()
    
    # Add option to clear chat history
    if st.button("Clear Chat History"):
        st.session_state[chat_history_key] = ``
        save_chat_history()
        st.success("Chat history cleared!")
        st.rerun()

def main():
    st.set_page_config(
        page_title="AI Fitness Trainer",
        page_icon="💪",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Display appropriate page based on login status
    if not st.session_state.logged_in:
        login_page()
    else:
        # Show logout in sidebar
        logout_button()
        
        # Display user info in sidebar
        st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
        
        # Navigation
        navigation()
        
        # Page routing
        if st.session_state.current_page == "home":
            home_page()
        elif st.session_state.current_page == "generate_workout":
            generate_workout_page()
        elif st.session_state.current_page == "workout_history":
            workout_history_page()
        elif st.session_state.current_page == "fitness_coach":
            fitness_coach_page()
        else:
            home_page()

if __name__ == "__main__":
    main()
