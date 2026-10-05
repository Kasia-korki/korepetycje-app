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

    except Exception:
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


/* =====================================================
   ZWYKŁE PRZYCISKI
   ===================================================== */

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


/* =====================================================
   ALERTY
   ===================================================== */

div[data-testid="stAlert"] {

    background-color: #c8f7c5 !important;

    color: #2f6f3e !important;

    border-left: 5px solid #4caf50 !important;
}


div[data-testid="stAlert"] p {

    color: #2f6f3e !important;

    font-weight: 600;
}


/* =====================================================
   DNI KALENDARZA
   ===================================================== */

.calendar-empty {

    height: 52px;

}


.calendar-unavailable {

    height: 52px;

    background-color: #ffffff;

    border: 1px solid #eeeeee;

    color: #aaaaaa;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 18px;

    box-sizing: border-box;

}


/* =====================================================
   PRZYCISKI KALENDARZA
   ===================================================== */

.calendar-button div.stButton > button {

    height: 52px !important;

    min-height: 52px !important;

    padding: 0 !important;

    border-radius: 0 !important;

    border: 1px solid #cccccc !important;

    background-color: #5ac252 !important;

    color: #000000 !important;

    font-size: 18px !important;

    font-weight: 500 !important;

}


.calendar-button div.stButton > button:hover {

    background-color: #4caf50 !important;

    color: white !important;

}


/* =====================================================
   NAGŁÓWKI DNI TYGODNIA
   ===================================================== */

.calendar-weekday {

    text-align: center;

    font-weight: 600;

    color: #555555;

    padding-bottom: 6px;

    font-size: 14px;

}


/* =====================================================
   DZISIAJ
   ===================================================== */

.calendar-today {

    height: 52px;

    background-color: #067806;

    color: white;

    border: 1px solid #cccccc;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 18px;

    box-sizing: border-box;

}


/* =====================================================
   WYBRANY DZIEŃ
   ===================================================== */

