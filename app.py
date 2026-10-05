import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import calendar


# =========================================================
# ID KALENDARZA OKIENEK
# =========================================================

CALENDAR_OKIENKA = "b30c87e78327bea962c617ff8642aa691b374d2444dc26d86bb8c5bfa42887ab@group.calendar.google.com"


# =========================================================
# GOOGLE CALENDAR – POŁĄCZENIE
# =========================================================

def get_calendar_service(scopes):
    sa_data = json.loads(
        st.secrets["service_account_json"]
    )

    creds = service_account.Credentials.from_service_account_info(
        sa_data,
        scopes=scopes
    )

    service = build(
        "calendar",
        "v3",
        credentials=creds
    )

    return service


# =========================================================
# CREATE EVENT
# =========================================================

def create_event(summary, start_time, end_time):

    service = get_calendar_service([
        "https://www.googleapis.com/auth/calendar"
    ])

    event = {
        "summary": summary,
        "start": {
            "dateTime": start_time,
            "timeZone": "Europe/Warsaw"
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Europe/Warsaw"
        },
    }

    event = service.events().insert(
        calendarId=CALENDAR_OKIENKA,
        body=event
    ).execute()

    return event["id"]


# =========================================================
# DELETE EVENT
# =========================================================

def delete_event(event_id):

    service = get_calendar_service([
        "https://www.googleapis.com/auth/calendar"
    ])

    try:
        service.events().delete(
            calendarId=CALENDAR_OKIENKA,
            eventId=event_id
        ).execute()

    except:
        pass


# =========================================================
# UI + CSS
# =========================================================

st.set_page_config(
    page_title="Rezerwacja zajęć"
)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(
        "<h1 style='color:#2f6f3e;'>Rezerwacja zajęć</h1>",
        unsafe_allow_html=True
    )

with col2:
    st.image(
        "avatar.png",
        width=100
    )


