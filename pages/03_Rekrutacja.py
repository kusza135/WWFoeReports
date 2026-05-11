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
# WARSTWA DANYCH — tylko @st.cache_data / @st.cache_resource, zero UI
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
def build_all_players_view(
    all_players_raw: pd.DataFrame, prospects: pd.DataFrame
) -> pd.DataFrame:
    """Laczy graczy z ich ostatnim statusem rekrutacji."""
    if prospects.empty:
        result = all_players_raw.copy()
        result["Prospect"] = None
        result["Status"] = None
        return result

    latest_prospects = (
        prospects
        .sort_values("last_change_date")
        .groupby("playerId", as_index=False)
        .last()[["playerId", "Prospect", "status_Name"]]
    )
    result = all_players_raw.merge(
        latest_prospects, on="playerId", how="left", indicator=True
    )
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
    world_selected = st.radio(
        label="Wybierz Swiat:", options=worlds_names,
        index=selected_id, horizontal=True,
    )
    return worlds_id[get_index_func(worlds_names, world_selected)]


def exec_prospect_sp(
    sp_name: str,
    p_world: str,
    p_guildid: int,
    p_player_id: int,
    p_status_id: int,
    p_recruiter_id: int,
    p_player_guild_id=None,
    p_invitation_date=None,
    p_future_invitation_date=None,
    p_notes=None,
) -> None:
    """Wywoluje procedure skladowana dla rekrutacji z commitem."""
    con = create_engine()
    # NaN -> 0 dla guild_id
    if p_player_guild_id != p_player_guild_id:
        p_player_guild_id = 0
    p_invitation_date = p_invitation_date or ""
    p_future_invitation_date = p_future_invitation_date or ""
    p_notes = p_notes or ""

    try:
        conn = con.raw_connection()
        cur = conn.cursor()
        cur.callproc(
            sp_name,
            args=[
                p_world, p_guildid, p_player_id, p_player_guild_id,
                int(p_status_id), int(p_recruiter_id),
                p_invitation_date, p_future_invitation_date, p_notes,
            ],
        )
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

def apply_filters(
    all_players: pd.DataFrame,
    df_guilds: pd.DataFrame,
    df_ages: pd.DataFrame,
    df_statuses: pd.DataFrame,
) -> pd.DataFrame:
    with st.expander("Filtruj...", expanded=True):
        col1, col2, col3, col4, col5 = st.columns([15, 5, 8, 8, 10])

        with col1:
            if st.checkbox("Wyklucz/Oznacz wybrane gildie", value=False):
                mode = st.radio(
                    "Gildie", options=["Wyklucz Gildie", "Wybrane Gildie"],
                    index=1, horizontal=True, label_visibility="hidden",
                )
                selected_guilds = st.multiselect(
                    "Wybierz gildie",
                    df_guilds.Gildia.sort_values().unique(),
                    placeholder="Rozwij lub zacznij wpisywac",
                )
                if selected_guilds:
                    clan_ids = df_guilds.loc[
                        df_guilds["Gildia"].isin(selected_guilds), "clanId"
                    ].tolist()
                    if mode == "Wyklucz Gildie":
                        all_players = all_players[~all_players["ClanId"].isin(clan_ids)]
                    else:
                        all_players = all_players[all_players["ClanId"].isin(clan_ids)]

            if st.checkbox("Wybrany Gracz", value=False):
                selected_names = st.multiselect(
                    "Wybierz gracza",
                    all_players.Gracz.sort_values().unique(),
                    max_selections=4,
                    placeholder="Rozwij lub zacznij wpisywac",
                )
                if selected_names:
                    player_ids = all_players.loc[
                        all_players["Gracz"].isin(selected_names), "playerId"
                    ].tolist()
                    all_players = all_players[all_players["playerId"].isin(player_ids)]

        with col2:
            homeless = st.radio(
                "Gracze", options=["bez Gildii", "w Gildii", "Wszyscy"], index=2
            )
            if homeless == "bez Gildii":
                all_players = all_players[all_players["ClanId"].isna()]
            elif homeless == "w Gildii":
                all_players = all_players[all_players["ClanId"].notna()]

        with col3:
            if st.checkbox("Wyswietl tylko aktywnych", value=False):
                metric = st.radio(
                    "Filtruj po", options=["Bitwy", "Punkty"],
                    index=0, horizontal=True, label_visibility="hidden",
                )
                if metric == "Bitwy":
                    threshold = st.number_input(
                        "Srednia ilosc walk (30 dni)", value=50, step=5
                    )
                    all_players = all_players[all_players["avg_last_battles"] > threshold]
                else:
                    threshold = st.number_input(
                        "Srednia ilosc punktow (30 dni)", value=300_000, step=500
                    )
                    all_players = all_players[all_players["avg_last_points"] > threshold]

        with col4:
            if st.checkbox("Wybierz Epoki", value=False):
                selected_ages = st.multiselect(
                    "Wybierz Epoki",
                    df_ages.Age_PL.sort_index().unique(),
                    placeholder="Rozwij lub zacznij wpisywac",
                )
                if selected_ages:
                    all_players = all_players[all_players["Epoka"].isin(selected_ages)]

        with col5:
            if st.checkbox("Rekrutacja", value=False):
                selected_statuses = st.pills(
                    "Status",
                    options=df_statuses.status_Name.sort_index().unique().tolist(),
                    selection_mode="multi",
                    format_func=str,
                    label_visibility="hidden",
                )
                if selected_statuses:
                    all_players = all_players[
                        all_players["Status"].isin(selected_statuses)
                    ]

    return all_players


