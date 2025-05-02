# models.py - For compatibility with clustering.py

# Classes for model definitions
class ClusteringProcess:
    def __init__(self, id=None, jenjang=None, skenario=None, status=None, created_by=None, created_at=None, completed_at=None):
        self.id = id
        self.jenjang = jenjang
        self.skenario = skenario
        self.status = status
        self.created_by = created_by
        self.created_at = created_at
        self.completed_at = completed_at
    
    @staticmethod
    def filter_by(jenjang=None, skenario=None):
        from app import mysql
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM clustering_processes"
        params = []
        
        if jenjang and skenario:
            query += " WHERE jenjang = %s AND skenario = %s"
            params = [jenjang, skenario]
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if not result:
            return None
            
        process = ClusteringProcess(
            id=result['id'],
            jenjang=result['jenjang'],
            skenario=result['skenario'],
            status=result['status'],
            created_by=result['created_by'],
            created_at=result['created_at'],
            completed_at=result['completed_at']
        )
        return process

class ClusteringResult:
    def __init__(self, id=None, process_id=None, jenjang=None, skenario=None, jumlah_cluster=None, 
                description=None, geojson_path=None, imported_at=None, status=None):
        self.id = id
        self.process_id = process_id
        self.jenjang = jenjang
        self.skenario = skenario
        self.jumlah_cluster = jumlah_cluster
        self.description = description
        self.geojson_path = geojson_path
        self.imported_at = imported_at
        self.status = status
    
    @staticmethod
    def query_get(result_id):
        from app import mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM clustering_results WHERE id = %s", [result_id])
        result = cursor.fetchone()
        
        if not result:
            return None
            
        return ClusteringResult(
            id=result['id'],
            process_id=result['process_id'],
            jenjang=result['jenjang'],
            skenario=result['skenario'],
            jumlah_cluster=result['jumlah_cluster'],
            description=result['description'],
            geojson_path=result['geojson_path'],
            imported_at=result['imported_at'],
            status=result['status']
        )

class ClusteringData:
    def __init__(self, id=None, result_id=None, kecamatan_id=None, cluster=None, is_medoid=None, 
                x1=None, x2=None, x3=None, x4=None, x5=None, x6=None, x7=None, dim1=None, dim2=None):
        self.id = id
        self.result_id = result_id
        self.kecamatan_id = kecamatan_id
        self.cluster = cluster
        self.is_medoid = is_medoid
        self.x1 = x1
        self.x2 = x2
        self.x3 = x3
        self.x4 = x4
        self.x5 = x5
        self.x6 = x6
        self.x7 = x7
        self.dim1 = dim1
        self.dim2 = dim2
    
    @staticmethod
    def filter_by(result_id=None, kecamatan_id=None, cluster=None):
        from app import mysql
        cursor = mysql.connection.cursor()
        
        where_clauses = []
        params = []
        
        if result_id is not None:
            where_clauses.append("result_id = %s")
            params.append(result_id)
        
        if kecamatan_id is not None:
            where_clauses.append("kecamatan_id = %s")
            params.append(kecamatan_id)
            
        if cluster is not None:
            where_clauses.append("cluster = %s")
            params.append(cluster)
            
        query = "SELECT * FROM clustering_data"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [ClusteringData(
            id=r['id'],
            result_id=r['result_id'],
            kecamatan_id=r['kecamatan_id'],
            cluster=r['cluster'],
            is_medoid=r['is_medoid'],
            x1=r['x1'],
            x2=r['x2'],
            x3=r['x3'],
            x4=r['x4'],
            x5=r['x5'],
            x6=r['x6'],
            x7=r['x7'],
            dim1=r['dim1'],
            dim2=r['dim2']
        ) for r in results]

