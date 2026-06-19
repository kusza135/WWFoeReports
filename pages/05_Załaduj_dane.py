import streamlit as st
from tools.streamlit_tools import page_header, create_engine, runsql, get_world_id, get_guild_id
from tools.login import login, check_user_role_permissions
import json
import pandas as pd
from datetime import datetime, date, timedelta
from random import randint
import time

guildPlayers = "Gracze Gildii Wzgórze Wisielców"
wg = "Wyprawy Gildyjne"
gpch = "Gildyjne Pola Chwały"
nk = "Najazdy Kwantowe"

_DATA_TYPES = [guildPlayers, wg, gpch, nk]


# ---------------------------------------------------------------------------
# OBLICZENIA DNI SEZONU
# ---------------------------------------------------------------------------

def wg_day(d: date) -> int:
    return d.weekday()


def gpch_day(d: date) -> int:
    start = datetime.strptime('2023-10-25', '%Y-%m-%d').date()
    diff = (d - start).days
    loop = diff // 14
    cur_run = (d - (start + timedelta(days=loop * 14))).days
    return cur_run if cur_run <= 11 else 0


def nk_day(d: date) -> int:
    start = datetime.strptime('2023-10-18', '%Y-%m-%d').date()
    diff = (d - start).days
    loop = diff // 14
    cur_run = (d - (start + timedelta(days=loop * 14))).days
    return cur_run if cur_run <= 11 else 0


# ---------------------------------------------------------------------------
# PARSOWANIE DANYCH
# ---------------------------------------------------------------------------

def dict_sweep(input_dict, key):
    if isinstance(input_dict, dict):
        return {k: dict_sweep(v, key) for k, v in input_dict.items() if k != key}
    if isinstance(input_dict, list):
        return [dict_sweep(element, key) for element in input_dict]
    return input_dict


def _parse_guild_players(string_data) -> pd.DataFrame:
    return pd.DataFrame(string_data)


def _parse_wg(string_data) -> pd.DataFrame:
    data = pd.json_normalize(string_data)
    data.columns = data.columns.str.lstrip('player.')
    return data


def _parse_gpch(string_data) -> pd.DataFrame:
    data = pd.json_normalize(string_data)
    data.drop(columns=['__class__'], inplace=True, errors='ignore')
    data.columns = data.columns.str.lstrip('player\\.')
    data.drop(columns=['__class__'], inplace=True, errors='ignore')
    return data


def _parse_nk(string_data) -> pd.DataFrame:
    if isinstance(string_data, list):
        for i in string_data:
            del i["__class__"]
    elif isinstance(string_data, dict) and 'rows' in string_data:
        string_data = dict_sweep(string_data["rows"], '__class__')
    data = pd.json_normalize(string_data)
    data.columns = data.columns.str.replace('player.', '', 1)
    return data


def _parse_data(file_type: str, string_data) -> pd.DataFrame:
    parsers = {
        guildPlayers: _parse_guild_players,
        wg: _parse_wg,
        gpch: _parse_gpch,
        nk: _parse_nk,
    }
    return parsers[file_type](string_data)


# ---------------------------------------------------------------------------
# WCZYTYWANIE PLIKU / SCHOWKA
# ---------------------------------------------------------------------------

def _read_upload(load_method: str, file_type: str, visibility: bool, key: str):
    if load_method == "File":
        st.markdown(body=f"Wybierz lub przeciągnij plik :blue[{file_type}]")
        return st.file_uploader(f"Wybierz lub przeciągnij plik {file_type}", key=key, disabled=not visibility, label_visibility="hidden")
    placeholder = "Dane powinny być w formacie JSON" if visibility else f"{file_type} w trakcie sezonu! \nOkno nie aktywne."
    st.markdown(body=f"Wklej dane :blue[{file_type}]")
    return st.text_area(label=f"Wklej dane {file_type}", height=200, placeholder=placeholder, key=key, disabled=not visibility, label_visibility="hidden")


def load_file(load_method: str, file_type: str, visibility: bool = True):
    key = st.session_state.get(f"{load_method}_{file_type}", "")
    uploaded = _read_upload(load_method, file_type, visibility, key)
    if uploaded is None:
        return None
    try:
        raw = uploaded.getvalue().decode("utf-8") if load_method == "File" else uploaded
        string_data = json.loads(raw)
        st.markdown(f"{file_type}  - Dane są poprawne :white_check_mark:")
        return _parse_data(file_type, string_data)
    except Exception:
        if uploaded != "":
            st.markdown(f"{file_type}  - Dane są błędne :thumbsdown:")
    return None


