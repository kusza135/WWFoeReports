import streamlit as st
import altair as alt
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id, get_guild_name
from tools.login import login, check_user_role_permissions
import numpy as np


# ---------------------------------------------------------------------------
# WARSTWA DANYCH
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def list_dates_wg(wg_cond: str) -> str:
    return f'''select distinct
CAST(report_date as CHAR(10))|| CASE
    WEEKDAY(report_date)
    when 0 then '  (Poniedziałek)'
    when 1 then '  (Wtorek)'
    when 2 then '  (Środa)'
    when 3 then '  (Czwartek)'
    when 4 then '  (Piątek)'
    when 5 then '  (Sobota)'
    when 6 then '  (Niedziela)'
END report_date
from V_WG WHERE 1=1 {wg_cond} '''


@st.cache_data(ttl=300)
def list_dates_gpc(gpc_cond: str) -> str:
    return f'''select distinct
CAST(report_date as CHAR(10))|| CASE
    WEEKDAY(report_date)
    when 0 then '  (Poniedziałek)'
    when 1 then '  (Wtorek)'
    when 2 then '  (Środa)'
    when 3 then '  (Czwartek)'
    when 4 then '  (Piątek)'
    when 5 then '  (Sobota)'
    when 6 then '  (Niedziela)'
END report_date
from V_GPCH WHERE 1=1 {gpc_cond} '''


@st.cache_data(ttl=300)
def list_dates(wg_checkbox: bool, gpc_checkbox: bool) -> list:
    wg_cond = 'AND wg_date_of_day=0' if wg_checkbox else ''
    gpc_cond = 'AND GPCH_DATE_OF_DAY=0' if gpc_checkbox else ''
    if wg_checkbox:
        qry = list_dates_wg(wg_cond)
    elif gpc_checkbox:
        qry = list_dates_gpc(gpc_cond)
    else:
        qry = f'{list_dates_wg(wg_cond)} \n UNION \n {list_dates_gpc(gpc_cond)}\n order by 1'
    return execute_query(qry, return_type="list")


