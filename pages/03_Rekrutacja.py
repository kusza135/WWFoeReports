import streamlit as st
import altair as alt
from tools.streamlit_tools import (
    execute_query, get_guild_id, get_world_id,
    page_header, create_engine, get_worlds
)
from tools.login import login, check_user_role_permissions
import pandas as pd
from datetime import date, timedelta
import time

# ---------------------------------------------------------------------------
# WARSTWA DANYCH
# ---------------------------------------------------------------------------

@st.cache_data(ttl=0)
def get_prospect_history() -> pd.DataFrame:
    return execute_query(
        """SELECT
                world, Guild_name, 'True' AS Prospect,
                playerId, status_id, status_Name,
                recriterid, name, invitation_date,
                future_invitation_date, last_change_date, notes
            FROM v_prospects
            WHERE world = :world AND guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_resource(ttl=14400, show_spinner="Pobieranie danych (wszyscy gracze)...")
def get_all_players(world: str) -> pd.DataFrame:
    return execute_query(
        """SELECT
                world, world_name, playerId,
                Player_rank AS `Ranking`, avatar, name AS Gracz,
                Player_link, ClanId, clanName AS Gildia,
                points AS `Punty Rankingowe`, battles AS `Wygrane Bitwy`,
                Age_PL AS Epoka, pointsDif, battlesDif,
                avg_last_battles, avg_last_points,
                guild_join_date, valid_to
            FROM V_ALL_PLAYERS
            WHERE world = :world AND valid_to = '3000-12-31'
        """,
        params={"world": world},
        return_type="df",
    )


@st.cache_resource(ttl=14400, show_spinner="Pobieranie danych (inne światy)...")
def get_player_other_worlds(world: str, player_id: int) -> pd.DataFrame:
    return execute_query(
        """SELECT
                world, world_name, playerId,
                Player_rank AS `Ranking`, avatar, name AS Gracz,
                Player_link, ClanId, clanName AS Gildia,
                points AS `Punty Rankingowe`, battles AS `Wygrane Bitwy`,
                Age_PL AS Epoka,
                pointsDif AS `Zdobyte punkty (wczoraj)`,
                battlesDif AS `Walki (wczoraj)`,
                avg_last_battles, avg_last_points, valid_to
            FROM V_ALL_PLAYERS
            WHERE world != :world
              AND playerId = :player_id
              AND valid_to = '3000-12-31'
        """,
        params={"world": world, "player_id": player_id},
        return_type="df",
    )


@st.cache_resource(ttl=28800, show_spinner="Pobieranie danych (aktywność gracza)...")
def get_player_activity(player_id: int) -> pd.DataFrame:
    return execute_query(
        """SELECT
                world, playerId, avatar, name,
                points AS `Punty rankingowe`,
                battles AS `Liczba bitew`,
                pointsDif AS `Roznica punktow rankingowych`,
                battlesDif AS `Roznica bitew`,
                CAST(DATE_ADD(valid_from, INTERVAL -1 DAY) AS CHAR) AS Data_danych,
                CASE WHEN f_gpch_day(DATE_ADD(valid_from, INTERVAL -1 DAY)) > 0
                     THEN 500 ELSE 0 END AS GPCh
            FROM V_ALL_PLAYERS
            WHERE valid_from > DATE_ADD(CURRENT_DATE(), INTERVAL -30 DAY)
              AND playerId = :player_id
        """,
        params={"player_id": player_id},
        return_type="df",
    )


@st.cache_resource(ttl=28800, show_spinner="Pobieranie danych (historia gildii)...")
def get_player_guild_history(world: str, player_id: int) -> pd.DataFrame:
    return execute_query(
        """SELECT
                playerId, name AS Gracz,
                clanName AS Gildia, joinDate AS `Data dolaczenia`
            FROM t_player_guild_history
            WHERE world = :world AND playerId = :player_id
        """,
        params={"world": world, "player_id": player_id},
        return_type="df",
    )


@st.cache_resource(ttl=28800, show_spinner="Pobieranie epok...")
def get_df_ages() -> pd.DataFrame:
    return execute_query(
        "SELECT id, Age_PL FROM t_ages WHERE valid_to = '3000-12-31' ORDER BY id",
        return_type="df",
    )


@st.cache_resource(ttl=28800, show_spinner="Pobieranie gildii...")
def get_guilds(world: str) -> pd.DataFrame:
    return execute_query(
        "SELECT clanId, name AS Gildia, members FROM V_all_guilds WHERE world = :world",
        params={"world": world},
        return_type="df",
    )


@st.cache_data(ttl=3600)
def get_df_recruters() -> pd.DataFrame:
    return execute_query(
        """SELECT playerId, name, is_active
           FROM v_recruters
           WHERE world = :world AND guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=3600)