# ---------------------------------------------------------------------------
# ZAPIS DO BAZY
# ---------------------------------------------------------------------------

def _call_proc(db_conn, sp_name: str, *args) -> None:
    try:
        conn = db_conn.raw_connection()
        cur = conn.cursor()
        cur.callproc(sp_name, args=list(args))
        cur.close()
    finally:
        conn.close()


def _load_guild_players(db_conn, df: pd.DataFrame, vdate: date) -> None:
    cols = ['player_id', 'name', 'score', 'rank', 'city_name', 'won_battles', 'era', 'title', 'permissions']
    input_data = df.loc[:, cols]
    runsql(db_conn, 'DROP TABLE IF EXISTS __guildPlayers')
    input_data.to_sql(name='__guildPlayers', con=db_conn, if_exists='replace')
    _call_proc(db_conn, "p_guildPlayers", "__guildPlayers", {vdate})


def _load_wg(db_conn, df: pd.DataFrame, vdate: date) -> None:
    cols = ['_id', 'xpeditionPoints', 'solvedEncounters', 'contributionDifficulty', 'currentTrial']
    input_data = df.loc[:, cols]
    runsql(db_conn, 'DROP TABLE IF EXISTS __wg')
    input_data.to_sql(name='__wg', con=db_conn, if_exists='append')
    _call_proc(db_conn, "p_wg", "__wg", get_world_id(), get_guild_id(), {vdate})


def _load_gpch(db_conn, df: pd.DataFrame, vdate: date) -> None:
    if 'negotiationsWon' not in df.columns:
        df['negotiationsWon'] = None
    cols = ['_id', 'nk', 'battlesWon', 'negotiationsWon', 'ttrition']
    input_data = df.loc[:, cols]
    runsql(db_conn, 'DROP TABLE IF EXISTS __gpch')
    input_data.to_sql(name='__gpch', con=db_conn, if_exists='append')
    _call_proc(db_conn, "p_gpch", "__gpch", get_world_id(), get_guild_id(), {vdate})


def _load_nk(db_conn, df: pd.DataFrame, vdate: date) -> None:
    cols = ['player_id', 'name', 'progressContribution', 'actionPoints']
    input_data = df.loc[:, cols]
    runsql(db_conn, 'DROP TABLE IF EXISTS __nk')
    input_data.to_sql(name='__nk', con=db_conn, if_exists='append')
    _call_proc(db_conn, "p_nk", "__nk", get_world_id(), get_guild_id(), {vdate})


def load_data_intoDB(db_conn, dfName: str, df: pd.DataFrame, vdate: date = date.today()) -> None:
    loaders = {
        'guildPlayers': _load_guild_players,
        'wg': _load_wg,
        'gpch': _load_gpch,
        'nk': _load_nk,
    }
    if dfName in loaders:
        loaders[dfName](db_conn, df, vdate)


def run_last_update_date(db_conn) -> None:
    conn = db_conn.raw_connection()
    cur = conn.cursor()
    cur.callproc("p_log")
    cur.close()


# ---------------------------------------------------------------------------
# LADOWANIE DANYCH (CALLBACK)
# ---------------------------------------------------------------------------

def _normalize_dataframes(gp, wg_d, gp_d, nk_d) -> tuple:
    return (
        gp if gp is not None and not (hasattr(gp, 'empty') and gp.empty) else pd.DataFrame(),
        wg_d if wg_d is not None and not (hasattr(wg_d, 'empty') and wg_d.empty) else pd.DataFrame(),
        gp_d if gp_d is not None and not (hasattr(gp_d, 'empty') and gp_d.empty) else pd.DataFrame(),
        nk_d if nk_d is not None and not (hasattr(nk_d, 'empty') and nk_d.empty) else pd.DataFrame(),
    )


