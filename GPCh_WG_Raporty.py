import streamlit as st
import altair as alt
# from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id, get_guild_name
from tools.login import login, check_user_role_permissions
import os
import numpy as np


path = os.path.dirname(__file__)

 
def get_text(type):
    res = execute_query(f"SELECT msg_text FROM t_tips WHERE msg_type = '{type}' AND valid_to ='3000-12-31'", return_type="df")
    return res.iloc[0]['msg_text']
    
def change_text(type, msg):
    execute_query(f"call p_change_tips('{type}','{msg}')", return_type="df")

@st.fragment
def list_dates_wg(wg_cond):
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
from V_WG 
WHERE 
    1=1
    {wg_cond} '''

@st.fragment
def list_dates_gpc(gpc_cond):
    return  f'''select distinct 
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
from V_GPCH
WHERE 
    1=1
    {gpc_cond} '''

@st.fragment
def list_dates(wg_checkbox, gpc_checkbox):
    wg_cond = ''
    gpc_cond = ''
    if wg_checkbox == True:
        wg_cond = 'AND wg_date_of_day=0'
        qry = list_dates_wg(wg_cond)
    elif gpc_checkbox == True:
        gpc_cond = 'AND GPCH_DATE_OF_DAY=0'
        qry = list_dates_gpc(gpc_cond)
    else:
        qry = f'{list_dates_wg(wg_cond)} \n UNION \n {list_dates_gpc(gpc_cond)}\n order by 1'
    return execute_query(qry, return_type="list")

@st.fragment
def list_wg_result_all(date_filter):
    wg_result_all = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  "WG_LEVEL"
                , "forecast"
from V_WG where report_date = '{date_filter}' 
''',
        return_type="df",
    )
    return wg_result_all

@st.fragment
def list_wg_result_catch(date_filter):
    wg_result_catch = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  WG_LEVEL
                , "forecast"
from V_WG where report_date = '{date_filter}' 
AND solvedEncounters < "forecast" 
''',
        return_type="df",
    )
    return wg_result_catch

@st.fragment
def list_gpch_result_all(date_filter):
    gpch_result_all = execute_query(
        f'''select 
                report_date
                , player_id
                , name as "Player_name"
                , Age_PL as "Epoka"
                , GPCH_DATE_OF_DAY as "GPCH_day"
                , "RANK"
                , battlesWon
                , negotiationsWon
                , score AS "Wygrane_bitwy"
                , "Forecast"
from V_GPCH where report_date = '{date_filter}' 
''',
        return_type="df",
    )
    return gpch_result_all

@st.fragment
def list_gpch_result_catch(date_filter):
    gpch_result_catch = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , GPCH_DATE_OF_DAY as "GPCH_day"
                , "RANK"
                , battlesWon
                , negotiationsWon
                , score AS "Wygrane_bitwy"
                , forecast
from V_GPCH 
where 
report_date = '{date_filter}' 
AND score < forecast
''',
        return_type="df",
    )
    return gpch_result_catch

@st.fragment
def list_guild_stats(date_filter):
    guild_stats_sql = execute_query(
        f'''SELECT 
	"RANK" AS "Rank"
	, NAME AS "Nick gracza"
	, Age_PL "Epoka"
	, won_battles "Wygrane bitwy"
	, SCORE "Punkty"
	, TITLE "Tytuł"
	, JOIN_DATE "Data przyłączenia"
	, leave_date AS  "Data opuszczenia"
FROM 
	V_GUILD_PLAYERS
WHERE 
	'{date_filter}'  BETWEEN valid_from  AND valid_to
ORDER BY "RANK"
''',
        return_type="df"
    )
    return guild_stats_sql

@st.fragment
def list_change_nick_name():
    return execute_query(f'''SELECT 
                        old_name AS "Poprzedni nick"
                        , name as "Obecny nick"
                        , valid_to
                        FROM 
                        (SELECT 
                            name  
                            , lag(name) OVER (partition by player_id ORDER BY player_id) old_name
                            , valid_to
                            from 
                                V_GUILD_PLAYERS
                            where 
                                player_id in (select player_id FROM V_GUILD_PLAYERS WHERE valid_to = '3000-12-31')
                        ) x 
                        WHERE name <> old_name and old_name is not null
                        ''', return_type="df")