# ---------------------------------------------------------------------------
# KOMPONENTY UI
# ---------------------------------------------------------------------------

@st.fragment
def table_and_details(
    all_players: pd.DataFrame,
    prospects: pd.DataFrame,
    df_recruters: pd.DataFrame,
    df_guilds: pd.DataFrame,
    df_statuses: pd.DataFrame,
    world: str,
) -> None:
    """
    Jeden fragment zawierajacy tabele i szczegoly gracza.
    Dzieki temu klikniecie wiersza rerenderuje ten fragment
    (tabela + szczegoly) ale NIE reszty strony (filtry, dane globalne).
    To jest wlasciwy wzorzec dla on_select w Streamlit.
    """
    result = st.dataframe(
        all_players,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "avatar": st.column_config.ImageColumn(label="Avatar", width="small"),
            "Player_link": st.column_config.LinkColumn(
                label="ScoreDB", display_text="Link"
            ),
            "avg_last_battles": st.column_config.NumberColumn(
                label="Srednia walk (30 dni)"
            ),
            "Prospect": st.column_config.CheckboxColumn(default=False, disabled=True),
            "guild_join_date": st.column_config.DateColumn(
                label="Data dolaczenia", format="YYYY-MM-DD"
            ),
            "world": None, "battlesDif": None, "pointsDif": None,
            "avg_last_points": None, "playerId": None, "ClanId": None,
            "_merge": None, "valid_to": None, "world_name": None,
        },
    )

    if not result.selection["rows"]:
        return

    idx = result.selection["rows"][0]
    player_id = int(all_players.iloc[idx]["playerId"])
    df_selected = all_players.iloc[[idx]]
    avg_battles = df_selected["avg_last_battles"].iloc[0]

    st.divider()

    recruitment_form(
        prospects, player_id, df_selected,
        df_recruters, df_guilds, df_statuses,
        world, avg_battles,
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Historia komunikacji",
        "Historia Aktywnosci",
        "Historia Gildii",
        "Inne Swiaty",
    ])
    with tab1:
        prospect_history_tab(player_id)
    with tab2:
        player_activity_tab(player_id)
    with tab3:
        guild_history_tab(world, player_id)
    with tab4:
        other_worlds_tab(world, player_id)


