import streamlit as st
import altair as alt
# from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id, get_guild_name
from tools.login import login, check_user_role_permissions
import os


path = os.path.dirname(__file__)

 
def get_text(type):
    res = execute_query(f"SELECT msg_text FROM t_tips WHERE msg_type = '{type}' AND valid_to ='3000-12-31'", return_type="df")
    return res.iloc[0]['msg_text']
    
def change_text(type, msg):
    execute_query(f"call p_change_tips('{type}','{msg}')", return_type="df")

@st.cache_data(ttl=0, experimental_allow_widgets=True)
def list_dates():
    return execute_query(
            f'''select distinct 
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
order by 1''', return_type="list"
        )

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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

@st.cache_data(ttl=0, experimental_allow_widgets=True)
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



def run_reports():
    check_nick_name_change()
    
    st.subheader("  ##  Filtr (suwak) po dacie  ## ")
    Report_Date_list = [ 
         row[0]
        for row in list_dates()
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


def check_nick_name_change():
    qry = list_change_nick_name()
    if not qry.empty:
        st.warning('Poniżej gracze którzy zmienili nick', icon="⚠️")
        st.dataframe(qry, hide_index=True, use_container_width=True)




@st.cache_data(ttl=0, experimental_allow_widgets=True)
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
            if check_user_role_permissions(username, 'GPC_STATS') == True:
                run_reports()   
            else:
                st.warning("Nie masz dostępu do tej zawartości.")  



    
    
    