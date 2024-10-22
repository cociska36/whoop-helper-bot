import requests

# Словарь для сопоставления sport_id и названия спорта
SPORTS = {
    -1: "Activity", 0: "Running", 1: "Cycling", 16: "Baseball", 17: "Basketball", 18: "Rowing", 
    19: "Fencing", 20: "Field Hockey", 21: "Football", 22: "Golf", 24: "Ice Hockey", 25: "Lacrosse", 
    27: "Rugby", 28: "Sailing", 29: "Skiing", 30: "Soccer", 31: "Softball", 32: "Squash", 33: "Swimming", 
    34: "Tennis", 35: "Track & Field", 36: "Volleyball", 37: "Water Polo", 38: "Wrestling", 39: "Boxing", 
    42: "Dance", 43: "Pilates", 44: "Yoga", 45: "Weightlifting", 47: "Cross Country Skiing", 48: "Functional Fitness", 
    49: "Duathlon", 51: "Gymnastics", 52: "Hiking/Rucking", 53: "Horseback Riding", 55: "Kayaking", 
    56: "Martial Arts", 57: "Mountain Biking", 59: "Powerlifting", 60: "Rock Climbing", 61: "Paddleboarding", 
    62: "Triathlon", 63: "Walking", 64: "Surfing", 65: "Elliptical", 66: "Stairmaster", 70: "Meditation", 
    71: "Other", 73: "Diving", 74: "Operations - Tactical", 75: "Operations - Medical", 76: "Operations - Flying", 
    77: "Operations - Water", 82: "Ultimate", 83: "Climber", 84: "Jumping Rope", 85: "Australian Football", 
    86: "Skateboarding", 87: "Coaching", 88: "Ice Bath", 89: "Commuting", 90: "Gaming", 91: "Snowboarding", 
    92: "Motocross", 93: "Caddying", 94: "Obstacle Course Racing", 95: "Motor Racing", 96: "HIIT", 97: "Spin", 
    98: "Jiu Jitsu", 99: "Manual Labor", 100: "Cricket", 101: "Pickleball", 102: "Inline Skating", 103: "Box Fitness", 
    104: "Spikeball", 105: "Wheelchair Pushing", 106: "Paddle Tennis", 107: "Barre", 108: "Stage Performance", 
    109: "High Stress Work", 110: "Parkour", 111: "Gaelic Football", 112: "Hurling/Camogie", 113: "Circus Arts", 
    121: "Massage Therapy", 123: "Strength Trainer", 125: "Watching Sports", 126: "Assault Bike", 
    127: "Kickboxing", 128: "Stretching", 230: "Table Tennis", 231: "Badminton", 232: "Netball", 
    233: "Sauna", 234: "Disc Golf", 235: "Yard Work", 236: "Air Compression", 237: "Percussive Massage", 
    238: "Paintball", 239: "Ice Skating", 240: "Handball"
}

def flatten_user_data(data):
    flat_data = ""
    if isinstance(data, dict):
        # Присваиваем значение user_id переменной flat_data
        flat_data = data["user_id"]
    return flat_data

