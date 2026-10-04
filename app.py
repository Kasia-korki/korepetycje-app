import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# 🔹 ID kalendarza OKIENEK (Korepetycje)
CALENDAR_OKIENKA = "b30c87e78327bea962c617ff8642aa691b374d2444dc26d86bb8c5bfa42887ab@group.calendar.google.com"

# -----------------------------------------
# GOOGLE LOGIN – tylko do rezerwacji
# -----------------------------------------
def google_login():
    import json
    creds_data = json.loads(st.secrets["credentials_json"])
    flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)

    creds = flow.run_local_server(port=0)
    return creds

# -----------------------------------------
# CREATE EVENT – zapis do głównego kalendarza
# -----------------------------------------
def create_event(creds, summary, start_time, end_time):
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "Europe/Warsaw"},
        "end": {"dateTime": end_time, "timeZone": "Europe/Warsaw"},
    }
    event = service.events().insert(calendarId="primary", body=event).execute()
    return event["id"]

# -----------------------------------------
# DELETE EVENT – z głównego kalendarza
# -----------------------------------------
def delete_event(creds, event_id):
    service = build("calendar", "v3", credentials=creds)
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except:
        pass

# -----------------------------------------
# UI + CSS
# -----------------------------------------
st.set_page_config(page_title="Rezerwacja zajęć")
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("<h1 style='color:#2f6f3e;'>Rezerwacja zajęć</h1>", unsafe_allow_html=True)

with col2:
    st.image("avatar.png", width=100)

