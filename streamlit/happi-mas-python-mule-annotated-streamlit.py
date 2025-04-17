# happi-mas-python-mule-annotated-streamlit.py
# Streamlit GUI for Multi-Agent System (Mule-powered CustomAgent & Agentforce integration)
# The 4 properties have been extracted out and will need to be entered into Streamlit separately.
# Think of "import" like grabbing a toolkit. 
# These toolkits let us do things like send messages to the internet (requests), build a web app (streamlit),
# generate random IDs (uuid), and work with structured text (JSON).
import requests
import streamlit as st
import uuid
import json

# These are web addresses where we send our chat questions or support queries.
# LLM powered by Mule answers general questions. The other three are for talking to Salesforce Agentforce support.
# We've now moved them to st.secrets so they can be injected securely via Streamlit Cloud.
MULE_AICHAIN_URL = st.secrets["MULE_AICHAIN_URL"]
AGENTFORCE_START_URL = st.secrets["AGENTFORCE_START_URL"]
AGENTFORCE_CONTINUE_URL = st.secrets["AGENTFORCE_CONTINUE_URL"]
AGENTFORCE_END_URL = st.secrets["AGENTFORCE_END_URL"]

# This is a list of words. If a user types one of these, it means they want support.
# We'll then switch them over to the Agentforce specialist bot.
ESCALATION_KEYWORDS = ["support", "help", "issue", "problem", "troubleshoot", "fix", "case status", "cases"]

# Sidebar message. This shows a fixed message on the side of the screen.
# No need for fancy images—just a clean label.
with st.sidebar:
    st.markdown(
        """
        <div style='text-align: center; margin-top: 10px; font-weight: bold; font-size: 16px;'>
            Autonomous LLM Powered Multi-agent System
        </div>
        """,
        unsafe_allow_html=True
    )
    # When clicked, this gives the user some helpful info about what this chatbot does.
    with st.expander("ℹ️ What is this?"):
        st.markdown("""
        This is a multi-agent chatbot interface.  
        - **CustomAgent** handles general queries  
        - **Agentforce** connects to a Salesforce specialist  
        Type keywords like *help* or *issue* to trigger escalation.
        """)

# -----------------------------------
# A function in Python is a reusable block of code. 
# "def" stands for define. So we're *defining* a function here.
# This one sends the user's question to the LLM chatbot via Mule  and returns the reply.
def chat_with_customagent(user_input):
    try:
        res = requests.post(MULE_AICHAIN_URL, json={"prompt": user_input})
        res.raise_for_status()
        return res.json().get("response", "⚠️ No valid response from LLM.")
    except Exception as e:
        return f"🚨 Error from Mule LLM: {e}"

# This function starts a new support session with Agentforce.
def start_agentforce_session():
    try:
        print("[DEBUG] Starting Agentforce session...")
        res = requests.post(AGENTFORCE_START_URL)
        print(f"[DEBUG] Raw response text: {res.text}")
        res.raise_for_status()
        session_id = res.json().get("payload", {}).get("sessionId")
        print(f"[DEBUG] Received Agentforce sessionId: {session_id}")
        return session_id
    except Exception as e:
        print(f"[DEBUG] Agentforce session error: {e}")
        return None

# This function sends a question to Agentforce (like: "what’s the status of my case?")
# and gets the AI’s reply.
def continue_agentforce_session(session_id, prompt):
    try:
        print(f"[DEBUG] Sending prompt to Agentforce: {prompt} | session_id={session_id}")
        payload = {"sessionId": session_id, "prompt": prompt}
        res = requests.post(AGENTFORCE_CONTINUE_URL, json=payload)
        res.raise_for_status()
        return res.json().get("payload", "⚠️ No valid response from Agentforce.")
    except Exception as e:
        print(f"[DEBUG] Agentforce continue error: {e}")
        return f"⚠️ Agentforce error: {e}"

# This one tries to close the support session when we're done.
def end_agentforce_session(session_id):
    try:
        requests.post(AGENTFORCE_END_URL, json={"sessionId": session_id})
    except:
        pass  # If it fails, just move on—no big deal