st.markdown("""
<style>

img.avatar:hover {
    transform: scale(1.35);
    box-shadow: 0px 8px 26px rgba(0,150,0,0.55);
}

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background-color: palegreen2 !important;
}

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

div[data-testid="stAlert"] {
    background-color: #c8f7c5 !important;
    color: #2f6f3e !important;
    border-left: 5px solid #4caf50 !important;
}

div[data-testid="stAlert"] p {
    color: #2f6f3e !important;
    font-weight: 600;
}

div.stButton > button:hover {
    background-color: #3e8e41;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# TRYB
# =========================================================

tryb = st.sidebar.radio(
    "Tryb:",
    ["Uczeń", "Administrator"]
)


# =========================================================
# WCZYTANIE CSV
# =========================================================

try:

    occupied = pd.read_csv(
        "occupied.csv"
    )

    occupied["start"] = pd.to_datetime(
        occupied["start"]
    )

    occupied["end"] = pd.to_datetime(
        occupied["end"]
    )

    if "event_id" not in occupied.columns:
        occupied["event_id"] = ""

except:

    occupied = pd.DataFrame(
        columns=[
            "date",
            "start",
            "end",
            "level",
            "duration",
            "price",
            "name",
            "topic",
            "event_id"
        ]
    )


# =========================================================
# OKIENKA Z GOOGLE CALENDAR
# =========================================================

def get_windows_from_calendar():

    service = get_calendar_service([
        "https://www.googleapis.com/auth/calendar.readonly"
    ])

    now = datetime.now(
        timezone.utc
    ).isoformat()

    events_result = service.events().list(
        calendarId=CALENDAR_OKIENKA,
        timeMin=now,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get(
        "items",
        []
    )

    windows = []

    for event in events:

        summary = event.get(
            "summary",
            ""
        )

        if "Okienko" in summary:

            start_dt = datetime.fromisoformat(
                event["start"]["dateTime"]
            ).replace(
                tzinfo=None
            )

            end_dt = datetime.fromisoformat(
                event["end"]["dateTime"]
            ).replace(
                tzinfo=None
            )

            windows.append(
                (start_dt, end_dt)
            )

    return windows


# =========================================================
# POBRANIE OKIENEK
# =========================================================

windows = get_windows_from_calendar()


if len(windows) == 0:

    st.error(
        "Brak dostępnych okienek w kalendarzu Korepetycje."
    )

    st.stop()


# =========================================================
# LISTA DNI
# =========================================================

days = sorted(
    list(
        set(
            [
                w[0].strftime("%Y-%m-%d")
                for w in windows
            ]
        )
    )
)


# =========================================================
# PANEL UCZNIA
# =========================================================

if tryb == "Uczeń":

    st.subheader(
        "Formularz rezerwacji"
    )


    # =====================================================
    # DATY
    # =====================================================

    today = datetime.now().date()

    tomorrow = today + timedelta(
        days=1
    )


    days_with_windows = sorted([
        datetime.strptime(
            d,
            "%Y-%m-%d"
        ).date()

        for d in days

        if datetime.strptime(
            d,
            "%Y-%m-%d"
        ).date() >= tomorrow
    ])


    if not days_with_windows:

        st.error(
            "Brak dostępnych okienek od jutra."
        )

        st.stop()


    # =====================================================
    # NAJBLIŻSZY DZIEŃ
    # =====================================================

    nearest_day = days_with_windows[0]

    nearest_day_str = nearest_day.strftime(
        "%Y-%m-%d"
    )


    # =====================================================
    # MIESIĄC KALENDARZA
    # =====================================================

    if "calendar_month" not in st.session_state:

        st.session_state.calendar_month = (
            nearest_day.month
        )

    if "calendar_year" not in st.session_state:

        st.session_state.calendar_year = (
            nearest_day.year
        )


    # =====================================================
    # WYBRANY DZIEN
    # =====================================================

    selected_day = st.query_params.get(
        "selected_day",
        nearest_day_str
    )


    # Sprawdzenie czy wybrany dzień istnieje
    try:

        selected_date = datetime.strptime(
            selected_day,
            "%Y-%m-%d"
        ).date()

    except:

        selected_date = nearest_day

        selected_day = nearest_day_str


    # =====================================================
    # STRZAŁKI MIESIĄCA
    # =====================================================

    col_prev, col_month, col_next = st.columns(
        [1, 3, 1]
    )


    with col_prev:

        if st.button("←"):

            if st.session_state.calendar_month == 1:

                st.session_state.calendar_month = 12

                st.session_state.calendar_year -= 1

            else:

                st.session_state.calendar_month -= 1

            st.rerun()


    with col_month:

        st.markdown(
            f"""
            <h3 style='text-align:center;'>
                {calendar.month_name[
                    st.session_state.calendar_month
                ]}
                {st.session_state.calendar_year}
            </h3>
            """,
            unsafe_allow_html=True
        )


    with col_next:

        if st.button("→"):

            if st.session_state.calendar_month == 12:

                st.session_state.calendar_month = 1

                st.session_state.calendar_year += 1

            else:

                st.session_state.calendar_month += 1

            st.rerun()


  # =====================================================
# KALENDARZ
# =====================================================

year = st.session_state.calendar_year
month = st.session_state.calendar_month

cal = calendar.monthcalendar(year, month)

# Styl kalendarza
st.markdown("""
<style>

.calendar-day button {
    min-height: 55px !important;
    height: 55px !important;
    padding: 5px !important;
    border-radius: 0px !important;
    border: 1px solid #ccc !important;
    font-size: 18px !important;
}

/* Zielone dostępne dni */
.available-day button {
    background-color: #5ac252 !important;
    color: black !important;
}

/* Zielone po najechaniu */
.available-day button:hover {
    background-color: #4caf50 !important;
    color: white !important;
}

/* Dzisiejszy dzień */
.today-day button {
    background-color: #067806 !important;
    color: white !important;
}

/* Wybrany dzień */
.selected-day button {
    background-color: #5ac252 !important;
    color: black !important;
    border: 3px solid #067806 !important;
}

/* Niedostępne dni */
.unavailable-day {
    min-height: 55px;
    height: 55px;
    padding: 5px;
    border: 1px solid #eee;
    color: #aaa;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-sizing: border-box;
}

/* Nagłówki dni tygodnia */
.weekday {
    text-align: center;
    font-weight: 600;
    color: #555;
    padding: 5px;
}

</style>
""", unsafe_allow_html=True)


# Nazwy dni tygodnia
weekdays = [
    "Pon",
    "Wt",
    "Śr",
    "Czw",
    "Pt",
    "Sob",
    "Nd"
]


# Nagłówki
header_cols = st.columns(7)

for i, weekday in enumerate(weekdays):

    with header_cols[i]:

        st.markdown(
            f"""
            <div class="weekday">
                {weekday}
            </div>
            """,
            unsafe_allow_html=True
        )


# =====================================================
# DNI MIESIĄCA
# =====================================================

for week in cal:

    cols = st.columns(7)

    for i, day_num in enumerate(week):

        with cols[i]:

            # Puste miejsce
            if day_num == 0:

                st.markdown(
                    """
                    <div class="unavailable-day"
                         style="visibility:hidden;">
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                continue


            d = datetime(
                year,
                month,
                day_num
            ).date()

            d_str = d.strftime("%Y-%m-%d")


            # =================================================
            # DZISIAJ
            # =================================================

            if d == today:

                st.markdown(
                    f"""
                    <div style="
                        min-height:55px;
                        height:55px;
                        background-color:#067806;
                        color:white;
                        border:1px solid #ccc;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-size:18px;
                        box-sizing:border-box;
                    ">
                        {day_num}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                continue


            # =================================================
            # DOSTĘPNY DZIEŃ
            # =================================================

            if (
                d in days_with_windows
                and d > today
            ):

                is_selected = (
                    d_str == selected_day
                )

                if is_selected:
                    container_class = "selected-day"
                else:
                    container_class = "available-day"


                st.markdown(
                    f'<div class="calendar-day {container_class}">',
                    unsafe_allow_html=True
                )


                clicked = st.button(
                    str(day_num),
                    key=f"calendar_day_{d_str}",
                    use_container_width=True
                )


                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )


                if clicked:

                    st.query_params["selected_day"] = d_str

                    st.rerun()


            # =================================================
            # DZIEŃ NIEDOSTĘPNY
            # =================================================

            else:

                st.markdown(
                    f"""
                    <div class="unavailable-day">
                        {day_num}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # =====================================================
    # WYBRANY DZIEŃ
    # =====================================================

    day = selected_day


    st.markdown(
        f"""
        <div style="
            margin-top:15px;
            margin-bottom:15px;
            color:#2f6f3e;
            font-size:17px;
            font-weight:600;
        ">
            Wybrany dzień:
            {selected_date.strftime("%d.%m.%Y")}
        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # OKIENKA DLA WYBRANEGO DNIA
    # =====================================================

    selected_windows = [
        w
        for w in windows
        if w[0].strftime("%Y-%m-%d") == day
    ]


    # =====================================================
    # DŁUGOŚĆ ZAJĘĆ
    # =====================================================

    duration = st.selectbox(
        "Długość zajęć (minuty):",
        [60, 90, 120]
    )


    # =====================================================
    # WOLNE FRAGMENTY
    # =====================================================

    free_windows = []


    for w_start, w_end in selected_windows:

        fragments = [
            (w_start, w_end)
        ]


        for _, row in occupied.iterrows():

            if row["date"] != day:
                continue


            occ_start = row["start"]

            occ_end = row["end"]


            new_fragments = []


            for f_start, f_end in fragments:

                # Brak kolizji

                if (
                    f_end <= occ_start
                    or
                    f_start >= occ_end
                ):

                    new_fragments.append(
                        (f_start, f_end)
                    )

                else:

                    # Fragment przed rezerwacją

                    if f_start < occ_start:

                        new_fragments.append(
                            (
                                f_start,
                                occ_start
                            )
                        )


                    # Fragment po rezerwacji

                    if f_end > occ_end:

                        new_fragments.append(
                            (
                                occ_end,
                                f_end
                            )
                        )


            fragments = new_fragments


        free_windows.extend(
            fragments
        )


    # =====================================================
    # GODZINY STARTU
    # =====================================================

    times = []


    for f_start, f_end in free_windows:

        current = f_start


        while (
            current + timedelta(
                minutes=duration
            ) <= f_end
        ):

            times.append(
                current.strftime("%H:%M")
            )

            current += timedelta(
                minutes=15
            )


    # Usuwanie duplikatów
    times = sorted(
        set(times)
    )


    # =====================================================
    # BRAK GODZIN
    # =====================================================

    if len(times) == 0:

        st.error(
            "Brak dostępnych godzin w tym dniu."
        )

        st.stop()


    # =====================================================
    # GODZINA
    # =====================================================

    start_time = st.selectbox(
        "Godzina rozpoczęcia:",
        times
    )


    # =====================================================
    # POZIOM
    # =====================================================

    level = st.selectbox(
        "Poziom zajęć:",
        [
            "Podstawówka",
            "Podstawa",
            "Rozszerzenie"
        ]
    )


    prices = {
        "Podstawówka": 70,
        "Podstawa": 80,
        "Rozszerzenie": 100
    }


    total_price = (
        prices[level]
        *
        (duration / 60)
    )


    st.info(
        f"Cena zajęć: {total_price} zł"
    )


    # =====================================================
    # DANE UCZNIA
    # =====================================================

    name = st.text_input(
        "Imię ucznia:"
    )

    topic = st.text_input(
        "Temat zajęć:"
    )


    # =====================================================
    # REZERWACJA
    # =====================================================

    if st.button("Rezerwuj"):

        # -----------------------------------------------
        # DATA START
        # -----------------------------------------------

        start_dt = datetime.strptime(
            f"{day} {start_time}",
            "%Y-%m-%d %H:%M"
        )


        # -----------------------------------------------
        # DATA KONIEC
        # -----------------------------------------------

        end_dt = (
            start_dt
            +
            timedelta(
                minutes=duration
            )
        )


        # 15 minut przerwy
        final_end = (
            end_dt
            +
            timedelta(
                minutes=15
            )
        )


        # -----------------------------------------------
        # SPRAWDZENIE KONFLIKTU
        # -----------------------------------------------

        conflict = occupied[
            (occupied["date"] == day)
            &
            (occupied["start"] < final_end)
            &
            (occupied["end"] > start_dt)
        ]


        if len(conflict) > 0:

            st.error(
                "Ten zakres jest już zajęty!"
            )

        else:

            # -------------------------------------------
            # GOOGLE CALENDAR
            # -------------------------------------------

            event_id = create_event(

                summary=(
                    f"Korepetycje: "
                    f"{name} – {topic}"
                ),

                start_time=start_dt.isoformat(),

                end_time=end_dt.isoformat()
            )


            # -------------------------------------------
            # NOWY WIERSZ
            # -------------------------------------------

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


            # -------------------------------------------
            # DODANIE DO REZERWACJI
            # -------------------------------------------

            occupied = pd.concat(
                [
                    occupied,
                    new_row
                ],
                ignore_index=True
            )


            # -------------------------------------------
            # ZAPIS CSV
            # -------------------------------------------

            occupied.to_csv(
                "occupied.csv",
                index=False
            )


            # -------------------------------------------
            # SUKCES
            # -------------------------------------------

            st.success(
                "Zarezerwowano!"
            )


# =========================================================
# PANEL ADMINISTRATORA
# =========================================================

if tryb == "Administrator":

    st.subheader(
        "Panel administratora"
    )


    access_code = st.text_input(
        "Podaj kod dostępu:",
        type="password"
    )


    if access_code != "123babajagapatrzy":

        st.warning(
            "Wpisz poprawny kod, aby zobaczyć panel administratora."
        )


    else:

        st.success(
            "Kod poprawny. Witaj w panelu administratora!"
        )


        st.subheader(
            "Wszystkie rezerwacje"
        )


        if len(occupied) == 0:

            st.info(
                "Brak rezerwacji."
            )


        else:

            st.dataframe(
                occupied
            )


            st.subheader(
                "Usuń rezerwację"
            )


            index_to_delete = st.number_input(
                "Podaj numer wiersza do usunięcia:",
                min_value=0,
                max_value=len(occupied) - 1,
                step=1
            )


            if st.button(
                "Usuń wybraną rezerwację"
            ):

                event_id = occupied.loc[
                    index_to_delete,
                    "event_id"
                ]


                # -----------------------------------------
                # USUNIĘCIE Z GOOGLE CALENDAR
                # -----------------------------------------

                if (
                    isinstance(event_id, str)
                    and event_id.strip() != ""
                ):

                    delete_event(
                        event_id
                    )


                # -----------------------------------------
                # USUNIĘCIE Z CSV
                # -----------------------------------------

                occupied = occupied.drop(
                    index_to_delete
                ).reset_index(
                    drop=True
                )


                occupied.to_csv(
                    "occupied.csv",
                    index=False
                )


                st.success(
                    "Rezerwacja została usunięta "
                    "(CSV + Google Calendar)."
                )


                st.rerun()