st.markdown("""
<style>
img.avatar:hover {
    transform: scale(1.35);
    box-shadow: 0px 8px 26px rgba(0,150,0,0.55);
}
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
[data-testid="stAppViewContainer"] { background-color: palegreen2 !important; }
[data-testid="stSidebar"] { background-color: #e8f5e9 !important; }
h1, h2, h3 { color: #2f6f3e !important; font-weight: 600; }
div.stButton > button {
    background-color: #4caf50; color: white; border-radius: 10px;
    padding: 10px 20px; font-size: 18px; border: none;
}
div[data-testid="stAlert"] {
    background-color: #c8f7c5 !important; color: #2f6f3e !important;
    border-left: 5px solid #4caf50 !important;
}
div[data-testid="stAlert"] p { color: #2f6f3e !important; font-weight: 600; }
div.stButton > button:hover { background-color: #3e8e41; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------
# TRYB
# -----------------------------------------
tryb = st.sidebar.radio("Tryb:", ["Uczeń", "Administrator"])

# -----------------------------------------
# WCZYTANIE CSV (rezerwacje) — NAIVE DATETIME
# -----------------------------------------
try:
    occupied = pd.read_csv("occupied.csv")
    occupied["start"] = pd.to_datetime(occupied["start"])
    occupied["end"] = pd.to_datetime(occupied["end"])
    if "event_id" not in occupied.columns:
        occupied["event_id"] = ""
except:
    occupied = pd.DataFrame(columns=[
        "date", "start", "end", "level", "duration", "price",
        "name", "topic", "event_id"
    ])

# -----------------------------------------
# OKIENKA Z PUBLICZNEGO KALENDARZA „Korepetycje”
# -----------------------------------------
from google.oauth2 import service_account

def get_windows_from_calendar():
    import json

    # Wczytanie service account z sekretów Streamlit Cloud
    sa_data = json.loads(st.secrets["service_account_json"])
    creds = service_account.Credentials.from_service_account_info(
        sa_data,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
    )

    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId=CALENDAR_OKIENKA,
        timeMin=now,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    windows = []

    for event in events:
        summary = event.get("summary", "")
        if "Okienko" in summary:
            start_dt = datetime.fromisoformat(event["start"]["dateTime"]).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(event["end"]["dateTime"]).replace(tzinfo=None)
            windows.append((start_dt, end_dt))

    return windows


# Pobranie okienek
windows = get_windows_from_calendar()

# Obsługa braku okienek
if len(windows) == 0:
    st.error("Brak dostępnych okienek w kalendarzu Korepetycje.")
    st.stop()

# Lista dni
days = sorted(list(set([w[0].strftime("%Y-%m-%d") for w in windows])))

# -----------------------------------------
# PANEL UCZNIA
# -----------------------------------------
if tryb == "Uczeń":

    st.subheader("Formularz rezerwacji")

    day = st.selectbox("Wybierz dzień:", days)

    selected_windows = [w for w in windows if w[0].strftime("%Y-%m-%d") == day]

    duration = st.selectbox("Długość zajęć (minuty):", [60, 90, 120])

    # DZIELENIE OKIENEK NA WOLNE FRAGMENTY
    free_windows = []

    for w_start, w_end in selected_windows:
        fragments = [(w_start, w_end)]

        for _, row in occupied.iterrows():
            if row["date"] != day:
                continue

            occ_start = row["start"]
            occ_end = row["end"]

            new_fragments = []

            for f_start, f_end in fragments:

                if f_end <= occ_start or f_start >= occ_end:
                    new_fragments.append((f_start, f_end))
                else:
                    if f_start < occ_start:
                        new_fragments.append((f_start, occ_start))
                    if f_end > occ_end:
                        new_fragments.append((occ_end, f_end))

            fragments = new_fragments

        free_windows.extend(fragments)

    # GENEROWANIE GODZIN STARTU
    times = []

    for f_start, f_end in free_windows:
        current = f_start
        while current + timedelta(minutes=duration) <= f_end:
            times.append(current.strftime("%H:%M"))
            current += timedelta(minutes=15)

    if len(times) == 0:
        st.error("Brak dostępnych godzin w tym dniu.")
        st.stop()

    start_time = st.selectbox("Godzina rozpoczęcia:", times)

    level = st.selectbox("Poziom zajęć:", ["Podstawówka", "Podstawa", "Rozszerzenie"])
    prices = {"Podstawówka": 70, "Podstawa": 80, "Rozszerzenie": 100}
    total_price = prices[level] * (duration / 60)

    st.info(f"Cena zajęć: {total_price} zł")

    name = st.text_input("Imię ucznia:")
    topic = st.text_input("Temat zajęć:")

    if st.button("Rezerwuj"):
        start_dt = datetime.strptime(f"{day} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)
        final_end = end_dt + timedelta(minutes=15)

        conflict = occupied[
            (occupied["date"] == day) &
            (occupied["start"] < final_end) &
            (occupied["end"] > start_dt)
        ]

        if len(conflict) > 0:
            st.error("Ten zakres jest już zajęty!")
        else:
            creds = google_login()
            event_id = create_event(
                creds,
                summary=f"Korepetycje: {name} – {topic}",
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat()
            )

            new_row = pd.DataFrame({
                "date": [day],
                "start": [start_dt],
                "end": [final_end],
                "level": [level],
                "duration": [duration],
                "price": [total_price],
                "name": [name],
                "topic": [topic],
                "event_id": [event_id]
            })

            occupied = pd.concat([occupied, new_row], ignore_index=True)
            occupied.to_csv("occupied.csv", index=False)

            st.success("Zarezerwowano!")

# -----------------------------------------
# PANEL ADMINISTRATORA
# -----------------------------------------
if tryb == "Administrator":

    st.subheader("Panel administratora")

    access_code = st.text_input("Podaj kod dostępu:", type="password")

    if access_code != "123babajagapatrzy":
        st.warning("Wpisz poprawny kod, aby zobaczyć panel administratora.")
    else:
        st.success("Kod poprawny. Witaj w panelu administratora!")

        st.subheader("Wszystkie rezerwacje")
        if len(occupied) == 0:
            st.info("Brak rezerwacji.")
        else:
            st.dataframe(occupied)

            st.subheader("Usuń rezerwację")
            index_to_delete = st.number_input(
                "Podaj numer wiersza do usunięcia:",
                min_value=0,
                max_value=len(occupied) - 1,
                step=1
            )

            if st.button("Usuń wybraną rezerwację"):
                event_id = occupied.loc[index_to_delete, "event_id"]

                if isinstance(event_id, str) and event_id.strip() != "":
                    creds = google_login()
                    delete_event(creds, event_id)

                occupied = occupied.drop(index_to_delete).reset_index(drop=True)
                occupied.to_csv("occupied.csv", index=False)

                st.success("Rezerwacja została usunięta (CSV + Google Calendar).")
                st.rerun()
