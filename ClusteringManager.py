"""
Module untuk pengelolaan data hasil klasterisasi wilayah berdasarkan indikator kualitas pendidikan.
Focus: Impor dan manajemen data hasil klasterisasi dari CSV, analisis karakteristik, dan evaluasi standar.
"""

import os
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
import pymysql
import MySQLdb.cursors
from typing import Dict, List, Tuple, Union, Optional, Any

# Install pymysql sebagai MySQLdb
pymysql.install_as_MySQLdb()

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("clustering.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("clustering")

# Konstanta untuk definisi indikator
INDICATORS = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']

INDICATOR_DESCRIPTIONS = {
    'x1': 'Rasio Siswa per Ruang Kelas',
    'x2': 'Rasio Siswa per Guru',
    'x3': 'Rasio Siswa per Rombel',
    'x4': 'Rasio Rombel per Sekolah',
    'x5': 'Persentase Ketersediaan Perpustakaan',
    'x6': 'Persentase Ketersediaan Laboratorium',
    'x7': 'Persentase Ketersediaan Ruang Kelas'
}

INDICATOR_CONTEXTS = {
    'x1': 'Rasio siswa per ruang kelas yang ideal memungkinkan pembelajaran yang lebih efektif dan interaksi yang lebih baik antara guru dan siswa',
    'x2': 'Rasio siswa per guru yang ideal memungkinkan perhatian yang lebih personal dan beban kerja guru yang lebih seimbang',
    'x3': 'Rasio siswa per rombel yang ideal menciptakan dinamika kelas yang lebih interaktif dan kondusif untuk pembelajaran',
    'x4': 'Jumlah rombel per sekolah yang proporsional memungkinkan manajemen sekolah yang efisien dan penggunaan sumber daya yang optimal',
    'x5': 'Ketersediaan perpustakaan mendukung literasi dan akses siswa ke berbagai sumber belajar',
    'x6': 'Ketersediaan laboratorium mendukung pembelajaran berbasis eksperimen dan pengembangan keterampilan praktis',
    'x7': 'Ketersediaan ruang kelas yang memadai mendukung proses belajar mengajar yang optimal'
}

class ClusteringManager:
    """
    Kelas untuk mengelola data hasil klasterisasi yang diimpor dari file CSV.
    """
    
    def __init__(self, db=None):
        """
        Inisialisasi manajer klasterisasi.
        
        Args:
            db: Instance MySQL dari flask_mysqldb
        """
        self.db = db
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'data', 'exports')
        os.makedirs(self.output_dir, exist_ok=True)
        self.standar_indikator = self._load_standar_indikator()
        
        
        
    def _load_standar_indikator(self) -> Dict[str, Dict[str, Any]]:
        """
        Memuat standar indikator dari database dengan penanganan kesalahan yang lebih baik
        dan caching untuk mengurangi query database berulang.
        
        Returns:
            dict: Standar indikator untuk evaluasi
        """
        try:
            # Cek apakah cache masih valid (cache berlaku 30 menit)
            current_time = datetime.now()
            cache_key = 'standar_indikator'
            
            # Cek apakah memiliki cache dan masih valid
            if hasattr(self, '_cache_time') and hasattr(self, '_cache_data'):
                cache_age = (current_time - self._cache_time).total_seconds()
                if cache_age < 1800:  # 30 menit dalam detik
                    logger.debug("Menggunakan standar indikator dari cache (berumur %d detik)", cache_age)
                    return self._cache_data.get(cache_key, self._get_default_standar_indikator())
            
            # Jika tidak ada koneksi database, gunakan nilai default
            if not self.db:
                logger.warning("Tidak ada koneksi database, menggunakan nilai standar default")
                default_data = self._get_default_standar_indikator()
                
                # Simpan di cache
                if not hasattr(self, '_cache_data'):
                    self._cache_data = {}
                if not hasattr(self, '_cache_time'):
                    self._cache_time = current_time
                    
                self._cache_data[cache_key] = default_data
                return default_data
                
            try:
                # Get cursor
                cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
                
                # Query standar indikator
                cur.execute("SELECT * FROM standar_indikator")
                standar_list = cur.fetchall()
                
                # Jika tidak ada data standar dalam database, gunakan default
                if not standar_list:
                    logger.warning("Tidak ada data standar indikator dalam database, menggunakan nilai default")
                    default_data = self._get_default_standar_indikator()
                    
                    # Simpan di cache
                    if not hasattr(self, '_cache_data'):
                        self._cache_data = {}
                    self._cache_time = current_time
                    self._cache_data[cache_key] = default_data
                    
                    return default_data
                
                standar = {}
                
                # Konversi ke format dictionary yang lebih mudah digunakan
                for item in standar_list:
                    indikator = item['indikator']
                    jenjang = item['jenjang']
                    
                    if indikator not in standar:
                        standar[indikator] = {}
                    
                    if jenjang == 'all':
                        # Standar yang berlaku untuk semua jenjang
                        standar[indikator].update({
                            'min': item['nilai_min'],
                            'max': item['nilai_max'],
                            'ideal': item['nilai_ideal'],
                            'description': item['deskripsi']
                        })
                    else:
                        # Standar spesifik untuk jenjang tertentu
                        key_min = f'min_{jenjang.lower()}'
                        key_max = f'max_{jenjang.lower()}'
                        key_ideal = f'ideal_{jenjang.lower()}'
                        
                        standar[indikator].update({
                            key_min: item['nilai_min'],
                            key_max: item['nilai_max'],
                            key_ideal: item['nilai_ideal']
                        })
                
                # Verifikasi bahwa semua indikator ada dan memiliki nilai yang diperlukan
                for indikator in INDICATORS:
                    if indikator not in standar:
                        logger.warning(f"Indikator {indikator} tidak ditemukan dalam database, menggunakan nilai default")
                        default_standar = self._get_default_standar_indikator()
                        standar[indikator] = default_standar[indikator]
                
                # Ganti karakter unicode dengan ascii untuk menghindari error encoding
                for indikator in standar:
                    if 'description' in standar[indikator]:
                        # Ganti karakter unicode "≤" dengan "<="
                        standar[indikator]['description'] = standar[indikator]['description'].replace('≤', '<=')
                
                # Logging untuk debugging - gunakan safe logging untuk menghindari error unicode
                try:
                    logger.info(f"Standar indikator berhasil dimuat: {standar}")
                except UnicodeEncodeError:
                    logger.info("Standar indikator berhasil dimuat (detail dihilangkan karena masalah encoding)")
                
                # Simpan di cache
                if not hasattr(self, '_cache_data'):
                    self._cache_data = {}
                self._cache_time = current_time
                self._cache_data[cache_key] = standar
                
                return standar
                
            except Exception as e:
                logger.error(f"Error loading standar indikator dari database: {str(e)}", exc_info=True)
                logger.info("Menggunakan nilai standar default")
                
                # Cek cache lama jika ada
                if hasattr(self, '_cache_data') and cache_key in self._cache_data:
                    logger.info("Menggunakan cache lama karena error")
                    return self._cache_data[cache_key]
                    
                default_data = self._get_default_standar_indikator()
                
                # Simpan di cache
                if not hasattr(self, '_cache_data'):
                    self._cache_data = {}
                self._cache_time = current_time
                self._cache_data[cache_key] = default_data
                
                return default_data
        
        except Exception as e:
            logger.error(f"Error yang tidak ditangani di _load_standar_indikator: {str(e)}", exc_info=True)
            # Fallback ke nilai hardcoded jika semua cara gagal
            return self._get_default_standar_indikator()
        
        

    def _get_default_standar_indikator(self) -> Dict[str, Dict[str, Any]]:
        """
        Mendapatkan nilai default standar indikator jika tidak bisa dimuat dari database.
        
        Returns:
            dict: Standar indikator default
        """
        return {
            'x1': {
                'min': 0, 
                'max': 32, 
                'ideal': 32, 
                'description': 'Ideal jika rasio <= 32 siswa/ruang kelas (Permendiknas No. 41 Tahun 2007)'
            },
            'x2': {
                'min': 0, 
                'max_sma': 20, 
                'max_smk': 15, 
                'ideal_sma': 20, 
                'ideal_smk': 15, 
                'description': 'Ideal jika rasio <= 20 untuk SMA, <= 15 untuk SMK (PP No. 74 Tahun 2008)'
            },
            'x3': {
                'min': 0, 
                'max': 32, 
                'ideal': 32, 
                'description': 'Ideal jika rasio <= 32 siswa/rombel (Permendiknas No. 41 Tahun 2007)'
            },
            'x4': {
                'min_sma': 3, 
                'max_sma': 27, 
                'min_smk': 3, 
                'max_smk': 48, 
                'ideal_sma': 15, 
                'ideal_smk': 24, 
                'description': 'Minimal 3 dan maksimal 27 untuk SMA, minimal 3 dan maksimal 48 untuk SMK (Permendiknas No. 24 Tahun 2007 dan No. 40 Tahun 2008)'
            },
            'x5': {
                'min': 0, 
                'max': 1, 
                'ideal': 1, 
                'description': 'Ideal jika semua sekolah memiliki perpustakaan (Nilai 1 berarti 100% sekolah memiliki perpustakaan)'
            },
            'x6': {
                'min': 0, 
                'max': 1, 
                'ideal': 1, 
                'description': 'Ideal jika semua sekolah memiliki laboratorium (Nilai 1 berarti 100% sekolah memiliki laboratorium)'
            },
            'x7': {
                'min': 0, 
                'max': 1, 
                'ideal': 1, 
                'description': 'Ideal jika semua sekolah memiliki ruang kelas yang memadai (Nilai 1 berarti 100% sekolah memiliki ruang kelas yang memadai)'
            }
        }


    def _normalize_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalisasi dan standardisasi nama kolom CSV.
        
        Args:
            df: DataFrame yang akan dinormalisasi kolomnya
            
        Returns:
            DataFrame: DataFrame dengan kolom yang sudah dinormalisasi
        """
        try:
            # Simpan kolom original untuk log
            original_columns = list(df.columns)
            
            # Konversi nama kolom menjadi lowercase dan ganti spasi dengan underscore
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Mapping untuk nama kolom standar
            column_mapping = {
                # Mapping kecamatan
                'kecamatan': 'kecamatan',
                'kec': 'kecamatan',
                'kec.': 'kecamatan',
                'nama_kecamatan': 'kecamatan',
                'nmkec': 'kecamatan',
                'nama_kec': 'kecamatan',
                'namakecamatan': 'kecamatan',
                'namakec': 'kecamatan',
                # Mapping cluster
                'cluster': 'cluster',
                'klaster': 'cluster',
                'kelompok': 'cluster',
                'cluster_id': 'cluster',
                'clusterid': 'cluster',
                'klasterid': 'cluster',
                'id_cluster': 'cluster',
                'idcluster': 'cluster',
                # Mapping medoid
                'is_medoid': 'is_medoid',
                'medoid': 'is_medoid',
                'is_center': 'is_medoid',
                'iscenter': 'is_medoid',
                'center': 'is_medoid',
                'pusat': 'is_medoid',
                'is_pusat': 'is_medoid',
                # Mapping indikator berdasarkan nama deskriptif
                'rasio_siswa_ruang_kelas': 'x1',
                'rasio_siswa_per_ruang_kelas': 'x1',
                'rasio_siswa_guru': 'x2',
                'rasio_siswa_per_guru': 'x2',
                'rasio_siswa_rombel': 'x3',
                'rasio_siswa_per_rombel': 'x3',
                'rasio_rombel_sekolah': 'x4',
                'rasio_rombel_per_sekolah': 'x4',
                'persentase_perpustakaan': 'x5',
                'persen_perpustakaan': 'x5',
                'perpustakaan': 'x5',
                'persentase_laboratorium': 'x6',
                'persen_laboratorium': 'x6',
                'laboratorium': 'x6',
                'persentase_ruang_kelas': 'x7',
                'persen_ruang_kelas': 'x7',
                'ruang_kelas': 'x7',
                # Mapping dengan format x1_nama
                'x1_rasio_siswa_ruang_kelas': 'x1',
                'x2_rasio_siswa_guru': 'x2',
                'x3_rasio_siswa_rombel': 'x3',
                'x4_rasio_rombel_sekolah': 'x4',
                'x5_persentase_perpustakaan': 'x5',
                'x6_persentase_laboratorium': 'x6',
                'x7_persentase_ruang_kelas': 'x7',
                # Mapping data sekolah
                'nama_sekolah': 'nama_sekolah',
                'sekolah': 'nama_sekolah',
                'nama': 'nama_sekolah',
                'alamat': 'alamat',
                'status': 'status',
                'jenjang': 'jenjang',
                'jumlah_siswa': 'jumlah_siswa',
                'jml_siswa': 'jumlah_siswa',
                'siswa': 'jumlah_siswa',
                'jumlah_guru': 'jumlah_guru',
                'jml_guru': 'jumlah_guru',
                'guru': 'jumlah_guru',
                'jumlah_rombel': 'jumlah_rombel',
                'jml_rombel': 'jumlah_rombel',
                'rombel': 'jumlah_rombel',
                # Mapping dimensi untuk visualisasi
                'dim1': 'dim1',
                'dim_1': 'dim1',
                'dimensi_1': 'dim1',
                'pc1': 'dim1',
                'dim2': 'dim2',
                'dim_2': 'dim2',
                'dimensi_2': 'dim2',
                'pc2': 'dim2'
            }
            
            # Penanganan khusus untuk x1-x7
            for i in range(1, 8):
                column_mapping[f'x_{i}'] = f'x{i}'
                column_mapping[f'x.{i}'] = f'x{i}'
                column_mapping[f'x-{i}'] = f'x{i}'
                column_mapping[f'indikator_{i}'] = f'x{i}'
                column_mapping[f'indikator{i}'] = f'x{i}'
                column_mapping[f'ind_{i}'] = f'x{i}'
                column_mapping[f'ind{i}'] = f'x{i}'
            
            # Log untuk debugging
            logger.debug(f"Kolom original: {original_columns}")
            logger.debug(f"Kolom setelah lowercase dan replace space: {list(df.columns)}")
            
            # Terapkan mapping untuk kolom yang ada
            df = df.rename(columns={col: column_mapping[col] for col in df.columns if col in column_mapping})
            logger.debug(f"Kolom setelah mapping: {list(df.columns)}")
            
            # Pastikan tipe data kolom numerik
            numerical_columns = [f'x{i}' for i in range(1, 8)]
            if 'cluster' in df.columns:
                numerical_columns.append('cluster')
            
            for col in numerical_columns:
                if col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        nan_count = df[col].isna().sum()
                        if nan_count > 0:
                            logger.warning(f"Kolom {col} memiliki {nan_count} nilai yang tidak dapat dikonversi ke numerik")
                    except Exception as e:
                        logger.error(f"Error mengkonversi kolom {col} ke numerik: {str(e)}")
            
            # Konversi kolom is_medoid ke boolean jika ada
            if 'is_medoid' in df.columns:
                df['is_medoid'] = df['is_medoid'].map(
                    lambda x: str(x).lower() in ('true', 't', 'yes', 'y', '1', '1.0', 'true') 
                    if not pd.isna(x) else False
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error saat normalisasi kolom CSV: {str(e)}", exc_info=True)
            # Jika terjadi error, kembalikan DataFrame asli
            return df
    
    
    
    def _match_kecamatan_names(self, cur, kecamatan_list: List[str]) -> Tuple[Dict[str, int], List[str]]:
        """
        Pencocokan nama kecamatan dengan data di database dengan fleksibilitas yang ditingkatkan
        
        Args:
            cur: Database cursor
            kecamatan_list: Daftar nama kecamatan dari CSV
            
        Returns:
            tuple: (kecamatan_id_mapping, missing_kecamatan)
        """
        try:
            # Filter nilai None dan string kosong
            kecamatan_list = [k for k in kecamatan_list if k and not pd.isna(k)]
            
            # Normalisasi nama kecamatan dari CSV
            kecamatan_list_normalized = []
            for kec in kecamatan_list:
                if isinstance(kec, str):
                    # Konversi ke lowercase dan hilangkan whitespace di awal/akhir
                    kec_norm = kec.lower().strip()
                    kecamatan_list_normalized.append(kec_norm)
                else:
                    # Jika bukan string, gunakan apa adanya
                    kecamatan_list_normalized.append(kec)
            
            # Ambil data kecamatan dari database
            cur.execute("SELECT id, nama_kecamatan FROM kecamatan")
            kecamatan_db = cur.fetchall()
            
            if not kecamatan_db:
                logger.warning("Tidak ada data kecamatan di database, tidak bisa melakukan pencocokan")
                return {}, kecamatan_list
            
            # Buat mapping dengan variasi untuk pencocokan yang lebih baik
            kecamatan_mapping = {}  # Original name -> id
            kecamatan_names_lower = {}  # Lowercase name -> id
            kecamatan_names_normalized = {}  # Normalized name (no prefix) -> id
            
            # Prefiks/sufiks umum untuk normalisasi
            prefixes = ['kab.', 'kab ', 'kabupaten ', 'kota ', 'kota.', 'kec.', 'kec ', 'kecamatan ']
            
            for kec in kecamatan_db:
                name = kec['nama_kecamatan']
                kec_id = kec['id']
                kecamatan_mapping[name] = kec_id
                
                # Simpan versi lowercase
                name_lower = name.lower().strip()
                kecamatan_names_lower[name_lower] = kec_id
                
                # Simpan versi tanpa spasi
                kecamatan_names_lower[name_lower.replace(' ', '')] = kec_id
                
                # Simpan versi dengan prefiks/sufiks yang dihapus
                for prefix in prefixes:
                    if name_lower.startswith(prefix):
                        normalized = name_lower[len(prefix):].strip()
                        kecamatan_names_normalized[normalized] = kec_id
            
            # Informasi debug
            logger.debug(f"Total kecamatan di database: {len(kecamatan_db)}")
            logger.debug(f"Total kecamatan di CSV: {len(kecamatan_list)}")
            
            # Buat mapping untuk kecamatan di CSV
            kecamatan_id_mapping = {}
            missing_kecamatan = []
            
            # Track metode pencocokan untuk statistik
            match_stats = {'exact': 0, 'lowercase': 0, 'nospace': 0, 'normalized': 0, 'substring': 0, 'fuzzy': 0, 'missing': 0}
            
            for i, kec in enumerate(kecamatan_list):
                original_kec = kec
                # Skip jika sudah diproses
                if kec in kecamatan_id_mapping:
                    continue
                    
                # Normalisasi
                if isinstance(kec, str):
                    kec_lower = kec.lower().strip()
                    kec_nospace = kec_lower.replace(' ', '')
                else:
                    logger.warning(f"Kecamatan tidak valid: {kec} (bukan string)")
                    missing_kecamatan.append(kec)
                    match_stats['missing'] += 1
                    continue
                
                # Coba pencocokan langsung
                if kec in kecamatan_mapping:
                    kecamatan_id_mapping[kec] = kecamatan_mapping[kec]
                    match_stats['exact'] += 1
                    logger.debug(f"Exact match for '{kec}'")
                    continue
                
                # Coba pencocokan lowercase
                if kec_lower in kecamatan_names_lower:
                    kecamatan_id_mapping[kec] = kecamatan_names_lower[kec_lower]
                    match_stats['lowercase'] += 1
                    logger.debug(f"Lowercase match for '{kec}'")
                    continue
                
                # Coba tanpa spasi
                if kec_nospace in kecamatan_names_lower:
                    kecamatan_id_mapping[kec] = kecamatan_names_lower[kec_nospace]
                    match_stats['nospace'] += 1
                    logger.debug(f"No-space match for '{kec}'")
                    continue
                
                # Coba menghapus prefiks umum
                normalized_kec = kec_lower
                for prefix in prefixes:
                    if normalized_kec.startswith(prefix):
                        normalized_kec = normalized_kec[len(prefix):].strip()
                        break
                
                if normalized_kec in kecamatan_names_normalized:
                    kecamatan_id_mapping[kec] = kecamatan_names_normalized[normalized_kec]
                    match_stats['normalized'] += 1
                    logger.debug(f"Normalized match for '{kec}' as '{normalized_kec}'")
                    continue
                
                # Coba pencocokan substring
                matched = False
                for db_name_lower, kec_id in kecamatan_names_lower.items():
                    # Skip nama sangat pendek untuk menghindari false match
                    if len(db_name_lower) < 3 or len(kec_lower) < 3:
                        continue
                        
                    # Cek apakah salah satu adalah substring dari yang lain
                    if kec_lower in db_name_lower or db_name_lower in kec_lower:
                        kecamatan_id_mapping[kec] = kec_id
                        match_stats['substring'] += 1
                        logger.debug(f"Substring match for '{kec}' with '{db_name_lower}'")
                        matched = True
                        break
                
                # Jika tidak ditemukan dengan metode substring, coba Levenshtein distance jika tersedia
                if not matched:
                    try:
                        import Levenshtein
                        best_match = None
                        best_match_id = None
                        best_distance = float('inf')
                        
                        for db_name_lower, kec_id in kecamatan_names_lower.items():
                            # Skip nama sangat pendek
                            if len(db_name_lower) < 3 or len(kec_lower) < 3:
                                continue
                                
                            distance = Levenshtein.distance(kec_lower, db_name_lower)
                            
                            # Terima jika jarak cukup kecil relatif terhadap panjang string
                            threshold = min(len(kec_lower), len(db_name_lower)) * 0.3
                            if distance <= threshold and distance < best_distance:
                                best_distance = distance
                                best_match = db_name_lower
                                best_match_id = kec_id
                        
                        if best_match:
                            kecamatan_id_mapping[kec] = best_match_id
                            match_stats['fuzzy'] += 1
                            logger.info(f"Fuzzy match for '{kec}' with '{best_match}' (distance={best_distance})")
                            matched = True
                    except ImportError:
                        # Fallback jika Levenshtein tidak tersedia - gunakan simple character overlap
                        best_match = None
                        best_match_id = None
                        best_overlap = 0
                        
                        for db_name_lower, kec_id in kecamatan_names_lower.items():
                            # Skip nama sangat pendek
                            if len(db_name_lower) < 3 or len(kec_lower) < 3:
                                continue
                            
                            # Hitung jumlah karakter yang sama
                            overlap = 0
                            for c in kec_lower:
                                if c in db_name_lower:
                                    overlap += 1
                            
                            # Normalisasi overlap berdasarkan panjang string
                            overlap_ratio = overlap / len(kec_lower) if len(kec_lower) > 0 else 0
                            
                            if overlap_ratio > 0.7 and overlap_ratio > best_overlap:
                                best_overlap = overlap_ratio
                                best_match = db_name_lower
                                best_match_id = kec_id
                        
                        if best_match:
                            kecamatan_id_mapping[kec] = best_match_id
                            match_stats['fuzzy'] += 1
                            logger.info(f"Character overlap match for '{kec}' with '{best_match}' (overlap={best_overlap:.2f})")
                            matched = True
                
                if not matched:
                    missing_kecamatan.append(original_kec)
                    match_stats['missing'] += 1
                    logger.warning(f"No match found for kecamatan '{kec}'")
            
            # Log statistik pencocokan
            logger.info(f"Kecamatan matching statistics: {match_stats}")
            logger.info(f"Matched {len(kecamatan_id_mapping)} out of {len(kecamatan_list)} kecamatan")
            
            # Jika ada mapping yang berhasil dibuat, gunakan untuk kecamatan dengan nama yang sama
            updated_mapping = {}
            for kec in kecamatan_list:
                if kec in kecamatan_id_mapping:
                    # Jika sudah ada mapping, gunakan
                    updated_mapping[kec] = kecamatan_id_mapping[kec]
                elif kec in missing_kecamatan:
                    # Coba cari kecamatan yang sudah berhasil dipetakan dengan nama yang sama
                    kec_lower = kec.lower().strip() if isinstance(kec, str) else None
                    if kec_lower:
                        found = False
                        for mapped_kec, mapped_id in kecamatan_id_mapping.items():
                            mapped_kec_lower = mapped_kec.lower().strip() if isinstance(mapped_kec, str) else None
                            if mapped_kec_lower and mapped_kec_lower == kec_lower:
                                updated_mapping[kec] = mapped_id
                                found = True
                                logger.info(f"Using existing mapping for '{kec}' based on '{mapped_kec}'")
                                break
                        
                        if not found:
                            # Tetap dalam missing jika tidak ada yang cocok
                            continue
            
            # Gabungkan mapping yang diperbarui dengan yang asli
            kecamatan_id_mapping.update(updated_mapping)
            
            # Perbarui missing_kecamatan berdasarkan mapping terbaru
            missing_kecamatan = [k for k in kecamatan_list if k not in kecamatan_id_mapping]
            
            return kecamatan_id_mapping, missing_kecamatan
            
        except Exception as e:
            logger.error(f"Error in _match_kecamatan_names: {str(e)}", exc_info=True)
            # Return empty mapping jika terjadi error
            return {}, kecamatan_list
    
    
    def _import_clustering_data(self, cur, df: pd.DataFrame, result_id: int, kecamatan_id_mapping: Dict[str, int]) -> int:
        """
        Import clustering data ke database dengan batch processing dan penanganan error yang ditingkatkan
        
        Args:
            cur: Database cursor
            df: DataFrame dengan data clustering
            result_id: ID hasil clustering
            kecamatan_id_mapping: Mapping nama kecamatan ke ID
            
        Returns:
            int: Jumlah record yang berhasil diinsert
        """
        try:
            # Persiapkan list untuk batch insert
            insert_rows = []
            clustering_data_count = 0
            error_count = 0
            
            # Log untuk debugging
            logger.info(f"Memulai import {len(df)} baris data dengan {len(kecamatan_id_mapping)} kecamatan mapping")
            
            # Proses setiap baris data
            for idx, row in df.iterrows():
                try:
                    # Ambil nama kecamatan
                    kecamatan_name = row['kecamatan']
                    
                    # Skip jika kecamatan adalah None atau NaN
                    if pd.isna(kecamatan_name) or kecamatan_name is None:
                        logger.warning(f"Baris {idx}: Kecamatan kosong atau NaN, dilewati")
                        error_count += 1
                        continue
                    
                    # Lewati jika kecamatan tidak ada dalam mapping
                    if kecamatan_name not in kecamatan_id_mapping:
                        logger.warning(f"Baris {idx}: Kecamatan '{kecamatan_name}' tidak ada dalam mapping, dilewati")
                        error_count += 1
                        continue
                        
                    kecamatan_id = kecamatan_id_mapping[kecamatan_name]
                    
                    # Parse boolean is_medoid
                    is_medoid = False
                    if 'is_medoid' in row:
                        try:
                            # Handle berbagai representasi boolean
                            if isinstance(row['is_medoid'], bool):
                                is_medoid = row['is_medoid']
                            elif isinstance(row['is_medoid'], (int, float)):
                                is_medoid = bool(row['is_medoid'])
                            elif isinstance(row['is_medoid'], str):
                                is_medoid = row['is_medoid'].lower() in ('true', 't', 'yes', 'y', '1')
                        except Exception as e:
                            logger.warning(f"Baris {idx}: Error parsing is_medoid untuk {kecamatan_name}: {str(e)}")
                    
                    # Validasi nilai numerik yang diperlukan
                    numeric_cols = [f'x{i}' for i in range(1, 8)] + ['cluster']
                    skip_row = False
                    for col in numeric_cols:
                        if col not in row or pd.isna(row[col]):
                            logger.warning(f"Baris {idx}: Kolom '{col}' kosong atau NaN untuk {kecamatan_name}, dilewati")
                            skip_row = True
                            break
                        
                        # Pastikan nilai adalah numerik
                        try:
                            float(row[col])
                        except (TypeError, ValueError):
                            logger.warning(f"Baris {idx}: Kolom '{col}' bukan numerik untuk {kecamatan_name}, dilewati")
                            skip_row = True
                            break
                    
                    if skip_row:
                        error_count += 1
                        continue
                    
                    # Ambil nilai dimensi jika ada
                    dim1 = float(row['dim1']) if 'dim1' in row and pd.notna(row['dim1']) else None
                    dim2 = float(row['dim2']) if 'dim2' in row and pd.notna(row['dim2']) else None
                    
                    # Tambahkan ke batch insert
                    insert_rows.append((
                        result_id,
                        kecamatan_id,
                        int(row['cluster']),
                        is_medoid,
                        float(row['x1']),
                        float(row['x2']),
                        float(row['x3']),
                        float(row['x4']),
                        float(row['x5']),
                        float(row['x6']),
                        float(row['x7']),
                        dim1,
                        dim2
                    ))
                    
                    clustering_data_count += 1
                    
                except Exception as row_e:
                    error_count += 1
                    logger.error(f"Baris {idx}: Error memproses baris untuk {row.get('kecamatan', 'unknown')}: {str(row_e)}")
                    continue
            
            # Log summary
            logger.info(f"Total baris diproses: {len(df)}, Berhasil: {clustering_data_count}, Gagal: {error_count}")
            
            # Batasi ukuran batch untuk menghindari query terlalu besar
            batch_size = 200  # Lebih kecil untuk menghindari timeout
            total_inserted = 0
            
            # Proses batch insert dengan pembagian batch
            for i in range(0, len(insert_rows), batch_size):
                batch = insert_rows[i:i+batch_size]
                
                if not batch:
                    continue
                
                try:
                    # Gunakan prepared statement untuk insert batch
                    cur.executemany("""
                        INSERT INTO clustering_data 
                        (result_id, kecamatan_id, cluster, is_medoid, x1, x2, x3, x4, x5, x6, x7, dim1, dim2) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, batch)
                    
                    # Commit setiap batch untuk menghindari transaksi terlalu besar
                    self.db.connection.commit()
                    
                    total_inserted += len(batch)
                    logger.info(f"Batch {i//batch_size + 1}: Berhasil menyisipkan {len(batch)} baris")
                except Exception as e:
                    logger.error(f"Batch {i//batch_size + 1}: Error dalam batch insert: {str(e)}")
                    self.db.connection.rollback()
                    
                    # Coba insert satu per satu untuk mengetahui baris mana yang bermasalah
                    for j, row_data in enumerate(batch):
                        try:
                            cur.execute("""
                                INSERT INTO clustering_data 
                                (result_id, kecamatan_id, cluster, is_medoid, x1, x2, x3, x4, x5, x6, x7, dim1, dim2) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, row_data)
                            self.db.connection.commit()
                            total_inserted += 1
                        except Exception as row_error:
                            logger.error(f"Batch {i//batch_size + 1}, Baris {j}: Error inserting: {str(row_error)}")
                            self.db.connection.rollback()
            
            # Verifikasi data yang telah diimpor
            cur.execute("SELECT COUNT(*) AS count FROM clustering_data WHERE result_id = %s", [result_id])
            result = cur.fetchone()
            actual_count = result['count'] if result else 0
            
            if actual_count != total_inserted:
                logger.warning(f"Perbedaan jumlah baris: Diproses={total_inserted}, Terverifikasi={actual_count}")
            
            logger.info(f"Total baris berhasil disisipkan ke database: {total_inserted}")
            return total_inserted
            
        except Exception as e:
            logger.error(f"Error dalam _import_clustering_data: {str(e)}", exc_info=True)
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            return 0
    
    def _cleanup_failed_import(self, result_id: int) -> None:
        """
        Clean up database after failed import with improved error handling
        
        Args:
            result_id: ID of the failed result
        """
        try:
            logger.info(f"Cleaning up failed import for result_id={result_id}")
            
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Log jumlah data yang akan dihapus
            tables = [
                ("clustering_data", "result_id"),
                ("cluster_characteristics", "result_id"),
                ("kecamatan_evaluasi", "result_id"),
                ("indikator_evaluations", "result_id"),
                ("sekolah_prioritas", "result_id"),
                ("sekolah_data", "result_id")
            ]
            
            for table, field in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) as count FROM {table} WHERE {field} = %s", [result_id])
                    count = cur.fetchone()['count']
                    logger.info(f"Will delete {count} rows from {table}")
                except Exception as te:
                    logger.warning(f"Error counting rows in {table}: {str(te)}")
            
            # Delete any partial data with error handling for each query
            for table, field in tables:
                try:
                    cur.execute(f"DELETE FROM {table} WHERE {field} = %s", [result_id])
                    rows_affected = cur.rowcount
                    logger.info(f"Deleted {rows_affected} rows from {table}")
                except Exception as e:
                    logger.warning(f"Error deleting from {table}: {str(e)}")
            
            # Finally delete the result itself
            try:
                cur.execute("DELETE FROM clustering_results WHERE id = %s", [result_id])
                rows_affected = cur.rowcount
                logger.info(f"Deleted result_id={result_id} from clustering_results ({rows_affected} rows)")
            except Exception as e:
                logger.error(f"Error deleting from clustering_results: {str(e)}")
            
            # Commit all deletions
            self.db.connection.commit()
            logger.info(f"Cleanup completed for result_id={result_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up failed import: {str(e)}", exc_info=True)
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.warning("Rollback performed due to cleanup error")
            



    def _generate_cluster_characteristics(self, result_id: int, jenjang: str) -> List[Dict[str, Any]]:
        """
        Generate karakteristik klaster berdasarkan data klasterisasi dengan konsistensi yang ditingkatkan.
        Implementasi analisis hierarkis di tiga level: klaster, kecamatan, dan sekolah.
        
        Args:
            result_id: ID hasil klasterisasi
            jenjang: Jenjang pendidikan (SMA/SMK)
            
        Returns:
            list: Daftar karakteristik klaster
        """
        try:
            # Langkah 1: Generate evaluasi kecamatan terlebih dahulu (level kecamatan)
            logger.info(f"Generating kecamatan evaluations for result_id={result_id}")
            self._generate_kecamatan_evaluations(result_id, jenjang)
            
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Langkah 2: Dapatkan daftar klaster yang ada (level klaster)
            clusters = self._get_distinct_clusters(cur, result_id)
            
            if not clusters:
                logger.warning(f"Tidak ditemukan data cluster untuk result_id={result_id}")
                return []
            
            # Hapus karakteristik yang sudah ada untuk hasil ini (jika ada)
            self._clear_existing_characteristics(cur, result_id)
            
            # Langkah 3: Generate karakteristik untuk setiap klaster
            all_characteristics = self._process_all_clusters(cur, result_id, clusters, jenjang)
            
            # Commit semua perubahan
            self.db.connection.commit()
            logger.info(f"Generated characteristics for {len(clusters)} clusters")
            
            return all_characteristics
            
        except Exception as e:
            logger.error(f"Error generating cluster characteristics: {str(e)}", exc_info=True)
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            raise e


    def _get_distinct_clusters(self, cur, result_id: int) -> List[int]:
        """
        Dapatkan daftar cluster yang tersedia untuk hasil klasterisasi tertentu.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            
        Returns:
            list: Daftar cluster yang tersedia
        """
        cur.execute("""
            SELECT DISTINCT cd.cluster
            FROM clustering_data cd
            WHERE cd.result_id = %s
            ORDER BY cd.cluster
        """, [result_id])
        
        return [row['cluster'] for row in cur.fetchall()]

    def _clear_existing_characteristics(self, cur, result_id: int) -> None:
        """
        Hapus karakteristik klaster yang sudah ada untuk hasil klasterisasi tertentu.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
        """
        cur.execute("DELETE FROM cluster_characteristics WHERE result_id = %s", [result_id])
        logger.info(f"Cleared existing characteristics for result_id={result_id}")

    def _process_all_clusters(self, cur, result_id: int, clusters: List[int], jenjang: str) -> List[Dict[str, Any]]:
        """
        Proses semua klaster dan generate karakteristiknya.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            clusters: Daftar cluster yang akan diproses
            jenjang: Jenjang pendidikan
            
        Returns:
            list: Daftar karakteristik klaster
        """
        all_characteristics = []
        
        for cluster in clusters:
            # 1. Analisis data klaster
            characteristic = self._process_single_cluster(cur, result_id, cluster, jenjang)
            
            if characteristic:
                all_characteristics.append(characteristic)
                
                # 2. Evaluasi sekolah dalam klaster (level sekolah)
                self._evaluate_schools_in_cluster(cur, result_id, cluster, jenjang)
                
                logger.info(f"Generated characteristics for cluster {cluster} in result_id {result_id}")
        
        return all_characteristics

    def _process_single_cluster(self, cur, result_id: int, cluster: int, jenjang: str) -> Optional[Dict[str, Any]]:
        """
        Proses satu klaster dan generate karakteristiknya.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            jenjang: Jenjang pendidikan
            
        Returns:
            dict: Karakteristik klaster, atau None jika gagal
        """
        # 1. Dapatkan data statistik klaster
        cluster_data = self._calculate_cluster_averages(cur, result_id, cluster)
        if not cluster_data:
            logger.warning(f"Tidak dapat menghitung nilai rata-rata untuk cluster {cluster}")
            return None
        
        # 2. Dapatkan medoid untuk klaster
        medoid_info = self._get_or_determine_medoid(cur, result_id, cluster, cluster_data)
        
        # 3. Dapatkan anggota klaster
        members = self._get_cluster_members(cur, result_id, cluster)
        
        # 4. Analisis dan evaluasi klaster
        result = self._analyze_cluster(cur, result_id, cluster, cluster_data, medoid_info, members, jenjang)
        
        return result

    def _analyze_cluster(self, cur, result_id: int, cluster: int, cluster_data: Dict[str, Any], 
                    medoid_info: Dict[str, Any], members: List[str], jenjang: str) -> Dict[str, Any]:
        """
        Analisis dan evaluasi karakteristik klaster.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            cluster_data: Data rata-rata klaster
            medoid_info: Informasi medoid
            members: Daftar anggota klaster
            jenjang: Jenjang pendidikan
            
        Returns:
            dict: Karakteristik klaster
        """
        # 1. Evaluasi indikator berdasarkan standar
        evaluations = self._evaluate_cluster_indicators(cluster_data, jenjang)
        
        # 2. Hitung berapa indikator yang memenuhi standar
        standar_terpenuhi = sum(1 for ev in evaluations.values() if ev['status'] == 'ideal')
        
        # 3. Tentukan level kualitas pendidikan berdasarkan standar yang terpenuhi
        kualitas_pendidikan = self._determine_education_quality(standar_terpenuhi, len(INDICATORS))
        
        # 4. Identifikasi kekuatan dan kelemahan
        fitur_tinggi, fitur_rendah = self._identify_strengths_weaknesses(result_id, cluster)
        
        # 5. Generate teks deskripsi, interpretasi, dan rekomendasi
        deskripsi = self._generate_cluster_description(
            cluster, cluster_data['jumlah_anggota'], standar_terpenuhi, fitur_tinggi, fitur_rendah
        )
        
        interpretasi = self._generate_interpretation_text(fitur_tinggi, fitur_rendah)
        rekomendasi = self._generate_recommendation_text(fitur_rendah, jenjang)
        
        # 6. Simpan ke database
        self._save_cluster_characteristics(
            cur, result_id, cluster, cluster_data, medoid_info, members,
            standar_terpenuhi, kualitas_pendidikan, fitur_tinggi, fitur_rendah,
            deskripsi, interpretasi, rekomendasi
        )
        
        # 7. Siapkan dan kembalikan hasil
        characteristic = {
            'cluster': cluster,
            'jumlah_anggota': cluster_data['jumlah_anggota'],
            'medoid_id': medoid_info['medoid_id'],
            'medoid_name': medoid_info['medoid_name'],
            'anggota': members,
            'x1_avg': cluster_data['x1_avg'],
            'x2_avg': cluster_data['x2_avg'],
            'x3_avg': cluster_data['x3_avg'],
            'x4_avg': cluster_data['x4_avg'],
            'x5_avg': cluster_data['x5_avg'],
            'x6_avg': cluster_data['x6_avg'],
            'x7_avg': cluster_data['x7_avg'],
            'standar_terpenuhi': standar_terpenuhi,
            'kualitas_pendidikan': kualitas_pendidikan,
            'fitur_tinggi': fitur_tinggi,
            'fitur_rendah': fitur_rendah,
            'deskripsi': deskripsi,
            'interpretasi': interpretasi,
            'rekomendasi': rekomendasi
        }
        
        return characteristic


    """
    Refaktorisasi metode import_from_csv menjadi fungsi-fungsi yang lebih kecil dan fokus
    """

    def import_from_csv(self, file_path: str, user_id: int, jenjang: str, 
                        skenario: str, jumlah_cluster: int, description: str = "") -> Tuple[bool, str, Optional[int]]:
            """
            Mengimpor hasil klasterisasi dari file CSV.
            
            Args:
                file_path: Path file CSV
                user_id: ID pengguna yang melakukan impor
                jenjang: Jenjang pendidikan (SMA/SMK)
                skenario: Nama skenario klasterisasi
                jumlah_cluster: Jumlah klaster
                description: Deskripsi tambahan
                
            Returns:
                tuple: (success, message, result_id)
            """
            try:
                # 1. Validasi input dan file CSV
                is_valid, message, df = self._validate_and_read_csv(file_path)
                
                if not is_valid:
                    return False, message, None
                
                # 2. Cek apakah proses dengan jenjang dan skenario ini sudah ada
                cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
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
                        user_id
                    ])
                    self.db.connection.commit()
                    process_id = cur.lastrowid
                    logger.info(f"Membuat proses klasterisasi baru dengan ID {process_id}")
                
                # 3. Buat record hasil klasterisasi di database
                result_id = self._create_clustering_result_record(process_id, jenjang, skenario, 
                                                            jumlah_cluster, description)
                
                # 4. Impor data klasterisasi
                success, message, total_imported = self._import_clustering_data_from_df(df, result_id)
                
                if not success:
                    self._cleanup_failed_import(result_id)
                    return False, message, None
                    
                # 5. Generate karakteristik klaster
                try:
                    characteristics = self._generate_cluster_characteristics(result_id, jenjang)
                    logger.info(f"Successfully generated characteristics for {len(characteristics)} clusters")
                except Exception as e:
                    logger.error(f"Error generating cluster characteristics: {str(e)}", exc_info=True)
                    self._cleanup_failed_import(result_id)
                    return False, f"Error saat menghasilkan karakteristik klaster: {str(e)}", None
                
                # 6. Update status klasterisasi
                self._update_clustering_result_status(result_id, 'completed')
                
                return True, f"Berhasil mengimpor {total_imported} data klasterisasi", result_id
                
            except Exception as e:
                logger.error(f"Error importing CSV: {str(e)}", exc_info=True)
                if 'result_id' in locals():
                    self._cleanup_failed_import(result_id)
                return False, f"Error: {str(e)}", None

    def _validate_and_read_csv(self, file_path: str) -> Tuple[bool, str, Optional[pd.DataFrame]]:
        """
        Validasi dan baca file CSV.
        
        Args:
            file_path: Path file CSV
            
        Returns:
            tuple: (is_valid, message, dataframe or None)
        """
        # Validasi file CSV menggunakan metode terpisah yang sudah ada
        is_valid, message, df = self.validate_csv_format(file_path)
        
        if not is_valid:
            return False, message, None
            
        # Normalisasi kolom CSV
        df = self._normalize_csv_columns(df)
        
        # Verifikasi jumlah data
        if len(df) == 0:
            return False, "File CSV tidak berisi data", None
            
        # Verifikasi kolom yang diperlukan
        required_columns = ['kecamatan', 'cluster'] + [f'x{i}' for i in range(1, 8)]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Kolom yang diperlukan tidak ditemukan: {missing_columns}", None
        
        return True, "File CSV valid", df

    def _create_clustering_result_record(self, process_id: int, jenjang: str, skenario: str, 
                                    jumlah_cluster: int, description: str = "") -> int:
        """
        Buat record hasil klasterisasi di database.
        
        Args:
            process_id: ID proses klasterisasi
            jenjang: Jenjang pendidikan
            skenario: Nama skenario klasterisasi
            jumlah_cluster: Jumlah klaster
            description: Deskripsi tambahan
            
        Returns:
            int: ID hasil klasterisasi
        """
        cur = self.db.connection.cursor()
        
        # Sanitasi input
        description = description.strip() if description else ""
        skenario = skenario.strip() if skenario else "Skenario 1"
        
        # Insert record hasil klasterisasi
        cur.execute("""
            INSERT INTO clustering_results 
            (process_id, jenjang, jumlah_cluster, skenario, status, description, created_at, imported_at) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, [process_id, jenjang, jumlah_cluster, skenario, 'importing', description])
        
        result_id = cur.lastrowid
        self.db.connection.commit()
        
        logger.info(f"Created clustering result record with ID {result_id}")
        return result_id

    def _import_clustering_data_from_df(self, df: pd.DataFrame, result_id: int) -> Tuple[bool, str, int]:
        """
        Impor data klasterisasi dari DataFrame.
        
        Args:
            df: DataFrame hasil klasterisasi
            result_id: ID hasil klasterisasi
            
        Returns:
            tuple: (success, message, total_imported)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # 1. Ambil mapping nama kecamatan ke ID
            kecamatan_id_mapping, missing_kecamatan = self._match_kecamatan_names(cur, df['kecamatan'].unique())
            
            # 2. Log kecamatan yang tidak ditemukan
            if missing_kecamatan:
                logger.warning(f"Kecamatan tidak ditemukan: {missing_kecamatan}")
                
                # Jika terlalu banyak kecamatan tidak ditemukan, mungkin perlu dibatalkan
                if len(missing_kecamatan) > 0.5 * len(df['kecamatan'].unique()):
                    return False, f"Terlalu banyak kecamatan yang tidak ditemukan ({len(missing_kecamatan)})", 0
            
            # 3. Import data klasterisasi
            total_imported = self._import_clustering_data(cur, df, result_id, kecamatan_id_mapping)
            
            if total_imported == 0:
                return False, "Tidak ada data yang berhasil diimpor", 0
                
            # 4. Commit perubahan
            self.db.connection.commit()
            
            return True, f"Berhasil mengimpor {total_imported} data klasterisasi", total_imported
            
        except Exception as e:
            logger.error(f"Error importing clustering data: {str(e)}", exc_info=True)
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            return False, f"Error: {str(e)}", 0

    def _update_clustering_result_status(self, result_id: int, status: str) -> None:
        """
        Update status hasil klasterisasi.
        
        Args:
            result_id: ID hasil klasterisasi
            status: Status baru ('importing', 'completed', 'failed')
        """
        cur = self.db.connection.cursor()
        
        # Update status
        cur.execute("""
            UPDATE clustering_results 
            SET status = %s, 
                imported_at = NOW() 
            WHERE id = %s
        """, [status, result_id])
        
        self.db.connection.commit()
        logger.info(f"Updated clustering result {result_id} status to '{status}'")



    # Tambahkan method berikut ke dalam class ClusteringManager di file ClusteringManager.py
    # Tempatkan method ini di antara method-method lain dalam class

    def _calculate_cluster_averages(self, cur, result_id, cluster):
        """
        Menghitung nilai rata-rata untuk semua indikator dalam sebuah klaster.
        
        Args:
            cur: Database cursor
            result_id: ID dari hasil klasterisasi
            cluster: Nomor klaster
            
        Returns:
            dict: Dictionary dengan nilai rata-rata untuk setiap indikator
        """
        # Query untuk menghitung rata-rata semua indikator dalam cluster
        cur.execute("""
            SELECT 
                AVG(x1) as x1_avg, 
                AVG(x2) as x2_avg, 
                AVG(x3) as x3_avg, 
                AVG(x4) as x4_avg, 
                AVG(x5) as x5_avg, 
                AVG(x6) as x6_avg, 
                AVG(x7) as x7_avg,
                COUNT(*) as jumlah_anggota
            FROM clustering_data 
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        # Ambil hasil query
        result = cur.fetchone()
        
        # Jika tidak ada data, kembalikan None
        if not result:
            return None
        
        # Kembalikan dictionary berisi rata-rata indikator
        return {
            'x1_avg': result['x1_avg'],
            'x2_avg': result['x2_avg'],
            'x3_avg': result['x3_avg'],
            'x4_avg': result['x4_avg'],
            'x5_avg': result['x5_avg'],
            'x6_avg': result['x6_avg'],
            'x7_avg': result['x7_avg'],
            'jumlah_anggota': result['jumlah_anggota']
        }

    def _get_or_determine_medoid(self, cur, result_id: int, cluster: int, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mendapatkan atau menentukan medoid untuk sebuah klaster.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            cluster_data: Data rata-rata klaster
            
        Returns:
            dict: Informasi medoid (id dan nama)
        """
        # Dapatkan medoid untuk klaster ini
        cur.execute("""
            SELECT cd.kecamatan_id, k.nama_kecamatan
            FROM clustering_data cd
            JOIN kecamatan k ON cd.kecamatan_id = k.id
            WHERE cd.result_id = %s AND cd.cluster = %s AND cd.is_medoid = 1
            LIMIT 1
        """, [result_id, cluster])
        
        medoid = cur.fetchone()
        medoid_id = medoid['kecamatan_id'] if medoid else None
        medoid_name = medoid['nama_kecamatan'] if medoid else None
        
        # Jika tidak ada medoid yang ditandai, hitung titik terdekat ke pusat klaster
        if not medoid_id:
            logger.info(f"Tidak ada medoid ditandai untuk cluster {cluster}, menghitung medoid terdekat")
            
            # Hitung jarak kuadrat dari setiap titik ke pusat
            cur.execute("""
                SELECT cd.kecamatan_id, k.nama_kecamatan, 
                    POWER(cd.x1 - %s, 2) + 
                    POWER(cd.x2 - %s, 2) + 
                    POWER(cd.x3 - %s, 2) + 
                    POWER(cd.x4 - %s, 2) + 
                    POWER(cd.x5 - %s, 2) + 
                    POWER(cd.x6 - %s, 2) + 
                    POWER(cd.x7 - %s, 2) as squared_distance
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                WHERE cd.result_id = %s AND cd.cluster = %s
                ORDER BY squared_distance ASC
                LIMIT 1
            """, [
                cluster_data['x1_avg'], cluster_data['x2_avg'], cluster_data['x3_avg'],
                cluster_data['x4_avg'], cluster_data['x5_avg'], cluster_data['x6_avg'],
                cluster_data['x7_avg'], result_id, cluster
            ])
            
            closest_point = cur.fetchone()
            if closest_point:
                medoid_id = closest_point['kecamatan_id']
                medoid_name = closest_point['nama_kecamatan']
                
                # Perbarui titik ini sebagai medoid
                cur.execute("""
                    UPDATE clustering_data 
                    SET is_medoid = 1 
                    WHERE result_id = %s AND kecamatan_id = %s
                """, [result_id, medoid_id])
                
                logger.info(f"Menetapkan {medoid_name} sebagai medoid untuk cluster {cluster}")
        
        return {
            'medoid_id': medoid_id,
            'medoid_name': medoid_name
        }

    def _get_cluster_members(self, cur, result_id: int, cluster: int) -> List[str]:
        """
        Mendapatkan daftar anggota sebuah klaster.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            
        Returns:
            list: Daftar nama kecamatan anggota klaster
        """
        # Dapatkan daftar anggota
        cur.execute("""
            SELECT k.nama_kecamatan
            FROM clustering_data cd
            JOIN kecamatan k ON cd.kecamatan_id = k.id
            WHERE cd.result_id = %s AND cd.cluster = %s
            ORDER BY k.nama_kecamatan
        """, [result_id, cluster])
        
        return [row['nama_kecamatan'] for row in cur.fetchall()]

    def _evaluate_cluster_indicators(self, cluster_data: Dict[str, Any], jenjang: str) -> Dict[str, Dict[str, Any]]:
        """
        Mengevaluasi indikator klaster berdasarkan standar.
        
        Args:
            cluster_data: Data rata-rata klaster
            jenjang: Jenjang pendidikan
            
        Returns:
            dict: Hasil evaluasi indikator
        """
        standar = self.standar_indikator
        evaluations = {}
        
        for indicator in INDICATORS:
            avg_field = f'{indicator}_avg'
            evaluations[indicator] = self._evaluate_indicator(indicator, cluster_data[avg_field], jenjang, standar)
        
        return evaluations

    def _save_cluster_characteristics(self, cur, result_id: int, cluster: int, cluster_data: Dict[str, Any], 
                                medoid_info: Dict[str, Any], members: List[str], standar_terpenuhi: int, 
                                kualitas_pendidikan: str, fitur_tinggi: List[str], fitur_rendah: List[str],
                                deskripsi: str, interpretasi: str, rekomendasi: str) -> None:
        """
        Menyimpan karakteristik klaster ke database.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            cluster_data: Data rata-rata klaster
            medoid_info: Informasi medoid
            members: Daftar anggota klaster
            standar_terpenuhi: Jumlah standar yang terpenuhi
            kualitas_pendidikan: Level kualitas pendidikan
            fitur_tinggi: Daftar fitur unggulan
            fitur_rendah: Daftar fitur yang perlu diperbaiki
            deskripsi: Deskripsi klaster
            interpretasi: Interpretasi hasil klaster
            rekomendasi: Rekomendasi perbaikan
        """
        cur.execute("""
            INSERT INTO cluster_characteristics 
            (result_id, cluster, jumlah_anggota, medoid_id, medoid_name, anggota, 
            x1_avg, x2_avg, x3_avg, x4_avg, x5_avg, x6_avg, x7_avg,
            standar_terpenuhi, kualitas_pendidikan, fitur_tinggi, fitur_rendah, 
            deskripsi, interpretasi, rekomendasi) 
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            result_id, cluster, cluster_data['jumlah_anggota'], 
            medoid_info['medoid_id'], medoid_info['medoid_name'], 
            ",".join(members) if members else "",
            cluster_data['x1_avg'], cluster_data['x2_avg'], cluster_data['x3_avg'], 
            cluster_data['x4_avg'], cluster_data['x5_avg'], cluster_data['x6_avg'], 
            cluster_data['x7_avg'],
            standar_terpenuhi, kualitas_pendidikan, 
            ",".join(fitur_tinggi) if fitur_tinggi else "", 
            ",".join(fitur_rendah) if fitur_rendah else "",
            deskripsi, interpretasi, rekomendasi
        ])

    def _evaluate_schools_in_cluster(self, cur, result_id: int, cluster: int, jenjang: str) -> None:
        """
        Mengevaluasi sekolah dalam sebuah klaster (level 3: sekolah).
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            jenjang: Jenjang pendidikan
        """
        # Cek apakah ada data sekolah untuk klaster ini
        cur.execute("""
            SELECT COUNT(*) as count
            FROM sekolah_data
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        count_result = cur.fetchone()
        if not count_result or count_result['count'] == 0:
            logger.info(f"Tidak ada data sekolah untuk cluster {cluster}, evaluasi level sekolah dilewati")
            return
        
        # Dapatkan data sekolah
        cur.execute("""
            SELECT id, nama_sekolah, x1, x2, x3, x4, x5, x6, x7
            FROM sekolah_data
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        schools = cur.fetchall()
        
        # Evaluasi setiap sekolah
        for school in schools:
            # Evaluasi indikator
            evaluations = {}
            non_ideal_indicators = []
            
            for indicator in INDICATORS:
                evaluation = self._evaluate_indicator(indicator, school[indicator], jenjang)
                evaluations[indicator] = evaluation
                
                if evaluation['status'] != 'ideal':
                    non_ideal_indicators.append((indicator, school[indicator], evaluation))
            
            # Urutkan indikator yang tidak ideal berdasarkan persentase (ascending)
            non_ideal_indicators.sort(key=lambda x: x[2]['percentage'])
            
            # Proses setiap indikator yang tidak ideal
            for indicator, value, evaluation in non_ideal_indicators:
                gap = 100 - evaluation['percentage']
                urgensi = self._determine_urgency(gap)
                
                # Dapatkan nilai ideal untuk perbandingan
                ideal_value = self._get_ideal_value(indicator, jenjang)
                
                # Generate rekomendasi
                rekomendasi = self._generate_detailed_recommendation(indicator, value, ideal_value, jenjang)
                
                # Perbarui atau buat prioritas
                self._create_or_update_priority(
                    cur, result_id, school['id'], indicator, value, ideal_value, gap, urgensi, rekomendasi
                )
            
            logger.debug(f"Evaluated school {school['nama_sekolah']} in cluster {cluster}")


    def _evaluate_indicator(self, indicator: str, value: float, jenjang: str, standar: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Mengevaluasi nilai indikator terhadap standar ideal dengan perbaikan konsistensi dan konteks pendidikan.
        
        Args:
            indicator: Kode indikator
            value: Nilai indikator
            jenjang: Jenjang pendidikan
            standar: Dictionary standar indikator. Jika None, akan menggunakan self.standar_indikator
                    
        Returns:
            dict: Hasil evaluasi dengan status, persentase kesesuaian, dan deskripsi
        """
        try:
            # Handle kasus nilai None atau NaN
            if value is None or (isinstance(value, float) and pd.isna(value)):
                logger.warning(f"Nilai indikator {indicator} adalah None atau NaN, menggunakan default")
                return {
                    'status': 'unknown',
                    'percentage': 0,
                    'description': f'Nilai indikator {indicator} tidak tersedia'
                }
                
            # Gunakan standar yang disediakan atau ambil dari instance
            if standar is None:
                standar = self.standar_indikator
            
            # Log detail untuk debugging
            logger.debug(f"Evaluating indicator {indicator}, value={value}, jenjang={jenjang}")
            
            # Cek apakah indikator ada dalam standar
            if indicator not in standar:
                logger.warning(f"Indikator {indicator} tidak ditemukan dalam standar")
                return {
                    'status': 'unknown',
                    'percentage': 50,  # Default 50%
                    'description': f'Standar evaluasi untuk indikator {indicator} belum tersedia'
                }
            
            # Penggunaan konstanta untuk status
            STATUS_IDEAL = 'ideal'
            STATUS_NOT_IDEAL = 'not_ideal'
            
            # Set konteks pendidikan dari konstanta
            context = INDICATOR_CONTEXTS.get(indicator, '')
            
            if indicator == 'x1':
                # Rasio Siswa per Ruang Kelas
                max_val = standar[indicator].get('max', 32)
                
                if value <= max_val:
                    # Nilai di bawah atau sama dengan standar max = IDEAL
                    return {
                        'status': STATUS_IDEAL,
                        'percentage': 100,
                        'description': f'Ideal (rasio {value:.1f} ≤ {max_val}, memungkinkan pembelajaran yang lebih efektif dan interaksi guru-siswa yang lebih baik)'
                    }
                else:
                    # Nilai di atas standar max = TIDAK IDEAL
                    # Persentase kesesuaian dihitung sebagai seberapa dekat dengan nilai ideal
                    # Formula yang lebih baik: 100 - (persentase_deviasi * 100)
                    # dengan batas minimum 0%
                    if max_val == 0:  # Hindari division by zero
                        percentage = 0
                    else:
                        percentage = max(0, min(100, 100 - ((value - max_val) / max_val * 100)))
                    
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (rasio {value:.1f} > {max_val}, kepadatan kelas terlalu tinggi yang menghambat interaksi efektif)'
                    }
                    
            elif indicator == 'x2':
                # Rasio Siswa per Guru
                max_key = 'max_sma' if jenjang == 'SMA' else 'max_smk'
                max_val = 20 if jenjang == 'SMA' else 15  # Default
                
                if max_key in standar[indicator]:
                    max_val = standar[indicator][max_key]
                
                if value <= max_val:
                    # Nilai di bawah atau sama dengan standar max = IDEAL
                    return {
                        'status': STATUS_IDEAL,
                        'percentage': 100,
                        'description': f'Ideal (rasio {value:.1f} ≤ {max_val}, memungkinkan perhatian lebih personal dan beban kerja guru yang seimbang)'
                    }
                else:
                    # Nilai di atas standar max = TIDAK IDEAL
                    if max_val == 0:  # Hindari division by zero
                        percentage = 0
                    else:
                        percentage = max(0, min(100, 100 - ((value - max_val) / max_val * 100)))
                    
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (rasio {value:.1f} > {max_val}, beban kerja guru terlalu tinggi yang dapat menurunkan kualitas pengajaran)'
                    }
                    
            elif indicator == 'x3':
                # Rasio Siswa per Rombel
                max_val = standar[indicator].get('max', 32)
                
                if value <= max_val:
                    # Nilai di bawah atau sama dengan batas maksimum = IDEAL
                    return {
                        'status': STATUS_IDEAL,
                        'percentage': 100,
                        'description': f'Ideal (rasio {value:.1f} ≤ {max_val}, memungkinkan pembelajaran yang interaktif dan kolaboratif)'
                    }
                else:
                    # Nilai di atas batas maksimum = TIDAK IDEAL
                    if max_val == 0:  # Hindari division by zero
                        percentage = 0
                    else:
                        percentage = max(0, min(100, 100 - ((value - max_val) / max_val * 100)))
                    
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (rasio {value:.1f} > {max_val}, rombel terlalu padat untuk pembelajaran yang efektif)'
                    }
            
            elif indicator == 'x4':
                # Rasio Rombel per Sekolah
                min_key = f'min_{jenjang.lower()}'
                max_key = f'max_{jenjang.lower()}'
                
                # Default values
                min_val = 3
                max_val = 27 if jenjang == 'SMA' else 48
                
                # Get values from standar if available
                if min_key in standar[indicator]:
                    min_val = standar[indicator][min_key]
                
                if max_key in standar[indicator]:
                    max_val = standar[indicator][max_key]
                
                if min_val <= value <= max_val:
                    # Dalam rentang ideal
                    return {
                        'status': STATUS_IDEAL,
                        'percentage': 100,
                        'description': f'Ideal (rasio {value:.1f} dalam rentang {min_val}-{max_val}, manajemen sekolah efisien dan penggunaan sumber daya optimal)'
                    }
                elif value < min_val:
                    # Di bawah minimum
                    if min_val == 0:  # Hindari division by zero
                        percentage = 0
                    else:
                        percentage = max(0, min(100, (value / min_val) * 100))
                    
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (rasio {value:.1f} < {min_val}, jumlah rombel terlalu sedikit yang dapat menghambat pengelolaan sekolah)'
                    }
                else:  # value > max_val
                    # Di atas maksimum
                    if max_val == 0:  # Hindari division by zero
                        percentage = 0
                    else:
                        percentage = max(0, min(100, 100 - ((value - max_val) / max_val * 100)))
                    
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (rasio {value:.1f} > {max_val}, jumlah rombel terlalu banyak yang memberatkan infrastruktur sekolah)'
                    }
                    
            elif indicator in ['x5', 'x6', 'x7']:
                # Persentase Ketersediaan Fasilitas - pastikan nilai dalam rentang 0-1
                # Jika nilai > 1, mungkin sudah dalam persentase (mis. 75 bukan 0.75)
                if value > 1:
                    value = value / 100
                    
                percentage = value * 100
                min_threshold = 0.9  # 90% adalah batas minimum ideal
                
                facility_types = {
                    'x5': 'perpustakaan',
                    'x6': 'laboratorium',
                    'x7': 'ruang kelas'
                }
                
                facility_contexts = {
                    'x5': 'mendukung literasi dan akses siswa ke berbagai sumber belajar',
                    'x6': 'mendukung pembelajaran berbasis eksperimen dan pengembangan keterampilan praktis',
                    'x7': 'mendukung proses belajar mengajar yang optimal'
                }
                
                facility_type = facility_types.get(indicator, 'fasilitas')
                facility_context = facility_contexts.get(indicator, '')
                
                if value >= min_threshold:
                    # Nilai di atas atau sama dengan 90% = IDEAL
                    return {
                        'status': STATUS_IDEAL,
                        'percentage': percentage,
                        'description': f'Ideal ({percentage:.1f}% ketersediaan {facility_type}, {facility_context})'
                    }
                else:
                    # Nilai di bawah 90% = TIDAK IDEAL
                    # Persentase sesuai dengan nilai asli (mis. 75% = 75% kesesuaian)
                    return {
                        'status': STATUS_NOT_IDEAL,
                        'percentage': percentage,
                        'description': f'Kurang ideal (hanya {percentage:.1f}% ketersediaan {facility_type}, yang dapat membatasi akses siswa dan menghambat proses pembelajaran)'
                    }
            
            # Default jika indikator tidak dikenali
            logger.warning(f"Indikator {indicator} tidak memiliki penanganan khusus")
            return {
                'status': 'unknown',
                'percentage': 50,
                'description': f'Evaluasi untuk indikator {indicator} belum tersedia'
            }
        
        except Exception as e:
            # Log error dan kembalikan nilai default jika terjadi kesalahan
            logger.error(f"Error evaluating indicator {indicator}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'percentage': 50,
                'description': f'Terjadi kesalahan saat mengevaluasi indikator {indicator}'
            }
    
    def _generate_cluster_description(self, cluster: int, jumlah_anggota: int, 
                                    standar_terpenuhi: int, fitur_tinggi: List[str], 
                                    fitur_rendah: List[str]) -> str:
        """
        Generate a descriptive text for the cluster
        
        Args:
            cluster: Cluster number
            jumlah_anggota: Number of members
            standar_terpenuhi: Number of standards met
            fitur_tinggi: List of high-performing features
            fitur_rendah: List of low-performing features
            
        Returns:
            str: Cluster description
        """
        deskripsi = f"Cluster {cluster} terdiri dari {jumlah_anggota} kecamatan. "
        
        if standar_terpenuhi > 0:
            deskripsi += f"Memenuhi {standar_terpenuhi} dari 7 standar indikator kualitas pendidikan. "
        else:
            deskripsi += "Tidak memenuhi semua standar indikator kualitas pendidikan. "
        
        if fitur_tinggi:
            fitur_tinggi_str = ", ".join([INDICATOR_DESCRIPTIONS.get(ft, ft) for ft in fitur_tinggi])
            deskripsi += f"Memiliki keunggulan pada: {fitur_tinggi_str}. "
        
        if fitur_rendah:
            fitur_rendah_str = ", ".join([INDICATOR_DESCRIPTIONS.get(fr, fr) for fr in fitur_rendah])
            deskripsi += f"Memiliki tantangan pada: {fitur_rendah_str}. "
            
        return deskripsi

    def _get_indicator_labels(self, indicator_list: List[str]) -> str:
        """
        Get human-readable labels for indicator codes
        
        Args:
            indicator_list: List of indicator codes (x1, x2, etc.)
            
        Returns:
            str: Comma-separated list of indicator labels
        """
        labels = []
        descriptions = {
            'x1': 'rasio siswa per ruang kelas',
            'x2': 'rasio siswa per guru',
            'x3': 'rasio siswa per rombel',
            'x4': 'rasio rombel per sekolah',
            'x5': 'ketersediaan perpustakaan',
            'x6': 'ketersediaan laboratorium',
            'x7': 'ketersediaan ruang kelas'
        }
        
        for indicator in indicator_list:
            if indicator in descriptions:
                labels.append(descriptions[indicator])
            else:
                labels.append(indicator)
        
        if not labels:
            return ""
            
        if len(labels) == 1:
            return labels[0]
        
        return ", ".join(labels[:-1]) + " dan " + labels[-1]

    def _generate_interpretation_text(self, fitur_tinggi: List[str], fitur_rendah: List[str]) -> str:
        """
        Generate interpretation text based on strengths and weaknesses
        
        Args:
            fitur_tinggi: List of indicators with high performance
            fitur_rendah: List of indicators with low performance
            
        Returns:
            str: Interpretation text
        """
        interpretasi = "Wilayah pada cluster ini "
        
        if fitur_tinggi:
            interpretasi += f"menunjukkan kualitas pendidikan yang baik pada aspek {self._get_indicator_labels(fitur_tinggi)}. "
        
        if fitur_rendah:
            interpretasi += f"perlu meningkatkan aspek {self._get_indicator_labels(fitur_rendah)}. "
            
        if not fitur_tinggi and not fitur_rendah:
            interpretasi += "menunjukkan kualitas pendidikan yang merata tanpa keunggulan atau kelemahan yang signifikan."
            
        return interpretasi
    

    def _generate_recommendation_text(self, fitur_rendah: List[str], jenjang: str) -> str:
        """
        Generate recommendation text based on low-performing features with contextual explanations
        sesuai dengan dokumentasi perbaikan
        
        Args:
            fitur_rendah: List of indicators with low performance
            jenjang: Education level
            
        Returns:
            str: Recommendation text with contextual explanations
        """
        if not fitur_rendah:
            return "Pertahankan kualitas pendidikan yang sudah baik pada seluruh indikator dengan melanjutkan program-program yang telah berhasil dan melakukan monitoring berkala."
        
        recommendations = []
        
        for indicator in fitur_rendah:
            if indicator == 'x1':
                recommendations.append("Perlu penambahan ruang kelas baru atau redistribusi siswa antar sekolah untuk mengurangi kepadatan kelas dan menciptakan lingkungan belajar yang lebih kondusif, sehingga interaksi antara guru dan siswa dapat lebih efektif")
            elif indicator == 'x2':
                recommendations.append("Perlu penambahan tenaga pengajar untuk mengurangi beban kerja guru dan memungkinkan perhatian yang lebih personal kepada setiap siswa, sehingga proses pembelajaran dapat lebih adaptif terhadap kebutuhan individu siswa")
            elif indicator == 'x3':
                recommendations.append("Perlu pengaturan ulang komposisi rombongan belajar untuk mencapai ukuran yang optimal, sehingga dinamika kelas lebih interaktif dan memungkinkan penggunaan metode pembelajaran kolaboratif yang efektif")
            elif indicator == 'x4':
                recommendations.append("Perlu optimalisasi jumlah rombongan belajar di setiap sekolah untuk memastikan efisiensi manajemen sekolah, penggunaan sumber daya yang tepat, dan distribusi beban mengajar yang merata bagi tenaga pendidik")
            elif indicator == 'x5':
                recommendations.append("Perlu pembangunan fasilitas perpustakaan di sekolah yang belum memilikinya untuk meningkatkan akses siswa terhadap sumber belajar, mendukung budaya literasi, dan memfasilitasi pembelajaran mandiri serta penelitian siswa")
            elif indicator == 'x6':
                recommendations.append("Perlu pengadaan laboratorium di sekolah yang belum memilikinya untuk mendukung pembelajaran berbasis eksperimen, mengembangkan keterampilan praktis siswa, dan memberikan pengalaman belajar yang lebih konkret terutama pada mata pelajaran sains dan teknologi")
            elif indicator == 'x7':
                recommendations.append("Perlu memastikan ketersediaan ruang kelas yang memadai dan proporsional dengan jumlah rombongan belajar, sehingga jadwal pembelajaran dapat berjalan optimal tanpa terkendala keterbatasan ruang dan waktu")
        
        if not recommendations:
            return "Perlu evaluasi lebih lanjut untuk meningkatkan kualitas pendidikan."
        
        # Menambahkan rekomendasi tambahan untuk konteks yang lebih spesifik
        if len(recommendations) > 1:
            # Untuk pendekatan terpadu
            recommendations.append(f"Merencanakan pendekatan terpadu untuk meningkatkan semua aspek yang memerlukan perhatian, dengan prioritas pada indikator yang paling kritis")
            
            # Rekomendasi spesifik berdasarkan jenjang
            if jenjang == 'SMA':
                recommendations.append("Meningkatkan kolaborasi dengan perguruan tinggi dan dunia usaha untuk memberikan siswa SMA wawasan dan persiapan yang lebih baik untuk pendidikan lanjutan atau dunia kerja")
            elif jenjang == 'SMK':
                recommendations.append("Memperkuat kerja sama dengan dunia industri untuk memastikan kurikulum dan fasilitas laboratorium/praktik sesuai dengan kebutuhan dunia kerja terkini")
        
        # Gabungkan semua rekomendasi dengan pemisah yang baik
        if len(recommendations) <= 2:
            # Untuk 1-2 rekomendasi, gunakan kalimat lengkap
            return " dan ".join(recommendations) + "."
        else:
            # Untuk 3+ rekomendasi, gunakan format bullet point dalam teks
            formatted_recommendations = []
            for i, rec in enumerate(recommendations):
                # Tambahkan nomor urut untuk rekomendasi
                formatted_recommendations.append(f"{i+1}) {rec}")
            
            return "; ".join(formatted_recommendations) + "."
    
    
    def _identify_strengths_weaknesses(self, result_id: int, cluster: int) -> Tuple[List[str], List[str]]:
        """
        Identify strengths and weaknesses for a cluster based on indicator evaluations
        
        Args:
            result_id: ID of the clustering result
            cluster: Cluster number
            
        Returns:
            tuple: (strengths_list, weaknesses_list)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get average indicator values for this cluster
            cur.execute("""
                SELECT 
                    AVG(cd.x1) as x1_avg, 
                    AVG(cd.x2) as x2_avg, 
                    AVG(cd.x3) as x3_avg, 
                    AVG(cd.x4) as x4_avg, 
                    AVG(cd.x5) as x5_avg, 
                    AVG(cd.x6) as x6_avg, 
                    AVG(cd.x7) as x7_avg
                FROM clustering_data cd
                WHERE cd.result_id = %s AND cd.cluster = %s
            """, [result_id, cluster])
            
            avg_values = cur.fetchone()
            
            if not avg_values:
                logger.warning(f"No data found for result_id={result_id}, cluster={cluster}")
                return [], []
            
            # Get indicator evaluations
            indicator_values = {}
            for ind in INDICATORS:
                indicator_values[ind] = avg_values.get(f'{ind}_avg')
                    
            # Get all indicator values across all clusters for comparison
            all_indicator_values = {}
            for ind in INDICATORS:
                cur.execute(f"""
                    SELECT AVG(value) as mean, STDDEV(value) as stddev
                    FROM (
                        SELECT {ind} as value 
                        FROM clustering_data 
                        WHERE result_id = %s
                    ) t
                """, [result_id])
                stats = cur.fetchone()
                
                # Handle special case when stddev is NULL (happens with only one value or all equal values)
                mean = stats['mean'] if stats['mean'] is not None else 0
                stddev = stats['stddev'] if stats['stddev'] is not None else 0.0001  # Small non-zero value to avoid div by zero
                
                all_indicator_values[ind] = {
                    'mean': mean,
                    'stddev': stddev
                }
            
            # Calculate z-scores for each indicator
            z_scores = {}
            for ind in INDICATORS:
                mean = all_indicator_values[ind]['mean']
                stddev = all_indicator_values[ind]['stddev']
                
                if stddev == 0:  # Avoid division by zero
                    z_scores[ind] = 0
                else:
                    z_scores[ind] = (indicator_values[ind] - mean) / stddev
                
                # Log for debugging
                logger.debug(f"Indicator {ind}: value={indicator_values[ind]:.2f}, mean={mean:.2f}, stddev={stddev:.2f}, z-score={z_scores[ind]:.2f}")
            
            # Identify strengths and weaknesses based on Z-score and evaluations
            strengths = []
            weaknesses = []
            
            # For x1, x2, x3: lower is better (negative z-score is good)
            for ind in ['x1', 'x2', 'x3']:
                # Changed threshold from 0.5 to 0.7 for better differentiation
                if z_scores[ind] < -0.7:  # Better than average (more than 0.7 std below mean)
                    strengths.append(ind)
                elif z_scores[ind] > 0.7:  # Worse than average (more than 0.7 std above mean)
                    weaknesses.append(ind)
            
            # For x4: close to ideal is better
            if 'x4' in z_scores:
                # Get ideal value based on jenjang
                cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
                result = cur.fetchone()
                jenjang = result['jenjang'] if result else 'SMA'
                
                x4_ideal = 15 if jenjang == 'SMA' else 24  # Middle of range for SMA/SMK
                x4_value = indicator_values['x4']
                
                # If close to ideal value (within 15% of ideal)
                if abs(x4_value - x4_ideal) <= x4_ideal * 0.15:
                    strengths.append('x4')
                # If far from ideal value (more than 30% from ideal)
                elif abs(x4_value - x4_ideal) >= x4_ideal * 0.30:
                    weaknesses.append('x4')
            
            # For x5, x6, x7: higher is better (positive z-score is good)
            for ind in ['x5', 'x6', 'x7']:
                # Use both z-score and absolute threshold
                value = indicator_values[ind]
                
                # Changed threshold from 0.5 to 0.7 for better differentiation
                if z_scores[ind] > 0.7 or value >= 0.9:  # Better than average OR >= 90%
                    strengths.append(ind)
                elif z_scores[ind] < -0.7 or value < 0.7:  # Worse than average OR < 70%
                    weaknesses.append(ind)
            
            # Log results
            logger.info(f"Cluster {cluster} strengths: {strengths}")
            logger.info(f"Cluster {cluster} weaknesses: {weaknesses}")
            
            return strengths, weaknesses
                
        except Exception as e:
            logger.error(f"Error identifying strengths/weaknesses: {str(e)}", exc_info=True)
            return [], []

    def _generate_kecamatan_evaluations(self, result_id: int, jenjang: str) -> None:
        """
        Generate evaluation for each kecamatan in the clustering result
        
        Args:
            result_id: ID of the clustering result
            jenjang: Education level (SMA/SMK)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get standar indikator
            standar = self.standar_indikator
            
            # Load result data with kecamatan names
            cur.execute("""
                SELECT cd.*, k.nama_kecamatan 
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                WHERE cd.result_id = %s
            """, [result_id])
            
            kecamatan_data = cur.fetchall()
            
            if not kecamatan_data:
                logger.warning(f"No kecamatan data found for result_id {result_id}")
                return
            
            # Delete existing evaluations for this result to avoid duplicates
            cur.execute("DELETE FROM kecamatan_evaluasi WHERE result_id = %s", [result_id])
            
            # Process each kecamatan
            for data in kecamatan_data:
                self._process_kecamatan_evaluation(cur, result_id, data, jenjang, standar)
            
            # Commit all changes
            self.db.connection.commit()
            logger.info(f"Generated evaluations for {len(kecamatan_data)} kecamatan in result_id {result_id}")
            
        except Exception as e:
            logger.error(f"Error generating kecamatan evaluations: {str(e)}", exc_info=True)
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            raise e

    def _process_kecamatan_evaluation(self, cur, result_id: int, data: Dict[str, Any], jenjang: str, 
                                    standar: Dict[str, Dict[str, Any]]) -> None:
        """
        Process evaluation for a single kecamatan
        
        Args:
            cur: Database cursor
            result_id: ID of the clustering result
            data: Kecamatan data from database
            jenjang: Education level
            standar: Standard indicators
        """
        kecamatan_id = data['kecamatan_id']
        cluster = data['cluster']
        cluster_is_medoid = data['is_medoid']
        
        # Extract indicator values
        indicator_values = {ind: data[ind] for ind in INDICATORS}
        
        # Get indicator evaluations
        evaluations = {ind: self._evaluate_indicator(ind, val, jenjang, standar) 
                    for ind, val in indicator_values.items()}
        
        # Count how many indicators meet standards
        standar_terpenuhi = sum(1 for ev in evaluations.values() if ev['status'] == 'ideal')
        
        # Determine education quality level based on standards met
        kualitas_pendidikan = self._determine_education_quality(standar_terpenuhi, len(INDICATORS))
        
        # Identify indicators with the lowest percentage compliance
        sorted_indicators = sorted(
            [(ind, ev['percentage']) for ind, ev in evaluations.items() if ev['status'] != 'ideal'],
            key=lambda x: x[1]
        )
        
        # Get the 3 lowest (if available)
        prioritas_1 = sorted_indicators[0][0] if len(sorted_indicators) > 0 else None
        prioritas_2 = sorted_indicators[1][0] if len(sorted_indicators) > 1 else None
        prioritas_3 = sorted_indicators[2][0] if len(sorted_indicators) > 2 else None
        
        # Generate recommendation text based on priorities
        rekomendasi_teks = self._generate_recommendation_text(
            [p for p in [prioritas_1, prioritas_2, prioritas_3] if p], 
            jenjang
        )
        
        # Insert evaluation data
        cur.execute("""
            INSERT INTO kecamatan_evaluasi (
                result_id, kecamatan_id, cluster, is_medoid,
                standar_terpenuhi, total_standar, kualitas_pendidikan,
                prioritas_1, prioritas_2, prioritas_3, rekomendasi,
                x1_value, x2_value, x3_value, x4_value, x5_value, x6_value, x7_value,
                x1_status, x2_status, x3_status, x4_status, x5_status, x6_status, x7_status,
                x1_percentage, x2_percentage, x3_percentage, x4_percentage, x5_percentage, x6_percentage, x7_percentage,
                x1_description, x2_description, x3_description, x4_description, x5_description, x6_description, x7_description
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
        """, [
            result_id, kecamatan_id, cluster, cluster_is_medoid,
            standar_terpenuhi, len(INDICATORS), kualitas_pendidikan,
            prioritas_1, prioritas_2, prioritas_3, rekomendasi_teks,
            indicator_values['x1'], indicator_values['x2'], indicator_values['x3'], 
            indicator_values['x4'], indicator_values['x5'], indicator_values['x6'], 
            indicator_values['x7'],
            evaluations['x1']['status'], evaluations['x2']['status'], evaluations['x3']['status'], 
            evaluations['x4']['status'], evaluations['x5']['status'], evaluations['x6']['status'], 
            evaluations['x7']['status'],
            evaluations['x1']['percentage'], evaluations['x2']['percentage'], evaluations['x3']['percentage'], 
            evaluations['x4']['percentage'], evaluations['x5']['percentage'], evaluations['x6']['percentage'], 
            evaluations['x7']['percentage'],
            evaluations['x1']['description'], evaluations['x2']['description'], evaluations['x3']['description'], 
            evaluations['x4']['description'], evaluations['x5']['description'], evaluations['x6']['description'], 
            evaluations['x7']['description']
        ])

    def import_sekolah_data(self, file_path: str, result_id: int) -> Tuple[bool, str, int]:
        """
        Mengimpor data sekolah dari file CSV untuk melengkapi data kecamatan.
        
        Args:
            file_path: Path file CSV data sekolah
            result_id: ID hasil klasterisasi
            
        Returns:
            tuple: (success, message, count)
        """
        try:
            # Validasi input
            if not os.path.isfile(file_path):
                return False, f"File tidak ditemukan: {file_path}", 0
                
            if not isinstance(result_id, int) or result_id <= 0:
                return False, "ID hasil klasterisasi tidak valid", 0
            
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info first
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan", 0
            
            jenjang = result['jenjang']
            
            # Membaca data dari file CSV dan validasi
            try:
                # Try different encodings
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='iso-8859-1')
                    
                logger.info(f"Berhasil membaca file CSV sekolah: {file_path}")
            except pd.errors.EmptyDataError:
                return False, "File CSV kosong", 0
            except pd.errors.ParserError:
                return False, "Format CSV tidak valid", 0
            except Exception as e:
                return False, f"Error membaca file CSV: {str(e)}", 0
            
            # Validasi kolom minimal
            required_columns = ['nama_sekolah', 'kecamatan']
            for i in range(1, 8):
                required_columns.append(f'x{i}')
                
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                # Try to normalize columns first to handle variants
                df = self._normalize_csv_columns(df)
                
                # Check again after normalization
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return False, f"Kolom yang diperlukan tidak ditemukan: {missing_columns}", 0
            
            # Get mapping of kecamatan name to ID and cluster
            kecamatan_mapping, cluster_mapping = self._get_kecamatan_and_cluster_mapping(cur, result_id)
            
            # Process and save each school
            saved_count = self._process_and_save_schools(cur, df, result_id, jenjang, 
                                                    kecamatan_mapping, cluster_mapping)
            
            # Commit all changes
            self.db.connection.commit()
            
            return True, f"Berhasil mengimpor data {saved_count} sekolah", saved_count
            
        except Exception as e:
            # Rollback in case of error
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.error(f"Error dalam mengimpor data sekolah dari CSV: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}", 0

    def _get_kecamatan_and_cluster_mapping(self, cur, result_id: int) -> Tuple[Dict[str, int], Dict[int, int]]:
        """
        Get mapping of kecamatan names to IDs and kecamatan IDs to clusters
        
        Args:
            cur: Database cursor
            result_id: ID of the clustering result
            
        Returns:
            tuple: (kecamatan_mapping, cluster_mapping)
        """
        # Get kecamatan mapping (nama -> id)
        kecamatan_mapping = {}
        cur.execute("SELECT id, nama_kecamatan FROM kecamatan")
        for kec in cur.fetchall():
            kecamatan_mapping[kec['nama_kecamatan'].lower().strip()] = kec['id']
        
        # Get cluster mapping (kecamatan_id -> cluster)
        cluster_mapping = {}
        cur.execute("SELECT kecamatan_id, cluster FROM clustering_data WHERE result_id = %s", [result_id])
        for row in cur.fetchall():
            cluster_mapping[row['kecamatan_id']] = row['cluster']
            
        return kecamatan_mapping, cluster_mapping
            
    def _process_and_save_schools(self, cur, df: pd.DataFrame, result_id: int, jenjang: str,
                                kecamatan_mapping: Dict[str, int], cluster_mapping: Dict[int, int]) -> int:
        """
        Process and save school data from DataFrame
        
        Args:
            cur: Database cursor
            df: DataFrame with school data
            result_id: ID of the clustering result
            jenjang: Education level
            kecamatan_mapping: Mapping of kecamatan names to IDs
            cluster_mapping: Mapping of kecamatan IDs to clusters
            
        Returns:
            int: Number of saved schools
        """
        saved_count = 0
        
        for _, row in df.iterrows():
            try:
                # Get kecamatan_id from name
                kec_name = row['kecamatan'].lower().strip()
                kecamatan_id = kecamatan_mapping.get(kec_name)
                
                if not kecamatan_id:
                    # Try more flexible matching if exact match fails
                    for db_name, kec_id in kecamatan_mapping.items():
                        if kec_name in db_name or db_name in kec_name:
                            kecamatan_id = kec_id
                            logger.info(f"Fuzzy matched '{kec_name}' to '{db_name}'")
                            break
                
                if not kecamatan_id:
                    logger.warning(f"Kecamatan tidak ditemukan: {row['kecamatan']}")
                    continue
                
                # Get cluster from kecamatan
                cluster = cluster_mapping.get(kecamatan_id)
                if cluster is None:
                    logger.warning(f"Cluster tidak ditemukan untuk kecamatan: {row['kecamatan']}")
                    continue
                
                # Check if school already exists
                cur.execute("""
                    SELECT * FROM sekolah_data
                    WHERE result_id = %s AND nama_sekolah = %s AND kecamatan_id = %s
                """, [result_id, row['nama_sekolah'], kecamatan_id])
                
                existing_school = cur.fetchone()
                
                # Get additional fields with defaults
                additional_fields = self._extract_school_additional_fields(row)
                
                if existing_school:
                    # Update existing school
                    self._update_existing_school(cur, row, existing_school, additional_fields)
                    sekolah_id = existing_school['id']
                else:
                    # Create new school
                    sekolah_id = self._create_new_school(cur, row, result_id, kecamatan_id, 
                                                    jenjang, cluster, additional_fields)
                
                # Process priorities
                self._process_sekolah_priorities(cur, result_id, sekolah_id, row, jenjang)
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error processing school {row.get('nama_sekolah', 'unknown')}: {str(e)}")
                continue
                
        return saved_count
            
    def _extract_school_additional_fields(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extract additional fields from school data row
        
        Args:
            row: DataFrame row with school data
            
        Returns:
            dict: Additional fields
        """
        return {
            'alamat': row.get('alamat', ''),
            'status': row.get('status'),
            'jumlah_siswa': int(row['jumlah_siswa']) if 'jumlah_siswa' in row and not pd.isna(row['jumlah_siswa']) else None,
            'jumlah_guru': int(row['jumlah_guru']) if 'jumlah_guru' in row and not pd.isna(row['jumlah_guru']) else None,
            'jumlah_rombel': int(row['jumlah_rombel']) if 'jumlah_rombel' in row and not pd.isna(row['jumlah_rombel']) else None,
        }
            
    def _update_existing_school(self, cur, row: pd.Series, existing_school: Dict[str, Any], 
                            additional_fields: Dict[str, Any]) -> None:
        """
        Update existing school in database
        
        Args:
            cur: Database cursor
            row: DataFrame row with school data
            existing_school: Existing school record
            additional_fields: Additional fields
        """
        cur.execute("""
            UPDATE sekolah_data SET
            x1 = %s, x2 = %s, x3 = %s, x4 = %s, x5 = %s, x6 = %s, x7 = %s,
            alamat = %s, status = %s, jumlah_siswa = %s, jumlah_guru = %s, jumlah_rombel = %s
            WHERE id = %s
        """, [
            float(row['x1']), float(row['x2']), float(row['x3']), 
            float(row['x4']), float(row['x5']), float(row['x6']), float(row['x7']),
            additional_fields['alamat'], additional_fields['status'], 
            additional_fields['jumlah_siswa'], additional_fields['jumlah_guru'], 
            additional_fields['jumlah_rombel'],
            existing_school['id']
        ])
            
    def _create_new_school(self, cur, row: pd.Series, result_id: int, kecamatan_id: int,
                        jenjang: str, cluster: int, additional_fields: Dict[str, Any]) -> int:
        """
        Create new school in database
        
        Args:
            cur: Database cursor
            row: DataFrame row with school data
            result_id: ID of the clustering result
            kecamatan_id: ID of the kecamatan
            jenjang: Education level
            cluster: Cluster number
            additional_fields: Additional fields
            
        Returns:
            int: ID of the created school
        """
        cur.execute("""
            INSERT INTO sekolah_data
            (result_id, nama_sekolah, kecamatan_id, alamat, status, jenjang,
            x1, x2, x3, x4, x5, x6, x7, jumlah_siswa, jumlah_guru, jumlah_rombel, cluster)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            result_id, row['nama_sekolah'], kecamatan_id, 
            additional_fields['alamat'], additional_fields['status'], jenjang,
            float(row['x1']), float(row['x2']), float(row['x3']), 
            float(row['x4']), float(row['x5']), float(row['x6']), float(row['x7']),
            additional_fields['jumlah_siswa'], additional_fields['jumlah_guru'], 
            additional_fields['jumlah_rombel'], cluster
        ])
        
        # Get ID of inserted record
        cur.execute("SELECT LAST_INSERT_ID() as id")
        return cur.fetchone()['id']

    def _process_sekolah_priorities(self, cur, result_id: int, sekolah_id: int, 
                                row_data: pd.Series, jenjang: str) -> None:
        """
        Process and save school priorities based on indicators.
        
        Args:
            cur: Database cursor
            result_id: Clustering result ID
            sekolah_id: School ID
            row_data: Pandas row with school data
            jenjang: Educational level (SMA/SMK)
        """
        # Evaluate each indicator against standards
        evaluations = {}
        for indicator in INDICATORS:
            value = float(row_data[indicator])
            evaluations[indicator] = self._evaluate_indicator(indicator, value, jenjang)
        
        # Filter to only non-ideal indicators
        non_ideal_indicators = [
            (indicator, float(row_data[indicator]), evaluation) 
            for indicator, evaluation in evaluations.items()
            if evaluation['status'] != 'ideal'
        ]
        
        # Sort by percentage (ascending) to prioritize worst indicators
        non_ideal_indicators.sort(key=lambda x: x[2]['percentage'])
        
        # Process each non-ideal indicator
        for indicator, value, evaluation in non_ideal_indicators:
            gap = 100 - evaluation['percentage']
            urgensi = self._determine_urgency(gap)
            
            # Get ideal value for comparison
            ideal_value = self._get_ideal_value(indicator, jenjang)
            
            # Generate recommendation
            rekomendasi = self._generate_detailed_recommendation(indicator, value, ideal_value, jenjang)
            
            # Create or update priority
            self._create_or_update_priority(
                cur, result_id, sekolah_id, indicator, value, ideal_value, gap, urgensi, rekomendasi
            )

    def _get_ideal_value(self, indicator: str, jenjang: str) -> float:
        """
        Get ideal value for an indicator based on standards.
        
        Args:
            indicator: Indicator code
            jenjang: Educational level
            
        Returns:
            float: Ideal value
        """
        standar = self.standar_indikator
        
        if indicator == 'x1':
            return standar[indicator].get('max', 32)
        
        elif indicator == 'x2':
            key = 'max_sma' if jenjang == 'SMA' else 'max_smk'
            return standar[indicator].get(key, 20 if jenjang == 'SMA' else 15)
        
        elif indicator == 'x3':
            return standar[indicator].get('max', 32)
        
        elif indicator == 'x4':
            if jenjang == 'SMA':
                return (standar[indicator].get('min_sma', 3) + standar[indicator].get('max_sma', 27)) / 2
            else:
                return (standar[indicator].get('min_smk', 3) + standar[indicator].get('max_smk', 48)) / 2
        
        elif indicator in ['x5', 'x6', 'x7']:
            return standar[indicator].get('ideal', 1)
        
        return 0

    def _determine_urgency(self, gap_percentage: float) -> str:
        """
        Menentukan tingkat urgensi berdasarkan persentase gap
        
        Args:
            gap_percentage: Persentase gap (float)
            
        Returns:
            String yang menunjukkan tingkat urgensi ('tinggi', 'sedang', 'rendah')
        """
        if gap_percentage > 30:
            return 'tinggi'
        elif gap_percentage > 15:
            return 'sedang'
        else:
            return 'rendah'



    def _determine_medoid_optimized(self, cur, result_id: int, cluster: int, 
                                cluster_data: List[Dict[str, Any]],
                                cluster_averages: Dict[str, Any]) -> Dict[str, Any]:
        """
        Menentukan medoid untuk sebuah klaster secara dioptimasi.
        
        Args:
            cur: Database cursor
            result_id: ID hasil klasterisasi
            cluster: Nomor klaster
            cluster_data: Data cluster yang sudah dikalkulasi
            cluster_averages: Nilai rata-rata cluster
            
        Returns:
            dict: Informasi medoid (id dan nama)
        """
        # Hitung jarak kuadrat dari setiap titik ke pusat
        min_distance = float('inf')
        closest_point = None
        
        for point in cluster_data:
            distance = (
                (point['x1'] - cluster_averages['x1_avg'])**2 +
                (point['x2'] - cluster_averages['x2_avg'])**2 +
                (point['x3'] - cluster_averages['x3_avg'])**2 +
                (point['x4'] - cluster_averages['x4_avg'])**2 +
                (point['x5'] - cluster_averages['x5_avg'])**2 +
                (point['x6'] - cluster_averages['x6_avg'])**2 +
                (point['x7'] - cluster_averages['x7_avg'])**2
            )**0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_point = point
        
        if closest_point:
            # Perbarui titik ini sebagai medoid jika belum
            if not closest_point['is_medoid']:
                cur.execute("""
                    UPDATE clustering_data 
                    SET is_medoid = 1 
                    WHERE result_id = %s AND kecamatan_id = %s
                """, [result_id, closest_point['kecamatan_id']])
            
            return {
                'medoid_id': closest_point['kecamatan_id'],
                'medoid_name': closest_point['nama_kecamatan']
            }
        
        # Fallback jika tidak ada data
        return {'medoid_id': None, 'medoid_name': None}
        
        
        
    def _generate_detailed_recommendation(self, indicator: str, value: float, 
                                        ideal_value: float, jenjang: str) -> str:
        """
        Generate a detailed recommendation based on indicator and current value
        
        Args:
            indicator: Indicator code
            value: Current value
            ideal_value: Ideal value
            jenjang: Education level
            
        Returns:
            str: Detailed recommendation
        """
        if indicator == 'x1':
            gap = value - ideal_value if value > ideal_value else 0
            if gap > 0:
                return f"Perlu penambahan ruang kelas baru atau redistribusi siswa antar sekolah untuk mengurangi kepadatan kelas dan menciptakan lingkungan belajar yang lebih kondusif, sehingga interaksi antara guru dan siswa dapat lebih efektif. (saat ini {value:.2f}, ideal ≤ {ideal_value})"
            else:
                return f"Pertahankan rasio siswa per ruang kelas yang sudah ideal (saat ini {value:.2f}, ideal ≤ {ideal_value}) untuk menjaga kualitas pembelajaran."
        
        elif indicator == 'x2':
            gap = value - ideal_value if value > ideal_value else 0
            if gap > 0:
                return f"Perlu penambahan tenaga pengajar untuk mengurangi beban kerja guru dan memungkinkan perhatian yang lebih personal kepada setiap siswa, sehingga proses pembelajaran dapat lebih adaptif terhadap kebutuhan individu siswa. (saat ini {value:.2f}, ideal ≤ {ideal_value})"
            else:
                return f"Pertahankan rasio siswa per guru yang sudah ideal (saat ini {value:.2f}, ideal ≤ {ideal_value}) untuk menjaga kualitas pembelajaran dan perhatian personal kepada siswa."
        
        elif indicator == 'x3':
            gap = value - ideal_value if value > ideal_value else 0
            if gap > 0:
                return f"Perlu pengaturan ulang komposisi rombongan belajar untuk mencapai ukuran yang optimal, sehingga dinamika kelas lebih interaktif dan memungkinkan penggunaan metode pembelajaran kolaboratif yang efektif. (saat ini {value:.2f}, ideal ≤ {ideal_value})"
            else:
                return f"Pertahankan rasio siswa per rombel yang sudah ideal (saat ini {value:.2f}, ideal ≤ {ideal_value}) untuk menjaga kualitas pembelajaran dan interaksi dalam kelas."
        
        elif indicator == 'x4':
            standar = self.standar_indikator[indicator]
            min_val = standar[f'min_{jenjang.lower()}'] if f'min_{jenjang.lower()}' in standar else 3
            max_val = standar[f'max_{jenjang.lower()}'] if f'max_{jenjang.lower()}' in standar else (27 if jenjang == 'SMA' else 48)
            
            if value < min_val:
                return f"Perlu optimalisasi jumlah rombongan belajar di tiap sekolah untuk memastikan efisiensi manajemen sekolah, penggunaan sumber daya yang tepat, dan distribusi beban mengajar yang merata bagi tenaga pendidik. (saat ini {value:.2f}, minimal {min_val})"
            elif value > max_val:
                return f"Perlu evaluasi ulang jumlah rombongan belajar di tiap sekolah untuk memastikan efisiensi manajemen dan penggunaan sumber daya, serta menghindari beban berlebih pada infrastruktur sekolah. (saat ini {value:.2f}, maksimal {max_val})"
            else:
                return f"Pertahankan rasio rombel per sekolah yang sudah ideal (saat ini {value:.2f}, rentang ideal {min_val}-{max_val}) untuk menjaga efisiensi manajemen sekolah."
        
        elif indicator == 'x5':
            percentage = value * 100
            if percentage < 100:
                return f"Perlu pembangunan fasilitas perpustakaan di sekolah yang belum memilikinya untuk meningkatkan akses siswa terhadap sumber belajar, mendukung budaya literasi, dan memfasilitasi pembelajaran mandiri serta penelitian siswa. (saat ini {percentage:.2f}%, ideal 100%)"
            else:
                return f"Pertahankan ketersediaan perpustakaan yang sudah ideal (saat ini {percentage:.2f}%) dan tingkatkan kualitas koleksi serta layanan perpustakaan."
        
        elif indicator == 'x6':
            percentage = value * 100
            if percentage < 100:
                return f"Perlu pengadaan laboratorium di sekolah yang belum memilikinya untuk mendukung pembelajaran berbasis eksperimen, mengembangkan keterampilan praktis siswa, dan memberikan pengalaman belajar yang lebih konkret terutama pada mata pelajaran sains dan teknologi. (saat ini {percentage:.2f}%, ideal 100%)"
            else:
                return f"Pertahankan ketersediaan laboratorium yang sudah ideal (saat ini {percentage:.2f}%) dan tingkatkan kualitas peralatan serta bahan praktikum."
        
        elif indicator == 'x7':
            percentage = value * 100
            if percentage < 100:
                return f"Perlu memastikan ketersediaan ruang kelas yang memadai dan proporsional dengan jumlah rombongan belajar, sehingga jadwal pembelajaran dapat berjalan optimal tanpa terkendala keterbatasan ruang dan waktu. (saat ini {percentage:.2f}%, ideal 100%)"
            else:
                return f"Pertahankan ketersediaan ruang kelas yang sudah ideal (saat ini {percentage:.2f}%) dan tingkatkan kualitas dan fasilitas ruang kelas."
        
        return f"Evaluasi indikator {INDICATOR_DESCRIPTIONS.get(indicator, indicator)} untuk meningkatkan kualitas pendidikan"

    def _create_or_update_priority(self, cur, result_id: int, sekolah_id: int, 
                                indikator: str, nilai_current: float, nilai_ideal: float, 
                                gap: float, urgensi: str, rekomendasi: str) -> None:
        """
        Create or update school priority.
        
        Args:
            cur: Database cursor
            result_id: Clustering result ID
            sekolah_id: School ID
            indikator: Indicator code
            nilai_current: Current value
            nilai_ideal: Ideal value
            gap: Gap percentage
            urgensi: Urgency level
            rekomendasi: Recommendation text
        """
        # Check if priority exists
        cur.execute("""
            SELECT * FROM sekolah_prioritas
            WHERE result_id = %s AND sekolah_id = %s AND indikator = %s
        """, [result_id, sekolah_id, indikator])
        
        priority = cur.fetchone()
        
        if priority:
            # Update
            cur.execute("""
                UPDATE sekolah_prioritas SET
                nilai_current = %s,
                nilai_ideal = %s,
                gap = %s,
                urgensi = %s,
                rekomendasi = %s
                WHERE id = %s
            """, [
                nilai_current, 
                nilai_ideal, 
                gap, 
                urgensi, 
                rekomendasi,
                priority['id']
            ])
        else:
            # Create new
            cur.execute("""
                INSERT INTO sekolah_prioritas
                (result_id, sekolah_id, indikator, nilai_current, nilai_ideal, gap, urgensi, rekomendasi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                result_id,
                sekolah_id,
                indikator,
                nilai_current,
                nilai_ideal,
                gap,
                urgensi,
                rekomendasi
            ])

    def export_to_csv(self, result_id: int, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Mengekspor data hasil klasterisasi ke CSV.
        
        Args:
            result_id: ID hasil klasterisasi
            output_path: Path file output
            
        Returns:
            tuple: (success, file_path or error message)
        """
        try:
            # Validate input
            if not isinstance(result_id, int) or result_id <= 0:
                return False, "ID hasil klasterisasi tidak valid"
                
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            # Generate output path if not provided
            if output_path is None:
                output_path = os.path.join(self.output_dir, f'cluster_result_{result_id}.csv')
            
            # Memastikan direktori ada
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get data
            cur.execute("""
                SELECT cd.*, k.nama_kecamatan
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                WHERE cd.result_id = %s
                ORDER BY cd.cluster, k.nama_kecamatan
            """, [result_id])
            
            clustering_data = cur.fetchall()
            
            # Convert to DataFrame
            data = []
            for cd in clustering_data:
                row = {
                    'kecamatan': cd['nama_kecamatan'],
                    'cluster': cd['cluster'],
                    'is_medoid': cd['is_medoid'],
                    'x1': cd['x1'],
                    'x2': cd['x2'],
                    'x3': cd['x3'],
                    'x4': cd['x4'],
                    'x5': cd['x5'],
                    'x6': cd['x6'],
                    'x7': cd['x7']
                }
                if cd['dim1'] is not None:
                    row['dim1'] = cd['dim1']
                if cd['dim2'] is not None:
                    row['dim2'] = cd['dim2']
                
                data.append(row)
            
            df = pd.DataFrame(data)
            
            # Menyimpan ke CSV
            df.to_csv(output_path, index=False)
            logger.info(f"Data hasil klasterisasi disimpan ke {output_path}")
            
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def export_to_excel(self, result_id: int, output_path: Optional[str] = None, 
                    include_characteristics: bool = True) -> Tuple[bool, str]:
        """
        Mengekspor data hasil klasterisasi ke Excel dengan format yang ditingkatkan.
        
        Args:
            result_id: ID hasil klasterisasi
            output_path: Path file output
            include_characteristics: Whether to include cluster characteristics
            
        Returns:
            tuple: (success, file_path or error message)
        """
        try:
            # Validate input
            if not isinstance(result_id, int) or result_id <= 0:
                return False, "ID hasil klasterisasi tidak valid"
                
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            # Generate output path if not provided
            if output_path is None:
                output_path = os.path.join(self.output_dir, f'cluster_result_{result_id}.xlsx')
            
            # Memastikan direktori ada
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get data and prepare DataFrame
            df_kecamatan = self._prepare_kecamatan_dataframe(cur, result_id)
            
            # Ensure pandas and openpyxl are available
            try:
                import pandas as pd
                from openpyxl import Workbook
                from openpyxl.utils.dataframe import dataframe_to_rows
                from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            except ImportError:
                return False, "Error: Required libraries not installed. Install with 'pip install pandas openpyxl'"
            
            # Create Excel writer
            writer = pd.ExcelWriter(output_path, engine='openpyxl')
            
            # Write main data sheet
            df_kecamatan.to_excel(writer, sheet_name='Data Kecamatan', index=False)
            
            # Include additional data if requested
            if include_characteristics:
                self._add_characteristic_sheets(cur, writer, result_id, result['jenjang'])
            
            # Save the Excel file
            writer.close()
            
            logger.info(f"Data hasil klasterisasi diekspor ke Excel: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def _prepare_kecamatan_dataframe(self, cur, result_id: int) -> pd.DataFrame:
        """
        Prepare DataFrame of kecamatan data for export
        
        Args:
            cur: Database cursor
            result_id: ID of the clustering result
            
        Returns:
            DataFrame: Kecamatan data for export
        """
        # Get data
        cur.execute("""
            SELECT cd.*, k.nama_kecamatan
            FROM clustering_data cd
            JOIN kecamatan k ON cd.kecamatan_id = k.id
            WHERE cd.result_id = %s
            ORDER BY cd.cluster, k.nama_kecamatan
        """, [result_id])
        
        clustering_data = cur.fetchall()
        
        # Convert to DataFrame with better formatting
        data = []
        for cd in clustering_data:
            row = {
                'Kecamatan': cd['nama_kecamatan'],
                'Cluster': cd['cluster'],
                'Medoid': 'Ya' if cd['is_medoid'] else 'Tidak',
                'X1 (Rasio Siswa/Ruang Kelas)': cd['x1'],
                'X2 (Rasio Siswa/Guru)': cd['x2'],
                'X3 (Rasio Siswa/Rombel)': cd['x3'],
                'X4 (Rasio Rombel/Sekolah)': cd['x4'],
                'X5 (% Perpustakaan)': cd['x5'] * 100,
                'X6 (% Laboratorium)': cd['x6'] * 100,
                'X7 (% Ruang Kelas)': cd['x7'] * 100
            }
            
            if cd['dim1'] is not None and cd['dim2'] is not None:
                row['Dimensi 1'] = cd['dim1']
                row['Dimensi 2'] = cd['dim2']
            
            data.append(row)
        
        return pd.DataFrame(data)

    def _add_characteristic_sheets(self, cur, writer, result_id: int, jenjang: str) -> None:
        """
        Add characteristic-related sheets to Excel export
        
        Args:
            cur: Database cursor
            writer: Excel writer
            result_id: ID of the clustering result
            jenjang: Education level
        """
        # Get characteristics data
        cur.execute("""
            SELECT * FROM cluster_characteristics
            WHERE result_id = %s
            ORDER BY cluster
        """, [result_id])
        
        chars = cur.fetchall()
        
        if chars:
            chars_data = []
            for char in chars:
                # Get medoid name
                medoid_name = "-"
                if char['medoid_id']:
                    cur.execute("SELECT nama_kecamatan FROM kecamatan WHERE id = %s", [char['medoid_id']])
                    medoid_result = cur.fetchone()
                    if medoid_result:
                        medoid_name = medoid_result['nama_kecamatan']
                
                chars_data.append({
                    'Cluster': char['cluster'],
                    'Jumlah Anggota': char['jumlah_anggota'],
                    'Kualitas Pendidikan': char['kualitas_pendidikan'].capitalize(),
                    'Standar Terpenuhi': f"{char['standar_terpenuhi']} dari 7",
                    'Medoid': medoid_name,
                    'X1 (Rata-rata)': char['x1_avg'],
                    'X2 (Rata-rata)': char['x2_avg'],
                    'X3 (Rata-rata)': char['x3_avg'],
                    'X4 (Rata-rata)': char['x4_avg'],
                    'X5 (% Perpustakaan)': char['x5_avg'] * 100,
                    'X6 (% Laboratorium)': char['x6_avg'] * 100,
                    'X7 (% Ruang Kelas)': char['x7_avg'] * 100,
                    'Fitur Unggulan': char['fitur_tinggi'],
                    'Fitur Tantangan': char['fitur_rendah'],
                    'Interpretasi': char['interpretasi']
                })
            
            chars_df = pd.DataFrame(chars_data)
            chars_df.to_excel(writer, sheet_name='Karakteristik Klaster', index=False)
        
        # Add evaluations sheet
        self._add_evaluations_sheet(cur, writer, result_id)
        
        # Add indicator descriptions sheet
        self._add_indicator_descriptions_sheet(writer, jenjang)
        
        # Add recommendations sheet
        self._add_recommendations_sheet(cur, writer, result_id)

    def _add_evaluations_sheet(self, cur, writer, result_id: int) -> None:
        """
        Add evaluations sheet to Excel export
        
        Args:
            cur: Database cursor
            writer: Excel writer
            result_id: ID of the clustering result
        """
        cur.execute("""
            SELECT ke.*, k.nama_kecamatan
            FROM kecamatan_evaluasi ke
            JOIN kecamatan k ON ke.kecamatan_id = k.id
            WHERE ke.result_id = %s
            ORDER BY ke.cluster, k.nama_kecamatan
        """, [result_id])
        
        evals = cur.fetchall()
        
        if evals:
            evals_data = []
            for eval_row in evals:
                # Build single row with basic info
                row_data = {
                    'Kecamatan': eval_row['nama_kecamatan'],
                    'Cluster': eval_row['cluster'],
                    'Standar Terpenuhi': f"{eval_row['standar_terpenuhi']} dari {eval_row['total_standar']}",
                    'Kualitas Pendidikan': eval_row['kualitas_pendidikan'].capitalize()
                }
                
                # Add data for each indicator
                for ind in INDICATORS:
                    status = eval_row[f'{ind}_status']
                    percentage = eval_row[f'{ind}_percentage']
                    row_data[f'{ind} - Nilai'] = eval_row[f'{ind}_value']
                    row_data[f'{ind} - Status'] = 'Ideal' if status == 'ideal' else 'Perlu Perbaikan'
                    row_data[f'{ind} - Kesesuaian (%)'] = percentage
                
                evals_data.append(row_data)
            
            evals_df = pd.DataFrame(evals_data)
            evals_df.to_excel(writer, sheet_name='Evaluasi Kecamatan', index=False)

    def _add_indicator_descriptions_sheet(self, writer, jenjang: str) -> None:
        """
        Add indicator descriptions sheet to Excel export
        
        Args:
            writer: Excel writer
            jenjang: Education level
        """
        # Create indicator descriptions
        indicator_desc = [
            {'Indikator': 'x1', 'Kode': 'X1', 'Deskripsi': 'Rasio Siswa per Ruang Kelas', 'Standar Ideal': '≤ 32 siswa per ruang kelas (Permendiknas No. 41 Tahun 2007)', 'Implikasi': INDICATOR_CONTEXTS['x1']},
            {'Indikator': 'x2 (SMA)', 'Kode': 'X2', 'Deskripsi': 'Rasio Siswa per Guru (SMA)', 'Standar Ideal': '≤ 20 siswa per guru (PP No. 74 Tahun 2008)', 'Implikasi': INDICATOR_CONTEXTS['x2']},
            {'Indikator': 'x2 (SMK)', 'Kode': 'X2', 'Deskripsi': 'Rasio Siswa per Guru (SMK)', 'Standar Ideal': '≤ 15 siswa per guru (PP No. 74 Tahun 2008)', 'Implikasi': INDICATOR_CONTEXTS['x2']},
            {'Indikator': 'x3', 'Kode': 'X3', 'Deskripsi': 'Rasio Siswa per Rombel', 'Standar Ideal': '≤ 32 siswa per rombel (Permendiknas No. 41 Tahun 2007)', 'Implikasi': INDICATOR_CONTEXTS['x3']},
            {'Indikator': 'x4 (SMA)', 'Kode': 'X4', 'Deskripsi': 'Rasio Rombel per Sekolah (SMA)', 'Standar Ideal': '3-27 rombel per sekolah (Permendiknas No. 24 Tahun 2007)', 'Implikasi': INDICATOR_CONTEXTS['x4']},
            {'Indikator': 'x4 (SMK)', 'Kode': 'X4', 'Deskripsi': 'Rasio Rombel per Sekolah (SMK)', 'Standar Ideal': '3-48 rombel per sekolah (Permendiknas No. 40 Tahun 2008)', 'Implikasi': INDICATOR_CONTEXTS['x4']},
            {'Indikator': 'x5', 'Kode': 'X5', 'Deskripsi': 'Persentase Ketersediaan Perpustakaan', 'Standar Ideal': '100% (Nilai 1.0 berarti 100% sekolah memiliki perpustakaan)', 'Implikasi': INDICATOR_CONTEXTS['x5']},
            {'Indikator': 'x6', 'Kode': 'X6', 'Deskripsi': 'Persentase Ketersediaan Laboratorium', 'Standar Ideal': '100% (Nilai 1.0 berarti 100% sekolah memiliki laboratorium)', 'Implikasi': INDICATOR_CONTEXTS['x6']},
            {'Indikator': 'x7', 'Kode': 'X7', 'Deskripsi': 'Persentase Ketersediaan Ruang Kelas', 'Standar Ideal': '100% (Nilai 1.0 berarti 100% sekolah memiliki ruang kelas yang memadai)', 'Implikasi': INDICATOR_CONTEXTS['x7']}
        ]
        
        pd.DataFrame(indicator_desc).to_excel(writer, sheet_name='Penjelasan Indikator', index=False)

    def _add_recommendations_sheet(self, cur, writer, result_id: int) -> None:
        """
        Add recommendations sheet to Excel export
        
        Args:
            cur: Database cursor
            writer: Excel writer
            result_id: ID of the clustering result
        """
        cur.execute("""
            SELECT ke.*, k.nama_kecamatan
            FROM kecamatan_evaluasi ke
            JOIN kecamatan k ON ke.kecamatan_id = k.id
            WHERE ke.result_id = %s
            ORDER BY k.nama_kecamatan
        """, [result_id])
        
        recs = cur.fetchall()
        
        if recs:
            recs_data = []
            for rec in recs:
                row_data = {
                    'Kecamatan': rec['nama_kecamatan'],
                    'Cluster': rec['cluster'],
                    'Kualitas Pendidikan': rec['kualitas_pendidikan'].capitalize()
                }
                
                # Add priority recommendations
                for i in range(1, 4):
                    priority_indicator = rec[f'prioritas_{i}']
                    if priority_indicator:
                        row_data[f'Prioritas {i}'] = INDICATOR_DESCRIPTIONS.get(priority_indicator, '')
                        description_field = f'x{priority_indicator[-1]}_description'
                        if description_field in rec and rec[description_field]:
                            row_data[f'Rekomendasi {i}'] = rec[description_field]
                
                recs_data.append(row_data)
            
            recs_df = pd.DataFrame(recs_data)
            recs_df.to_excel(writer, sheet_name='Rekomendasi Perbaikan', index=False)

    def export_to_pdf(self, result_id: int, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Mengekspor data hasil klasterisasi ke PDF.
        
        Args:
            result_id: ID hasil klasterisasi
            output_path: Path file output
            
        Returns:
            tuple: (success, file_path or error message)
        """
        try:
            # ReportLab library check
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
            except ImportError:
                return False, "Error: ReportLab package not installed. Install with 'pip install reportlab'"
            
            # Validate input
            if not isinstance(result_id, int) or result_id <= 0:
                return False, "ID hasil klasterisasi tidak valid"
                
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            # Generate output path if not provided
            if output_path is None:
                output_path = os.path.join(self.output_dir, f'cluster_result_{result_id}.pdf')
            
            # Memastikan direktori ada
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create the PDF document and build content
            self._build_pdf_document(cur, result, output_path)
            
            logger.info(f"Data hasil klasterisasi diekspor ke PDF: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def _build_pdf_document(self, cur, result: Dict[str, Any], output_path: str) -> None:
        """
        Build PDF document with clustering results
        
        Args:
            cur: Database cursor
            result: Clustering result info
            output_path: Output file path
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(letter),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Create custom styles
        styles.add(ParagraphStyle(
            name='SmallText',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=6
        ))
        
        # Create story elements
        elements = []
        
        # Add title
        title = Paragraph(f"Hasil Klasterisasi {result['jenjang']} - Skenario {result['skenario']}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.25*inch))
        
        # Add description
        if result.get('description'):
            desc = Paragraph(f"Deskripsi: {result['description']}", normal_style)
            elements.append(desc)
            elements.append(Spacer(1, 0.1*inch))
        
        # Add metadata
        metadata = [
            f"Jenjang: {result['jenjang']}",
            f"Skenario: {result['skenario']}",
            f"Jumlah Klaster: {result['jumlah_cluster']}",
            f"Tanggal Import: {result['imported_at'].strftime('%d %B %Y, %H:%M') if result.get('imported_at') else 'N/A'}"
        ]
        
        for line in metadata:
            elements.append(Paragraph(line, normal_style))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Add cluster characteristics
        self._add_cluster_characteristics_to_pdf(cur, result, elements, styles, subtitle_style)
        
        # Add data kecamatan
        self._add_kecamatan_data_to_pdf(cur, result, elements, styles, subtitle_style)
        
        # Add explanation of indicators
        self._add_indicator_explanation_to_pdf(elements, styles, subtitle_style)
        
        # Add footer with timestamp
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Laporan dibuat pada: {datetime.now().strftime('%d %B %Y, %H:%M')}", styles['SmallText']))
        
        # Build the PDF
        doc.build(elements)

    def _add_cluster_characteristics_to_pdf(self, cur, result: Dict[str, Any], elements: List, 
                                        styles, subtitle_style) -> None:
        """
        Add cluster characteristics section to PDF
        
        Args:
            cur: Database cursor
            result: Clustering result info
            elements: PDF elements list
            styles: PDF styles
            subtitle_style: Subtitle style
        """
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
        
        elements.append(Paragraph("Karakteristik Klaster", subtitle_style))
        elements.append(Spacer(1, 0.1*inch))
        
        cur.execute("""
            SELECT * FROM cluster_characteristics
            WHERE result_id = %s
            ORDER BY cluster
        """, [result['id']])
        
        chars = cur.fetchall()
        
        for char in chars:
            # Get medoid name
            medoid_name = "-"
            if char['medoid_id']:
                cur.execute("SELECT nama_kecamatan FROM kecamatan WHERE id = %s", [char['medoid_id']])
                medoid_result = cur.fetchone()
                if medoid_result:
                    medoid_name = medoid_result['nama_kecamatan']
            
            quality_level = char['kualitas_pendidikan'].capitalize()
            elements.append(Paragraph(f"Klaster {char['cluster']} - Kualitas Pendidikan: {quality_level}", styles['Heading3']))
            elements.append(Spacer(1, 0.05*inch))
            
            # Create a table for cluster info
            cluster_data = [
                ["Jumlah Anggota", f"{char['jumlah_anggota']}"],
                ["Standar Terpenuhi", f"{char['standar_terpenuhi']} dari 7"],
                ["Medoid", medoid_name]
            ]
            
            t_info = Table(cluster_data, colWidths=[1.5*inch, 2*inch])
            t_info.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(t_info)
            elements.append(Spacer(1, 0.1*inch))
            
            # Create a table for indicator values
            jenjang = result['jenjang']
            self._add_indicator_table_to_pdf(elements, char, jenjang)
            
            # Add interpretation and recommendations
            elements.append(Paragraph("Interpretasi:", styles['Heading4']))
            elements.append(Paragraph(char['interpretasi'], styles['Normal']))
            elements.append(Spacer(1, 0.05*inch))
            
            elements.append(Paragraph("Rekomendasi:", styles['Heading4']))
            elements.append(Paragraph(char['rekomendasi'], styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

  
    def _add_indicator_table_to_pdf(self, elements: List, char: Dict[str, Any], jenjang: str) -> None:
        """
        Add indicator values table to PDF
        
        Args:
            elements: PDF elements list
            char: Cluster characteristics
            jenjang: Education level
        """
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        # Create a table for indicator values
        char_data = [
            ["Indikator", "Nilai Rata-rata", "Status"],
            ["Rasio Siswa per Ruang Kelas (X1)", f"{char['x1_avg']:.2f}", 
            "Ideal" if self._evaluate_indicator('x1', char['x1_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Rasio Siswa per Guru (X2)", f"{char['x2_avg']:.2f}", 
            "Ideal" if self._evaluate_indicator('x2', char['x2_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Rasio Siswa per Rombel (X3)", f"{char['x3_avg']:.2f}", 
            "Ideal" if self._evaluate_indicator('x3', char['x3_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Rasio Rombel per Sekolah (X4)", f"{char['x4_avg']:.2f}", 
            "Ideal" if self._evaluate_indicator('x4', char['x4_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Persentase Perpustakaan (X5)", f"{char['x5_avg']*100:.2f}%", 
            "Ideal" if self._evaluate_indicator('x5', char['x5_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Persentase Laboratorium (X6)", f"{char['x6_avg']*100:.2f}%", 
            "Ideal" if self._evaluate_indicator('x6', char['x6_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"],
            ["Persentase Ruang Kelas (X7)", f"{char['x7_avg']*100:.2f}%", 
            "Ideal" if self._evaluate_indicator('x7', char['x7_avg'], jenjang)['status'] == 'ideal' else "Perlu Perbaikan"]
        ]
        
        # Create a table for the data
        t = Table(char_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (2, 1), (2, -1), 
            lambda x, y: colors.lightgreen if y % 8 != 0 and char_data[y][2] == 'Ideal' else colors.salmon)
        ]))
        
        elements.append(t)

    def _add_kecamatan_data_to_pdf(self, cur, result: Dict[str, Any], elements: List, 
                                styles, subtitle_style) -> None:
        """
        Add kecamatan data section to PDF
        
        Args:
            cur: Database cursor
            result: Clustering result info
            elements: PDF elements list
            styles: PDF styles
            subtitle_style: Subtitle style
        """
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        elements.append(Paragraph("Data Per Kecamatan (Ringkasan)", subtitle_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Get kecamatan data
        cur.execute("""
            SELECT cd.*, k.nama_kecamatan, ke.standar_terpenuhi, ke.kualitas_pendidikan
            FROM clustering_data cd
            JOIN kecamatan k ON cd.kecamatan_id = k.id
            LEFT JOIN kecamatan_evaluasi ke ON cd.result_id = ke.result_id AND cd.kecamatan_id = ke.kecamatan_id
            WHERE cd.result_id = %s
            ORDER BY cd.cluster, k.nama_kecamatan
        """, [result['id']])
        
        kecamatan_data = cur.fetchall()
        
        # Prepare data for table
        kecamatan_table_data = [["Kecamatan", "Klaster", "Standar Terpenuhi", "X1", "X2", "X3", "X4", "X5", "X6", "X7"]]
        
        for data in kecamatan_data:
            kecamatan_table_data.append([
                data['nama_kecamatan'],
                str(data['cluster']),
                f"{data['standar_terpenuhi'] if data['standar_terpenuhi'] else 0}/7",
                f"{data['x1']:.2f}",
                f"{data['x2']:.2f}",
                f"{data['x3']:.2f}",
                f"{data['x4']:.2f}",
                f"{data['x5']*100:.1f}%",
                f"{data['x6']*100:.1f}%",
                f"{data['x7']*100:.1f}%"
            ])
        
        # Create a table for kecamatan data
        t = Table(kecamatan_table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Left-align kecamatan names
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(t)

    def _add_indicator_explanation_to_pdf(self, elements: List, styles, subtitle_style) -> None:
        """
        Add indicator explanation section to PDF
        
        Args:
            elements: PDF elements list
            styles: PDF styles
            subtitle_style: Subtitle style
        """
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        # Add explanation of indicators
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("Penjelasan Indikator", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))
        
        indicator_text = """
        <b>X1:</b> Rasio Siswa per Ruang Kelas (≤ 32) - Ruang kelas yang tidak terlalu padat memungkinkan pembelajaran yang lebih efektif<br/>
        <b>X2:</b> Rasio Siswa per Guru (≤ 20 untuk SMA, ≤ 15 untuk SMK) - Guru dapat memberikan perhatian lebih pada setiap siswa<br/>
        <b>X3:</b> Rasio Siswa per Rombel (≤ 32) - Rombongan belajar yang ideal memungkinkan interaksi yang lebih baik<br/>
        <b>X4:</b> Rasio Rombel per Sekolah (3-27 SMA, 3-48 SMK) - Jumlah rombel yang tepat memungkinkan manajemen sekolah yang efisien<br/>
        <b>X5:</b> Persentase Perpustakaan (100%) - Perpustakaan mendukung literasi dan penelitian<br/>
        <b>X6:</b> Persentase Laboratorium (100%) - Laboratorium mendukung pembelajaran praktik dan eksperimental<br/>
        <b>X7:</b> Persentase Ruang Kelas (100%) - Ruang kelas yang memadai mendukung proses belajar mengajar
        """
        
        elements.append(Paragraph(indicator_text, styles['SmallText']))

    def get_cluster_data_for_map(self, result_id: int) -> Dict[str, Any]:
        """
        Get data for map visualization.
        
        Args:
            result_id: ID hasil klasterisasi
            
        Returns:
            dict: Map data including kecamatan info and cluster counts
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get kecamatan data with coordinates
            cur.execute("""
                SELECT cd.cluster, k.nama_kecamatan, k.latitude, k.longitude, ke.standar_terpenuhi
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                LEFT JOIN kecamatan_evaluasi ke ON cd.result_id = ke.result_id AND cd.kecamatan_id = ke.kecamatan_id
                WHERE cd.result_id = %s
                ORDER BY cd.cluster, k.nama_kecamatan
            """, [result_id])
            
            kecamatan_data = cur.fetchall()
            
            # Get cluster characteristics
            cur.execute("""
                SELECT * FROM cluster_characteristics
                WHERE result_id = %s
                ORDER BY cluster
            """, [result_id])
            
            cluster_chars = cur.fetchall()
            
            # Build map data
            kecamatan_list = []
            for data in kecamatan_data:
                if data['latitude'] is not None and data['longitude'] is not None:
                    kecamatan_list.append({
                        'nama': data['nama_kecamatan'],
                        'cluster': data['cluster'],
                        'latitude': data['latitude'],
                        'longitude': data['longitude'],
                        'standar_terpenuhi': data['standar_terpenuhi'] if data['standar_terpenuhi'] else 0
                    })
            
            # Build cluster info
            cluster_info = {}
            for char in cluster_chars:
                # Map color based on quality level
                map_colors = {
                    'sangat tinggi': '#1a9641',  # Dark green
                    'tinggi': '#a6d96a',        # Light green
                    'sedang': '#ffffbf',        # Yellow
                    'rendah': '#fdae61',        # Orange
                    'sangat rendah': '#d7191c'  # Red
                }
                
                warna_peta = map_colors.get(char['kualitas_pendidikan'], '#ffffbf')
                
                # Format percentage values for display
                x5_percent = f"{char['x5_avg']*100:.1f}%"
                x6_percent = f"{char['x6_avg']*100:.1f}%"
                x7_percent = f"{char['x7_avg']*100:.1f}%"
                
                cluster_info[char['cluster']] = {
                    'count': char['jumlah_anggota'],
                    'kualitas_pendidikan': char['kualitas_pendidikan'].capitalize(),
                    'standar_terpenuhi': f"{char['standar_terpenuhi']} dari 7",
                    'x1_avg': f"{char['x1_avg']:.2f}",
                    'x2_avg': f"{char['x2_avg']:.2f}",
                    'x3_avg': f"{char['x3_avg']:.2f}",
                    'x4_avg': f"{char['x4_avg']:.2f}",
                    'x5_avg': x5_percent,
                    'x6_avg': x6_percent,
                    'x7_avg': x7_percent,
                    'fitur_tinggi': char['fitur_tinggi'],
                    'fitur_rendah': char['fitur_rendah'],
                    'interpretasi': char['interpretasi'],
                    'rekomendasi': char['rekomendasi'],
                    'warna': warna_peta
                }
            
            return {
                'kecamatan': kecamatan_list,
                'cluster_info': cluster_info
            }
            
        except Exception as e:
            logger.error(f"Error getting map data for result {result_id}: {str(e)}", exc_info=True)
            return {'kecamatan': [], 'cluster_info': {}}

    def get_cluster_evaluation_data(self, result_id: int) -> Dict[str, Any]:
        """
        Get evaluation data for all clusters dengan perbaikan perhitungan dan tampilan.
        
        Args:
            result_id: ID of the clustering result
                
        Returns:
            dict: Evaluation data for all indicators across clusters
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info to access jenjang
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result_info = cur.fetchone()
            
            if not result_info:
                logger.error(f"Result with ID {result_id} not found")
                return {}
                    
            jenjang = result_info['jenjang']
            logger.info(f"Processing evaluation data for result_id={result_id}, jenjang={jenjang}")
            
            # Get cluster characteristics to access average values
            cur.execute("""
                SELECT cluster, x1_avg, x2_avg, x3_avg, x4_avg, x5_avg, x6_avg, x7_avg, jumlah_anggota
                FROM cluster_characteristics
                WHERE result_id = %s
                ORDER BY cluster
            """, [result_id])
            
            cluster_chars = cur.fetchall()
            
            if not cluster_chars:
                logger.warning(f"No cluster characteristics found for result_id={result_id}")
                return {}
            
            # Organize data by indicator and cluster
            evaluation_data = {}
            cluster_weights = {}  # Store cluster weights (jumlah_anggota) for weighted averages
            total_members = 0
            
            # Initialize structure
            for indicator in INDICATORS:
                evaluation_data[indicator] = {
                    'name': INDICATOR_DESCRIPTIONS[indicator],
                    'context': INDICATOR_CONTEXTS[indicator],
                    'clusters': {},
                    'overall': {
                        'avg_value': 0,
                        'percentage': 0,
                        'status': 'unknown',
                        'description': ''
                    }
                }
            
            # Process each cluster and calculate evaluations
            for char in cluster_chars:
                cluster = char['cluster']
                cluster_weights[cluster] = char['jumlah_anggota']
                total_members += char['jumlah_anggota']
                
                # Process each indicator
                for indicator in INDICATORS:
                    avg_value_field = f'{indicator}_avg'
                    avg_value = char[avg_value_field]
                    
                    # Evaluate the indicator with the fixed evaluation function
                    eval_result = self._evaluate_indicator(indicator, avg_value, jenjang)
                    
                    # Store evaluation in data structure
                    evaluation_data[indicator]['clusters'][cluster] = {
                        'avg_value': avg_value,
                        'percentage': eval_result['percentage'],
                        'status': eval_result['status'],
                        'description': eval_result['description']
                    }
                    
                    logger.debug(f"Evaluated {indicator} for cluster {cluster}: value={avg_value}, status={eval_result['status']}")
            
            # Calculate weighted overall averages for each indicator
            for indicator in INDICATORS:
                weighted_sum_value = 0
                weighted_sum_percentage = 0
                
                for cluster, weight in cluster_weights.items():
                    if cluster in evaluation_data[indicator]['clusters']:
                        cluster_data = evaluation_data[indicator]['clusters'][cluster]
                        weight_factor = weight / total_members if total_members > 0 else 0
                        
                        weighted_sum_value += cluster_data['avg_value'] * weight_factor
                        weighted_sum_percentage += cluster_data['percentage'] * weight_factor
                
                # Round values for readability
                avg_value = round(weighted_sum_value, 2)
                avg_percentage = round(weighted_sum_percentage, 2)
                
                # Evaluate the average value to get status and description
                eval_result = self._evaluate_indicator(indicator, avg_value, jenjang)
                
                evaluation_data[indicator]['overall'] = {
                    'avg_value': avg_value,
                    'percentage': avg_percentage,
                    'status': eval_result['status'],
                    'description': eval_result['description']
                }
                
                logger.info(f"Overall {indicator}: avg_value={avg_value}, percentage={avg_percentage}%, status={eval_result['status']}")

            # Add standar indikator to the response for frontend
            standar_data = {}
            for indicator in INDICATORS:
                desc = INDICATOR_DESCRIPTIONS[indicator]
                context = INDICATOR_CONTEXTS[indicator]
                standard = self._get_indicator_standard(indicator, jenjang)
                
                standar_data[indicator] = {
                    'desc': desc,
                    'context': context,
                    'standard': standard
                }
            
            return {
                'evaluation_data': evaluation_data,
                'standar_indikator': standar_data,
                'jenjang': jenjang
            }
                
        except Exception as e:
            logger.error(f"Error getting evaluation data for result {result_id}: {str(e)}", exc_info=True)
            return {}

    def _get_indicator_standard(self, indicator: str, jenjang: str) -> str:
        """
        Get standard text description for an indicator
        
        Args:
            indicator: Indicator code
            jenjang: Education level
            
        Returns:
            str: Standard description
        """
        if indicator == 'x1':
            return '≤ 32 siswa/ruang kelas (Permendiknas No. 41 Tahun 2007)'
        elif indicator == 'x2':
            if jenjang == 'SMA':
                return '≤ 20 siswa/guru (PP No. 74 Tahun 2008)'
            else:
                return '≤ 15 siswa/guru (PP No. 74 Tahun 2008)'
        elif indicator == 'x3':
            return '≤ 32 siswa/rombel (Permendiknas No. 41 Tahun 2007)'
        elif indicator == 'x4':
            if jenjang == 'SMA':
                return '3-27 rombel/sekolah (Permendiknas No. 24 Tahun 2007)'
            else:
                return '3-48 rombel/sekolah (Permendiknas No. 40 Tahun 2008)'
        elif indicator == 'x5':
            return '100% ketersediaan perpustakaan'
        elif indicator == 'x6':
            return '100% ketersediaan laboratorium'
        elif indicator == 'x7':
            return '100% ketersediaan ruang kelas yang memadai'
        else:
            return 'Standar tidak tersedia'

    def get_available_clustering_results(self) -> List[Dict[str, Any]]:
        """
        Get all available clustering results.
        
        Returns:
            list: List of result info dictionaries
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get results with process info
            cur.execute("""
                SELECT r.*, p.created_by, 
                (SELECT COUNT(*) FROM clustering_data WHERE result_id = r.id) as kecamatan_count
                FROM clustering_results r
                JOIN clustering_processes p ON r.process_id = p.id
                ORDER BY r.imported_at DESC
            """)
            
            results = cur.fetchall()
            
            result_list = []
            for res in results:
                result_list.append({
                    'id': res['id'],
                    'jenjang': res['jenjang'],
                    'skenario': res['skenario'],
                    'jumlah_cluster': res['jumlah_cluster'],
                    'description': res['description'],
                    'imported_at': res['imported_at'],
                    'status': res['status'],
                    'process_id': res['process_id'],
                    'created_by': res['created_by'],
                    'kecamatan_count': res['kecamatan_count']
                })
        
            return result_list
            
        except Exception as e:
            logger.error(f"Error getting clustering results: {str(e)}", exc_info=True)
            return []

    def get_clustering_result(self, result_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed info for a specific clustering result.
        
        Args:
            result_id: ID of clustering result
            
        Returns:
            dict: Result info or None if not found
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result with process info
            cur.execute("""
                SELECT r.*, p.created_by, 
                (SELECT COUNT(*) FROM clustering_data WHERE result_id = r.id) as kecamatan_count,
                (SELECT COUNT(*) FROM sekolah_data WHERE result_id = r.id) as sekolah_count
                FROM clustering_results r
                JOIN clustering_processes p ON r.process_id = p.id
                WHERE r.id = %s
            """, [result_id])
            
            result = cur.fetchone()
            
            if not result:
                return None
            
            # Get cluster counts
            cur.execute("""
                SELECT cluster, COUNT(*) as count
                FROM clustering_data
                WHERE result_id = %s
                GROUP BY cluster
                ORDER BY cluster
            """, [result_id])
            
            cluster_counts = cur.fetchall()
            cluster_distribution = {str(row['cluster']): row['count'] for row in cluster_counts}
            
            # Get quality levels distribution
            cur.execute("""
                SELECT cc.kualitas_pendidikan, COUNT(*) as count
                FROM cluster_characteristics cc
                WHERE cc.result_id = %s
                GROUP BY cc.kualitas_pendidikan
            """, [result_id])
            
            quality_levels = cur.fetchall()
            quality_distribution = {row['kualitas_pendidikan']: row['count'] for row in quality_levels}
            
            # Build result info
            result_info = {
                'id': result['id'],
                'process_id': result['process_id'],
                'jenjang': result['jenjang'],
                'skenario': result['skenario'],
                'jumlah_cluster': result['jumlah_cluster'],
                'kecamatan_count': result['kecamatan_count'],
                'sekolah_count': result['sekolah_count'],
                'description': result['description'],
                'imported_at': result['imported_at'],
                'status': result['status'],
                'created_by': result['created_by'],
                'cluster_distribution': cluster_distribution,
                'quality_distribution': quality_distribution
            }
            
            return result_info
            
        except Exception as e:
            logger.error(f"Error getting clustering result {result_id}: {str(e)}", exc_info=True)
            return None

    def get_kecamatan_data(self, result_id: int, cluster_filter: Optional[int] = None, sort_by: str = 'nama') -> List[Dict[str, Any]]:
        """
        Get kecamatan data for a specific clustering result.
        
        Args:
            result_id: ID of clustering result
            cluster_filter: Filter by cluster
            sort_by: Sort field ('nama', 'cluster', 'rank')
            
        Returns:
            list: List of kecamatan data dictionaries
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Build query
            query = """
                SELECT cd.*, k.nama_kecamatan, ke.standar_terpenuhi, ke.kualitas_pendidikan
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                LEFT JOIN kecamatan_evaluasi ke ON cd.result_id = ke.result_id AND cd.kecamatan_id = ke.kecamatan_id
                WHERE cd.result_id = %s
            """
            params = [result_id]
            
            # Apply cluster filter if specified
            if cluster_filter is not None:
                query += " AND cd.cluster = %s"
                params.append(cluster_filter)
            
            # Apply sorting
            if sort_by == 'nama' or sort_by == 'kecamatan':
                query += " ORDER BY k.nama_kecamatan"
            elif sort_by == 'cluster':
                query += " ORDER BY cd.cluster, k.nama_kecamatan"
            elif sort_by == 'standar_terpenuhi':
                query += " ORDER BY ke.standar_terpenuhi DESC, k.nama_kecamatan"
            elif sort_by.startswith('x') and sort_by[1:].isdigit():
                # Sort by indicator
                indicator = sort_by
                query += f" ORDER BY cd.{indicator} DESC, k.nama_kecamatan"
            else:
                query += " ORDER BY k.nama_kecamatan"  # Default sorting
            
            # Execute query
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Convert to list of dictionaries
            data_list = []
            for data in results:
                # Get evaluations for this kecamatan
                cur.execute("""
                    SELECT prioritas_1, prioritas_2, prioritas_3, rekomendasi
                    FROM kecamatan_evaluasi
                    WHERE result_id = %s AND kecamatan_id = %s
                """, [result_id, data['kecamatan_id']])
                
                evaluasi = cur.fetchone()
                recommendations = []
                
                if evaluasi:
                    if evaluasi['prioritas_1']:
                        recommendations.append({
                            'indicator': evaluasi['prioritas_1'],
                            'name': INDICATOR_DESCRIPTIONS.get(evaluasi['prioritas_1'], evaluasi['prioritas_1'])
                        })
                    if evaluasi['prioritas_2']:
                        recommendations.append({
                            'indicator': evaluasi['prioritas_2'],
                            'name': INDICATOR_DESCRIPTIONS.get(evaluasi['prioritas_2'], evaluasi['prioritas_2'])
                        })
                    if evaluasi['prioritas_3']:
                        recommendations.append({
                            'indicator': evaluasi['prioritas_3'],
                            'name': INDICATOR_DESCRIPTIONS.get(evaluasi['prioritas_3'], evaluasi['prioritas_3'])
                        })
                
                data_list.append({
                    'id': data['id'],
                    'kecamatan_id': data['kecamatan_id'],
                    'nama_kecamatan': data['nama_kecamatan'],
                    'cluster': data['cluster'],
                    'is_medoid': bool(data['is_medoid']),
                    'x1': data['x1'],
                    'x2': data['x2'],
                    'x3': data['x3'],
                    'x4': data['x4'],
                    'x5': data['x5'],
                    'x6': data['x6'],
                    'x7': data['x7'],
                    'dim1': data['dim1'],
                    'dim2': data['dim2'],
                    'standar_terpenuhi': data['standar_terpenuhi'] if data.get('standar_terpenuhi') is not None else 0,
                    'kualitas_pendidikan': data['kualitas_pendidikan'] if data.get('kualitas_pendidikan') else 'tidak diketahui',
                    'prioritas': recommendations,
                    'rekomendasi': evaluasi['rekomendasi'] if evaluasi and evaluasi.get('rekomendasi') else ""
                })
            
            return data_list
            
        except Exception as e:
            logger.error(f"Error getting kecamatan data for result {result_id}: {str(e)}", exc_info=True)
            return []

    def get_sekolah_data(self, result_id: int, kecamatan_id: Optional[int] = None, 
                    status: Optional[str] = None, sort_by: str = 'nama_sekolah') -> List[Dict[str, Any]]:
        """
        Get school data for a specific clustering result.
        
        Args:
            result_id: ID of clustering result
            kecamatan_id: Filter by kecamatan
            status: Filter by status ('Negeri'/'Swasta')
            sort_by: Sort field ('nama_sekolah', 'kecamatan', 'cluster')
            
        Returns:
            list: List of school data dictionaries
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info first to access jenjang
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result_info = cur.fetchone()
            
            if not result_info:
                return []
                
            jenjang = result_info['jenjang']
            
            # Build query
            query = """
                SELECT s.*, k.nama_kecamatan
                FROM sekolah_data s
                JOIN kecamatan k ON s.kecamatan_id = k.id
                WHERE s.result_id = %s
            """
            params = [result_id]
            
            # Apply filters
            if kecamatan_id is not None:
                query += " AND s.kecamatan_id = %s"
                params.append(kecamatan_id)
            
            if status is not None:
                query += " AND s.status = %s"
                params.append(status)
            
            # Apply sorting
            if sort_by == 'nama_sekolah' or sort_by == 'nama':
                query += " ORDER BY s.nama_sekolah"
            elif sort_by == 'kecamatan':
                query += " ORDER BY k.nama_kecamatan, s.nama_sekolah"
            elif sort_by == 'cluster':
                query += " ORDER BY s.cluster, s.nama_sekolah"
            elif sort_by.startswith('x') and sort_by[1:].isdigit():
                # Sort by indicator
                indicator = sort_by
                query += f" ORDER BY s.{indicator} DESC, s.nama_sekolah"
            elif sort_by in ['jumlah_siswa', 'jumlah_guru', 'jumlah_rombel']:
                query += f" ORDER BY s.{sort_by} DESC, s.nama_sekolah"
            else:
                query += " ORDER BY s.nama_sekolah"  # Default sorting
            
            # Execute query
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Convert to list of dictionaries
            data_list = []
            for data in results:
                # Evaluate each indicator for this school
                evaluations = {}
                for indicator in INDICATORS:
                    value = data[indicator]
                    evaluation = self._evaluate_indicator(indicator, value, jenjang)
                    evaluations[indicator] = {
                        'value': value,
                        'status': evaluation['status'],
                        'percentage': evaluation['percentage'],
                        'description': evaluation['description']
                    }
                
                # Get priorities for this school
                cur.execute("""
                    SELECT * FROM sekolah_prioritas
                    WHERE result_id = %s AND sekolah_id = %s
                    ORDER BY gap DESC
                    LIMIT 3
                """, [result_id, data['id']])
                
                priorities = cur.fetchall()
                priorities_list = []
                
                for priority in priorities:
                    priorities_list.append({
                        'indikator': priority['indikator'],
                        'deskripsi': INDICATOR_DESCRIPTIONS.get(priority['indikator'], ''),
                        'nilai_current': priority['nilai_current'],
                        'nilai_ideal': priority['nilai_ideal'],
                        'gap': priority['gap'],
                        'urgensi': priority['urgensi'],
                        'rekomendasi': priority['rekomendasi']
                    })
                
                # Calculate standards met
                standards_met = sum(1 for ind, eval_data in evaluations.items() if eval_data['status'] == 'ideal')
                
                data_list.append({
                    'id': data['id'],
                    'result_id': data['result_id'],
                    'nama_sekolah': data['nama_sekolah'],
                    'kecamatan_id': data['kecamatan_id'],
                    'kecamatan': data['nama_kecamatan'],
                    'alamat': data['alamat'],
                    'status': data['status'],
                    'jenjang': data['jenjang'],
                    'x1': data['x1'],
                    'x2': data['x2'],
                    'x3': data['x3'],
                    'x4': data['x4'],
                    'x5': data['x5'],
                    'x6': data['x6'],
                    'x7': data['x7'],
                    'jumlah_siswa': data['jumlah_siswa'],
                    'jumlah_guru': data['jumlah_guru'],
                    'jumlah_rombel': data['jumlah_rombel'],
                    'cluster': data['cluster'],
                    'created_at': data['created_at'],
                    'evaluations': evaluations,
                    'priorities': priorities_list,
                    'standar_terpenuhi': standards_met
                })
            
            return data_list
            
        except Exception as e:
            logger.error(f"Error getting school data for result {result_id}: {str(e)}", exc_info=True)
            return []
        

    def delete_clustering_result(self, result_id: int) -> bool:
        """
        Delete a clustering result and all related data.
        
        Args:
            result_id: ID of clustering result to delete
            
        Returns:
            bool: Success or failure
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # 1. Delete related data from dependent tables first
            # Delete school priorities
            cur.execute("DELETE FROM sekolah_prioritas WHERE result_id = %s", [result_id])
            
            # Delete school data
            cur.execute("DELETE FROM sekolah_data WHERE result_id = %s", [result_id])
            
            # Delete improvement recommendations
            cur.execute("DELETE FROM rekomendasi_perbaikan WHERE result_id = %s", [result_id])
            
            # Delete indicator evaluations
            cur.execute("DELETE FROM indikator_evaluations WHERE result_id = %s", [result_id])
            
            # Delete kecamatan evaluations
            cur.execute("DELETE FROM kecamatan_evaluasi WHERE result_id = %s", [result_id])
            
            # Delete cluster characteristics
            cur.execute("DELETE FROM cluster_characteristics WHERE result_id = %s", [result_id])
            
            # Delete clustering data (kecamatan)
            cur.execute("DELETE FROM clustering_data WHERE result_id = %s", [result_id])
            
            # 2. Delete the clustering result itself
            cur.execute("DELETE FROM clustering_results WHERE id = %s", [result_id])
            
            # Commit changes
            self.db.connection.commit()
            
            logger.info(f"Successfully deleted clustering result with ID {result_id}")
            return True
            
        except Exception as e:
            # Rollback in case of error
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.error(f"Error deleting clustering result {result_id}: {str(e)}", exc_info=True)
            return False

    def get_dashboard_summary(self, result_id: int) -> Dict[str, Any]:
        """
        Get summary data for dashboard visualization.
        
        Args:
            result_id: ID of clustering result
            
        Returns:
            dict: Summary data for dashboard
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get basic result info
            cur.execute("""
                SELECT r.*, 
                (SELECT COUNT(*) FROM clustering_data WHERE result_id = %s) as total_kecamatan, 
                (SELECT COUNT(*) FROM sekolah_data WHERE result_id = %s) as total_sekolah
                FROM clustering_results r WHERE r.id = %s
            """, [result_id, result_id, result_id])
            
            result = cur.fetchone()
            
            if not result:
                return {}
            
            # Get cluster counts
            cur.execute("""
                SELECT cluster, COUNT(*) as count 
                FROM clustering_data 
                WHERE result_id = %s 
                GROUP BY cluster 
                ORDER BY cluster
            """, [result_id])
            
            cluster_counts = cur.fetchall()
            
            # Get quality levels counts
            cur.execute("""
                SELECT cc.kualitas_pendidikan, COUNT(*) as count 
                FROM cluster_characteristics cc 
                WHERE cc.result_id = %s 
                GROUP BY cc.kualitas_pendidikan
            """, [result_id])
            
            quality_counts = cur.fetchall()
            
            # Get indicator summary
            indicator_summary = self._get_indicator_summary(cur, result_id, result['jenjang'])
            
            # Format summary data
            summary = {
                'basic_info': {
                    'jenjang': result['jenjang'],
                    'jumlah_cluster': result['jumlah_cluster'],
                    'total_kecamatan': result['total_kecamatan'],
                    'total_sekolah': result['total_sekolah'],
                    'description': result['description'],
                    'created_at': result['created_at'].strftime('%d %B %Y') if result['created_at'] else 'N/A'
                },
                'cluster_distribution': {str(c['cluster']): c['count'] for c in cluster_counts},
                'quality_distribution': {q['kualitas_pendidikan']: q['count'] for q in quality_counts},
                'indicator_summary': indicator_summary
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary for result {result_id}: {str(e)}", exc_info=True)
            return {}

    def _get_indicator_summary(self, cur, result_id: int, jenjang: str) -> Dict[str, Any]:
        """
        Get summary of indicator evaluations.
        
        Args:
            cur: Database cursor
            result_id: Clustering result ID
            jenjang: Education level
            
        Returns:
            dict: Indicator summary
        """
        indicator_summary = {}
        
        try:
            # Get overall indicator stats
            for indicator in INDICATORS:
                # Get average value
                cur.execute(f"""
                    SELECT AVG({indicator}) as avg_value 
                    FROM clustering_data 
                    WHERE result_id = %s
                """, [result_id])
                
                avg_row = cur.fetchone()
                avg_value = avg_row['avg_value'] if avg_row else 0
                
                # Evaluate against standards
                evaluation = self._evaluate_indicator(indicator, avg_value, jenjang)
                
                # Get count of kecamatan meeting standard
                status_field = f"{indicator}_status"
                cur.execute(f"""
                    SELECT COUNT(*) as count 
                    FROM kecamatan_evaluasi 
                    WHERE result_id = %s AND {status_field} = 'ideal'
                """, [result_id])
                
                count_row = cur.fetchone()
                count_ideal = count_row['count'] if count_row else 0
                
                # Get total kecamatan count
                cur.execute("""
                    SELECT COUNT(*) as total 
                    FROM clustering_data 
                    WHERE result_id = %s
                """, [result_id])
                
                total_row = cur.fetchone()
                total_kecamatan = total_row['total'] if total_row else 0
                
                # Calculate percentage
                percentage_ideal = (count_ideal / total_kecamatan * 100) if total_kecamatan > 0 else 0
                
                # Format values for display
                formatted_value = avg_value
                if indicator in ['x5', 'x6', 'x7']:
                    formatted_value = f"{avg_value * 100:.1f}%"
                else:
                    formatted_value = f"{avg_value:.2f}"
                
                # Get standard text
                standard_text = self._get_indicator_standard(indicator, jenjang)
                
                indicator_summary[indicator] = {
                    'name': INDICATOR_DESCRIPTIONS[indicator],
                    'avg_value': avg_value,
                    'formatted_value': formatted_value,
                    'status': evaluation['status'],
                    'percentage': evaluation['percentage'],
                    'count_ideal': count_ideal,
                    'total_kecamatan': total_kecamatan,
                    'percentage_ideal': percentage_ideal,
                    'standard': standard_text,
                    'context': INDICATOR_CONTEXTS[indicator]
                }
                
        except Exception as e:
            logger.error(f"Error getting indicator summary: {str(e)}", exc_info=True)
        
        return indicator_summary

    def get_recommendation_summary(self, result_id: int) -> Dict[str, Any]:
        """
        Get summary of recommendations.
        
        Args:
            result_id: Clustering result ID
            
        Returns:
            dict: Recommendation summary
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get result info
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return {}
            
            jenjang = result['jenjang']
            
            # Get counts of priority indicators
            priority_counts = {}
            
            for indicator in INDICATORS:
                # Count number of kecamatan with this indicator as priority
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM kecamatan_evaluasi 
                    WHERE result_id = %s AND (prioritas_1 = %s OR prioritas_2 = %s OR prioritas_3 = %s)
                """, [result_id, indicator, indicator, indicator])
                
                count_row = cur.fetchone()
                count = count_row['count'] if count_row else 0
                
                # Count high priority (prioritas_1)
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM kecamatan_evaluasi 
                    WHERE result_id = %s AND prioritas_1 = %s
                """, [result_id, indicator])
                
                high_priority_row = cur.fetchone()
                high_priority = high_priority_row['count'] if high_priority_row else 0
                
                priority_counts[indicator] = {
                    'name': INDICATOR_DESCRIPTIONS[indicator],
                    'count': count,
                    'high_priority': high_priority,
                    'recommendation': self._generate_detailed_recommendation(indicator, 999, 0, jenjang)  # Generic recommendation
                }
            
            # Sort indicators by count (descending)
            sorted_indicators = sorted(INDICATORS, key=lambda x: priority_counts[x]['count'], reverse=True)
            
            # Get cluster-level recommendations
            cur.execute("""
                SELECT cluster, fitur_rendah, rekomendasi 
                FROM cluster_characteristics 
                WHERE result_id = %s 
                ORDER BY cluster
            """, [result_id])
            
            cluster_recommendations = []
            
            for row in cur.fetchall():
                cluster_recommendations.append({
                    'cluster': row['cluster'],
                    'fitur_rendah': row['fitur_rendah'],
                    'rekomendasi': row['rekomendasi']
                })
            
            return {
                'priority_indicators': [priority_counts[ind] for ind in sorted_indicators],
                'cluster_recommendations': cluster_recommendations
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation summary for result {result_id}: {str(e)}", exc_info=True)
            return {}

    def optimize_clustering_data(self, result_id: int) -> Tuple[bool, str]:
        """
        Optimize clustering data by calculating missing medoids and fixing data inconsistencies.
        
        Args:
            result_id: Clustering result ID
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if result exists
            cur.execute("SELECT id, jenjang FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            jenjang = result['jenjang']
            
            # Count number of medoids
            cur.execute("""
                SELECT cluster, COUNT(*) as medoid_count 
                FROM clustering_data 
                WHERE result_id = %s AND is_medoid = 1 
                GROUP BY cluster
            """, [result_id])
            
            medoid_counts = {row['cluster']: row['medoid_count'] for row in cur.fetchall()}
            
            # Get distinct clusters
            cur.execute("SELECT DISTINCT cluster FROM clustering_data WHERE result_id = %s ORDER BY cluster", [result_id])
            clusters = [row['cluster'] for row in cur.fetchall()]
            
            # Fix issues
            issues_fixed = 0
            
            # 1. Fix missing medoids
            for cluster in clusters:
                if cluster not in medoid_counts or medoid_counts[cluster] == 0:
                    # Find closest point to cluster center
                    self._assign_medoid_for_cluster(cur, result_id, cluster)
                    issues_fixed += 1
                    
                elif medoid_counts[cluster] > 1:
                    # Too many medoids, keep only one
                    self._fix_multiple_medoids(cur, result_id, cluster)
                    issues_fixed += 1
            
            # 2. Regenerate evaluations
            self._generate_kecamatan_evaluations(result_id, jenjang)
            
            # 3. Regenerate cluster characteristics
            self._generate_cluster_characteristics(result_id, jenjang)
            
            # Commit changes
            self.db.connection.commit()
            
            return True, f"Data berhasil dioptimasi. {issues_fixed} masalah diperbaiki."
            
        except Exception as e:
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.error(f"Error optimizing clustering data: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def _assign_medoid_for_cluster(self, cur, result_id: int, cluster: int) -> None:
        """
        Assign a medoid for a cluster that doesn't have one.
        
        Args:
            cur: Database cursor
            result_id: Clustering result ID
            cluster: Cluster number
        """
        # Calculate cluster center (average of all points)
        cur.execute(f"""
            SELECT AVG(x1) as x1_avg, AVG(x2) as x2_avg, AVG(x3) as x3_avg, 
                AVG(x4) as x4_avg, AVG(x5) as x5_avg, AVG(x6) as x6_avg, AVG(x7) as x7_avg
            FROM clustering_data 
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        center = cur.fetchone()
        
        if not center:
            logger.warning(f"No data found for cluster {cluster}")
            return
        
        # Get all points in this cluster
        cur.execute("""
            SELECT id, kecamatan_id, x1, x2, x3, x4, x5, x6, x7 
            FROM clustering_data 
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        points = cur.fetchall()
        
        if not points:
            logger.warning(f"No points found for cluster {cluster}")
            return
        
        # Calculate distance to center for each point
        min_distance = float('inf')
        closest_point_id = None
        
        for point in points:
            distance = (
                (point['x1'] - center['x1_avg'])**2 +
                (point['x2'] - center['x2_avg'])**2 +
                (point['x3'] - center['x3_avg'])**2 +
                (point['x4'] - center['x4_avg'])**2 +
                (point['x5'] - center['x5_avg'])**2 +
                (point['x6'] - center['x6_avg'])**2 +
                (point['x7'] - center['x7_avg'])**2
            )**0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_point_id = point['id']
        
        if closest_point_id:
            # Set as medoid
            cur.execute("UPDATE clustering_data SET is_medoid = 1 WHERE id = %s", [closest_point_id])
            logger.info(f"Assigned new medoid for cluster {cluster}")

    def _fix_multiple_medoids(self, cur, result_id: int, cluster: int) -> None:
        """
        Fix a cluster with multiple medoids by keeping only one.
        
        Args:
            cur: Database cursor
            result_id: Clustering result ID
            cluster: Cluster number
        """
        # Calculate cluster center
        cur.execute(f"""
            SELECT AVG(x1) as x1_avg, AVG(x2) as x2_avg, AVG(x3) as x3_avg, 
                AVG(x4) as x4_avg, AVG(x5) as x5_avg, AVG(x6) as x6_avg, AVG(x7) as x7_avg
            FROM clustering_data 
            WHERE result_id = %s AND cluster = %s
        """, [result_id, cluster])
        
        center = cur.fetchone()
        
        # Get current medoids
        cur.execute("""
            SELECT id, kecamatan_id, x1, x2, x3, x4, x5, x6, x7 
            FROM clustering_data 
            WHERE result_id = %s AND cluster = %s AND is_medoid = 1
        """, [result_id, cluster])
        
        medoids = cur.fetchall()
        
        if len(medoids) <= 1:
            return  # Nothing to fix
        
        # Calculate distance to center for each medoid
        min_distance = float('inf')
        best_medoid_id = None
        
        for medoid in medoids:
            distance = (
                (medoid['x1'] - center['x1_avg'])**2 +
                (medoid['x2'] - center['x2_avg'])**2 +
                (medoid['x3'] - center['x3_avg'])**2 +
                (medoid['x4'] - center['x4_avg'])**2 +
                (medoid['x5'] - center['x5_avg'])**2 +
                (medoid['x6'] - center['x6_avg'])**2 +
                (medoid['x7'] - center['x7_avg'])**2
            )**0.5
            
            if distance < min_distance:
                min_distance = distance
                best_medoid_id = medoid['id']
        
        if best_medoid_id:
            # Reset all medoids
            cur.execute("""
                UPDATE clustering_data 
                SET is_medoid = 0 
                WHERE result_id = %s AND cluster = %s
            """, [result_id, cluster])
            
            # Set only the best one
            cur.execute("UPDATE clustering_data SET is_medoid = 1 WHERE id = %s", [best_medoid_id])
            logger.info(f"Fixed multiple medoids for cluster {cluster}, kept ID {best_medoid_id}")



    def validate_csv_format(self, file_path: str) -> Tuple[bool, str, Optional[pd.DataFrame]]:
        """
        Validasi format file CSV sebelum import dengan penanganan error yang lebih baik
        termasuk penanganan untuk network response error
        
        Args:
            file_path: Path ke file CSV atau URL
            
        Returns:
            tuple: (is_valid, message, dataframe atau None)
        """
        try:
            # Deteksi apakah file_path adalah URL
            is_url = file_path.startswith(('http://', 'https://', 'ftp://'))
            
            if is_url:
                # Penanganan untuk file yang diakses melalui URL
                try:
                    # Tambahkan timeout untuk mencegah proses menggantung
                    timeout = 30  # 30 detik timeout
                    headers = {'User-Agent': 'ClusteringManagerBot/1.0'}
                    
                    logger.info(f"Mengakses file CSV dari URL: {file_path}")
                    response = requests.get(file_path, timeout=timeout, headers=headers, stream=True)
                    
                    # Cek status HTTP
                    if response.status_code != 200:
                        return False, f"Network response error: HTTP status code {response.status_code} ({response.reason})", None
                    
                    # Cek tipe konten
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/csv' not in content_type and 'application/csv' not in content_type and 'application/vnd.ms-excel' not in content_type:
                        logger.warning(f"Content-Type tidak standar untuk CSV: {content_type}")
                        # Lanjutkan meskipun content-type tidak sesuai, karena banyak server tidak mengatur content-type dengan benar
                    
                    # Cek ukuran file
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) == 0:
                        return False, "File CSV kosong (0 bytes) dari server", None
                    
                    # Gunakan io.StringIO untuk menyimpan konten respons sebagai file-like object
                    import io
                    csv_content = io.StringIO(response.text)
                    
                    # Coba baca dengan berbagai encoding
                    encoding_errors = []
                    for encoding in ['utf-8', 'iso-8859-1', 'cp1252', 'latin1']:
                        try:
                            # Reset posisi file-like object
                            csv_content.seek(0)
                            df = pd.read_csv(csv_content, encoding=encoding)
                            logger.info(f"Berhasil membaca CSV dari URL dengan encoding {encoding}")
                            break
                        except UnicodeDecodeError as e:
                            encoding_errors.append(f"{encoding}: {str(e)}")
                            continue
                        except pd.errors.EmptyDataError:
                            return False, "File CSV kosong atau hanya berisi header", None
                        except pd.errors.ParserError as e:
                            return False, f"Format CSV tidak valid: {str(e)}", None
                    else:
                        # Jika semua encoding gagal
                        return False, f"File tidak dapat dibaca dengan encoding yang didukung. Errors: {encoding_errors}", None
                    
                except requests.exceptions.Timeout:
                    return False, f"Network timeout error: Koneksi ke {file_path} timeout setelah {timeout} detik", None
                except requests.exceptions.ConnectionError:
                    return False, f"Network connection error: Tidak dapat terhubung ke {file_path}", None
                except requests.exceptions.TooManyRedirects:
                    return False, f"Network redirect error: Terlalu banyak redirect saat mengakses {file_path}", None
                except requests.exceptions.RequestException as e:
                    return False, f"Network request error: {str(e)}", None
                
            else:
                # Penanganan untuk file lokal (kode yang sudah ada)
                # Validasi path file
                if not os.path.exists(file_path):
                    return False, f"File tidak ditemukan: {file_path}", None
                    
                if not os.path.isfile(file_path):
                    return False, f"Path bukan file: {file_path}", None
                    
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return False, "File kosong (0 bytes)", None
                    
                # Log ukuran file untuk debugging
                logger.info(f"Validasi file CSV: {file_path}, ukuran: {file_size} bytes")
                    
                # Coba baca file dengan encoding berbeda
                encoding_errors = []
                for encoding in ['utf-8', 'iso-8859-1', 'cp1252', 'latin1']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger.info(f"Berhasil membaca CSV dengan encoding {encoding}")
                        break
                    except UnicodeDecodeError as e:
                        encoding_errors.append(f"{encoding}: {str(e)}")
                        continue
                    except pd.errors.EmptyDataError:
                        return False, "File CSV kosong atau hanya berisi header", None
                    except pd.errors.ParserError as e:
                        return False, f"Format CSV tidak valid: {str(e)}", None
                else:
                    # Jika semua encoding gagal
                    return False, f"File tidak dapat dibaca dengan encoding yang didukung. Errors: {encoding_errors}", None
            
            # Kode berikut sama untuk file lokal maupun URL (setelah berhasil membaca ke DataFrame)
            # Cek apakah file kosong
            if df.empty:
                return False, "File CSV kosong (tidak ada baris data)", None
                
            # Log sample data untuk debugging
            logger.info(f"CSV columns original: {list(df.columns)}")
            logger.info(f"CSV shape: {df.shape}")
            
            # Normalisasi nama kolom untuk pencocokan yang lebih baik
            df = self._normalize_csv_columns(df)
            
            # Log kolom setelah normalisasi
            logger.info(f"CSV columns normalized: {list(df.columns)}")
            if len(df) > 0:
                logger.info(f"Sample data (first row): \n{df.iloc[0].to_dict()}")
            
            # Verifikasi kolom yang diperlukan untuk data klasterisasi
            clustering_required = ['kecamatan', 'cluster'] + [f'x{i}' for i in range(1, 8)]
            missing_clustering = [col for col in clustering_required if col not in df.columns]
            
            # Verifikasi kolom yang diperlukan untuk data sekolah
            school_required = ['nama_sekolah', 'kecamatan'] + [f'x{i}' for i in range(1, 8)]
            missing_school = [col for col in school_required if col not in df.columns]
            
            # Tentukan jenis file
            if not missing_clustering:
                file_type = "clustering"
                
                # Cek tipe data dan validitas
                error_cols = []
                for i in range(1, 8):
                    col = f'x{i}'
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        nan_count = df[col].isna().sum()
                        if nan_count > 0:
                            error_cols.append(f"{col} ({nan_count} nilai tidak valid)")
                    except Exception as e:
                        error_cols.append(f"{col} (error: {str(e)})")
                
                try:
                    df['cluster'] = pd.to_numeric(df['cluster'], errors='coerce')
                    nan_count = df['cluster'].isna().sum()
                    if nan_count > 0:
                        error_cols.append(f"cluster ({nan_count} nilai tidak valid)")
                except Exception as e:
                    error_cols.append(f"cluster (error: {str(e)})")
                
                if error_cols:
                    return False, f"Kolom berikut memiliki nilai yang tidak valid: {', '.join(error_cols)}", None
                
                # Hitung nilai NaN
                nan_rows = df[clustering_required].isna().any(axis=1)
                nan_count = nan_rows.sum()
                if nan_count > len(df) * 0.3:  # Jika lebih dari 30% baris bermasalah
                    return False, f"Terlalu banyak baris ({nan_count} dari {len(df)}) dengan nilai NaN di kolom penting", None
                
                # Cek duplikasi kecamatan
                duplicates = df['kecamatan'].duplicated()
                if duplicates.any():
                    dup_count = duplicates.sum()
                    dup_names = df.loc[duplicates, 'kecamatan'].tolist()
                    logger.warning(f"Ditemukan {dup_count} duplikasi kecamatan: {dup_names[:5]}...")
                    # Peringatan saja, tidak perlu menolak import
                
                source_text = "URL" if is_url else "file lokal"
                logger.info(f"File CSV valid untuk data klasterisasi dari {source_text}, {len(df)} baris data")
                return True, f"File CSV valid untuk data klasterisasi, {len(df)} baris data", df
                    
            elif not missing_school:
                file_type = "school"
                
                # Cek tipe data untuk kolom indikator
                error_cols = []
                for i in range(1, 8):
                    col = f'x{i}'
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        nan_count = df[col].isna().sum()
                        if nan_count > 0:
                            error_cols.append(f"{col} ({nan_count} nilai tidak valid)")
                    except Exception as e:
                        error_cols.append(f"{col} (error: {str(e)})")
                
                if error_cols:
                    return False, f"Kolom berikut memiliki nilai yang tidak valid: {', '.join(error_cols)}", None
                
                # Cek kolom yang diperlukan
                if df['nama_sekolah'].isna().any() or df['kecamatan'].isna().any():
                    return False, "Kolom nama_sekolah dan kecamatan tidak boleh kosong", None
                
                # Hitung nilai NaN di kolom penting
                nan_count = df[['nama_sekolah', 'kecamatan'] + [f'x{i}' for i in range(1, 8)]].isna().sum().sum()
                if nan_count > len(df) * 0.3:  # Jika lebih dari 30% nilai bermasalah
                    return False, f"Terlalu banyak nilai NaN pada kolom-kolom penting ({nan_count} nilai)", None
                
                source_text = "URL" if is_url else "file lokal"
                logger.info(f"File CSV valid untuk data sekolah dari {source_text}, {len(df)} baris data")
                return True, f"File CSV valid untuk data sekolah, {len(df)} baris data", df
                    
            else:
                # Missing kedua jenis kolom yang diperlukan
                all_missing = list(set(missing_clustering).intersection(set(missing_school)))
                return False, f"Kolom yang diperlukan tidak ditemukan: {', '.join(all_missing)}", None
                    
        except Exception as e:
            logger.error(f"Error validasi CSV: {str(e)}", exc_info=True)
            return False, f"Error validasi CSV: {str(e)}", None
        
        
        
        
    def _identify_strengths_weaknesses_optimized(self, all_data: List[Dict[str, Any]], 
                                            cluster: int, 
                                            cluster_avgs: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Identify strengths and weaknesses with optimized method (no additional DB queries)
        
        Args:
            all_data: All cluster data
            cluster: Current cluster
            cluster_avgs: Averages for current cluster
            
        Returns:
            tuple: (strengths_list, weaknesses_list)
        """
        try:
            # Hitung statistik untuk seluruh data (sekali saja)
            all_indicator_values = {}
            for ind in INDICATORS:
                values = [row[ind] for row in all_data]
                mean = sum(values) / len(values) if values else 0
                
                # Hitung standar deviasi
                variance = sum((x - mean) ** 2 for x in values) / len(values) if values else 0
                stddev = variance ** 0.5 if variance > 0 else 0.0001  # Small non-zero value
                
                all_indicator_values[ind] = {
                    'mean': mean,
                    'stddev': stddev
                }
            
            # Calculate z-scores for each indicator
            z_scores = {}
            for ind in INDICATORS:
                mean = all_indicator_values[ind]['mean']
                stddev = all_indicator_values[ind]['stddev']
                
                if stddev == 0:  # Avoid division by zero
                    z_scores[ind] = 0
                else:
                    z_scores[ind] = (cluster_avgs[f"{ind}_avg"] - mean) / stddev
                
                # Log for debugging
                logger.debug(f"Indicator {ind}: value={cluster_avgs[f'{ind}_avg']:.2f}, mean={mean:.2f}, stddev={stddev:.2f}, z-score={z_scores[ind]:.2f}")
            
            # Identify strengths and weaknesses based on Z-score and evaluations
            strengths = []
            weaknesses = []
            
            # For x1, x2, x3: lower is better (negative z-score is good)
            for ind in ['x1', 'x2', 'x3']:
                # Changed threshold from 0.5 to 0.7 for better differentiation
                if z_scores[ind] < -0.7:  # Better than average (more than 0.7 std below mean)
                    strengths.append(ind)
                elif z_scores[ind] > 0.7:  # Worse than average (more than 0.7 std above mean)
                    weaknesses.append(ind)
            
            # For x4: close to ideal is better
            if 'x4' in z_scores:
                # Get ideal value based on jenjang (pass as parameter instead of querying DB)
                x4_ideal = 15  # Default for SMA
                x4_value = cluster_avgs['x4_avg']
                
                # If close to ideal value (within 15% of ideal)
                if abs(x4_value - x4_ideal) <= x4_ideal * 0.15:
                    strengths.append('x4')
                # If far from ideal value (more than 30% from ideal)
                elif abs(x4_value - x4_ideal) >= x4_ideal * 0.30:
                    weaknesses.append('x4')
            
            # For x5, x6, x7: higher is better (positive z-score is good)
            for ind in ['x5', 'x6', 'x7']:
                # Use both z-score and absolute threshold
                value = cluster_avgs[f'{ind}_avg']
                
                # Changed threshold from 0.5 to 0.7 for better differentiation
                if z_scores[ind] > 0.7 or value >= 0.9:  # Better than average OR >= 90%
                    strengths.append(ind)
                elif z_scores[ind] < -0.7 or value < 0.7:  # Worse than average OR < 70%
                    weaknesses.append(ind)
            
            # Log results
            logger.info(f"Cluster {cluster} strengths: {strengths}")
            logger.info(f"Cluster {cluster} weaknesses: {weaknesses}")
            
            return strengths, weaknesses
                
        except Exception as e:
            logger.error(f"Error identifying strengths/weaknesses: {str(e)}", exc_info=True)
            return [], []
        
        
        
    

    def backup_clustering_result(self, result_id: int, output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a backup of a clustering result, exporting all related data.
        
        Args:
            result_id: ID of clustering result
            output_dir: Directory to save the backup
            
        Returns:
            tuple: (success, backup_path or error message)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if result exists
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            # Create backup directory
            if output_dir is None:
                backup_dir = os.path.join(self.output_dir, f'backup_result_{result_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            else:
                backup_dir = os.path.join(output_dir, f'backup_result_{result_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # 1. Export result metadata
            result_info = {
                'id': result['id'],
                'process_id': result['process_id'],
                'jenjang': result['jenjang'],
                'jumlah_cluster': result['jumlah_cluster'],
                'skenario': result['skenario'],
                'status': result['status'],
                'description': result['description'],
                'created_at': result['created_at'].strftime('%Y-%m-%d %H:%M:%S') if result['created_at'] else None,
                'imported_at': result['imported_at'].strftime('%Y-%m-%d %H:%M:%S') if result['imported_at'] else None,
            }
            
            with open(os.path.join(backup_dir, 'result_info.json'), 'w') as f:
                json.dump(result_info, f, indent=2)
            
            # 2. Export clustering data
            cur.execute("""
                SELECT cd.*, k.nama_kecamatan 
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                WHERE cd.result_id = %s
            """, [result_id])
            
            clustering_data = []
            for row in cur.fetchall():
                clustering_data.append({
                    'kecamatan': row['nama_kecamatan'],
                    'cluster': row['cluster'],
                    'is_medoid': row['is_medoid'],
                    'x1': row['x1'],
                    'x2': row['x2'],
                    'x3': row['x3'],
                    'x4': row['x4'],
                    'x5': row['x5'],
                    'x6': row['x6'],
                    'x7': row['x7'],
                    'dim1': row['dim1'],
                    'dim2': row['dim2']
                })
            
            pd.DataFrame(clustering_data).to_csv(os.path.join(backup_dir, 'clustering_data.csv'), index=False)
            
            # 3. Export cluster characteristics
            cur.execute("SELECT * FROM cluster_characteristics WHERE result_id = %s", [result_id])
            
            cluster_chars = []
            for row in cur.fetchall():
                cluster_chars.append({
                    'cluster': row['cluster'],
                    'jumlah_anggota': row['jumlah_anggota'],
                    'medoid_name': row['medoid_name'],
                    'x1_avg': row['x1_avg'],
                    'x2_avg': row['x2_avg'],
                    'x3_avg': row['x3_avg'],
                    'x4_avg': row['x4_avg'],
                    'x5_avg': row['x5_avg'],
                    'x6_avg': row['x6_avg'],
                    'x7_avg': row['x7_avg'],
                    'standar_terpenuhi': row['standar_terpenuhi'],
                    'kualitas_pendidikan': row['kualitas_pendidikan'],
                    'fitur_tinggi': row['fitur_tinggi'],
                    'fitur_rendah': row['fitur_rendah'],
                    'deskripsi': row['deskripsi'],
                    'interpretasi': row['interpretasi'],
                    'rekomendasi': row['rekomendasi']
                })
            
            pd.DataFrame(cluster_chars).to_csv(os.path.join(backup_dir, 'cluster_characteristics.csv'), index=False)
            
            # 4. Export kecamatan evaluations
            cur.execute("""
                SELECT ke.*, k.nama_kecamatan 
                FROM kecamatan_evaluasi ke
                JOIN kecamatan k ON ke.kecamatan_id = k.id
                WHERE ke.result_id = %s
            """, [result_id])
            
            kecamatan_evals = []
            for row in cur.fetchall():
                kecamatan_evals.append({
                    'kecamatan': row['nama_kecamatan'],
                    'cluster': row['cluster'],
                    'standar_terpenuhi': row['standar_terpenuhi'],
                    'kualitas_pendidikan': row['kualitas_pendidikan'],
                    'prioritas_1': row['prioritas_1'],
                    'prioritas_2': row['prioritas_2'],
                    'prioritas_3': row['prioritas_3'],
                    'rekomendasi': row['rekomendasi'],
                    'x1_value': row['x1_value'],
                    'x2_value': row['x2_value'],
                    'x3_value': row['x3_value'],
                    'x4_value': row['x4_value'],
                    'x5_value': row['x5_value'],
                    'x6_value': row['x6_value'],
                    'x7_value': row['x7_value']
                })
            
            pd.DataFrame(kecamatan_evals).to_csv(os.path.join(backup_dir, 'kecamatan_evaluations.csv'), index=False)
            
            # 5. Export sekolah data if exists
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM sekolah_data 
                WHERE result_id = %s
            """, [result_id])
            
            count_row = cur.fetchone()
            if count_row and count_row['count'] > 0:
                cur.execute("""
                    SELECT sd.*, k.nama_kecamatan 
                    FROM sekolah_data sd
                    JOIN kecamatan k ON sd.kecamatan_id = k.id
                    WHERE sd.result_id = %s
                """, [result_id])
                
                sekolah_data = []
                for row in cur.fetchall():
                    sekolah_data.append({
                        'nama_sekolah': row['nama_sekolah'],
                        'kecamatan': row['nama_kecamatan'],
                        'alamat': row['alamat'],
                        'status': row['status'],
                        'jenjang': row['jenjang'],
                        'cluster': row['cluster'],
                        'x1': row['x1'],
                        'x2': row['x2'],
                        'x3': row['x3'],
                        'x4': row['x4'],
                        'x5': row['x5'],
                        'x6': row['x6'],
                        'x7': row['x7'],
                        'jumlah_siswa': row['jumlah_siswa'],
                        'jumlah_guru': row['jumlah_guru'],
                        'jumlah_rombel': row['jumlah_rombel']
                    })
                
                pd.DataFrame(sekolah_data).to_csv(os.path.join(backup_dir, 'sekolah_data.csv'), index=False)
            
            # 6. Create a combined Excel report
            self.export_to_excel(result_id, os.path.join(backup_dir, 'full_report.xlsx'))
            
            # 7. Create a PDF report
            self.export_to_pdf(result_id, os.path.join(backup_dir, 'full_report.pdf'))
            
            # Create a ZIP file
            import shutil
            zip_path = f"{backup_dir}.zip"
            shutil.make_archive(backup_dir, 'zip', backup_dir)
            
            return True, zip_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def restore_clustering_result(self, backup_path: str) -> Tuple[bool, str, Optional[int]]:
        """
        Restore a clustering result from a backup.
        
        Args:
            backup_path: Path to the backup ZIP file
            
        Returns:
            tuple: (success, message, result_id)
        """
        try:
            import shutil
            import tempfile
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract ZIP file
                shutil.unpack_archive(backup_path, temp_dir, 'zip')
                
                # Read result_info.json
                result_info_path = os.path.join(temp_dir, 'result_info.json')
                if not os.path.exists(result_info_path):
                    return False, "File info hasil klasterisasi tidak ditemukan dalam backup", None
                    
                with open(result_info_path, 'r') as f:
                    result_info = json.load(f)
                    
                # Read clustering_data.csv
                clustering_data_path = os.path.join(temp_dir, 'clustering_data.csv')
                if not os.path.exists(clustering_data_path):
                    return False, "File data klasterisasi tidak ditemukan dalam backup", None
                    
                # Get cursor
                cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
                
                # Create new process entry
                cur.execute("""
                    INSERT INTO clustering_processes 
                    (name, jenjang, description, status, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    f"Restored from backup {os.path.basename(backup_path)}",
                    result_info['jenjang'],
                    result_info['description'],
                    'completed',
                    'admin',  # Default user for restored processes
                    datetime.now()
                ])
                
                self.db.connection.commit()
                process_id = cur.lastrowid
                
                # Create new clustering result
                cur.execute("""
                    INSERT INTO clustering_results 
                    (process_id, jenjang, jumlah_cluster, skenario, status, description, created_at, imported_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    process_id,
                    result_info['jenjang'],
                    result_info['jumlah_cluster'],
                    result_info['skenario'],
                    'completed',
                    f"{result_info['description']} (Restored from backup)",
                    datetime.now(),
                    datetime.now()
                ])
                
                self.db.connection.commit()
                result_id = cur.lastrowid
                
                # Import clustering data
                df_clustering = pd.read_csv(clustering_data_path)
                
                # Match kecamatan names to IDs
                kecamatan_mapping, missing_kecamatan = self._match_kecamatan_names(cur, df_clustering['kecamatan'].unique())
                
                if missing_kecamatan and len(missing_kecamatan) > len(df_clustering['kecamatan'].unique()) * 0.2:
                    # If more than 20% kecamatan are missing, abort
                    return False, f"Terlalu banyak kecamatan tidak ditemukan: {', '.join(missing_kecamatan[:10])}...", None
                
                # Import clustering data
                for _, row in df_clustering.iterrows():
                    kecamatan_name = row['kecamatan']
                    if kecamatan_name not in kecamatan_mapping:
                        continue
                        
                    kecamatan_id = kecamatan_mapping[kecamatan_name]
                    
                    # Parse is_medoid
                    is_medoid = False
                    if 'is_medoid' in row:
                        if isinstance(row['is_medoid'], bool):
                            is_medoid = row['is_medoid']
                        elif isinstance(row['is_medoid'], (int, float)):
                            is_medoid = bool(row['is_medoid'])
                        elif isinstance(row['is_medoid'], str):
                            is_medoid = row['is_medoid'].lower() in ('true', 't', 'yes', 'y', '1')
                    
                    # Insert data
                    cur.execute("""
                        INSERT INTO clustering_data 
                        (result_id, kecamatan_id, cluster, is_medoid, x1, x2, x3, x4, x5, x6, x7, dim1, dim2)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        result_id,
                        kecamatan_id,
                        int(row['cluster']),
                        is_medoid,
                        float(row['x1']),
                        float(row['x2']),
                        float(row['x3']),
                        float(row['x4']),
                        float(row['x5']),
                        float(row['x6']),
                        float(row['x7']),
                        float(row['dim1']) if 'dim1' in row and pd.notna(row['dim1']) else None,
                        float(row['dim2']) if 'dim2' in row and pd.notna(row['dim2']) else None
                    ])
                
                # Regenerate cluster characteristics and evaluations
                self._generate_cluster_characteristics(result_id, result_info['jenjang'])
                
                # Import sekolah data if available
                sekolah_data_path = os.path.join(temp_dir, 'sekolah_data.csv')
                if os.path.exists(sekolah_data_path):
                    df_sekolah = pd.read_csv(sekolah_data_path)
                    self._import_sekolah_data_from_df(cur, df_sekolah, result_id, result_info['jenjang'], kecamatan_mapping)
                
                self.db.connection.commit()
                
                return True, f"Berhasil memulihkan hasil klasterisasi dari backup dengan ID baru: {result_id}", result_id
                
        except Exception as e:
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.error(f"Error restoring from backup: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}", None

    def _import_sekolah_data_from_df(self, cur, df: pd.DataFrame, result_id: int, jenjang: str, 
                                    kecamatan_mapping: Dict[str, int]) -> int:
        """
        Import school data from DataFrame.
        
        Args:
            cur: Database cursor
            df: DataFrame with school data
            result_id: ID of the clustering result
            jenjang: Education level
            kecamatan_mapping: Mapping of kecamatan names to IDs
            
        Returns:
            int: Number of schools imported
        """
        # Get cluster mapping
        cur.execute("SELECT kecamatan_id, cluster FROM clustering_data WHERE result_id = %s", [result_id])
        cluster_mapping = {row['kecamatan_id']: row['cluster'] for row in cur.fetchall()}
        
        # Import school data
        count = 0
        for _, row in df.iterrows():
            try:
                kecamatan_name = row['kecamatan']
                if kecamatan_name not in kecamatan_mapping:
                    continue
                    
                kecamatan_id = kecamatan_mapping[kecamatan_name]
                
                # Get cluster
                cluster = cluster_mapping.get(kecamatan_id)
                if cluster is None:
                    continue
                    
                # Insert school data
                cur.execute("""
                    INSERT INTO sekolah_data 
                    (result_id, nama_sekolah, kecamatan_id, alamat, status, jenjang, 
                    x1, x2, x3, x4, x5, x6, x7, jumlah_siswa, jumlah_guru, jumlah_rombel, cluster)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    result_id,
                    row['nama_sekolah'],
                    kecamatan_id,
                    row['alamat'] if 'alamat' in row else '',
                    row['status'] if 'status' in row else None,
                    jenjang,
                    float(row['x1']),
                    float(row['x2']),
                    float(row['x3']),
                    float(row['x4']),
                    float(row['x5']),
                    float(row['x6']),
                    float(row['x7']),
                    int(row['jumlah_siswa']) if 'jumlah_siswa' in row and pd.notna(row['jumlah_siswa']) else None,
                    int(row['jumlah_guru']) if 'jumlah_guru' in row and pd.notna(row['jumlah_guru']) else None,
                    int(row['jumlah_rombel']) if 'jumlah_rombel' in row and pd.notna(row['jumlah_rombel']) else None,
                    cluster
                ])
                
                count += 1
                
            except Exception as e:
                logger.error(f"Error importing school {row.get('nama_sekolah', 'unknown')}: {str(e)}")
                continue
        
        return count

    def check_data_quality(self, result_id: int) -> Dict[str, Any]:
        """
        Check data quality for a clustering result.
        
        Args:
            result_id: ID of the clustering result
            
        Returns:
            dict: Quality issues found
        """
        issues = {
            'missing_medoids': [],
            'multiple_medoids': [],
            'outlier_indicators': [],
            'missing_evaluations': [],
            'inconsistent_data': []
        }
        
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if result exists
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return {'error': f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"}
            
            jenjang = result['jenjang']
            
            # Check for clusters with missing medoids
            cur.execute("""
                SELECT cd.cluster 
                FROM (SELECT DISTINCT cluster FROM clustering_data WHERE result_id = %s) cd
                LEFT JOIN (
                    SELECT cluster FROM clustering_data 
                    WHERE result_id = %s AND is_medoid = 1
                ) m ON cd.cluster = m.cluster
                WHERE m.cluster IS NULL
            """, [result_id, result_id])
            
            for row in cur.fetchall():
                issues['missing_medoids'].append(row['cluster'])
            
            # Check for clusters with multiple medoids
            cur.execute("""
                SELECT cluster, COUNT(*) as medoid_count 
                FROM clustering_data 
                WHERE result_id = %s AND is_medoid = 1 
                GROUP BY cluster 
                HAVING COUNT(*) > 1
            """, [result_id])
            
            for row in cur.fetchall():
                issues['multiple_medoids'].append({
                    'cluster': row['cluster'],
                    'count': row['medoid_count']
                })
            
            # Check for outlier indicator values
            for indicator in INDICATORS:
                # Get indicator stats
                cur.execute(f"""
                    SELECT 
                        AVG({indicator}) as mean, 
                        STDDEV({indicator}) as stddev,
                        MIN({indicator}) as min_val,
                        MAX({indicator}) as max_val
                    FROM clustering_data 
                    WHERE result_id = %s
                """, [result_id])
                
                stats = cur.fetchone()
                if not stats or stats['stddev'] is None:
                    continue
                    
                mean = stats['mean']
                stddev = stats['stddev']
                
                # Define outlier threshold (3 standard deviations)
                upper_threshold = mean + 3 * stddev
                lower_threshold = mean - 3 * stddev
                
                # Find outliers
                cur.execute(f"""
                    SELECT cd.id, k.nama_kecamatan, cd.cluster, cd.{indicator} as value
                    FROM clustering_data cd
                    JOIN kecamatan k ON cd.kecamatan_id = k.id
                    WHERE cd.result_id = %s AND (cd.{indicator} > %s OR cd.{indicator} < %s)
                    ORDER BY cd.{indicator} DESC
                """, [result_id, upper_threshold, lower_threshold])
                
                outliers = []
                for row in cur.fetchall():
                    outliers.append({
                        'kecamatan': row['nama_kecamatan'],
                        'cluster': row['cluster'],
                        'value': row['value'],
                        'mean': mean,
                        'stddev': stddev
                    })
                
                if outliers:
                    issues['outlier_indicators'].append({
                        'indicator': indicator,
                        'name': INDICATOR_DESCRIPTIONS[indicator],
                        'outliers': outliers[:5]  # Limit to top 5
                    })
            
            # Check for missing evaluations
            cur.execute("""
                SELECT cd.kecamatan_id, k.nama_kecamatan
                FROM clustering_data cd
                JOIN kecamatan k ON cd.kecamatan_id = k.id
                LEFT JOIN kecamatan_evaluasi ke ON cd.result_id = ke.result_id AND cd.kecamatan_id = ke.kecamatan_id
                WHERE cd.result_id = %s AND ke.kecamatan_id IS NULL
            """, [result_id])
            
            for row in cur.fetchall():
                issues['missing_evaluations'].append({
                    'kecamatan_id': row['kecamatan_id'],
                    'kecamatan': row['nama_kecamatan']
                })
            
            # Check for inconsistent data (different indicator values between cluster avg and actual)
            cur.execute("""
                SELECT cc.cluster, cc.x1_avg, cc.x2_avg, cc.x3_avg, cc.x4_avg, cc.x5_avg, cc.x6_avg, cc.x7_avg
                FROM cluster_characteristics cc
                WHERE cc.result_id = %s
            """, [result_id])
            
            cluster_avgs = {row['cluster']: row for row in cur.fetchall()}
            
            for cluster, avgs in cluster_avgs.items():
                # Calculate actual averages
                cur.execute("""
                    SELECT 
                        AVG(x1) as x1_avg, 
                        AVG(x2) as x2_avg, 
                        AVG(x3) as x3_avg, 
                        AVG(x4) as x4_avg, 
                        AVG(x5) as x5_avg, 
                        AVG(x6) as x6_avg, 
                        AVG(x7) as x7_avg
                    FROM clustering_data 
                    WHERE result_id = %s AND cluster = %s
                """, [result_id, cluster])
                
                actual_avgs = cur.fetchone()
                
                # Compare stored vs actual averages
                inconsistencies = []
                for indicator in INDICATORS:
                    stored_avg = avgs[f"{indicator}_avg"]
                    actual_avg = actual_avgs[f"{indicator}_avg"]
                    
                    # Check for significant difference (>1%)
                    if abs((stored_avg - actual_avg) / actual_avg) > 0.01:
                        inconsistencies.append({
                            'indicator': indicator,
                            'name': INDICATOR_DESCRIPTIONS[indicator],
                            'stored_avg': stored_avg,
                            'actual_avg': actual_avg,
                            'difference': stored_avg - actual_avg
                        })
                
                if inconsistencies:
                    issues['inconsistent_data'].append({
                        'cluster': cluster,
                        'inconsistencies': inconsistencies
                    })
            
            # Add issue counts
            issues['count'] = {
                'missing_medoids': len(issues['missing_medoids']),
                'multiple_medoids': len(issues['multiple_medoids']),
                'outlier_indicators': len(issues['outlier_indicators']),
                'missing_evaluations': len(issues['missing_evaluations']),
                'inconsistent_data': len(issues['inconsistent_data'])
            }
            
            issues['total_issues'] = sum(issues['count'].values())
            
            return issues
            
        except Exception as e:
            logger.error(f"Error checking data quality: {str(e)}", exc_info=True)
            return {'error': f"Error: {str(e)}"}

    def fix_data_quality_issues(self, result_id: int) -> Tuple[bool, str]:
        """
        Fix data quality issues for a clustering result.
        
        Args:
            result_id: ID of the clustering result
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if result exists
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            
            if not result:
                return False, f"Hasil klasterisasi dengan ID {result_id} tidak ditemukan"
            
            jenjang = result['jenjang']
            
            # First, check for issues
            issues = self.check_data_quality(result_id)
            
            if 'error' in issues:
                return False, issues['error']
                
            if issues['total_issues'] == 0:
                return True, "Tidak ada masalah kualitas data yang ditemukan"
            
            fixes_applied = []
            
            # 1. Fix missing medoids
            if issues['missing_medoids']:
                for cluster in issues['missing_medoids']:
                    self._assign_medoid_for_cluster(cur, result_id, cluster)
                    fixes_applied.append(f"Menetapkan medoid baru untuk cluster {cluster}")
            
            # 2. Fix multiple medoids
            if issues['multiple_medoids']:
                for item in issues['multiple_medoids']:
                    cluster = item['cluster']
                    self._fix_multiple_medoids(cur, result_id, cluster)
                    fixes_applied.append(f"Memperbaiki {item['count']} medoid ganda pada cluster {cluster}")
            
            # 3. Handle outliers (log them but don't remove)
            if issues['outlier_indicators']:
                for item in issues['outlier_indicators']:
                    indicator = item['indicator']
                    outlier_count = len(item['outliers'])
                    logger.warning(f"Teridentifikasi {outlier_count} outlier untuk indikator {indicator} ({item['name']})")
                    fixes_applied.append(f"Mencatat {outlier_count} outlier untuk indikator {indicator}")
            
            # 4. Fix missing evaluations
            if issues['missing_evaluations']:
                self._generate_kecamatan_evaluations(result_id, jenjang)
                fixes_applied.append(f"Membuat ulang evaluasi kecamatan untuk {len(issues['missing_evaluations'])} kecamatan")
            
            # 5. Fix inconsistent data
            if issues['inconsistent_data']:
                # Regenerate cluster characteristics
                self._generate_cluster_characteristics(result_id, jenjang)
                fixes_applied.append(f"Membuat ulang karakteristik cluster untuk {len(issues['inconsistent_data'])} cluster")
            
            # Commit changes
            self.db.connection.commit()
            
            return True, f"Berhasil memperbaiki {len(fixes_applied)} masalah kualitas data:\n- " + "\n- ".join(fixes_applied)
            
        except Exception as e:
            if hasattr(self.db, 'connection'):
                self.db.connection.rollback()
            logger.error(f"Error fixing data quality issues: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def get_comparison_data(self, result_ids: List[int]) -> Dict[str, Any]:
        """
        Get comparison data for multiple clustering results.
        
        Args:
            result_ids: List of clustering result IDs to compare
            
        Returns:
            dict: Comparison data
        """
        comparison = {
            'results': [],
            'indicators': {},
            'clusters': {},
            'quality_levels': {}
        }
        
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get basic info for each result
            for result_id in result_ids:
                cur.execute("""
                    SELECT r.*, 
                    (SELECT COUNT(*) FROM clustering_data WHERE result_id = %s) as total_kecamatan
                    FROM clustering_results r WHERE r.id = %s
                """, [result_id, result_id])
                
                result = cur.fetchone()
                
                if not result:
                    logger.warning(f"Result with ID {result_id} not found")
                    continue
                    
                # Get cluster count by quality level
                cur.execute("""
                    SELECT kualitas_pendidikan, COUNT(*) as count 
                    FROM cluster_characteristics 
                    WHERE result_id = %s 
                    GROUP BY kualitas_pendidikan
                """, [result_id])
                
                quality_counts = {row['kualitas_pendidikan']: row['count'] for row in cur.fetchall()}
                
                # Add to results list
                comparison['results'].append({
                    'id': result_id,
                    'jenjang': result['jenjang'],
                    'jumlah_cluster': result['jumlah_cluster'],
                    'skenario': result['skenario'],
                    'total_kecamatan': result['total_kecamatan'],
                    'imported_at': result['imported_at'],
                    'description': result['description'],
                    'quality_counts': quality_counts
                })
            
            # Compare indicator averages
            for indicator in INDICATORS:
                indicator_data = {
                    'name': INDICATOR_DESCRIPTIONS[indicator],
                    'values': {}
                }
                
                for result_id in result_ids:
                    cur.execute(f"""
                        SELECT AVG({indicator}) as avg_value 
                        FROM clustering_data 
                        WHERE result_id = %s
                    """, [result_id])
                    
                    avg_row = cur.fetchone()
                    indicator_data['values'][result_id] = avg_row['avg_value'] if avg_row else None
                    
                comparison['indicators'][indicator] = indicator_data
            
            # Compare cluster distributions
            comparison['cluster_counts'] = {}
            
            for result_id in result_ids:
                cur.execute("""
                    SELECT cluster, COUNT(*) as count 
                    FROM clustering_data 
                    WHERE result_id = %s 
                    GROUP BY cluster 
                    ORDER BY cluster
                """, [result_id])
                
                comparison['cluster_counts'][result_id] = {str(row['cluster']): row['count'] for row in cur.fetchall()}
            
            # Compare quality level distributions
            comparison['quality_distributions'] = {}
            
            for result_id in result_ids:
                cur.execute("""
                    SELECT cc.kualitas_pendidikan, COUNT(*) as count 
                    FROM cluster_characteristics cc 
                    WHERE cc.result_id = %s 
                    GROUP BY cc.kualitas_pendidikan
                """, [result_id])
                
                comparison['quality_distributions'][result_id] = {
                    row['kualitas_pendidikan']: row['count'] for row in cur.fetchall()
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error getting comparison data: {str(e)}", exc_info=True)
            return {'error': f"Error: {str(e)}"}



    def _determine_education_quality(self, standards_met: int, total_standards: int) -> str:
        """
        Menentukan level kualitas pendidikan berdasarkan jumlah standar yang terpenuhi.
        
        Args:
            standards_met: Jumlah standar yang terpenuhi
            total_standards: Total jumlah standar
            
        Returns:
            str: Level kualitas pendidikan
        """
        if total_standards == 0:
            return 'tidak dapat ditentukan'
            
        percentage = (standards_met / total_standards) * 100
        
        # Pengelompokan level kualitas berdasarkan persentase standar terpenuhi
        # Disesuaikan berdasarkan dokumentasi perbaikan
        if percentage >= 90:
            return 'sangat tinggi'
        elif percentage >= 75:
            return 'tinggi'
        elif percentage >= 50:
            return 'sedang'
        elif percentage >= 25:
            return 'rendah'
        else:
            return 'sangat rendah'        
        
    def get_detailed_characteristics(self, result_id: int) -> Dict[str, Any]:
        """
        Mendapatkan data karakteristik klaster secara detail.
        
        Args:
            result_id: ID hasil klasterisasi
            
        Returns:
            dict: Data karakteristik klaster
        """
        try:
            # Get cursor
            cur = self.db.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Get cluster characteristics
            cur.execute("""
                SELECT * FROM cluster_characteristics
                WHERE result_id = %s
                ORDER BY cluster
            """, [result_id])
            
            characteristics = cur.fetchall()
            
            if not characteristics:
                return {"error": "Karakteristik klaster tidak ditemukan"}
            
            # Get result info
            cur.execute("SELECT jenjang FROM clustering_results WHERE id = %s", [result_id])
            result = cur.fetchone()
            jenjang = result['jenjang'] if result else "SMA"
            
            # Format data for response
            detailed_data = {
                "jenjang": jenjang,
                "clusters": []
            }
            
            for char in characteristics:
                # Get members
                members = char['anggota'].split(',') if char['anggota'] else []
                
                # Get strengths and weaknesses
                fitur_tinggi = char['fitur_tinggi'].split(',') if char['fitur_tinggi'] else []
                fitur_rendah = char['fitur_rendah'].split(',') if char['fitur_rendah'] else []
                
                # Format characteristics data
                cluster_data = {
                    "cluster": char['cluster'],
                    "jumlah_anggota": char['jumlah_anggota'],
                    "medoid_name": char['medoid_name'],
                    "anggota": members,
                    "standar_terpenuhi": char['standar_terpenuhi'],
                    "kualitas_pendidikan": char['kualitas_pendidikan'],
                    "indikator": {
                        "x1": {"name": INDICATOR_DESCRIPTIONS['x1'], "value": char['x1_avg']},
                        "x2": {"name": INDICATOR_DESCRIPTIONS['x2'], "value": char['x2_avg']},
                        "x3": {"name": INDICATOR_DESCRIPTIONS['x3'], "value": char['x3_avg']},
                        "x4": {"name": INDICATOR_DESCRIPTIONS['x4'], "value": char['x4_avg']},
                        "x5": {"name": INDICATOR_DESCRIPTIONS['x5'], "value": char['x5_avg'] * 100},  # Convert to percentage
                        "x6": {"name": INDICATOR_DESCRIPTIONS['x6'], "value": char['x6_avg'] * 100},  # Convert to percentage
                        "x7": {"name": INDICATOR_DESCRIPTIONS['x7'], "value": char['x7_avg'] * 100}   # Convert to percentage
                    },
                    "fitur_tinggi": fitur_tinggi,
                    "fitur_rendah": fitur_rendah,
                    "deskripsi": char['deskripsi'],
                    "interpretasi": char['interpretasi'],
                    "rekomendasi": char['rekomendasi']
                }
                
                detailed_data["clusters"].append(cluster_data)
            
            return detailed_data
            
        except Exception as e:
            logger.error(f"Error getting detailed characteristics for result {result_id}: {str(e)}", exc_info=True)
            return {"error": f"Error: {str(e)}"}       