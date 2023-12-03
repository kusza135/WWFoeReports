import streamlit as st
from PIL import Image
from tools.streamlit_tools import execute_query
# import pandas as pd
import  altair as alt
from tools.login import login
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
                , "forecast"
            from V_WG
            WHERE wg_date_of_day = 0
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
                , "forecast"
            from V_WG a
            INNER JOIN 
            	(SELECT MIN(report_date) as report_date FROM V_WG) c
            	ON a.report_date = c.report_date
            ''',
                    return_type="df",
                )
        wg_result_all = wg_result_all[wg_result_all['player_id'].isin(filters)]
        
        
        base=alt.Chart(wg_result_all).mark_bar(strokeWidth=1).encode(
            x=alt.X('Report_date:N', axis = alt.Axis(title = 'Data zakończenia WG', labelAngle=5)),
            y='Wygrane_bitwy:Q',
            xOffset="Player_name:N",
            tooltip=["Player_name:N", "Report_date", "Epoka", "WG_LEVEL", "Wygrane_bitwy"]
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
        f'''select 
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
            	(SELECT MIN(report_date) AS report_date FROM V_GPCH) c
            ON a.report_date = c.report_date
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
        
def guild_player_stats(filters):
        guild_stats_sql = execute_query(
        f'''select 
                a.player_id
                , Report_date
                , a.`rank`
                , a.name as "Player_name"
                , a.score
                , a.won_battles
                , a.Age_PL as "Epoka"
                , title
                , Join_date
                , leave_date
from V_GUILD_PLAYERS a
inner join V_WG b on a.player_id   = b.player_id 
where wg_date_of_day = 0
AND report_date between valid_from and valid_to
            ''',
                    return_type="df",
                )
        st.table(guild_stats_sql[guild_stats_sql['player_id'].isin(filters)])
        
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
            from V_GUILD_PLAYERS a
            ORDER BY
                Join_date
            '''
        guild_hist_sql = execute_query(query, return_type="df")
 
        with st.expander("Dodaj notatkę graczowi", expanded=True):
            def add_note(player_id, note):
                st.markdown(f"call p_notes({player_id},'{note}')")
                execute_query(f"call p_notes({player_id},'{note}')", return_type="df")
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
        query = f'''select 
                MAX(a.player_id) as player_id
                , a.name as "Player_name"
                , notka
            from V_GUILD_PLAYERS a
            WHERE 
                notka is not null
            GROUP BY a.name, notka
            '''
        guild_hist_sql_tmp = execute_query(query, return_type="df")
        guild_hist_sql = guild_hist_sql_tmp[guild_hist_sql_tmp['player_id'].isin(filters)]
        for names in range(len(guild_hist_sql)):
            player_name = guild_hist_sql['Player_name'][names]
            notka = guild_hist_sql['notka'][names]
            
            st.warning(f'Gracz **{player_name}** ma zapisaną notatkę: {notka}', icon='⚠️')
         

   
def run_reports():
    # st.empty
    colx, coly = st.columns([5, 10])
    image = Image.open(path + '/../.streamlit/Logo.png')
    colx.image(image, width=150)
    coly.title('Wzgórze Wisielców  \n\n', anchor='main')
    
    st.subheader(" ##  Postępy Graczy  ## ", anchor='PostępyGraczy')
    
    filters = filter_Setup()
    
    list_notes_for_users(filters)
    
    st.subheader('Wyprawy Gildyjne  \n  \n',anchor='wg',  divider='rainbow')
    st.text("\n\n\n")
    wg_player_stats(filters)
    st.subheader('Gildyjne Pola Chwały  \n  \n',anchor='gpch',  divider='rainbow')
    st.text("\n\n\n")
    gpch_player_stats(filters)
    st.subheader('Statystyki w Gildii  \n  \n',anchor='stats',  divider='rainbow')
    st.text("\n\n\n")
    guild_player_stats(filters)
    st.subheader('Historia zmian w Gildii  \n  \n',anchor='history',  divider='rainbow')
    st.text("\n\n\n")
    guild_player_history(filters)
    # wg_player_stats()
    
    
     
if __name__ == '__main__':    
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    login()
    if st.session_state['authenticator_status']:
        run_reports()
 