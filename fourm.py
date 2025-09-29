import web
import sqlite3
import hashlib
import os
import time
from datetime import datetime
import re

# URLs routing
urls = (
    '/', 'Index',
    '/register', 'Register',
    '/login', 'Login',
    '/logout', 'Logout',
    '/post', 'CreatePost',
    '/post/(\d+)', 'ViewPost',
    '/edit/(\d+)', 'EditPost',
    '/delete/(\d+)', 'DeletePost',
    '/comment/(\d+)', 'AddComment',
    '/profile', 'UserProfile',
    '/search', 'Search',
    '/admin', 'AdminPanel',
    '/category/(\d+)', 'CategoryPosts'
)

# Web.py application
app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'))

# Database setup
def setup_database():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bio TEXT DEFAULT ''
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT DEFAULT '#667eea'
        )
    ''')
    
    # Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views INTEGER DEFAULT 0,
            is_pinned BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parent_id INTEGER DEFAULT NULL,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert default categories
    cursor.execute('''
        INSERT OR IGNORE INTO categories (id, name, description, color) VALUES
        (1, 'General', 'General discussions', '#667eea'),
        (2, 'Questions', 'Ask questions here', '#4CAF50'),
        (3, 'Suggestions', 'Share your ideas', '#FF9800'),
        (4, 'Announcements', 'Important announcements', '#F44336')
    ''')
    
    # Create admin user if not exists
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, role) 
        VALUES ('admin', 'admin@forum.com', ?, 'admin')
    ''', (admin_hash,))
    
    conn.commit()
    conn.close()

# Initialize database
setup_database()

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_id():
    return session.get('user_id', None)

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') == 'admin'