def get_statuses() -> pd.DataFrame:
    return execute_query(
        "SELECT status_id, status_Name FROM t_statuses WHERE module_name = 'PROSPECT'",
        return_type="df",
    )


@st.cache_data(ttl=0)
def build_all_players_view(all_players_raw: pd.DataFrame, prospects: pd.DataFrame) -> pd.DataFrame:
    if prospects.empty:
        result = all_players_raw.copy()
        result["Prospect"] = None
        result["Status"] = None
        return result
    latest_prospects = (
        prospects.sort_values("last_change_date")
        .groupby("playerId", as_index=False)
        .last()[["playerId", "Prospect", "status_Name"]]
    )
    result = all_players_raw.merge(latest_prospects, on="playerId", how="left", indicator=True)
    result.rename(columns={"status_Name": "Status"}, inplace=True)
    return result


# ---------------------------------------------------------------------------
# HELPERY
# ---------------------------------------------------------------------------

def get_index_func(lov: list, current_value) -> int | None:
    try:
        return lov.index(current_value)
    except ValueError:
        return None


def select_world() -> str:
    worlds = get_worlds()
    worlds_id = worlds["world"].sort_values().unique().tolist()
    worlds_names = worlds["world_name"].sort_values().unique().tolist()
    selected_id = get_index_func(worlds_id, get_world_id())
    world_selected = st.radio(label="Wybierz Swiat:", options=worlds_names, index=selected_id, horizontal=True)
    return worlds_id[get_index_func(worlds_names, world_selected)]


def _normalize_sp_args(p_player_guild_id, p_invitation_date, p_future_invitation_date, p_notes) -> tuple:
    if p_player_guild_id != p_player_guild_id:
        p_player_guild_id = 0
    return p_player_guild_id, p_invitation_date or "", p_future_invitation_date or "", p_notes or ""


def exec_prospect_sp(sp_name, p_world, p_guildid, p_player_id, p_status_id, p_recruiter_id,
                     p_player_guild_id=None, p_invitation_date=None, p_future_invitation_date=None, p_notes=None) -> None:
    p_player_guild_id, p_invitation_date, p_future_invitation_date, p_notes = _normalize_sp_args(
        p_player_guild_id, p_invitation_date, p_future_invitation_date, p_notes
    )
    con = create_engine()
    try:
        conn = con.raw_connection()
        cur = conn.cursor()
        cur.callproc(sp_name, args=[p_world, p_guildid, p_player_id, p_player_guild_id,
                                    int(p_status_id), int(p_recruiter_id),
                                    p_invitation_date, p_future_invitation_date, p_notes])
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"Blad zapisu: {e}")
        time.sleep(5)
    finally:
        conn.close()


def clear_recruitment_cache() -> None:
    get_prospect_history.clear()
    build_all_players_view.clear()
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# FILTRY
# ---------------------------------------------------------------------------