def get_recovery_data(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = "https://api.prod.whoop.com/developer/v1/recovery"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        recovery_data = response.json()
        return recovery_data
    else:
        print("Error:", response.status_code, response.text)

def flatten_recovery_data(data):
    flat_data = []
    for entry in data['records']:
        # Извлекаем необходимые поля, корректируя ключи по мере необходимости
        entry_data = {
            "cycle_id": entry["cycle_id"],
            "sleep_id": entry["sleep_id"],
            "user_id": entry["user_id"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
            "score_state": entry["score_state"],
            "user_calibrating": entry["score"]["user_calibrating"],
            "recovery_score": entry["score"]["recovery_score"],
            "resting_heart_rate": entry["score"]["resting_heart_rate"],
            "hrv_rmssd_milli": entry["score"]["hrv_rmssd_milli"],
            "spo2_percentage": entry["score"]["spo2_percentage"],
            "skin_temp_celsius": entry["score"]["skin_temp_celsius"]
        }
        flat_data.append(list(entry_data.values()))  # Преобразуем в список
    
    return flat_data

def get_all_workouts(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = "https://api.prod.whoop.com/developer/v1/activity/workout"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        workouts_data = response.json()
        return workouts_data
    else:
        print("Error:", response.status_code, response.text)

def flatten_workout_data(data):
    flat_data = []
    for entry in data['records']:
        # Получаем sport_id
        sport_id = entry.get("sport_id")
        # Получаем название спорта на основе sport_id
        sport_name = SPORTS.get(sport_id, "Unknown")

        # Извлекаем необходимые поля, корректируя ключи по мере необходимости
        entry_data = {
            "id": entry.get("id"),
            "user_id": entry.get("user_id"),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at"),
            "start": entry.get("start"),
            "end": entry.get("end"),
            "timezone_offset": entry.get("timezone_offset"),
            "sport_id": sport_id,
            "sport_name": sport_name,
            "score_state": entry.get("score_state"),
            "strain": entry["score"].get("strain"),
            "average_heart_rate": entry["score"].get("average_heart_rate"),
            "max_heart_rate": entry["score"].get("max_heart_rate"),
            "kilojoule": entry["score"].get("kilojoule"),
            "percent_recorded": entry["score"].get("percent_recorded"),
            "distance_meter": entry["score"].get("distance_meter"),
            "altitude_gain_meter": entry["score"].get("altitude_gain_meter"),
            "altitude_change_meter": entry["score"].get("altitude_change_meter"),
            "zone_zero_milli": entry["score"]["zone_duration"].get("zone_zero_milli"),
            "zone_one_milli": entry["score"]["zone_duration"].get("zone_one_milli"),
            "zone_two_milli": entry["score"]["zone_duration"].get("zone_two_milli"),
            "zone_three_milli": entry["score"]["zone_duration"].get("zone_three_milli"),
            "zone_four_milli": entry["score"]["zone_duration"].get("zone_four_milli"),
            "zone_five_milli": entry["score"]["zone_duration"].get("zone_five_milli"),
        }

        flat_data.append(list(entry_data.values()))  # Преобразуем в список
    return flat_data

def get_all_sleep_sessions(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = "https://api.prod.whoop.com/developer/v1/activity/sleep"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        sleep_data = response.json()
        return sleep_data
    else:
        print("Error:", response.status_code, response.text)

def flatten_sleep_data(data):
    flat_data = []
    for entry in data['records']:
        # Извлекаем необходимые поля, корректируя ключи по мере необходимости
        entry_data = {
            "id": entry.get("id"),
            "user_id": entry.get("user_id"),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at"),
            "start": entry.get("start"),
            "end": entry.get("end"),
            "timezone_offset": entry.get("timezone_offset"),
            "nap": entry.get("nap"),
            "score_state": entry.get("score_state"),
            "total_in_bed_time_milli": entry["score"]["stage_summary"].get("total_in_bed_time_milli"),
            "total_awake_time_milli": entry["score"]["stage_summary"].get("total_awake_time_milli"),
            "total_no_data_time_milli": entry["score"]["stage_summary"].get("total_no_data_time_milli"),
            "total_light_sleep_time_milli": entry["score"]["stage_summary"].get("total_light_sleep_time_milli"),
            "total_slow_wave_sleep_time_milli": entry["score"]["stage_summary"].get("total_slow_wave_sleep_time_milli"),
            "total_rem_sleep_time_milli": entry["score"]["stage_summary"].get("total_rem_sleep_time_milli"),
            "sleep_cycle_count": entry["score"]["stage_summary"].get("sleep_cycle_count"),
            "disturbance_count": entry["score"]["stage_summary"].get("disturbance_count"),
            "baseline_sleep_needed_milli": entry["score"]["sleep_needed"].get("baseline_milli"),
            "need_from_sleep_debt_milli": entry["score"]["sleep_needed"].get("need_from_sleep_debt_milli"),
            "need_from_recent_strain_milli": entry["score"]["sleep_needed"].get("need_from_recent_strain_milli"),
            "need_from_recent_nap_milli": entry["score"]["sleep_needed"].get("need_from_recent_nap_milli"),
            "respiratory_rate": entry["score"].get("respiratory_rate"),
            "sleep_performance_percentage": entry["score"].get("sleep_performance_percentage"),
            "sleep_consistency_percentage": entry["score"].get("sleep_consistency_percentage"),
            "sleep_efficiency_percentage": entry["score"].get("sleep_efficiency_percentage")
        }

        flat_data.append(list(entry_data.values()))  # Преобразуем в список
    return flat_data

def get_all_cycles(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = "https://api.prod.whoop.com/developer/v1/cycle"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        cycles_data = response.json()
        return cycles_data
    else:
        print("Error:", response.status_code, response.text)

def flatten_cycles_data(data):
    flat_data = []
    for entry in data['records']:
        # Извлекаем необходимые поля, корректируя ключи по мере необходимости
        entry_data = {
            "id": entry.get("id"),
            "user_id": entry.get("user_id"),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at"),
            "start": entry.get("start"),
            "end": entry.get("end"),
            "timezone_offset": entry.get("timezone_offset"),
            "score_state": entry.get("score_state"),
            "strain": entry["score"].get("strain"),
            "kilojoule": entry["score"].get("kilojoule"),
            "average_heart_rate": entry["score"].get("average_heart_rate"),
            "max_heart_rate": entry["score"].get("max_heart_rate")
        }

        flat_data.append(list(entry_data.values()))  # Преобразуем в список
    return flat_data