@st.cache_data(ttl=300)
def list_wg_result_all(date_filter: str):
    return execute_query(
        f'''select
                report_date, name as "Player_name", Age_PL as "Epoka",
                wg_date_of_day as "WG_day", expeditionPoints,
                solvedEncounters AS "Wygrane_bitwy", "WG_LEVEL",
                currentTrial AS "Próba", "forecast"
        from V_WG where report_date = '{date_filter}' ''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_wg_result_catch(date_filter: str):
    return execute_query(
        f'''select
                report_date, name as "Player_name", Age_PL as "Epoka",
                wg_date_of_day as "WG_day", expeditionPoints,
                solvedEncounters AS "Wygrane_bitwy", WG_LEVEL,
                currentTrial AS "Próba", "forecast"
        from V_WG where report_date = '{date_filter}'
        AND solvedEncounters < "forecast" ''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_gpch_result_all(date_filter: str):
    return execute_query(
        f'''WITH all_players AS (
                SELECT playerId, ClanId, avatar
                FROM V_ALL_PLAYERS
                WHERE world = '{get_world_id()}'
                  AND '{date_filter[0:10]}' BETWEEN valid_from AND valid_to
            )
            SELECT
                report_date, player_id, avatar,
                V_GPCH.name as "Player_name", V_GPCH.Age_PL as "Epoka",
                GPCH_DATE_OF_DAY as "GPCH_day", "RANK",
                battlesWon, negotiationsWon,
                score AS "Wygrane_bitwy", "Forecast"
            FROM V_GPCH
            LEFT JOIN all_players tap
                ON tap.playerId = V_GPCH.player_id AND guild_id = tap.ClanId
            WHERE report_date = '{date_filter[0:10]}' ''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_gpch_result_catch(date_filter: str):
    return execute_query(
        f'''select
                report_date, name as "Player_name", Age_PL as "Epoka",
                GPCH_DATE_OF_DAY as "GPCH_day", "RANK",
                battlesWon, negotiationsWon,
                score AS "Wygrane_bitwy", forecast
        from V_GPCH
        where report_date = '{date_filter[0:10]}' AND score < forecast''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_nk_result_all(date_filter: str):
    return execute_query(
        f'''select
                report_date, player_id, name as "Player_name", Age_PL as "Epoka",
                NK_DATE_OF_DAY as "NK_day",
                progressContribution AS "Postęp", actionPoints AS "Działania", forecast
        from V_NK
        where report_date = '{date_filter[0:10]}'
          and world = '{get_world_id()}' and guild_id = {get_guild_id()}''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_nk_result_catch(date_filter: str):
    return execute_query(
        f'''select
                report_date, player_id, name as "Player_name", Age_PL as "Epoka",
                NK_DATE_OF_DAY as "NK_day",
                progressContribution AS "Postęp", actionPoints AS "Działania", forecast
        from V_NK
        where report_date = '{date_filter[0:10]}'
          and world = '{get_world_id()}' and guild_id = {get_guild_id()}
        AND actionPoints < forecast''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_guild_stats(date_filter: str):
    return execute_query(
        f'''WITH all_players AS (
                SELECT playerId, ClanId, avatar, guild_join_date
                FROM V_ALL_PLAYERS
                WHERE world = '{get_world_id()}'
                  AND '{date_filter[0:10]}' BETWEEN valid_from AND valid_to
            )
            SELECT
                V_GUILD_PLAYERS."RANK" AS "Rank", all_players.Avatar,
                V_GUILD_PLAYERS.name AS "Nick gracza", V_GUILD_PLAYERS.Age_PL AS "Epoka",
                V_GUILD_PLAYERS.won_battles "Wygrane bitwy", V_GUILD_PLAYERS.score "Punkty",
                V_GUILD_PLAYERS.TITLE "Tytuł",
                COALESCE(all_players.guild_join_date, V_GUILD_PLAYERS.join_date) "Data przyłączenia",
                V_GUILD_PLAYERS.leave_date AS "Data opuszczenia"
            FROM V_GUILD_PLAYERS
            LEFT JOIN all_players ON V_GUILD_PLAYERS.player_id = all_players.playerId
            WHERE '{date_filter[0:10]}' BETWEEN V_GUILD_PLAYERS.valid_from AND V_GUILD_PLAYERS.valid_to
            ORDER BY "RANK" ''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_change_nick_name():
    return execute_query(
        f'''SELECT old_name AS "Poprzedni nick", name as "Obecny nick", valid_to
            FROM (
                SELECT name,
                       lag(name) OVER (partition by player_id ORDER BY player_id) old_name,
                       valid_to
                FROM V_GUILD_PLAYERS
                WHERE player_id IN (SELECT player_id FROM V_GUILD_PLAYERS WHERE valid_to = '3000-12-31')
            ) x
            WHERE name <> old_name and old_name is not null''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_winners(date_filter: str):
    return execute_query(
        f'''SELECT world, ClanId, load_date, player_id, name
            FROM V_GPC_LOTTERY
            WHERE world = '{get_world_id()}'
              AND ClanId = {get_guild_id()}
              AND load_date = '{date_filter[0:10]}' ''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_GPCH_leader(date_filter: str, rank: int):
    return execute_query(
        f'''SELECT report_date, playerId, avatar, name, player_score, RN
            FROM (
                SELECT report_date, playerId, avatar, name, player_score,
                       ROW_NUMBER() OVER (PARTITION BY report_date ORDER BY player_score DESC) RN
                FROM (
                    SELECT report_date, playerId, avatar,
                           Foe_WW.V_GPCH.name name, max(score) player_score
                    FROM Foe_WW.V_ALL_PLAYERS tap
                    INNER JOIN Foe_WW.V_GPCH
                        ON tap.world = V_GPCH.world
                        AND playerId = player_id
                        AND tap.clanId = V_GPCH.guild_id
                    WHERE tap.world = '{get_world_id()}'
                      AND report_date = '{date_filter[0:10]}'
                      AND valid_from BETWEEN
                          DATE_ADD(report_date, INTERVAL CASE WHEN GPCH_DATE_OF_DAY=0 THEN -11 ELSE -GPCH_DATE_OF_DAY END DAY)
                          AND report_date
                    GROUP BY 1, 2, 3, 4
                    HAVING count(DISTINCT tap.Age_PL) = 1
                ) x
            ) y
            WHERE RN = {rank}''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def players_changed_age(date_filter: str):
    return execute_query(
        f'''SELECT report_date, playerId, avatar, name, player_score,
                   ROW_NUMBER() OVER (PARTITION BY report_date ORDER BY player_score DESC) RN
            FROM (
                SELECT report_date, playerId, avatar,
                       Foe_WW.V_GPCH.name name, max(score) player_score
                FROM Foe_WW.V_ALL_PLAYERS tap
                INNER JOIN Foe_WW.V_GPCH
                    ON playerId = player_id
                    AND tap.world = V_GPCH.world
                    AND tap.clanId = V_GPCH.guild_id
                WHERE tap.world = '{get_world_id()}'
                  AND report_date = '{date_filter[0:10]}'
                  AND valid_from BETWEEN
                      DATE_ADD(report_date, INTERVAL CASE WHEN GPCH_DATE_OF_DAY=0 THEN -11 ELSE -GPCH_DATE_OF_DAY END DAY)
                      AND report_date
                GROUP BY 1, 2, 3, 4
                HAVING count(DISTINCT tap.Age_PL) > 1
            ) x''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def list_gpc_lottery_exceptions():
    return execute_query(
        f'''SELECT player_id FROM t_gpc_lottery_exceptions
            WHERE world = '{get_world_id()}' AND ClanId = {get_guild_id()}''',
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_param_value(param_name: str):
    return execute_query(
        """SELECT JSON_UNQUOTE(json_extract(`Params`, '$.value')) AS Param_Value
           FROM t_params
           WHERE world = :world AND ClanId = :guildid
             AND json_extract(`Params`, '$.key') = :param_name""",
        params={"world": get_world_id(), "guildid": get_guild_id(), "param_name": param_name},
        return_type="df",
    )


# ---------------------------------------------------------------------------
# KLASY SEKCJI UI
# ---------------------------------------------------------------------------

class WgSection:
    @staticmethod
    def _status(data) -> None:
        day = data.iloc[0]['WG_day']
        if 0 < day < 7:
            st.markdown(f"*Wyprawy Gildyjne* są 🟢🟢 :green[w trakcie] 🟢🟢 day({day}).")
        else:
            st.markdown("*Wyprawy Gildyjne* są 🔴 :red[zakończone] 🔴.")

    @staticmethod
    def _chart_all(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar().encode(
            x=alt.X("Player_name", title='Nick Gracza'),
            y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
            color="WG_LEVEL",
            tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy", "Próba"],
        ).properties(title='Statystyka edycji WG', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='red', thickness=2, size=18).encode(
            x="Player_name", y="forecast"
        )
        return bar + tick

    @staticmethod
    def _chart_catch(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar(color='#e8513a').encode(
            x=alt.X("Player_name", title='Nick Gracza'),
            y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
            tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy", "Próba"],
        ).properties(title='Warto skontaktować się z', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='#47b552', thickness=2, size=18).encode(
            x="Player_name", y="forecast"
        )
        return bar + tick

    @staticmethod
    def render(date_filter: str) -> None:
        data_all = list_wg_result_all(date_filter)
        data_catch = list_wg_result_catch(date_filter)
        WgSection._status(data_all)
        col1, col2 = st.columns([1, 1])
        col1.altair_chart(WgSection._chart_all(data_all), width='stretch')
        col2.altair_chart(WgSection._chart_catch(data_catch), theme="streamlit", width='stretch')


class GpchSection:
    @staticmethod
    def _status(data) -> None:
        day = data.iloc[0]['GPCH_day']
        if 0 < day < 12:
            st.markdown(f"*Pola Chwały* są 🟢🟢 :green[w trakcie] 🟢🟢 day({day}).")
        else:
            st.markdown("*Pola Chwały* są 🔴 :red[zakończone] 🔴.")

    @staticmethod
    def _chart_all(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar().encode(
            x=alt.X("Player_name:N", title='Nick Gracza'),
            y=alt.Y("Wygrane_bitwy:Q", title='Wygrane bitwy'),
            tooltip=["Player_name:N", "Epoka:N", "battlesWon:Q", "negotiationsWon:Q"],
        ).properties(title='Statystyka edycji GPCh', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='red', thickness=2, size=18).encode(
            x="Player_name:N", y="forecast:Q"
        )
        return bar + tick

    @staticmethod
    def _chart_catch(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar(color='#e8513a').encode(
            x=alt.X("Player_name:N", title='Nick Gracza'),
            y=alt.Y("Wygrane_bitwy:Q", title='Wygrane bitwy'),
            tooltip=["Player_name:N", "Epoka:N", "battlesWon:Q", "negotiationsWon:Q"],
        ).properties(title='Warto skontaktować się z', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='#47b552', thickness=2, size=18).encode(
            x="Player_name:N", y="forecast:Q"
        )
        return bar + tick

    @staticmethod
    def render(date_filter: str) -> None:
        data_all = list_gpch_result_all(date_filter)
        data_catch = list_gpch_result_catch(date_filter)
        GpchSection._status(data_all)
        col1, col2 = st.columns([1, 1])
        col1.altair_chart(GpchSection._chart_all(data_all), width='stretch')
        col2.altair_chart(GpchSection._chart_catch(data_catch), theme="streamlit", width='stretch')


class NkSection:
    @staticmethod
    def _status(data) -> None:
        day = data.iloc[0]['NK_day']
        if 0 < day < 12:
            st.markdown(f"*Najazdy Kwantowe* są 🟢🟢 :green[w trakcie] 🟢🟢 day({day}).")
        else:
            st.markdown("*Najazdy Kwantowe* są 🔴 :red[zakończone] 🔴.")

    @staticmethod
    def _chart_all(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar().encode(
            x=alt.X("Player_name:N", title='Nick Gracza'),
            y=alt.Y("Postęp:Q", title='Postęp'),
            tooltip=["Player_name:N", "Epoka:N", "Postęp:Q", "Działania:Q"],
        ).properties(title='Statystyka edycji Najazdów Kwantowych', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='red', thickness=2, size=18).encode(
            x="Player_name:N", y="forecast:Q"
        )
        return bar + tick

    @staticmethod
    def _chart_catch(data) -> alt.Chart:
        bar = alt.Chart(data).mark_bar(color='#e8513a').encode(
            x=alt.X("Player_name:N", title='Nick Gracza'),
            y=alt.Y("Postęp:Q", title='Postęp'),
            tooltip=["Player_name:N", "Epoka:N", "Postęp:Q", "Działania:Q"],
        ).properties(title='Warto zachęcić', width=alt.Step(40)).interactive()
        tick = alt.Chart(data).mark_tick(color='#47b552', thickness=2, size=18).encode(
            x="Player_name:N", y="forecast:Q"
        )
        return bar + tick

    @staticmethod
    def render(date_filter: str) -> None:
        data_all = list_nk_result_all(date_filter)
        data_catch = list_nk_result_catch(date_filter)
        NkSection._status(data_all)
        col1, col2 = st.columns([1, 1])
        col1.altair_chart(NkSection._chart_all(data_all), width='stretch')
        col2.altair_chart(NkSection._chart_catch(data_catch), theme="streamlit", width='stretch')


class GpcStats:
    @staticmethod
    def _params_input() -> tuple:
        col1, col2, col3, col4 = st.columns([15, 15, 25, 50])
        player_pos = col1.number_input("Pozycja w tabeli", value=1, min_value=1, max_value=80)
        perc_ind = col2.number_input("Procent od wyniku", value=5, min_value=1, max_value=100) / 100
        player_pos2 = col1.number_input("Pozycja w tabeli", value=10, min_value=1, max_value=80)
        perc_ind2 = col2.number_input("Procent od wyniku", value=10, min_value=1, max_value=100) / 100
        player_activity = col3.radio("Gracze", options=['Wszyscy', 'Aktywni', 'Nieaktywni'], index=2)
        return player_pos, perc_ind, player_pos2, perc_ind2, player_activity

    @staticmethod
    def _leader_info(date_filter, player_pos, player_pos2, perc_ind, perc_ind2) -> tuple:
        gpc_leader = get_GPCH_leader(date_filter, player_pos)
        gpc_leader2 = get_GPCH_leader(date_filter, player_pos2)
        cc1, cc2 = st.columns([40, 30])
        s1 = int(round(gpc_leader['player_score'].iloc[0] * perc_ind, 0))
        s2 = int(round(gpc_leader2['player_score'].iloc[0] * perc_ind2, 0))
        cc1.markdown(f"TOP {player_pos} GPCH był **{gpc_leader['name'].iloc[0]}** z wynikiem **{gpc_leader['player_score'].iloc[0]}** walk. Wynik do osiągnięcia: **{s1}**")
        cc1.markdown(f"TOP {player_pos2} GPCH był **{gpc_leader2['name'].iloc[0]}** z wynikiem **{gpc_leader2['player_score'].iloc[0]}** walk. Wynik do osiągnięcia: **{s2}**")
        return gpc_leader, gpc_leader2, cc2

    @staticmethod
    def _changed_age_expander(cc2, date_filter: str) -> None:
        with cc2.expander("Gracze, którzy zmienili epokę ..."):
            st.dataframe(
                players_changed_age(date_filter),
                column_config={
                    "report_date": st.column_config.DateColumn(label="Data końca GPCh"),
                    "playerId": None, "RN": None,
                    "avatar": st.column_config.ImageColumn(label="Avatar", width="small"),
                    "name": st.column_config.TextColumn(label="Gracz"),
                    "player_score": st.column_config.NumberColumn(label="Wygrane Bitwy"),
                },
                hide_index=True, width='stretch',
            )

    @staticmethod
    def _highlight_survived(s):
        bad = (s.score_1 == False) or (s.score_2 == False)
        return ['background-color: #ebd8d8'] * len(s) if bad else ['background-color: #f5faf2'] * len(s)

    @staticmethod
    def _column_config(gpc_leader, gpc_leader2, t1: int, t2: int) -> dict:
        return {
            "report_date": st.column_config.DateColumn(label="Data końca GPCh"),
            "player_id": None, "rank": st.column_config.NumberColumn(label="Ranking"),
            "avatar": st.column_config.ImageColumn(label="Avatar", width="small"),
            "Player_name": st.column_config.TextColumn(label="Gracz"),
            "Epoka": st.column_config.TextColumn(label="Epoka"),
            "GPCH_day": None, "battlesWon": None, "negotiationsWon": None, "forecast": None,
            "Wygrane_bitwy": st.column_config.NumberColumn(label="Wygrane Bitwy"),
            "score_1": st.column_config.CheckboxColumn(label=f"Aktywność - {gpc_leader['name'].iloc[0]} ({t1})"),
            "score_2": st.column_config.CheckboxColumn(label=f"Aktywność - {gpc_leader2['name'].iloc[0]} ({t2})"),
        }

    @staticmethod
    def _results_table(date_filter, gpc_leader, gpc_leader2, perc_ind, perc_ind2, player_activity) -> None:
        gpc_results = list_gpch_result_all(date_filter)
        gpc_results['score_1'] = np.where(gpc_results['Wygrane_bitwy'] < gpc_leader['player_score'].iloc[0] * perc_ind, False, True)
        gpc_results['score_2'] = np.where(gpc_results['Wygrane_bitwy'] < gpc_leader2['player_score'].iloc[0] * perc_ind2, False, True)
        if player_activity == 'Aktywni':
            gpc_results = gpc_results[(gpc_results['score_1'] == True) | (gpc_results['score_2'] == True)]
        elif player_activity == 'Nieaktywni':
            gpc_results = gpc_results[(gpc_results['score_1'] == False) | (gpc_results['score_2'] == False)]
        t1 = int(round(gpc_leader['player_score'].iloc[0] * perc_ind, 0))
        t2 = int(round(gpc_leader2['player_score'].iloc[0] * perc_ind2, 0))
        st.dataframe(gpc_results.style.apply(GpcStats._highlight_survived, axis=1),
                     column_config=GpcStats._column_config(gpc_leader, gpc_leader2, t1, t2),
                     hide_index=True, width='stretch')

    @staticmethod
    def render(date_filter: str) -> None:
        st.subheader('Rozliczenia GPC', anchor='GPC stats', divider='rainbow')
        with st.expander(label="Parametry"):
            player_pos, perc_ind, player_pos2, perc_ind2, player_activity = GpcStats._params_input()
        if get_GPCH_leader(date_filter, player_pos).empty:
            return
        gpc_leader, gpc_leader2, cc2 = GpcStats._leader_info(date_filter, player_pos, player_pos2, perc_ind, perc_ind2)
        GpcStats._changed_age_expander(cc2, date_filter)
        GpcStats._results_table(date_filter, gpc_leader, gpc_leader2, perc_ind, perc_ind2, player_activity)


class LotterySection:
    @staticmethod
    def _lottery_css() -> None:
        st.markdown("""<style>
            .st-dd, .stTextInput > div > div > input, .stButton > button, .stSlider > div {
                vertical-align: middle !important; font-family: 'Inter'; font-size: 40px; font-weight: 500;
            }
            .stTextInput > div > div > input { margin-top: 5px !important; }
        </style>""", unsafe_allow_html=True)

    @staticmethod
    def _lottery_params(gpch_result_all) -> tuple:
        with st.expander(label="Ustawienia losowania"):
            col1, col2, col3, col4 = st.columns([40, 40, 20, 40])
            num_players = col1.number_input("Top osób biorących udział w losowaniu",
                                            step=1, value=30, min_value=1, max_value=len(gpch_result_all))
            num_winners = col2.number_input("Ile osób może wygrać w losowaniu",
                                            step=1, min_value=1, value=5, max_value=num_players)
        return num_players, num_winners

    @staticmethod
    def _do_draw(gpch_selected, date_filter: str, num_winners: int) -> None:
        exceptions = list_gpc_lottery_exceptions()
        eligible = gpch_selected[~gpch_selected["player_id"].isin(exceptions["player_id"])]
        winners = eligible.sample(n=num_winners)
        for ind in winners.index:
            pl_id = winners["player_id"][ind]
            execute_query(f"call p_gpc_lottery('{get_world_id()}', {get_guild_id()}, '{date_filter[0:10]}', {pl_id})", return_type="df")
        st.cache_data.clear()

    @staticmethod
    def _draw_form(gpch_result_all, date_filter: str) -> None:
        LotterySection._lottery_css()
        num_players, num_winners = LotterySection._lottery_params(gpch_result_all)
        gpch_selected = gpch_result_all[gpch_result_all["Wygrane_bitwy"].isin(
            gpch_result_all["Wygrane_bitwy"].nlargest(n=num_players)
        )]
        st.button("Wylosuj zwyciężców", type="primary",
                  on_click=LotterySection._do_draw, args=(gpch_selected, date_filter, num_winners))

    @staticmethod
    def _show_winners(check_winners) -> None:
        msg = "Gratulujemy poniższym graczom za wspólną zabawę:\n\n"
        for ind in check_winners.index:
            msg += f"\t{check_winners['name'][ind]}\n"
        msg += f"\n\nDziękujemy, że jesteście z Nami i wspieracie {get_guild_name()}."
        st.code(msg)

    @staticmethod
    def render(date_filter: str) -> None:
        if get_param_value('GPC Lottery module')["Param_Value"].iloc[0] != True:
            return
        gpch_result_all = list_gpch_result_all(date_filter)
        day = gpch_result_all.iloc[0]['GPCH_day']
        if 0 < day < 12:
            return
        st.subheader('Losowanie graczy  \n  \n', anchor='gpch', divider='rainbow')
        check_winners = list_winners(date_filter)
        if check_winners.empty:
            LotterySection._draw_form(gpch_result_all, date_filter)
        else:
            LotterySection._show_winners(check_winners)


# ---------------------------------------------------------------------------
# @st.fragment FUNKCJE UI
# ---------------------------------------------------------------------------

@st.fragment
def check_nick_name_change() -> None:
    qry = list_change_nick_name()
    if not qry.empty:
        st.warning('Poniżej gracze którzy zmienili nick', icon="⚠️")
        st.dataframe(qry, hide_index=True, width='stretch')


@st.fragment
def wg_reports(date_filter: str) -> None:
    st.subheader('Wyprawy Gildyjne  \n  \n', anchor='wg', divider='rainbow')
    try:
        WgSection.render(date_filter)
    except IndexError:
        st.error("Brak danych do wyświetlenia. Upewnij się, że Dane za WG są załadowane za wybrany dzień.", icon="🚨")


@st.fragment
def gpch_reports(date_filter: str) -> None:
    st.subheader('Pola Chwały  \n  \n', anchor='gpch', divider='rainbow')
    try:
        GpchSection.render(date_filter)
    except IndexError:
        st.error("Brak danych do wyświetlenia. Upewnij się, że Dane za GPC są załadowane za wybrany dzień.", icon="🚨")


@st.fragment
def nk_reports(date_filter: str) -> None:
    st.subheader('Najazdy Kwantowe  \n  \n', anchor='nk', divider='rainbow')
    try:
        NkSection.render(date_filter)
    except IndexError:
        st.error("Brak danych do wyświetlenia. Upewnij się, że NK są aktywne lub zakończone w wybranym dniu.", icon="🚨")


@st.fragment
def guild_stats(date_filter: str) -> None:
    st.subheader('Statystyki Gildii', anchor='guild', divider='rainbow')
    st.dataframe(list_guild_stats(date_filter), width='stretch', hide_index=True,
                 column_config={"avatar": st.column_config.ImageColumn(label="Avatar", width="small")})


@st.fragment
def new_approach(date_filter: str) -> None:
    GpcStats.render(date_filter)


@st.fragment
def lottery_top_gpch_players(date_filter: str) -> None:
    LotterySection.render(date_filter)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def _date_slider(wg_checkbox: bool, gpc_checkbox: bool) -> str:
    dates = [row[0] for row in list_dates(wg_checkbox, gpc_checkbox)]
    while len(dates) < 2:
        dates.append("_empty")
    return st.select_slider(label="Select a report date", options=dates,
                            value=max(dates), label_visibility="hidden")


def _render_all_sections(date_filter: str) -> None:
    for fn in [wg_reports, gpch_reports, nk_reports, new_approach, lottery_top_gpch_players, guild_stats]:
        st.text("\n\n\n")
        fn(date_filter)


def run_reports() -> None:
    check_nick_name_change()
    st.subheader("  ##  Filtr (suwak) po dacie  ## ")
    col1, col2, col3 = st.columns([15, 15, 50])
    wg_checkbox = col1.checkbox(label="Tylko koniec WG", value=False)
    gpc_checkbox = col2.checkbox(label="Tylko koniec GPC", value=False)
    date_filter = _date_slider(wg_checkbox, gpc_checkbox)
    if date_filter != "--":
        _render_all_sections(date_filter)


if __name__ == '__main__':
    page_header()
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    authenticator, users, username = login()
    if username and st.session_state['authentication_status']:
        if check_user_role_permissions(username, 'GPC_STATS'):
            run_reports()
        else:
            st.warning("Nie masz dostępu do tej zawartości.")
