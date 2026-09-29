"""
KimBoş - Müsaitlik ve Ders Arası Hesaplama Motoru

Kural:
"boş duruma çıkabilmesi için aranın 15 dakikadan fazla olması gerekiyor"
- İki ders arasındaki mola 15 dakika veya daha azsa, kullanıcı bu aralıkta boş sayılmaz (zincirleme dolu kabul edilir).
- Kullanıcının boş sayılabilmesi için ya o gün hiç dersi olmamalı, ya tüm dersleri bitmiş olmalı, 
  ya ilk dersine 15 dakikadan fazla süre olmalı, ya da iki ders arasındaki mola 15 dakikadan uzun olup 
  sıradaki derse en az 15 dakika kalmış olmalıdır.
"""

from datetime import datetime, time

def time_to_minutes(time_str):
    """'HH:MM' formatındaki saati günün başlangıcından itibaren dakikaya çevirir."""
    try:
        parts = time_str.strip().split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0

def minutes_to_time(minutes):
    """Dakikayı 'HH:MM' formatına çevirir."""
    minutes = max(0, min(1439, minutes))
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def format_duration(minutes):
    """Dakika süresini kullanıcı dostu metne dönüştürür (örn: '1 sa 45 dk' veya '40 dk')."""
    if minutes <= 0:
        return "0 dk"
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h} saat {m} dk"
    elif h > 0:
        return f"{h} saat"
    else:
        return f"{m} dk"

def build_busy_chains(classes):
    """
    Kullanıcının o günkü derslerini alır ve aralarında 15 dakika veya daha az
    fark olan ardışık dersleri tek bir 'zincirlenmiş dolu blok' haline birleştirir.
    
    Her bir blok:
    {
        'start_min': int,
        'end_min': int,
        'start_time': str,
        'end_time': str,
        'classes': list of class dicts,
        'summary': str
    }
    """
    if not classes:
        return []
    
    # Başlangıç saatine göre sırala
    sorted_classes = sorted(classes, key=lambda c: time_to_minutes(c['start_time']))
    
    chains = []
    current_chain = None
    
    for c in sorted_classes:
        c_start = time_to_minutes(c['start_time'])
        c_end = time_to_minutes(c['end_time'])
        
        # Hatalı saat girişi önleme
        if c_end <= c_start:
            c_end = c_start + 50 # Varsayılan 50 dk
            
        c_obj = dict(c)
        c_obj['start_min'] = c_start
        c_obj['end_min'] = c_end
        
        if current_chain is None:
            current_chain = {
                'start_min': c_start,
                'end_min': c_end,
                'classes': [c_obj]
            }
        else:
            # Önceki ders ile bu ders arasındaki mola
            gap = c_start - current_chain['end_min']
            
            # KURAL: Ara 15 dakika veya daha azsa birleştir!
            if gap <= 15:
                # Blok genişletilir
                current_chain['end_min'] = max(current_chain['end_min'], c_end)
                current_chain['classes'].append(c_obj)
            else:
                # Zincir bitti, listeye ekle ve yenisini başlat
                current_chain['start_time'] = minutes_to_time(current_chain['start_min'])
                current_chain['end_time'] = minutes_to_time(current_chain['end_min'])
                chains.append(current_chain)
                current_chain = {
                    'start_min': c_start,
                    'end_min': c_end,
                    'classes': [c_obj]
                }
                
    if current_chain:
        current_chain['start_time'] = minutes_to_time(current_chain['start_min'])
        current_chain['end_time'] = minutes_to_time(current_chain['end_min'])
        chains.append(current_chain)
        
    return chains