class RecruitmentFilters:
    @staticmethod
    def _guild_filter(all_players: pd.DataFrame, df_guilds: pd.DataFrame, col) -> pd.DataFrame:
        if not col.checkbox("Wyklucz/Oznacz wybrane gildie", value=False):
            return all_players
        mode = col.radio("Gildie", options=["Wyklucz Gildie", "Wybrane Gildie"], index=1, horizontal=True, label_visibility="hidden")
        selected_guilds = col.multiselect("Wybierz gildie", df_guilds.Gildia.sort_values().unique(), placeholder="Rozwij lub zacznij wpisywac")
        if not selected_guilds:
            return all_players
        clan_ids = df_guilds.loc[df_guilds["Gildia"].isin(selected_guilds), "clanId"].tolist()
        return all_players[~all_players["ClanId"].isin(clan_ids)] if mode == "Wyklucz Gildie" else all_players[all_players["ClanId"].isin(clan_ids)]

    @staticmethod
    def _player_filter(all_players: pd.DataFrame, col) -> pd.DataFrame:
        if not col.checkbox("Wybrany Gracz", value=False):
            return all_players
        selected = col.multiselect("Wybierz gracza", all_players.Gracz.sort_values().unique(), max_selections=4, placeholder="Rozwij lub zacznij wpisywac")
        if not selected:
            return all_players
        pids = all_players.loc[all_players["Gracz"].isin(selected), "playerId"].tolist()
        return all_players[all_players["playerId"].isin(pids)]

    @staticmethod
    def _homeless_filter(all_players: pd.DataFrame, col) -> pd.DataFrame:
        homeless = col.radio("Gracze", options=["bez Gildii", "w Gildii", "Wszyscy"], index=2)
        if homeless == "bez Gildii":
            return all_players[all_players["ClanId"].isna()]
        if homeless == "w Gildii":
            return all_players[all_players["ClanId"].notna()]
        return all_players

    @staticmethod
    def _activity_filter(all_players: pd.DataFrame, col) -> pd.DataFrame:
        if not col.checkbox("Wyswietl tylko aktywnych", value=False):
            return all_players
        metric = col.radio("Filtruj po", options=["Bitwy", "Punkty"], index=0, horizontal=True, label_visibility="hidden")
        if metric == "Bitwy":
            threshold = col.number_input("Srednia ilosc walk (30 dni)", value=50, step=5)
            return all_players[all_players["avg_last_battles"] > threshold]
        threshold = col.number_input("Srednia ilosc punktow (30 dni)", value=300_000, step=500)
        return all_players[all_players["avg_last_points"] > threshold]

    @staticmethod
    def _age_filter(all_players: pd.DataFrame, df_ages: pd.DataFrame, col) -> pd.DataFrame:
        if not col.checkbox("Wybierz Epoki", value=False):
            return all_players
        selected_ages = col.multiselect("Wybierz Epoki", df_ages.Age_PL.sort_index().unique(), placeholder="Rozwij lub zacznij wpisywac")
        if not selected_ages:
            return all_players
        return all_players[all_players["Epoka"].isin(selected_ages)]

    @staticmethod
    def _status_filter(all_players: pd.DataFrame, df_statuses: pd.DataFrame, col) -> pd.DataFrame:
        if not col.checkbox("Rekrutacja", value=False):
            return all_players
        selected_statuses = col.pills("Status", options=df_statuses.status_Name.sort_index().unique().tolist(),
                                      selection_mode="multi", format_func=str, label_visibility="hidden")
        if not selected_statuses:
            return all_players
        return all_players[all_players["Status"].isin(selected_statuses)]

    @staticmethod
    def apply(all_players: pd.DataFrame, df_guilds: pd.DataFrame,
              df_ages: pd.DataFrame, df_statuses: pd.DataFrame) -> pd.DataFrame:
        with st.expander("Filtruj...", expanded=True):
            col1, col2, col3, col4, col5 = st.columns([15, 5, 8, 8, 10])
            with col1:
                all_players = RecruitmentFilters._guild_filter(all_players, df_guilds, col1)
                all_players = RecruitmentFilters._player_filter(all_players, col1)
            all_players = RecruitmentFilters._homeless_filter(all_players, col2)
            all_players = RecruitmentFilters._activity_filter(all_players, col3)
            all_players = RecruitmentFilters._age_filter(all_players, df_ages, col4)
            all_players = RecruitmentFilters._status_filter(all_players, df_statuses, col5)
        return all_players


