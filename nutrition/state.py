#!/usr/bin/env python3
"""Nutrition State Manager - pure data layer, no LLM calls."""
import json, sys
from datetime import date, timedelta, datetime
from pathlib import Path

BASE_DIR         = Path(__file__).parent
PROFILE_FILE     = BASE_DIR / "profile.json"
SAVED_MEALS_FILE = BASE_DIR / "saved_meals.json"
DAILY_DIR        = BASE_DIR / "daily"
DAILY_DIR.mkdir(exist_ok=True)

def load_json(path, default=None):
    p = Path(path)
    if p.exists(): return json.loads(p.read_text())
    return default if default is not None else {}

def save_json(path, data): Path(path).write_text(json.dumps(data, indent=2))
def today_str(): return date.today().isoformat()
def now_hm(): return datetime.now().strftime("%H:%M")
def daily_file(day=None): return DAILY_DIR / "{}.json".format(day or today_str())

def load_today():
    f = daily_file()
    if f.exists(): return load_json(f)
    return {"date": today_str(), "food_log": [], "exercise_log": [],
            "calories_consumed": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0,
            "calories_burned": 0, "weight_lb": None, "notes": ""}

def save_today(state):   save_json(daily_file(), state)
def load_profile():      return load_json(PROFILE_FILE)
def save_profile(p):     save_json(PROFILE_FILE, p)
def load_saved_meals():  return load_json(SAVED_MEALS_FILE, {"meals": {}})
def save_saved_meals(m): save_json(SAVED_MEALS_FILE, m)

# -- Write ops

def log_food(entry):
    today = load_today()
    entry.setdefault('logged_at', now_hm())
    today['food_log'].append(entry)
    today['calories_consumed'] = round(today['calories_consumed'] + entry.get('calories', 0), 1)
    today['protein_g']         = round(today['protein_g']         + entry.get('protein_g', 0), 1)
    today['carbs_g']           = round(today['carbs_g']           + entry.get('carbs_g', 0), 1)
    today['fat_g']             = round(today['fat_g']             + entry.get('fat_g', 0), 1)
    save_today(today)
    return today

def log_exercise(entry):
    today = load_today()
    entry.setdefault('logged_at', now_hm())
    today['exercise_log'].append(entry)
    today['calories_burned'] = round(today['calories_burned'] + entry.get('calories_burned', 0), 1)
    save_today(today)
    return today

def log_weight(weight_lb):
    today = load_today()
    today['weight_lb'] = weight_lb
    save_today(today)
    profile = load_profile()
    wlog = profile.setdefault('weight_log', [])
    existing_w = [w for w in wlog if w['date'] == today_str()]
    if existing_w:
        existing_w[0]['weight_lb'] = weight_lb
    else:
        wlog.append({'date': today_str(), 'weight_lb': weight_lb})
    save_profile(profile)
    return today

def save_meal(meal):
    meals_db = load_saved_meals()
    meals_db['meals'][meal['name']] = {k: meal[k] for k in ('calories','protein_g','carbs_g','fat_g')}
    save_saved_meals(meals_db)
    return meals_db

def adjust_hypothesis(new_value, reason):
    profile = load_profile()
    old = profile['calorie_hypothesis']
    profile.setdefault('calorie_hypothesis_history', []).append(
        {'date': today_str(), 'from': old, 'to': new_value, 'reason': reason}
    )
    profile['calorie_hypothesis']           = new_value
    profile['calorie_hypothesis_updated']   = today_str()
    profile['calorie_hypothesis_rationale'] = reason
    save_profile(profile)
    return profile

# -- Read ops

