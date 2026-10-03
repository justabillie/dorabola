# app.py - Complete with drama detail page
import streamlit as st
import pandas as pd
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Dorabola",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load external CSS
def load_css():
    try:
        with open('styles.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

# ========== SESSION STATE INITIALIZATION ==========
if "mood_filter" not in st.session_state:
    st.session_state.mood_filter = "Any"
if "genre_filter" not in st.session_state:
    st.session_state.genre_filter = "Any"
if "cast_filter" not in st.session_state:
    st.session_state.cast_filter = "Any"
if "status_filter" not in st.session_state:
    st.session_state.status_filter = "All"
if "min_rating" not in st.session_state:
    st.session_state.min_rating = 0.0
if "show_watched" not in st.session_state:
    st.session_state.show_watched = False
if "show_rating_dialog" not in st.session_state:
    st.session_state.show_rating_dialog = False
if "current_rating_drama" not in st.session_state:
    st.session_state.current_rating_drama = None
if "temp_rating" not in st.session_state:
    st.session_state.temp_rating = 8.0
if "selected_drama_id" not in st.session_state:
    st.session_state.selected_drama_id = None
if "view_detail" not in st.session_state:
    st.session_state.view_detail = False

# ========== STICKY HEADER CSS ==========
st.markdown("""
    <style>
        .filter-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #5C3D45;
            margin-bottom: 0.2rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Hide default Streamlit elements */
        #MainMenu, footer, header, .stDeployButton, 
        [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display: none !important;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .rating-dialog {
            animation: slideIn 0.25s ease-out;
        }
    </style>
""", unsafe_allow_html=True)

# ========== STAR RATING FUNCTIONS ==========
def get_star_display(rating):
    full_stars = int(rating // 2)
    half_star = 1 if (rating % 2) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    star_string = "★" * full_stars
    if half_star:
        star_string += "⯨"
    star_string += "☆" * empty_stars
    
    return star_string

# ========== DATABASE FUNCTIONS ==========
def init_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS watched (
            drama_id INTEGER PRIMARY KEY,
            drama_title TEXT NOT NULL,
            rating REAL,
            date_watched TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_to_watched(drama_id, drama_title, rating):
    try:
        conn = sqlite3.connect('user_data.db')
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO watched (drama_id, drama_title, rating, date_watched)
            VALUES (?, ?, ?, ?)
        ''', (int(drama_id), drama_title, float(rating), datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def remove_from_watched(drama_id):
    try:
        conn = sqlite3.connect('user_data.db')
        c = conn.cursor()
        c.execute('DELETE FROM watched WHERE drama_id = ?', (int(drama_id),))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def get_watched_list():
    try:
        conn = sqlite3.connect('user_data.db')
        c = conn.cursor()
        c.execute('SELECT drama_id, drama_title, rating FROM watched ORDER BY date_watched DESC')
        watched = c.fetchall()
        conn.close()
        return watched
    except Exception:
        return []

def is_watched(drama_id):
    watched = get_watched_list()
    return any(w[0] == int(drama_id) for w in watched)

# ========== DATA LOADING ==========
@st.cache_data
def load_data():
    df = pd.read_csv('dramas.csv')
    df['id'] = df['id'].astype(int)
    current_year = datetime.now().year
    df['status'] = df['year'].apply(lambda x: 'Ongoing' if str(x) == str(current_year) else 'Completed')
    df = df.drop_duplicates(subset=['title'], keep='first')
    return df

@st.cache_data
def create_similarity_matrix(df):
    df['combined'] = (
        df['genres'].fillna('') + ' ' +
        df['cast'].fillna('') + ' ' +
        df['overview'].fillna('') + ' ' +
        df['mood_tags'].fillna('')
    )
    tfidf = TfidfVectorizer(stop_words='english', max_features=3000)
    matrix = tfidf.fit_transform(df['combined'])
    similarity = cosine_similarity(matrix)
    return similarity

def get_all_cast_members(df):
    all_cast = set()
    for c in df['cast'].dropna():
        for actor in str(c).split(','):
            actor = actor.strip()
            if actor and actor not in ['Loading...', 'Popular cast members', 'Cast information not available']:
                all_cast.add(actor)
    return sorted(list(all_cast))

def get_drama_by_id(df, drama_id):
    drama_data = df[df['id'] == drama_id]
    if len(drama_data) > 0:
        drama = drama_data.iloc[0]
        return {
            'id': int(drama['id']),
            'title': str(drama['title']),
            'poster': str(drama['poster_url']) if pd.notna(drama['poster_url']) else None,
            'rating': float(drama['vote_average']),
            'genres': str(drama['genres']),
            'cast': str(drama['cast']),
            'overview': str(drama['overview']),
            'status': str(drama['status']),
            'year': str(drama['year']),
            'mood_tags': str(drama['mood_tags']) if 'mood_tags' in drama else ''
        }
    return None

def get_recommendations(df, similarity, watched_list, mood_filter=None, genre_filter=None, cast_filter=None, status_filter=None, min_rating=0, n=20):
    all_indices = list(range(len(df)))
    watched_ids = [w[0] for w in watched_list] if watched_list else []
    unwatched_indices = [i for i in all_indices if df.iloc[i]['id'] not in watched_ids]
    
    if watched_list and len(watched_list) > 0:
        high_rated_ids = [w[0] for w in watched_list if w[2] >= 7]
        if high_rated_ids:
            scores = {}
            for drama_id in high_rated_ids:
                idx = df[df['id'] == drama_id].index
                if len(idx) > 0:
                    idx = idx[0]
                    for i in unwatched_indices:
                        if i not in scores:
                            scores[i] = 0
                        scores[i] += similarity[idx][i]
            sorted_indices = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        else:
            sorted_indices = df.iloc[unwatched_indices]['vote_count'].sort_values(ascending=False).index.tolist()
    else:
        sorted_indices = df.iloc[unwatched_indices]['vote_count'].sort_values(ascending=False).index.tolist()
    
    if mood_filter and mood_filter != "Any":
        filtered_indices = []
        for idx in sorted_indices:
            if mood_filter in str(df.iloc[idx]['mood_tags']):
                filtered_indices.append(idx)
        sorted_indices = filtered_indices
    
    if genre_filter and genre_filter != "Any":
        filtered_indices = []
        for idx in sorted_indices:
            if genre_filter in str(df.iloc[idx]['genres']):
                filtered_indices.append(idx)
        sorted_indices = filtered_indices
    
    if cast_filter and cast_filter != "Any":
        filtered_indices = []
        for idx in sorted_indices:
            if cast_filter in str(df.iloc[idx]['cast']):
                filtered_indices.append(idx)
        sorted_indices = filtered_indices
    
    if status_filter and status_filter != "All":
        filtered_indices = []
        for idx in sorted_indices:
            if df.iloc[idx]['status'] == status_filter:
                filtered_indices.append(idx)
        sorted_indices = filtered_indices
    
    if min_rating > 0:
        filtered_indices = []
        for idx in sorted_indices:
            if df.iloc[idx]['vote_average'] >= min_rating:
                filtered_indices.append(idx)
        sorted_indices = filtered_indices
    
    seen_titles = set()
    recommendations = []
    for idx in sorted_indices:
        if len(recommendations) >= n:
            break
        title = str(df.iloc[idx]['title'])
        if title not in seen_titles:
            seen_titles.add(title)
            recommendations.append({
                'id': int(df.iloc[idx]['id']),
                'title': title,
                'poster': str(df.iloc[idx]['poster_url']) if pd.notna(df.iloc[idx]['poster_url']) and df.iloc[idx]['poster_url'] != 'nan' else None,
                'rating': float(df.iloc[idx]['vote_average']),
                'genres': str(df.iloc[idx]['genres']),
                'cast': str(df.iloc[idx]['cast']),
                'overview': str(df.iloc[idx]['overview'])[:150],
                'status': str(df.iloc[idx]['status'])
            })
    
    return recommendations

# ========== MAIN APP ==========
init_db()

try:
    df = load_data()
    similarity = create_similarity_matrix(df)
    all_cast_members = get_all_cast_members(df)
except FileNotFoundError:
    st.error("No drama data found. Please run: python data_fetcher.py first")
    st.stop()

# ========== DRAMA DETAIL PAGE ==========
def show_drama_detail():
    """Display detailed information about a drama"""
    drama = get_drama_by_id(df, st.session_state.selected_drama_id)
    
    if not drama:
        st.error("Drama not found")
        return
    
    # Back button
    if st.button("← Back to Recommendations", use_container_width=False):
        st.session_state.view_detail = False
        st.session_state.selected_drama_id = None
        st.rerun()
    
    st.markdown("---")
    
    # Drama header with poster and info side by side
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if drama['poster']:
            st.image(drama['poster'], use_container_width=True)
        else:
            st.markdown(f'<div style="background: #FFB8C6; height: 400px; border-radius: 12px; display: flex; align-items: center; justify-content: center;"><span style="font-size: 3rem;">🎬</span></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<h2 style='margin-bottom: 0.5rem; color: #2D1B1F;'>{drama['title']}</h2>", unsafe_allow_html=True)
        
        stars = get_star_display(drama['rating'])
        st.markdown(f"<p style='font-size: 1.1rem; color: #FFB800; margin-bottom: 1rem;'>{stars} {drama['rating']:.1f}/10</p>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="margin: 1rem 0; line-height: 1.8;">
            <p><strong>Year:</strong> {drama['year']}</p>
            <p><strong>Status:</strong> {drama['status']}</p>
            <p><strong>Genres:</strong> {drama['genres']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if is_watched(drama['id']):
            st.markdown('<div style="background: #E8F5F0; color: #7BC5AE; text-align: center; padding: 0.6rem; border-radius: 8px; font-weight: 500;">Already in Your Watched List</div>', unsafe_allow_html=True)
        else:
            if st.button("Mark as Watched", use_container_width=True):
                st.session_state.show_rating_dialog = True
                st.session_state.current_rating_drama = drama
                st.session_state.temp_rating = 8.0
                st.rerun()
    
    # Synopsis section
    st.markdown("---")
    st.markdown("<h3>Synopsis</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='line-height: 1.6; color: #2D1B1F;'>{drama['overview']}</p>", unsafe_allow_html=True)
    
    # Cast section
    if drama['cast'] and drama['cast'] != 'Cast information not available':
        st.markdown("<h3>Cast</h3>", unsafe_allow_html=True)
        cast_list = [c.strip() for c in drama['cast'].split(',')]
        
        cast_cols = st.columns(4)
        for idx, actor in enumerate(cast_list[:12]):
            with cast_cols[idx % 4]:
                st.markdown(f"<p style='margin: 0.25rem 0; color: #5C3D45;'>{actor}</p>", unsafe_allow_html=True)
    
    st.markdown("---")

# ========== RATING DIALOG ==========
def show_rating_dialog():
    if st.session_state.show_rating_dialog and st.session_state.current_rating_drama:
        drama = st.session_state.current_rating_drama
        
        with st.container():
            st.markdown('<div class="rating-dialog">', unsafe_allow_html=True)
            st.markdown("---")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f"<h3 style='text-align: center; margin-bottom: 0;'>Rate This Drama</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; color: #5C3D45; margin-top: 0;'>{drama['title']}</p>", unsafe_allow_html=True)
                
                rating_options = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
                rating_index = rating_options.index(st.session_state.temp_rating) if st.session_state.temp_rating in rating_options else 16
                rating = st.selectbox(
                    "Your Rating (0-10, 0.5 increments)",
                    rating_options,
                    index=rating_index,
                    format_func=lambda x: f"{x:.1f}",
                    key="dialog_rating"
                )
                
                stars = get_star_display(rating)
                st.markdown(f'<p style="text-align: center; font-size: 1.2rem; color: #FFB800;">{stars} {rating:.1f}/10</p>', unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Save", use_container_width=True):
                        if add_to_watched(drama['id'], drama['title'], rating):
                            st.session_state.show_rating_dialog = False
                            st.session_state.current_rating_drama = None
                            st.session_state.temp_rating = 8.0
                            st.success(f"Added {drama['title']} to your watched list!")
                            st.rerun()
                with col_btn2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.show_rating_dialog = False
                        st.session_state.current_rating_drama = None
                        st.session_state.temp_rating = 8.0
                        st.rerun()
            st.markdown("---")
            st.markdown('</div>', unsafe_allow_html=True)

# ========== MAIN UI ==========
if st.session_state.view_detail:
    show_drama_detail()
else:
    # ========== HEADER CONTAINER ==========
    with st.container():
        st.markdown('<h1 style="text-align: center; font-size: 1.8rem; color: #2D1B1F; margin-bottom: 0;">Dorabola</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #5C3D45; font-size: 0.75rem; margin-bottom: 1rem;">Discover your next favorite K-drama</p>', unsafe_allow_html=True)

        # Filters
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.markdown('<div class="filter-label">MOOD</div>', unsafe_allow_html=True)
            mood_options = ["Any", "Romantic", "Heartwarming", "Emotional", "Thrilling", "Exciting", "Magical"]
            selected_mood = st.selectbox("", mood_options, key="mood_select", label_visibility="collapsed")
            if selected_mood != st.session_state.mood_filter:
                st.session_state.mood_filter = selected_mood
                st.rerun()

        with col2:
            st.markdown('<div class="filter-label">GENRE</div>', unsafe_allow_html=True)
            all_genres = set()
            for g in df['genres'].dropna():
                for genre in str(g).split(','):
                    all_genres.add(genre.strip())
            genre_options = ["Any"] + sorted(list(all_genres))[:25]
            selected_genre = st.selectbox("", genre_options, key="genre_select", label_visibility="collapsed")
            if selected_genre != st.session_state.genre_filter:
                st.session_state.genre_filter = selected_genre
                st.rerun()

        with col3:
            st.markdown('<div class="filter-label">CAST</div>', unsafe_allow_html=True)
            cast_options = ["Any"] + all_cast_members[:40]
            selected_cast = st.selectbox("", cast_options, key="cast_select", label_visibility="collapsed")
            if selected_cast != st.session_state.cast_filter:
                st.session_state.cast_filter = selected_cast
                st.rerun()

        with col4:
            st.markdown('<div class="filter-label">STATUS</div>', unsafe_allow_html=True)
            status_options = ["All", "Completed", "Ongoing"]
            selected_status = st.selectbox("", status_options, key="status_select", label_visibility="collapsed")
            if selected_status != st.session_state.status_filter:
                st.session_state.status_filter = selected_status
                st.rerun()

        with col5:
            st.markdown('<div class="filter-label">MINIMUM RATING</div>', unsafe_allow_html=True)
            rating_options = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
            selected_index = rating_options.index(st.session_state.min_rating) if st.session_state.min_rating in rating_options else 0
            min_rating = st.selectbox("", rating_options, index=selected_index, format_func=lambda x: f"{x:.1f}", key="min_rating_select", label_visibility="collapsed")
            if min_rating != st.session_state.min_rating:
                st.session_state.min_rating = min_rating
                st.rerun()

        with col6:
            st.markdown('<div class="filter-label">HISTORY</div>', unsafe_allow_html=True)
            if st.button("View Watched List" if not st.session_state.show_watched else "Close List", use_container_width=True):
                st.session_state.show_watched = not st.session_state.show_watched
                st.rerun()

        active = []
        if st.session_state.mood_filter != "Any":
            active.append(f"Mood: {st.session_state.mood_filter}")
        if st.session_state.genre_filter != "Any":
            active.append(f"Genre: {st.session_state.genre_filter}")
        if st.session_state.cast_filter != "Any":
            active.append(f"Cast: {st.session_state.cast_filter}")
        if st.session_state.status_filter != "All":
            active.append(f"Status: {st.session_state.status_filter}")
        if st.session_state.min_rating > 0:
            active.append(f"Min Rating: {st.session_state.min_rating:.1f}+")
        
        if active:
            st.caption(f"Active filters: {', '.join(active)}")

    # ========== RATING DIALOG ==========
    show_rating_dialog()

    # ========== WATCHED LIST ==========
    if st.session_state.show_watched:
        st.markdown("### Your Watch History")
        watched_list = get_watched_list()
        
        if watched_list:
            watched_dramas = []
            for drama_id, title, user_rating in watched_list:
                drama_data = df[df['id'] == drama_id]
                if len(drama_data) > 0:
                    drama = drama_data.iloc[0]
                    watched_dramas.append({
                        'id': drama_id,
                        'title': title,
                        'poster': drama['poster_url'] if pd.notna(drama['poster_url']) else None,
                        'rating': drama['vote_average'],
                        'user_rating': user_rating,
                        'genres': drama['genres']
                    })
            
            cols = st.columns(4)
            for idx, drama in enumerate(watched_dramas):
                with cols[idx % 4]:
                    if drama['poster']:
                        st.image(drama['poster'], use_container_width=True)
                    else:
                        st.markdown(f'<div style="background: #FFB8C6; height: 250px; border-radius: 12px;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="padding: 0.5rem 0;">
                        <div style="font-weight: 600;">{drama['title'][:35]}</div>
                        <div style="color: #FFB800; font-size: 0.8rem;">{get_star_display(drama['rating'])} {drama['rating']:.1f}</div>
                        <div style="color: #7BC5AE; font-size: 0.75rem;">Your rating: {get_star_display(drama['user_rating'])} {drama['user_rating']:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("Remove", key=f"remove_{drama['id']}"):
                        remove_from_watched(drama['id'])
                        st.rerun()
            
            if st.button("Clear All History", use_container_width=True):
                conn = sqlite3.connect('user_data.db')
                c = conn.cursor()
                c.execute('DELETE FROM watched')
                conn.commit()
                conn.close()
                st.rerun()
        else:
            st.info("Your watch history is empty.")
        st.markdown("---")

    # ========== RECOMMENDATIONS ==========
    if not st.session_state.show_rating_dialog:
        watched_list = get_watched_list()
        recommendations = get_recommendations(
            df, similarity, watched_list,
            mood_filter=st.session_state.mood_filter if st.session_state.mood_filter != "Any" else None,
            genre_filter=st.session_state.genre_filter if st.session_state.genre_filter != "Any" else None,
            cast_filter=st.session_state.cast_filter if st.session_state.cast_filter != "Any" else None,
            status_filter=st.session_state.status_filter if st.session_state.status_filter != "All" else None,
            min_rating=st.session_state.min_rating,
            n=20
        )

        if recommendations:
            st.markdown(f"### Recommendations")
            st.caption(f"{len(recommendations)} dramas found")
            
            cols = st.columns(4)
            for idx, drama in enumerate(recommendations):
                with cols[idx % 4]:
                    with st.container():
                        if drama['poster']:
                            st.image(drama['poster'], use_container_width=True)
                        else:
                            st.markdown(f'<div style="background: #FFB8C6; height: 250px; border-radius: 12px;"></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div style="padding: 0.5rem 0;">
                            <div style="font-weight: 600; font-size: 0.95rem;">{drama['title'][:35]}</div>
                            <div style="color: #FFB800; font-size: 0.8rem;">{get_star_display(drama['rating'])} {drama['rating']:.1f}</div>
                            <div style="color: #5C3D45; font-size: 0.7rem;">{drama['genres'][:35]}</div>
                            <div style="color: #5C3D45; font-size: 0.65rem;">Cast: {drama['cast'][:50]}...</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("Details", key=f"detail_{drama['id']}", use_container_width=True):
                                st.session_state.view_detail = True
                                st.session_state.selected_drama_id = drama['id']
                                st.rerun()
                        with col_btn2:
                            if is_watched(drama['id']):
                                st.markdown('<div style="background: #E8F5F0; color: #7BC5AE; text-align: center; padding: 0.3rem; border-radius: 8px; font-size: 0.7rem;">Watched</div>', unsafe_allow_html=True)
                            else:
                                if st.button("Rate", key=f"rate_{drama['id']}", use_container_width=True):
                                    st.session_state.show_rating_dialog = True
                                    st.session_state.current_rating_drama = drama
                                    st.session_state.temp_rating = 8.0
                                    st.rerun()
        else:
            st.info("No recommendations found. Try adjusting your filters.")

    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: #5C3D45; font-size: 0.7rem;">
        Dorabola — Your personal K-drama companion
    </div>
    """, unsafe_allow_html=True)