def evaluate_user_status(user, classes_for_day, query_minutes):
    """
    Belirli bir kullanıcı ve gün için sorgu dakikasındaki (query_minutes)
    durumu tespit eder:
    
    Dönüş:
    {
        'user': user_dict,
        'is_free': bool,
        'status_type': 'FREE' | 'BUSY',
        'badge_label': 'Boş' | 'Dolu',
        'current_activity': str,
        'busy_until': str or None,
        'free_until': str or None,
        'remaining_duration_text': str,
        'details': str,
        'reason': str,
        'next_class': dict or None
    }
    """
    result = {
        'user_id': user['id'],
        'name': user['name'],
        'avatar_color': user.get('avatar_color', '#4F46E5'),
        'email': user.get('email', ''),
        'is_free': True,
        'status_type': 'FREE',
        'badge_label': 'Boş',
        'current_activity': 'Müsait',
        'busy_until': None,
        'free_until': None,
        'free_minutes': 0,
        'remaining_duration_text': '',
        'details': '',
        'reason': '',
        'next_class': None
    }
    
    # 1. O gün hiç ders yoksa
    if not classes_for_day:
        result['is_free'] = True
        result['status_type'] = 'FREE'
        result['badge_label'] = 'Tüm Gün Boş'
        result['current_activity'] = 'Bugün dersi yok'
        result['free_until'] = 'Günün Sonu'
        result['free_minutes'] = 1440 - query_minutes
        result['remaining_duration_text'] = 'Tüm gün müsait 🎉'
        result['details'] = 'Bugün hiç dersi görünmüyor.'
        return result
        
    # Zincirleri oluştur
    chains = build_busy_chains(classes_for_day)
    
    # Sıralı tekil dersler
    sorted_classes = sorted(classes_for_day, key=lambda c: time_to_minutes(c['start_time']))
    
    # Sorgu dakikasının hangi zincirde veya aralıkta olduğunu bul
    for chain in chains:
        c_start = chain['start_min']
        c_end = chain['end_min']
        
        # Durum 1: Kullanıcı bu zincirlenmiş dolu blok içinde (ders veya <= 15 dk mola)
        if c_start <= query_minutes < c_end:
            result['is_free'] = False
            result['status_type'] = 'BUSY'
            result['badge_label'] = 'Dolu'
            result['busy_until'] = chain['end_time']
            mins_left = c_end - query_minutes
            result['remaining_duration_text'] = f"{chain['end_time']}'a kadar ({format_duration(mins_left)})"
            
            # Şu an tam olarak hangi derste veya molada?
            active_class = None
            in_short_break = False
            prev_c = None
            next_c = None
            
            for i, cls in enumerate(chain['classes']):
                s = cls['start_min']
                e = cls['end_min']
                if s <= query_minutes < e:
                    active_class = cls
                    break
                elif prev_c and prev_c['end_min'] <= query_minutes < s:
                    # İki ders arasındaki <= 15 dk mola
                    in_short_break = True
                    next_c = cls
                    break
                prev_c = cls
                
            if active_class:
                result['current_activity'] = active_class['title']
                loc = f" ({active_class['location']})" if active_class.get('location') else ""
                result['details'] = f"Şu an '{active_class['title']}'{loc} dersinde. Saat {chain['end_time']}'a kadar dolu."
            elif in_short_break and next_c:
                result['current_activity'] = f"Kısa Ders Arası (15 dk altı)"
                result['details'] = f"Önceki ders bitti, saat {next_c['start_time']}'daki '{next_c['title']}' dersine geçiyor (ara 15 dk altı olduğu için dolu sayılıyor)."
            else:
                result['current_activity'] = chain['classes'][0]['title']
                result['details'] = f"Saat {chain['end_time']}'a kadar dolu."
                
            result['reason'] = f"{chain['end_time']}'a kadar zincirli ders programı var."
            return result

    # Durum 2: Sorgu saati zincirlerin dışındaysa (Boş veya derse çok az kalmış)
    
    # 2a. Günün ilk dersinden önce mi?
    first_chain = chains[0]
    if query_minutes < first_chain['start_min']:
        diff = first_chain['start_min'] - query_minutes
        first_class = first_chain['classes'][0]
        result['next_class'] = first_class
        
        # Sıradaki derse 15 dakika veya daha az kalmışsa:
        if diff <= 15:
            result['is_free'] = False
            result['status_type'] = 'BUSY'
            result['badge_label'] = 'Dolu (Derse Az Kaldı)'
            result['busy_until'] = first_chain['end_time']
            result['current_activity'] = f"Derse Hazırlık ({first_class['title']})"
            result['remaining_duration_text'] = f"{diff} dk sonra dersi var (Dolu: {first_chain['end_time']}'a kadar)"
            result['details'] = f"Dersin başlamasına sadece {diff} dakika var (15 dk altı mola kuralı). Saat {first_chain['end_time']}'a kadar meşgul."
            return result
        else:
            result['is_free'] = True
            result['status_type'] = 'FREE'
            result['badge_label'] = 'Boş'
            result['free_until'] = first_class['start_time']
            result['free_minutes'] = diff
            result['current_activity'] = 'İlk derse kadar müsait'
            result['remaining_duration_text'] = f"{first_class['start_time']}'a kadar boş ({format_duration(diff)})"
            loc = f" ({first_class['location']})" if first_class.get('location') else ""
            result['details'] = f"İlk dersi {first_class['start_time']}'da '{first_class['title']}'{loc}."
            return result

    # 2b. Günün son dersinden sonra mı?
    last_chain = chains[-1]
    if query_minutes >= last_chain['end_min']:
        diff = 1440 - query_minutes
        result['is_free'] = True
        result['status_type'] = 'FREE'
        result['badge_label'] = 'Günün Sonu Boş'
        result['free_until'] = 'Günün Sonu'
        result['free_minutes'] = diff
        result['current_activity'] = 'Tüm dersleri bitti 🎉'
        result['remaining_duration_text'] = 'Günün geri kalanında tamamen müsait'
        result['details'] = f"Bugünkü son dersi {last_chain['end_time']}'da bitti. Artık tamamen serbest!"
        return result

    # 2c. İki büyük zincir arasındaki boşlukta mı? (> 15 dakika olan gerçek mola)
    for i in range(len(chains) - 1):
        chain_before = chains[i]
        chain_after = chains[i + 1]
        
        if chain_before['end_min'] <= query_minutes < chain_after['start_min']:
            # Bu boşluk > 15 dakikadır (çünkü <= 15 olsaydı build_busy_chains birleştirirdi)
            total_gap = chain_after['start_min'] - chain_before['end_min']
            time_until_next = chain_after['start_min'] - query_minutes
            next_class = chain_after['classes'][0]
            result['next_class'] = next_class
            
            # Eğer sıradaki derse 15 dakika veya daha az kalmışsa:
            if time_until_next <= 15:
                result['is_free'] = False
                result['status_type'] = 'BUSY'
                result['badge_label'] = 'Dolu (Derse Az Kaldı)'
                result['busy_until'] = chain_after['end_time']
                result['current_activity'] = f"Derse Hazırlık ({next_class['title']})"
                result['remaining_duration_text'] = f"{time_until_next} dk sonra dersi var (Dolu: {chain_after['end_time']}'a kadar)"
                result['details'] = f"Bir sonraki ders {next_class['start_time']}'da başlıyor ({time_until_next} dk kaldı). 15 dakikadan az süre kaldığı için dolu kabul ediliyor."
                return result
            else:
                result['is_free'] = True
                result['status_type'] = 'FREE'
                result['badge_label'] = 'Boş'
                result['free_until'] = chain_after['start_time']
                result['free_minutes'] = time_until_next
                result['current_activity'] = f"Ders arası boşluk ({format_duration(total_gap)})"
                result['remaining_duration_text'] = f"{chain_after['start_time']}'a kadar boş ({format_duration(time_until_next)})"
                loc = f" ({next_class['location']})" if next_class.get('location') else ""
                result['details'] = f"Saat {chain_after['start_time']}'daki '{next_class['title']}'{loc} dersine kadar {format_duration(time_until_next)} müsait."
                return result

    return result

