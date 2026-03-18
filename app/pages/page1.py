import streamlit as st
import requests
import json

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in first!")
    st.switch_page("app.py") 
    st.stop()
    
st.sidebar.write(f"Logged in as: {st.session_state['logged_in']}")
if st.sidebar.button("Log Out"):
    del st.session_state["logged_in"]
    st.switch_page("app.py")
st.title("Model Operations Dashboard")

tab_heart, tab_xray = st.tabs(["Heart", "Xray"])
# Make sure to update this URL every time you restart Colab!
API_URL = "https://unlimp-augustus-labouredly.ngrok-free.dev/"

st.set_page_config(
    page_title="Healthcare SISA System",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Healthcare Test Result Predictor")
st.caption("Powered by BERT + SISA Machine Unlearning")

tab1, tab2 = st.tabs(["🔍 Predict", "🗑️ Unlearn"])


# ==============================================================================
# TAB 1 — PREDICTION
# ==============================================================================

with tab1:
    st.header("Predict Patient Test Result")
    st.info("Fill in the patient details below. BERT will predict the test result "
            "using an ensemble of all trained shard models.")

    col1, col2 = st.columns(2)

    with col1:
        age       = st.number_input("Age",            min_value=1,  max_value=120, value=45)
        gender    = st.selectbox("Gender",            ["Male", "Female"])
        blood     = st.selectbox("Blood Type",        ["A+","A-","B+","B-","O+","O-","AB+","AB-"])
        condition = st.selectbox("Medical Condition", ["Cancer","Diabetes","Hypertension",
                                                       "Obesity","Asthma","Arthritis"])

    with col2:
        admission = st.selectbox("Admission Type",    ["Elective", "Emergency", "Urgent"])
        medication= st.selectbox("Medication",        ["Aspirin","Ibuprofen","Paracetamol",
                                                       "Metformin","Penicillin","Lipitor"])
        insurance = st.selectbox("Insurance Provider",["Aetna","Blue Cross","Cigna",
                                                       "Medicare","UnitedHealthcare"])

    if st.button("🔍 Predict Test Result", use_container_width=True):
        payload = {
            "Age": age, "Gender": gender, "Blood Type": blood,
            "Medical Condition": condition, "Admission Type": admission,
            "Medication": medication, "Insurance Provider": insurance,
        }
        with st.spinner("Running BERT inference across all shards..."):
            try:
                resp = requests.post(f"{API_URL}/predict", json=payload, timeout=60)
                resp.raise_for_status()
                result = resp.json()["prediction"]

                color_map = {
                    "Normal":       "green",
                    "Abnormal":     "red",
                    "Inconclusive": "orange",
                }
                color = color_map.get(result, "blue")
                st.markdown(f"## Predicted Result: :{color}[{result}]")

                if result == "Normal":
                    st.success("✅ Test results appear Normal.")
                elif result == "Abnormal":
                    st.error("🚨 Test results appear Abnormal. Please consult a doctor.")
                else:
                    st.warning("⚠️ Test results are Inconclusive. Further tests may be needed.")

            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to the API. Make sure Colab is running and ngrok is active.")
            except Exception as e:
                st.error(f"Error: {e}")


# ==============================================================================
# TAB 2 — UNLEARNING  (UID-based)
# ==============================================================================

with tab2:
    st.header("Request Data Unlearning")
    st.info(
        "Enter a Patient UID (format: **PID-XXXXXXXX**) to request removal of their "
        "data from the trained model. The system will:\n"
        "1. Check if the UID exists in the dataset\n"
        "2. If found, run SISA unlearning on the affected shards only\n"
        "3. Update the model checkpoints on Google Drive"
    )

    # ── Step 1: Check UID ─────────────────────────────────────────────────────
    st.subheader("Step 1 — Verify Patient UID")

    uid_input = st.text_input(
        "Enter Patient UID",
        placeholder="e.g. PID-3F8A92C1",
        max_chars=12,
    ).strip().upper()

    check_clicked = st.button("🔎 Check UID", use_container_width=True)

    if check_clicked:
        if not uid_input:
            st.warning("Please enter a UID first.")
        else:
            with st.spinner(f"Looking up {uid_input}..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/check_uid",
                        json={"uid": uid_input},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if data["found"]:
                        st.success(f"✅ UID **{uid_input}** found in the dataset.")
                        st.write(f"**Patient Name:** {data['name']}")

                        st.write("**Admission records:**")
                        st.table(data["admissions"])

                        # Store UID in session state for Step 2
                        st.session_state["verified_uid"]  = uid_input
                        st.session_state["verified_name"] = data["name"]

                    else:
                        st.error(f"❌ {data['message']}")
                        st.session_state.pop("verified_uid",  None)
                        st.session_state.pop("verified_name", None)

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the API.")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # ── Step 2: Unlearn (only shown after a successful UID check) ─────────────
    st.subheader("Step 2 — Confirm Unlearning")

    if "verified_uid" in st.session_state:
        uid  = st.session_state["verified_uid"]
        name = st.session_state["verified_name"]

        st.warning(
            f"You are about to permanently remove **{name}** (UID: `{uid}`) "
            f"from the trained model. This will retrain the affected shards. "
            f"This action cannot be undone."
        )

        confirm = st.checkbox(f"I confirm I want to unlearn data for {name} ({uid})")

        if st.button("🚨 Confirm & Unlearn", disabled=not confirm, use_container_width=True):
            with st.spinner(
                f"Running SISA unlearning for {uid}... "
                f"This may take several minutes depending on which slice is affected."
            ):
                try:
                    resp = requests.post(
                        f"{API_URL}/unlearn",
                        json={"uid": uid},
                        timeout=600,   # unlearning can take a few minutes
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if result["found"]:
                        st.success(result["message"])
                        st.balloons()
                    else:
                        st.info(result["message"])

                    # Clear session state after unlearning
                    st.session_state.pop("verified_uid",  None)
                    st.session_state.pop("verified_name", None)

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the API.")
                except requests.exceptions.Timeout:
                    st.warning(
                        "⏳ The request timed out — unlearning is still running in Colab. "
                        "Check the Colab output to confirm it completed."
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("👆 Complete Step 1 first by entering and verifying a UID.")
