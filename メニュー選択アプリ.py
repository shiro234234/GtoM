import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

# 構造化出力用のデータ型を定義
# クラス定義の末尾にコロンと型注釈を追加
class MenuItem(BaseModel):
    name: str
    price: str

# クラス定義の末尾にコロンと型注釈を追加
class MenuList(BaseModel):
    items: list[MenuItem]

# 文字列をダブルクォーテーションで囲む
st.title("写真からメニュー選択アプリ")

# 画像のアップロード
# 文字列およびリスト内の要素をダブルクォーテーションで囲む
uploaded_file = st.file_uploader("メニューの写真をアップロードしてください", type=["jpg", "jpeg", "png"])

# if文の末尾にコロンを追加
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    # 文字列をダブルクォーテーションで囲む
    st.image(image, caption="アップロードされた画像", use_container_width=True)	

    # if文の末尾にコロン、文字列をダブルクォーテーションで囲む
    if st.button("メニューを解析する"):
        # with文の末尾にコロン、文字列をダブルクォーテーションで囲む
        with st.spinner("AIが解析中..."):
            # Clientの初期化（環境変数 GEMINI_API_KEY が設定されている前提）
            client = genai.Client(api_key="AQ.Ab8RN6J1IADCLstn16IjVt0Z-YfW_Bu4wt6p8KkeypScEXjgUQ")
            
            # 画像から構造化されたJSONデータを抽出
            # 文字列をダブルクォーテーションで囲む
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[image, "画像に写っているメニューと価格を抽出してください。"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MenuList,
                ),
            )
            
            # レスポンス（Pydanticオブジェクト）の取得
            # 型注釈の記述をコロンに修正
            menu_data: MenuList = response.parsed
            st.session_state['menu_items'] = menu_data.items

# 解析結果が存在すれば選択可能なリストを表示
# if文の末尾にコロンを追加
if 'menu_items' in st.session_state:
    # 文字列をダブルクォーテーションで囲む
    st.write("### 選択可能なメニュー一覧")
    selected_items = []
    
    # for文の末尾にコロンを追加
    for item in st.session_state['menu_items']:
        # f-stringのフォーマットをクォーテーションで囲む
        label = f"{item.name} ({item.price})"
        # if文の末尾にコロンを追加
        if st.checkbox(label, key=label):
            selected_items.append(item)
            
    # if文の末尾にコロンを追加
    if selected_items:
        # 文字列をダブルクォーテーションで囲む
        st.write("---")
        st.write("**選択されたメニュー:**")
        # for文の末尾にコロンを追加
        for sel in selected_items:
            # f-stringのフォーマットをクォーテーションで囲む
            st.write(f"- {sel.name}: {sel.price}")