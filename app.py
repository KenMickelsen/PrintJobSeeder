"""
Print Job Seeder - Flask Application
Sends multiple print jobs to Vasion Output API with industry-specific metadata
"""

import os
import sys
import json
import random
import tempfile
import shutil
import threading
import time
import uuid
import logging
import webbrowser
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

from print_utils import (
    log, LOG_FILE, SETTINGS_FILE,
    CLOUD_REGIONS, INDUSTRIES, INDUSTRY_DISPLAY_NAMES,
    INDUSTRY_PRESETS, USERNAME_PRESETS, INDUSTRY_CONTENT, LOREM_IPSUM,
    get_default_settings, load_settings, save_settings,
    obfuscate_key, deobfuscate_key, build_onprem_url, get_cloud_base_url,
    fetch_printers_from_api, generate_pdf, generate_random_delay,
    send_single_job, send_single_job_from_buffer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size (multiple industry uploads)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Test log at startup
log("PrintJobSeeder starting up - logging initialized")

# Store active job sessions for streaming results
job_sessions = {}

# Available industries
job_results = []


@app.route('/')
def index():
    """Render the main web interface"""
    settings = load_settings()
    # Don't expose actual API keys to frontend, just whether they're set
    settings_status = {
        'cloud_link': {
            'region': settings['cloud_link'].get('region', ''),
            'has_api_key': bool(settings['cloud_link'].get('api_key', ''))
        },
        'on_premise': {
            'server': settings['on_premise'].get('server', ''),
            'protocol': settings['on_premise'].get('protocol', 'https'),
            'port': settings['on_premise'].get('port', '443'),
            'has_bearer_token': bool(settings['on_premise'].get('bearer_token', ''))
        }
    }
    return render_template('index.html', 
                          presets=INDUSTRY_PRESETS, 
                          username_presets=USERNAME_PRESETS,
                          industries=INDUSTRIES,
                          industry_names=INDUSTRY_DISPLAY_NAMES,
                          cloud_regions=CLOUD_REGIONS,
                          settings_status=settings_status)


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings (with keys masked)"""
    settings = load_settings()
    defaults = get_default_settings()
    # Return masked version
    return jsonify({
        'cloud_link': {
            'region': settings['cloud_link'].get('region', ''),
            'api_key_set': bool(settings['cloud_link'].get('api_key', ''))
        },
        'on_premise': {
            'server': settings['on_premise'].get('server', ''),
            'protocol': settings['on_premise'].get('protocol', 'https'),
            'port': settings['on_premise'].get('port', '443'),
            'bearer_token_set': bool(settings['on_premise'].get('bearer_token', ''))
        },
        'industry_paths': settings.get('industry_paths', defaults['industry_paths']),
        'cloud_regions': CLOUD_REGIONS
    })


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.get_json()
        current_settings = load_settings()
        
        # Update cloud link settings
        if 'cloud_link' in data:
            cl = data['cloud_link']
            if 'region' in cl:
                current_settings['cloud_link']['region'] = cl['region']
            if 'api_key' in cl and cl['api_key'] is not None:
                # Only update if a new key is provided (not empty string means clear, None means keep existing)
                current_settings['cloud_link']['api_key'] = obfuscate_key(cl['api_key'])
        
        # Update on-premise settings
        if 'on_premise' in data:
            op = data['on_premise']
            if 'server' in op:
                current_settings['on_premise']['server'] = op['server']
            if 'protocol' in op:
                current_settings['on_premise']['protocol'] = op['protocol']
            if 'port' in op:
                current_settings['on_premise']['port'] = op['port']
            if 'bearer_token' in op and op['bearer_token'] is not None:
                current_settings['on_premise']['bearer_token'] = obfuscate_key(op['bearer_token'])
        
        # Update industry paths
        if 'industry_paths' in data:
            if 'industry_paths' not in current_settings:
                current_settings['industry_paths'] = {}
            for industry, path in data['industry_paths'].items():
                current_settings['industry_paths'][industry] = path
        
        if save_settings(current_settings):
            return jsonify({'success': True, 'message': 'Settings saved'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/validate', methods=['GET'])
def validate_settings():
    """Validate current settings for each destination type"""
    settings = load_settings()
    
    cloud_valid = bool(
        settings['cloud_link'].get('region') and 
        settings['cloud_link'].get('api_key')
    )
    cloud_region = settings['cloud_link'].get('region', '')
    cloud_url = CLOUD_REGIONS.get(cloud_region, {}).get('url', '') if cloud_region else ''
    
    onprem_valid = bool(settings['on_premise'].get('server'))
    onprem_url = build_onprem_url(settings) if onprem_valid else ''
    onprem_has_token = bool(settings['on_premise'].get('bearer_token'))
    
    return jsonify({
        'cloud_link': {
            'valid': cloud_valid,
            'region': cloud_region,
            'url': cloud_url,
            'missing': [] if cloud_valid else (
                ['region'] if not settings['cloud_link'].get('region') else []
            ) + (
                ['api_key'] if not settings['cloud_link'].get('api_key') else []
            )
        },
        'on_premise': {
            'valid': onprem_valid,
            'url': onprem_url,
            'has_token': onprem_has_token,
            'missing': ['server'] if not onprem_valid else []
        }
    })


@app.route('/api/settings/get-auth', methods=['POST'])
def get_auth_for_destination():
    """Get the authentication token for a specific destination type (internal use only)"""
    try:
        data = request.get_json()
        dest_type = data.get('type')
        settings = load_settings()
        
        if dest_type == 'cloud':
            api_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
            region = settings['cloud_link'].get('region', '')
            url = CLOUD_REGIONS.get(region, {}).get('url', '')
            return jsonify({
                'success': True,
                'url': url,
                'token': api_key
            })
        elif dest_type == 'onprem':
            token = deobfuscate_key(settings['on_premise'].get('bearer_token', ''))
            url = build_onprem_url(settings)
            return jsonify({
                'success': True,
                'url': url,
                'token': token
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid destination type'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/printers/<industry>', methods=['GET'])
def get_printers_for_industry(industry):
    """Fetch printers from Vasion API for a specific industry folder"""
    try:
        settings = load_settings()
        
        # Check if cloud link is configured
        region = settings['cloud_link'].get('region', '')
        api_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
        
        if not region or not api_key:
            return jsonify({
                'success': False,
                'error': 'API Cloud Link must be configured to fetch printers. Please configure it in Settings.'
            }), 400
        
        # Get the path filter for this industry
        industry_paths = settings.get('industry_paths', get_default_settings()['industry_paths'])
        path_filter = industry_paths.get(industry, f'*{industry.capitalize()}*')
        
        if not path_filter:
            return jsonify({
                'success': False,
                'error': f'No folder path configured for {industry}'
            }), 400
        
        # Get the base URL for the cloud region
        base_url = get_cloud_base_url(region)
        if not base_url:
            return jsonify({
                'success': False,
                'error': f'Invalid cloud region: {region}'
            }), 400
        
        # Fetch printers
        printers, error = fetch_printers_from_api(api_key, base_url, path_filter)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        return jsonify({
            'success': True,
            'printers': printers,
            'count': len(printers),
            'path_filter': path_filter
        })
        
    except Exception as e:
        log(f"Error fetching printers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/printers/all', methods=['GET'])
def get_all_printers():
    """Fetch printers for every configured industry vertical, grouped by industry"""
    try:
        settings = load_settings()

        region = settings['cloud_link'].get('region', '')
        api_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))

        if not region or not api_key:
            return jsonify({
                'success': False,
                'error': 'API Cloud Link must be configured to fetch printers. Please configure it in Settings.'
            }), 400

        base_url = get_cloud_base_url(region)
        if not base_url:
            return jsonify({'success': False, 'error': f'Invalid cloud region: {region}'}), 400

        industry_paths = settings.get('industry_paths', get_default_settings()['industry_paths'])

        grouped = {}
        errors = []

        for industry in INDUSTRIES:
            path_filter = industry_paths.get(industry, f'*{industry.capitalize()}*')
            if not path_filter:
                continue
            printers, error = fetch_printers_from_api(api_key, base_url, path_filter)
            if error:
                errors.append(f'{industry}: {error}')
            else:
                grouped[industry] = {
                    'display_name': INDUSTRY_DISPLAY_NAMES[industry],
                    'printers': printers
                }

        return jsonify({
            'success': True,
            'grouped': grouped,
            'errors': errors
        })

    except Exception as e:
        log(f"Error fetching all printers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/send-single-job', methods=['POST'])
def send_single_job_endpoint():
    """Send a single print job immediately and return the result"""
    try:
        # Support both JSON (generate) and multipart/form-data (with optional file upload)
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = request.get_json()
            url = data.get('url', '').strip()
            bearer_token = data.get('bearer_token', '').strip()
            printer = data.get('printer', '').strip()
            industry = data.get('industry', 'healthcare')
            pdf_source = 'generate'
            custom_filename = ''
            uploaded_file = None
        else:
            url = request.form.get('url', '').strip()
            bearer_token = request.form.get('bearer_token', '').strip()
            printer = request.form.get('printer', '').strip()
            industry = request.form.get('industry', 'healthcare')
            pdf_source = request.form.get('pdf_source', 'generate')
            custom_filename = request.form.get('custom_filename', '').strip()
            uploaded_file = request.files.get('file')

        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        if not printer:
            return jsonify({'success': False, 'error': 'Printer name is required'}), 400
        if industry not in INDUSTRIES:
            industry = 'healthcare'

        username = random.choice(USERNAME_PRESETS.get(industry, USERNAME_PRESETS['healthcare']))

        if pdf_source == 'upload' and uploaded_file and uploaded_file.filename:
            original_filename = secure_filename(uploaded_file.filename)
            filename = custom_filename if custom_filename else original_filename
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'

            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'single_{uuid.uuid4()}_{original_filename}')
            uploaded_file.save(temp_path)

            try:
                result = send_single_job(
                    url=url,
                    bearer_token=bearer_token,
                    file_path=temp_path,
                    filename=filename,
                    username=username,
                    printer=printer,
                    job_number=1,
                    industry=industry
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            # Generate a PDF
            filename = random.choice(INDUSTRY_PRESETS.get(industry, INDUSTRY_PRESETS['healthcare']))
            pdf_buffer = generate_pdf(filename, industry, 1, 15)

            result = send_single_job_from_buffer(
                url=url,
                bearer_token=bearer_token,
                file_buffer=pdf_buffer,
                filename=filename,
                username=username,
                printer=printer,
                job_number=1,
                industry=industry
            )

        return jsonify({
            'success': result['success'],
            'filename': result['filename'],
            'username': result['username'],
            'printer': result['printer'],
            'industry': industry,
            'status_code': result['status_code'],
            'response': result['response']
        })

    except Exception as e:
        log(f"Error in send-single-job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Return industry presets as JSON"""
    return jsonify({
        'filenames': INDUSTRY_PRESETS, 
        'usernames': USERNAME_PRESETS,
        'industries': INDUSTRIES,
        'industry_names': INDUSTRY_DISPLAY_NAMES
    })


@app.route('/api/start-jobs', methods=['POST'])
def start_jobs():
    """Initialize a job session and return session ID for streaming"""
    global job_sessions
    
    log("=== /api/start-jobs called ===")
    
    try:
        # Get global settings
        url = request.form.get('url', '').strip()
        bearer_token = request.form.get('bearer_token', '').strip()
        log(f"URL: {url}")
        log(f"Bearer token present: {bool(bearer_token)}")
        
        # Timing settings
        timing_mode = request.form.get('timing_mode', 'fixed')
        fixed_delay = float(request.form.get('fixed_delay', 1.0))
        min_delay = float(request.form.get('min_delay', 0.5))
        max_delay = float(request.form.get('max_delay', 120.0))
        
        # Get active industries from JSON
        industry_configs_json = request.form.get('industry_configs', '{}')
        industry_configs = json.loads(industry_configs_json)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        if not industry_configs:
            return jsonify({'success': False, 'error': 'At least one industry must be configured'}), 400
        
        # Build job queue from all industries
        all_jobs = []
        temp_files = {}  # Store uploaded files per industry
        
        for industry, config in industry_configs.items():
            num_jobs = int(config.get('num_jobs', 0))
            if num_jobs <= 0:
                continue
                
            usernames = [u.strip() for u in config.get('usernames', '').split(',') if u.strip()]
            printers = [p.strip() for p in config.get('printers', '').split(',') if p.strip()]
            filenames = [f.strip() for f in config.get('filenames', '').split(',') if f.strip()]
            pdf_source = config.get('pdf_source', 'generate')
            min_pages = int(config.get('min_pages', 1))
            max_pages = int(config.get('max_pages', 15))
            
            if not usernames:
                return jsonify({'success': False, 'error': f'{industry}: At least one username is required'}), 400
            if not printers:
                return jsonify({'success': False, 'error': f'{industry}: At least one printer is required'}), 400
            if not filenames:
                return jsonify({'success': False, 'error': f'{industry}: At least one filename is required'}), 400
            
            # Handle file upload for this industry
            temp_path = None
            if pdf_source == 'upload':
                file_key = f'file_{industry}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        original_filename = secure_filename(file.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{industry}_{original_filename}')
                        file.save(temp_path)
                        temp_files[industry] = temp_path
                
                if not temp_path:
                    return jsonify({'success': False, 'error': f'{industry}: No file uploaded'}), 400
            
            # Create jobs for this industry
            for i in range(num_jobs):
                job = {
                    'industry': industry,
                    'username': usernames[i % len(usernames)],
                    'printer': printers[i % len(printers)],
                    'filename': filenames[i % len(filenames)],
                    'pdf_source': pdf_source,
                    'min_pages': min_pages,
                    'max_pages': max_pages,
                    'temp_path': temp_path
                }
                # Ensure filename ends with .pdf
                if not job['filename'].lower().endswith('.pdf'):
                    job['filename'] += '.pdf'
                all_jobs.append(job)
        
        if not all_jobs:
            return jsonify({'success': False, 'error': 'No jobs to send'}), 400
        
        # Shuffle jobs to interleave industries naturally
        random.shuffle(all_jobs)
        
        # Create session
        session_id = str(uuid.uuid4())
        job_sessions[session_id] = {
            'jobs': all_jobs,
            'results': [],
            'status': 'ready',
            'total': len(all_jobs),
            'completed': 0,
            'url': url,
            'bearer_token': bearer_token,
            'timing_mode': timing_mode,
            'fixed_delay': fixed_delay,
            'min_delay': min_delay,
            'max_delay': max_delay,
            'temp_files': temp_files,
            'stop_requested': False,
            'created_at': time.time()
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_jobs': len(all_jobs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stop-jobs/<session_id>', methods=['POST'])
def stop_jobs(session_id):
    """Stop a running job session"""
    global job_sessions
    
    if session_id not in job_sessions:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    session = job_sessions[session_id]
    session['stop_requested'] = True
    session['status'] = 'stopping'
    
    return jsonify({
        'success': True,
        'message': 'Stop requested',
        'completed': session['completed'],
        'total': session['total']
    })


