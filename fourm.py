import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Advanced Forum",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
def setup_database():
    conn = sqlite3.connect('forum.db', check_same_thread=False)
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
        (4, 'Method', 'Helping For Peoples', '#F44336')
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

def get_categories():
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_user(user_id):
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_category_posts(category_id):
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
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
    return posts

def search_posts(query):
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, c.name as category_name
        FROM posts p
        JOIN users u ON p.user_id = u.id
        JOIN categories c ON p.category_id = c.id
        WHERE p.title LIKE ? OR p.content LIKE ? OR u.username LIKE ?
        ORDER BY p.created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    conn.close()
    return results

# Session state initialization
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'current_post' not in st.session_state:
    st.session_state.current_post = None
if 'category_id' not in st.session_state:
    st.session_state.category_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ''

# Authentication functions
def login_user(username, password):
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id, username, password_hash, role FROM users WHERE username = ? OR email = ?',
        (username, username)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user and user[2] == hash_password(password):
        st.session_state.user = {
            'id': user[0],
            'username': user[1],
            'role': user[3]
        }
        return True
    return False

def register_user(username, email, password):
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        
        # Auto login
        cursor.execute('SELECT id, username, role FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        st.session_state.user = {
            'id': user[0],
            'username': user[1],
            'role': user[2]
        }
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def logout_user():
    st.session_state.user = None
    st.session_state.page = 'home'

# Page functions
def show_home():
    st.title("💬 Advanced Forum")
    
    # Search bar
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Search posts...", placeholder="Search by title, content, or username")
    with col2:
        if st.button("Search", use_container_width=True):
            if search_query:
                st.session_state.search_query = search_query
                st.session_state.page = 'search'
            else:
                st.session_state.search_query = ''
    
    # Stats
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments')
    total_comments = cursor.fetchone()[0]
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Posts", total_posts)
    with col2:
        st.metric("👥 Total Users", total_users)
    with col3:
        st.metric("💬 Total Comments", total_comments)
    
    # Categories
    st.subheader("📂 Categories")
    categories = get_categories()
    cols = st.columns(len(categories))
    for idx, cat in enumerate(categories):
        with cols[idx]:
            cursor.execute('SELECT COUNT(*) FROM posts WHERE category_id = ?', (cat[0],))
            post_count = cursor.fetchone()[0]
            if st.button(
                f"{cat[1]}\n({post_count} posts)",
                key=f"cat_{cat[0]}",
                use_container_width=True
            ):
                st.session_state.page = 'category'
                st.session_state.category_id = cat[0]
                st.rerun()
    
    # Recent posts
    st.subheader("📝 Recent Posts")
    cursor.execute('''
        SELECT p.*, u.username, c.name as category_name, c.color as category_color,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        JOIN categories c ON p.category_id = c.id
        ORDER BY p.is_pinned DESC, p.created_at DESC
        LIMIT 10
    ''')
    posts = cursor.fetchall()
    conn.close()
    
    if not posts:
        st.info("No posts yet. Be the first to share something! 🚀")
    else:
        for post in posts:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    if post[8]:  # is_pinned
                        st.write(f"**📌 {post[3]}**")
                    else:
                        st.write(f"**{post[3]}**")
                    
                    st.write(f"👤 **{post[9]}** | 📂 **{post[10]}** | 👁️ **{post[7]}** | 💬 **{post[12]}**")
                    st.write(f"🕒 {post[5]}")
                    # Display content with proper line breaks
                    content_display = post[4].replace('\n', '  \n')
                    st.write(content_display[:200] + "...")
                
                with col2:
                    if st.button("Read More", key=f"read_{post[0]}"):
                        st.session_state.page = 'view_post'
                        st.session_state.current_post = post[0]
                        st.rerun()
                    
                    # Edit button for post owners and admins
                    if st.session_state.user and (st.session_state.user['id'] == post[1] or st.session_state.user['role'] == 'admin'):
                        if st.button("Edit", key=f"edit_{post[0]}"):
                            st.session_state.page = 'edit_post'
                            st.session_state.current_post = post[0]
                            st.rerun()
                
                st.divider()
    
    # Create post button
    if st.session_state.user:
        if st.button("✏️ Create New Post", use_container_width=True):
            st.session_state.page = 'create_post'
            st.rerun()

