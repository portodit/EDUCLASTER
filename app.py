from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

import pandas as pd
import folium
import os

# Flask initialization
app = Flask(__name__)

# Secret key for sessions
app.secret_key = 'your_secret_key'

# Setup MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'pendidikandb'

mysql = MySQL(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Menentukan endpoint untuk login

# Custom login message (opsional)
login_manager.login_message = "Silakan login untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

# User class to represent a logged-in user
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

# Login manager callback function
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cur.fetchone()
    if user:
        return User(id=user[0], username=user[1], email=user[3])
    return None

# Create a Flask-WTF form for login
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[DataRequired()])

# Create a Flask-WTF form for register
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])

# Routes for login and registration
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cur.fetchone()

        if user and check_password_hash(user[2], password):  # Verifikasi password yang telah di-hash
            login_user(User(id=user[0], username=user[1], email=user[3]))
            
            # Redirect ke halaman yang diminta sebelumnya (jika ada)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('home'))
        else:
            flash('Username atau password tidak valid. Silakan coba lagi.', 'danger')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data

        # Check if username already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        existing_user = cur.fetchone()
        
        if existing_user:
            flash('Username sudah digunakan. Silakan pilih username lain.', 'danger')
        else:
            hashed_password = generate_password_hash(password)  # Meng-hash password sebelum disimpan
            # Insert the new user
            cur.execute("INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)", 
                        (username, hashed_password, email))
            mysql.connection.commit()
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Anda telah keluar dari sistem.', 'info')
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html')

# Pastikan folder STATIC untuk menyimpan peta
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)  # Buat folder static jika belum ada

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)  # Buat folder data jika belum ada

# Warna berdasarkan cluster
cluster_colors = {
    0: "red",   # Cluster 0
    1: "blue",  # Cluster 1
    2: "green"  # Cluster 2
}

def generate_map(data_file, map_filename, selected_clusters=None):
    """ Fungsi untuk membuat peta klasterisasi berdasarkan data SMA/SMK """
    try:
        df = pd.read_csv(data_file, sep=None, engine="python", encoding="utf-8")
        
        # Pastikan ada kolom latitude, longitude, dan Cluster
        required_columns = {"latitude", "longitude", "Cluster"}
        if not required_columns.issubset(df.columns):
            return f"Error: Kolom yang diperlukan tidak ditemukan dalam {data_file}", None
        
        # Buat peta awal dengan titik tengah Surabaya
        fmap = folium.Map(location=[-7.2575, 112.7521], zoom_start=12)
        
        # Filter berdasarkan klaster yang dipilih
        if selected_clusters:
            df = df[df['Cluster'].isin(selected_clusters)]
        
        # Tambahkan titik berdasarkan klaster
        for _, row in df.iterrows():
            cluster = row["Cluster"]
            color = cluster_colors.get(cluster, "gray")  # Default warna jika cluster tidak ditemukan
            
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=7,  # Ukuran marker
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                popup=f"{row['Kecamatan']} - Cluster {cluster}"
            ).add_to(fmap)
        
        # Simpan ke file HTML dalam folder static
        map_path = os.path.join(STATIC_DIR, map_filename)
        fmap.save(map_path)
        print(f"Peta berhasil disimpan di: {map_path}")  # Debugging log
        return map_path, df
    
    except Exception as e:
        print(f"Error saat membuat peta: {e}")  # Log error jika terjadi kesalahan
        return None, None

def get_cluster_counts(df):
    """Mendapatkan jumlah sekolah per klaster dari DataFrame"""
    if df is not None:
        return df['Cluster'].value_counts().to_dict()
    return {0: 0, 1: 0, 2: 0}

@app.route('/test-db')
def test_db_connection():
    """Cek apakah Flask berhasil terhubung ke MySQL"""
    try:
        # Membuat cursor untuk eksekusi query
        cur = mysql.connection.cursor()

        # Menjalankan query sederhana untuk memverifikasi koneksi
        cur.execute('SELECT 1')

        # Ambil hasilnya
        result = cur.fetchone()

        # Jika berhasil, tampilkan pesan ini
        if result:
            return "Flask berhasil terhubung dengan MySQL!"
        else:
            return "Gagal terhubung dengan MySQL."
    except Exception as e:
        return f"Terjadi error: {str(e)}"