# ---------------------------------------------------------------------------
# FORMULARZ REKRUTACYJNY
# ---------------------------------------------------------------------------

class RecruitmentForm:
    @staticmethod
    def _get_active(prospect_history: pd.DataFrame, player_id: int) -> pd.DataFrame:
        df_history = prospect_history[prospect_history["playerId"] == player_id]
        if df_history.empty:
            return pd.DataFrame()
        return df_history[df_history["last_change_date"] == df_history["last_change_date"].max()]

    @staticmethod
    def _player_info(col1, col2, df_selected: pd.DataFrame, df_guilds: pd.DataFrame) -> None:
        col1.markdown(f"Gracz: **:blue[{df_selected['Gracz'].iloc[0]}]**")
        col1.markdown(f"Epoka: **{df_selected['Epoka'].iloc[0]}**")
        col2.markdown(f"Gildia: **{df_selected['Gildia'].iloc[0]}**")
        clan_id = df_selected["ClanId"].iloc[0]
        guild_match = df_guilds[df_guilds["clanId"] == clan_id]
        num_members = 0 if pd.isna(clan_id) or guild_match.empty else guild_match["members"].iloc[0]
        col2.markdown(f"Liczba graczy w Gildii: **{num_members}**")

    @staticmethod
    def _recruiter_input(col3, df_recruters: pd.DataFrame, df_active: pd.DataFrame):
        active = df_recruters[df_recruters["is_active"] == True]
        recruiter_idx = None
        if not df_active.empty and "recriterid" in df_active.columns:
            recruiter_idx = get_index_func(active.playerId.tolist(), df_active["recriterid"].iloc[0])
        selected = col3.selectbox("Rekruter", options=active.name.sort_values().unique(), index=recruiter_idx)
        return active.loc[active["name"] == selected, "playerId"].iloc[0] if selected else None

    @staticmethod
    def _date_input(col3, df_active: pd.DataFrame):
        inv_date_val = date.today()
        if not df_active.empty and "invitation_date" in df_active.columns:
            raw = df_active["invitation_date"].iloc[0]
            if pd.notna(raw):
                inv_date_val = raw
        return col3.date_input("Data zaproszenia", value=inv_date_val, format="YYYY-MM-DD")

    @staticmethod
    def _status_input(col4, df_statuses: pd.DataFrame, df_active: pd.DataFrame) -> tuple:
        status_idx = 0
        if not df_active.empty and "status_id" in df_active.columns:
            status_idx = get_index_func(df_statuses.status_id.tolist(), df_active["status_id"].iloc[0]) or 0
        selected_status = col4.selectbox("Status", options=df_statuses.status_Name.sort_index().unique(), index=status_idx)
        status_id = df_statuses.loc[df_statuses["status_Name"] == selected_status, "status_id"].iloc[0] if selected_status else None
        next_comm_date = None
        if selected_status == "Zawieszono":
            next_comm_date = col4.date_input("Data nastepnej komunikacji", value=date.today() + timedelta(days=60), min_value=date.today(), format="YYYY-MM-DD")
        return status_id, next_comm_date

    @staticmethod
    def _save_section(df_selected, avg_battles, world, player_id, recruiter_id, status_id, inv_date, next_comm_date, clan_id) -> None:
        col0, col_metric, col_notes = st.columns([8, 22, 60])
        col0.image(df_selected["avatar"].iloc[0])
        col_metric.metric("Srednia walk (30 dni)", value=avg_battles)
        with col_notes:
            add_text = st.text_area("Uwagi:")
            btn_disabled = not (recruiter_id and status_id)
            if world != get_world_id():
                st.error("Mozesz rekrutowac tylko w swoim swiecie")
            elif st.button("Zapisz zmiany", type="primary", disabled=btn_disabled):
                exec_prospect_sp("p_prospect_history", get_world_id(), get_guild_id(), player_id,
                                 status_id, recruiter_id, clan_id, inv_date, next_comm_date, add_text)
                clear_recruitment_cache()
                st.toast("Zmiany wprowadzone", icon="✅")
                st.rerun()

    @staticmethod
    def render(prospect_history, player_id, df_selected, df_recruters, df_guilds, df_statuses, world, avg_battles) -> None:
        df_active = RecruitmentForm._get_active(prospect_history, player_id)
        st.markdown(f"#### Rekrutacja Gracza {df_selected['Gracz'].iloc[0]} ####")
        col1, col2, col3, col4 = st.columns([15, 15, 30, 30])
        RecruitmentForm._player_info(col1, col2, df_selected, df_guilds)
        recruiter_id = RecruitmentForm._recruiter_input(col3, df_recruters, df_active)
        inv_date = RecruitmentForm._date_input(col3, df_active)
        status_id, next_comm_date = RecruitmentForm._status_input(col4, df_statuses, df_active)
        RecruitmentForm._save_section(df_selected, avg_battles, world, player_id, recruiter_id, status_id, inv_date, next_comm_date, df_selected["ClanId"].iloc[0])


