# Tambahkan impor pymysql di awal file
import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import pandas as pd
import numpy as np
import folium
import os
import json
import datetime
import uuid
import matplotlib
matplotlib.use('Agg')  # Backend non-GUI
import matplotlib.pyplot as plt  # Untuk plotting
import MySQLdb
import logging
import traceback

import io
import base64

# Import modul kustom ClusteringManager
from ClusteringManager import ClusteringManager

# Flask initialization
app = Flask(__name__)

# Secret key for sessions
app.secret_key = 'your_secret_key'

# Setup MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'educlusterdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # Gunakan DictCursor secara default

# Setup file upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Buat folder uploads jika belum ada
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max size


# Direktori untuk output gambar klasterisasi
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'clustering')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)  # Buat folder output jika belum ada

# Direktori untuk hasil ekspor data
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'data', 'exports')
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)  # Buat folder exports jika belum ada

mysql = MySQL(app)

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# Helper function to get ClusteringManager instance
def get_clustering_manager():
    """
    Mengembalikan instance ClusteringManager untuk digunakan dalam route handlers
    """
    try:
        # Buat instance ClusteringManager
        manager = ClusteringManager(mysql)
        return manager
    except Exception as e:
        logger.error(f"Error creating ClusteringManager: {str(e)}", exc_info=True)
        raise

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Menentukan endpoint untuk login

# Custom login message (opsional)
login_manager.login_message = "Silakan login untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

# User class to represent a logged-in user
class User(UserMixin):
    def __init__(self, id, username, email, role='user'):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

# Login manager callback function
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cur.fetchone()
    if user:
        return User(id=user['id'], username=user['username'], email=user['email'], role=user['role'])
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

###############################################################################
# ROUTE - Autentikasi dan halaman dasar
###############################################################################

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

        if user and check_password_hash(user['password_hash'], password):  # Akses sebagai dict, bukan tuple
            login_user(User(id=user['id'], username=user['username'], email=user['email'], role=user['role']))
            
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
            cur.execute("INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)", 
                        (username, hashed_password, email, 'user'))
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

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/about')
def about():
    return render_template('about.html')

###############################################################################
# ROUTE - Fitur Klasterisasi Wilayah
###############################################################################

