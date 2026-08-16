import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
import re

# 構造化出力用のデータ型を定義
class MenuItem(BaseModel):
    name: str
    price: str

class MenuList(BaseModel):
    items: list[MenuItem]

# 数字以外の文字を取り除いて数値（int）に変換するヘルパー関数
def parse_price(price_str: str) -> int:
    # 数字だけを抽出（例: "1,200円" -> "1200"）
    numbers = re.sub(r'[^\d]', '', price_str)
    return int(numbers) if numbers else 0
    
st.title("写真からメニュー選択アプリ")

# 画像のアップロード
uploaded_file = st.file_uploader("メニューの写真をアップロードしてください", type=["jpg", "jpeg", "png"])

# if文の末尾にコロンを追加
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_container_width=True)	

    # if文の末尾にコロン、文字列をダブルクォーテーションで囲む
    if st.button("メニューを解析する"):
        # with文の末尾にコロン、文字列をダブルクォーテーションで囲む
        with st.spinner("AIが解析中..."):
            # Clientの初期化（環境変数 GEMINI_API_KEY が設定されている前提）
            client = genai.Client(api_key="AQ.Ab8RN6J1IADCLstn16IjVt0Z-YfW_Bu4wt6p8KkeypScEXjgUQ")
            
            # 画像から構造化されたJSONデータを抽出
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[image, "画像に写っているメニューと価格を抽出してください。"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MenuList,
                ),
            )
            
            # レスポンス（Pydanticオブジェクト）の取得
            menu_data: MenuList = response.parsed
            st.session_state['menu_items'] = menu_data.items
            # 数量を管理する辞書を初期化
            st.session_state['quantities'] = {item.name: 0 for item in menu_data.items}

# 解析結果が存在すれば選択可能なリストを表示
if 'menu_items' in st.session_state:
    st.write("### 選択可能なメニュー一覧")
    selected_items = []
    total_amount = 0
    
    # 各メニューごとに数量変更ボタン（＋／ー）を配置
    for idx, item in enumerate(st.session_state['menu_items']):
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.write(f"**{item.name}**")
            st.caption(f"価格: {item.price}")
            
        with col2:
            # ＋ーボタン付きの数値入力UI
            # 数量の初期値や増減の設定
            current_qty = st.session_state['quantities'].get(item.name, 0)
            qty = st.number_input(
                "数量",
                min_value=0,
                max_value=20,
                value=current_qty,
                step=1,
                key=f"qty_{idx}_{item.name}",
                label_visibility="collapsed"
            )
            st.session_state['quantities'][item.name] = qty
            
        if qty > 0:
            unit_price = parse_price(item.price)
            subtotal = unit_price * qty
            total_amount += subtotal
            selected_orders.append({
                "name": item.name,
                "price_str": item.price,
                "unit_price": unit_price,
                "qty": qty,
                "subtotal": subtotal
            })
            
        st.write("---")
            
    # 注文内容の確認と合計金額の表示
    if selected_orders:
        st.write("### 🛒 選択された注文内容")
        for order in selected_orders:
            if order['unit_price'] > 0:
                st.write(f"- **{order['name']}** × {order['qty']}個（小計: {order['subtotal']:,}円）")
            else:
                st.write(f"- **{order['name']}** ({order['price_str']}) × {order['qty']}個")
                
        st.write("---")
        if total_amount > 0:
            st.subheader(f"合計金額: {total_amount:,} 円")
