import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
import re
from collections import defaultdict

# 構造化出力用のデータ型を定義
class MenuItem(BaseModel):
    name: str
    price: str

class MenuList(BaseModel):
    items: list[MenuItem]

# 数字以外の文字を取り除いて数値（int）に変換するヘルパー関数
def parse_price(price_str: str) -> int:
    # 「税込」の直後にある数字（カンマ込み）を探す
    tax_included_match = re.search(r'税込\s*([\d,]+)', price_str)
    if tax_included_match:
        return int(tax_included_match.group(1).replace(',', ''))
    
    # 税込表記がない場合は最初に出てくる数字を取得
    first_match = re.search(r'\d[\d,]*', price_str)
    if first_match:
        return int(first_match.group().replace(',', ''))
        
    return 0

# 【追加】メニュー名から商品名本体とグラム数/サイズ等のバリエーションを分離する関数
def parse_menu_name(full_name: str):
    # グラム数、サイズ、個数などのパターン（例: 200g, 100g, S/M/L, 2人前など）
    pattern = r'(\d+\s*(?:g|g|kg|粒|個|本|枚|皿|人前)|[SMLsml]サイズ|[大中小]|シングル|ダブル)'
    match = re.search(pattern, full_name)
    
    if match:
        variant = match.group(0)
        # バリエーション部分を取り除いたものを商品名本体とする
        base_name = full_name.replace(variant, '').strip()
        # 記号の取りこぼし等を整理
        base_name = re.sub(r'[\s\(\)（）]+$', '', base_name).strip()
        return base_name if base_name else full_name, variant
    else:
        return full_name, "通常"
    
st.title("写真からメニュー選択アプリ")

# 画像のアップロード
uploaded_files = st.file_uploader(
    "メニューの写真をアップロードしてください（複数可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    images = [Image.open(file) for file in uploaded_files]
    
    # 選択された画像をグリッド表示
    st.write(f"**アップロード済み: {len(images)} 枚**")
    cols = st.columns(min(len(images), 3))
    for i, img in enumerate(images):
        cols[i % 3].image(img, caption=f"画像 {i+1}", use_container_width=True)
        
    if st.button("メニューを解析する"):
        with st.spinner("AIがすべての画像を解析中..."):
            client = genai.Client(api_key="AQ.Ab8RN6J1IADCLstn16IjVt0Z-YfW_Bu4wt6p8KkeypScEXjgUQ")
            
            # すべての画像とプロンプトをリストにして送信
            contents = [*images, "送信されたすべての画像から、写っている全メニューと価格を網羅して抽出してください。"]
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contents,
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
    st.write("### メニュー一覧と数量選択")
    # 【追加】商品名本体ごとにメニューをグループ化
    grouped_items = defaultdict(list)
    for item in st.session_state['menu_items']:
        base_name, variant = parse_menu_name(item.name)
        grouped_items[base_name].append((variant, item))

    selected_orders = []
    total_amount = 0
    item_index = 0
    
    # グループごとにまとめて表示
    for base_name, variants in grouped_items.items():
        st.markdown(f"#### 🍽️ {base_name}")
        
        for variant, item in variants:
            col1, col2 = st.columns([3, 2])
        
        with col1:
            if variant != "通常":
                    st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;・ **{variant}**")
                else:
                    st.write("&nbsp;&nbsp;&nbsp;&nbsp;・ 通常")
                st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;価格: {item.price}")
            
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
            item_index += 1
            
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