def recruitment_form(
    prospect_history: pd.DataFrame,
    player_id: int,
    df_selected: pd.DataFrame,
    df_recruters: pd.DataFrame,
    df_guilds: pd.DataFrame,
    df_statuses: pd.DataFrame,
    world: str,
    avg_battles: float,
) -> None:
    """Formularz rekrutacyjny dla wybranego gracza."""
    df_history = prospect_history[prospect_history["playerId"] == player_id]
    df_active = (
        df_history[
            df_history["last_change_date"] == df_history["last_change_date"].max()
        ]
        if not df_history.empty
        else pd.DataFrame()
    )

    st.markdown(f"#### Rekrutacja Gracza {df_selected['Gracz'].iloc[0]} ####")
    col1, col2, col3, col4 = st.columns([15, 15, 30, 30])

    col1.markdown(f"Gracz: **:blue[{df_selected['Gracz'].iloc[0]}]**")
    col1.markdown(f"Epoka: **{df_selected['Epoka'].iloc[0]}**")
    col2.markdown(f"Gildia: **{df_selected['Gildia'].iloc[0]}**")

    clan_id = df_selected["ClanId"].iloc[0]
    guild_match = df_guilds[df_guilds["clanId"] == clan_id]
    num_members = (
        0 if pd.isna(clan_id) or guild_match.empty
        else guild_match["members"].iloc[0]
    )
    col2.markdown(f"Liczba graczy w Gildii: **{num_members}**")

    # Rekruter
    active_recruters = df_recruters[df_recruters["is_active"] == True]
    recruiter_idx = None
    if not df_active.empty and "recriterid" in df_active.columns:
        recruiter_idx = get_index_func(
            active_recruters.playerId.tolist(),
            df_active["recriterid"].iloc[0],
        )
    selected_recruit = col3.selectbox(
        "Rekruter",
        options=active_recruters.name.sort_values().unique(),
        index=recruiter_idx,
    )
    selected_recruit_id = (
        active_recruters.loc[
            active_recruters["name"] == selected_recruit, "playerId"
        ].iloc[0]
        if selected_recruit else None
    )

    # Data zaproszenia
    inv_date_val = date.today()
    if not df_active.empty and "invitation_date" in df_active.columns:
        raw = df_active["invitation_date"].iloc[0]
        if pd.notna(raw):
            inv_date_val = raw
    inv_date = col3.date_input(
        "Data zaproszenia", value=inv_date_val, format="YYYY-MM-DD"
    )

    # Status
    status_idx = 0
    if not df_active.empty and "status_id" in df_active.columns:
        status_idx = get_index_func(
            df_statuses.status_id.tolist(),
            df_active["status_id"].iloc[0],
        ) or 0
    selected_status = col4.selectbox(
        "Status",
        options=df_statuses.status_Name.sort_index().unique(),
        index=status_idx,
    )
    selected_status_id = (
        df_statuses.loc[
            df_statuses["status_Name"] == selected_status, "status_id"
        ].iloc[0]
        if selected_status else None
    )

    next_comm_date = None
    if selected_status == "Zawieszono":
        next_comm_date = col4.date_input(
            "Data nastepnej komunikacji",
            value=date.today() + timedelta(days=60),
            min_value=date.today(),
            format="YYYY-MM-DD",
        )

    col0, col_metric, col_notes = st.columns([8, 22, 60])
    col0.image(df_selected["avatar"].iloc[0])
    col_metric.metric("Srednia walk (30 dni)", value=avg_battles)

    with col_notes:
        add_text = st.text_area("Uwagi:")
        btn_disabled = not (selected_recruit_id and selected_status_id)

        if world != get_world_id():
            st.error("Mozesz rekrutowac tylko w swoim swiecie")
        else:
            if st.button("Zapisz zmiany", type="primary", disabled=btn_disabled):
                exec_prospect_sp(
                    "p_prospect_history",
                    get_world_id(), get_guild_id(), player_id,
                    selected_status_id, selected_recruit_id,
                    clan_id, inv_date, next_comm_date, add_text,
                )
                clear_recruitment_cache()
                st.toast("Zmiany wprowadzone", icon="✅")
                st.rerun()


@st.fragment
def prospect_history_tab(player_id: int) -> None:
    """Tab z historia komunikacji z graczem."""
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
            "invitation_date": st.column_config.DateColumn(
                label="Data zaproszenia", format="YYYY-MM-DD"
            ),
            "future_invitation_date": st.column_config.DateColumn(
                label="Data ponownej komunikacji", format="YYYY-MM-DD"
            ),
            "last_change_date": st.column_config.DatetimeColumn(
                label="Data ostatniej zmiany", format="YYYY-MM-DD HH:mm:ss"
            ),
            "notes": st.column_config.TextColumn(label="Notatki"),
            "world": None, "status_id": None,
            "recriterid": None, "Prospect": None,
        },
        width="stretch",
        hide_index=True,
    )