.selected-info {

    margin-top: 15px;

    margin-bottom: 15px;

    color: #2f6f3e;

    font-size: 17px;

    font-weight: 600;

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

    if "date" not in occupied.columns:
        occupied["date"] = ""

    occupied["date"] = occupied["date"].astype(str)

    if "start" in occupied.columns:
        occupied["start"] = pd.to_datetime(
            occupied["start"],
            errors="coerce"
        )

    else:
        occupied["start"] = pd.NaT


    if "end" in occupied.columns:
        occupied["end"] = pd.to_datetime(
            occupied["end"],
            errors="coerce"
        )

    else:
        occupied["end"] = pd.NaT


    if "event_id" not in occupied.columns:
        occupied["event_id"] = ""


except Exception:

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

        maxResults=2500,

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


        if "Okienko" not in summary:
            continue


        start_data = event.get(
            "start",
            {}
        )

        end_data = event.get(
            "end",
            {}
        )


        start_string = start_data.get(
            "dateTime"
        )

        end_string = end_data.get(
            "dateTime"
        )


        # Pomijamy wydarzenia całodniowe
        if not start_string or not end_string:
            continue


        try:

            start_dt = datetime.fromisoformat(
                start_string
            ).replace(
                tzinfo=None
            )


            end_dt = datetime.fromisoformat(
                end_string
            ).replace(
                tzinfo=None
            )


            windows.append(
                (
                    start_dt,
                    end_dt
                )
            )

        except Exception:

            continue


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
            w[0].strftime("%Y-%m-%d")
            for w in windows
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


    days_with_windows = sorted(
        [
            datetime.strptime(
                d,
                "%Y-%m-%d"
            ).date()

            for d in days

            if datetime.strptime(
                d,
                "%Y-%m-%d"
            ).date() >= tomorrow
        ]
    )


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
    # INICJALIZACJA KALENDARZA
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
    # WYBRANY DZIEŃ
    # =====================================================

    if "selected_day" not in st.session_state:

        st.session_state.selected_day = (
            nearest_day_str
        )


    # =====================================================
    # FUNKCJA WYBORU DNIA
    # =====================================================

    def select_day(day_string):

        st.session_state.selected_day = day_string


    selected_day = st.session_state.selected_day


    # =====================================================
    # STRZAŁKI MIESIĄCA
    # =====================================================

    col_prev, col_month, col_next = st.columns(
        [1, 3, 1]
    )


    with col_prev:

        if st.button(
            "←",
            key="previous_month"
        ):

            if st.session_state.calendar_month == 1:

                st.session_state.calendar_month = 12

                st.session_state.calendar_year -= 1

            else:

                st.session_state.calendar_month -= 1

            st.rerun()


    with col_month:

        st.markdown(
            f"""
            <h3 style="
                text-align:center;
                margin-top:5px;
                margin-bottom:15px;
            ">
                {calendar.month_name[
                    st.session_state.calendar_month
                ]}
                {st.session_state.calendar_year}
            </h3>
            """,
            unsafe_allow_html=True
        )


    with col_next:

        if st.button(
            "→",
            key="next_month"
        ):

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


    # Zawsze poniedziałek jako pierwszy dzień tygodnia
    cal = calendar.Calendar(
        firstweekday=calendar.MONDAY
    ).monthdayscalendar(
        year,
        month
    )


    # =====================================================
    # NAGŁÓWKI DNI TYGODNIA
    # =====================================================

    weekdays = [
        "Pon",
        "Wt",
        "Śr",
        "Czw",
        "Pt",
        "Sob",
        "Nd"
    ]


    header_cols = st.columns(
        7,
        gap="small"
    )


    for i, weekday in enumerate(
        weekdays
    ):

        with header_cols[i]:

            st.markdown(
                f"""
                <div class="calendar-weekday">
                    {weekday}
                </div>
                """,
                unsafe_allow_html=True
            )


    # =====================================================
    # DNI MIESIĄCA
    # =====================================================

    for week_index, week in enumerate(cal):

        cols = st.columns(
            7,
            gap="small"
        )


        for day_index, day_num in enumerate(
            week
        ):

            with cols[day_index]:

                # -----------------------------------------
                # PUSTE POLE
                # -----------------------------------------

                if day_num == 0:

                    st.markdown(
                        """
                        <div class="calendar-empty">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    continue


                # -----------------------------------------
                # DATA
                # -----------------------------------------

                d = datetime(
                    year,
                    month,
                    day_num
                ).date()


                d_str = d.strftime(
                    "%Y-%m-%d"
                )


                # -----------------------------------------
                # DZISIAJ
                # -----------------------------------------

                if d == today:

                    st.markdown(
                        f"""
                        <div class="calendar-today">
                            {day_num}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    continue


                # -----------------------------------------
                # DOSTĘPNY DZIEŃ
                # -----------------------------------------

                if (
                    d in days_with_windows
                    and d > today
                ):

                    # Osobny kontener dla stylu
                    st.markdown(
                        '<div class="calendar-button">',
                        unsafe_allow_html=True
                    )


                    st.button(
                        str(day_num),

                        key=f"calendar_day_{d_str}",

                        width="stretch",

                        on_click=select_day,

                        args=(d_str,)
                    )


                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True
                    )


                # -----------------------------------------
                # NIEDOSTĘPNY DZIEŃ
                # -----------------------------------------

                else:

                    st.markdown(
                        f"""
                        <div class="calendar-unavailable">
                            {day_num}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


    # =====================================================
    # OSTATECZNY WYBRANY DZIEŃ
    # =====================================================

    selected_day = st.session_state.selected_day


    try:

        selected_date = datetime.strptime(
            selected_day,
            "%Y-%m-%d"
        ).date()

    except Exception:

        selected_date = nearest_day

        selected_day = nearest_day_str

        st.session_state.selected_day = (
            nearest_day_str
        )


    # =====================================================
    # INFORMACJA O WYBRANYM DNIU
    # =====================================================

    st.markdown(
        f"""
        <div class="selected-info">
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

        if w[0].strftime(
            "%Y-%m-%d"
        ) == selected_day

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
            (
                w_start,
                w_end
            )
        ]


        for _, row in occupied.iterrows():

            if str(row["date"]) != selected_day:
                continue


            occ_start = row["start"]

            occ_end = row["end"]


            if pd.isna(
                occ_start
            ) or pd.isna(
                occ_end
            ):

                continue


            new_fragments = []


            for f_start, f_end in fragments:

                # Brak kolizji

                if (
                    f_end <= occ_start
                    or
                    f_start >= occ_end
                ):

                    new_fragments.append(
                        (
                            f_start,
                            f_end
                        )
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
            current
            +
            timedelta(
                minutes=duration
            )
            <= f_end
        ):

            times.append(
                current.strftime(
                    "%H:%M"
                )
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

    if st.button(
        "Rezerwuj",
        key="reserve_button"
    ):

        # -----------------------------------------------
        # DATA START
        # -----------------------------------------------

        start_dt = datetime.strptime(
            f"{selected_day} {start_time}",
            "%Y-%m-%d %H:%M"
        )


        # -----------------------------------------------
        # DATA KONIEC ZAJĘĆ
        # -----------------------------------------------

        end_dt = (
            start_dt
            +
            timedelta(
                minutes=duration
            )
        )


        # 15 minut przerwy po zajęciach

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

            (occupied["date"] == selected_day)

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

            try:

                # ---------------------------------------
                # GOOGLE CALENDAR
                # ---------------------------------------

                event_id = create_event(

                    summary=(
                        f"Korepetycje: "
                        f"{name} – {topic}"
                    ),

                    start_time=start_dt.isoformat(),

                    end_time=end_dt.isoformat()

                )


                # ---------------------------------------
                # NOWY WIERSZ
                # ---------------------------------------

                new_row = pd.DataFrame({

                    "date": [
                        selected_day
                    ],

                    "start": [
                        start_dt
                    ],

                    "end": [
                        final_end
                    ],

                    "level": [
                        level
                    ],

                    "duration": [
                        duration
                    ],

                    "price": [
                        total_price
                    ],

                    "name": [
                        name
                    ],

                    "topic": [
                        topic
                    ],

                    "event_id": [
                        event_id
                    ]

                })


                # ---------------------------------------
                # DODANIE DO CSV
                # ---------------------------------------

                occupied = pd.concat(
                    [occupied, new_row],
                    ignore_index=True
                )

                occupied.to_csv(
                    "occupied.csv",
                    index=False
                )


                # ---------------------------------------
                # PODSUMOWANIE REZERWACJI
                # ---------------------------------------

                summary_html = f"""
                <div style="
                    background: #f0fff4;
                    border-left: 6px solid #38a169;
                    padding: 18px 22px;
                    border-radius: 10px;
                    font-family: 'Poppins', sans-serif;
                    margin-top: 15px;
                ">

                    <h3 style="
                        margin: 0;
                        color: #2f855a;
                        font-size: 22px;
                    ">
                        ✔ Rezerwacja potwierdzona!
                    </h3>

                    <div style="
                        margin-top: 12px;
                        font-size: 16px;
                        color: #2d3748;
                    ">

                        <p style="margin: 6px 0;">
                            📅 <strong>Data:</strong>
                            {selected_date.strftime('%d.%m.%Y')}
                        </p>

                        <p style="margin: 6px 0;">
                            ⏰ <strong>Godzina:</strong>
                            {start_dt.strftime('%H:%M')}
                            –
                            {end_dt.strftime('%H:%M')}
                        </p>

                        <p style="margin: 6px 0;">
                            🎒 <strong>Rodzaj zajęć:</strong>
                            {level}
                        </p>

                        <p style="margin: 6px 0;">
                            💸 <strong>Cena:</strong>
                            {total_price:.0f} zł
                        </p>

                        <p style="margin: 6px 0;">
                            🔐 <strong>Status:</strong>
                            Rezerwacja została potwierdzona
                        </p>

                    </div>

                    <div style="
                        margin-top: 15px;
                        font-size: 15px;
                        color: #276749;
                    ">
                        Do zobaczenia na zajęciach! 😊
                    </div>

                </div>
                """


                st.markdown(
                    summary_html,
                    unsafe_allow_html=True
                )


            except Exception as e:

                st.error(
                    f"Nie udało się utworzyć rezerwacji: {e}"
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
                # GOOGLE CALENDAR
                # -----------------------------------------

                if (
                    isinstance(
                        event_id,
                        str
                    )
                    and
                    event_id.strip() != ""
                ):

                    delete_event(
                        event_id
                    )


                # -----------------------------------------
                # CSV
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