@st.fragment
def list_winners(date_filter):
    list_winners_sql = execute_query(f'''SELECT  
		world
		, ClanId
		, load_date
		, player_id
        , name
    FROM 
        V_GPC_LOTTERY
    WHERE 
        world = '{get_world_id()}'
        AND ClanId = {get_guild_id()}
        AND load_date = '{date_filter[0:10]}' 
    ''', return_type="df")
    return list_winners_sql


@st.fragment
def get_GPCH_leader(date_filter, rank):
    qry = f'''
SELECT  
	report_date
	, playerId
	, name
	, player_score
	, RN                                  
FROM
    (                                   
        SELECT 
            report_date
            , playerId
            , name
            , player_score
            , ROW_NUMBER() OVER (PARTITION BY report_date ORDER BY player_score DESC) RN
        FROM 
        (
            select 
                report_date
                , playerId
                , Foe_WW.V_GPCH.name name 
                ,  max(score) player_score
        FROM 
            Foe_WW.t_all_players tap
        INNER JOIN 
            Foe_WW.V_GPCH
            on playerId = player_id 
            and tap.world =V_GPCH.world
            and tap.clanId = V_GPCH.guild_id
        WHERE tap.world  = '{get_world_id()}'
        AND report_date  = '{date_filter[0:10]}' 
        and valid_from  between DATE_ADD(report_date ,INTERVAL case when GPCH_DATE_OF_DAY=0 then -11 else -GPCH_DATE_OF_DAY end  DAY) and report_date
        GROUP BY 1, 2, 3
        having count(DISTINCT era)=1
    ) x
) y 
WHERE 
	RN = {rank}
    '''
    gpc_leader_sql = execute_query(qry, return_type="df")
    return gpc_leader_sql


@st.fragment
def players_changed_age(date_filter):
    qry = f'''SELECT 
            report_date
            , playerId
            , name
            , player_score
            , ROW_NUMBER() OVER (PARTITION BY report_date ORDER BY player_score DESC) RN
        FROM 
        (
            select 
                report_date
                , playerId
                , Foe_WW.V_GPCH.name name 
                ,  max(score) player_score
        FROM 
            Foe_WW.t_all_players tap
        INNER JOIN 
            Foe_WW.V_GPCH
            on playerId = player_id 
            and tap.world =V_GPCH.world
            and tap.clanId = V_GPCH.guild_id
        WHERE tap.world  = '{get_world_id()}'
        AND report_date  = '{date_filter[0:10]}' 
        and valid_from  between DATE_ADD(report_date ,INTERVAL case when GPCH_DATE_OF_DAY=0 then -11 else -GPCH_DATE_OF_DAY end  DAY) and report_date
        GROUP BY 1, 2, 3
        having count(DISTINCT era)>1
    ) x'''
    players_changed_age = execute_query(qry, return_type="df")
    return players_changed_age

def list_gpc_lottery_exceptions():
    list_gpc_lottery_exceptions = execute_query(f'''SELECT  
		player_id
    FROM 
        t_gpc_lottery_exceptions
    WHERE 
        world = '{get_world_id()}'
        AND ClanId = {get_guild_id()}
    ''', return_type="df")
    return list_gpc_lottery_exceptions

def run_reports():
    check_nick_name_change()
    
    st.subheader("  ##  Filtr (suwak) po dacie  ## ")
    col1, col2, col3 = st.columns([15, 15, 50])
    wg_checkbox = col1.checkbox(label="Tylko koniec WG", value=False)
    gpc_checkbox = col2.checkbox(label="Tylko koniec GPC",value= False)
    Report_Date_list = [ 
         row[0]
        for row in list_dates(wg_checkbox, gpc_checkbox)
    ]
    while  len(Report_Date_list)<2:
        Report_Date_list.append("_empty")
    date_filter = st.select_slider(label="Select a report date", options=Report_Date_list, value=max(Report_Date_list), label_visibility="hidden")


    if date_filter != "--":
        st.text("\n\n\n")
        wg_reports(date_filter)
        st.text("\n\n\n")
        gpch_reports(date_filter)

        st.text("\n\n\n")
        new_approach(date_filter)
        st.text("\n\n\n")
        lottery_top_gpch_players(date_filter)
        st.text("\n\n\n")
        guild_stats(date_filter)
 