def get_categories():
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_user(user_id):
    conn = sqlite3.connect('forum.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Base template with common layout
def base_template(title, content, show_header=True):
    user_info = ""
    if is_logged_in():
        user = get_user(get_user_id())
        user_info = f"""
        <div class="user-menu">
            <span class="avatar-icon">👤</span>
            <span>Welcome, {user[1]}!</span>
            <div class="dropdown">
                <a href="/profile">👤 Profile</a>
                {f'<a href="/admin">⚙️ Admin</a>' if is_admin() else ''}
                <a href="/logout">🚪 Logout</a>
            </div>
        </div>
        """
    else:
        user_info = """
        <div class="auth-buttons">
            <a href="/login" class="btn btn-outline">Login</a>
            <a href="/register" class="btn btn-primary">Register</a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Advanced Forum</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            .header {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 20px 30px;
                margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .logo {{
                font-size: 2em;
                font-weight: bold;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .nav-links {{
                display: flex;
                gap: 20px;
                align-items: center;
            }}
            
            .btn {{
                padding: 10px 20px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                transition: all 0.3s ease;
                display: inline-block;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .btn-outline {{
                border: 2px solid #667eea;
                color: #667eea;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .user-menu {{
                position: relative;
                display: flex;
                align-items: center;
                gap: 10px;
                cursor: pointer;
            }}
            
            .avatar-icon {{
                font-size: 1.5em;
            }}
            
            .dropdown {{
                position: absolute;
                top: 100%;
                right: 0;
                background: white;
                border-radius: 10px;
                padding: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: none;
                min-width: 150px;
                z-index: 1000;
            }}
            
            .user-menu:hover .dropdown {{
                display: block;
            }}
            
            .dropdown a {{
                display: block;
                padding: 8px 12px;
                color: #333;
                text-decoration: none;
                border-radius: 5px;
            }}
            
            .dropdown a:hover {{
                background: #f8f9fa;
            }}
            
            .main-content {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .alert {{
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            
            .alert-success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .alert-error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {f'<div class="header"><div class="logo">💬 Advanced Forum</div><div class="nav-links">{user_info}</div></div>' if show_header else ''}
            <div class="main-content">
                {content}
            </div>
        </div>
    </body>
    </html>
    """

class Index:
    def GET(self):
        page = web.input(page=1).page
        page = int(page)
        per_page = 10
        offset = (page - 1) * per_page
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Get total posts count
        cursor.execute('SELECT COUNT(*) FROM posts')
        total_posts = cursor.fetchone()[0]
        
        # Get posts with user info
        cursor.execute('''
            SELECT p.*, u.username, c.name as category_name, c.color as category_color,
                   (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN categories c ON p.category_id = c.id
            ORDER BY p.is_pinned DESC, p.created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        posts = cursor.fetchall()
        
        categories = get_categories()
        conn.close()
        
        # Render posts
        posts_html = ""
        for post in posts:
            post_id, user_id, category_id, title, content, created_at, updated_at, views, is_pinned, username, category_name, category_color, comment_count = post
            
            created_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            time_str = created_time.strftime('%B %d, %Y at %I:%M %p')
            
            posts_html += f"""
            <div class="post-card {'pinned' if is_pinned else ''}">
                <div class="post-header">
                    <span class="category-tag" style="background: {category_color}">{category_name}</span>
                    {'<span class="pinned-badge">📌 Pinned</span>' if is_pinned else ''}
                    <h3><a href="/post/{post_id}">{web.websafe(title)}</a></h3>
                </div>
                <div class="post-meta">
                    <span class="user-info">👤 {web.websafe(username)}</span>
                    <span class="time">📅 {time_str}</span>
                    <span class="views">👁️ {views} views</span>
                    <span class="comments">💬 {comment_count} comments</span>
                </div>
                <div class="post-preview">{web.websafe(content)[:200]}...</div>
                <div class="post-actions">
                    <a href="/post/{post_id}" class="btn-read">Read More</a>
                    {f'<a href="/edit/{post_id}" class="btn-edit">Edit</a>' if is_logged_in() and (get_user_id() == user_id or is_admin()) else ''}
                </div>
            </div>
            """
        
        # Pagination
        total_pages = (total_posts + per_page - 1) // per_page
        pagination = ""
        if total_pages > 1:
            pagination = '<div class="pagination">'
            if page > 1:
                pagination += f'<a href="/?page={page-1}">← Previous</a>'
            for p in range(max(1, page-2), min(total_pages+1, page+3)):
                if p == page:
                    pagination += f'<span class="current">{p}</span>'
                else:
                    pagination += f'<a href="/?page={p}">{p}</a>'
            if page < total_pages:
                pagination += f'<a href="/?page={page+1}">Next →</a>'
            pagination += '</div>'
        
        content = f"""
        <style>
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            
            .categories-sidebar {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-bottom: 30px;
            }}
            
            .category-item {{
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                color: white;
                text-decoration: none;
                font-weight: bold;
            }}
            
            .post-card {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                border-left: 4px solid #667eea;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .post-card.pinned {{
                border-left-color: #FFD700;
                background: #fff9e6;
            }}
            
            .pinned-badge {{
                background: #FFD700;
                color: #333;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 0.8em;
                margin-left: 10px;
            }}
            
            .category-tag {{
                color: white;
                padding: 4px 12px;
                border-radius: 15px;
                font-size: 0.8em;
                font-weight: bold;
            }}
            
            .post-header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }}
            
            .post-header h3 {{
                margin: 0;
                flex-grow: 1;
            }}
            
            .post-header h3 a {{
                color: #333;
                text-decoration: none;
            }}
            
            .post-meta {{
                display: flex;
                gap: 15px;
                margin-bottom: 10px;
                font-size: 0.9em;
                color: #666;
                flex-wrap: wrap;
            }}
            
            .post-preview {{
                color: #444;
                line-height: 1.5;
                margin-bottom: 15px;
            }}
            
            .post-actions {{
                display: flex;
                gap: 10px;
            }}
            
            .btn-read, .btn-edit {{
                padding: 8px 16px;
                border-radius: 15px;
                text-decoration: none;
                font-size: 0.9em;
            }}
            
            .btn-read {{
                background: #667eea;
                color: white;
            }}
            
            .btn-edit {{
                background: #28a745;
                color: white;
            }}
            
            .pagination {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 30px;
            }}
            
            .pagination a, .pagination span {{
                padding: 8px 16px;
                border-radius: 5px;
                text-decoration: none;
            }}
            
            .pagination a {{
                background: #f8f9fa;
                color: #667eea;
            }}
            
            .pagination .current {{
                background: #667eea;
                color: white;
            }}
            
            .create-post-btn {{
                display: block;
                width: 200px;
                margin: 20px auto;
                text-align: center;
            }}
        </style>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📊 Total Posts</h3>
                <p>{total_posts}</p>
            </div>
            <div class="stat-card">
                <h3>👥 Active Users</h3>
                <p>{len([post for post in posts])}</p>
            </div>
            <div class="stat-card">
                <h3>💬 Total Comments</h3>
                <p>{sum(post[12] for post in posts)}</p>
            </div>
        </div>
        
        <div class="categories-sidebar">
            {"".join([f'<a href="/category/{cat[0]}" class="category-item" style="background: {cat[3]}">{cat[1]}</a>' for cat in categories])}
        </div>
        
        {f'<a href="/post" class="btn btn-primary create-post-btn"><i class="fas fa-plus"></i> Create New Post</a>' if is_logged_in() else ''}
        
        <div class="posts-list">
            {posts_html if posts else '<div class="no-posts">No posts yet. Be the first to share something! 🚀</div>'}
        </div>
        
        {pagination}
        """
        
        return base_template("Home", content)

class Register:
    def GET(self):
        if is_logged_in():
            raise web.seeother('/')
        
        content = """
        <style>
            .auth-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            
            .auth-form {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #333;
            }
            
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s ease;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .auth-header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .auth-header h2 {
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
        </style>
        
        <div class="auth-container">
            <div class="auth-form">
                <div class="auth-header">
                    <h2>👤 Create Account</h2>
                    <p>Join our community today!</p>
                </div>
                
                <form method="post">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required maxlength="50">
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required minlength="6">
                    </div>
                    
                    <div class="form-group">
                        <label for="confirm_password">Confirm Password:</label>
                        <input type="password" id="confirm_password" name="confirm_password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary" style="width: 100%">Register</button>
                </form>
                
                <p style="text-align: center; margin-top: 20px;">
                    Already have an account? <a href="/login">Login here</a>
                </p>
            </div>
        </div>
        """
        return base_template("Register", content, False)
    
    def POST(self):
        form = web.input()
        username = form.username.strip()
        email = form.email.strip()
        password = form.password
        confirm_password = form.confirm_password
        
        if password != confirm_password:
            return base_template("Register", '<div class="alert alert-error">Passwords do not match!</div>', False)
        
        if len(password) < 6:
            return base_template("Register", '<div class="alert alert-error">Password must be at least 6 characters!</div>', False)
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        try:
            password_hash = hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            
            # Auto login after registration
            cursor.execute('SELECT id, username, role FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            session.user_id = user[0]
            session.username = user[1]
            session.role = user[2]
            
            conn.close()
            raise web.seeother('/')
            
        except sqlite3.IntegrityError:
            conn.close()
            return base_template("Register", '<div class="alert alert-error">Username or email already exists!</div>', False)

class Login:
    def GET(self):
        if is_logged_in():
            raise web.seeother('/')
        
        content = """
        <style>
            .auth-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            
            .auth-form {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #333;
            }
            
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s ease;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .auth-header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .auth-header h2 {
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
        </style>
        
        <div class="auth-container">
            <div class="auth-form">
                <div class="auth-header">
                    <h2>🔐 Login</h2>
                    <p>Welcome back!</p>
                </div>
                
                <form method="post">
                    <div class="form-group">
                        <label for="username">Username or Email:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary" style="width: 100%">Login</button>
                </form>
                
                <p style="text-align: center; margin-top: 20px;">
                    Don't have an account? <a href="/register">Register here</a>
                </p>
            </div>
        </div>
        """
        return base_template("Login", content, False)
    
    def POST(self):
        form = web.input()
        username = form.username.strip()
        password = form.password
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, username, password_hash, role FROM users WHERE username = ? OR email = ?',
            (username, username)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user and user[2] == hash_password(password):
            session.user_id = user[0]
            session.username = user[1]
            session.role = user[3]
            raise web.seeother('/')
        else:
            return base_template("Login", '<div class="alert alert-error">Invalid username or password!</div>', False)

class Logout:
    def GET(self):
        session.kill()
        raise web.seeother('/')

class CreatePost:
    def GET(self):
        if not is_logged_in():
            raise web.seeother('/login')
        
        categories = get_categories()
        categories_options = "".join([f'<option value="{cat[0]}">{cat[1]}</option>' for cat in categories])
        
        content = f"""
        <style>
            .post-form {{
                max-width: 800px;
                margin: 0 auto;
            }}
            
            .form-group {{
                margin-bottom: 25px;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                color: #333;
                font-size: 1.1em;
            }}
            
            .form-group input, .form-group select, .form-group textarea {{
                width: 100%;
                padding: 15px;
                border: 2px solid #e1e8ed;
                border-radius: 10px;
                font-size: 16px;
                font-family: inherit;
                transition: border-color 0.3s ease, box-shadow 0.3s ease;
            }}
            
            .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }}
            
            .form-group textarea {{
                resize: vertical;
                min-height: 200px;
            }}
            
            .button-group {{
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 30px;
            }}
        </style>
        
        <div class="post-form">
            <h2 style="text-align: center; margin-bottom: 30px; background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                ✏️ Create New Post
            </h2>
            
            <form method="post">
                <div class="form-group">
                    <label for="title">📝 Post Title:</label>
                    <input type="text" id="title" name="title" required maxlength="200" placeholder="What's your post about?">
                </div>
                
                <div class="form-group">
                    <label for="category">📂 Category:</label>
                    <select id="category" name="category" required>
                        {categories_options}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="content">💬 Your Message:</label>
                    <textarea id="content" name="content" required maxlength="5000" placeholder="Share your thoughts, ask questions, or start a discussion..."></textarea>
                </div>
                
                <div class="button-group">
                    <button type="submit" class="btn btn-primary">🚀 Post Message</button>
                    <a href="/" class="btn btn-outline">❌ Cancel</a>
                </div>
            </form>
        </div>
        """
        return base_template("Create Post", content)
    
    def POST(self):
        if not is_logged_in():
            raise web.seeother('/login')
        
        form = web.input()
        title = form.title.strip()
        content = form.content.strip()
        category_id = form.category
        
        if title and content:
            conn = sqlite3.connect('forum.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO posts (user_id, category_id, title, content) VALUES (?, ?, ?, ?)',
                (get_user_id(), category_id, title, content)
            )
            conn.commit()
            conn.close()
        
        raise web.seeother('/')

class ViewPost:
    def GET(self, post_id):
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Increment view count
        cursor.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (post_id,))
        
        # Get post with user info
        cursor.execute('''
            SELECT p.*, u.username, c.name as category_name, c.color as category_color
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
        ''', (post_id,))
        post = cursor.fetchone()
        
        if not post:
            conn.close()
            return base_template("Error", "<div class='alert alert-error'>Post not found!</div>")
        
        # Get comments
        cursor.execute('''
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ? AND c.parent_id IS NULL
            ORDER BY c.created_at ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        
        conn.close()
        
        post_content = f"""
        <style>
            .post-detail {{
                margin-bottom: 40px;
            }}
            
            .post-header {{
                border-bottom: 2px solid #e1e8ed;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            
            .post-title {{
                font-size: 2em;
                color: #333;
                margin-bottom: 10px;
            }}
            
            .post-meta {{
                display: flex;
                gap: 20px;
                color: #666;
                flex-wrap: wrap;
            }}
            
            .post-content {{
                font-size: 1.1em;
                line-height: 1.6;
                color: #444;
                margin-bottom: 30px;
            }}
            
            .comments-section {{
                margin-top: 40px;
            }}
            
            .comment {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
            }}
            
            .comment-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }}
            
            .comment-user {{
                font-weight: bold;
                color: #667eea;
            }}
            
            .comment-form {{
                margin-top: 30px;
            }}
            
            .comment-form textarea {{
                width: 100%;
                padding: 15px;
                border: 2px solid #e1e8ed;
                border-radius: 10px;
                font-size: 16px;
                min-height: 100px;
                margin-bottom: 15px;
            }}
        </style>
        
        <div class="post-detail">
            <div class="post-header">
                <h1 class="post-title">{web.websafe(post[3])}</h1>
                <div class="post-meta">
                    <span class="user-info">👤 {web.websafe(post[9])}</span>
                    <span class="category-tag" style="background: {post[10]}">{post[10]}</span>
                    <span class="time">📅 {datetime.strptime(post[5], '%Y-%m-%d %H:%M:%S').strftime('%B %d, %Y at %I:%M %p')}</span>
                    <span class="views">👁️ {post[7]} views</span>
                </div>
            </div>
            
            <div class="post-content">
                {web.websafe(post[4]).replace(chr(10), '<br>')}
            </div>
            
            {f'<div class="post-actions"><a href="/edit/{post_id}" class="btn btn-primary">Edit Post</a></div>' if is_logged_in() and (get_user_id() == post[1] or is_admin()) else ''}
        </div>
        
        <div class="comments-section">
            <h3>💬 Comments ({len(comments)})</h3>
            
            {''.join([f'''
            <div class="comment">
                <div class="comment-header">
                    <span class="comment-user">👤 {web.websafe(comment[6])}</span>
                    <span class="comment-time">{datetime.strptime(comment[4], '%Y-%m-%d %H:%M:%S').strftime('%B %d, %Y at %I:%M %p')}</span>
                </div>
                <div class="comment-content">{web.websafe(comment[3]).replace(chr(10), '<br>')}</div>
            </div>
            ''' for comment in comments])}
            
            {f'''
            <div class="comment-form">
                <form method="post" action="/comment/{post_id}">
                    <textarea name="content" placeholder="Add your comment..." required></textarea>
                    <button type="submit" class="btn btn-primary">Post Comment</button>
                </form>
            </div>
            ''' if is_logged_in() else '<p><a href="/login">Login</a> to post a comment.</p>'}
        </div>
        """
        
        return base_template(f"Post: {post[3]}", post_content)

class EditPost:
    def GET(self, post_id):
        if not is_logged_in():
            raise web.seeother('/login')
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        conn.close()
        
        if not post:
            return base_template("Error", "<div class='alert alert-error'>Post not found!</div>")
        
        if get_user_id() != post[1] and not is_admin():
            return base_template("Error", "<div class='alert alert-error'>You are not authorized to edit this post!</div>")
        
        categories = get_categories()
        categories_options = "".join([f'<option value="{cat[0]}" {"selected" if cat[0] == post[2] else ""}>{cat[1]}</option>' for cat in categories])
        
        content = f"""
        <div class="post-form">
            <h2 style="text-align: center; margin-bottom: 30px;">✏️ Edit Post</h2>
            
            <form method="post">
                <div class="form-group">
                    <label for="title">📝 Post Title:</label>
                    <input type="text" id="title" name="title" value="{web.websafe(post[3])}" required maxlength="200">
                </div>
                
                <div class="form-group">
                    <label for="category">📂 Category:</label>
                    <select id="category" name="category" required>
                        {categories_options}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="content">💬 Your Message:</label>
                    <textarea id="content" name="content" required maxlength="5000">{web.websafe(post[4])}</textarea>
                </div>
                
                <div class="button-group">
                    <button type="submit" class="btn btn-primary">💾 Update Post</button>
                    <a href="/post/{post_id}" class="btn btn-outline">❌ Cancel</a>
                </div>
            </form>
        </div>
        """
        return base_template("Edit Post", content)
    
    def POST(self, post_id):
        if not is_logged_in():
            raise web.seeother('/login')
        
        form = web.input()
        title = form.title.strip()
        content = form.content.strip()
        category_id = form.category
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Check ownership
        cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        
        if not post or (get_user_id() != post[0] and not is_admin()):
            conn.close()
            return base_template("Error", "<div class='alert alert-error'>You are not authorized to edit this post!</div>")
        
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, category_id, post_id)
        )
        conn.commit()
        conn.close()
        
        raise web.seeother(f'/post/{post_id}')