# Tab 1: Import Data (untuk admin)
@app.route('/klasterisasi')
@login_required
def klasterisasi():
    """Menampilkan halaman klasterisasi utama"""
    try:
        # Dapatkan hasil klasterisasi dari ClusteringManager
        clustering_manager = get_clustering_manager()
        results = clustering_manager.get_available_clustering_results()
        return render_template('klasterisasi.html', results=results)
    except Exception as e:
        logger.error(f"Error in klasterisasi route: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        return render_template('klasterisasi.html', results=[])

@app.route('/klasterisasi/create_process', methods=['POST'])
@login_required
def create_process():
    """Menangani upload dan import hasil klasterisasi"""
    if 'csv_file' not in request.files:
        flash('Tidak ada file yang diunggah', 'danger')
        return redirect(url_for('klasterisasi'))
   
    file = request.files['csv_file']
    if file.filename == '':
        flash('Tidak ada file yang dipilih', 'danger')
        return redirect(url_for('klasterisasi'))
   
    # Dapatkan parameter dari form
    jenjang = request.form.get('jenjang', 'SMA')
    skenario = request.form.get('skenario', '1')
    jumlah_cluster = request.form.get('jumlah_cluster', '')
    description = request.form.get('description', '')
   
    # Validasi input
    if jenjang not in ['SMA', 'SMK']:
        flash('Jenjang pendidikan tidak valid', 'danger')
        return redirect(url_for('klasterisasi'))
   
    if skenario not in ['1', '2']:
        flash('Skenario tidak valid', 'danger')
        return redirect(url_for('klasterisasi'))
   
    # Simpan file sementara
    temp_filename = secure_filename(f"temp_{uuid.uuid4().hex}_{file.filename}")
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    file.save(temp_filepath)
   
    try:
        # Dapatkan instance ClusteringManager
        clustering_manager = get_clustering_manager()
        
        # Buat proses klasterisasi terlebih dahulu
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id FROM clustering_processes 
            WHERE jenjang = %s AND skenario = %s
        """, [jenjang, skenario])
        
        process_result = cur.fetchone()
        
        if process_result:
            process_id = process_result['id']
            logger.info(f"Menggunakan proses klasterisasi yang sudah ada dengan ID {process_id}")
        else:
            # Buat proses baru jika belum ada
            cur.execute("""
                INSERT INTO clustering_processes 
                (name, jenjang, skenario, status, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, [
                f"Proses Klasterisasi {jenjang} - Skenario {skenario}", 
                jenjang, 
                skenario, 
                'active', 
                current_user.id
            ])
            mysql.connection.commit()
            process_id = cur.lastrowid
            logger.info(f"Membuat proses klasterisasi baru dengan ID {process_id}")
        
        # Proses file dengan clustering_manager menggunakan process_id yang didapat
        success, message, result_id = clustering_manager.import_from_csv(
            temp_filepath,
            process_id,  # Gunakan process_id, bukan current_user.id
            jenjang,
            skenario,
            jumlah_cluster,
            description
        )
       
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
       
        # Hapus file sementara
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
       
        return redirect(url_for('klasterisasi'))
       
    except Exception as e:
        logger.error(f"Error in create_process: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat memproses file: {str(e)}', 'danger')
       
        # Hapus file sementara jika ada error
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
       
        return redirect(url_for('klasterisasi'))

@app.route('/klasterisasi/import_sekolah_data', methods=['POST'])
@login_required
def import_sekolah_data():
    """Menangani upload dan import data sekolah untuk melengkapi hasil klasterisasi"""
    if 'sekolah_file' not in request.files:
        flash('Tidak ada file data sekolah yang diunggah', 'danger')
        return redirect(url_for('klasterisasi'))
    
    file = request.files['sekolah_file']
    if file.filename == '':
        flash('Tidak ada file data sekolah yang dipilih', 'danger')
        return redirect(url_for('klasterisasi'))
    
    # Dapatkan ID hasil klasterisasi
    result_id = request.form.get('result_id')
    if not result_id:
        flash('ID hasil klasterisasi diperlukan', 'danger')
        return redirect(url_for('klasterisasi'))
    
    # Validasi result_id
    try:
        result_id = int(result_id)
    except ValueError:
        flash('ID hasil klasterisasi tidak valid', 'danger')
        return redirect(url_for('klasterisasi'))
    
    # Cek apakah result_id ada di database
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
    if not cur.fetchone():
        flash('ID hasil klasterisasi tidak ditemukan', 'danger')
        return redirect(url_for('klasterisasi'))
    
    # Simpan file sementara
    temp_filename = secure_filename(f"temp_sekolah_{uuid.uuid4().hex}_{file.filename}")
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    file.save(temp_filepath)
    
    try:
        # Dapatkan instance ClusteringManager
        clustering_manager = get_clustering_manager()
        
        # Proses file data sekolah
        success, message, count = clustering_manager.import_sekolah_data(temp_filepath, result_id)
        
        if success:
            flash(f'{message} ({count} sekolah)', 'success')
        else:
            flash(message, 'danger')
        
        # Hapus file sementara
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return redirect(url_for('klasterisasi'))
        
    except Exception as e:
        logger.error(f"Error in import_sekolah_data: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat memproses data sekolah: {str(e)}', 'danger')
        
        # Hapus file sementara jika ada error
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return redirect(url_for('klasterisasi'))

@app.route('/klasterisasi/export/<format>/<int:result_id>')
@login_required
def export_data(format, result_id):
    """Mengekspor hasil klasterisasi dalam format tertentu"""
    try:
        # Validasi format
        if format not in ['csv', 'excel', 'pdf']:
            flash('Format ekspor tidak valid', 'danger')
            return redirect(url_for('klasterisasi'))
        
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            flash('ID hasil klasterisasi tidak ditemukan', 'danger')
            return redirect(url_for('klasterisasi'))
            
        clustering_manager = get_clustering_manager()
       
        if format == 'csv':
            success, path = clustering_manager.export_to_csv(result_id)
            if success:
                return send_file(path, as_attachment=True, download_name=f'cluster_result_{result_id}.csv')
            else:
                flash(f'Error ekspor CSV: {path}', 'danger')
       
        elif format == 'excel':
            success, path = clustering_manager.export_to_excel(result_id)
            if success:
                return send_file(path, as_attachment=True, download_name=f'cluster_result_{result_id}.xlsx')
            else:
                flash(f'Error ekspor Excel: {path}', 'danger')
       
        elif format == 'pdf':
            success, path = clustering_manager.export_to_pdf(result_id)
            if success:
                return send_file(path, as_attachment=True, download_name=f'cluster_result_{result_id}.pdf')
            else:
                flash(f'Error ekspor PDF: {path}', 'danger')
           
    except Exception as e:
        logger.error(f"Error in export_data: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat mengekspor: {str(e)}', 'danger')
   
    return redirect(url_for('klasterisasi'))

@app.route('/klasterisasi/backup/<int:result_id>')
@login_required
def backup_result(result_id):
    """Backup hasil klasterisasi ke file ZIP"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            flash('ID hasil klasterisasi tidak ditemukan', 'danger')
            return redirect(url_for('klasterisasi'))
            
        clustering_manager = get_clustering_manager()
        success, path = clustering_manager.backup_clustering_result(result_id)
        
        if success:
            return send_file(path, as_attachment=True, download_name=f'backup_cluster_{result_id}.zip')
        else:
            flash(f'Error backup: {path}', 'danger')
            
    except Exception as e:
        logger.error(f"Error in backup_result: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat backup: {str(e)}', 'danger')
    
    return redirect(url_for('klasterisasi'))

@app.route('/klasterisasi/restore', methods=['POST'])
@login_required
def restore_result():
    """Memulihkan hasil klasterisasi dari file backup"""
    if 'backup_file' not in request.files:
        flash('Tidak ada file backup yang diunggah', 'danger')
        return redirect(url_for('klasterisasi'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('Tidak ada file backup yang dipilih', 'danger')
        return redirect(url_for('klasterisasi'))
    
    # Simpan file sementara
    temp_filename = secure_filename(f"temp_backup_{uuid.uuid4().hex}_{file.filename}")
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    file.save(temp_filepath)
    
    try:
        # Dapatkan instance ClusteringManager
        clustering_manager = get_clustering_manager()
        
        # Proses file backup
        success, message, result_id = clustering_manager.restore_clustering_result(temp_filepath)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        # Hapus file sementara
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return redirect(url_for('klasterisasi'))
        
    except Exception as e:
        logger.error(f"Error in restore_result: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat memulihkan backup: {str(e)}', 'danger')
        
        # Hapus file sementara jika ada error
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return redirect(url_for('klasterisasi'))

@app.route('/klasterisasi/preview_csv', methods=['POST'])
def preview_csv():
    """API untuk preview data CSV sebelum import"""
    if 'csv_file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diunggah'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400
    
    try:
        # Simpan file sementara
        temp_filename = secure_filename(f"preview_{uuid.uuid4().hex}_{file.filename}")
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_filepath)
        
        # Validasi format CSV dengan ClusteringManager
        clustering_manager = get_clustering_manager()
        is_valid, message, df = clustering_manager.validate_csv_format(temp_filepath)
        
        # Hapus file sementara
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Hanya ambil beberapa baris untuk preview
        preview_rows = df.head(10).to_dict('records')
        
        # Dapatkan informasi kolom
        columns = list(df.columns)
        
        # Periksa apakah kolom yang diperlukan ada
        required_columns = ['kecamatan', 'cluster', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']
        missing_columns = [col for col in required_columns if col not in [c.lower() for c in df.columns]]
        
        # Hitung jumlah baris dan kolom
        row_count = len(df)
        column_count = len(df.columns)
        
        # Dapatkan statistik dasar untuk kolom numerik
        stats = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                stats[col] = {
                    'mean': df[col].mean(),
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'na_count': df[col].isna().sum()
                }
        
        return jsonify({
            'preview': preview_rows,
            'columns': columns,
            'missing_columns': missing_columns,
            'row_count': row_count,
            'column_count': column_count,
            'stats': stats
        })
    
    except Exception as e:
        # Hapus file sementara jika ada error
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            
        logger.error(f"Error in preview_csv: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# Tab 2: Hasil Klasterisasi (tabel hasil)
@app.route('/klasterisasi/delete/<int:result_id>', methods=['POST'])
@login_required
def delete_cluster_result(result_id):
    """Menghapus hasil klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'ID hasil klasterisasi tidak ditemukan'})
            
        clustering_manager = get_clustering_manager()
        success = clustering_manager.delete_clustering_result(result_id)
       
        if success:
            return jsonify({'success': True, 'message': 'Hasil klasterisasi berhasil dihapus'})
        else:
            return jsonify({'success': False, 'message': 'Gagal menghapus hasil klasterisasi'})
   
    except Exception as e:
        logger.error(f"Error in delete_cluster_result: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'})

@app.route('/klasterisasi/check_quality/<int:result_id>')
@login_required
def check_quality(result_id):
    """Memeriksa kualitas data klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        clustering_manager = get_clustering_manager()
        issues = clustering_manager.check_data_quality(result_id)
        
        return jsonify(issues)
    except Exception as e:
        logger.error(f"Error in check_quality: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/fix_issues/<int:result_id>', methods=['POST'])
@login_required
def fix_issues(result_id):
    """Memperbaiki masalah kualitas data klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'ID hasil klasterisasi tidak ditemukan'})
            
        clustering_manager = get_clustering_manager()
        success, message = clustering_manager.fix_data_quality_issues(result_id)
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"Error in fix_issues: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e), 'trace': traceback.format_exc()})

@app.route('/klasterisasi/optimize/<int:result_id>', methods=['POST'])
@login_required
def optimize_clustering(result_id):
    """Mengoptimalkan data klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'ID hasil klasterisasi tidak ditemukan'})
            
        clustering_manager = get_clustering_manager()
        success, message = clustering_manager.optimize_clustering_data(result_id)
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"Error in optimize_clustering: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e), 'trace': traceback.format_exc()})

@app.route('/klasterisasi/compare')
@login_required
def compare_results():
    """Membandingkan beberapa hasil klasterisasi"""
    # Dapatkan daftar ID hasil klasterisasi dari query parameter
    result_ids = request.args.getlist('ids', type=int)
    
    if not result_ids or len(result_ids) < 2:
        flash('Pilih minimal dua hasil klasterisasi untuk dibandingkan', 'warning')
        return redirect(url_for('klasterisasi'))
    
    try:
        clustering_manager = get_clustering_manager()
        comparison_data = clustering_manager.get_comparison_data(result_ids)
        
        return render_template('compare_results.html', comparison=comparison_data, result_ids=result_ids)
    except Exception as e:
        logger.error(f"Error in compare_results: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan saat membandingkan: {str(e)}', 'danger')
        return redirect(url_for('klasterisasi'))

# Tab 3: Analisis Karakteristik Klaster
@app.route('/klasterisasi/karakteristik/<int:result_id>')
@login_required
def cluster_characteristics(result_id):
    """Menampilkan halaman karakteristik klaster"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
        result = cur.fetchone()
        
        if not result:
            flash('ID hasil klasterisasi tidak ditemukan', 'danger')
            return redirect(url_for('klasterisasi'))
        
        # Dapatkan data dari ClusteringManager
        clustering_manager = get_clustering_manager()
        characteristics = clustering_manager.get_cluster_characteristics(result_id)
        
        return render_template('karakteristik_klaster.html', 
                              result=result, 
                              characteristics=characteristics)
                              
    except Exception as e:
        logger.error(f"Error in cluster_characteristics: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        return redirect(url_for('klasterisasi'))

# Tab 4: Evaluasi Standar
@app.route('/klasterisasi/evaluasi/<int:result_id>')
@login_required
def evaluate_clusters(result_id):
    """Menampilkan halaman evaluasi standar klaster"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
        result = cur.fetchone()
        
        if not result:
            flash('ID hasil klasterisasi tidak ditemukan', 'danger')
            return redirect(url_for('klasterisasi'))
        
        # Dapatkan data dari ClusteringManager
        clustering_manager = get_clustering_manager()
        evaluation_data = clustering_manager.get_cluster_evaluation_data(result_id)
        
        return render_template('evaluasi_klaster.html', 
                              result=result, 
                              evaluation=evaluation_data)
                              
    except Exception as e:
        logger.error(f"Error in evaluate_clusters: {str(e)}", exc_info=True)
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        return redirect(url_for('klasterisasi'))

###############################################################################
# ROUTE - Fitur Data Wilayah (akan diimplementasikan di masa mendatang)
###############################################################################

"""
# Daftar lengkap kecamatan
@app.route('/wilayah/<int:result_id>')
def wilayah(result_id):
    # Implementasi daftar wilayah kecamatan
    pass

# Detail kualitas pendidikan kecamatan
@app.route('/wilayah/<int:result_id>/<int:kecamatan_id>')
def wilayah_detail(result_id, kecamatan_id):
    # Implementasi detail wilayah kecamatan
    pass
"""

###############################################################################
# ROUTE - Fitur Peta Klaster Pendidikan (akan diimplementasikan di masa mendatang)
###############################################################################

"""
@app.route('/peta/<int:result_id>')
def peta_klaster(result_id):
    # Implementasi peta klaster
    pass
"""

###############################################################################
# ROUTE - Fitur Statistik Pendidikan (akan diimplementasikan di masa mendatang)
###############################################################################

"""
@app.route('/statistik/<int:result_id>')
def statistik(result_id):
    # Implementasi statistik pendidikan
    pass
"""

###############################################################################
# API ROUTES - Klasterisasi
###############################################################################

@app.route('/klasterisasi/api/results')
def api_results():
    """API untuk mendapatkan daftar semua hasil klasterisasi"""
    try:
        clustering_manager = get_clustering_manager()
        results = clustering_manager.get_available_clustering_results()
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Error in api_results: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/clusters/<int:result_id>')
def api_clusters(result_id):
    """API untuk mendapatkan informasi cluster dari hasil klasterisasi tertentu"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        # Query cluster data
        cur.execute("""
            SELECT cluster, COUNT(*) as count 
            FROM clustering_data 
            WHERE result_id = %s 
            GROUP BY cluster
            ORDER BY cluster
        """, [result_id])
        
        clusters = {}
        for row in cur.fetchall():
            clusters[row['cluster']] = row['count']
        
        return jsonify({'clusters': clusters})
    except Exception as e:
        logger.error(f"Error in api_clusters: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/characteristics/<int:result_id>')
def api_characteristics(result_id):
    """API untuk mendapatkan karakteristik cluster"""
    try:
        # Filter berdasarkan cluster
        cluster = request.args.get('cluster', type=int)
        
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        clustering_manager = get_clustering_manager()
        
        # Periksa apakah data tersedia
        cur.execute("SELECT COUNT(*) as count FROM clustering_data WHERE result_id = %s", [result_id])
        count = cur.fetchone()['count']
        if count == 0:
            return jsonify({'error': f'No clustering data found for result_id={result_id}'}), 404
        
        # Get characteristics
        characteristics = clustering_manager.get_cluster_characteristics(result_id)
        
        # Filter jika parameter cluster diberikan
        if cluster is not None:
            characteristics = [char for char in characteristics if char['cluster'] == cluster]
            
            # Jika tidak ada data untuk cluster yang diminta
            if not characteristics:
                return jsonify({'error': f'No characteristics data found for cluster={cluster}'}), 404
        
        return jsonify({'characteristics': characteristics})
    except Exception as e:
        # Log error detail
        logger.error(f"Error in api_characteristics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/klasterisasi/api/detailed_characteristics/<int:result_id>')
def api_detailed_characteristics(result_id):
    """API untuk mendapatkan karakteristik cluster dengan detail lengkap"""
    try:
        # Filter berdasarkan cluster
        cluster = request.args.get('cluster', type=int)
       
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
           
        # Dapatkan data karakteristik dari database
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT * FROM cluster_characteristics
            WHERE result_id = %s
            ORDER BY cluster
        """, [result_id])
        
        characteristics_data = cur.fetchall()
        
        if not characteristics_data:
            return jsonify({'error': 'Karakteristik klaster tidak ditemukan'}), 404
        
        # Konversi hasil cursor menjadi list of dictionaries
        characteristics = []
        for char in characteristics_data:
            # Konversi row dari cursor ke dictionary
            char_dict = dict(char)
            
            # Get strengths and weaknesses
            fitur_tinggi = char_dict['fitur_tinggi'].split(',') if char_dict['fitur_tinggi'] else []
            fitur_rendah = char_dict['fitur_rendah'].split(',') if char_dict['fitur_rendah'] else []
            
            # Get members
            anggota = char_dict['anggota'].split(',') if char_dict['anggota'] else []
            
            # Tambahkan ke list dengan format yang sesuai dengan yang diharapkan frontend
            characteristics.append({
                "cluster": char_dict['cluster'],
                "jumlah_anggota": char_dict['jumlah_anggota'],
                "medoid_name": char_dict['medoid_name'],
                "anggota": anggota,
                "standar_terpenuhi": char_dict['standar_terpenuhi'],
                "kualitas_pendidikan": char_dict['kualitas_pendidikan'],
                "x1_avg": char_dict['x1_avg'],
                "x2_avg": char_dict['x2_avg'],
                "x3_avg": char_dict['x3_avg'],
                "x4_avg": char_dict['x4_avg'],
                "x5_avg": char_dict['x5_avg'],
                "x6_avg": char_dict['x6_avg'],
                "x7_avg": char_dict['x7_avg'],
                "fitur_tinggi": fitur_tinggi,
                "fitur_rendah": fitur_rendah,
                "deskripsi": char_dict['deskripsi'],
                "interpretasi": char_dict['interpretasi'],
                "rekomendasi": char_dict['rekomendasi']
            })
        
        # Filter jika parameter cluster diberikan
        if cluster is not None:
            characteristics = [char for char in characteristics if char['cluster'] == cluster]
           
            # Jika tidak ada data untuk cluster yang diminta
            if not characteristics:
                return jsonify({'error': f'No characteristics data found for cluster={cluster}'}), 404
       
        return jsonify({'characteristics': characteristics})
    except Exception as e:
        logger.error(f"Error in api_detailed_characteristics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    

@app.route('/klasterisasi/api/stats/<int:result_id>')
def api_stats(result_id):
    """API untuk mendapatkan statistik indikator per cluster"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, jenjang FROM clustering_results WHERE id = %s", [result_id])
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        jenjang = result['jenjang']
            
        clustering_manager = get_clustering_manager()
        evaluation_data = clustering_manager.get_cluster_evaluation_data(result_id)
        
        return jsonify({
            'evaluation_data': evaluation_data,
            'jenjang': jenjang
        })
    except Exception as e:
        logger.error(f"Error in api_stats: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/kecamatan/<int:result_id>')
def api_kecamatan(result_id):
    """API untuk mendapatkan daftar kecamatan dari hasil klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        cur.execute("""
            SELECT DISTINCT k.id, k.nama_kecamatan 
            FROM clustering_data cd
            JOIN kecamatan k ON cd.kecamatan_id = k.id
            WHERE cd.result_id = %s
            ORDER BY k.nama_kecamatan
        """, [result_id])
        
        kecamatan = []
        for row in cur.fetchall():
            kecamatan.append({
                'id': row['id'],
                'nama_kecamatan': row['nama_kecamatan']
            })
        
        return jsonify({'kecamatan': kecamatan})
    except Exception as e:
        logger.error(f"Error in api_kecamatan: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/kecamatan_data/<int:result_id>')
def api_kecamatan_data(result_id):
    """API untuk mendapatkan data kecamatan dari hasil klasterisasi"""
    try:
        # Parameter filter
        cluster = request.args.get('cluster', default='')
        sort_by = request.args.get('sort_by', default='kecamatan')
        search = request.args.get('search', default='')
        
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        # Validasi sort_by
        valid_sort_fields = ['nama', 'kecamatan', 'cluster', 'rank', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']
        if sort_by not in valid_sort_fields:
            sort_by = 'kecamatan'  # Default jika tidak valid
            
        clustering_manager = get_clustering_manager()
        kecamatan_data = clustering_manager.get_kecamatan_data(
            result_id, 
            int(cluster) if cluster and cluster.isdigit() else None, 
            sort_by
        )
        
        # Terapkan filter pencarian jika ada
        if search:
            search = search.lower()
            kecamatan_data = [item for item in kecamatan_data 
                             if search in item['nama_kecamatan'].lower()]
        
        return jsonify({'kecamatan': kecamatan_data})
    except Exception as e:
        logger.error(f"Error in api_kecamatan_data: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/kecamatan_detail/<int:result_id>/<int:kecamatan_id>')
def api_kecamatan_detail(result_id, kecamatan_id):
    """API untuk mendapatkan detail kecamatan beserta sekolah di dalamnya"""
    try:
        # Validasi result_id dan kecamatan_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        cur.execute("SELECT id FROM kecamatan WHERE id = %s", [kecamatan_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID kecamatan tidak ditemukan'}), 404
        
        # Dapatkan data menggunakan ClusteringManager
        clustering_manager = get_clustering_manager()
        kecamatan_detail = clustering_manager.get_kecamatan_detail(result_id, kecamatan_id)
        
        if not kecamatan_detail:
            return jsonify({'error': 'Data kecamatan tidak ditemukan untuk hasil klasterisasi ini'}), 404
        
        return jsonify(kecamatan_detail)
    except Exception as e:
        logger.error(f"Error in api_kecamatan_detail: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/sekolah/<int:result_id>')
def api_sekolah(result_id):
    """API untuk mendapatkan data sekolah dari hasil klasterisasi"""
    try:
        # Parameter filter
        kecamatan = request.args.get('kecamatan', default='')
        status = request.args.get('status', default='')
        sort_by = request.args.get('sort_by', default='nama_sekolah')
        search = request.args.get('search', default='')
        
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, jenjang FROM clustering_results WHERE id = %s", [result_id])
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        jenjang = result['jenjang']
        
        # Validasi kecamatan_id jika ada
        if kecamatan and kecamatan.isdigit():
            cur.execute("SELECT id FROM kecamatan WHERE id = %s", [int(kecamatan)])
            if not cur.fetchone():
                return jsonify({'error': 'ID kecamatan tidak ditemukan'}), 404
                
        # Validasi sort_by
        valid_sort_fields = ['nama_sekolah', 'nama', 'kecamatan', 'cluster', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'jumlah_siswa', 'jumlah_guru', 'jumlah_rombel']
        if sort_by not in valid_sort_fields:
            sort_by = 'nama_sekolah'  # Default jika tidak valid
            
        clustering_manager = get_clustering_manager()
        sekolah_data = clustering_manager.get_sekolah_data(
            result_id, 
            int(kecamatan) if kecamatan and kecamatan.isdigit() else None, 
            status, 
            sort_by
        )
        
        # Terapkan filter pencarian jika ada
        if search:
            search = search.lower()
            sekolah_data = [item for item in sekolah_data
                           if search in item['nama_sekolah'].lower()]
        
        return jsonify({
            'sekolah': sekolah_data,
            'jenjang': jenjang,
            'total': len(sekolah_data)
        })
    except Exception as e:
        logger.error(f"Error in api_sekolah: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/sekolah_detail/<int:result_id>/<int:sekolah_id>')
def api_sekolah_detail(result_id, sekolah_id):
    """API untuk mendapatkan detail sekolah"""
    try:
        # Validasi result_id dan sekolah_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        cur.execute("SELECT id FROM sekolah_data WHERE id = %s AND result_id = %s", [sekolah_id, result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID sekolah tidak ditemukan untuk hasil klasterisasi ini'}), 404
        
        # Dapatkan data menggunakan ClusteringManager
        clustering_manager = get_clustering_manager()
        sekolah_detail = clustering_manager.get_sekolah_detail(result_id, sekolah_id)
        
        if not sekolah_detail:
            return jsonify({'error': 'Data sekolah tidak ditemukan'}), 404
        
        return jsonify(sekolah_detail)
    except Exception as e:
        logger.error(f"Error in api_sekolah_detail: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/evaluasi/<int:result_id>')
def api_evaluasi(result_id):
    """API untuk mendapatkan evaluasi indikator dari hasil klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, jenjang FROM clustering_results WHERE id = %s", [result_id])
        result_info = cur.fetchone()
        
        if not result_info:
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        # Dapatkan data dari ClusteringManager
        clustering_manager = get_clustering_manager()
        evaluation_data = clustering_manager.get_cluster_evaluation_data(result_id)
        
        return jsonify(evaluation_data)
    except Exception as e:
        logger.error(f"Error in api_evaluasi: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/map_data/<int:result_id>')
def api_map_data(result_id):
    """API untuk mendapatkan data peta klasterisasi"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        clustering_manager = get_clustering_manager()
        map_data = clustering_manager.get_cluster_data_for_map(result_id)
        
        return jsonify(map_data)
    except Exception as e:
        logger.error(f"Error in api_map_data: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/klasterisasi/api/recommendations/<int:result_id>')
def api_recommendations(result_id):
    """API untuk mendapatkan rekomendasi perbaikan"""
    try:
        # Validasi result_id
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM clustering_results WHERE id = %s", [result_id])
        if not cur.fetchone():
            return jsonify({'error': 'ID hasil klasterisasi tidak ditemukan'}), 404
            
        clustering_manager = get_clustering_manager()
        recommendations = clustering_manager.get_recommendation_summary(result_id)
        
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Error in api_recommendations: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(debug=True)