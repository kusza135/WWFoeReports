import streamlit as st
import altair as alt
# from streamlit_extras.stylable_container import stylable_container
from tools.streamlit_tools import execute_query, get_guild_id, get_world_id, page_header, create_engine
from tools.login import login, check_user_role_permissions
import pandas as pd
from datetime import date, timedelta
import numpy as np
import time

dump_value = "-1z"
st.session_state['textmsg']= dump_value

@st.cache_data(ttl=0, experimental_allow_widgets=True)
def get_prospect_history():
    sql_prospect_def = f'''SELECT 
                                            world
                                            , Guild_name
                                            , 'True' As Prospect
                                            , playerId
                                            , status_id
                                            , status_Name
                                            , recriterid
                                            , name
                                            , invitation_date
                                            , future_invitation_date
                                            , last_change_date
                                            , notes  
                                        FROM 
                                            v_prospects 
                                        WHERE
                                            world = '{get_world_id()}' 
                                            AND guildid = {get_guild_id()}
                                            '''
    df_prospect_def = execute_query(sql_prospect_def,return_type="df")
    return df_prospect_def
@st.cache_resource(ttl=14400, experimental_allow_widgets=True, show_spinner="Pobieranie danych (wszyscy gracze) ...")
def get_all_players():
    all_players_worlds = execute_query(
        f'''SELECT 
                world
                , world_name
                , playerId
                , Player_rank as "Ranking"
                , name Gracz
                , Player_link
                , ClanId
                , clanName Gildia
                , points "Punty Rankingowe"
                , battles "Wygrane Bitwy"
                , Age_PL "Epoka"
                , pointsDif
                , battlesDif
                , avg_last_battles
                , avg_last_points
                , valid_to
            FROM V_all_players
            WHERE
                world = '{get_world_id()}'
                AND valid_to = '3000-12-31'
            ''',
                    return_type="df",
                )
    return all_players_worlds
@st.cache_resource(ttl=14400, experimental_allow_widgets=True, show_spinner="Pobieranie danych (wszyscy gracze) ...")
def get_player_other_worlds(Player_id):
    df_tabs_player_other_worlds = execute_query(
        f'''SELECT 
                world
                , world_name
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
                , avg_last_battles
                , avg_last_points
                , valid_to
            FROM V_all_players
            WHERE 
                world != '{get_world_id()}'
                AND playerId = {Player_id}
                AND valid_to = '3000-12-31'
            ''',
                    return_type="df",
                )
    return df_tabs_player_other_worlds
@st.cache_resource(ttl=28800, experimental_allow_widgets=True, show_spinner="Pobieranie danych (aktywność graczy) ...")
def get_player_activity(Player_id):
    player_activity = execute_query(
    f'''SELECT 
            world
            , playerId
            , name
            , points as "Punty rankingowe"
            , battles as "Liczba bitew"
            , pointsDif as "Różnica punktów rankingowych"
            , battlesDif as "Różnica bitew"
            , CAST(DATE_ADD(valid_from, INTERVAL -1 DAY) AS CHAR) as Data_danych
            , case when f_gpch_day(DATE_ADD(valid_from, INTERVAL -1 DAY)) > 0 then 500 else 0 END GPCh
        FROM V_all_players
        WHERE 
            valid_from > DATE_ADD(CURRENT_DATE(), INTERVAL -30 DAY)
            AND playerId = {Player_id}
        ''',
                return_type="df",
            )
    return player_activity
@st.cache_resource(ttl=28800, experimental_allow_widgets=True, show_spinner="Pobieranie danych (historia gildii) ...")
def get_player_guild_history(Player_id):
    df_player_guild_history = execute_query(
                f'''SELECT  
                        playerId
                        , name as Gracz
                        , clanName AS Gildia
                        , joinDate AS "Data dołączenia"
                        FROM t_player_guild_history
                        WHERE world  = '{get_world_id()}'
                        AND playerId  = {Player_id}
                    ''',
                            return_type="df",
                        ) 
    return df_player_guild_history