# Halaman yang memerlukan login (klasterisasi)
@app.route('/map/sma')
@login_required  # Hanya pengguna yang sudah login yang dapat mengakses
def map_sma():
    # Mengambil parameter klaster yang dipilih
    clusters = request.args.get('clusters', default="", type=str)
    selected_clusters = [int(c) for c in clusters.split(',')] if clusters else None
    data_file = os.path.join(DATA_DIR, 'data_aggregated_sma_new.csv')
    map_file, df = generate_map(data_file, "map_sma.html", selected_clusters)
    
    if map_file and df is not None:
        # Menghitung jumlah klaster
        cluster_counts = get_cluster_counts(df)
        return render_template('map.html', map_file="/static/map_sma.html", cluster_counts=cluster_counts)
    else:
        flash("Terjadi kesalahan saat membuat peta SMA", "error")
        return redirect(url_for('home'))

@app.route('/map/smk')
@login_required  # Hanya pengguna yang sudah login yang dapat mengakses
def map_smk():
    # Mengambil parameter klaster yang dipilih
    clusters = request.args.get('clusters', default="", type=str)
    selected_clusters = [int(c) for c in clusters.split(',')] if clusters else None
    data_file = os.path.join(DATA_DIR, 'data_aggregated_smk_new.csv')
    map_file, df = generate_map(data_file, "map_smk.html", selected_clusters)
    
    if map_file and df is not None:
        # Menghitung jumlah klaster
        cluster_counts = get_cluster_counts(df)
        return render_template('map.html', map_file="/static/map_smk.html", cluster_counts=cluster_counts)
    else:
        flash("Terjadi kesalahan saat membuat peta SMK", "error")
        return redirect(url_for('home'))

# API Endpoints (Tidak memerlukan login)

@app.route('/api/map/<type>')
def api_map(type):
    """
    API khusus untuk mengembalikan HANYA iframe dengan peta.
    Tidak memerlukan login.
    """
    # Mengambil parameter klaster yang dipilih
    clusters = request.args.get('clusters', default="0,1,2", type=str)
    selected_clusters = [int(c) for c in clusters.split(',')] if clusters else [0, 1, 2]
    
    # Pilih file data berdasarkan tipe
    if type == 'sma':
        data_file = os.path.join(DATA_DIR, 'data_aggregated_sma_new.csv')
        map_filename = "map_sma.html"
    else:  # smk
        data_file = os.path.join(DATA_DIR, 'data_aggregated_smk_new.csv')
        map_filename = "map_smk.html"
    
    # Generate map
    map_file, _ = generate_map(data_file, map_filename, selected_clusters)
    
    if map_file:
        # Mengembalikan HANYA HTML iframe yang berisi peta
        return f'<iframe src="/static/{map_filename}" width="100%" height="600px" class="border-0"></iframe>'
    else:
        return "Terjadi kesalahan saat membuat peta", 500

@app.route('/api/cluster-counts/<type>')
def api_cluster_counts(type):
    """
    API untuk mendapatkan jumlah sekolah per klaster untuk tipe tertentu.
    Tidak memerlukan login.
    """
    # Mengambil parameter klaster yang dipilih
    clusters = request.args.get('clusters', default="0,1,2", type=str)
    selected_clusters = [int(c) for c in clusters.split(',')] if clusters else [0, 1, 2]
    
    # Pilih file data berdasarkan tipe
    if type == 'sma':
        data_file = os.path.join(DATA_DIR, 'data_aggregated_sma_new.csv')
    else:  # smk
        data_file = os.path.join(DATA_DIR, 'data_aggregated_smk_new.csv')
    
    try:
        # Baca data
        df = pd.read_csv(data_file, sep=None, engine="python", encoding="utf-8")
        
        # Filter berdasarkan klaster yang dipilih
        if selected_clusters:
            df = df[df['Cluster'].isin(selected_clusters)]
        
        # Hitung jumlah per klaster
        counts = get_cluster_counts(df)
        
        # Pastikan semua klaster ada dalam respons
        for cluster in [0, 1, 2]:
            if cluster not in counts:
                counts[cluster] = 0
        
        return jsonify(counts)
    
    except Exception as e:
        print(f"Error saat mendapatkan jumlah klaster: {e}")
        return jsonify({0: 0, 1: 0, 2: 0})

# Route untuk dashboard (tidak memerlukan login)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route untuk about (tidak memerlukan login)
@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)