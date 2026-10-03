# theme_switcher.py - Helper to change themes
import re

def change_theme(theme_name):
    """Switch between predefined themes"""
    
    themes = {
        "creamy": {
            "bg_primary": "linear-gradient(135deg, #FFF9F5 0%, #FFF5EE 100%)",
            "text_primary": "#8B5E3C",
            "accent": "linear-gradient(135deg, #D4A574 0%, #C4956A 100%)"
        },
        "minty": {
            "bg_primary": "linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%)",
            "text_primary": "#2E7D32",
            "accent": "linear-gradient(135deg, #81C784 0%, #66BB6A 100%)"
        },
        "lavender": {
            "bg_primary": "linear-gradient(135deg, #F3E5F5 0%, #EDE7F6 100%)",
            "text_primary": "#6A1B9A",
            "accent": "linear-gradient(135deg, #CE93D8 0%, #BA68C8 100%)"
        },
        "peach": {
            "bg_primary": "linear-gradient(135deg, #FBE9E7 0%, #FFCCBC 100%)",
            "text_primary": "#BF360C",
            "accent": "linear-gradient(135deg, #FFAB91 0%, #FF8A65 100%)"
        }
    }
    
    if theme_name in themes:
        theme = themes[theme_name]
        
        with open('styles.css', 'r') as f:
            css = f.read()
        
        # Replace color variables
        css = re.sub(r'--bg-primary: [^;]+;', f'--bg-primary: {theme["bg_primary"]};', css)
        css = re.sub(r'--text-primary: [^;]+;', f'--text-primary: {theme["text_primary"]};', css)
        css = re.sub(r'--accent-primary: [^;]+;', f'--accent-primary: {theme["accent"]};', css)
        
        with open('styles.css', 'w') as f:
            f.write(css)
        
        print(f"✅ Theme changed to {theme_name}!")
        print("🔄 Refresh your browser to see the change")
    else:
        print(f"Themes available: {', '.join(themes.keys())}")

if __name__ == "__main__":
    print("🎨 Dorabola Theme Switcher")
    print("Available themes: creamy, minty, lavender, peach")
    theme = input("Enter theme name: ").strip().lower()
    change_theme(theme)