@st.cache_resource(ttl=28800, experimental_allow_widgets=True, show_spinner="Pobieranie danych (epoki) ...")
def get_df_ages():
    df_ages = execute_query(f'''SELECT id, Age_PL  FROM t_ages WHERE valid_to = '3000-12-31' ORDER BY id ''',return_type="df")
    return df_ages
@st.cache_resource(ttl=28800, experimental_allow_widgets=True, show_spinner="Pobieranie danych (wszystkie gildie) ...")
def get_guilds():
    df_guilds = execute_query(f'''SELECT clanId, name AS Gildia, members  FROM V_all_guilds WHERE world = '{get_world_id()}' -- and clanId <> {get_guild_id()} ''',return_type="df")
    return df_guilds

@st.cache_resource(ttl=0, experimental_allow_widgets=True, show_spinner="Pobieranie danych (rekruterzy) ...")
def get_df_recruters():
    df_recruters = execute_query(f'''SELECT playerId, name, is_active FROM v_recruters WHERE world = '{get_world_id()}' and guildid = {get_guild_id()} ''',return_type="df")
    return df_recruters
@st.cache_resource(ttl=0, experimental_allow_widgets=True, show_spinner="Pobieranie danych (statusy) ...")
def get_statuses():
    df_statuses = execute_query(f'''SELECT  status_id, status_Name FROM t_statuses WHERE module_name = 'PROSPECT' ''',return_type="df")
    return df_statuses

@st.cache_data(ttl=0, experimental_allow_widgets=True)
def get_all_players_from_raw(all_players_raw, prospects):
    prospects_only_last_rows = prospects.merge(prospects.groupby(['playerId'])['last_change_date'].max(), on=['playerId', 'last_change_date'])[["playerId", "Prospect","status_Name"]]
    all_players_raw = all_players_raw.merge(prospects_only_last_rows, on='playerId', how='left', indicator=True)
    all_players_raw.rename(columns = {'status_Name':'Status'}, inplace = True) 
    # st.write(all_players_raw)
    return all_players_raw
    