def get_summary():
    profile = load_profile()
    today   = load_today()
    cal_target = profile['calorie_hypothesis']
    macros     = profile['macro_targets']
    return {
        'date': today_str(),
        'cal_target':   cal_target,
        'cal_consumed': today['calories_consumed'],
        'cal_burned':   today['calories_burned'],
        'net_cal':      today['calories_consumed'] - today['calories_burned'],
        'protein_g':    today['protein_g'],
        'carbs_g':      today['carbs_g'],
        'fat_g':        today['fat_g'],
        'rem_cal':      cal_target - today['calories_consumed'],
        'rem_protein':  macros['protein_g'] - today['protein_g'],
        'rem_carbs':    macros['carbs_g']   - today['carbs_g'],
        'rem_fat':      macros['fat_g']     - today['fat_g'],
        'macro_targets':        macros,
        'food_log':             today['food_log'],
        'exercise_log':         today['exercise_log'],
        'weight_lb':            today['weight_lb'],
        'hypothesis_rationale': profile.get('calorie_hypothesis_rationale', ''),
        'hypothesis_updated':   profile.get('calorie_hypothesis_updated', ''),
    }

def get_context_block():
    profile  = load_profile()
    today    = load_today()
    meals_db = load_saved_meals()
    cal_target  = profile['calorie_hypothesis']
    macros      = profile['macro_targets']
    rem_cal     = cal_target - today['calories_consumed']
    rem_protein = macros['protein_g'] - today['protein_g']
    rem_carbs   = macros['carbs_g']   - today['carbs_g']
    rem_fat     = macros['fat_g']     - today['fat_g']
    net_cal     = today['calories_consumed'] - today['calories_burned']

    hist_lines = []
    for i in range(1, 7):
        d  = (date.today() - timedelta(days=i)).isoformat()
        df = daily_file(d)
        if df.exists():
            ds = load_json(df)
            wt = ', wt: {}lb'.format(ds['weight_lb']) if ds.get('weight_lb') else ''
            hist_lines.append('  {}: {} kcal | P{}g C{}g F{}g | burned {}{}'.format(
                d, ds.get('calories_consumed',0), ds.get('protein_g',0),
                ds.get('carbs_g',0), ds.get('fat_g',0), ds.get('calories_burned',0), wt))
    hist_str = chr(10).join(hist_lines) if hist_lines else '  (no history yet)'
    wt_log = profile.get('weight_log', [])[-14:]
    wt_str = ', '.join('{}: {}lb'.format(w['date'], w['weight_lb']) for w in wt_log) or 'none recorded'
    hyp_hist = profile.get('calorie_hypothesis_history', [])[-3:]
    hyp_str = chr(10).join('  {}: {}->{}kcal ({})'.format(
        h['date'],h['from'],h['to'],h['reason']) for h in hyp_hist) or '  (no adjustments yet)'
    food_str = chr(10).join('  - {}: {} kcal | P{}g C{}g F{}g'.format(
        e['name'],e['calories'],e['protein_g'],e['carbs_g'],e['fat_g']
    ) for e in today['food_log']) or '  (nothing logged yet)'
    ex_str = chr(10).join('  - {}: ~{} kcal burned'.format(
        e['activity'],e['calories_burned']) for e in today['exercise_log']) or '  (none)'
    meal_str = chr(10).join('  [{}]: {} kcal | P{}g C{}g F{}g'.format(
        k, m['calories'], m['protein_g'], m['carbs_g'], m['fat_g']
    ) for k, m in meals_db['meals'].items()) or '  (none saved yet)'

    return chr(10).join([
        '=== NUTRITION COACHING CONTEXT ===',
        'Calorie target (hypothesis): {} kcal'.format(cal_target),
        'Rationale: {} | Updated: {}'.format(
            profile.get('calorie_hypothesis_rationale','initial estimate'),
            profile.get('calorie_hypothesis_updated','')),
        'Hypothesis history:',
        hyp_str,
        'Macros: Protein>={}g | Carbs~{}g | Fat~{}g'.format(
            macros['protein_g'],macros['carbs_g'],macros['fat_g']),
        'Priority: 1)calories 2)protein 3)carbs 4)fat. Weekly consistency beats daily precision.',
        '',
        'TODAY ({}):'.format(today_str()),
        '  Consumed: {} kcal | P{}g C{}g F{}g'.format(
            today['calories_consumed'],today['protein_g'],today['carbs_g'],today['fat_g']),
        '  Burned: {} kcal | Net: {} kcal'.format(today['calories_burned'], net_cal),
        '  Remaining: {} kcal | P{}g | C{}g | F{}g'.format(
            rem_cal,rem_protein,rem_carbs,rem_fat),
        '',
        'Food logged:',
        food_str,
        'Exercise:',
        ex_str,
        '',
        'Last 6 days:',
        hist_str,
        'Weight trend: ' + wt_str,
        '',
        'Saved meals:',
        meal_str,
        '',
        'Preferred foods:',
        '  Proteins: chicken breast, rotisserie chicken, lean ground beef, turkey breast, eggs, Skyr, Greek yogurt, vegan protein powder',
        '  Carbs: jasmine rice, potatoes, oats, bananas, apples, mandarins, pineapple, fruit, vegetables',
        '  Fats: eggs, rotisserie chicken skin, lean ground beef, avocado (occasional), nuts (occasional)',
        '',
        'Coaching rules:',
        '  - Estimate confidently. Only ask if uncertainty is material to the estimate.',
        '  - After every food log: show totals, remaining, on-track status, biggest gap, one recommendation.',
        '  - Restaurant meals: estimate from published data or comparable meals, state assumptions.',
        '  - If over calories: recover through normal eating next day, not restriction.',
        '  - Calorie target is a hypothesis — refine weekly based on weight trend + gym performance.',
        '  - Communication: concise, practical, no praise, no judgment.',
        '=== END NUTRITION CONTEXT ===',
    ])