# -----------------------------------
# Now comes the *main function*. This is where everything comes together.
# Think of this as the "director" that tells all the other functions when to run.
def main():
    print("[INFO] Starting Streamlit multi-agent app...")

    # Styling: This makes the input box stay "stuck" to the top of the screen like a toolbar.
    st.markdown(
        """
        <style>
        .sticky-prompt {
            position: fixed;
            top: 0;
            width: 100%;
            z-index: 100;
            background-color: white;
            padding: 10px;
            border-bottom: 1px solid #ccc;
        }
        .spacer {
            height: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Chat memory: This saves everything the user and bot say during the chat session.
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "mode" not in st.session_state:
        st.session_state.mode = "general"
    if "agentforce_session_id" not in st.session_state:
        st.session_state.agentforce_session_id = None

    # --- Delayed Escalation Logic ---
    # If the user asks for help, we don't immediately start Agentforce.
    # We first show a confirmation button ("OK - connect me to Agentforce") so they’re sure.
    if st.session_state.get("escalation_triggered") and not st.session_state.get("pending_confirmation"):
        user_msg = st.session_state.pop("escalated_input", "")
        st.session_state.chat_history.append({"sender": "System", "message": "Connecting to Agentforce..."})
        session_id = start_agentforce_session()
        if session_id:
            st.session_state.agentforce_session_id = session_id
            st.session_state.chat_history.append({"sender": "System", "message": "Agentforce connected. Specialist ready."})
            if user_msg:
                response = continue_agentforce_session(session_id, user_msg)
                st.session_state.chat_history.append({"sender": "Agentforce", "message": response})
        else:
            st.session_state.chat_history.append({"sender": "System", "message": "⚠️ Agentforce connection failed."})
        st.session_state.pop("escalation_triggered", None)
        st.rerun()

    # --- Chat Input Box ---
    # This lets the user type their question
    st.markdown('<div class="sticky-prompt">', unsafe_allow_html=True)
    user_input = st.text_input("Your message:", key="user_input")
    if st.button("Send") and user_input:
        st.session_state.chat_history.append({"sender": "User", "message": user_input})

        # If the user types "exit", we stop the session
        if user_input.strip().lower() == "exit":
            if st.session_state.mode == "agentforce":
                end_agentforce_session(st.session_state.agentforce_session_id)
                st.session_state.chat_history.append({"sender": "System", "message": "Agentforce session ended."})
                st.session_state.mode = "general"
                st.session_state.agentforce_session_id = None
            else:
                st.session_state.chat_history.append({"sender": "System", "message": "Session ended."})

        # Handle normal messages
        elif st.session_state.mode == "general":
            if any(keyword in user_input.lower() for keyword in ESCALATION_KEYWORDS):
                st.session_state.chat_history.append({"sender": "CustomAgent", "message": "I'll connect you to a specialist agent."})
                st.session_state.mode = "agentforce"
                st.session_state["pending_confirmation"] = True
                st.session_state["escalated_input"] = user_input
            else:
                response = chat_with_customagent(user_input)
                st.session_state.chat_history.append({"sender": "CustomAgent", "message": response})

        # If in Agentforce mode, forward the message there
        elif st.session_state.mode == "agentforce":
            session_id = st.session_state.agentforce_session_id
            if not session_id:
                st.session_state.chat_history.append({"sender": "System", "message": "Agentforce session not initialized."})
            else:
                response = continue_agentforce_session(session_id, user_input)
                st.session_state.chat_history.append({"sender": "Agentforce", "message": response})
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Show "OK" button if escalation is pending ---
    if st.session_state.get("pending_confirmation"):
        if st.button("OK - Connect me to Agentforce"):
            st.session_state["escalation_triggered"] = True
            st.session_state.pop("pending_confirmation", None)
            st.rerun()

    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

    # --- Display Chat History (newest messages at the top) ---
    for entry in reversed(st.session_state.chat_history):
        sender = entry["sender"]
        message = entry["message"]
        icon = {"CustomAgent": "🤖", "Agentforce": "🛠️", "User": "🧑", "System": "ℹ️"}.get(sender, "💬")
        st.markdown(f"**{icon} {sender}:** {message}")

# --- Entry Point of Program ---
# This line says: only run main() when this file is run directly (not when imported elsewhere).
# If you're new: think of `main()` as the "start" button for your program.
if __name__ == "__main__":
    main()