class ClusterCharacteristics:
    def __init__(self, id=None, result_id=None, cluster=None, jumlah_anggota=None, medoid_id=None,
                x1_avg=None, x2_avg=None, x3_avg=None, x4_avg=None, x5_avg=None, x6_avg=None, x7_avg=None,
                fitur_tinggi=None, fitur_rendah=None, interpretasi=None, rekomendasi=None,
                kualitas_pendidikan=None, standar_terpenuhi=None, warna_peta=None):
        self.id = id
        self.result_id = result_id
        self.cluster = cluster
        self.jumlah_anggota = jumlah_anggota
        self.medoid_id = medoid_id
        self.x1_avg = x1_avg
        self.x2_avg = x2_avg
        self.x3_avg = x3_avg
        self.x4_avg = x4_avg
        self.x5_avg = x5_avg
        self.x6_avg = x6_avg
        self.x7_avg = x7_avg
        self.fitur_tinggi = fitur_tinggi
        self.fitur_rendah = fitur_rendah
        self.interpretasi = interpretasi
        self.rekomendasi = rekomendasi
        self.kualitas_pendidikan = kualitas_pendidikan
        self.standar_terpenuhi = standar_terpenuhi
        self.warna_peta = warna_peta
    
    @staticmethod
    def filter_by(result_id=None, cluster=None):
        from app import mysql
        cursor = mysql.connection.cursor()
        
        where_clauses = []
        params = []
        
        if result_id is not None:
            where_clauses.append("result_id = %s")
            params.append(result_id)
        
        if cluster is not None:
            where_clauses.append("cluster = %s")
            params.append(cluster)
            
        query = "SELECT * FROM cluster_characteristics"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [ClusterCharacteristics(
            id=r['id'],
            result_id=r['result_id'],
            cluster=r['cluster'],
            jumlah_anggota=r['jumlah_anggota'],
            medoid_id=r['medoid_id'],
            x1_avg=r['x1_avg'],
            x2_avg=r['x2_avg'],
            x3_avg=r['x3_avg'],
            x4_avg=r['x4_avg'],
            x5_avg=r['x5_avg'],
            x6_avg=r['x6_avg'],
            x7_avg=r['x7_avg'],
            fitur_tinggi=r['fitur_tinggi'],
            fitur_rendah=r['fitur_rendah'],
            interpretasi=r['interpretasi'],
            rekomendasi=r['rekomendasi'],
            kualitas_pendidikan=r['kualitas_pendidikan'],
            standar_terpenuhi=r['standar_terpenuhi'],
            warna_peta=r['warna_peta']
        ) for r in results]

class Kecamatan:
    def __init__(self, id=None, nama_kecamatan=None, kota_kab_id=None, latitude=None, longitude=None, geojson_id=None, created_at=None):
        self.id = id
        self.nama_kecamatan = nama_kecamatan
        self.kota_kab_id = kota_kab_id
        self.latitude = latitude
        self.longitude = longitude
        self.geojson_id = geojson_id
        self.created_at = created_at
    
    @staticmethod
    def query_all():
        from app import mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM kecamatan")
        results = cursor.fetchall()
        
        return [Kecamatan(
            id=r['id'],
            nama_kecamatan=r['nama_kecamatan'],
            kota_kab_id=r['kota_kab_id'],
            latitude=r['latitude'],
            longitude=r['longitude'],
            geojson_id=r['geojson_id'],
            created_at=r['created_at']
        ) for r in results]

class StandarIndikator:
    def __init__(self, id=None, indikator=None, jenjang=None, nilai_min=None, nilai_max=None, nilai_ideal=None, deskripsi=None, referensi=None):
        self.id = id
        self.indikator = indikator
        self.jenjang = jenjang
        self.nilai_min = nilai_min
        self.nilai_max = nilai_max
        self.nilai_ideal = nilai_ideal
        self.deskripsi = deskripsi
        self.referensi = referensi
    
    @staticmethod
    def query_all():
        from app import mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM standar_indikator")
        results = cursor.fetchall()
        
        return [StandarIndikator(
            id=r['id'],
            indikator=r['indikator'],
            jenjang=r['jenjang'],
            nilai_min=r['nilai_min'],
            nilai_max=r['nilai_max'],
            nilai_ideal=r['nilai_ideal'],
            deskripsi=r['deskripsi'],
            referensi=r['referensi']
        ) for r in results]