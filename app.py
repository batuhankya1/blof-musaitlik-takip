import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
from database import DAYS, DAY_INDEX_TO_NAME
from availability import query_group_availability
from parser import (
    parse_schedule_image_with_gemini,
    parse_schedule_text,
    SAMPLE_SCHEDULES,
    sanitize_extracted_classes
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# Kalıcı session secret key (Vercel gibi ortamlarda read-only hata vermez)
app.secret_key = os.environ.get('SECRET_KEY', 'blof-musaitlik-takip-secret-key-2026')
if not os.environ.get('VERCEL'):
    SECRET_KEY_PATH = os.path.join(BASE_DIR, '.secret_key')
    try:
        if os.path.exists(SECRET_KEY_PATH):
            with open(SECRET_KEY_PATH, 'rb') as f:
                app.secret_key = f.read()
        else:
            key = os.urandom(32)
            with open(SECRET_KEY_PATH, 'wb') as f:
                f.write(key)
            app.secret_key = key
    except Exception:
        pass

app.permanent_session_lifetime = timedelta(days=30)

# Veritabanını başlat
db.init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Giriş yapmanız gerekiyor.'}), 401
            return redirect(url_for('login_page', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    current_user = None
    if 'user_id' in session:
        current_user = db.find_user_by_id(session['user_id'])
    return {
        'current_user': current_user,
        'DAYS': DAYS
    }

# ----------------- SAYFA ROTALARI -----------------

@app.route('/')
@login_required
def index_page():
    """Ana sayfa: Kim Boş? sorgu paneli"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index_page'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/schedule')
@login_required
def schedule_page():
    """Kullanıcının kendi ders programını düzenleme ve görsel yükleme sayfası"""
    return render_template('schedule.html')

@app.route('/group-calendar')
@login_required
def group_calendar_page():
    """Tüm arkadaşların ortak haftalık takvimi"""
    return render_template('group_calendar.html')

@app.route('/friends')
@login_required
def friends_page():
    """Arkadaş listesi ve tekil program inceleme"""
    return render_template('friends.html')

# ----------------- KULLANICI & KİMLİK DOĞRULAMA API -----------------

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    remember_me = bool(data.get('remember_me', True))
    
    if not name or not email or not password:
        return jsonify({'error': 'Lütfen isim, e-posta ve şifre alanlarını doldurun.'}), 400
        
    if len(name) < 2:
        return jsonify({'error': 'İsim en az 2 karakter olmalıdır.'}), 400
        
    if len(password) < 4:
        return jsonify({'error': 'Şifre en az 4 karakter olmalıdır.'}), 400

    # Büyük/küçük harf duyarsız isim kontrolü
    if db.find_user_by_name(name):
        return jsonify({'error': f"'{name}' ismi ile zaten kayıtlı bir üye var. Lütfen giriş yapın veya farklı bir isim seçin."}), 400
        
    if db.find_user_by_email(email):
        return jsonify({'error': f"'{email}' e-posta adresi zaten kullanılıyor."}), 400
        
    pwd_hash = generate_password_hash(password)
    user_id = db.create_user(name=name, email=email, password_hash=pwd_hash)
    
    # Oturum aç
    session['user_id'] = user_id
    session['user_name'] = name
    session.permanent = remember_me
    
    return jsonify({
        'success': True,
        'message': f'Hoş geldin, {name}! Kaydın başarıyla oluşturuldu.',
        'user': {'id': user_id, 'name': name, 'email': email},
        'is_new_user': True
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    password = (data.get('password') or '').strip()
    remember_me = bool(data.get('remember_me', False))
    
    if not name or not password:
        return jsonify({'error': 'Lütfen isim ve şifrenizi girin.'}), 400
        
    # Büyük / küçük harf duyarsız isim arama
    user = db.find_user_by_name(name)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Kullanıcı adı veya şifre hatalı.'}), 401
        
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session.permanent = remember_me
    
    # Kullanıcının ders programı var mı kontrol et
    classes = db.get_user_classes(user['id'])
    has_schedule = len(classes) > 0
    
    return jsonify({
        'success': True,
        'message': f"Tekrar hoş geldin, {user['name']}!",
        'user': {'id': user['id'], 'name': user['name'], 'email': user['email']},
        'has_schedule': has_schedule
    })

@app.route('/api/me')
@login_required
def api_me():
    user = db.find_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'Kullanıcı bulunamadı.'}), 404
    classes = db.get_user_classes(user['id'])
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'avatar_color': user['avatar_color'],
            'created_at': user['created_at'],
            'class_count': len(classes)
        }
    })

# ----------------- DERS PROGRAMI YÖNETİMİ API -----------------

@app.route('/api/schedule', methods=['GET'])
@login_required
def api_get_my_schedule():
    classes = db.get_user_classes(session['user_id'])
    return jsonify({'classes': classes})

@app.route('/api/schedule/<int:user_id>', methods=['GET'])
@login_required
def api_get_user_schedule(user_id):
    user = db.find_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
    classes = db.get_user_classes(user_id)
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'avatar_color': user['avatar_color']
        },
        'classes': classes
    })

@app.route('/api/schedule', methods=['POST'])
@login_required
def api_save_my_schedule():
    """Tüm ders listesini toplu kaydeder"""
    data = request.get_json() or {}
    classes_list = data.get('classes', [])
    sanitized = sanitize_extracted_classes(classes_list)
    db.save_all_classes_for_user(session['user_id'], sanitized)
    return jsonify({
        'success': True,
        'message': f'{len(sanitized)} ders başarıyla kaydedildi.',
        'classes': sanitized
    })

@app.route('/api/classes', methods=['POST'])
@login_required
def api_add_class():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    day_index = int(data.get('day_index', 0))
    start_time = (data.get('start_time') or '').strip()
    end_time = (data.get('end_time') or '').strip()
    location = (data.get('location') or '').strip()
    color = data.get('color', '#3B82F6')
    
    if not title or not start_time or not end_time:
        return jsonify({'error': 'Ders adı, başlangıç ve bitiş saati zorunludur.'}), 400
        
    class_id = db.add_class(
        user_id=session['user_id'],
        day_index=day_index,
        start_time=start_time,
        end_time=end_time,
        title=title,
        location=location,
        color=color
    )
    return jsonify({'success': True, 'class_id': class_id})

@app.route('/api/classes/<int:class_id>', methods=['PUT'])
@login_required
def api_update_class(class_id):
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    day_index = int(data.get('day_index', 0))
    start_time = (data.get('start_time') or '').strip()
    end_time = (data.get('end_time') or '').strip()
    location = (data.get('location') or '').strip()
    color = data.get('color', '#3B82F6')
    
    db.update_class(
        class_id=class_id,
        user_id=session['user_id'],
        day_index=day_index,
        start_time=start_time,
        end_time=end_time,
        title=title,
        location=location,
        color=color
    )
    return jsonify({'success': True})

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
@login_required
def api_delete_class(class_id):
    db.delete_class(class_id, session['user_id'])
    return jsonify({'success': True})

@app.route('/api/schedule/load-sample', methods=['POST'])
@login_required
def api_load_sample_schedule():
    """Örnek hazır program yükleme (Sabancı/SUIS, Mühendislik, Tıp, Hukuk)"""
    data = request.get_json() or {}
    sample_key = data.get('key', 'sabanci')
    sample = SAMPLE_SCHEDULES.get(sample_key)
    if not sample:
        sample = SAMPLE_SCHEDULES['sabanci']
        
    db.save_all_classes_for_user(session['user_id'], sample)
    display_names = {
        'sabanci': 'Sabancı Üniversitesi (SUIS)',
        'muhendislik': 'Mühendislik Fakültesi',
        'tip': 'Tıp Fakültesi',
        'hukuk': 'Hukuk Fakültesi'
    }
    return jsonify({
        'success': True,
        'message': f"'{display_names.get(sample_key, sample_key)}' programı başarıyla yüklendi ({len(sample)} ders).",
        'classes': sample
    })

@app.route('/api/schedule/parse-text', methods=['POST'])
@login_required
def api_parse_text():
    """Kullanıcının yapıştırdığı metinden dersleri çıkarır"""
    data = request.get_json() or {}
    raw_text = data.get('text', '')
    if not raw_text.strip():
        return jsonify({'error': 'Lütfen ders programı metnini yapıştırın.'}), 400
        
    classes = parse_schedule_text(raw_text)
    if not classes:
        return jsonify({'error': 'Metinden uygun ders saati tespit edilemedi. Örnek formatlar:\n- Monday 9:40 am - 10:30 am MATH 203\n- Pazartesi 09:00 - 11:50 Algoritmalar'}), 400
        
    return jsonify({
        'success': True,
        'classes': classes,
        'message': f'{len(classes)} ders başarıyla tespit edildi! Aşağıdaki tablodan kontrol edip kaydedebilirsiniz.'
    })

@app.route('/api/schedule/parse-image', methods=['POST'])
@login_required
def api_parse_image():
    """
    Kullanıcının yüklediği ders programı ekran görüntüsünü Gemini 3.5 Flash Vision ile ayrıştırır.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'Lütfen bir görsel dosyası seçin.'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi.'}), 400
        
    image_bytes = file.read()
    mime_type = file.mimetype or 'image/png'

    # 1. Doğrudan sistemin global Gemini 3.5 Flash anahtarını kullan
    try:
        classes = parse_schedule_image_with_gemini(image_bytes, mime_type)
        if classes and len(classes) > 0:
            return jsonify({
                'success': True,
                'classes': classes,
                'message': f'Yapay zeka ile görsel analiz edildi! {len(classes)} ders tespit edildi.'
            })
    except Exception as e:
        gemini_err = str(e)
        print("Gemini Vision API hatası:", e)

    return jsonify({
        'success': False,
        'error': f'Görsel analiz edilemedi ({gemini_err}). İpucu: Çizelgenizi "Metin Yapıştır" sekmesine yapıştırabilir veya hazır şablon seçebilirsiniz.'
    }), 400

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """Kullanıcıyı ve derslerini sistemden tamamen siler"""
    user = db.find_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'Kullanıcı bulunamadı.'}), 404
        
    db.delete_user(user_id)
    is_self = (session.get('user_id') == user_id)
    if is_self:
        session.clear()
        
    return jsonify({
        'success': True,
        'message': f"'{user['name']}' kullanıcısı ve ders programı başarıyla silindi.",
        'is_self': is_self
    })

@app.route('/api/users/clear-demos', methods=['POST'])
@login_required
def api_clear_demos():
    """Tüm demo kullanıcılarını (Ahmet, Zeynep, Burak, Ayşe) tek tıkla siler"""
    db.delete_demo_users()
    return jsonify({'success': True, 'message': 'Hazır demo hesaplar başarıyla temizlendi.'})

# ----------------- MÜSAİTLİK & KİM BOŞ SORGULAMA API -----------------

@app.route('/api/availability')
@login_required
def api_availability():
    """
    Kim Boş? sorgu motoru.
    Girdi: ?day=1&time=14:30
    Varsayılan: Şu anki gün ve saat
    """
    now = datetime.now()
    
    # Gün parametresi (0-6)
    day_param = request.args.get('day')
    if day_param is not None and day_param != '':
        day_index = int(day_param) % 7
    else:
        day_index = now.weekday() # 0: Pazartesi ... 6: Pazar
        
    # Saat parametresi ('HH:MM')
    time_param = request.args.get('time')
    if time_param:
        query_time = time_param.strip()
    else:
        query_time = now.strftime('%H:%M')
        
    all_users = db.get_all_users()
    
    # Tüm kullanıcıların derslerini çek
    all_classes_by_user = {}
    for u in all_users:
        all_classes_by_user[u['id']] = db.get_user_classes(u['id'], day_index=day_index)
        
    result = query_group_availability(all_users, all_classes_by_user, day_index, query_time)
    result['day_name'] = DAY_INDEX_TO_NAME.get(day_index, 'Pazartesi')
    return jsonify(result)

@app.route('/api/all-friends')
@login_required
def api_all_friends():
    users = db.get_all_users()
    return jsonify({'friends': users})

@app.route('/api/settings/gemini-key', methods=['GET', 'POST'])
@login_required
def api_gemini_key():
    if request.method == 'POST':
        data = request.get_json() or {}
        key = data.get('api_key', '').strip()
        db.set_setting('gemini_api_key', key)
        return jsonify({'success': True, 'message': 'API Anahtarı kaydedildi.'})
    else:
        val = db.get_setting('gemini_api_key', '')
        has_key = bool(val)
        masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else ("Var" if has_key else "Yok")
        return jsonify({'has_key': has_key, 'masked_key': masked})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"KimBos sunucusu calisiyor: http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