def wg_reports(date_filter):
    st.subheader('Wyprawy Gildyjne  \n  \n',anchor='wg',  divider='rainbow')
    wg_result_all = list_wg_result_all(date_filter)
    wg_result_catch = list_wg_result_catch(date_filter)

    
    if (wg_result_all.iloc[0]['WG_day'] <7 and wg_result_all.iloc[0]['WG_day'] >0): 
        st.markdown(f"*Wyprawy Gildyjne* są :large_green_circle::large_green_circle: :green[w trakcie] :large_green_circle::large_green_circle: day({wg_result_all.iloc[0]['WG_day']}).")
    else:  
        st.markdown("*Wyprawy Gildyjne* są :red_circle: :red[zakończone] :red_circle:.")
        
    col1, col2 = st.columns([1, 1])

    bar1 = alt.Chart(wg_result_all).mark_bar().encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    color="WG_LEVEL",
    tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy"]
    ).properties(
        title='Statystyka edycji WG',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick1 = alt.Chart(wg_result_all).mark_tick(
        color='red',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
 
    ## drugi wykres
    
    bar2 = alt.Chart(wg_result_catch).mark_bar(color='#e8513a').encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy"]
    ).properties(
        title='Warto skontaktować się z',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()

    tick2 = alt.Chart(wg_result_catch).mark_tick(
        color='#47b552',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
    col1.altair_chart(bar1 + tick1, use_container_width=True)
    col2.altair_chart(bar2 + tick2, theme="streamlit", use_container_width=True)
    # col1.bar_chart(wg_result_all, x="Player_name", y= "Wygrane_bitwy" )
    #col2.bar_chart(wg_result_catch, x="Player_name", y= "Wygrane_bitwy", color="#f24951" )

def gpch_reports(date_filter):
    st.subheader('Pola Chwały  \n  \n', anchor='gpch', divider='rainbow')
    gpch_result_all = list_gpch_result_all(date_filter)
    gpch_result_catch = list_gpch_result_catch(date_filter)
    if (gpch_result_all.iloc[0]['GPCH_day'] <12 and gpch_result_all.iloc[0]['GPCH_day']>0): 
        st.markdown(f"*Pola Chwały* są :large_green_circle::large_green_circle: :green[w trakcie] :large_green_circle::large_green_circle: day({gpch_result_all.iloc[0]['GPCH_day']}).")
    else:  
        st.markdown("*Pola Chwały* są :red_circle: :red[zakończone] :red_circle:.")
    col1, col2 = st.columns([1, 1])
    
    bar1 = alt.Chart(gpch_result_all).mark_bar().encode(
    x=alt.X("Player_name:N", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy:Q", title='Wygrane bitwy'),
    tooltip=["Player_name:N", "Epoka:N", "battlesWon:Q", "negotiationsWon:Q"]
    ).properties(
        title='Statystyka edycji GPCh',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick1 = alt.Chart(gpch_result_all).mark_tick(
        color='red',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name:N",
        y="forecast:Q"
    )
    
    bar2 = alt.Chart(gpch_result_catch).mark_bar(color='#e8513a').encode(
    x=alt.X("Player_name:N", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy:Q", title='Wygrane bitwy'),
    tooltip=["Player_name:N", "Epoka:N", "battlesWon:Q", "negotiationsWon:Q"]
    ).properties(
        title='Warto skontaktować się z',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick2 = alt.Chart(gpch_result_catch).mark_tick(
        color='#47b552',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name:N",
        y="forecast:Q"
    )
    
    col1.altair_chart(bar1 + tick1, use_container_width=True)
    col2.altair_chart(bar2 + tick2, theme="streamlit", use_container_width=True)
    # col1.bar_chart(gpch_result_all, x="Player_name", y= "Wygrane_bitwy" )
    # col2.bar_chart(gpch_result_catch, x="Player_name", y= "Wygrane_bitwy" , color="#f24951" )

def guild_stats(date_filter):
    st.subheader('Statystyki Gildii', anchor='guild', divider='rainbow')
    guild_stats_sql = list_guild_stats(date_filter)
    st.dataframe(guild_stats_sql, use_container_width=True, hide_index=True)


def new_approach(date_filter):
    def highlight_survived(s):
        return ['background-color: #ebd8d8']*len(s) if s.score_1 ==False | s.score_2 ==False else ['background-color: #f5faf2']*len(s)

    with st.expander(label="Parametry"):
        col1, col2, col3, col4 = st.columns([15,15,25,50])
        player_pos= (col1.number_input(label="Pozycja w tabeli", value=1, min_value=1, max_value=80)) 
        perc_ind = (col2.number_input(label="Procent od wyniku", value=5, min_value=1, max_value=100))/100
        player_pos2= (col1.number_input(label="Pozycja w tabeli", value=10, min_value=1, max_value=80)) 
        perc_ind2 = (col2.number_input(label="Procent od wyniku", value=10, min_value=1, max_value=100))/100
        player_activity = col3.radio(label="Gracze", options=['Wszyscy', 'Aktywni', 'Nieaktywni'], index=2)


    if not get_GPCH_leader(date_filter, player_pos).empty:
        gpc_leader = get_GPCH_leader(date_filter, player_pos)
        gpc_leader2 = get_GPCH_leader(date_filter, player_pos2)
        cc1, cc2 = st.columns([40,  30])
        cc1.markdown(f"TOP {player_pos} GPCH był **{gpc_leader['name'].iloc[0]}** z wynikiem **{gpc_leader['player_score'].iloc[0]}** walk. Wynik do osiągnięcia wynosi **{int(round(gpc_leader['player_score'].iloc[0]*perc_ind, 0))}**")
        cc1.markdown(f"TOP {player_pos2} GPCH był **{gpc_leader2['name'].iloc[0]}** z wynikiem **{gpc_leader2['player_score'].iloc[0]}** walk. Wynik do osiągnięcia wynosi **{int(round(gpc_leader2['player_score'].iloc[0]*perc_ind2, 0))}**")

        with cc2.expander(label="Gracze, którzy zmienili epokę ..."):
            changed_age_players = players_changed_age(date_filter)
            st.dataframe(changed_age_players, column_config={
                                    "report_date": st.column_config.DateColumn(label="Data końca GPCh"), 
                                    "playerId": None, 
                                    "RN": None, 
                                    "name": st.column_config.TextColumn(label="Gracz"), 
                                    "player_score": st.column_config.NumberColumn(label="Wygrane Bitwy")
                                },
                        hide_index=True
                        , use_container_width=True)

        gpc_results = list_gpch_result_all(date_filter)
        gpc_results['score_1'] = np.where(gpc_results['Wygrane_bitwy']< gpc_leader['player_score'].iloc[0]*perc_ind, False, True)
        gpc_results['score_2'] = np.where(gpc_results['Wygrane_bitwy']< gpc_leader2['player_score'].iloc[0]*perc_ind2, False, True)

        if player_activity == 'Aktywni':
            gpc_results = gpc_results[(gpc_results['score_1']==True) | (gpc_results['score_2']==True)] 
        elif player_activity == 'Nieaktywni':
            gpc_results = gpc_results[(gpc_results['score_1']==False) | (gpc_results['score_2']==False)] 
        elif player_activity == 'Wszyscy':
            None
        

        st.dataframe(gpc_results.style.apply(highlight_survived, axis=1),column_config={
                                "report_date": st.column_config.DateColumn(label="Data końca GPCh"), 
                                "player_id": None, 
                                "rank": st.column_config.NumberColumn(label="Ranking"), 
                                "Player_name": st.column_config.TextColumn(label="Gracz"), 
                                "Epoka" : st.column_config.TextColumn(label="Epoka"), 
                                "GPCH_day" : None, 
                                "battlesWon": None,
                                "negotiationsWon": None,
                                "forecast": None,
                                "Wygrane_bitwy": st.column_config.NumberColumn(label="Wygrane Bitwy"), 
                                "score_1": st.column_config.CheckboxColumn(label=f"Znacznik Aktywności - {gpc_leader['name'].iloc[0]} ({int(round(gpc_leader['player_score'].iloc[0]*perc_ind, 0))})"),
                                "score_2": st.column_config.CheckboxColumn(label=f"Znacznik Aktywności - {gpc_leader2['name'].iloc[0]} ({int(round(gpc_leader2['player_score'].iloc[0]*perc_ind2, 0))})")
                            },
                    hide_index=True
                    , use_container_width=True)



    # st.dataframe(gpc_results[gpc_results['score_boolean']==only_poor_activity].style.applymap(cooling_highlight, subset=['score_1', 'score_2']), hide_index=True)


    # st.dataframe(gpc_results
    #               .style.apply(cooling_highlight, axis=1))



def check_nick_name_change():
    qry = list_change_nick_name()
    if not qry.empty:
        st.warning('Poniżej gracze którzy zmienili nick', icon="⚠️")
        st.dataframe(qry, hide_index=True, use_container_width=True)




@st.fragment
def lottery_top_gpch_players(date_filter):
    gpch_result_all = list_gpch_result_all(date_filter)
    
    check_winners = list_winners(date_filter)
    if not (gpch_result_all.iloc[0]['GPCH_day'] <12 and gpch_result_all.iloc[0]['GPCH_day']>0):
        st.subheader('Losowanie graczy  \n  \n', anchor='gpch', divider='rainbow')
        if check_winners.empty: 
        
            if 'clicked' not in st.session_state:
                st.session_state.clicked = False
            def click_button():
                st.session_state.clicked = True

            st.markdown("""
                <style>
                    .st-dd, .stTextInput > div > div > input, .stButton > button, .stSlider > div {
                        vertical-align: middle !important;
                        font-family: 'Inter';
                        font-size: 40px;
                        font-weight: 500;
                    }
                    .stTextInput > div > div > input {
                        margin-top: 5px !important;
                    }
                </style>
                """, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([40, 40, 20, 40])

            with st.expander(label="Ustawienia losowania"):
                col1, col2, col3, col4 = st.columns([40, 40, 20, 40])
                num_of_lottery_players = col1.number_input(label="Wpisz Top osób biorących udział w losowaniu", step=1, value=30,  min_value=1, max_value=len(gpch_result_all))
                num_of_winners = col2.number_input(label="Wpisz ile osób może wygrać w losowaniu", step=1,  min_value=1, value=5, max_value=num_of_lottery_players)
            gpch_result_selected = gpch_result_all[gpch_result_all["Wygrane_bitwy"].isin( gpch_result_all["Wygrane_bitwy"].nlargest(n=num_of_lottery_players))]
            st.button(label="Wylosuj zwyciężców", type="primary", on_click=click_button())
            if st.session_state.clicked:
                list_gpc_lottery_exc = list_gpc_lottery_exceptions()
                gpch_result_selected = gpch_result_selected[~gpch_result_selected["player_id"].isin(list_gpc_lottery_exc["player_id"])] 
                winners= gpch_result_selected.sample(n=num_of_winners)
                for ind in winners.index:
                    pl_id = winners["player_id"][ind]
                    execute_query(f"call p_gpc_lottery('{get_world_id()}', {get_guild_id()}, '{date_filter[0:10]}', {pl_id})", return_type="df")
                st.cache_data.clear()
        else:
            loterry_msg = '''Gratulujemy poniższym graczom za wspólną zabawę:\n\n'''   
            for ind in check_winners.index:
                    loterry_msg += f'''\t{check_winners["name"][ind]}\n'''

            loterry_msg += f'''\n\nDziękujemy, że jesteście z Nami i wspieracie {get_guild_name()}.'''

            st.code(loterry_msg)


if __name__ == '__main__':    
  
    page_header()
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    authenticator, users, username  = login()
    if username:
        # st.write(st.session_state['authenticator_status'])
        if st.session_state['authenticator_status']:
            if check_user_role_permissions(username, 'GPC_STATS') == True:
                run_reports()   
            else:
                st.warning("Nie masz dostępu do tej zawartości.")  



    
    
    