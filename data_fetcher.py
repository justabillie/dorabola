# data_fetcher.py - Fetches ALL available K-dramas
import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = 'https://api.themoviedb.org/3'
IMAGE_BASE = 'https://image.tmdb.org/t/p/w200'

def fetch_all_kdramas():
    """Fetch ALL Korean dramas from TMDB (up to 500+ dramas)"""
    
    print("🐉 Fetching ALL K-dramas...")
    all_dramas = []
    seen_titles = set()
    
    # Increase max pages - TMDB allows up to 500 pages but realistically 50-100 pages of Korean dramas
    max_pages = 500  # This will fetch ~2000 dramas (20 per page)
    
    for page in range(1, max_pages + 1):
        print(f"📥 Fetching page {page}/{max_pages}...")
        
        url = f"{BASE_URL}/discover/tv"
        params = {
            'api_key': API_KEY,
            'with_original_language': 'ko',
            'sort_by': 'popularity.desc',
            'page': page,
            'vote_count.gte': 10  # Lower threshold to get more shows (was 50)
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'results' not in data or not data['results']:
                print(f"⚠️ No more results at page {page}")
                break
                
            print(f"   Found {len(data['results'])} shows on this page")
            
            for show in data['results']:
                title = show.get('name', '')
                
                # Skip duplicates
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                print(f"   📺 Processing: {title}")
                
                # Get detailed info with cast
                detail_url = f"{BASE_URL}/tv/{show['id']}"
                detail_params = {
                    'api_key': API_KEY,
                    'append_to_response': 'credits'
                }
                
                try:
                    detail_response = requests.get(detail_url, params=detail_params)
                    detail_data = detail_response.json()
                    
                    # Get genres
                    genres = [genre['name'] for genre in detail_data.get('genres', [])]
                    
                    # Get cast - REAL ACTOR NAMES
                    cast_list = []
                    if 'credits' in detail_data and 'cast' in detail_data['credits']:
                        # Get top 10 cast members for more data
                        for actor in detail_data['credits']['cast'][:10]:
                            cast_list.append(actor['name'])
                    
                    cast_string = ', '.join(cast_list) if cast_list else 'Cast information not available'
                    
                    # Get all available mood tags
                    mood_tags = []
                    if any(g in ['Romance', 'Comedy'] for g in genres):
                        mood_tags.append('Romantic')
                    if any(g in ['Thriller', 'Crime', 'Mystery'] for g in genres):
                        mood_tags.append('Thrilling')
                    if any(g in ['Comedy'] for g in genres):
                        mood_tags.append('Heartwarming')
                    if any(g in ['Drama', 'Melodrama'] for g in genres):
                        mood_tags.append('Emotional')
                    if any(g in ['Action', 'Adventure'] for g in genres):
                        mood_tags.append('Exciting')
                    if 'Fantasy' in genres:
                        mood_tags.append('Magical')
                    
                    # Add more mood tags based on keywords in overview
                    overview = show.get('overview', '').lower()
                    if 'revenge' in overview:
                        mood_tags.append('Revenge')
                    if 'friendship' in overview:
                        mood_tags.append('Friendship')
                    if 'family' in overview:
                        mood_tags.append('Family')
                    if 'healing' in overview:
                        mood_tags.append('Healing')
                    
                    # Determine year and status
                    first_air_date = show.get('first_air_date', '')
                    year = first_air_date[:4] if first_air_date else ''
                    
                    # Get last air date for ongoing check
                    last_air_date = detail_data.get('last_air_date', '')
                    status = detail_data.get('status', 'Unknown')
                    
                    drama = {
                        'id': show['id'],
                        'title': title,
                        'overview': show.get('overview', 'No description available'),
                        'first_air_date': first_air_date,
                        'last_air_date': last_air_date,
                        'status': status,
                        'vote_average': show.get('vote_average', 0),
                        'vote_count': show.get('vote_count', 0),
                        'popularity': show.get('popularity', 0),
                        'genres': ', '.join(genres) if genres else 'Various',
                        'cast': cast_string,
                        'mood_tags': ', '.join(set(mood_tags)) if mood_tags else 'Various',
                        'poster_url': f"{IMAGE_BASE}{show['poster_path']}" if show.get('poster_path') else None,
                        'year': year,
                        'number_of_episodes': detail_data.get('number_of_episodes', 0),
                        'number_of_seasons': detail_data.get('number_of_seasons', 0)
                    }
                    
                    all_dramas.append(drama)
                    print(f"      ✅ Added - Rating: {drama['vote_average']:.1f}/10, Cast: {len(cast_list)} actors")
                    time.sleep(0.1)  # Be nice to API (100ms delay)
                    
                except Exception as e:
                    print(f"      ⚠️ Error fetching details: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            continue
        
        # Small delay between pages
        time.sleep(0.2)
    
    # Create DataFrame and save
    df = pd.DataFrame(all_dramas)
    
    # Remove any exact duplicates by title
    df = df.drop_duplicates(subset=['title'], keep='first')
    
    # Sort by popularity/vote count
    df = df.sort_values(by='vote_count', ascending=False)
    
    df.to_csv('dramas.csv', index=False)
    print(f"\n✅ Successfully saved {len(df)} unique K-dramas to dramas.csv!")
    
    # Print statistics
    print("\n📊 STATISTICS:")
    print(f"   Total dramas: {len(df)}")
    print(f"   Average rating: {df['vote_average'].mean():.1f}/10")
    print(f"   Years range: {df['year'].min()} - {df['year'].max()}")
    print(f"   Most common genres: {df['genres'].value_counts().head(5).to_dict()}")
    
    # Show sample
    print("\n🎬 SAMPLE DRAMAS:")
    for i in range(min(5, len(df))):
        print(f"   {i+1}. {df.iloc[i]['title']} (★ {df.iloc[i]['vote_average']:.1f})")
    
    return df

def fetch_kdramas_by_year():
    """Alternative: Fetch dramas year by year for more complete data"""
    all_dramas = []
    current_year = datetime.now().year
    
    for year in range(2000, current_year + 1):
        print(f"Fetching dramas from {year}...")
        
        for page in range(1, 6):  # 5 pages per year
            url = f"{BASE_URL}/discover/tv"
            params = {
                'api_key': API_KEY,
                'with_original_language': 'ko',
                'first_air_date_year': year,
                'sort_by': 'popularity.desc',
                'page': page
            }
            
            # Same processing as above...
            # (You can copy the processing logic from fetch_all_kdramas)
    
    return pd.DataFrame(all_dramas)

if __name__ == "__main__":
    if not API_KEY:
        print("❌ No API key found!")
        print("Create .env file with: TMDB_API_KEY=your_key_here")
    else:
        print("🎬 Starting K-drama data collection...")
        print("This may take 5-10 minutes depending on your internet speed.\n")
        
        # Fetch all dramas
        df = fetch_all_kdramas()
        
        print(f"\n✨ Done! You now have {len(df)} K-dramas in your database.")
        print("Run 'streamlit run app.py' to see them in your recommender!")