def run_loads(load_method: str, gp_data, wg_data, gp_data2, nk_data, vdate: date) -> None:
    gp_data, wg_data, gp_data2, nk_data = _normalize_dataframes(gp_data, wg_data, gp_data2, nk_data)
    with st.status("inicjuję połączenie.", expanded=True) as status:
        con = create_engine()
        stats = pd.DataFrame(columns=['Source', 'Loaded records'])
        for label, df_item, key in [(guildPlayers, gp_data, 'guildPlayers'), (wg, wg_data, 'wg'), (gpch, gp_data2, 'gpch'), (nk, nk_data, 'nk')]:
            if not df_item.empty:
                st.write(f"Ładowanie {label}...")
                load_data_intoDB(con, key, df_item, vdate)
                status.update(label=f"Zakończono {label}!", state='running', expanded=True)
                stats.loc[len(stats)] = [label, len(df_item)]
        st.cache_data.clear()
        run_last_update_date(con)
        status.update(label="Zakończono ładowanie danych!", state='complete', expanded=True)
        st.dataframe(stats)
        time.sleep(5)
        status.update(label="Zakończono ładowanie danych!", state='complete', expanded=False)
    for dtype in _DATA_TYPES:
        st.session_state.pop(f"{load_method}_{dtype}", None)


# ---------------------------------------------------------------------------
# KLASA STRONY
# ---------------------------------------------------------------------------

class DataLoaderPage:
    @staticmethod
    def _init_session_state() -> None:
        for dtype in _DATA_TYPES:
            for prefix in ["File", "Clipboard"]:
                key = f"{prefix}_{dtype}"
                if key not in st.session_state:
                    st.session_state[key] = str(randint(1000, 100000000))

    @staticmethod
    def _top_controls() -> tuple:
        xcol, xlcol, xxlcol = st.columns(3)
        with xcol.container(border=True):
            load_type = st.checkbox(label="Wymagaj ładowania wszystkich ekstraktów", value=True)
            wg_gpch_daily_run = st.checkbox(label="Pozwalaj na ładowanie danych w trakcie WG / GPCh", value=True)
        with xlcol.container(border=True):
            przycisk1 = st.toggle('zmień datę ładowania danych')
            vdate = date.today()
            if przycisk1:
                vdate = st.date_input("Wybierz datę", value="today", format='DD-MM-YYYY')
        return load_type, wg_gpch_daily_run, vdate

    @staticmethod
    def _should_show_button(load_type: bool, wg_gpch_daily_run: bool, datasets: list) -> bool:
        any_data = any(d is not None for d in datasets)
        all_data = all(d is not None for d in datasets)
        if load_type and wg_gpch_daily_run:
            return all_data
        return any_data

    @staticmethod
    def _data_tab(load_method: str, vdate: date, wg_gpch_daily_run: bool, load_type: bool) -> None:
        col1, col2, col3, col4 = st.columns(4, gap="small")
        with col1.container():
            gp_data = load_file(load_method, guildPlayers)
        with col2.container():
            wg_data = load_file(load_method, wg, wg_gpch_daily_run or wg_day(vdate) == 0)
        with col3.container():
            gp_data2 = load_file(load_method, gpch, wg_gpch_daily_run or gpch_day(vdate) == 0)
        with col4.container():
            nk_data = load_file(load_method, nk, wg_gpch_daily_run or nk_day(vdate) == 0)
        DataLoaderPage._load_button(load_method, gp_data, wg_data, gp_data2, nk_data, vdate, load_type, wg_gpch_daily_run)

    @staticmethod
    def _load_button(load_method, gp_data, wg_data, gp_data2, nk_data, vdate, load_type, wg_gpch_daily_run) -> None:
        datasets = [gp_data, wg_data, gp_data2, nk_data]
        if not DataLoaderPage._should_show_button(load_type, wg_gpch_daily_run, datasets):
            return
        label = "Załaduj dane" if load_method == "Clipboard" else "Załaduj pliki"
        gp_data, wg_data, gp_data2, nk_data = _normalize_dataframes(gp_data, wg_data, gp_data2, nk_data)
        st.button(label=label, type='primary', on_click=run_loads,
                  args=(load_method, gp_data, wg_data, gp_data2, nk_data, vdate))

    @staticmethod
    def render(username: str) -> None:
        if not check_user_role_permissions(username, 'MANUAL_DATA_RELOAD'):
            st.warning("Nie masz dostępu do tej zawartości.")
            return
        DataLoaderPage._init_session_state()
        load_type, wg_gpch_daily_run, vdate = DataLoaderPage._top_controls()
        tab1, tab2 = st.tabs(["Załaduj ze schowka", "Załaduj z pliku"])
        with tab1:
            DataLoaderPage._data_tab("Clipboard", vdate, wg_gpch_daily_run, load_type)
        with tab2:
            DataLoaderPage._data_tab("File", vdate, wg_gpch_daily_run, load_type)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    page_header()

    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None

    authenticator, users, username = login()

    if username and st.session_state.get("authentication_status"):
        DataLoaderPage.render(username)
