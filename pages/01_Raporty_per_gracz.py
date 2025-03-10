import streamlit as st
from PIL import Image
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id
# import pandas as pd
import  altair as alt
from tools.login import login, check_user_role_permissions
import os


path = os.path.dirname(__file__)

def filter_Setup() -> list:

    modification_container = st.container()

    with modification_container:
        filters = []
        df= execute_query(f'''
                          SELECT 
                            DISTINCT 
                                player_id,
                                name as "Player_name"
                            FROM
                                V_GUILD_PLAYERS
                          ''',
                    return_type="df",
                )
        to_filter_columns = st.multiselect("Wybierz nick gracza", df.Player_name.sort_values().unique(), max_selections =4, placeholder="Rozwiń lub zacznij wpisywać")
        for row in to_filter_columns:
            df2=df.loc[df['Player_name'] == row, 'player_id'].iloc[0]
            filters.append(df2)

        # df = df[df['player_id'].isin(filters)]

    return filters

# @st.cache_resource(ttl=14400, experimental_allow_widgets=True, show_spinner="Pobieranie danych ...")
@st.fragment()
def _df_player_activity():
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
                , case when f_gpch_day(DATE_ADD(valid_from, INTERVAL -1 DAY)) > 0 then 500 else 0 END GPCh
            FROM V_all_players
            WHERE 
                world = '{get_world_id()}'  
                AND valid_from > DATE_ADD(CURRENT_DATE(), INTERVAL -30 DAY)
                AND ClanId = '{get_guild_id()}'
            ''',
                    return_type="df",
                )
    return df_tabs_player_activity

def tabs_player_activity(Player_id):
    df_tabs_player_activity = _df_player_activity()
    
    ops = st.radio(label="Wybierz metryki:", options=['Punty rankingowe', 'Liczba bitew', 'Różnica punktów rankingowych', 'Różnica bitew'], horizontal=True, index=3)
    # st.dataframe(tabs_player_activity)
    # pl_name = df_tabs_player_activity[df_tabs_player_activity['playerId'] == Player_id]["name"].iloc[0]
    c= alt.Chart(df_tabs_player_activity[df_tabs_player_activity['playerId'].isin(Player_id)]).mark_line(
                            point=alt.OverlayMarkDef(filled=True, size=25)
                                    ).encode(
                                        x=alt.X("Data_danych", title='Data danych'),
                                        y=alt.Y(ops, title=ops),
                                        # color='name:N', 
                                        color=alt.Color('name:N', legend=alt.Legend(
                                                                        orient='none',
                                                                        legendX=450, legendY=-47,
                                                                        direction='horizontal',
                                                                        titleAnchor='middle')), 
                                        # xOffset="name:N",
                                        tooltip=ops
                                    ).properties(
                                                title=f"Historia gry z ostatnich 30 dni"
                                                , height=450
                                                # , width='container'  # controls width of bar.
                                            )
    # bars = c.mark_line().encode(
    #        ,
    #     )
    tick1 = alt.Chart(df_tabs_player_activity[df_tabs_player_activity['playerId'].isin(Player_id)]).mark_tick(
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
    
    
def wg_player_stats(filters):
        wg_result_all = execute_query(
        f'''select 
                Player_id
                , CAST(report_date AS CHAR) AS Report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  "WG_LEVEL"
                , currentTrial AS "Próba"
                , "forecast"
            from V_WG
            WHERE wg_date_of_day = 0
            AND world = '{get_world_id()}'
            AND guild_id = {get_guild_id()}
            UNION ALL
            select 
                Player_id
                , CAST(a.report_date AS CHAR) AS Report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  "WG_LEVEL"
                , currentTrial AS "Próba"
                , "forecast"
            from V_WG a
            INNER JOIN 
            	(SELECT MIN(report_date) as report_date FROM V_WG WHERE world = '{get_world_id()}' AND guild_id = {get_guild_id()}) c
            	ON a.report_date = c.report_date
            WHERE 
                a.world = '{get_world_id()}'
            AND a.guild_id = {get_guild_id()}
            ''',
                    return_type="df",
                )
        wg_result_all = wg_result_all[wg_result_all['player_id'].isin(filters)]
        
        
        base=alt.Chart(wg_result_all).mark_bar(strokeWidth=1).encode(
            x=alt.X('Report_date:N', axis = alt.Axis(title = 'Data zakończenia WG', labelAngle=5)),
            y='Wygrane_bitwy:Q',
            xOffset="Player_name:N",
            tooltip=["Player_name:N", "Report_date", "Epoka", "WG_LEVEL", "Wygrane_bitwy", "Próba"]
            # column=alt.Column('report_date:T', title="", spacing =1), #spacing =0 removes space between columns, column for can and st 
        ).properties( title='Statystyka wszystkich edycji WG gracza/y'
            , width=alt.Step(10)).interactive()
        # .configure_header(labelOrient='bottom').configure_view(
        #     strokeOpacity=1)
        
        bars = base.mark_bar().encode(
            color='Player_name:N',
        )
        text = base.mark_text(
            align='center',
            baseline='top'
            , color="black"
            , dy=-30  # Nudges text to right so it doesn't appear on top of the bar
        ).encode(
            text='Player_name:N'
        )
        st.altair_chart(bars + text, theme=None, use_container_width=True)
        
def gpch_player_stats(filters):
        gpch_result_all = execute_query(
        f'''
               select 
                    player_id
                    , CAST(report_date AS CHAR) AS Report_date
                    , name as "Player_name"
                    , Age_PL as "Epoka"
                    , GPCH_DATE_OF_DAY as "GPCH_day"
                    , "RANK"
                    , battlesWon "Wygrane_bitwy"
                    , negotiationsWon  "Wygrane_negocjacje"
                    , score 
                    , "Forecast"
                from V_GPCH where GPCH_DATE_OF_DAY = 0
                AND world = '{get_world_id()}'
                AND guild_id = {get_guild_id()}
                UNION ALL
                select 
                    player_id
                    , CAST(a.report_date AS CHAR) AS Report_date
                    , name as "Player_name"
                    , Age_PL as "Epoka"
                    , GPCH_DATE_OF_DAY as "GPCH_day"
                    , "RANK"
                    , battlesWon "Wygrane_bitwy"
                    , negotiationsWon  "Wygrane_negocjacje"
                    , score 
                    , "Forecast"
                from V_GPCH a
                INNER JOIN 
                    (SELECT MIN(report_date) AS report_date FROM V_GPCH WHERE world = '{get_world_id()}' AND guild_id = {get_guild_id()}) c
                ON a.report_date = c.report_date
                WHERE 
                a.world = '{get_world_id()}'
                AND a.guild_id = {get_guild_id()}
            ''',
                    return_type="df",
                )
        gpch_result_all = gpch_result_all[gpch_result_all['player_id'].isin(filters)]
        
        base=alt.Chart(gpch_result_all).mark_bar(strokeWidth=1).encode(
            x=alt.X('Report_date:N', axis = alt.Axis(title = 'Data zakończenia GPCh', labelAngle=5)),
            y=alt.Y('score:Q', axis = alt.Axis(title = 'Wynik walk i nego', labelAngle=5)),
            xOffset="Player_name:N",
            tooltip=["Player_name:N", "Report_date", "Epoka", "Wygrane_bitwy:Q", "Wygrane_negocjacje:Q"]
            # column=alt.Column('report_date:T', title="", spacing =1), #spacing =0 removes space between columns, column for can and st 
        ).properties( height = 300, title='Statystyka wszystkich edycji GPCh gracza/y'
            , width=alt.Step(3)).interactive()
        
        bars = base.mark_bar().encode(
            color='Player_name:N',
        )
        text = base.mark_text(
            align='center',
            baseline='top'
            , color="black"
            , dy=-30  # Nudges text to right so it doesn't appear on top of the bar
        ).encode(
            text='Player_name:N'
        )
        st.altair_chart(bars + text, theme=None, use_container_width=True)
        
def nk_player_stats(filters):
        nk_result_all = execute_query(
        f'''SELECT 
                DISTINCT *
            FROM 
            (
                select 
                    player_id
                    , CAST(report_date AS CHAR) AS Report_date
                    , name as "Player_name"
                    , Age_PL as "Epoka"
                    , NK_DATE_OF_DAY as "NK_day"
                    , progressContribution AS "Postep"
                    , actionPoints AS "Działania"
                from V_NK where NK_DATE_OF_DAY = 0
                AND world = '{get_world_id()}'
                AND guild_id = {get_guild_id()}
                UNION ALL
                select 
                    player_id
                    , CAST(a.report_date AS CHAR) AS Report_date
                    , name as "Player_name"
                    , Age_PL as "Epoka"
                    , NK_DATE_OF_DAY as "NK_day"
                    , progressContribution AS "Postep"
                    , actionPoints AS "Działania"
                from V_NK a
                INNER JOIN 
                    (SELECT MIN(report_date) AS report_date FROM V_NK WHERE world = '{get_world_id()}' AND guild_id = {get_guild_id()}) c
                ON a.report_date = c.report_date
                WHERE 
                a.world = '{get_world_id()}'
                AND a.guild_id = {get_guild_id()}
            ) as x
            ''',
                    return_type="df",
                )
        nk_result_all = nk_result_all[nk_result_all['player_id'].isin(filters)]

        
        base=alt.Chart(nk_result_all).mark_bar(strokeWidth=1).encode(
            x=alt.X('Report_date:N', axis = alt.Axis(title = 'Data zakończenia Najazdów Kwantowych', labelAngle=5)),
            y=alt.Y('Postep:Q', axis = alt.Axis(title = 'Postęp', labelAngle=5)),
            xOffset="Player_name:N",
            tooltip=["Player_name:N", "Report_date", "Epoka", "Postep:Q", "Działania:Q"]
            # column=alt.Column('report_date:T', title="", spacing =1), #spacing =0 removes space between columns, column for can and st 
        ).properties( height = 300, title='Statystyka wszystkich edycji Najazdów Kwantowych gracza/y'
            , width=alt.Step(3)).interactive()
        
        bars = base.mark_bar().encode(
            color='Player_name:N',
        )
        text = base.mark_text(
            align='center',
            baseline='top'
            , color="black"
            , dy=-30  # Nudges text to right so it doesn't appear on top of the bar
        ).encode(
            text='Player_name:N'
        )
        st.altair_chart(bars + text, theme=None, use_container_width=True)
   

        
def guild_player_history(filters):
        query = f'''select 
                a.player_id
                , a.`rank`
                , a.name as "Player_name"
                , a.score
                , a.won_battles
                , a.Age_PL as "Epoka"
                , title
                , case 
                    permissions
                    when  126 then 'Zarządzanie GPCh'
                    when 127 then 'Zarządzanie Gildią'
                    end "Uprawnienia"
                , Join_date
                , leave_date
                , valid_from
                , valid_to
            from V_GUILD_PLAYERS a
            # WHERE 
            #     a.world = '{get_world_id()}'
            #     AND a.guild_id = {get_guild_id()}
            ORDER BY
                Valid_from
            '''
        guild_hist_sql = execute_query(query, return_type="df")
 
        with st.expander("Dodaj notatkę graczowi", expanded=True):
            def add_note(player_id, note):
                st.markdown(f"call p_notes({player_id},'{note}')")
                execute_query(f"call p_notes({player_id},'{note}')", return_type="df")
                st.toast("Dane zapisane", icon="✅")
            # st.markdown(
            #     """
            # <style>
            # button {
            #     height: 50px;
            #     padding-top: 16px !important;
            #     padding-bottom: 16px !important;
            # }
            # </style>
            # """,
            #     unsafe_allow_html=True,
            # )                
            col1, col2, col3 = st.columns([5, 10, 5])
            nickname = col1.selectbox( label= "Wyznacz gracza", index=None,  options=guild_hist_sql['Player_name'].sort_values().unique(), label_visibility='hidden')
            if nickname != None:
                pid = guild_hist_sql.loc[guild_hist_sql['Player_name'] == nickname, 'player_id'].values[0]
                notka = col2.text_input(label="Wpisz któtką notkę", placeholder="Wpisz któtką notkę",label_visibility='hidden')
                if (notka == None or notka == ""):
                    przycisk = st.button(label="Zapisz", on_click=add_note, args=(pid, notka), disabled=True)
                else:
                    przycisk = st.button(label="Zapisz", on_click=add_note, args=(pid, notka), disabled=False)
                    guild_hist_sql = None
                    st.cache_data.clear()
                    guild_hist_sql = execute_query(query, return_type="df")

           
        st.dataframe(guild_hist_sql[guild_hist_sql['player_id'].isin(filters)], use_container_width=True, hide_index=True)
     
def list_notes_for_users(filters):
        query = f'''
            SELECT 
                * 
            FROM
            ( 
                SELECT 
                    a.player_id
                    , a.name as "Player_name"
                    , notka
                    , ROW_NUMBER() OVER (PARTITION BY a.player_id ORDER BY VALID_TO DESC ) RN
                FROM V_GUILD_PLAYERS a
                WHERE 
                    notka is not null
                    # AND a.world = '{get_world_id()}'
                    # AND a.guild_id = {get_guild_id()}
            ) x
            WHERE RN = 1
            '''
        guild_hist_sql_tmp = execute_query(query, return_type="df")
        guild_hist_sql = guild_hist_sql_tmp[guild_hist_sql_tmp['player_id'].isin(filters)]
        
        for names in range(len(guild_hist_sql)):
            player_name = guild_hist_sql['Player_name'].iloc[names]
            notka = guild_hist_sql['notka'].iloc[names]
            
            st.warning(f'Gracz **{player_name}** ma zapisaną notatkę: \n\n{notka}\n', icon='⚠️')
         
def player_nick_changes(filters):
        changed_nick_sql = execute_query( f'''
                        SELECT 
                          GP.player_id              
                          , GP.name "OLD_NAME" 
                          , VAP.name "CURRENT_NAME"
                        FROM 
                          (SELECT player_id, name, ROW_NUMBER() over (partition by player_id order by valid_to desc) rn FROM V_GUILD_PLAYERS) GP
                        Inner JOIN
                          V_all_players VAP
                          ON GP.player_id =  VAP.PLAYERID 
                          and rn = 1
                        WHERE 
                            VAP.VALID_TO  = '3000-12-31'
                            AND VAP.WORLD = '{get_world_id()}' 
                            and GP.name <> VAP.name
            ''', return_type="df")
        changed_nick = changed_nick_sql[changed_nick_sql['player_id'].isin(filters)]

        
        for names in range(len(changed_nick)):
            old_name = changed_nick['OLD_NAME'].iloc[names]
            current_name = changed_nick['CURRENT_NAME'].iloc[names]
            
            st.info(f'Gracz **{old_name}** zmienił nick na **{current_name}**', icon="ℹ️")
   
def run_reports():
    st.subheader(" ##  Postępy Graczy  ## ", anchor='PostępyGraczy')
    
    filters = filter_Setup()

    player_nick_changes(filters)

    list_notes_for_users(filters)
    
    st.subheader('Historia aktywności z ostatnich 30 dni  \n  \n',anchor='activity',  divider='rainbow')
    st.text("\n\n\n")
    tabs_player_activity(filters)
    
    st.subheader('Wyprawy Gildyjne  \n  \n',anchor='wg',  divider='rainbow')
    st.text("\n\n\n")
    wg_player_stats(filters)
    st.subheader('Gildyjne Pola Chwały  \n  \n',anchor='gpch',  divider='rainbow')
    st.text("\n\n\n")
    gpch_player_stats(filters)
    st.subheader('Najazdy Kwantowe  \n  \n',anchor='nk',  divider='rainbow')
    st.text("\n\n\n")
    nk_player_stats(filters)
    # st.subheader('Statystyki w Gildii  \n  \n',anchor='stats',  divider='rainbow')
    # st.text("\n\n\n")
    # guild_player_stats(filters)
    st.subheader('Historia zmian w Gildii  \n  \n',anchor='history',  divider='rainbow')
    st.text("\n\n\n")
    guild_player_history(filters)
    # wg_player_stats()
    
    
     
if __name__ == '__main__': 

    page_header()
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    authenticator, users, username  = login()
    if username:
        if st.session_state['authenticator_status']:
            if check_user_role_permissions(username, 'GUILD_PLAYER_STATS') == True:
                run_reports()   
            else:
                st.warning("Nie masz dostępu do tej zawartości.")    
 