def get_weekly_review():
    profile = load_profile()
    rows = []
    for i in range(7):
        d  = (date.today() - timedelta(days=i)).isoformat()
        df = daily_file(d)
        if df.exists():
            rows.append(load_json(df))
    if not rows:
        return None
    avg_cal     = sum(r.get('calories_consumed', 0) for r in rows) / len(rows)
    avg_protein = sum(r.get('protein_g', 0) for r in rows) / len(rows)
    avg_carbs   = sum(r.get('carbs_g', 0) for r in rows) / len(rows)
    avg_fat     = sum(r.get('fat_g', 0) for r in rows) / len(rows)
    avg_burned  = sum(r.get('calories_burned', 0) for r in rows) / len(rows)
    weights     = [r['weight_lb'] for r in rows if r.get('weight_lb')]
    cal_target  = profile['calorie_hypothesis']
    return {
        'days_tracked':  len(rows),
        'avg_calories':  round(avg_cal),
        'avg_protein':   round(avg_protein),
        'avg_carbs':     round(avg_carbs),
        'avg_fat':       round(avg_fat),
        'avg_burned':    round(avg_burned),
        'avg_deficit':   round(cal_target - avg_cal),
        'weight_start':  weights[-1] if len(weights) > 1 else None,
        'weight_end':    weights[0]  if len(weights) > 1 else None,
        'weight_change': round(weights[0] - weights[-1], 1) if len(weights) > 1 else None,
        'cal_target':    cal_target,
        'macro_targets': profile['macro_targets'],
    }


if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'context'
    if cmd == 'context':      print(get_context_block())
    elif cmd == 'summary':    import json; print(json.dumps(get_summary(), indent=2))
    elif cmd == 'weekly':     import json; print(json.dumps(get_weekly_review(), indent=2))
    elif cmd == 'log_food':   import json; print(json.dumps(log_food(json.loads(sys.argv[2])), indent=2))
    elif cmd == 'log_exercise': import json; print(json.dumps(log_exercise(json.loads(sys.argv[2])), indent=2))
    elif cmd == 'log_weight': print(json.dumps(log_weight(float(sys.argv[2])), indent=2))
    elif cmd == 'save_meal':  import json; print(json.dumps(save_meal(json.loads(sys.argv[2])), indent=2))
    elif cmd == 'adjust':     print(json.dumps(adjust_hypothesis(int(sys.argv[2]), sys.argv[3]), indent=2))
    else: print('Unknown command:', cmd)
