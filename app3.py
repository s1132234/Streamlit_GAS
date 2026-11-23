"""附近揪團｜第二階段整合程式：目前位置 + OSM 地圖點選 + 直線距離。"""
from datetime import date, time
import math
import os
from urllib.parse import quote_plus

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="附近揪團", page_icon="📍", layout="wide")
DEMO = [
    {"id": "D001", "title": "下課一起吃飯", "category": "美食", "date": "2099-12-20", "time": "18:30", "place": "台中車站附近", "address": "台中市示範地址", "lat": 24.1368, "lng": 120.6850, "capacity": 5, "joined": 1, "host": "小安"},
    {"id": "D002", "title": "週末桌遊團", "category": "桌遊", "date": "2099-12-21", "time": "14:00", "place": "草悟道附近", "address": "台中市示範地址", "lat": 24.1500, "lng": 120.6630, "capacity": 6, "joined": 1, "host": "阿哲"},
]
MAP_START = [24.1368, 120.6850]


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
for key, value in {
    "pick_lat": MAP_START[0], "pick_lng": MAP_START[1], "picked": False,
    "handled_click": None, "map_center": MAP_START[:], "map_zoom": 15, "map_key_id": 0,
    "place": "", "address": "", "origin_lat": None, "origin_lng": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


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
            raise RuntimeError("請設定 GAS_API_TOKEN")
        return fetch_events(URL, TOKEN)
    return st.session_state.demo_events


def distance_km(lat1, lng1, lat2, lng2):
    """Haversine 公式：兩點間地表直線距離，非道路里程。"""
    earth_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * earth_km * math.asin(math.sqrt(value))


def show_flash_message():
    message = st.session_state.pop("success_message", None)
    if message:
        st.success(message)


st.title("📍 附近揪團")
st.caption("第二階段：瀏覽器定位、OpenStreetMap 點選、直線距離；未使用 Google Maps API Key。")
st.info("GAS 試算表雲端資料" if URL else "示範資料模式（只存在目前程式執行記憶體）")
show_flash_message()
with st.sidebar:
    st.header("我的位置")
    mode = st.radio("選擇出發位置", ["瀏覽器目前位置", "手動輸入座標"])
    origin_lat = origin_lng = None
    if mode == "瀏覽器目前位置":
        position = streamlit_geolocation()
        if position and position.get("latitude") is not None and position.get("longitude") is not None:
            st.session_state.origin_lat = float(position["latitude"])
            st.session_state.origin_lng = float(position["longitude"])
        origin_lat, origin_lng = st.session_state.origin_lat, st.session_state.origin_lng
        if origin_lat is not None:
            st.success("已取得目前位置（切換模式後仍保留）")
        else:
            st.caption("按定位按鈕並允許瀏覽器存取位置；也可改用手動輸入。")
    else:
        origin_lat = st.number_input("緯度", min_value=-90.0, max_value=90.0, value=24.1477, format="%.5f")
        origin_lng = st.number_input("經度", min_value=-180.0, max_value=180.0, value=120.6736, format="%.5f")
    category_filter = st.selectbox("活動類別", ["全部", "美食", "桌遊", "運動", "其他"])
    max_km = st.slider("距離範圍（直線）公里", 1, 50, 20)
    include_unknown = st.checkbox("顯示無法計算距離的活動", value=True)
    st.caption("無法計算距離時，可能是尚未允許定位或活動沒有座標。出發位置不寫入試算表。")

left, right = st.columns([1.4, 1])
with left:
    st.header("活動清單")
    try:
        events = get_events()
    except Exception as exc:
        st.error(f"讀取失敗：{exc}")
        events = []
    shown = []
    for item in events:
        lat, lng = item.get("lat"), item.get("lng")
        try:
            item["distance"] = distance_km(origin_lat, origin_lng, float(lat), float(lng)) if origin_lat is not None and origin_lng is not None and lat is not None and lng is not None else None
        except (TypeError, ValueError):
            item["distance"] = None
        if category_filter != "全部" and item.get("category") != category_filter:
            continue
        if item["distance"] is None:
            if include_unknown:
                shown.append(item)
        elif item["distance"] <= max_km:
            shown.append(item)
    shown.sort(key=lambda item: item["distance"] if item["distance"] is not None else math.inf)
    if not shown:
        st.info("目前範圍內沒有符合條件的活動。")
    for item in shown:
        with st.container(border=True):
            st.subheader(item.get("title", "未命名活動"))
            st.write(f"{item.get('category', '')}｜{item.get('date', '')} {item.get('time', '')}")
            st.write(f"📍 {item.get('place', '')}｜{item.get('address', '')}")
            st.write(f"主揪：{item.get('host', '')}　名額：{item.get('joined', 0)} / {item.get('capacity', 0)}")
            dist = item.get("distance")
            st.metric("直線距離", f"{dist:.1f} 公里" if dist is not None else "尚無座標或尚未定位")
            destination = f"{item.get('lat')},{item.get('lng')}" if item.get("lat") is not None else item.get("address", "")
            if origin_lat is not None:
                url = f"https://www.google.com/maps/dir/?api=1&origin={quote_plus(f'{origin_lat},{origin_lng}')}&destination={quote_plus(str(destination))}"
            else:
                url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(str(destination))}"
            st.link_button("開啟 Google Maps 導航（網址連結）", url)
            with st.form(f"join_{item.get('id')}"):
                name = st.text_input("報名暱稱", key=f"name_{item.get('id')}")
                join = st.form_submit_button("報名")
            if join:
                try:
                    if URL:
                        gas_post({"action": "joinEvent", "eventId": item["id"], "name": name})
                        fetch_events.clear()
                    else:
                        target = next(row for row in st.session_state.demo_events if row["id"] == item["id"])
                        if not name.strip():
                            raise ValueError("請填報名暱稱")
                        already_joined = any(
                            row["eventId"] == item["id"] and row["name"].casefold() == name.strip().casefold()
                            for row in st.session_state.demo_joins
                        )
                        if already_joined:
                            raise ValueError("這個暱稱已報名（主揪也已占用一個名額）")
                        if target["joined"] >= target["capacity"]:
                            raise ValueError("活動已額滿")
                        target["joined"] += 1
                        st.session_state.demo_joins.append({"eventId": item["id"], "name": name.strip()})
                    st.session_state.success_message = "報名完成"
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

