import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
import re
from collections import defaultdict

# 構造化出力用のデータ型を定義
class MenuItem(BaseModel):
    main_name: str  # 例: "熟成牛の荒引きハンバーグ(ランチ)"
    category: str   # 例: "ランチ", "グランドメニュー", "セット", "単品" など
    variant: str    # 例: "200g", "250g", "ダブル", "通常" など
    price: str      # 例: "1180円(税込1298円)"

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

# @st.cache_data を削除して毎回フレッシュにAPI呼び出しを行う
# @st.cache_data(show_spinner=False)
def analyze_images(_images, prompt_text):
    client = genai.Client()
    contents = [*_images, prompt_text]
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MenuList,
        ),
    )
    return response.parsed

st.title("写真からメニュー選択アプリ")

# 画像のアップロード
uploaded_files = st.file_uploader(
    "メニューの写真をアップロードしてください（複数可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# ファイルの選択状況が変わった場合にセッション内の旧解析データをクリア
current_files_key = [f"{f.name}_{f.size}" for f in uploaded_files] if uploaded_files else []
if st.session_state.get('prev_uploaded_files') != current_files_key:
    st.session_state['prev_uploaded_files'] = current_files_key
    if 'menu_items' in st.session_state:
        del st.session_state['menu_items']
    if 'quantities' in st.session_state:
        del st.session_state['quantities']

if uploaded_files:
    images = [Image.open(file) for file in uploaded_files]
    
    # 選択された画像をグリッド表示
    st.write(f"**アップロード済み: {len(images)} 枚**")
    cols = st.columns(min(len(images), 3))
    for i, img in enumerate(images):
        cols[i % 3].image(img, caption=f"画像 {i+1}", use_container_width=True)
        
    if st.button("メニューを解析する"):
        # 【追加】ボタン押下時にキャッシュとセッションの旧データを完全消去
        st.cache_data.clear()
        if 'menu_items' in st.session_state:
            del st.session_state['menu_items']
        if 'quantities' in st.session_state:
            del st.session_state['quantities']

        with st.spinner("AIがすべての画像を解析中..."):
            client = genai.Client()
            
            prompt = (
                "送信された画像から、写っている全メニューと価格を抽出してください。\n"
                "1. main_name: 商品名本体(例: 熟成牛の荒引きハンバーグ)\n"
                "2. category: ランチメニューか、グランドメニュー(ディナー)か、セット/単品などの区分(例: ランチ, 通常)\n"
                "3. variant: グラム数やサイズ(例: 200g, ダブル)。ない場合は '通常'\n"
                "4. price: 価格表記\n"
                "同じ商品名でもランチとディナー、あるいはセット内容で価格が異なる場合は category を明確に区別してください。"
            )
            
            try:
                # 【修正】関数の引数からアンダースコアを除去して直接呼び出し
                menu_data = analyze_images(images, prompt)
                st.session_state['menu_items'] = menu_data.items
                st.session_state['quantities'] = {
                    f"{item.main_name}_{item.category}_{item.variant}_{idx}": 0 
                    for idx, item in enumerate(menu_data.items)
                }

            except Exception as e:
                st.error(f"解析エラー: {e}")

# 解析結果が存在すれば選択可能なリストを表示
if 'menu_items' in st.session_state:
    st.write("### メニュー一覧と数量選択")
    # 親メニュー名ごとにグループ化
    grouped_items = defaultdict(list)
    for idx, item in enumerate(st.session_state['menu_items']):
        grouped_items[item.main_name].append((idx, item))

    selected_orders = []
    total_amount = 0
    
    # グループごとにまとめて表示
    for main_name, items in grouped_items.items():
        st.markdown(f"#### 🍽️ {main_name}")
        
        for idx, item in items:
            col1, col2 = st.columns([3, 2])
            
            # 表示時に category（区分）を添えて判別可能にする
            with col1:
                cat_tag = f"[{item.category}] " if item.category and item.category != "通常" else ""
                if item.variant and item.variant != "通常":
                    st.write(f"・ **{cat_tag}{item.variant}**")
                else:
                    st.write(f"・ **{cat_tag}通常**")
                st.caption(f"価格: {item.price}")
            
            with col2:
                item_key = f"{item.main_name}_{item.variant}_{idx}"
                current_qty = st.session_state['quantities'].get(item_key, 0)
                qty = st.number_input(
                    "数量",
                    min_value=0,
                    max_value=20,
                    value=current_qty,
                    step=1,
                    key=f"qty_{idx}",
                    label_visibility="collapsed"
                )
                st.session_state['quantities'][item_key] = qty
            
            if qty > 0:
                unit_price = parse_price(item.price)
                subtotal = unit_price * qty
                total_amount += subtotal
                display_name = f"{item.main_name} ({item.variant})" if item.variant != "通常" else item.main_name
                selected_orders.append({
                    "name": display_name,
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