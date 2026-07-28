"""
Batch job session routes for the Print Job Seeder.
One Vasion batch to one printer: open → parallel job submit → close (auto or manual).
"""

import os
import json
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import request, jsonify, Response
from werkzeug.utils import secure_filename

from print_utils import (
    log,
    get_api_base_url, open_batch, close_batch,
    generate_pdf, send_single_job, send_single_job_from_buffer
)

BATCH_PARALLEL_WORKERS = 8

# Populated by register_batch_routes
batch_sessions = {}
_upload_folder = None
_build_batch_name = None


def _cleanup_batch_temp_files(temp_files):
    for paths in (temp_files or {}).values():
        for temp_path in paths:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


def register_batch_routes(app, upload_folder, build_batch_name_fn):
    """Attach batch routes to the Flask app and share helpers/state."""
    global _upload_folder, _build_batch_name
    _upload_folder = upload_folder
    _build_batch_name = build_batch_name_fn

    @app.route('/api/start-batch-jobs', methods=['POST'])
    def start_batch_jobs():
        """Initialize a batch job session (one batch, one printer) and return session ID."""
        log("=== /api/start-batch-jobs called ===")

        try:
            url = request.form.get('url', '').strip()
            bearer_token = request.form.get('bearer_token', '').strip()
            close_mode = request.form.get('close_mode', 'auto')
            if close_mode not in ('auto', 'manual'):
                close_mode = 'auto'

            industry = request.form.get('industry', '').strip()
            printer = request.form.get('printer', '').strip()
            pdf_source = request.form.get('pdf_source', 'generate')
            num_jobs = int(request.form.get('num_jobs', 0) or 0)
            min_pages = int(request.form.get('min_pages', 1) or 1)
            max_pages = int(request.form.get('max_pages', 15) or 15)
            usernames = [u.strip() for u in request.form.get('usernames', '').split(',') if u.strip()]
            filenames = [f.strip() for f in request.form.get('filenames', '').split(',') if f.strip()]

            if not url:
                return jsonify({'success': False, 'error': 'URL is required'}), 400
            if not industry:
                return jsonify({'success': False, 'error': 'An industry is required'}), 400
            if not printer:
                return jsonify({'success': False, 'error': 'A printer is required'}), 400
            if not usernames:
                return jsonify({'success': False, 'error': 'At least one username is required'}), 400

            base_url = get_api_base_url(url)
            if not base_url:
                return jsonify({'success': False, 'error': 'Could not derive API base URL from print URL'}), 400

            temp_files = {}

            if pdf_source == 'upload':
                # The uploaded PDFs are the batch: one job per file, in the order listed
                token = uuid.uuid4().hex[:8]
                job_files = []
                for index, file in enumerate(request.files.getlist('files')):
                    if not file.filename:
                        continue
                    filename = secure_filename(file.filename)
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    temp_path = os.path.join(_upload_folder, f'batch_{token}_{index}_{filename}')
                    file.save(temp_path)
                    job_files.append((filename, temp_path))

                if not job_files:
                    return jsonify({'success': False, 'error': 'At least one PDF file must be uploaded'}), 400

                temp_files[industry] = [path for _, path in job_files]
            else:
                if num_jobs <= 0:
                    return jsonify({'success': False, 'error': 'Number of jobs must be at least 1'}), 400
                if not filenames:
                    return jsonify({'success': False, 'error': 'At least one filename is required'}), 400

                job_files = []
                for i in range(num_jobs):
                    filename = filenames[i % len(filenames)]
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    job_files.append((filename, None))

            jobs = []
            for i, (filename, temp_path) in enumerate(job_files):
                jobs.append({
                    'industry': industry,
                    'username': usernames[i % len(usernames)],
                    'printer': printer,
                    'filename': filename,
                    'pdf_source': pdf_source,
                    'min_pages': min_pages,
                    'max_pages': max_pages,
                    'temp_path': temp_path,
                    'job_id': str(uuid.uuid4()),
                    'job_number': i + 1
                })

            batch = {
                'industry': industry,
                'batch_id': str(uuid.uuid4()),
                'name': _build_batch_name(industry),
                'jobs': jobs,
                'job_ids': [j['job_id'] for j in jobs]
            }

            session_id = str(uuid.uuid4())
            batch_sessions[session_id] = {
                'batches': [batch],
                'results': [],
                'status': 'ready',
                'total': len(jobs),
                'completed': 0,
                'url': url,
                'base_url': base_url,
                'bearer_token': bearer_token,
                'close_mode': close_mode,
                'temp_files': temp_files,
                'close_requested': False,
                'cancel_requested': False,
                'awaiting_close': False,
                'current_batch_id': None,
                'created_at': time.time()
            }

            return jsonify({
                'success': True,
                'session_id': session_id,
                'total_jobs': len(jobs),
                'batch_count': 1,
                'close_mode': close_mode
            })

        except Exception as e:
            log(f"start_batch_jobs error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/close-batch/<session_id>', methods=['POST'])
    def close_batch_session(session_id):
        """Signal that the user wants to close the current awaiting batch."""
        if session_id not in batch_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        session = batch_sessions[session_id]
        if not session.get('awaiting_close'):
            return jsonify({'success': False, 'error': 'No batch is currently awaiting close'}), 400

        session['close_requested'] = True
        return jsonify({
            'success': True,
            'message': 'Close requested',
            'batch_id': session.get('current_batch_id')
        })

    @app.route('/api/cancel-batch/<session_id>', methods=['POST'])
    def cancel_batch_session(session_id):
        """Cancel a batch session locally without closing batches on Output."""
        if session_id not in batch_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        session = batch_sessions[session_id]
        session['cancel_requested'] = True
        session['close_requested'] = True  # unblock any wait loop
        session['status'] = 'cancelling'

        return jsonify({
            'success': True,
            'message': 'Cancel requested',
            'completed': session['completed'],
            'total': session['total']
        })

    @app.route('/api/stream-batch-jobs/<session_id>')
    def stream_batch_jobs(session_id):
        """Stream batch open / job submit / batch close events via SSE."""
        log(f"=== /api/stream-batch-jobs/{session_id} called ===")

        def generate():
            if session_id not in batch_sessions:
                yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
                return

            session = batch_sessions[session_id]
            session['status'] = 'running'

            print_url = session['url']
            base_url = session['base_url']
            bearer_token = session['bearer_token']
            close_mode = session['close_mode']
            temp_files = session['temp_files']
            total_jobs = session['total']
            batches = session['batches']

            def send_one_job(job):
                try:
                    if job['pdf_source'] == 'generate':
                        pdf_buffer = generate_pdf(
                            job['filename'], job['industry'],
                            job['min_pages'], job['max_pages']
                        )
                        return send_single_job_from_buffer(
                            url=print_url,
                            bearer_token=bearer_token,
                            file_buffer=pdf_buffer,
                            filename=job['filename'],
                            username=job['username'],
                            printer=job['printer'],
                            job_number=job['job_number'],
                            industry=job['industry'],
                            job_id=job['job_id']
                        )
                    else:
                        new_file_path = os.path.join(
                            _upload_folder,
                            f'batch_job_{job["job_id"]}_{job["filename"]}'
                        )
                        shutil.copy(job['temp_path'], new_file_path)
                        try:
                            return send_single_job(
                                url=print_url,
                                bearer_token=bearer_token,
                                file_path=new_file_path,
                                filename=job['filename'],
                                username=job['username'],
                                printer=job['printer'],
                                job_number=job['job_number'],
                                industry=job['industry'],
                                job_id=job['job_id']
                            )
                        finally:
                            if os.path.exists(new_file_path):
                                os.remove(new_file_path)
                except Exception as e:
                    return {
                        'job_number': job['job_number'],
                        'success': False,
                        'status_code': None,
                        'filename': job['filename'],
                        'username': job['username'],
                        'printer': job['printer'],
                        'industry': job['industry'],
                        'job_id': job['job_id'],
                        'response': str(e)
                    }

            for batch in batches:
                if session.get('cancel_requested'):
                    break

                industry = batch['industry']
                batch_id = batch['batch_id']
                batch_name = batch['name']
                jobs = batch['jobs']
                job_ids = batch['job_ids']

                session['current_batch_id'] = batch_id
                session['close_requested'] = False
                session['awaiting_close'] = False

                open_result = open_batch(
                    base_url=base_url,
                    bearer_token=bearer_token,
                    batch_id=batch_id,
                    job_ids=job_ids,
                    name=batch_name,
                    require_all_jobs=True
                )

                if not open_result['success']:
                    err_msg = open_result.get('response', 'unknown error')
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to open batch for {industry}: {err_msg}', 'industry': industry, 'batch_id': batch_id})}\n\n"
                    continue

                auth_mode = open_result.get('auth_mode')
                yield f"data: {json.dumps({'type': 'batch_opened', 'industry': industry, 'batch_id': batch_id, 'name': batch_name, 'job_count': len(jobs)})}\n\n"

                if session.get('cancel_requested'):
                    break

                workers = min(BATCH_PARALLEL_WORKERS, max(1, len(jobs)))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {executor.submit(send_one_job, job): job for job in jobs}
                    for future in as_completed(futures):
                        if session.get('cancel_requested'):
                            for f in futures:
                                f.cancel()
                            break

                        result = future.result()
                        session['results'].append(result)
                        session['completed'] = len(session['results'])
                        progress = (session['completed'] / total_jobs * 100) if total_jobs else 100
                        yield f"data: {json.dumps({'type': 'job_result', 'result': result, 'progress': progress})}\n\n"

                if session.get('cancel_requested'):
                    break

                # Give Output a moment to associate parallel submits before close
                # (especially important with requireAllJobs=true).
                time.sleep(1.0)

                if close_mode == 'auto':
                    close_result = close_batch(base_url, bearer_token, batch_id, auth_mode=auth_mode)
                    yield f"data: {json.dumps({'type': 'batch_closed', 'industry': industry, 'batch_id': batch_id, 'success': close_result['success'], 'status_code': close_result.get('status_code'), 'response': close_result.get('response', ''), 'attempt': close_result.get('attempt')})}\n\n"
                else:
                    session['awaiting_close'] = True
                    yield f"data: {json.dumps({'type': 'awaiting_close', 'industry': industry, 'batch_id': batch_id, 'name': batch_name})}\n\n"

                    while not session.get('close_requested') and not session.get('cancel_requested'):
                        time.sleep(0.5)

                    session['awaiting_close'] = False

                    if session.get('cancel_requested'):
                        break

                    close_result = close_batch(base_url, bearer_token, batch_id, auth_mode=auth_mode)
                    session['close_requested'] = False
                    yield f"data: {json.dumps({'type': 'batch_closed', 'industry': industry, 'batch_id': batch_id, 'success': close_result['success'], 'status_code': close_result.get('status_code'), 'response': close_result.get('response', ''), 'attempt': close_result.get('attempt')})}\n\n"

            _cleanup_batch_temp_files(temp_files)

            success_count = sum(1 for r in session['results'] if r.get('success'))

            if session.get('cancel_requested'):
                session['status'] = 'cancelled'
                yield f"data: {json.dumps({'type': 'cancelled', 'success_count': success_count, 'completed': session['completed'], 'total': total_jobs})}\n\n"
            else:
                session['status'] = 'complete'
                yield f"data: {json.dumps({'type': 'complete', 'success_count': success_count, 'total': total_jobs})}\n\n"

            def cleanup():
                time.sleep(300)
                if session_id in batch_sessions:
                    del batch_sessions[session_id]
            threading.Thread(target=cleanup, daemon=True).start()

        return Response(generate(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        })
