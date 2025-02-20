import streamlit as st
import json
import os
import datetime
import uuid
import google.generativeai as genai
from dotenv import load_dotenv

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
    return genai.GenerativeModel('models/gemini-2.0-flash')

# User authentication
USERS = {
    "Zach": {"password": "ZML", "workouts": []},
    "Mal": {"password": "MMM", "workouts": []}
}

# File operations
def save_users_data():
    """Save user data to a JSON file"""
    with open("users_data.json", "w") as f:
        json.dump(USERS, f)

def load_users_data():
    """Load user data from a JSON file"""
    global USERS
    try:
        with open("users_data.json", "r") as f:
            USERS = json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, save the current data
        save_users_data()

# Load data on startup
try:
    load_users_data()
except Exception as e:
    st.error(f"Error loading user data: {e}")

# Initialize session state
def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

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
            st.rerun()
    
    with col2:
        if st.button("Generate Workout"):
            st.session_state.current_page = "generate_workout"
            st.rerun()
    
    with col3:
        if st.button("Workout History"):
            st.session_state.current_page = "workout_history"
            st.rerun()
    
    with col4:
        if st.button("Fitness Coach"):
            st.session_state.current_page = "fitness_coach"
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
    
    if generate_button:
        with st.spinner("Generating your personalized workout..."):
            muscle_group_str = ", ".join(muscle_group) if muscle_group else "Full Body"
            workout_content = generate_workout(
                workout_type, muscle_group_str, workout_duration, additional_notes
            )
            
            st.subheader("Your Personalized Workout")
            st.markdown(workout_content)
            
            # Save options
            workout_data = {
                "workout_type": workout_type,
                "muscle_group": muscle_group,
                "duration": workout_duration,
                "notes": additional_notes,
                "content": workout_content
            }
            
            save_col, download_col = st.columns(2)
            
            with save_col:
                if st.button("Save to History"):
                    workout_id = save_workout(st.session_state.username, workout_data)
                    st.success(f"Workout saved to your history! ID: {workout_id[:8]}")
            
            with download_col:
                # Create download button for JSON
                workout_json = json.dumps(workout_data, indent=2)
                st.download_button(
                    label="Download as JSON",
                    data=workout_json,
                    file_name=f"workout_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
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
            st.write(f"**Type:** {workout['data']['workout_type']}")
            st.write(f"**Muscle Groups:** {', '.join(workout['data']['muscle_group'])}")
            st.write(f"**Duration:** {workout['data']['duration']} minutes")
            
            st.markdown("### Workout Details")
            st.markdown(workout['data']['content'])
            
            # Download option
            workout_json = json.dumps(workout['data'], indent=2)
            st.download_button(
                label="Download as JSON",
                data=workout_json,
                file_name=f"workout_{workout['id'][:8]}.json",
                mime="application/json"
            )

def fitness_coach_page():
    st.title("AI Fitness Coach")
    st.write("Ask me anything about fitness, nutrition, or workout techniques!")
    
    # Initialize chat history if not already done
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:  # User message
            st.markdown(f"**You:** {message}")
        else:  # Coach response
            st.markdown(f"**Coach Alex:** {message}")
    
    # Chat input
    user_query = st.text_input("Your question:", key="fitness_query")
    
    if st.button("Ask Coach"):
        if user_query:
            # Add user query to chat history
            st.session_state.chat_history.append(user_query)
            
            with st.spinner("Coach Alex is thinking..."):
                # Get response from AI
                coach_response = chat_with_fitness_coach(
                    user_query, 
                    st.session_state.chat_history[:-1]  # Exclude current query
                )
                
                # Add coach response to chat history
                st.session_state.chat_history.append(coach_response)
            
            # Clear input and refresh to show new messages
            st.rerun()

def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.current_page = "login"
        st.session_state.chat_history = []
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
