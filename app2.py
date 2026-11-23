"""附近揪團｜第一階段完整程式：GAS + 試算表，不含地圖/定位。"""
from datetime import date, time
import os
import requests
import streamlit as st

st.set_page_config(page_title="附近揪團", page_icon="🍲", layout="wide")
DEMO = [{"id": "D001", "title": "下課一起吃飯", "category": "美食", "date": "2099-12-20", "time": "18:30", "place": "台中車站", "address": "台中市示範地址", "capacity": 5, "joined": 1, "host": "小安"}]


def secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return os.getenv(name, "").strip()


URL, TOKEN = secret("GAS_WEB_APP_URL"), secret("GAS_API_TOKEN")
if "demo_events" not in st.session_state:
    st.session_state.demo_events = [dict(item) for item in DEMO]
if "demo_joins" not in st.session_state:
    st.session_state.demo_joins = [{"eventId": item["id"], "name": item["host"]} for item in DEMO]


def request_api(endpoint, token, payload):
    response = requests.post(endpoint, json={**payload, "token": token}, timeout=20)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("GAS 回傳的不是 JSON，請檢查部署存取權與 /exec 網址") from exc
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "GAS 回傳錯誤"))
    return data


def gas_post(payload):
    return request_api(URL, TOKEN, payload)


@st.cache_data(ttl=20)
def fetch_events(endpoint, token):
    return request_api(endpoint, token, {"action": "listEvents"}).get("events", [])


def get_events():
    if URL:
        if not TOKEN:
            raise RuntimeError("已填 GAS 網址，還要設定 GAS_API_TOKEN")
        return fetch_events(URL, TOKEN)
    return st.session_state.demo_events


def show_flash_message():
    message = st.session_state.pop("success_message", None)
    if message:
        st.success(message)


def display_event(item):
    st.subheader(item.get("title", "未命名活動"))
    st.write(f"{item.get('category', '其他')}｜{item.get('date', '')} {item.get('time', '')}")
    st.write(f"📍 {item.get('place', '')}｜{item.get('address', '')}")
    st.write(f"主揪：{item.get('host', '')}　名額：{item.get('joined', 0)} / {item.get('capacity', 0)}")


st.title("🍲 附近揪團")
st.caption("第一階段：活動、報名與雲端資料同步；地圖和定位留到第二階段。")
st.info("目前使用 GAS 雲端資料" if URL else "目前使用示範資料；本機記憶體資料不會跨裝置同步")
show_flash_message()
left, right = st.columns([1.4, 1])
with left:
    st.header("活動清單")
    try:
        events = get_events()
    except Exception as exc:
        st.error(f"讀取失敗：{exc}")
        events = []
    if not events:
        st.info("目前沒有活動，請建立一團。")
    for item in events:
        with st.container(border=True):
            display_event(item)
            with st.form(f"join_{item.get('id')}"):
                who = st.text_input("報名暱稱", key=f"who_{item.get('id')}")
                join = st.form_submit_button("報名")
            if join:
                try:
                    if URL:
                        gas_post({"action": "joinEvent", "eventId": item["id"], "name": who})
                        fetch_events.clear()
                    else:
                        target = next(x for x in st.session_state.demo_events if x["id"] == item["id"])
                        if not who.strip():
                            raise ValueError("請填暱稱")
                        already_joined = any(
                            row["eventId"] == item["id"] and row["name"].casefold() == who.strip().casefold()
                            for row in st.session_state.demo_joins
                        )
                        if already_joined:
                            raise ValueError("這個暱稱已報名（主揪也已占用一個名額）")
                        if target["joined"] >= target["capacity"]:
                            raise ValueError("活動已額滿")
                        target["joined"] += 1
                        st.session_state.demo_joins.append({"eventId": item["id"], "name": who.strip()})
                    st.session_state.success_message = "報名完成"
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
with right:
    st.header("建立活動")
    with st.form("create"):
        title = st.text_input("活動名稱")
        category = st.selectbox("類別", ["美食", "桌遊", "運動", "其他"])
        event_date = st.date_input("日期", value=date.today())
        event_time = st.time_input("時間", value=time(18, 0))
        place = st.text_input("地標名稱")
        address = st.text_input("地址")
        capacity = st.number_input("名額（含主揪）", min_value=2, max_value=30, value=5)
        host = st.text_input("主揪暱稱")
        submit = st.form_submit_button("建立活動", type="primary")
    if submit:
        if not all([title.strip(), place.strip(), address.strip(), host.strip()]):
            st.warning("請填活動名稱、地標、地址與主揪暱稱")
        else:
            payload = {"action": "createEvent", "title": title.strip(), "category": category, "date": event_date.isoformat(), "time": event_time.strftime("%H:%M"), "place": place.strip(), "address": address.strip(), "capacity": int(capacity), "host": host.strip()}
            try:
                if URL:
                    gas_post(payload)
                    fetch_events.clear()
                else:
                    new_id = f"D{len(st.session_state.demo_events) + 1:03}"
                    st.session_state.demo_events.append({**payload, "id": new_id, "joined": 1})
                    st.session_state.demo_joins.append({"eventId": new_id, "name": host.strip()})
                st.session_state.success_message = "活動已建立"
                st.rerun()
            except Exception as exc:
                st.error(f"建立失敗：{exc}")
st.divider()
st.caption("請用虛構暱稱和活動資料練習。第一階段不需要 Google Maps 金鑰。")
