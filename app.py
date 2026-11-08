import calendar
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


# ============================================================
# KONFIGURACJA
# ============================================================

CALENDAR_ID = "b30c87e78327bea962c617ff8642aa691b374d2444dc26d86bb8c5bfa42887ab@group.calendar.google.com"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
WARSAW = ZoneInfo("Europe/Warsaw")

# Przerwa po korepetycjach, która również blokuje termin.
BUFFER_MINUTES = 15

PRICES = {
    "Podstawówka": 70,
    "Podstawa": 80,
    "Rozszerzenie": 100,
}

POLISH_MONTHS = [
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad",
    "grudzień",
]

WEEKDAYS = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"]


# ============================================================
# GOOGLE CALENDAR
# ============================================================

def get_calendar_service():
    """Tworzy połączenie z Google Calendar na podstawie Streamlit Secrets."""
    sa_data = json.loads(st.secrets["service_account_json"])
    creds = service_account.Credentials.from_service_account_info(
        sa_data,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_calendar_datetime(value):
    """
    Zamienia czas z Google Calendar na lokalny, naiwny datetime
    w strefie Europe/Warsaw.
    Obsługuje też wydarzenia całodniowe.
    """
    if value.get("dateTime"):
        dt = datetime.fromisoformat(value["dateTime"])
        if dt.tzinfo is not None:
            dt = dt.astimezone(WARSAW).replace(tzinfo=None)
        return dt

    if value.get("date"):
        day = datetime.strptime(value["date"], "%Y-%m-%d").date()
        return datetime.combine(day, datetime.min.time())

    return None


def get_calendar_data():
    """
    Pobiera wydarzenia z kalendarza.

    Wydarzenia, których tytuł zawiera „Okienko”, oznaczają dostępność.
    KAŻDE inne wydarzenie blokuje swój termin.
    Rezerwacje z aplikacji blokują dodatkowo 15 minut przerwy.
    """
    service = get_calendar_service()
    now = datetime.now(WARSAW)
    time_min = (now - timedelta(days=1)).isoformat()

    windows = []
    busy_events = []
    page_token = None

    while True:
        response = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            maxResults=2500,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        ).execute()

        for event in response.get("items", []):
            if event.get("status") == "cancelled":
                continue

            start_dt = parse_calendar_datetime(event.get("start", {}))
            end_dt = parse_calendar_datetime(event.get("end", {}))

            if start_dt is None or end_dt is None or end_dt <= start_dt:
                continue

            summary = event.get("summary", "")
            if "okienko" in summary.casefold():
                windows.append((start_dt, end_dt))
            else:
                # Wydarzenia z aplikacji otrzymują 15 minut przerwy.
                if summary.startswith("Korepetycje:"):
                    end_dt += timedelta(minutes=BUFFER_MINUTES)

                busy_events.append((start_dt, end_dt))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return windows, busy_events


def create_event(summary, start_dt, end_dt):
    """Dodaje potwierdzone korepetycje do Google Calendar."""
    service = get_calendar_service()

    start_aware = start_dt.replace(tzinfo=WARSAW)
    end_aware = end_dt.replace(tzinfo=WARSAW)

    event = {
        "summary": summary,
        "start": {
            "dateTime": start_aware.isoformat(),
            "timeZone": "Europe/Warsaw",
        },
        "end": {
            "dateTime": end_aware.isoformat(),
            "timeZone": "Europe/Warsaw",
        },
    }

    created = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event,
    ).execute()

    return created["id"]


# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================

def subtract_busy_events(windows, busy_events, selected_day):
    """Odejmuje zajęte terminy od dostępnych okienek w wybranym dniu."""
    free_windows = []

    for window_start, window_end in windows:
        if window_start.strftime("%Y-%m-%d") != selected_day:
            continue

        fragments = [(window_start, window_end)]

        for busy_start, busy_end in busy_events:
            new_fragments = []

            for fragment_start, fragment_end in fragments:
                # Brak nakładania się wydarzeń.
                if fragment_end <= busy_start or fragment_start >= busy_end:
                    new_fragments.append((fragment_start, fragment_end))
                else:
                    if fragment_start < busy_start:
                        new_fragments.append((fragment_start, busy_start))
                    if fragment_end > busy_end:
                        new_fragments.append((busy_end, fragment_end))

            fragments = new_fragments

        free_windows.extend(fragments)

    return free_windows


def get_available_start_times(free_windows, duration):
    """Tworzy listę godzin rozpoczęcia zajęć, co 15 minut."""
    times = []

    for window_start, window_end in free_windows:
        current = window_start

        while current + timedelta(minutes=duration) <= window_end:
            times.append(current.strftime("%H:%M"))
            current += timedelta(minutes=15)

    return sorted(set(times))


# ============================================================
# WYGLĄD APLIKACJI
# ============================================================