class DeletePost:
    def GET(self, post_id):
        if not is_logged_in():
            raise web.seeother('/login')
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Check ownership
        cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        
        if not post or (get_user_id() != post[0] and not is_admin()):
            conn.close()
            return base_template("Error", "<div class='alert alert-error'>You are not authorized to delete this post!</div>")
        
        cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        cursor.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
        conn.commit()
        conn.close()
        
        raise web.seeother('/')

class AddComment:
    def POST(self, post_id):
        if not is_logged_in():
            raise web.seeother('/login')
        
        form = web.input()
        content = form.content.strip()
        
        if content:
            conn = sqlite3.connect('forum.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
                (post_id, get_user_id(), content)
            )
            conn.commit()
            conn.close()
        
        raise web.seeother(f'/post/{post_id}')

class UserProfile:
    def GET(self):
        if not is_logged_in():
            raise web.seeother('/login')
        
        user = get_user(get_user_id())
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Get user's posts
        cursor.execute('''
            SELECT p.*, c.name as category_name
            FROM posts p
            JOIN categories c ON p.category_id = c.id
            WHERE p.user_id = ?
            ORDER BY p.created_at DESC
            LIMIT 10
        ''', (get_user_id(),))
        posts = cursor.fetchall()
        
        # Get user's comments
        cursor.execute('''
            SELECT c.content, c.created_at, p.title, p.id as post_id
            FROM comments c
            JOIN posts p ON c.post_id = p.id
            WHERE c.user_id = ?
            ORDER BY c.created_at DESC
            LIMIT 10
        ''', (get_user_id(),))
        comments = cursor.fetchall()
        
        conn.close()
        
        content = f"""
        <style>
            .profile-header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 30px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border-radius: 15px;
            }}
            
            .avatar-large {{
                font-size: 4em;
                margin-bottom: 15px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 30px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                color: #333;
                border: 2px solid #e1e8ed;
            }}
            
            .section {{
                margin-bottom: 40px;
            }}
            
            .post-item, .comment-item {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
            }}
        </style>
        
        <div class="profile-header">
            <div class="avatar-large">👤</div>
            <h1>{user[1]}</h1>
            <p>{user[6] or 'No bio yet'}</p>
            <p>Member since {datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S').strftime('%B %Y')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📝 Posts</h3>
                <p>{len(posts)}</p>
            </div>
            <div class="stat-card">
                <h3>💬 Comments</h3>
                <p>{len(comments)}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Posts</h2>
            {''.join([f'''
            <div class="post-item">
                <h4><a href="/post/{post[0]}">{web.websafe(post[3])}</a></h4>
                <p>{web.websafe(post[4])[:100]}...</p>
                <small>{post[9]} • {datetime.strptime(post[5], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')}</small>
            </div>
            ''' for post in posts]) or '<p>No posts yet.</p>'}
        </div>
        
        <div class="section">
            <h2>Recent Comments</h2>
            {''.join([f'''
            <div class="comment-item">
                <p>{web.websafe(comment[0])[:100]}...</p>
                <small>On: <a href="/post/{comment[3]}">{web.websafe(comment[2])}</a> • {datetime.strptime(comment[1], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')}</small>
            </div>
            ''' for comment in comments]) or '<p>No comments yet.</p>'}
        </div>
        """
        
        return base_template("My Profile", content)

