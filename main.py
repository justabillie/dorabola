import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image, ImageTk
import requests
from io import BytesIO
import threading

# Load data
df = pd.read_csv('dramas.csv')
df['id'] = df['id'].astype(int)
df = df.drop_duplicates(subset=['title'], keep='first')

# Pre-validate cast members - ONLY those that actually have matching dramas
print("Validating cast members...")
VALID_CAST_MEMBERS = ["Any"]
all_cast = set()

for cast in df['cast'].dropna():
    for actor in str(cast).split(','):
        actor = actor.strip()
        if actor and len(actor) > 2:
            all_cast.add(actor)

print(f"Total unique cast names: {len(all_cast)}")

# Test each actor
for actor in sorted(list(all_cast)):
    try:
        matches = df[df['cast'].str.contains(actor, na=False, case=False, regex=False)]
        if len(matches) > 0:
            VALID_CAST_MEMBERS.append(actor)
        else:
            print(f"Skipping '{actor}' - no dramas found")
    except:
        pass

print(f"Valid cast members: {len(VALID_CAST_MEMBERS)-1}")

class DorabolaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dorabola")
        self.root.geometry("1200x800")
        self.root.minsize(600, 500)
        self.root.configure(bg='#FFD6E0')
        
        # Image cache
        self.image_cache = {}
        
        # Current view
        self.current_view = "home"
        
        # Resize flag
        self.resize_timer = None
        
        # Card size variables
        self.card_width = 255
        self.card_height = 420
        self.poster_size = (240, 260)
        self.columns = 6
        
        # Create UI
        self.create_header()
        self.create_filter_bar()
        self.create_content_area()
        
        # Bind resize event
        self.root.bind('<Configure>', self.on_window_resize)
        
        # Load home view
        self.show_home()
    
    def on_window_resize(self, event):
        if event.widget == self.root:
            if self.resize_timer:
                self.root.after_cancel(self.resize_timer)
            self.resize_timer = self.root.after(200, self._refresh_layout)
    
    def _refresh_layout(self):
        window_width = self.root.winfo_width()
        
        if window_width < 845:
            new_columns = 2
        elif window_width < 1130:
            new_columns = 3
        elif window_width < 1415:
            new_columns = 4
        elif window_width < 1700:
            new_columns = 5
        else:
            new_columns = 6
        
        if new_columns != self.columns:
            self.columns = new_columns
            
            if self.current_view == "home":
                self.show_home()
            elif self.current_view == "watched":
                self.show_watched()
    
    def create_header(self):
        self.header = tk.Frame(self.root, bg='#FFD6E0', height=70)
        self.header.pack(fill='x')
        self.header.pack_propagate(False)
        
        title = tk.Label(self.header, text="Dorabola", font=('Arial', 24, 'bold'), 
                        bg='#FFD6E0', fg='#2D1B1F')
        title.place(relx=0.5, rely=0.4, anchor='center')
        
        subtitle = tk.Label(self.header, text="Discover your next favorite K-drama", 
                           font=('Arial', 10), bg='#FFD6E0', fg='#5C3D45')
        subtitle.place(relx=0.5, rely=0.75, anchor='center')
    
    def create_filter_bar(self):
        self.filter_frame = tk.Frame(self.root, bg='#FFD6E0', height=80)
        self.filter_frame.pack(fill='x', pady=5, padx=10)
        self.filter_frame.pack_propagate(False)
        
        for i in range(3):
            self.filter_frame.grid_columnconfigure(i, weight=1)
        
        # Genre filter
        tk.Label(self.filter_frame, text="GENRE", font=('Arial', 9, 'bold'), bg='#FFD6E0', fg='#5C3D45').grid(row=0, column=0, padx=5, sticky='w')
        self.genre_var = tk.StringVar(value="Any")
        genres = ["Any"] + sorted(set([g for genres in df['genres'].dropna() for g in str(genres).split(',')]))[:15]
        genre_dropdown = ttk.Combobox(self.filter_frame, textvariable=self.genre_var, values=genres, font=('Arial', 9))
        genre_dropdown.grid(row=1, column=0, padx=5, pady=2, sticky='ew')
        genre_dropdown.bind('<<ComboboxSelected>>', lambda e: None)
        
        # Rating filter
        tk.Label(self.filter_frame, text="MIN RATING", font=('Arial', 9, 'bold'), bg='#FFD6E0', fg='#5C3D45').grid(row=0, column=1, padx=5, sticky='w')
        
        rating_frame = tk.Frame(self.filter_frame, bg='#FFD6E0')
        rating_frame.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        
        self.rating_var = tk.StringVar(value="")
        
        rating_spinbox = tk.Spinbox(
            rating_frame, 
            from_=0.0, 
            to=10.0, 
            increment=0.1,
            textvariable=self.rating_var,
            font=('Arial', 9),
            width=12
        )
        rating_spinbox.pack(side='left', fill='x', expand=True)
        
        # Buttons frame
        buttons_frame = tk.Frame(self.filter_frame, bg='#FFD6E0')
        buttons_frame.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
        
        # Apply Filters button
        apply_btn = tk.Button(buttons_frame, text="Apply Filters", bg='#FF6B8A', fg='white', 
                              font=('Arial', 9), command=self.apply_filters)
        apply_btn.pack(side='left', padx=2, fill='x', expand=True)
        
        # History button
        history_btn = tk.Button(buttons_frame, text="Watched List", bg='#FF6B8A', fg='white', 
                               font=('Arial', 9), command=self.show_watched)
        history_btn.pack(side='left', padx=2, fill='x', expand=True)

    def apply_filters(self):
        self.show_home()

    def create_content_area(self):
        self.content_container = tk.Frame(self.root, bg='#FFD6E0')
        self.content_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.content_container, bg='#FFD6E0', highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        self.v_scrollbar = tk.Scrollbar(self.content_container, orient="vertical", command=self.canvas.yview)
        self.v_scrollbar.pack(side='right', fill='y')
        
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel_linux_up)
        self.canvas.bind('<Button-5>', self._on_mousewheel_linux_down)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg='#FFD6E0')
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="n")
        
        self.scrollable_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.root.bind('<MouseWheel>', self._on_mousewheel_root)
        self.root.bind('<Button-4>', self._on_mousewheel_root_up)
        self.root.bind('<Button-5>', self._on_mousewheel_root_down)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_mousewheel_linux_up(self, event):
        self.canvas.yview_scroll(-1, "units")
    
    def _on_mousewheel_linux_down(self, event):
        self.canvas.yview_scroll(1, "units")
    
    def _on_mousewheel_root(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_mousewheel_root_up(self, event):
        self.canvas.yview_scroll(-1, "units")
    
    def _on_mousewheel_root_down(self, event):
        self.canvas.yview_scroll(1, "units")
    
    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event=None):
        canvas_width = event.width
        frame_width = self.scrollable_frame.winfo_reqwidth()
        if frame_width > 0:
            x_offset = max(0, (canvas_width - frame_width) // 2)
            self.canvas.coords(self.canvas_frame, x_offset, 0)
        self.canvas.itemconfig(self.canvas_frame, width=canvas_width)
    
    def clear_content(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
    def load_image(self, url, size, card_id):
        """Load image with card ID to prevent updating stale widgets"""
        cache_key = f"{url}_{size[0]}_{size[1]}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            img = img.resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[cache_key] = photo
            return photo
        except:
            return None
    
    def create_drama_card(self, parent, drama, card_id):
        card = tk.Frame(parent, bg='white', relief='raised', bd=1)
        card.pack(side='left', padx=8, pady=5, anchor='n')
        card.config(width=self.card_width, height=self.card_height)
        card.pack_propagate(False)
        
        poster_url = drama['poster_url'] if pd.notna(drama['poster_url']) else None
        poster_container = tk.Frame(card, bg='#FFB8C6', width=self.poster_size[0], height=self.poster_size[1])
        poster_container.pack(pady=5)
        poster_container.pack_propagate(False)
        
        if poster_url:
            def load_poster():
                photo = self.load_image(poster_url, self.poster_size, card_id)
                if photo:
                    self.root.after(0, lambda: poster_label.config(image=photo) if poster_label.winfo_exists() else None)
                    self.root.after(0, lambda: setattr(poster_label, 'image', photo) if poster_label.winfo_exists() else None)
            
            poster_label = tk.Label(poster_container, bg='#FFB8C6')
            poster_label.pack(fill='both', expand=True)
            threading.Thread(target=load_poster, daemon=True).start()
        else:
            poster_label = tk.Label(poster_container, text="🎬", font=('Arial', 40), bg='#FFB8C6')
            poster_label.pack(fill='both', expand=True)
        
        title_font_size = max(9, int(11 * (self.card_width / 250)))
        tk.Label(card, text=drama['title'][:35], font=('Arial', title_font_size, 'bold'), 
                bg='white', fg='#2D1B1F', wraplength=self.card_width-20).pack(pady=3)
        
        tk.Label(card, text=f"★ {drama['vote_average']:.1f}/10", font=('Arial', title_font_size-1), 
                bg='white', fg='#FFB800').pack()
        
        tk.Label(card, text=drama['genres'][:30], font=('Arial', title_font_size-2), 
                bg='white', fg='#5C3D45', wraplength=self.card_width-20).pack()
        
        btn_frame = tk.Frame(card, bg='white')
        btn_frame.pack(pady=8)
        
        btn_width = max(6, int(self.card_width / 35))
        tk.Button(btn_frame, text="Details", bg='#FF6B8A', fg='white', width=btn_width,
                 command=lambda: self.show_detail_popup(drama)).pack(side='left', padx=2)
        tk.Button(btn_frame, text="Rate", bg='#7BC5AE', fg='white', width=btn_width,
                 command=lambda: self.rate_drama(drama)).pack(side='left', padx=2)
    
    def show_detail_popup(self, drama):
        """Show drama details in a popup window"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Dorabola - {drama['title']}")
        detail_window.geometry("700x500")
        detail_window.configure(bg='white')
        detail_window.transient(self.root)
        detail_window.grab_set()
        
        # Center the window
        detail_window.update_idletasks()
        x = (detail_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (detail_window.winfo_screenheight() // 2) - (500 // 2)
        detail_window.geometry(f"700x500+{x}+{y}")
        
        # Main content frame
        main_frame = tk.Frame(detail_window, bg='white')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Poster
        poster_url = drama['poster_url'] if pd.notna(drama['poster_url']) else None
        poster_container = tk.Frame(main_frame, bg='#FFB8C6', width=180, height=260)
        poster_container.pack(side='left', padx=10)
        poster_container.pack_propagate(False)
        
        if poster_url:
            def load_detail_poster():
                try:
                    response = requests.get(poster_url, timeout=5)
                    img = Image.open(BytesIO(response.content))
                    img = img.resize((180, 260), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    detail_window.after(0, lambda: poster_label.config(image=photo))
                    detail_window.after(0, lambda: setattr(poster_label, 'image', photo))
                except:
                    pass
            
            poster_label = tk.Label(poster_container, bg='#FFB8C6')
            poster_label.pack(fill='both', expand=True)
            threading.Thread(target=load_detail_poster, daemon=True).start()
        else:
            poster_label = tk.Label(poster_container, text="🎬", font=('Arial', 50), bg='#FFB8C6')
            poster_label.pack(fill='both', expand=True)
        
        # Details frame
        details_frame = tk.Frame(main_frame, bg='white')
        details_frame.pack(side='left', fill='both', expand=True, padx=20)
        
        # Title
        tk.Label(details_frame, text=drama['title'], font=('Arial', 18, 'bold'), 
                bg='white', fg='#2D1B1F', wraplength=400).pack(anchor='w')
        
        # Rating
        tk.Label(details_frame, text=f"★ {drama['vote_average']:.1f}/10", font=('Arial', 12), 
                bg='white', fg='#FFB800').pack(anchor='w', pady=5)
        
        # Year and Genres
        info_frame = tk.Frame(details_frame, bg='white')
        info_frame.pack(anchor='w', pady=5)
        
        tk.Label(info_frame, text=f"Year: {drama['year']}", font=('Arial', 10), 
                bg='white', fg='#5C3D45').pack(side='left', padx=5)
        tk.Label(info_frame, text=f"Genres: {drama['genres'][:50]}", font=('Arial', 10), 
                bg='white', fg='#5C3D45').pack(side='left', padx=5)
        
        # Synopsis
        tk.Label(details_frame, text="Synopsis", font=('Arial', 12, 'bold'), 
                bg='white', fg='#2D1B1F').pack(anchor='w', pady=(15, 5))
        
        synopsis_text = tk.Text(details_frame, height=6, wrap='word', font=('Arial', 9), 
                                bg='#F8F8F8', fg='#2D1B1F', relief='flat')
        overview_text = drama['overview'][:500] + "..." if len(str(drama['overview'])) > 500 else drama['overview']
        synopsis_text.insert('1.0', overview_text)
        synopsis_text.config(state='disabled')
        synopsis_text.pack(fill='x', pady=5)
        
        # Cast
        tk.Label(details_frame, text="Cast", font=('Arial', 12, 'bold'), 
                bg='white', fg='#2D1B1F').pack(anchor='w', pady=(10, 5))
        
        cast_text = tk.Text(details_frame, height=3, wrap='word', font=('Arial', 9), 
                            bg='#F8F8F8', fg='#5C3D45', relief='flat')
        cast_text.insert('1.0', drama['cast'][:300])
        cast_text.config(state='disabled')
        cast_text.pack(fill='x')
        
        # Mark as Watched button
        if not is_watched(drama['id']):
            button_frame = tk.Frame(details_frame, bg='white')
            button_frame.pack(fill='x', pady=15)
            
            rate_btn = tk.Button(button_frame, text="Mark as Watched", bg='#FF6B8A', fg='white', 
                                font=('Arial', 11), command=lambda: [detail_window.destroy(), self.rate_drama(drama)])
            rate_btn.pack()
        else:
            tk.Label(details_frame, text="✓ Already in your watched list", font=('Arial', 10), 
                    bg='white', fg='#7BC5AE').pack(pady=15)
    
    def get_recommendations(self):
        """Get recommendations based on user's watch history, filters, and randomize order"""
        import random
        
        watched = get_watched_list()
        
        # Start with all dramas
        filtered = df.copy()
        
        # Exclude already watched
        watched_ids = [d_id for d_id, _ in watched]
        filtered = filtered[~filtered['id'].isin(watched_ids)]
        
        # Apply genre filter from UI
        if hasattr(self, 'genre_var') and self.genre_var.get() != "Any":
            filtered = filtered[filtered['genres'].str.contains(self.genre_var.get(), na=False, case=False)]
        
        # Apply rating filter from UI
        if hasattr(self, 'rating_var') and self.rating_var.get() != "":
            try:
                min_rating = float(self.rating_var.get())
                filtered = filtered[filtered['vote_average'] >= min_rating]
            except ValueError:
                pass
        
        # Randomize the order of results
        if not filtered.empty:
            filtered = filtered.sample(frac=1)
        
        return filtered.head(100)

    def show_home(self):
        self.current_view = "home"
        self.clear_content()
        
        # Get recommendations with all filters applied
        filtered = self.get_recommendations()
        
        if len(filtered) == 0:
            tk.Label(self.scrollable_frame, text="No dramas found. Try different filters.", 
                    font=('Arial', 14), bg='#FFD6E0', fg='#5C3D45').pack(pady=50)
        else:
            grid_container = tk.Frame(self.scrollable_frame, bg='#FFD6E0')
            grid_container.pack(expand=True)
            
            row_frame = None
            for i, (_, drama) in enumerate(filtered.iterrows()):
                if i % self.columns == 0:
                    row_frame = tk.Frame(grid_container, bg='#FFD6E0')
                    row_frame.pack(pady=5, anchor='center')
                self.create_drama_card(row_frame, drama, i)
        
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def rate_drama(self, drama):
        rating_window = tk.Toplevel(self.root)
        rating_window.title("Rate Drama")
        rating_window.geometry("450x350")
        rating_window.configure(bg='white')
        rating_window.transient(self.root)
        rating_window.grab_set()
        
        rating_window.update_idletasks()
        x = (rating_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (rating_window.winfo_screenheight() // 2) - (350 // 2)
        rating_window.geometry(f"450x350+{x}+{y}")
        
        tk.Label(rating_window, text=f"Rate: {drama['title']}", font=('Arial', 12, 'bold'), 
                bg='white', wraplength=400).pack(pady=15)
        tk.Label(rating_window, text="Your rating (0-10, decimal allowed)", bg='white').pack()
        
        rating_var = tk.DoubleVar(value=8.0)
        
        rating_spinbox = tk.Spinbox(
            rating_window,
            from_=0.0,
            to=10.0,
            increment=0.5,
            textvariable=rating_var,
            font=('Arial', 14),
            width=10,
            justify='center'
        )
        rating_spinbox.pack(pady=10)
        
        star_frame = tk.Frame(rating_window, bg='white')
        star_frame.pack(pady=10)
        
        star_labels = []
        
        def update_stars_from_rating(value):
            full_stars = int(value)
            half_star = 1 if (value - full_stars) >= 0.5 else 0
            for i, star in enumerate(star_labels, 1):
                if i <= full_stars:
                    star.config(text="★", fg="#FFB800")
                elif i == full_stars + 1 and half_star:
                    star.config(text="⯨", fg="#FFB800")
                else:
                    star.config(text="☆", fg="#CCCCCC")
        
        def update_from_spinbox(event=None):
            try:
                value = rating_var.get()
                update_stars_from_rating(value)
            except:
                pass
        
        for i in range(1, 11):
            star = tk.Label(star_frame, text="★" if i <= 8 else "☆", font=('Arial', 22), 
                           bg='white', fg="#FFB800" if i <= 8 else "#CCCCCC", cursor="hand2")
            star.pack(side='left', padx=2)
            
            def star_click(idx):
                rating_var.set(float(idx))
                update_from_spinbox()
            
            star.bind('<Button-1>', lambda e, idx=i: star_click(idx))
            star_labels.append(star)
        
        rating_spinbox.bind('<KeyRelease>', update_from_spinbox)
        rating_spinbox.bind('<<Increment>>', update_from_spinbox)
        rating_spinbox.bind('<<Decrement>>', update_from_spinbox)
        
        rating_display = tk.Label(rating_window, text=f"Rating: 8.0 / 10", font=('Arial', 12), bg='white')
        rating_display.pack(pady=5)
        
        def update_display(event=None):
            try:
                val = rating_var.get()
                rating_display.config(text=f"Rating: {val:.1f} / 10")
                update_stars_from_rating(val)
            except:
                pass
        
        rating_spinbox.bind('<KeyRelease>', update_display)
        rating_spinbox.bind('<<Increment>>', update_display)
        rating_spinbox.bind('<<Decrement>>', update_display)
        update_display()
        
        def save():
            rating = rating_var.get()
            add_to_watched(drama['id'], drama['title'], rating)
            rating_window.destroy()
            # Force a complete refresh of recommendations
            self.show_home()
            messagebox.showinfo("Success", f"Added {drama['title']} to your watched list with rating {rating:.1f}/10!\nRecommendations have been updated!")
        
        tk.Button(rating_window, text="Save Rating", bg='#FF6B8A', fg='white', command=save, 
                 width=20, height=1, font=('Arial', 11)).pack(pady=20)

    def show_watched(self):
        self.current_view = "watched"
        self.clear_content()
        
        watched_container = tk.Frame(self.scrollable_frame, bg='#FFD6E0')
        watched_container.pack(expand=True, fill='both')
        
        back_btn = tk.Button(watched_container, text="← Back to Home", bg='#FF6B8A', fg='white', 
                            font=('Arial', 10), command=self.show_home)
        back_btn.pack(anchor='w', pady=5)
        
        tk.Label(watched_container, text="Your Watch History", font=('Arial', 18, 'bold'), 
                bg='#FFD6E0', fg='#2D1B1F').pack(pady=10)
        
        conn = sqlite3.connect('user_data.db')
        c = conn.cursor()
        c.execute('SELECT drama_id, drama_title, rating FROM watched ORDER BY date_watched DESC')
        watched = c.fetchall()
        conn.close()
        
        if not watched:
            tk.Label(watched_container, text="No dramas in your watched list", 
                    bg='#FFD6E0', fg='#5C3D45', font=('Arial', 12)).pack(pady=50)
        else:
            grid_container = tk.Frame(watched_container, bg='#FFD6E0')
            grid_container.pack(expand=True)
            
            row_frame = None
            for i, (drama_id, title, rating) in enumerate(watched):
                if i % self.columns == 0:
                    row_frame = tk.Frame(grid_container, bg='#FFD6E0')
                    row_frame.pack(pady=5, anchor='center')
                
                drama = df[df['id'] == drama_id].iloc[0] if len(df[df['id'] == drama_id]) > 0 else None
                if drama is not None:
                    self.create_drama_card(row_frame, drama, i)
        
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

def is_watched(drama_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM watched WHERE drama_id = ?', (drama_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_watched_list():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('SELECT drama_id, rating FROM watched')
    watched = c.fetchall()
    conn.close()
    return watched

def add_to_watched(drama_id, title, rating):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watched (drama_id INTEGER PRIMARY KEY, drama_title TEXT, rating REAL, date_watched TEXT)')
    c.execute('INSERT OR REPLACE INTO watched VALUES (?, ?, ?, ?)', (drama_id, title, rating, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk
    except ImportError:
        import subprocess
        subprocess.check_call(['pip', 'install', 'Pillow'])
        from PIL import Image, ImageTk
    
    root = tk.Tk()
    app = DorabolaApp(root)
    root.mainloop()