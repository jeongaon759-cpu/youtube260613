import streamlit as st
import pandas as pd
import re
from collections import Counter

from googleapiclient.discovery import build

import plotly.express as px

from wordcloud import WordCloud
import matplotlib.pyplot as plt


# =====================================================
# 페이지 설정
# =====================================================

st.set_page_config(
    page_title="유튜브 댓글 심층 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 유튜브 댓글 심층 분석기")
st.caption("YouTube API 기반 댓글 수집 및 여론 분석")


# =====================================================
# API KEY
# =====================================================

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)


# =====================================================
# 유튜브 ID 추출
# =====================================================

def extract_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be\/([^?]+)",
        r"shorts\/([^?]+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


# =====================================================
# 댓글 수집
# =====================================================

def get_comments(video_id, max_comments=1000):

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

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "comment": snippet["textDisplay"],
                "likes": snippet["likeCount"]
            })

            if len(comments) >= max_comments:
                break

        if len(comments) >= max_comments:
            break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return pd.DataFrame(comments)


# =====================================================
# 감성 사전
# =====================================================

positive_words = [
    "좋다", "최고", "멋지다", "감동", "재밌다",
    "행복", "대박", "훌륭", "추천", "사랑",
    "웃기다", "잘한다", "응원", "감사" , "100" 
]

negative_words = [
    "별로", "싫다", "최악", "짜증", "화난다",
    "실망", "구리다", "아쉽다", "노잼",
    "답답", "억지", "망했다"
]


def sentiment(text):

    score = 0

    text = str(text)

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

    else:
        return "중립"


# =====================================================
# 키워드 추출
# =====================================================

STOPWORDS = {
    "진짜", "그냥", "너무", "정말",
    "영상", "댓글", "사람", "생각",
    "이번", "이거", "저거", "그것",
    "에서", "으로", "그리고", "입니다",
    "있는", "하는", "같은", "근데",
    "하면", "하는데", "왜냐하면"
}


def extract_keywords(texts):

    words = []

    for text in texts:

        found = re.findall(
            r"[가-힣]{2,}",
            str(text)
        )

        words.extend(found)

    words = [
        word for word in words
        if word not in STOPWORDS
    ]

    return words


# =====================================================
# 워드클라우드
# =====================================================

def generate_wordcloud(freq_dict):

    try:

        wc = WordCloud(
            font_path="NanumGothic.ttf",
            width=1200,
            height=600,
            background_color="white"
        ).generate_from_frequencies(freq_dict)

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig)

    except Exception:

        st.error(
            "프로젝트 폴더에 NanumGothic.ttf 파일을 업로드해주세요."
        )


# =====================================================
# UI
# =====================================================

url = st.text_input(
    "유튜브 링크 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)

if st.button("분석 시작"):

    if not url:

        st.warning("유튜브 링크를 입력해주세요.")
        st.stop()

    video_id = extract_video_id(url)

    if not video_id:

        st.error("올바른 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id)

    if len(df) == 0:

        st.error("댓글이 없습니다.")
        st.stop()

    st.success(f"{len(df):,}개의 댓글을 수집했습니다.")

    # =================================================
    # 기본 통계
    # =================================================

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "댓글 수",
            f"{len(df):,}"
        )

    with col2:

        st.metric(
            "총 좋아요",
            f"{df['likes'].sum():,}"
        )

    # =================================================
    # 감성분석
    # =================================================

    st.subheader("😊 감성 분석")

    df["감성"] = df["comment"].apply(sentiment)

    sentiment_df = (
        df["감성"]
        .value_counts()
        .reset_index()
    )

    sentiment_df.columns = [
        "감성",
        "개수"
    ]

    fig = px.pie(
        sentiment_df,
        names="감성",
        values="개수",
        hole=0.4
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =================================================
    # 좋아요 TOP 댓글
    # =================================================

    st.subheader("🔥 좋아요 TOP 10 댓글")

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

    # =================================================
    # 키워드 분석
    # =================================================

    st.subheader("📌 핵심 키워드")

    keywords = extract_keywords(
        df["comment"]
    )

    counter = Counter(keywords)

    keyword_df = pd.DataFrame(
        counter.most_common(20),
        columns=["단어", "빈도"]
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

    # =================================================
    # 워드클라우드
    # =================================================

    st.subheader("☁️ 워드클라우드")

    generate_wordcloud(counter)

    # =================================================
    # 자주 등장한 단어
    # =================================================

    st.subheader("📊 단어 빈도 순위")

    st.dataframe(
        keyword_df,
        use_container_width=True
    )

    # =================================================
    # 전체 댓글
    # =================================================

    with st.expander("전체 댓글 보기"):

        st.dataframe(
            df,
            use_container_width=True
        )
