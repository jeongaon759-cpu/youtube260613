import re
import streamlit as st
import pandas as pd
from collections import Counter

from googleapiclient.discovery import build

import plotly.express as px

from konlpy.tag import Okt

from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --------------------
# 페이지 설정
# --------------------
st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 YouTube 댓글 심층 분석기")

st.markdown("""
유튜브 링크를 입력하면

- 댓글 수집
- 감성 분석
- 키워드 분석
- 워드클라우드
- 여론 요약

을 수행합니다.
""")

# --------------------
# API KEY
# --------------------

api_key = st.text_input(
    "YouTube API Key",
    type="password"
)

video_url = st.text_input(
    "유튜브 링크 입력"
)

# --------------------
# URL → VIDEO ID
# --------------------

def extract_video_id(url):
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be\/([a-zA-Z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


# --------------------
# 댓글 수집
# --------------------

def get_comments(video_id, api_key):

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key
    )

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request:

        response = request.execute()

        for item in response["items"]:

            comment = item["snippet"][
                "topLevelComment"
            ]["snippet"]["textDisplay"]

            comments.append(comment)

        request = youtube.commentThreads().list_next(
            request,
            response
        )

        if len(comments) >= 3000:
            break

    return comments


# --------------------
# 간단 감성 분석
# --------------------

positive_words = [
    "좋다","좋아요","최고","감동",
    "멋지다","대박","응원",
    "행복","재밌다","훌륭"
]

negative_words = [
    "별로","싫다","최악",
    "실망","문제","망했다",
    "짜증","불편","아쉽다"
]


def sentiment(comment):

    score = 0

    for word in positive_words:
        if word in comment:
            score += 1

    for word in negative_words:
        if word in comment:
            score -= 1

    if score > 0:
        return "긍정"

    elif score < 0:
        return "부정"

    else:
        return "중립"


# --------------------
# 형태소 분석
# --------------------

okt = Okt()

stopwords = {
    "영상","진짜","너무","그냥",
    "정말","이거","저거","에서",
    "하는","하고","입니다","있다"
}


def extract_keywords(comments):

    nouns = []

    for comment in comments:

        try:
            words = okt.nouns(comment)

            words = [
                w for w in words
                if len(w) >= 2
                and w not in stopwords
            ]

            nouns.extend(words)

        except:
            pass

    return Counter(nouns)


# --------------------
# 분석 시작
# --------------------

if st.button("분석 시작"):

    if not api_key:
        st.error("API Key를 입력하세요.")
        st.stop()

    video_id = extract_video_id(video_url)

    if not video_id:
        st.error("올바른 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        comments = get_comments(
            video_id,
            api_key
        )

    if len(comments) == 0:
        st.warning("댓글이 없습니다.")
        st.stop()

    df = pd.DataFrame({
        "comment": comments
    })

    # ----------------
    # 감성 분석
    # ----------------

    df["sentiment"] = df["comment"].apply(
        sentiment
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "댓글 수",
        len(df)
    )

    col2.metric(
        "긍정 댓글",
        (df["sentiment"]=="긍정").sum()
    )

    col3.metric(
        "부정 댓글",
        (df["sentiment"]=="부정").sum()
    )

    sentiment_count = (
        df["sentiment"]
        .value_counts()
        .reset_index()
    )

    fig = px.pie(
        sentiment_count,
        names="sentiment",
        values="count",
        title="감성 비율"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ----------------
    # 키워드 분석
    # ----------------

    keyword_counter = extract_keywords(
        comments
    )

    top_words = keyword_counter.most_common(30)

    word_df = pd.DataFrame(
        top_words,
        columns=["단어","빈도"]
    )

    st.subheader("🔥 주요 키워드 TOP 30")

    fig2 = px.bar(
        word_df,
        x="단어",
        y="빈도"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ----------------
    # 워드클라우드
    # ----------------

    st.subheader("☁️ 워드클라우드")

    try:

        font_path = "NanumGothic.ttf"

        wc = WordCloud(
            font_path=font_path,
            width=1200,
            height=700,
            background_color="white"
        )

        wc.generate_from_frequencies(
            keyword_counter
        )

        fig3, ax = plt.subplots(
            figsize=(12,6)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig3)

    except Exception as e:

        st.error(
            "NanumGothic.ttf 파일을 프로젝트 폴더에 넣어주세요."
        )

    # ----------------
    # 대표 의견
    # ----------------

    st.subheader("📝 대표 댓글")

    for c in comments[:20]:
        st.write("•", c)
