"""
KimBoş - Örnek Arkadaş Grubu ve Ders Programı Yükleyici
Bu betik veritabanına hazır 4 arkadaş ve gerçekçi ders programları ekler.
"""

from werkzeug.security import generate_password_hash
from database import init_db, get_db, find_user_by_name, create_user, save_all_classes_for_user
from parser import SAMPLE_SCHEDULES

DEMO_FRIENDS = [
    {
        "name": "Ahmet",
        "email": "ahmet@kampus.edu.tr",
        "password": "password123",
        "avatar_color": "#3B82F6",
        "schedule_type": "muhendislik"
    },
    {
        "name": "Zeynep",
        "email": "zeynep@kampus.edu.tr",
        "password": "password123",
        "avatar_color": "#EC4899",
        "schedule_type": "tip"
    },
    {
        "name": "Burak",
        "email": "burak@kampus.edu.tr",
        "password": "password123",
        "avatar_color": "#10B981",
        "schedule_type": "hukuk"
    },
    {
        "name": "Ayşe",
        "email": "ayse@kampus.edu.tr",
        "password": "password123",
        "avatar_color": "#F59E0B",
        "schedule": [
            {"day_index": 0, "day_name": "Pazartesi", "start_time": "11:00", "end_time": "12:50", "title": "Mikroiktisat", "location": "İİBF 101", "color": "#F59E0B"},
            {"day_index": 0, "day_name": "Pazartesi", "start_time": "13:00", "end_time": "14:50", "title": "İşletme Yönetimi", "location": "İİBF 204", "color": "#8B5CF6"},
            {"day_index": 1, "day_name": "Salı", "start_time": "09:00", "end_time": "10:50", "title": "Pazarlama İlkeleri", "location": "İİBF 105", "color": "#3B82F6"},
            {"day_index": 1, "day_name": "Salı", "start_time": "11:00", "end_time": "12:50", "title": "Muhasebe I", "location": "İİBF 102", "color": "#10B981"},
            {"day_index": 2, "day_name": "Çarşamba", "start_time": "10:00", "end_time": "11:50", "title": "Finansal Yönetim", "location": "İİBF 301", "color": "#EF4444"},
            {"day_index": 3, "day_name": "Perşembe", "start_time": "13:00", "end_time": "15:50", "title": "İstatistik", "location": "İİBF Lab", "color": "#06B6D4"},
            {"day_index": 4, "day_name": "Cuma", "start_time": "10:00", "end_time": "12:50", "title": "Uluslararası Ticaret", "location": "İİBF 201", "color": "#EC4899"}
        ]
    }
]

def seed_demo_data():
    init_db()
    for friend in DEMO_FRIENDS:
        existing = find_user_by_name(friend["name"])
        if not existing:
            pwd_hash = generate_password_hash(friend["password"])
            user_id = create_user(
                name=friend["name"],
                email=friend["email"],
                password_hash=pwd_hash,
                avatar_color=friend["avatar_color"]
            )
            print(f"Olusturuldu: {friend['name']} (ID: {user_id})")
            
            schedule = friend.get("schedule")
            if not schedule and friend.get("schedule_type"):
                schedule = SAMPLE_SCHEDULES.get(friend["schedule_type"], [])
                
            if schedule:
                save_all_classes_for_user(user_id, schedule)
                print(f" -> {len(schedule)} ders eklendi.")
        else:
            print(f"Zaten mevcut: {friend['name']}")

if __name__ == '__main__':
    seed_demo_data()
