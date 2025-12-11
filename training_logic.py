from datetime import datetime
import statistics

# --- Парсер Strava ---
def parse_strava_activities(raw):
    workouts = []
    for a in raw:
        try:
            distance_km = a.get("distance", 0) / 1000
            moving_min = a.get("moving_time", 0) / 60
            avg_speed = a.get("average_speed", None)  # м/с

            pace_min_per_km = (1000 / avg_speed) / 60 if avg_speed else (moving_min / distance_km if distance_km > 0 else None)
            speed_kmh = distance_km / (moving_min / 60) if moving_min > 0 else 0

            workouts.append({
                "distance_km": distance_km,
                "time_min": moving_min,
                "pace": pace_min_per_km,
                "speed_kmh": speed_kmh,
                "date": datetime.strptime(a.get("start_date"), "%Y-%m-%dT%H:%M:%SZ")
            })
        except Exception:
            continue
    return workouts

# --- Расчёты ---
def average_pace(workouts, days):
    now = datetime.now()
    p = [w["pace"] for w in workouts if w["pace"] and (now - w["date"]).days <= days]
    return statistics.mean(p) if p else None

def calculate_ftp(workouts):
    candidates = [w["pace"] for w in workouts if w["pace"]]
    if not candidates:
        return None
    best = sorted(candidates)[:3] if len(candidates) >= 3 else candidates
    return statistics.mean(best) * 0.97

def pace_zones(ftp):
    return {"Z1": ftp + 0.8, "Z2": ftp + 0.4, "Z3": ftp + 0.15, "Z4": ftp - 0.1, "Z5": ftp - 0.25}

def automl_load_adjustment(workouts):
    avg14 = average_pace(workouts, 14)
    avg7 = average_pace(workouts, 7)
    if avg14 is None or avg7 is None:
        return 0.0
    change = avg14 - avg7
    if change > 0.12: return 0.06
    elif change < -0.12: return -0.05
    return 0.02

def pace_to_kmh(pace_min_per_km):
    return 60 / pace_min_per_km if pace_min_per_km else 0

# --- Построение плана ---
def build_week_plan(workouts, goal="pace"):
    if not workouts:
        return "Тренировок в Strava пока нет."

    ftp = calculate_ftp(workouts)
    if ftp is None:
        return "Недостаточно данных для расчёта точного плана. Сделайте хотя бы одну полноценную тренировку."

    zones_min = pace_zones(ftp)
    zones_kmh = {z: pace_to_kmh(p) for z, p in zones_min.items()}
    load_factor = automl_load_adjustment(workouts)
    last_week_km = sum(w["distance_km"] for w in workouts if (datetime.now() - w["date"]).days <= 7)
    target_km = last_week_km * (1 + load_factor)

    if goal == "pace":
        return f"""🎯 Цель: увеличить скорость
ФП: {ftp:.2f} мин/км ({pace_to_kmh(ftp):.2f} км/ч)
Недельный объём: {target_km:.2f} км ({load_factor*100:+.1f}%)
Тренировки:
1) Интервалы — 6×400 м в Z4 = {zones_min['Z4']:.2f} мин/км ({zones_kmh['Z4']:.2f} км/ч)
2) Темповая — 3 км в Z3 = {zones_min['Z3']:.2f} мин/км ({zones_kmh['Z3']:.2f} км/ч)
3) Лёгкий бег — {max(target_km*0.4, 0):.2f} км в Z1 = {zones_min['Z1']:.2f} мин/км ({zones_kmh['Z1']:.2f} км/ч)
"""
    else:  # goal == distance
        long_run = max(target_km * 0.4, 0)
        easy1 = max(target_km * 0.3, 0)
        easy2 = max(target_km * 0.3, 0)
        return f"""🎯 Цель: увеличивать дистанцию
ФП: {ftp:.2f} мин/км ({pace_to_kmh(ftp):.2f} км/ч)
Недельный объём: {target_km:.2f} км ({load_factor*100:+.1f}%)
Тренировки:
1) Длинная пробежка — {long_run:.2f} км, темп Z2 = {zones_min['Z2']:.2f} мин/км ({zones_kmh['Z2']:.2f} км/ч)
2) Лёгкая тренировка — {easy1:.2f} км, темп Z1 = {zones_min['Z1']:.2f} мин/км ({zones_kmh['Z1']:.2f} км/ч)
3) Лёгкая тренировка — {easy2:.2f} км, темп Z1 = {zones_min['Z1']:.2f} мин/км ({zones_kmh['Z1']:.2f} км/ч)
"""
