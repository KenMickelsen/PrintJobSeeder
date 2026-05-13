"""
app_erp.py — Apex Industrial ERP Demo
A fake manufacturing ERP system that wraps the Vasion print engine.
Runs on port 5758.
"""

import os
import sys
import uuid
import random
import tempfile
import threading
import webbrowser
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response

from print_utils import (
    log, CLOUD_REGIONS, INDUSTRIES,
    load_settings, save_settings,
    obfuscate_key, deobfuscate_key, build_onprem_url, get_cloud_base_url,
    fetch_printers_from_api, generate_pdf, generate_random_delay,
    send_single_job, send_single_job_from_buffer, INDUSTRY_PRESETS, USERNAME_PRESETS
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# ============================================================
# Fake data generators
# ============================================================

OPERATORS = [
    'James Miller', 'Linda Davis', 'William Garcia', 'Patricia Rodriguez',
    'Richard Martinez', 'Barbara Anderson', 'Joseph Taylor', 'Susan Thomas',
    'Charles Hernandez', 'Margaret Moore', 'Thomas Jackson', 'Dorothy Martin',
    'Christopher Lee', 'Nancy White', 'Daniel Harris', 'Karen Clark',
    'Mark Lewis', 'Betty Walker', 'Steven Hall', 'Helen Allen'
]

VENDORS = [
    'Acme Steel Supply', 'Precision Parts Inc.', 'National Metal Works',
    'Summit Components', 'Allied Industrial', 'Northwest Fasteners',
    'Delta Alloys', 'Core Materials Group', 'Ridge Line Supply',
    'Cornerstone Metals'
]

CUSTOMERS = [
    ('Harrington Aerospace', 'Atlanta, GA', 'Robert Harrington'),
    ('BlueStar Defense', 'Huntsville, AL', 'Sandra Kowalski'),
    ('Titan Automotive', 'Detroit, MI', 'Marcus Webb'),
    ('Keystone Rail Systems', 'Pittsburgh, PA', 'Jennifer Okafor'),
    ('Summit Energy Solutions', 'Houston, TX', 'David Nguyen'),
    ('Pinnacle Medical Devices', 'Minneapolis, MN', 'Catherine Reyes'),
    ('Ironclad Mining', 'Denver, CO', 'Thomas Petrov'),
    ('Pacific Shipbuilding', 'Seattle, WA', 'Laura Chen'),
    ('Atlas Heavy Equipment', 'Columbus, OH', 'Michael Dubois'),
    ('Vanguard Electronics', 'Austin, TX', 'Priya Sharma'),
    ('CrestLine Agriculture', 'Des Moines, IA', 'Gary Thompson'),
    ('Harbor Defense Corp', 'Norfolk, VA', 'Elizabeth Moss'),
    ('MidWest Pump & Valve', 'Kansas City, MO', 'John Ramirez'),
    ('Continental Structures', 'Phoenix, AZ', 'Maria Vasquez'),
    ('NorthStar Fabrication', 'Minneapolis, MN', 'Andrew Park'),
]

PART_FAMILIES = [
    ('Bracket', 'BKT'), ('Housing', 'HSG'), ('Shaft', 'SFT'), ('Gear', 'GER'),
    ('Flange', 'FLG'), ('Bushing', 'BSH'), ('Coupling', 'CPL'), ('Valve', 'VLV'),
    ('Manifold', 'MNF'), ('Plate', 'PLT'), ('Cover', 'CVR'), ('Clamp', 'CLM'),
]

WO_STATUSES = ['Open', 'In Progress', 'Complete', 'On Hold']
PO_STATUSES = ['Pending', 'Approved', 'Received', 'Invoiced']
WO_STATUS_WEIGHTS = [0.25, 0.40, 0.25, 0.10]
PO_STATUS_WEIGHTS = [0.15, 0.30, 0.35, 0.20]


def _rand_part_number():
    family, prefix = random.choice(PART_FAMILIES)
    num = random.randint(10000, 99999)
    return f'{prefix}-{num}', family


def _rand_date_offset(min_offset, max_offset):
    """Return a date string offset from today by a random number of days.
    min_offset/max_offset can be negative (past) or positive (future).
    """
    base = datetime.now()
    offset = random.randint(min_offset, max_offset)
    return (base + timedelta(days=offset)).strftime('%Y-%m-%d')


def generate_work_orders(n=30):
    orders = []
    for i in range(n):
        pn, fam = _rand_part_number()
        wo_id = f'WO-{random.randint(70000, 99999)}'
        status = random.choices(WO_STATUSES, weights=WO_STATUS_WEIGHTS)[0]
        qty = random.choice([10, 25, 50, 100, 200, 500])
        orders.append({
            'id': wo_id,
            'part_number': pn,
            'description': f'{fam} Assembly',
            'quantity': qty,
            'operator': random.choice(OPERATORS),
            'customer': random.choice(CUSTOMERS)[0],
            'status': status,
            'due_date': _rand_date_offset(-10, 45),
            'created_date': _rand_date_offset(-60, -1),
        })
    return sorted(orders, key=lambda x: x['id'])


def generate_purchase_orders(n=20):
    orders = []
    for i in range(n):
        po_id = f'PO-{random.randint(20000, 49999)}'
        status = random.choices(PO_STATUSES, weights=PO_STATUS_WEIGHTS)[0]
        line_count = random.randint(1, 6)
        amount = round(random.uniform(500, 45000), 2)
        orders.append({
            'id': po_id,
            'vendor': random.choice(VENDORS),
            'line_items': line_count,
            'amount': amount,
            'status': status,
            'order_date': _rand_date_offset(-45, -1),
            'expected_date': _rand_date_offset(0, 30),
            'buyer': random.choice(OPERATORS),
        })
    return sorted(orders, key=lambda x: x['id'])


def generate_dashboard_data(work_orders, purchase_orders):
    total_wo = len(work_orders)
    open_po = sum(1 for p in purchase_orders if p['status'] in ['Pending', 'Approved'])
    on_time = round(random.uniform(88, 97), 1)
    jobs_today = random.randint(18, 75)

    # 30-day bar chart data (orders opened per day)
    labels = []
    wo_counts = []
    print_counts = []
    base = datetime.now()
    for d in range(29, -1, -1):
        day = base - timedelta(days=d)
        labels.append(day.strftime('%b %d'))
        wo_counts.append(random.randint(0, 4))
        print_counts.append(random.randint(2, 12))

    recent_activity = []
    combined = (
        [('Work Order', wo['id'], wo['status'], wo['operator']) for wo in work_orders[:3]] +
        [('Purchase Order', po['id'], po['status'], po['buyer']) for po in purchase_orders[:2]]
    )
    random.shuffle(combined)
    for kind, ref, status, user in combined[:5]:
        recent_activity.append({
            'type': kind,
            'ref': ref,
            'status': status,
            'user': user,
            'time': f'{random.randint(1, 59)} min ago',
        })

    return {
        'kpis': {
            'total_work_orders': total_wo,
            'open_purchase_orders': open_po,
            'on_time_delivery': on_time,
            'jobs_today': jobs_today,
        },
        'chart_labels': labels,
        'wo_counts': wo_counts,
        'print_counts': print_counts,
        'recent_activity': recent_activity,
    }


# Generate fake data at startup (module level — stable per process)
random.seed(42)
WORK_ORDERS = generate_work_orders(30)
PURCHASE_ORDERS = generate_purchase_orders(20)
DASHBOARD = generate_dashboard_data(WORK_ORDERS, PURCHASE_ORDERS)
random.seed()  # Restore true randomness after seeding

# SSE session store
job_sessions = {}

# ============================================================
# Helper: build print URL from settings
# ============================================================

def _get_print_url_and_token():
    """Return (url, bearer_token) from settings, or (None, None)."""
    settings = load_settings()
    dest = settings.get('destination', 'cloud_link')

    if dest == 'on_premise':
        url = build_onprem_url(settings)
        token = settings['on_premise'].get('bearer_token', '')
        if token and not token.startswith('Bearer '):
            token = f'Bearer {token}'
        return url, token
    else:
        region = settings['cloud_link'].get('region', '')
        raw_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
        if not region or not raw_key:
            return None, None
        base = get_cloud_base_url(region)
        url = f'{base}/v1/print'
        return url, f'Bearer {raw_key}'


# ============================================================
# Page routes
# ============================================================

@app.route('/')
def dashboard():
    return render_template('erp/dashboard.html',
                           page='dashboard',
                           dashboard=DASHBOARD)


@app.route('/orders')
def orders():
    tab = request.args.get('tab', 'work_orders')
    return render_template('erp/orders.html',
                           page='orders',
                           tab=tab,
                           work_orders=WORK_ORDERS,
                           purchase_orders=PURCHASE_ORDERS)


@app.route('/customers')
def customers():
    return render_template('erp/customers.html',
                           page='customers',
                           customers=CUSTOMERS)


@app.route('/print-queue')
def print_queue():
    settings = load_settings()
    return render_template('erp/print_queue.html',
                           page='print_queue',
                           industries=INDUSTRIES,
                           settings=settings,
                           cloud_regions=list(CLOUD_REGIONS.keys()))


@app.route('/admin')
def admin():
    settings = load_settings()
    display = {
        'destination': settings.get('destination', 'cloud_link'),
        'cloud_link': {
            'region': settings['cloud_link'].get('region', ''),
            'has_api_key': bool(settings['cloud_link'].get('api_key', ''))
        },
        'on_premise': {
            'server': settings['on_premise'].get('server', ''),
            'protocol': settings['on_premise'].get('protocol', 'https'),
            'port': settings['on_premise'].get('port', '443'),
            'has_token': bool(settings['on_premise'].get('bearer_token', ''))
        },
        'industry_paths': settings.get('industry_paths', {})
    }
    return render_template('erp/admin.html',
                           page='admin',
                           settings=display,
                           cloud_regions=list(CLOUD_REGIONS.keys()),
                           industries=INDUSTRIES)


# ============================================================
# API: Settings
# ============================================================

@app.route('/api/erp/settings', methods=['GET', 'POST'])
def erp_settings():
    if request.method == 'GET':
        settings = load_settings()
        safe = {
            'cloud_link': {
                'region': settings['cloud_link'].get('region', ''),
                'has_api_key': bool(settings['cloud_link'].get('api_key', ''))
            },
            'on_premise': {
                'server': settings['on_premise'].get('server', ''),
                'protocol': settings['on_premise'].get('protocol', 'https'),
                'port': settings['on_premise'].get('port', '443'),
                'has_token': bool(settings['on_premise'].get('bearer_token', ''))
            },
            'industry_paths': settings.get('industry_paths', {})
        }
        return jsonify(safe)

    data = request.get_json(force=True)
    settings = load_settings()

    if 'destination' in data:
        settings['destination'] = data['destination']

    if 'cloud_link' in data:
        cl = data['cloud_link']
        if 'region' in cl:
            settings['cloud_link']['region'] = cl['region']
        if 'api_key' in cl and cl['api_key']:
            settings['cloud_link']['api_key'] = obfuscate_key(cl['api_key'])

    if 'on_premise' in data:
        op = data['on_premise']
        for field in ['server', 'protocol', 'port']:
            if field in op:
                settings['on_premise'][field] = op[field]
        if 'bearer_token' in op and op['bearer_token']:
            settings['on_premise']['bearer_token'] = op['bearer_token']

    if 'industry_paths' in data:
        for ind, path in data['industry_paths'].items():
            settings['industry_paths'][ind] = path

    if save_settings(settings):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Could not save settings'}), 500


# ============================================================
# API: Printers
# ============================================================

@app.route('/api/erp/printers')
def erp_printers():
    industry = request.args.get('industry', 'manufacturing')
    settings = load_settings()

    region = settings['cloud_link'].get('region', '')
    raw_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
    path_filter = settings.get('industry_paths', {}).get(industry, f'*{industry.title()}*')

    if not region or not raw_key:
        return jsonify({'success': False, 'error': 'Cloud Link not configured', 'printers': []})

    base_url = get_cloud_base_url(region)
    printers, error = fetch_printers_from_api(raw_key, base_url, path_filter)

    if error:
        return jsonify({'success': False, 'error': error, 'printers': []})
    return jsonify({'success': True, 'printers': printers})


# ============================================================
# API: Print single order
# ============================================================

@app.route('/api/erp/print-order', methods=['POST'])
def erp_print_order():
    """Print a single work order or PO as a manufacturing PDF."""
    data = request.get_json(force=True)
    order_id = data.get('order_id', 'WO-00000')
    printer = data.get('printer', '')
    username = data.get('username', 'erp-system@apexindustrial.com')

    if not printer:
        return jsonify({'success': False, 'error': 'No printer specified'}), 400

    url, token = _get_print_url_and_token()
    if not url:
        return jsonify({'success': False, 'error': 'Print destination not configured'}), 400

    filename = f'{order_id}_Print.pdf'
    buffer = generate_pdf(filename, 'manufacturing', min_pages=1, max_pages=3)
    result = send_single_job_from_buffer(url, token, buffer, filename, username, printer, 1, 'manufacturing')

    return jsonify({
        'success': result['success'],
        'order_id': order_id,
        'status_code': result['status_code'],
        'message': 'Print job sent successfully' if result['success'] else result['response']
    })


# ============================================================
# API: Start / Stop bulk print run (SSE)
# ============================================================

@app.route('/api/erp/start-print-run', methods=['POST'])
def erp_start_print_run():
    """Start a bulk manufacturing print run. Returns session_id for SSE stream."""
    destination = request.form.get('destination', 'cloud_link')
    industry = request.form.get('industry', 'manufacturing')
    num_jobs = int(request.form.get('num_jobs', 10))
    timing_mode = request.form.get('timing_mode', 'random')
    fixed_delay = float(request.form.get('fixed_delay', 1.0))
    min_delay = float(request.form.get('min_delay', 0.5))
    max_delay = float(request.form.get('max_delay', 30.0))
    printer = request.form.get('printer', '')

    if not printer:
        return jsonify({'success': False, 'error': 'No printer selected'}), 400

    settings = load_settings()

    if destination == 'on_premise':
        url = build_onprem_url(settings)
        raw_token = settings['on_premise'].get('bearer_token', '')
        bearer_token = f'Bearer {raw_token}' if raw_token and not raw_token.startswith('Bearer ') else raw_token
    else:
        region = settings['cloud_link'].get('region', '')
        raw_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
        if not region or not raw_key:
            return jsonify({'success': False, 'error': 'Cloud Link not configured'}), 400
        base = get_cloud_base_url(region)
        url = f'{base}/v1/print'
        bearer_token = f'Bearer {raw_key}'

    if not url:
        return jsonify({'success': False, 'error': 'Print destination not configured'}), 400

    session_id = str(uuid.uuid4())
    job_sessions[session_id] = {
        'status': 'running',
        'results': [],
        'stop_flag': False,
        'total': num_jobs,
        'completed': 0,
        'success_count': 0,
    }

    thread = threading.Thread(
        target=_run_print_jobs,
        args=(session_id, url, bearer_token, industry, num_jobs,
              timing_mode, fixed_delay, min_delay, max_delay, printer),
        daemon=True
    )
    thread.start()
    log(f"ERP print run started: session={session_id}, jobs={num_jobs}, industry={industry}")
    return jsonify({'success': True, 'session_id': session_id})


def _run_print_jobs(session_id, url, bearer_token, industry, num_jobs,
                    timing_mode, fixed_delay, min_delay, max_delay, printer):
    """Worker thread: sends print jobs and updates session state."""
    import time
    session = job_sessions[session_id]
    filenames = INDUSTRY_PRESETS.get(industry, INDUSTRY_PRESETS['manufacturing'])
    usernames = USERNAME_PRESETS.get(industry, USERNAME_PRESETS['manufacturing'])

    for i in range(1, num_jobs + 1):
        if session['stop_flag']:
            break

        filename = random.choice(filenames)
        username = random.choice(usernames)

        buffer = generate_pdf(filename, industry, min_pages=1, max_pages=8)
        result = send_single_job_from_buffer(
            url, bearer_token, buffer, filename, username, printer, i, industry
        )

        session['results'].append(result)
        session['completed'] = i
        if result['success']:
            session['success_count'] += 1

        if i < num_jobs and not session['stop_flag']:
            delay = generate_random_delay(timing_mode, fixed_delay, min_delay, max_delay)
            time.sleep(delay)

    session['status'] = 'stopped' if session['stop_flag'] else 'complete'
    log(f"ERP print run {session_id}: {session['success_count']}/{session['completed']} succeeded")


@app.route('/api/erp/stream-jobs/<session_id>')
def erp_stream_jobs(session_id):
    """SSE endpoint: streams job results to the browser."""
    import time
    import json as _json

    def generate():
        last_sent = 0
        while True:
            session = job_sessions.get(session_id)
            if not session:
                yield 'data: {"error": "Session not found"}\n\n'
                break

            results = session['results']
            for result in results[last_sent:]:
                yield f'data: {_json.dumps(result)}\n\n'
                last_sent += 1

            if session['status'] in ('complete', 'stopped') and last_sent >= len(results):
                summary = {
                    'type': 'complete',
                    'total': session['completed'],
                    'success': session['success_count'],
                    'status': session['status']
                }
                yield f'data: {_json.dumps(summary)}\n\n'
                break

            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/erp/stop-jobs/<session_id>', methods=['POST'])
def erp_stop_jobs(session_id):
    session = job_sessions.get(session_id)
    if session:
        session['stop_flag'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/api/erp/session-status/<session_id>')
def erp_session_status(session_id):
    session = job_sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({
        'status': session['status'],
        'completed': session['completed'],
        'total': session['total'],
        'success_count': session['success_count'],
    })


# ============================================================
# API: Presets (for print queue panel)
# ============================================================

@app.route('/api/erp/presets')
def erp_presets():
    from print_utils import INDUSTRY_PRESETS, USERNAME_PRESETS, INDUSTRIES, INDUSTRY_DISPLAY_NAMES
    return jsonify({
        'filenames': INDUSTRY_PRESETS,
        'usernames': USERNAME_PRESETS,
        'industries': INDUSTRIES,
        'industry_names': INDUSTRY_DISPLAY_NAMES
    })


# ============================================================
# Run
# ============================================================

if __name__ == '__main__':
    log("Apex Industrial ERP Demo starting on port 5758")
    import threading as _t
    _t.Timer(1.5, lambda: webbrowser.open('http://localhost:5758')).start()
    app.run(debug=False, host='localhost', port=5758)