class Search:
    def GET(self):
        query = web.input().get('q', '').strip()
        
        if not query:
            return base_template("Search", "<div class='alert alert-error'>Please enter a search term.</div>")
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Search in posts and comments
        cursor.execute('''
            SELECT p.*, u.username, c.name as category_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.title LIKE ? OR p.content LIKE ?
            ORDER BY p.created_at DESC
        ''', (f'%{query}%', f'%{query}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        results_html = "".join([f"""
        <div class="post-card">
            <h3><a href="/post/{result[0]}">{web.websafe(result[3])}</a></h3>
            <div class="post-meta">
                <span>By {web.websafe(result[9])}</span>
                <span>In {result[10]}</span>
                <span>{datetime.strptime(result[5], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')}</span>
            </div>
            <p>{web.websafe(result[4])[:200]}...</p>
        </div>
        """ for result in results])
        
        content = f"""
        <h2>Search Results for "{web.websafe(query)}"</h2>
        <p>Found {len(results)} results</p>
        <div class="search-results">
            {results_html if results else '<p>No results found.</p>'}
        </div>
        """
        
        return base_template("Search", content)

class AdminPanel:
    def GET(self):
        if not is_logged_in() or not is_admin():
            return base_template("Error", "<div class='alert alert-error'>Admin access required!</div>")
        
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM posts')
        total_posts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM comments')
        total_comments = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute('''
            SELECT p.title, u.username, p.created_at 
            FROM posts p 
            JOIN users u ON p.user_id = u.id 
            ORDER BY p.created_at DESC 
            LIMIT 5
        ''')
        recent_posts = cursor.fetchall()
        
        conn.close()
        
        content = f"""
        <style>
            .admin-stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 25px;
                border-radius: 10px;
                text-align: center;
            }}
            
            .recent-activity {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
            }}
        </style>
        
        <h1>⚙️ Admin Panel</h1>
        
        <div class="admin-stats">
            <div class="stat-card">
                <h3>👥 Total Users</h3>
                <p>{total_users}</p>
            </div>
            <div class="stat-card">
                <h3>📝 Total Posts</h3>
                <p>{total_posts}</p>
            </div>
            <div class="stat-card">
                <h3>💬 Total Comments</h3>
                <p>{total_comments}</p>
            </div>
        </div>
        
        <div class="recent-activity">
            <h3>Recent Activity</h3>
            {"".join([f'<p>📝 <strong>{web.websafe(post[1])}</strong> posted: "{web.websafe(post[0])}"</p>' for post in recent_posts])}
        </div>
        """
        
        return base_template("Admin Panel", content)

class CategoryPosts:
    def GET(self, category_id):
        conn = sqlite3.connect('forum.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
        category = cursor.fetchone()
        
        if not category:
            conn.close()
            return base_template("Error", "<div class='alert alert-error'>Category not found!</div>")
        
        cursor.execute('''
            SELECT p.*, u.username, c.name as category_name, c.color as category_color
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.category_id = ?
            ORDER BY p.created_at DESC
        ''', (category_id,))
        posts = cursor.fetchall()
        conn.close()
        
        posts_html = "".join([f"""
        <div class="post-card">
            <h3><a href="/post/{post[0]}">{web.websafe(post[3])}</a></h3>
            <div class="post-meta">
                <span>By {web.websafe(post[9])}</span>
                <span>{datetime.strptime(post[5], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')}</span>
            </div>
            <p>{web.websafe(post[4])[:200]}...</p>
        </div>
        """ for post in posts])
        
        content = f"""
        <h2>Posts in {category[0]}</h2>
        <p>{len(posts)} posts found</p>
        <div class="category-posts">
            {posts_html if posts else '<p>No posts in this category yet.</p>'}
        </div>
        """
        
        return base_template(f"Category: {category[0]}", content)

if __name__ == "__main__":
    app.run()