st.set_page_config(
    page_title="Rezerwacja zajęć",
    page_icon="📚",
    layout="wide",
)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(
        "<h1 style='color:#2f6f3e;'>Rezerwacja zajęć</h1>",
        unsafe_allow_html=True,
    )

with col2:
    try:
        st.image("avatar.png", width=100)
    except Exception:
        pass

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] {
        background-color: #e8f5e9 !important;
    }

    h1, h2, h3 {
        color: #2f6f3e !important;
        font-weight: 600;
    }

    div.stButton > button {
        background-color: #4caf50;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 18px;
        border: none;
    }

    div.stButton > button:hover {
        background-color: #3e8e41;
        color: white;
    }

    div[data-testid="stAlert"] {
        background-color: #c8f7c5 !important;
        color: #2f6f3e !important;
        border-left: 5px solid #4caf50 !important;
    }

    div[data-testid="stAlert"] p {
        color: #2f6f3e !important;
        font-weight: 600;
    }

    .calendar-empty {
        height: 52px;
    }

    .calendar-unavailable {
        height: 52px;
        background-color: #fff;
        border: 1px solid #eee;
        color: #aaa;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        box-sizing: border-box;
    }

    .calendar-button div.stButton > button {
        height: 52px !important;
        min-height: 52px !important;
        padding: 0 !important;
        border-radius: 0 !important;
        border: 1px solid #ccc !important;
        background-color: #5ac252 !important;
        color: #000 !important;
        font-size: 18px !important;
        font-weight: 500 !important;
    }

    .calendar-button div.stButton > button:hover {
        background-color: #4caf50 !important;
        color: white !important;
    }

    .calendar-weekday {
        text-align: center;
        font-weight: 600;
        color: #555;
        padding-bottom: 6px;
        font-size: 14px;
    }

    .calendar-today {
        height: 52px;
        background-color: #067806;
        color: white;
        border: 1px solid #ccc;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        box-sizing: border-box;
    }

    .selected-info {
        margin-top: 15px;
        margin-bottom: 15px;
        color: #2f6f3e;
        font-size: 17px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# POBRANIE AKTUALNYCH DANYCH Z GOOGLE CALENDAR
# ============================================================

try:
    windows, busy_events = get_calendar_data()
except Exception as e:
    st.error(
        "Nie udało się pobrać danych z Google Calendar. "
        "Sprawdź połączenie i konfigurację Secrets."
    )
    st.exception(e)
    st.stop()

if not windows:
    st.error("Brak dostępnych okienek w kalendarzu Korepetycje.")
    st.stop()


# ============================================================
# WYBÓR DNIA
# ============================================================

today = datetime.now(WARSAW).date()
tomorrow = today + timedelta(days=1)

days_with_windows = sorted(
    {
        datetime.strptime(start.strftime("%Y-%m-%d"), "%Y-%m-%d").date()
        for start, end in windows
        if start.date() >= tomorrow
    }
)

if not days_with_windows:
    st.error("Brak dostępnych okienek od jutra.")
    st.stop()

nearest_day = days_with_windows[0]
nearest_day_str = nearest_day.strftime("%Y-%m-%d")

if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = nearest_day.month

if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = nearest_day.year

if "selected_day" not in st.session_state:
    st.session_state.selected_day = nearest_day_str


def select_day(day_string):
    st.session_state.selected_day = day_string


col_prev, col_month, col_next = st.columns([1, 3, 1])

with col_prev:
    if st.button("←", key="previous_month"):
        if st.session_state.calendar_month == 1:
            st.session_state.calendar_month = 12
            st.session_state.calendar_year -= 1
        else:
            st.session_state.calendar_month -= 1
        st.rerun()

with col_month:
    month_name = POLISH_MONTHS[st.session_state.calendar_month - 1]
    st.markdown(
        f"""
        <h3 style="text-align:center;margin-top:5px;margin-bottom:15px;">
            {month_name.capitalize()} {st.session_state.calendar_year}
        </h3>
        """,
        unsafe_allow_html=True,
    )

with col_next:
    if st.button("→", key="next_month"):
        if st.session_state.calendar_month == 12:
            st.session_state.calendar_month = 1
            st.session_state.calendar_year += 1
        else:
            st.session_state.calendar_month += 1
        st.rerun()


year = st.session_state.calendar_year
month = st.session_state.calendar_month

month_calendar = calendar.Calendar(
    firstweekday=calendar.MONDAY
).monthdayscalendar(year, month)

header_cols = st.columns(7, gap="small")

for i, weekday in enumerate(WEEKDAYS):
    with header_cols[i]:
        st.markdown(
            f'<div class="calendar-weekday">{weekday}</div>',
            unsafe_allow_html=True,
        )

for week in month_calendar:
    cols = st.columns(7, gap="small")

    for day_index, day_num in enumerate(week):
        with cols[day_index]:
            if day_num == 0:
                st.markdown(
                    '<div class="calendar-empty"></div>',
                    unsafe_allow_html=True,
                )
                continue

            day_date = datetime(year, month, day_num).date()
            day_string = day_date.strftime("%Y-%m-%d")

            if day_date == today:
                st.markdown(
                    f'<div class="calendar-today">{day_num}</div>',
                    unsafe_allow_html=True,
                )
            elif day_date in days_with_windows and day_date > today:
                st.markdown(
                    '<div class="calendar-button">',
                    unsafe_allow_html=True,
                )
                st.button(
                    str(day_num),
                    key=f"calendar_day_{day_string}",
                    width="stretch",
                    on_click=select_day,
                    args=(day_string,),
                )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="calendar-unavailable">{day_num}</div>',
                    unsafe_allow_html=True,
                )