# ---------------------------------------------------------------------------
# KOMPONENTY UI
# ---------------------------------------------------------------------------

def _players_dataframe_config() -> dict:
    return {
        "avatar": st.column_config.ImageColumn(label="Avatar", width="small"),
        "Player_link": st.column_config.LinkColumn(label="ScoreDB", display_text="Link"),
        "avg_last_battles": st.column_config.NumberColumn(label="Srednia walk (30 dni)"),
        "Prospect": st.column_config.CheckboxColumn(default=False, disabled=True),
        "guild_join_date": st.column_config.DateColumn(label="Data dolaczenia", format="YYYY-MM-DD"),
        "world": None, "battlesDif": None, "pointsDif": None,
        "avg_last_points": None, "playerId": None, "ClanId": None,
        "_merge": None, "valid_to": None, "world_name": None,
    }


def _player_tabs(world: str, player_id: int) -> None:
    tab1, tab2, tab3, tab4 = st.tabs(["Historia komunikacji", "Historia Aktywnosci", "Historia Gildii", "Inne Swiaty"])
    with tab1:
        prospect_history_tab(player_id)
    with tab2:
        player_activity_tab(player_id)
    with tab3:
        guild_history_tab(world, player_id)
    with tab4:
        other_worlds_tab(world, player_id)


@st.fragment
def table_and_details(all_players, prospects, df_recruters, df_guilds, df_statuses, world) -> None:
    result = st.dataframe(all_players, hide_index=True, width="stretch",
                          on_select="rerun", selection_mode="single-row",
                          column_config=_players_dataframe_config())
    if not result.selection["rows"]:
        return
    idx = result.selection["rows"][0]
    player_id = int(all_players.iloc[idx]["playerId"])
    df_selected = all_players.iloc[[idx]]
    avg_battles = df_selected["avg_last_battles"].iloc[0]
    st.divider()
    RecruitmentForm.render(prospects, player_id, df_selected, df_recruters, df_guilds, df_statuses, world, avg_battles)
    _player_tabs(world, player_id)


@st.fragment
def prospect_history_tab(player_id: int) -> None:
    col1, col2 = st.columns([50, 5])
    col1.markdown("#### Historia komunikacji z graczem ####")
    col2.button("Refresh", on_click=clear_recruitment_cache)
    df = get_prospect_history()
    st.dataframe(
        df[df["playerId"] == player_id],
        column_config={
            "playerid": st.column_config.TextColumn(label="Id Gracza"),
            "Guild_name": st.column_config.TextColumn(label="Gildia"),
            "status_Name": st.column_config.TextColumn(label="Status"),
            "name": st.column_config.TextColumn(label="Rekruter"),
            "invitation_date": st.column_config.DateColumn(label="Data zaproszenia", format="YYYY-MM-DD"),
            "future_invitation_date": st.column_config.DateColumn(label="Data ponownej komunikacji", format="YYYY-MM-DD"),
            "last_change_date": st.column_config.DatetimeColumn(label="Data ostatniej zmiany", format="YYYY-MM-DD HH:mm:ss"),
            "notes": st.column_config.TextColumn(label="Notatki"),
            "world": None, "status_id": None, "recriterid": None, "Prospect": None,
        },
        width="stretch", hide_index=True,
    )