def first_report():

    all_players_raw = get_all_players()
    df_ages = get_df_ages()
    df_guilds = get_guilds()
    df_recruters = get_df_recruters()
    df_statuses = get_statuses()

    all_players = get_all_players_from_raw(all_players_raw, get_prospect_history())

    def tabs_player_prospect(df_prospect_def, Player_id, df_selected_player, df_recruters, delta_number_battles):
        
        def get_index_func(LOV, current_value):
            for (index, item) in enumerate(LOV):
                if item == current_value:
                    return index
            return None
        
        df_historical_data = df_prospect_def[df_prospect_def['playerId'] == Player_id]
        df_active_row = df_historical_data[df_historical_data['last_change_date'] == df_historical_data["last_change_date"].max()]
        
        st.markdown(body=f"#### Rekrutacja Gracza {df_selected_player['Gracz'].iloc[0]} ####")
        col1, col2, col3, col4 = st.columns([15, 15, 30, 30])
        col1.markdown(f"Gracz: **:blue[{df_selected_player['Gracz'].iloc[0]}]**")
        col1.markdown(f"Epoka: **{df_selected_player['Epoka'].iloc[0]}**")
        col2.markdown(f"Gildia: **{df_selected_player['Gildia'].iloc[0]}**")
        if np.isnan(df_selected_player['ClanId'].iloc[0]):
            num_of_guild_players = 0
        else: 
            num_of_guild_players = df_guilds[df_guilds['clanId'] == df_selected_player['ClanId'].iloc[0]].members.iloc[0]
        col2.markdown(f"Liczba graczy w Gildii: **{num_of_guild_players}**")

        
        df_active_recruters = df_recruters[df_recruters["is_active"]==True].name.sort_index().unique()
        if df_active_row['recriterid'].empty:
            recruit_index = None
        else:
            recruit_index=get_index_func(df_recruters[df_recruters["is_active"]==True].playerId.sort_index().unique().tolist(), df_active_row['recriterid'].iloc[0])
        
        selected_recruit = col3.selectbox(label="Rekruter", options=df_active_recruters, index=recruit_index)
        if selected_recruit:
            selected_recruit_id = df_recruters[df_recruters['name'] == selected_recruit].playerId.iloc[0]
        # selected_recruit_id = ', '.join([str(recr) for recr in np.where(df_active_recruters == selected_recruit)[0]])
        
        # inv_date_val = df_active_row['invitation_date'].iloc[0]
        if df_active_row['invitation_date'].empty:
            inv_date_val = date.today()
        else:
            inv_date_val = df_active_row['invitation_date'].iloc[0]
        inv_date = col3.date_input(label="Data zaproszenia", value=inv_date_val, format="YYYY-MM-DD", disabled=False, label_visibility="visible")
        
        
        if df_active_row['status_id'].empty:
            status_index = 0
        else:
            status_index=get_index_func(df_statuses.status_id.sort_index().unique().tolist(), df_active_row['status_id'].iloc[0])
        
        selected_status = col4.selectbox(label="## Status ##", options=df_statuses.status_Name.sort_index().unique(), index=status_index)
        if selected_status:
            selected_status_id = df_statuses[df_statuses['status_Name'] == selected_status].status_id.iloc[0]
        # selected_status_id = ', '.join([str(stat) for stat in np.where(df_statuses == selected_status)[0]])
        
        
        selected_next_communication_date = None        
        if selected_status == "Zawieszono":
            selected_next_communication_date = col4.date_input(label="Data następnej komunikacji", value=date.today()+ timedelta(days=60), min_value=date.today(), format="YYYY-MM-DD", disabled=False, label_visibility="visible")
       
        col0, col1_tmp, col2_tmp = st.columns([8,22,60])
        with col1_tmp.container():
            # st.write("###")
            st.metric(label="Średnia ilość walk (30 dni)", value=df_selected_player['avg_last_battles'].iloc[0], delta=delta_number_battles, delta_color="normal", help=None, label_visibility="visible")
        with col2_tmp.container():
            add_text = st.text_area(label="Uwagi:")
            if 'selected_recruit_id' in locals() and 'selected_status_id' in locals():
                if selected_recruit_id is None:
                    brn_disabled = True
                if selected_recruit_id and selected_status_id: 
                    brn_disabled = False
                    # st.write(int(selected_recruit_id), int(selected_status_id), inv_date, selected_next_communication_date, add_text)
                    if st.button(label="Zapisz zmiany", on_click=exec_sp, args=('p_prospect_history', get_world_id(), get_guild_id(), Player_id,  selected_status_id, selected_recruit_id, df_selected_player['ClanId'].iloc[0], inv_date, selected_next_communication_date, add_text), type="primary", disabled=brn_disabled):
                        selected_recruit_id = None
                        button_cb()
                        st.success("Zmiany wprowadzone")
                        st.rerun()
                        

        
    def exec_sp(sp_name, p_world,  p_guildid,  p_playerId, p_status_id,  p_recriterid,  p_playerGuildId = None, p_invitation_date = None,  p_future_invitation_date = None,  p_notes= None):
        con = create_engine()
        if p_playerGuildId != p_playerGuildId:
            p_playerGuildId = 0
        if p_invitation_date is None:
            p_invitation_date = ''
        if p_future_invitation_date is None:
            p_future_invitation_date = ''
        if p_notes is None:
            p_notes = ''
        try:
            conn = con.raw_connection()
            cur = conn.cursor()
            cur.callproc(sp_name, args=[p_world, p_guildid, p_playerId, p_playerGuildId,  int(p_status_id),  int(p_recriterid),  p_invitation_date,   p_future_invitation_date,  p_notes])
            cur.close() 
        except Exception as e:
            st.error(e)
            time.sleep(20)
        finally:
            conn.close()

    def button_cb():
        get_prospect_history.clear()
        get_all_players_from_raw.clear()
        # dataframe_with_selections.clear()
        st.cache_data.clear()

    def prospect_history(Player_id):
            # st.rerun()
        col1, col2 = st.columns([50, 5])
        get_prospect_history.clear()
        df_prospect_def = get_prospect_history()
        df_historical_data = df_prospect_def[df_prospect_def['playerId'] == Player_id]
        col1.markdown("#### Historia komunikacji z graczem ####")
        col2.button("Refresh", on_click=button_cb ) 
        
        # df_historical_data = df_prospect_def[df_prospect_def['playerId'] == Player_id]
        st.dataframe(df_historical_data, column_config={
                            "playerid":  st.column_config.TextColumn(label="Id Gracza"),
                            "Guild_name": st.column_config.TextColumn(label="Gildia"), 
                        "status_Name": st.column_config.TextColumn(label="Status"), 
                        "name": st.column_config.TextColumn(label="Rekruter"), 
                        "invitation_date" : st.column_config.DateColumn(label="Data zaproszenia", format='YYYY-MM-DD'), 
                        "future_invitation_date" : st.column_config.DateColumn(label="Data ponowniej komunikacji", format='YYYY-MM-DD'), 
                        "last_change_date" : st.column_config.DatetimeColumn(label="Data ostatniej zmiany", format='YYYY-MM-DD HH:mm:ss'), 
                        "notes": st.column_config.TextColumn(label="Notatki"), 
                        "world": None, 
                        "status_id" : None,
                        "recriterid" : None
                        },
                    use_container_width=True, hide_index= True)

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
    
    def inc_players(df_player_guild_history) -> list:
            modification_container = st.container()
            with modification_container:
                filters = []
                to_filter_columns = st.multiselect("Wybierz gildie", df_player_guild_history.Gracz.sort_values().unique(), max_selections =4, placeholder="Rozwiń lub zacznij wpisywać")
                for row in to_filter_columns:
                    df2=df_player_guild_history.loc[df_player_guild_history['Gracz'] == row, 'playerId'].iloc[0]
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
        coll1, coll2 = st.columns([5, 50])
        
        df_selected_player_activity = df_tabs_player_activity[df_tabs_player_activity['playerId'] == Player_id]
        pl_name = df_selected_player_activity["name"].iloc[0]
        with coll1:
            st.markdown("**Wybierz Świat:**")
            Worlds = df_selected_player_activity.world.sort_values().unique().tolist()
            selected_worlds = []
            for index, i in enumerate(Worlds):
                if st.checkbox(label=i, value=True, key=f"Checkbx{index}"):
                        selected_worlds.append(i)
        with coll2:
            c= alt.Chart(df_selected_player_activity[df_selected_player_activity['world'].isin(selected_worlds)]).mark_line(
                                    point=alt.OverlayMarkDef(filled=False, fill="white", size=50)
                                            ).encode(
                                                x=alt.X("Data_danych", title='Data danych'),
                                                y=alt.Y(ops, title=ops)
                                                # , xOffset="World:N"
                                                , color='world:N'
                                                , tooltip=ops
                                            ).properties(
                                                        title=f"Historia gry {pl_name} z ostatnich 30 dni"
                                                        # width=alt.Step(400)  # controls width of bar.
                                                    )

            tick1 = alt.Chart(df_selected_player_activity[df_selected_player_activity['world'].isin(selected_worlds)]).mark_tick(
                color='purple',
                thickness=2,
                size=40 * 0.45,  # controls width of tick.
            ).encode(
                x="Data_danych",
                y="GPCh"
            ).properties(title="dzień GPCh")
                                            
            text = c.mark_text(
                align='center'
                , baseline='top'
                , color="black"
                , fontSize = 13
                , dy=-30  # Nudges text to right so it doesn't appear on top of the bar
                ).encode(
                    text=f"{ops}:Q",
                    )
            st.altair_chart(c.interactive() + tick1 + text, use_container_width=True)    
        
    def tabs_player_other_worlds(df_tabs_player_other_worlds, Player_id):
        st.dataframe(df_tabs_player_other_worlds[df_tabs_player_other_worlds['playerId'] == Player_id],  column_config={
                            "world_name": st.column_config.TextColumn(label="Świat"), 
                            "playerId": st.column_config.TextColumn(label="playerId"), 
                            "Gracz": st.column_config.TextColumn(label="Gracz"), 
                            "Epoka" : st.column_config.TextColumn(label="Epoka"), 
                            "Gildia" : st.column_config.TextColumn(label="Gildia"), 
                            "Punty rankingowe": st.column_config.TextColumn(label="Punty rankingowe"), 
                            "Wygrane Bitwy": st.column_config.TextColumn(label="Wygrane Bitwy"), 
                            "Zdobyte punkty (wczoraj)": st.column_config.TextColumn(label="Zdobyte punkty (wczoraj)"), 
                            "Walki (wczoraj)": st.column_config.TextColumn(label="Walki (wczoraj)"), 
                            "world" : None,
                            "Ranking" : None, 
                            "Player_link" : None, 
                            "ClanId" : None,
                            "notes": None, 
                            "avg_last_battles": None, 
                            "avg_last_points": None, 
                            "Prospect" : None, 
                            "Status": None,
                            "valid_to": None
                        }
                     , use_container_width=True, hide_index= True)
        
    def guild_history(df_player_guild_history, Player_id):
        st.info("Dane dostępne od 2024-02-01 ")
        st.dataframe(
                df_player_guild_history[df_player_guild_history['playerId'] == Player_id].sort_values(by=["Data dołączenia"], ascending=True)
                , use_container_width=True
                , hide_index= True
                , column_config={"playerId" : None}
                )

    @st.cache_data(ttl=0, experimental_allow_widgets=True)
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
                            "avg_last_battles": st.column_config.NumberColumn(label="Średnia ilość walk (30 dni)"), 
                            "Prospect": st.column_config.CheckboxColumn(default=False, disabled=True), 
                            "world" : None,
                            "battlesDif": None, 
                            "pointsDif": None, 
                            "avg_last_points": None, 
                            "playerId" : None,
                            "ClanId" : None, 
                            "_merge": None,
                            "valid_to": None, 
                            "world_name" : None
                        },
            disabled=( "Ranking", "Gracz", "Player_link", "Gildia", "Punty Rankingowe", "Wygrane Bitwy", "Epoka")
        )
        selected_player= ""
        # Filter the dataframe using the temporary column, then drop the column
        selected_rows = edited_df[edited_df.Select]
        if len(selected_rows)>1:
            st.error("Zanzacz tylko jeden rekord")
            return pd.DataFrame()
        if not selected_rows.empty:
            selected_player =selected_rows["playerId"].iloc[0]
            return selected_rows[selected_rows['playerId'] == selected_player]
    
    

    with st.expander(label="Filtuj ...", expanded=True):
        col1, col2, col3, col4, col5 = st.columns([15,5,8,8, 10])
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
                    
            f_players = st.checkbox(label="Wybrany Gracz", value=False)
            if f_players:
                f_inc_players  = inc_players(all_players)
                all_players = all_players[all_players['playerId'].isin(f_inc_players)]  
            
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
        with col5.container():
            filter_by_prospect = st.checkbox(label="Rekrutacja", value=True)
            if filter_by_prospect:
                filter_by_prospect = st.radio(label="Status", options=df_statuses.status_Name.sort_index().unique(), index=0, horizontal=True, label_visibility="hidden")
                all_players = all_players[all_players['Status'] == (filter_by_prospect)]          


    df_selected_player = dataframe_with_selections(all_players)
    if df_selected_player is not None: 
        if len(df_selected_player)==1:
            selected_player =df_selected_player["playerId"].iloc[0]

            if  selected_player is not None:
                st.divider()
                if 'number' not in locals():
                    number = 0
                tabs_player_prospect(get_prospect_history(), selected_player, df_selected_player, df_recruters, number )
                # st.divider()
                tab1, tab2, tab3, tab4 = st.tabs(["Historia komunikacji z Graczem", "Historia Aktywności Gracza", "Historia Gildii", "Inne Światy"])
                with tab1:
                    prospect_history(selected_player)
                with tab2:
                    tabs_player_activity(get_player_activity(selected_player), selected_player)
                with tab3:
                    guild_history(get_player_guild_history(selected_player), selected_player)
                with tab4:
                    tabs_player_other_worlds(get_player_other_worlds(selected_player), selected_player)


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

    authenticator, users, username  = login()
    if username:
        # st.write(st.session_state['authenticator_status'])
        if st.session_state['authenticator_status']:
            if check_user_role_permissions(username, 'RECRUIT') == True:
                run_reports()   
            else:
                st.warning("Nie masz dostępu do tej zawartości.")  