# ============================================================
# FORMULARZ REZERWACJI
# ============================================================

selected_day = st.session_state.selected_day

try:
    selected_date = datetime.strptime(
        selected_day, "%Y-%m-%d"
    ).date()
except ValueError:
    selected_date = nearest_day
    selected_day = nearest_day_str
    st.session_state.selected_day = nearest_day_str

st.markdown(
    f'<div class="selected-info">Wybrany dzień: '
    f'{selected_date.strftime("%d.%m.%Y")}</div>',
    unsafe_allow_html=True,
)

selected_windows = [
    (start, end)
    for start, end in windows
    if start.strftime("%Y-%m-%d") == selected_day
]

duration = st.selectbox(
    "Długość zajęć (minuty):",
    [60, 90, 120],
)

free_windows = subtract_busy_events(
    selected_windows,
    busy_events,
    selected_day,
)

times = get_available_start_times(free_windows, duration)

if not times:
    st.error("Brak dostępnych godzin w tym dniu.")
    st.stop()

start_time = st.selectbox(
    "Godzina rozpoczęcia:",
    times,
)

level = st.selectbox(
    "Poziom zajęć:",
    list(PRICES.keys()),
)

total_price = PRICES[level] * (duration / 60)

st.info(f"Cena zajęć: {total_price:.0f} zł")

name = st.text_input("Imię ucznia:")
topic = st.text_input("Temat zajęć:")


# ============================================================
# POTWIERDZENIE REZERWACJI
# ============================================================

if st.button("Rezerwuj", key="reserve_button"):
    if not name.strip():
        st.error("Wpisz imię ucznia.")
        st.stop()

    if not topic.strip():
        st.error("Wpisz temat zajęć.")
        st.stop()

    start_dt = datetime.strptime(
        f"{selected_day} {start_time}",
        "%Y-%m-%d %H:%M",
    )
    end_dt = start_dt + timedelta(minutes=duration)
    final_end = end_dt + timedelta(minutes=BUFFER_MINUTES)

    try:
        # Pobieramy kalendarz ponownie tuż przed zapisem.
        # Dzięki temu sprawdzamy także rezerwacje dodane od
        # momentu wyświetlenia formularza.
        latest_windows, latest_busy_events = get_calendar_data()

        # Sprawdzamy, czy wybrana godzina nadal mieści się
        # w którymś z aktualnych okienek.
        inside_window = any(
            window_start <= start_dt
            and end_dt <= window_end
            and window_start.strftime("%Y-%m-%d") == selected_day
            for window_start, window_end in latest_windows
        )

        if not inside_window:
            st.error(
                "To okienko nie jest już dostępne. "
                "Odśwież stronę i wybierz inny termin."
            )
            st.stop()

        # Sprawdzamy kolizję razem z 15-minutową przerwą
        # po rezerwowanych zajęciach.
        conflict = any(
            busy_start < final_end and busy_end > start_dt
            for busy_start, busy_end in latest_busy_events
        )

        if conflict:
            st.error(
                "Ten termin został właśnie zajęty! "
                "Odśwież stronę i wybierz inną godzinę."
            )
            st.stop()

        event_id = create_event(
            f"Korepetycje: {name.strip()} – {topic.strip()}",
            start_dt,
            end_dt,
        )

        st.session_state["reservation_message"] = (
            f"Rezerwacja potwierdzona! "
            f"{selected_date.strftime('%d.%m.%Y')}, "
            f"{start_dt.strftime('%H:%M')} – "
            f"{end_dt.strftime('%H:%M')}. "
            f"Cena: {total_price:.0f} zł."
        )

        # Odświeżenie powoduje ponowne pobranie wydarzeń
        # z Google Calendar. Zajęta godzina znika z listy.
        st.rerun()

    except HttpError as e:
        st.error(f"Google Calendar zwrócił błąd: {e}")
    except Exception as e:
        st.error(f"Nie udało się utworzyć rezerwacji: {e}")
