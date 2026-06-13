import streamlit as st
import pandas as pd
import re
from collections import Counter

from googleapiclient.discovery import build
import plotly.express as px

# =====================================================
# 페이지 설정
# =====================================================

st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 유튜브 댓글 심층 분석기")
st.caption("YouTube API 기반 댓글 여론 분석")

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
# 영상 ID 추출
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
# 불용어
# =====================================================

STOPWORDS = {
    "진짜","그냥","너무","정말","영상",
    "댓글","사람","생각","이거","저거",
    "그거","이번","이런","저런","있는",
    "하는","같은","근데","에서","으로",
    "그리고","입니다","하면","하는데",
    "왜냐하면","오늘","지금","보고",
    "정도","때문","하네요","합니다"
}

# =====================================================
# 키워드 추출
# =====================================================

def extract_keywords(texts):

    words = []

    for text in texts:

        found = re.findall(
            r"[가-힣]{2,}",
            str(text)
        )

        words.extend(found)

    words = [
        word
        for word in words
        if word not in STOPWORDS
    ]

    return words

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

    with st.spinner("댓글 분석 중..."):

        df = get_comments(video_id)

    if len(df) == 0:

        st.error("댓글이 없습니다.")
        st.stop()

    st.success(f"{len(df):,}개의 댓글을 수집했습니다.")

    # =================================================
    # 통계
    # =================================================

    col1, col2 = st.columns(2)

    with col1:
        st.metric("댓글 수", f"{len(df):,}")

    with col2:
        st.metric(
            "총 좋아요 수",
            f"{df['likes'].sum():,}"
        )

    # =================================================
    # 키워드 분석
    # =================================================

    keywords = extract_keywords(
        df["comment"]
    )

    counter = Counter(keywords)

    top5 = counter.most_common(5)

    top5_words = [
        word
        for word, count in top5
    ]

    st.subheader("🔍 핵심 키워드")

    st.info(
        "이 영상에서 가장 많이 관측된 키워드는\n\n"
        + ", ".join(top5_words)
        + " 입니다."
    )

    # =================================================
    # TOP20 그래프
    # =================================================

    keyword_df = pd.DataFrame(
        counter.most_common(20),
        columns=["키워드", "빈도"]
    )

    st.subheader("📈 키워드 빈도")

    fig = px.bar(
        keyword_df,
        x="키워드",
        y="빈도",
        text="빈도"
    )

    fig.update_layout(
        xaxis_title="키워드",
        yaxis_title="등장 횟수"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =================================================
    # TOP 댓글
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
    # 전체 댓글
    # =================================================

    with st.expander("전체 댓글 보기"):

        st.dataframe(
            df,
            use_container_width=True
        )
