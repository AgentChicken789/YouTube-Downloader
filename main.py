import sys
from flask import Flask, send_file, render_template_string, request, session, redirect, url_for
import os
from datetime import datetime
import sqlite3
import secrets
import yt_dlp

ydl_opts = {
    'cookiefile': 'cookies.txt',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['URL'])


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('downloads.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  video_title TEXT,
                  channel TEXT,
                  thumbnail TEXT,
                  ip_address TEXT,
                  download_date DATETIME)''')
    conn.commit()
    conn.close()

def load_admin_password():
    with open('passwort.txt', 'r') as file:
        return file.readline().strip()

ADMIN_PASSWORD = load_admin_password()  # Passwort aus passwort.txt laden

def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt'  # <--- HIER HINZUFÜGEN
    }
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info['title'],
            'thumbnail': info.get('thumbnail'),
            'channel': info.get('uploader', 'Unknown'),
            'duration': info.get('duration')
        }

def download_video(url):
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info['title']
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Downloader</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 90%;
            max-width: 500px;
            text-align: center;
        }
        .video-preview {
            margin: 20px 0;
        }
        .video-preview img {
            max-width: 100%;
            border-radius: 8px;
        }
        h2 {
            color: #1a73e8;
            margin-bottom: 1.5rem;
        }
        .download-btn {
            background: #1a73e8;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            width: 100%;
            display: inline-block;
            text-decoration: none;
            box-sizing: border-box;
        }
        .download-btn:hover {
            background: #1557b0;
        }
        .home-btn {
            display: inline-block;
            background: #34a853;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            width: auto;
            transition: background 0.3s;
        }
        .home-btn:hover {
            background: #2d8745;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="home-btn">← Zurück zur Startseite</a>
        <h2>Download Ready</h2>
        <div class="video-preview">
            <img src="{{ thumbnail }}" alt="Video thumbnail">
            <p><strong>Channel:</strong> {{ channel }}</p>
        </div>
        <p>Your video "{{ title }}" is ready!</p>
        <a href="/download/{{ filename }}" class="download-btn">Download Video</a>
    </div>
</body>
</html>
'''

HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Downloader</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 90%;
            max-width: 500px;
            text-align: center;
        }
        h2 {
            color: #1a73e8;
            margin-bottom: 1.5rem;
        }
        .input-group {
            margin-bottom: 1rem;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input[type="text"]:focus {
            border-color: #1a73e8;
            outline: none;
        }
        button {
            background: #1a73e8;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            width: 100%;
        }
        button:hover {
            background: #1557b0;
        }
        .admin-link {
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <form action="/preview" method="post">
            <div class="input-group">
                <input type="text" name="url" placeholder="Enter YouTube URL">
            </div>
            <button type="submit">Preview Video</button>
        </form>
        <div class="admin-link">
            <a href="/admin">Admin Panel</a>
        </div>
    </div>
</body>
</html>
'''

ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        /* Same styles as above */
        body { 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 90%;
            max-width: 500px;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
        }
        button {
            background: #1a73e8;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Admin Login</h2>
        <form method="post">
            <input type="password" name="password" placeholder="Enter password">
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            padding: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #1a73e8;
            color: white;
        }
        img {
            max-width: 120px;
            border-radius: 4px;
        }
        .logout {
            float: right;
            color: #1a73e8;
            text-decoration: none;
        }
        .clear-logs {
            background: #dc3545;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
            transition: background 0.3s;
        }
        .clear-logs:hover {
            background: #c82333;
        }
        .header-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header-actions">
        <h1>Download History</h1>
        <div>
            <form action="/admin/clear-logs" method="post" style="display: inline;">
                <button type="submit" class="clear-logs" onclick="return confirm('Wirklich alle Logs löschen?')">Logs Löschen</button>
            </form>
            <a href="/admin/logout" class="logout">Logout</a>
        </div>
    </div>
    <table>
        <tr>
            <th>Thumbnail</th>
            <th>Video Title</th>
            <th>Channel</th>
            <th>IP Address</th>
            <th>Download Date</th>
        </tr>
        {% for download in downloads %}
        <tr>
            <td><img src="{{ download[3] }}" alt="Thumbnail"></td>
            <td>{{ download[1] }}</td>
            <td>{{ download[2] }}</td>
            <td>{{ download[4] }}</td>
            <td>{{ download[5] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
'''

@app.route('/')
def home():
    return HOME_TEMPLATE

@app.route('/preview', methods=['POST'])
def preview():
    url = request.form['url']
    video_info = get_video_info(url)
    session['video_info'] = video_info
    session['url'] = url
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Preview</title>
        <style>
            /* Same styles as above */
            body { 
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #f0f2f5;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                width: 90%;
                max-width: 500px;
                text-align: center;
            }
            img {
                max-width: 100%;
                border-radius: 8px;
                margin: 20px 0;
            }
            button {
                background: #1a73e8;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                margin: 5px 0;
            }
            .home-btn {
                display: inline-block;
                background: #34a853;
                color: white;
                text-decoration: none;
                padding: 10px 20px;
                border-radius: 6px;
                margin-bottom: 20px;
                width: auto;
                transition: background 0.3s;
            }
            .home-btn:hover {
                background: #2d8745;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="home-btn">← Zurück zur Startseite</a>
            <h2>Video Preview</h2>
            <img src="{{ video_info.thumbnail }}" alt="Video thumbnail">
            <h3>{{ video_info.title }}</h3>
            <p>Channel: {{ video_info.channel }}</p>
            <p>Duration: {{ video_info.duration // 60 }}:{{ video_info.duration % 60 }}</p>
            <form action="/download" method="post">
                <button type="submit">Download Video</button>
            </form>
        </div>
    </body>
    </html>
    ''', video_info=video_info)

@app.route('/download', methods=['POST'])
def process_download():
    if 'url' not in session or 'video_info' not in session:
        return redirect(url_for('home'))
    
    url = session['url']
    video_info = session['video_info']
    filename, title = download_video(url)
    
    # Log download
    conn = sqlite3.connect('downloads.db')
    c = conn.cursor()
    c.execute('''INSERT INTO downloads (video_title, channel, thumbnail, ip_address, download_date)
                 VALUES (?, ?, ?, ?, ?)''',
              (video_info['title'], video_info['channel'], video_info['thumbnail'],
               request.remote_addr, datetime.now()))
    conn.commit()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE,
                                filename=filename,
                                title=title,
                                thumbnail=video_info['thumbnail'],
                                channel=video_info['channel'])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        return "Invalid password"
    
    if not session.get('admin'):
        return ADMIN_LOGIN_TEMPLATE
    
    conn = sqlite3.connect('downloads.db')
    c = conn.cursor()
    downloads = c.execute('SELECT * FROM downloads ORDER BY download_date DESC').fetchall()
    conn.close()
    
    return render_template_string(ADMIN_TEMPLATE, downloads=downloads)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/admin/clear-logs', methods=['POST'])
def clear_logs():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    conn = sqlite3.connect('downloads.db')
    c = conn.cursor()
    c.execute('DELETE FROM downloads')
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/download/<path:filename>')
def download_file(filename):
    response = send_file(filename, as_attachment=True)
    @response.call_on_close
    def delete_file():
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Deleted file: {filename}")
        except Exception as e:
            print(f"Error deleting file: {e}")
    return response

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=3000)