def _activity_chart(df, metric: str, pl_name: str) -> alt.Chart:
    line = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=False, fill="white", size=50))
        .encode(x=alt.X("Data_danych", title="Data danych"), y=alt.Y(metric, title=metric),
                color="world:N", tooltip=metric)
        .properties(title=f"Historia gry {pl_name} z ostatnich 30 dni")
    )
    ticks = alt.Chart(df).mark_tick(color="purple", thickness=2, size=18).encode(x="Data_danych", y="GPCh").properties(title="dzien GPCh")
    labels = line.mark_text(align="center", baseline="top", color="black", fontSize=13, dy=-30).encode(text=f"{metric}:Q")
    return (line + ticks + labels).interactive()


@st.fragment
def player_activity_tab(player_id: int) -> None:
    df = get_player_activity(player_id)
    if df.empty:
        st.info("Brak danych aktywnosci dla tego gracza.")
        return
    st.info("Dane dostepne od 2024-02-01")
    metric = st.radio("Wybierz metryki:", options=["Punty rankingowe", "Liczba bitew", "Roznica punktow rankingowych", "Roznica bitew"], horizontal=True, index=3)
    df_player = df[df["playerId"] == player_id]
    pl_name = df_player["name"].iloc[0] if not df_player.empty else ""
    coll1, coll2 = st.columns([5, 50])
    with coll1:
        st.markdown("**Wybierz Swiat:**")
        worlds = df_player.world.sort_values().unique().tolist()
        selected_worlds = [w for i, w in enumerate(worlds) if st.checkbox(w, value=True, key=f"world_cb_{i}")]
    with coll2:
        st.altair_chart(_activity_chart(df_player[df_player["world"].isin(selected_worlds)], metric, pl_name), width="stretch")


@st.fragment
def guild_history_tab(world: str, player_id: int) -> None:
    df = get_player_guild_history(world, player_id)
    st.info("Dane dostepne od 2024-02-01")
    st.dataframe(df[df["playerId"] == player_id].sort_values("Data dolaczenia"), width="stretch", hide_index=True, column_config={"playerId": None})


@st.fragment
def other_worlds_tab(world: str, player_id: int) -> None:
    df = get_player_other_worlds(world, player_id)
    st.dataframe(
        df[df["playerId"] == player_id],
        column_config={
            "world_name": st.column_config.TextColumn(label="Swiat"),
            "playerId": None, "world": None, "Ranking": None, "Player_link": None, "ClanId": None,
            "avg_last_battles": None, "avg_last_points": None, "valid_to": None,
            "avatar": st.column_config.ImageColumn(label="Avatar", width="small"),
        },
        width="stretch", hide_index=True,
    )


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA
# ---------------------------------------------------------------------------

def first_report() -> None:
    world = select_world()
    all_players_raw = get_all_players(world)
    df_ages = get_df_ages()
    df_guilds = get_guilds(world)
    df_recruters = get_df_recruters()
    df_statuses = get_statuses()
    prospects = get_prospect_history()
    all_players = build_all_players_view(all_players_raw, prospects)
    all_players = RecruitmentFilters.apply(all_players, df_guilds, df_ages, df_statuses)
    table_and_details(all_players, prospects, df_recruters, df_guilds, df_statuses, world)


def run_reports() -> None:
    st.subheader("Panel rekrutacyjny", anchor="Rekrutacja")
    first_report()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    page_header()

    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None

    authenticator, users, username = login()

    if username and st.session_state.get("authentication_status"):
        if check_user_role_permissions(username, "RECRUIT"):
            run_reports()
        else:
            st.warning("Nie masz dostepu do tej zawartosci.")
