import streamlit as st
import pandas as pd
import numpy as np
import re

from googleapiclient.discovery import build

from collections import Counter

import plotly.express as px

from wordcloud import WordCloud
import matplotlib.pyplot as plt

from konlpy.tag import Okt

# --------------------
# 페이지 설정
# --------------------

st.set_page_config(
    page_title="유튜브 댓글 심층 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 유튜브 댓글 심층 분석기")
st.caption("YouTube API 기반 댓글 감성 분석 + 한글 워드클라우드")

# --------------------
# API
# --------------------

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# --------------------
# 영상 ID 추출
# --------------------

def extract_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be\/([^?]+)",
        r"shorts\/([^?]+)"
    ]

    for p in patterns:
        match = re.search(p, url)

        if match:
            return match.group(1)

    return None

# --------------------
# 댓글 수집
# --------------------

def get_comments(video_id, max_comments=1000):

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < max_comments:

        response = request.execute()

        for item in response["items"]:

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "comment": snippet["textDisplay"],
                "likes": snippet["likeCount"]
            })

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return pd.DataFrame(comments)

# --------------------
# 감성분석
# --------------------

positive_words = [
    "좋다","최고","멋지다","감동","재밌다","행복",
    "대박","훌륭","추천","사랑","웃기다"
]

negative_words = [
    "별로","싫다","최악","짜증","화난다",
    "노잼","실망","구리다","아쉽다"
]

def sentiment(text):

    score = 0

    for word in positive_words:
        if word in text:
            score += 1

    for word in negative_words:
        if word in text:
            score -= 1

    if score > 0:
        return "긍정"

    elif score < 0:
        return "부정"

    return "중립"

# --------------------
# 형태소 분석
# --------------------

okt = Okt()

def extract_nouns(texts):

    nouns = []

    for text in texts:

        try:
            nouns.extend(
                okt.nouns(str(text))
            )

        except:
            pass

    nouns = [
        n for n in nouns
        if len(n) >= 2
    ]

    return nouns

# --------------------
# UI
# --------------------

url = st.text_input(
    "유튜브 링크 입력"
)

if st.button("분석 시작"):

    if not url:
        st.warning("링크를 입력하세요.")
        st.stop()

    video_id = extract_video_id(url)

    if not video_id:
        st.error("유효한 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id)

    if len(df) == 0:
        st.error("댓글을 찾을 수 없습니다.")
        st.stop()

    st.success(
        f"{len(df):,}개의 댓글 수집 완료"
    )

    # --------------------
    # 감성분석
    # --------------------

    df["감성"] = df["comment"].apply(sentiment)

    sentiment_count = (
        df["감성"]
        .value_counts()
        .reset_index()
    )

    sentiment_count.columns = [
        "감성",
        "개수"
    ]

    st.subheader("😊 감성 분석")

    fig = px.pie(
        sentiment_count,
        names="감성",
        values="개수"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------
    # 좋아요 TOP 댓글
    # --------------------

    st.subheader("🔥 좋아요 TOP 댓글")

    top_comments = (
        df.sort_values(
            "likes",
            ascending=False
        )
        .head(10)
    )

    st.dataframe(
        top_comments,
        use_container_width=True
    )

    # --------------------
    # 단어 분석
    # --------------------

    st.subheader("📌 핵심 키워드")

    nouns = extract_nouns(
        df["comment"]
    )

    word_count = Counter(nouns)

    keyword_df = pd.DataFrame(
        word_count.most_common(20),
        columns=["단어","빈도"]
    )

    fig2 = px.bar(
        keyword_df,
        x="단어",
        y="빈도"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # --------------------
    # 워드클라우드
    # --------------------

    st.subheader("☁️ 워드클라우드")

    # 한글 폰트 경로
    font_path = "NanumGothic.ttf"

    try:

        wc = WordCloud(
            font_path=font_path,
            width=1200,
            height=600,
            background_color="white"
        ).generate_from_frequencies(
            word_count
        )

        fig3, ax = plt.subplots(
            figsize=(12,6)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig3)

    except Exception:

        st.error(
            "NanumGothic.ttf 파일을 프로젝트 루트에 업로드하세요."
        )

    # --------------------
    # 원본 댓글
    # --------------------

    st.subheader("💬 전체 댓글")

    st.dataframe(
        df,
        use_container_width=True
    )