with right:
    st.header("在地圖選活動地點")
    st.caption("地圖初始顯示台中車站附近；點地圖選點後，活動才會取得座標。地圖來源：© OpenStreetMap contributors。")
    map_obj = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap", control_scale=True)
    if st.session_state.picked:
        selected = [float(st.session_state.pick_lat), float(st.session_state.pick_lng)]
        folium.Marker(selected, tooltip="目前選取的活動位置").add_to(map_obj)
    map_key = f"place_picker_{st.session_state.map_key_id}"
    result = st_folium(map_obj, height=330, width=None, key=map_key, returned_objects=["last_clicked", "bounds", "zoom"])
    if result:
        bounds = result.get("bounds") or {}
        southwest, northeast = bounds.get("_southWest"), bounds.get("_northEast")
        if southwest and northeast:
            try:
                st.session_state.map_center = [
                    (float(southwest["lat"]) + float(northeast["lat"])) / 2,
                    (float(southwest["lng"]) + float(northeast["lng"])) / 2,
                ]
            except (KeyError, TypeError, ValueError):
                pass
        zoom = result.get("zoom")
        if isinstance(zoom, (int, float)):
            st.session_state.map_zoom = int(zoom)
        click = result.get("last_clicked")
        if click and click.get("lat") is not None and click.get("lng") is not None:
            new_click = (round(float(click["lat"]), 7), round(float(click["lng"]), 7))
            if new_click != st.session_state.handled_click:
                st.session_state.handled_click = new_click
                st.session_state.pick_lat, st.session_state.pick_lng = new_click
                st.session_state.picked = True
                st.rerun()
    if st.session_state.picked:
        st.caption(f"已選位置：{st.session_state.pick_lat:.5f}, {st.session_state.pick_lng:.5f}")
    else:
        st.warning("尚未選擇地點。請先在地圖上點選位置，再建立活動。")
    with st.form("create_event"):
        title = st.text_input("活動名稱")
        category = st.selectbox("類別", ["美食", "桌遊", "運動", "其他"])
        event_date = st.date_input("日期", value=date.today())
        event_time = st.time_input("時間", value=time(18, 0))
        place = st.text_input("地標/店家名稱", key="place")
        address = st.text_input("地址或補充說明", key="address")
        host = st.text_input("主揪暱稱")
        capacity = st.number_input("名額（含主揪）", min_value=2, max_value=30, value=5)
        submit = st.form_submit_button("建立活動", type="primary")
    if submit:
        if not st.session_state.picked:
            st.warning("請先在地圖上點選位置，再建立活動。")
        elif not all([title.strip(), place.strip(), address.strip(), host.strip()]):
            st.warning("請填活動、地標、地址和暱稱")
        else:
            payload = {"action": "createEvent", "title": title.strip(), "category": category, "date": event_date.isoformat(), "time": event_time.strftime("%H:%M"), "place": place.strip(), "address": address.strip(), "capacity": int(capacity), "host": host.strip(), "lat": st.session_state.pick_lat, "lng": st.session_state.pick_lng}
            try:
                if URL:
                    gas_post(payload)
                    fetch_events.clear()
                else:
                    event_id = f"D{len(st.session_state.demo_events) + 1:03}"
                    st.session_state.demo_events.append({**payload, "id": event_id, "joined": 1})
                    st.session_state.demo_joins.append({"eventId": event_id, "name": host.strip()})
                st.session_state.picked = False
                st.session_state.handled_click = None
                st.session_state.map_key_id += 1
                st.session_state.success_message = "活動已建立。若要再開一團，請重新在地圖上點選位置。"
                st.rerun()
            except Exception as exc:
                st.error(f"建立失敗：{exc}")
st.divider()
st.caption("距離是球面直線距離，不是開車/步行路程。地圖點位座標屬於活動資料；目前位置不存入試算表。")