@app.route('/api/session-status/<session_id>')
def session_status(session_id):
    """Get the current status of a job session (for reconnection)"""
    global job_sessions
    
    if session_id not in job_sessions:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    session = job_sessions[session_id]
    
    return jsonify({
        'success': True,
        'status': session['status'],
        'total': session['total'],
        'completed': session['completed'],
        'results': session['results'],
        'stop_requested': session.get('stop_requested', False)
    })


@app.route('/api/stream-jobs/<session_id>')
def stream_jobs(session_id):
    """Stream job results using Server-Sent Events"""
    log(f"=== /api/stream-jobs/{session_id} called ===")
    
    def generate():
        global job_sessions
        log(f"Generator started for session {session_id}")
        
        if session_id not in job_sessions:
            log(f"Session {session_id} not found!")
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return
        
        session = job_sessions[session_id]
        session['status'] = 'running'
        log(f"Session found. Jobs: {len(session['jobs'])}")
        
        all_jobs = session['jobs']
        url = session['url']
        bearer_token = session['bearer_token']
        timing_mode = session['timing_mode']
        fixed_delay = session['fixed_delay']
        min_delay = session['min_delay']
        max_delay = session['max_delay']
        temp_files = session['temp_files']
        total_jobs = len(all_jobs)
        
        for i, job in enumerate(all_jobs):
            # Check if stop was requested
            if session.get('stop_requested', False):
                session['status'] = 'stopped'
                success_count = sum(1 for r in session['results'] if r['success'])
                yield f"data: {json.dumps({'type': 'stopped', 'success_count': success_count, 'completed': session['completed'], 'total': total_jobs})}\n\n"
                # Clean up temp files
                for temp_path in temp_files.values():
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                return
            
            try:
                log(f"Processing job {i + 1}/{total_jobs}: {job['filename']} for {job['username']}")
                if job['pdf_source'] == 'generate':
                    # Generate a new PDF for each job
                    pdf_buffer = generate_pdf(job['filename'], job['industry'], job['min_pages'], job['max_pages'])
                    log(f"PDF generated, calling send_single_job_from_buffer...")
                    result = send_single_job_from_buffer(
                        url=url,
                        bearer_token=bearer_token,
                        file_buffer=pdf_buffer,
                        filename=job['filename'],
                        username=job['username'],
                        printer=job['printer'],
                        job_number=i + 1,
                        industry=job['industry']
                    )
                else:
                    # Use uploaded file
                    new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'job_{i}_{job["filename"]}')
                    shutil.copy(job['temp_path'], new_file_path)
                    
                    result = send_single_job(
                        url=url,
                        bearer_token=bearer_token,
                        file_path=new_file_path,
                        filename=job['filename'],
                        username=job['username'],
                        printer=job['printer'],
                        job_number=i + 1,
                        industry=job['industry']
                    )
                    
                    # Clean up the renamed file copy
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                
                session['results'].append(result)
                session['completed'] = i + 1
                
                # Send result to client
                yield f"data: {json.dumps({'type': 'job_result', 'result': result, 'progress': (i + 1) / total_jobs * 100})}\n\n"
                
                # Apply delay between jobs (except for the last one)
                if i < total_jobs - 1:
                    # Check stop during delay (check every 0.5 seconds)
                    delay = generate_random_delay(timing_mode, fixed_delay, min_delay, max_delay)
                    # Send delay info to client
                    yield f"data: {json.dumps({'type': 'delay', 'seconds': round(delay, 1)})}\n\n"
                    
                    # Sleep in small increments to allow stop checking
                    elapsed = 0
                    while elapsed < delay:
                        if session.get('stop_requested', False):
                            break
                        sleep_time = min(0.5, delay - elapsed)
                        time.sleep(sleep_time)
                        elapsed += sleep_time
                    
            except Exception as e:
                error_result = {
                    'job_number': i + 1,
                    'success': False,
                    'status_code': None,
                    'filename': job['filename'],
                    'username': job['username'],
                    'printer': job['printer'],
                    'industry': job['industry'],
                    'response': str(e)
                }
                session['results'].append(error_result)
                session['completed'] = i + 1
                yield f"data: {json.dumps({'type': 'job_result', 'result': error_result, 'progress': (i + 1) / total_jobs * 100})}\n\n"
        
        # Clean up temp files
        for temp_path in temp_files.values():
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Send completion message
        success_count = sum(1 for r in session['results'] if r['success'])
        yield f"data: {json.dumps({'type': 'complete', 'success_count': success_count, 'total': total_jobs})}\n\n"
        
        session['status'] = 'complete'
        
        # Clean up session after a delay (keep it around longer for reconnection)
        def cleanup():
            time.sleep(300)  # Keep session for 5 minutes for reconnection
            if session_id in job_sessions:
                del job_sessions[session_id]
        threading.Thread(target=cleanup, daemon=True).start()
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })


# Keep the old endpoint for backwards compatibility but mark deprecated
@app.route('/api/send-jobs', methods=['POST'])
def send_jobs():
    """Handle the print job submission for multiple industries (deprecated - use start-jobs + stream-jobs)"""
    global job_results
    job_results = []
    
    try:
        # Get global settings
        url = request.form.get('url', '').strip()
        bearer_token = request.form.get('bearer_token', '').strip()
        
        # Timing settings
        timing_mode = request.form.get('timing_mode', 'fixed')
        fixed_delay = float(request.form.get('fixed_delay', 1.0))
        min_delay = float(request.form.get('min_delay', 0.5))
        max_delay = float(request.form.get('max_delay', 120.0))
        
        # Get active industries from JSON
        industry_configs_json = request.form.get('industry_configs', '{}')
        industry_configs = json.loads(industry_configs_json)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        if not industry_configs:
            return jsonify({'success': False, 'error': 'At least one industry must be configured'}), 400
        
        # Build job queue from all industries
        all_jobs = []
        temp_files = {}  # Store uploaded files per industry
        
        for industry, config in industry_configs.items():
            num_jobs = int(config.get('num_jobs', 0))
            if num_jobs <= 0:
                continue
                
            usernames = [u.strip() for u in config.get('usernames', '').split(',') if u.strip()]
            printers = [p.strip() for p in config.get('printers', '').split(',') if p.strip()]
            filenames = [f.strip() for f in config.get('filenames', '').split(',') if f.strip()]
            pdf_source = config.get('pdf_source', 'generate')
            min_pages = int(config.get('min_pages', 1))
            max_pages = int(config.get('max_pages', 15))
            
            if not usernames:
                return jsonify({'success': False, 'error': f'{industry}: At least one username is required'}), 400
            if not printers:
                return jsonify({'success': False, 'error': f'{industry}: At least one printer is required'}), 400
            if not filenames:
                return jsonify({'success': False, 'error': f'{industry}: At least one filename is required'}), 400
            
            # Handle file upload for this industry
            temp_path = None
            if pdf_source == 'upload':
                file_key = f'file_{industry}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        original_filename = secure_filename(file.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{industry}_{original_filename}')
                        file.save(temp_path)
                        temp_files[industry] = temp_path
                
                if not temp_path:
                    return jsonify({'success': False, 'error': f'{industry}: No file uploaded'}), 400
            
            # Create jobs for this industry
            for i in range(num_jobs):
                job = {
                    'industry': industry,
                    'username': usernames[i % len(usernames)],
                    'printer': printers[i % len(printers)],
                    'filename': filenames[i % len(filenames)],
                    'pdf_source': pdf_source,
                    'min_pages': min_pages,
                    'max_pages': max_pages,
                    'temp_path': temp_path
                }
                # Ensure filename ends with .pdf
                if not job['filename'].lower().endswith('.pdf'):
                    job['filename'] += '.pdf'
                all_jobs.append(job)
        
        if not all_jobs:
            return jsonify({'success': False, 'error': 'No jobs to send'}), 400
        
        # Shuffle jobs to interleave industries naturally
        random.shuffle(all_jobs)
        
        # Send the jobs
        results = []
        total_jobs = len(all_jobs)
        
        for i, job in enumerate(all_jobs):
            if job['pdf_source'] == 'generate':
                # Generate a new PDF for each job
                pdf_buffer = generate_pdf(job['filename'], job['industry'], job['min_pages'], job['max_pages'])
                result = send_single_job_from_buffer(
                    url=url,
                    bearer_token=bearer_token,
                    file_buffer=pdf_buffer,
                    filename=job['filename'],
                    username=job['username'],
                    printer=job['printer'],
                    job_number=i + 1,
                    industry=job['industry']
                )
            else:
                # Use uploaded file
                new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'job_{i}_{job["filename"]}')
                shutil.copy(job['temp_path'], new_file_path)
                
                result = send_single_job(
                    url=url,
                    bearer_token=bearer_token,
                    file_path=new_file_path,
                    filename=job['filename'],
                    username=job['username'],
                    printer=job['printer'],
                    job_number=i + 1,
                    industry=job['industry']
                )
                
                # Clean up the renamed file copy
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
            
            results.append(result)
            
            # Apply delay between jobs (except for the last one)
            if i < total_jobs - 1:
                delay = generate_random_delay(timing_mode, fixed_delay, min_delay, max_delay)
                time.sleep(delay)
        
        # Clean up temp files
        for temp_path in temp_files.values():
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        
        job_results = results
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': True,
            'message': f'Completed {success_count}/{total_jobs} jobs successfully',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/results', methods=['GET'])
def get_results():
    """Return the current job results"""
    return jsonify(job_results)


if __name__ == '__main__':
    print("=" * 50)
    print("Print Job Seeder")
    print("=" * 50)
    print("Starting server at http://localhost:5757")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser automatically
    
    def open_browser():
        time.sleep(1.5)  # Wait for server to start
        webbrowser.open('http://localhost:5757')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=False, host='localhost', port=5757)
