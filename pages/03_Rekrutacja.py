import streamlit as st
import altair as alt
from streamlit_extras.stylable_container import stylable_container
from tools.streamlit_tools import execute_query, get_guild_id, get_world_id, page_header
from tools.login import login
import pandas as pd

dump_value = "-1z"
st.session_state['textmsg']= dump_value


def first_report():

    all_players = execute_query(
        f'''SELECT 
                world
                , playerId
                , Player_rank as "Ranking"
                , name Gracz
                , Player_link
                , ClanId
                , clanName Gildia
                , points "Punty Rankingowe"
                , battles "Wygrane Bitwy"
                , Age_PL "Epoka"
                , pointsDif "Zdobyte punkty (wczoraj)"
                , battlesDif "Walki (wczoraj)"
                , prospect as Prospect
                , avg_last_battles
                , avg_last_points
                , STATUS as "Status"
                , notes
            FROM V_all_players
            WHERE   
                world = '{get_world_id()}'  -- and (ClanId <> {get_guild_id()} or ClanId IS NULL) 
                and valid_to = '3000-12-31'
            ''',
                    return_type="df",
                )
    df_tabs_player_activity = execute_query(
        f'''SELECT 
                world
                , playerId
                , name
                , points as "Punty rankingowe"
                , battles as "Liczba bitew"
                , pointsDif as "Różnica punktów rankingowych"
                , battlesDif as "Różnica bitew"
                , CAST(DATE_ADD(valid_from, INTERVAL -1 DAY) AS CHAR) as Data_danych
            FROM V_all_players
            WHERE 
                world = '{get_world_id()}'  
                AND valid_from > DATE_ADD(CURRENT_DATE(), INTERVAL -30 DAY)
            ''',
                    return_type="df",
                )     
    df_tabs_player_other_worlds = execute_query(
        f'''SELECT 
                world_name "Świat"
                , playerId
                , name as "Gracz"
                , points as "Punty rankingowe"
                , battles as "Liczba Bitw"
                , pointsDif as "Różnica punktów rankingowych"
                , battlesDif as "Różnica bitw"
            FROM V_all_players
            WHERE world <> '{get_world_id()}'  AND valid_to = '3000-12-31'
            ''',
                    return_type="df",
                ) 
    df_player_guild_history = execute_query(
                f'''SELECT  
                        playerId
                        , name as Gracz
                        , clanName AS Gildia
                        , MIN(VALID_FROM) "Data dołączenia"
                        FROM V_all_players
                        WHERE world  = '{get_world_id()}'
                    GROUP BY playerId, Gracz, GILDIA
                    ''',
                            return_type="df",
                        ) 
    df_ages = execute_query(f'''SELECT id, Age_PL  FROM t_ages WHERE valid_to = '3000-12-31' ORDER BY id ''',return_type="df")
    df_guilds = execute_query(f'''SELECT clanId, name AS Gildia  FROM V_all_guilds WHERE world = '{get_world_id()}'  and clanId <> {get_guild_id()} ''',return_type="df")


    def exl_guids(df_guilds) -> list:
        modification_container = st.container()
        with modification_container:
            filters = []
            to_filter_columns = st.multiselect("Wybierz gildie", df_guilds.Gildia.sort_values().unique(),  placeholder="Rozwiń lub zacznij wpisywać")
            for row in to_filter_columns:
                df2=df_guilds.loc[df_guilds['Gildia'] == row, 'clanId'].iloc[0]
                filters.append(df2)
        return filters

    def inc_guids(df_guilds) -> list:
        modification_container = st.container()
        with modification_container:
            filters = []
            to_filter_columns = st.multiselect("Wybierz gildie", df_guilds.Gildia.sort_values().unique(),  placeholder="Rozwiń lub zacznij wpisywać")
            for row in to_filter_columns:
                df2=df_guilds.loc[df_guilds['Gildia'] == row, 'clanId'].iloc[0]
                filters.append(df2)
        return filters
    
    def select_ages(df_ages) -> list:
        modification_container = st.container()
        with modification_container:
            filters = []

            to_filter_columns = st.multiselect("Wybierz Epoki", df_ages.Age_PL.sort_index().unique(),  placeholder="Rozwiń lub zacznij wpisywać")
            for row in to_filter_columns:
                df2=df_ages.loc[df_ages['Age_PL'] == row, 'Age_PL'].iloc[0]
                filters.append(df2)
        return filters

    def tabs_player_activity(df_tabs_player_activity, Player_id):
        st.info("Dane dostępne od 2024-02-01 ")
        ops = st.radio(label="Wybierz metryki:", options=['Punty rankingowe', 'Liczba bitew', 'Różnica punktów rankingowych', 'Różnica bitew'], horizontal=True, index=3)
        # st.dataframe(tabs_player_activity)
        pl_name = df_tabs_player_activity[df_tabs_player_activity['playerId'] == Player_id]["name"].iloc[0]
        c= alt.Chart(df_tabs_player_activity[df_tabs_player_activity['playerId'] == Player_id]).mark_line(
                                point=alt.OverlayMarkDef(filled=False, fill="white", size=50)
                                        ).encode(
                                            x=alt.X("Data_danych", title='Data danych'),
                                            y=alt.Y(ops, title=ops)
                                            , tooltip=ops
                                        ).properties(
                                                    title=f"Historia gry {pl_name} z ostatnich 30 dni"
                                                    # width=alt.Step(400)  # controls width of bar.
                                                ).interactive()
        text = c.mark_text(
            align='center'
            , baseline='top'
            , color="black"
            , fontSize = 13
            , dy=-30  # Nudges text to right so it doesn't appear on top of the bar
            ).encode(
                text=f"{ops}:Q",
                )
        st.altair_chart(c + text, use_container_width=True)    
        
    def tabs_player_other_worlds(df_tabs_player_other_worlds, Player_id):
        st.dataframe(df_tabs_player_other_worlds[df_tabs_player_other_worlds['playerId'] == Player_id], use_container_width=True, hide_index= True)
        
    def guild_history(df_player_guild_history, Player_id):
        st.info("Dane dostępne od 2024-02-01 ")
        st.dataframe(
                df_player_guild_history[df_player_guild_history['playerId'] == Player_id].sort_values(by=["Data dołączenia"], ascending=True)
                , use_container_width=True
                , hide_index= True
                , column_config={"playerId" : None}
                )

        
        
    def dataframe_with_selections(df):
        df_with_selections = df.copy()
        df_with_selections.insert(0, "Select", False)

        # Get dataframe row-selections from user with st.data_editor
        edited_df = st.data_editor(
            df_with_selections,
            hide_index=True,
            use_container_width=True,
            column_config={
                            "Select": st.column_config.CheckboxColumn(required=True), 
                            "Player_link":  st.column_config.LinkColumn(label="Player_link", display_text="ScoreDB link"), 
                        "Prospect": st.column_config.CheckboxColumn(default=False), 
                        "world" : None,
                        "notes": None, 
                        "avg_last_battles": None, 
                        "avg_last_points": None, 
                        "playerId" : None,
                        "ClanId" : None
                        },
            disabled=( "Ranking", "Gracz", "Player_link", "Gildia", "Punty Rankingowe", "Wygrane Bitwy", "Epoka", "Zdobyte punkty (wczoraj)", "Walki (wczoraj)")
        )
        selected_player= ""
        # Filter the dataframe using the temporary column, then drop the column
        selected_rows = edited_df[edited_df.Select]
        if len(selected_rows)>1:
            st.error("Zanzacz tylko jeden rekord")
            return None
        if not selected_rows.empty:
            selected_player = selected_rows["playerId"].iloc[0]
            return selected_player
    
    

    with st.expander(label="Filtuj ...", expanded=True):
        col1, col2, col3, col4, col5 = st.columns([15,5,8,7,10])
        with col1.container():
            f_guilds = st.checkbox(label="Wyklucz/Oznacz wybrane gildie", value=False)
            if f_guilds:
                radio_guilds = st.radio(label="Gildie", options=['Wyklucz Gildie', 'Wybrane Gildie'], index=0, horizontal=True, label_visibility="hidden")
                if radio_guilds== 'Wyklucz Gildie':
                    f_exl_guilds = exl_guids(df_guilds)
                    all_players = all_players[~all_players['ClanId'].isin(f_exl_guilds)]
                elif radio_guilds== 'Wybrane Gildie':
                    f_inc_guilds = inc_guids(df_guilds)
                    all_players = all_players[all_players['ClanId'].isin(f_inc_guilds)]  
        with col2.container():
            homeless = st.radio(label="Gracze", options=['bez Gildii', 'w Gildii', 'Wszyscy'], index=2)
            if homeless == 'bez Gildii':
                all_players = all_players[all_players['ClanId'].isna()]
            elif homeless == 'w Gildii':
                all_players = all_players[~all_players['ClanId'].isna()]
            elif homeless == 'bez Gildii':
                None
        with col3.container():
            filter_by_activity = st.checkbox(label="Wyświetl tylko aktywnych", value=True)
            if filter_by_activity:
                choose_option = st.radio(label="Filtruj po", options=['Bitwy', 'Punkty'], index=0, horizontal=True, label_visibility="hidden")
                if choose_option == 'Bitwy':
                    number = st.number_input("Ilość średnia ilość walk (30 dni)", value=50, step=5)
                    all_players = all_players[all_players['avg_last_battles'] > number]  
                elif choose_option == 'Punkty':
                    number = st.number_input("Ilość średnia ilość punktów (30 dni)", value=300000, step=500)
                    all_players = all_players[all_players['avg_last_points'] > number]  
        with col4.container():
            x_select_ages = st.checkbox(label="Wybierz wybrane Epoki", value=False)
            if x_select_ages:
                f_select_ages = select_ages(df_ages)
                all_players = all_players[all_players['Epoka'].isin(f_select_ages)]
                            


    selected_player = dataframe_with_selections(all_players)


    tab1, tab2, tab3, tab4 = st.tabs(["Prospect", "Historia Aktywności Gracza", "Historia Gildii", "Inne Światy"])
    if  selected_player is not None:
        with tab2:
            tabs_player_activity(df_tabs_player_activity, selected_player)
        with tab3:
            guild_history(df_player_guild_history, selected_player)
        with tab4:
            tabs_player_other_worlds(df_tabs_player_other_worlds, selected_player)


def run_reports():
    st.subheader(" ##  Panel rekrutacyjny  ## ", anchor='Rekrutacja')  
    first_report()

        
if __name__ == '__main__':
    st.set_page_config(
        page_title="WW Stats",
        page_icon=".streamlit//logo.png",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'http://www.google_com/',
            'Report a Bug' : 'mailto:adamus01@gmail.com', 
            'About': "# This apps may help to monitor guild health."
        }
    ) 
    page_header()
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    login()
    if st.session_state['authenticator_status']:
        run_reports()