def show_login():
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username and password:
                if login_user(username, password):
                    st.success("Login successful!")
                    st.session_state.page = 'home'
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password!")
            else:
                st.error("Please enter both username and password!")
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_register():
    st.title("👤 Register")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill in all fields!")
            elif password != confirm_password:
                st.error("Passwords do not match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters!")
            else:
                if register_user(username, email, password):
                    st.success("Registration successful! You are now logged in.")
                    st.session_state.page = 'home'
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Username or email already exists!")
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_create_post():
    st.title("✏️ Create New Post")
    
    categories = get_categories()
    category_names = [cat[1] for cat in categories]
    category_ids = [cat[0] for cat in categories]
    
    with st.form("create_post_form"):
        title = st.text_input("Post Title", placeholder="Enter a descriptive title for your post")
        category = st.selectbox("Category", category_names)
        content = st.text_area("Content", height=200, placeholder="Write your post content here...\nYou can use line breaks for better formatting.")
        submit = st.form_submit_button("Create Post")
        
        if submit:
            if title and content:
                category_id = category_ids[category_names.index(category)]
                conn = sqlite3.connect('forum.db', check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO posts (user_id, category_id, title, content) VALUES (?, ?, ?, ?)',
                    (st.session_state.user['id'], category_id, title, content)
                )
                conn.commit()
                conn.close()
                st.success("Post created successfully!")
                st.session_state.page = 'home'
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please fill in both title and content!")
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_edit_post():
    if not st.session_state.current_post:
        st.error("No post selected!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (st.session_state.current_post,))
    post = cursor.fetchone()
    conn.close()
    
    if not post:
        st.error("Post not found!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    # Check ownership
    if st.session_state.user['id'] != post[1] and st.session_state.user['role'] != 'admin':
        st.error("You are not authorized to edit this post!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.title("✏️ Edit Post")
    
    categories = get_categories()
    category_names = [cat[1] for cat in categories]
    category_ids = [cat[0] for cat in categories]
    
    # Get current category name
    current_category_name = None
    for cat in categories:
        if cat[0] == post[2]:
            current_category_name = cat[1]
            break
    
    with st.form("edit_post_form"):
        title = st.text_input("Post Title", value=post[3])
        category = st.selectbox("Category", category_names, index=category_names.index(current_category_name) if current_category_name else 0)
        content = st.text_area("Content", value=post[4], height=200)
        submit = st.form_submit_button("Update Post")
        
        if submit:
            if title and content:
                category_id = category_ids[category_names.index(category)]
                conn = sqlite3.connect('forum.db', check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE posts SET title = ?, content = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (title, content, category_id, st.session_state.current_post)
                )
                conn.commit()
                conn.close()
                st.success("Post updated successfully!")
                st.session_state.page = 'view_post'
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please fill in all fields!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Post"):
            st.session_state.page = 'view_post'
            st.rerun()
    with col2:
        if st.button("← Back to Home"):
            st.session_state.page = 'home'
            st.rerun()

def show_view_post():
    if not st.session_state.current_post:
        st.error("No post selected!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Increment view count
    cursor.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (st.session_state.current_post,))
    
    # Get post details
    cursor.execute('''
        SELECT p.*, u.username, c.name as category_name, c.color as category_color
        FROM posts p
        JOIN users u ON p.user_id = u.id
        JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
    ''', (st.session_state.current_post,))
    post = cursor.fetchone()
    
    if not post:
        st.error("Post not found!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    # Display post
    if post[8]:  # is_pinned
        st.title(f"📌 {post[3]}")
    else:
        st.title(post[3])
    
    st.write(f"**👤 By:** {post[9]} | **📂 Category:** {post[10]} | **👁️ Views:** {post[7]} | **🕒 Posted:** {post[5]}")
    
    # Edit and Delete buttons for post owners and admins
    if st.session_state.user and (st.session_state.user['id'] == post[1] or st.session_state.user['role'] == 'admin'):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Edit Post"):
                st.session_state.page = 'edit_post'
                st.rerun()
        with col2:
            if st.button("🗑️ Delete Post"):
                cursor.execute('DELETE FROM posts WHERE id = ?', (st.session_state.current_post,))
                cursor.execute('DELETE FROM comments WHERE post_id = ?', (st.session_state.current_post,))
                conn.commit()
                st.success("Post deleted successfully!")
                st.session_state.page = 'home'
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # Display content with proper line breaks
    content_display = post[4].replace('\n', '  \n')
    st.write(content_display)
    
    st.divider()
    
    # Comments section
    st.subheader("💬 Comments")
    
    # Get comments
    cursor.execute('''
        SELECT c.*, u.username
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id = ? AND c.parent_id IS NULL
        ORDER BY c.created_at ASC
    ''', (st.session_state.current_post,))
    comments = cursor.fetchall()
    
    if not comments:
        st.info("No comments yet. Be the first to comment! 💬")
    else:
        for comment in comments:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{comment[6]}** - {comment[4]}")
                    comment_content = comment[3].replace('\n', '  \n')
                    st.write(comment_content)
                with col2:
                    # Delete comment button for comment owners and admins
                    if st.session_state.user and (st.session_state.user['id'] == comment[2] or st.session_state.user['role'] == 'admin'):
                        if st.button("Delete", key=f"del_comment_{comment[0]}"):
                            cursor.execute('DELETE FROM comments WHERE id = ?', (comment[0],))
                            conn.commit()
                            st.success("Comment deleted!")
                            st.rerun()
                st.divider()
    
    # Add comment form
    if st.session_state.user:
        with st.form("add_comment_form"):
            comment_content = st.text_area("Add a comment", placeholder="Share your thoughts...")
            submit = st.form_submit_button("💬 Post Comment")
            
            if submit:
                if comment_content:
                    cursor.execute(
                        'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
                        (st.session_state.current_post, st.session_state.user['id'], comment_content)
                    )
                    conn.commit()
                    st.success("Comment added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter a comment!")
    else:
        st.info("Please login to post a comment.")
    
    conn.close()
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_profile():
    if not st.session_state.user:
        st.error("Please login to view profile!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.title("👤 User Profile")
    
    user = get_user(st.session_state.user['id'])
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # User info
    col1, col2 = st.columns([1, 3])
    with col1:
        st.header("👤")
    with col2:
        st.write(f"### {user[1]}")
        st.write(f"**Email:** {user[2]}")
        st.write(f"**Role:** {user[4]}")
        st.write(f"**Member since:** {user[5][:10]}")
        if user[6]:
            st.write(f"**Bio:** {user[6]}")
    
    st.divider()
    
    # User stats
    cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user[0],))
    post_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments WHERE user_id = ?', (user[0],))
    comment_count = cursor.fetchone()[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📝 Posts", post_count)
    with col2:
        st.metric("💬 Comments", comment_count)
    
    st.divider()
    
    # Recent posts
    st.subheader("Recent Posts")
    cursor.execute('''
        SELECT p.*, c.name as category_name
        FROM posts p
        JOIN categories c ON p.category_id = c.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
        LIMIT 5
    ''', (user[0],))
    posts = cursor.fetchall()
    
    if not posts:
        st.info("No posts yet.")
    else:
        for post in posts:
            with st.container():
                st.write(f"**{post[3]}** (in {post[9]})")
                content_preview = post[4].replace('\n', ' ')[:100] + "..."
                st.write(content_preview)
                if st.button("View", key=f"view_my_post_{post[0]}"):
                    st.session_state.page = 'view_post'
                    st.session_state.current_post = post[0]
                    st.rerun()
                st.divider()
    
    conn.close()
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_admin():
    if not st.session_state.user or st.session_state.user['role'] != 'admin':
        st.error("Admin access required!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.title("⚙️ Admin Panel")
    
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Stats
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments')
    total_comments = cursor.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Users", total_users)
    with col2:
        st.metric("📝 Total Posts", total_posts)
    with col3:
        st.metric("💬 Total Comments", total_comments)
    
    st.divider()
    
    # Recent activity
    st.subheader("Recent Activity")
    cursor.execute('''
        SELECT p.title, u.username, p.created_at 
        FROM posts p 
        JOIN users u ON p.user_id = u.id 
        ORDER BY p.created_at DESC 
        LIMIT 5
    ''')
    recent_posts = cursor.fetchall()
    
    for post in recent_posts:
        st.write(f"📝 **{post[1]}** posted: *{post[0]}*")
    
    st.divider()
    
    # User management
    st.subheader("User Management")
    cursor.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    
    for user in users:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.write(f"**{user[1]}**")
        with col2:
            # Hide email for privacy - show only first 3 characters
            email_display = user[2][:3] + "***" + user[2].split('@')[1] if '@' in user[2] else "***"
            st.write(email_display)
        with col3:
            st.write(user[3])
        with col4:
            if user[1] != 'admin':  # Don't allow deleting admin
                if st.button("Delete", key=f"del_user_{user[0]}"):
                    cursor.execute('DELETE FROM users WHERE id = ?', (user[0],))
                    # Also delete user's posts and comments
                    cursor.execute('DELETE FROM posts WHERE user_id = ?', (user[0],))
                    cursor.execute('DELETE FROM comments WHERE user_id = ?', (user[0],))
                    conn.commit()
                    st.success(f"User {user[1]} deleted!")
                    st.rerun()
    
    conn.close()
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_category():
    if not st.session_state.category_id:
        st.error("No category selected!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    conn = sqlite3.connect('forum.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM categories WHERE id = ?', (st.session_state.category_id,))
    category = cursor.fetchone()
    
    if not category:
        st.error("Category not found!")
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.title(f"📂 {category[0]} Posts")
    
    posts = get_category_posts(st.session_state.category_id)
    
    if not posts:
        st.info(f"No posts in {category[0]} yet. Be the first to post! 🚀")
    else:
        for post in posts:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{post[3]}**")
                    st.write(f"👤 **{post[9]}** | 👁️ **{post[7]}** | 🕒 **{post[5]}**")
                    content_preview = post[4].replace('\n', ' ')[:200] + "..."
                    st.write(content_preview)
                with col2:
                    if st.button("Read More", key=f"cat_read_{post[0]}"):
                        st.session_state.page = 'view_post'
                        st.session_state.current_post = post[0]
                        st.rerun()
                st.divider()
    
    conn.close()
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

def show_search():
    if not st.session_state.search_query:
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.title(f"🔍 Search Results for '{st.session_state.search_query}'")
    
    results = search_posts(st.session_state.search_query)
    
    if not results:
        st.info("No results found. Try different keywords.")
    else:
        st.write(f"Found {len(results)} results:")
        
        for post in results:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{post[3]}**")
                    st.write(f"👤 **{post[9]}** | 📂 **{post[10]}** | 👁️ **{post[7]}** | 🕒 **{post[5]}**")
                    content_preview = post[4].replace('\n', ' ')[:200] + "..."
                    st.write(content_preview)
                with col2:
                    if st.button("Read More", key=f"search_read_{post[0]}"):
                        st.session_state.page = 'view_post'
                        st.session_state.current_post = post[0]
                        st.rerun()
                st.divider()
    
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

# Sidebar
with st.sidebar:
    st.title("💬 Advanced Forum")
    
    if st.session_state.user:
        st.success(f"Welcome, **{st.session_state.user['username']}**!")
        st.write(f"Role: **{st.session_state.user['role']}**")
        
        if st.button("👤 Profile", use_container_width=True):
            st.session_state.page = 'profile'
            st.rerun()
        
        if st.session_state.user['role'] == 'admin':
            if st.button("⚙️ Admin Panel", use_container_width=True):
                st.session_state.page = 'admin'
                st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()
        with col2:
            if st.button("👤 Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()
    
    st.divider()
    
    # Navigation
    st.subheader("Navigation")
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
    
    if st.session_state.user:
        if st.button("✏️ Create Post", use_container_width=True):
            st.session_state.page = 'create_post'
            st.rerun()
    
    st.divider()
    st.write("**Need Help?**")
    st.write("Contact forum administrator")

# Main content based on current page
if st.session_state.page == 'home':
    show_home()
elif st.session_state.page == 'login':
    show_login()
elif st.session_state.page == 'register':
    show_register()
elif st.session_state.page == 'create_post':
    show_create_post()
elif st.session_state.page == 'edit_post':
    show_edit_post()
elif st.session_state.page == 'view_post':
    show_view_post()
elif st.session_state.page == 'profile':
    show_profile()
elif st.session_state.page == 'admin':
    show_admin()
elif st.session_state.page == 'category':
    show_category()
elif st.session_state.page == 'search':
    show_search()