def query_group_availability(users, all_classes_by_user, day_index, query_time_str):
    """
    Belirli bir gün ve saat için tüm arkadaş grubunun müsaitlik listesini döndürür.
    
    ÖNEMLİ KURAL GEREĞİ:
    - En başta BOŞ OLANLAR (free_list)
    - Listenin altında DOLU OLANLAR (busy_list - saat kaça kadar dolu oldukları ile)
    """
    query_minutes = time_to_minutes(query_time_str)
    
    free_users = []
    busy_users = []
    
    for u in users:
        u_classes = all_classes_by_user.get(u['id'], [])
        # Sadece sorgulanan güne ait olanlar
        day_classes = [c for c in u_classes if c['day_index'] == day_index]
        
        status = evaluate_user_status(u, day_classes, query_minutes)
        
        if status['is_free']:
            free_users.append(status)
        else:
            busy_users.append(status)
            
    # Boş olanları en uzun süre boş olanlara göre sırala (veya isme göre)
    free_users.sort(key=lambda s: (-s['free_minutes'], s['name'].lower()))
    
    # Dolu olanları en erken boşa çıkacak olanlara göre sırala
    busy_users.sort(key=lambda s: (time_to_minutes(s['busy_until'] or '23:59'), s['name'].lower()))
    
    return {
        'day_index': day_index,
        'query_time': query_time_str,
        'total_count': len(users),
        'free_count': len(free_users),
        'busy_count': len(busy_users),
        'free_users': free_users,
        'busy_users': busy_users
    }