@st.fragment
def player_activity_tab(player_id: int) -> None:
    """Tab z historia aktywnosci gracza."""
    df = get_player_activity(player_id)
    if df.empty:
        st.info("Brak danych aktywnosci dla tego gracza.")
        return

    st.info("Dane dostepne od 2024-02-01")
    metric = st.radio(
        "Wybierz metryki:",
        options=[
            "Punty rankingowe", "Liczba bitew",
            "Roznica punktow rankingowych", "Roznica bitew",
        ],
        horizontal=True,
        index=3,
    )

    df_player = df[df["playerId"] == player_id]
    pl_name = df_player["name"].iloc[0] if not df_player.empty else ""

    coll1, coll2 = st.columns([5, 50])
    with coll1:
        st.markdown("**Wybierz Swiat:**")
        worlds = df_player.world.sort_values().unique().tolist()
        selected_worlds = [
            w for i, w in enumerate(worlds)
            if st.checkbox(w, value=True, key=f"world_cb_{i}")
        ]

    df_filtered = df_player[df_player["world"].isin(selected_worlds)]

    with coll2:
        line = (
            alt.Chart(df_filtered)
            .mark_line(point=alt.OverlayMarkDef(filled=False, fill="white", size=50))
            .encode(
                x=alt.X("Data_danych", title="Data danych"),
                y=alt.Y(metric, title=metric),
                color="world:N",
                tooltip=metric,
            )
            .properties(title=f"Historia gry {pl_name} z ostatnich 30 dni")
        )
        ticks = (
            alt.Chart(df_filtered)
            .mark_tick(color="purple", thickness=2, size=18)
            .encode(x="Data_danych", y="GPCh")
            .properties(title="dzien GPCh")
        )
        labels = line.mark_text(
            align="center", baseline="top",
            color="black", fontSize=13, dy=-30,
        ).encode(text=f"{metric}:Q")

        st.altair_chart((line + ticks + labels).interactive(), width="stretch")


@st.fragment
def guild_history_tab(world: str, player_id: int) -> None:
    """Tab z historia gildii gracza."""
    df = get_player_guild_history(world, player_id)
    st.info("Dane dostepne od 2024-02-01")
    st.dataframe(
        df[df["playerId"] == player_id].sort_values("Data dolaczenia"),
        width="stretch",
        hide_index=True,
        column_config={"playerId": None},
    )


@st.fragment
def other_worlds_tab(world: str, player_id: int) -> None:
    """Tab z aktywnoscia gracza na innych swiatach."""
    df = get_player_other_worlds(world, player_id)
    st.dataframe(
        df[df["playerId"] == player_id],
        column_config={
            "world_name": st.column_config.TextColumn(label="Swiat"),
            "playerId": None, "world": None, "Ranking": None,
            "Player_link": None, "ClanId": None,
            "avg_last_battles": None, "avg_last_points": None,
            "valid_to": None,
            "avatar" : st.column_config.ImageColumn(label="Avatar", width="small")
        },
        width="stretch",
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA
# ---------------------------------------------------------------------------

def first_report() -> None:
    world = select_world()

    # Dane cache'owane — przy rerenderze nie trafiaja do bazy
    all_players_raw = get_all_players(world)
    df_ages         = get_df_ages()
    df_guilds       = get_guilds(world)
    df_recruters    = get_df_recruters()
    df_statuses     = get_statuses()
    prospects       = get_prospect_history()

    all_players = build_all_players_view(all_players_raw, prospects)
    all_players = apply_filters(all_players, df_guilds, df_ages, df_statuses)

    # Jeden fragment: tabela + szczegoly gracza
    # Klikniecie wiersza rerenderuje ten fragment, nie cala strone
    table_and_details(
        all_players, prospects,
        df_recruters, df_guilds, df_statuses,
        world,
    )


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