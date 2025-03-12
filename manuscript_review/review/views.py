from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import Manuscript
import os
from .utils import process_math_review, process_full_review_async, process_final_review, extract_text_from_pdf
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.utils.decorators import method_decorator
import uuid
import asyncio
import aiohttp
from django.core.cache import cache
from django.http import HttpResponse
from django.core.cache import cache
from functools import wraps
from .queue_manager import RequestQueueManager
import json
from datetime import datetime
from pathlib import Path
from .agents.gpt_compare import ComparisonAgent
from django.views.decorators.http import require_GET

class HttpResponseTooManyRequests(HttpResponse):
    status_code = 429

import logging
logger = logging.getLogger(__name__)

from .queue_manager import RequestQueueManager
import uuid

# Initialize the queue manager as a global variable
queue_manager = RequestQueueManager()

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from functools import wraps
from django.http import JsonResponse#, HttpResponseTooManyRequests
import asyncio
import uuid
from django_ratelimit.decorators import ratelimit

def async_ratelimit(key='ip', rate='60/m', block=True):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped_view(request, *args, **kwargs):
            # Apply the regular ratelimit decorator to an intermediate sync function
            @ratelimit(key=key, rate=rate, block=block)
            def sync_check(request):
                return True
            
            # Run the ratelimit check
            sync_check(request)
            # If we get here, the rate limit check passed
            return await view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

# Change the order of decorators and use the async version
@csrf_exempt
@async_ratelimit(key='ip', rate='60/m', block=True)
async def full_review(request, manuscript_id):
    """
    Asynchronous view to handle full manuscript review.
    """
    print("Starting full_review view function")
    request_id = str(uuid.uuid4())
    try:
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        print(f"Processing request {request_id} from {ip_address}")
        
        # Clear any existing requests from this IP
        queue_manager.clear_ip_requests(ip_address)
        
        if not queue_manager.register_request(request_id, ip_address, 'review'):
            return JsonResponse({"error": "Server is busy"}, status=503)
        
        print(f"Getting manuscript {manuscript_id}")
        manuscript = await asyncio.to_thread(Manuscript.objects.get, id=manuscript_id)
        include_math = True
        print("Starting process_full_review_async")
        
        # Set initial progress
        cache.set(f'review_progress_{manuscript_id}', {
            'stage': 'Extracting text and images',
            'progress': 10
        })
        
        try:
            # Update progress before processing
            cache.set(f'review_progress_{manuscript_id}', {
                'stage': 'Running primary analysis',
                'progress': 30
            })
            
            reviews, full_text, rubric = await process_full_review_async(manuscript.file.path, include_math)
            
            # Update progress before final review
            cache.set(f'review_progress_{manuscript_id}', {
                'stage': 'Processing claims and issues',
                'progress': 60
            })
            
            final_review = process_final_review(reviews, full_text, rubric)
            print("Final review: ",final_review)
            
            # Set completion
            cache.set(f'review_progress_{manuscript_id}', {
                'stage': 'Generating final review',
                'progress': 80
            })
            
            return JsonResponse({
                "status": "success",
                "full_review": final_review
            })
        except Exception as e:
            logger.error(f"Error processing review: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
            
    except Exception as e:
        logger.error(f"Error in full_review: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        queue_manager.finish_request(request_id)

@csrf_exempt
def upload_pdf(request):
    """Upload a PDF manuscript file - accept ANY form of POST"""
    import logging
    import boto3
    import uuid
    from django.conf import settings
    
    # Log basic information
    print(f"UPLOAD ENDPOINT CALLED WITH METHOD: {request.method}")
    print(f"Content type: {request.content_type}")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    # Check where the file might be
    file = None
    
    # Option 1: Check if file is in standard form upload (multipart/form-data)
    if 'file' in request.FILES:
        file = request.FILES['file']
        print(f"Found file in request.FILES: {file.name}, size: {file.size}")
    
    # Option 2: Look in request.POST items (sometimes Django puts small files here)
    elif 'file' in request.POST:
        # This is rare but can happen
        file_data = request.POST['file']
        print(f"Found file reference in POST data")
    
    # Option 3: Check if it's a JSON payload with S3 info
    elif request.content_type and 'application/json' in request.content_type:
        try:
            import json
            data = json.loads(request.body)
            file_key = data.get('file_key')
            
            if file_key:
                print(f"Found S3 file key in JSON payload: {file_key}")
                
                # Create manuscript record for the S3 file
                manuscript = Manuscript(file=file_key)
                manuscript.save()
                
                return JsonResponse({
                    'success': True,
                    'manuscript_id': manuscript.id,
                    'message': 'S3 upload registered'
                })
        except Exception as e:
            print(f"Error parsing JSON: {str(e)}")
            return JsonResponse({'error': f'Error parsing JSON: {str(e)}'}, status=400)
    
    # No file found at all
    if not file and 'file_key' not in locals():
        print("No file found in request")
        return JsonResponse({
            'error': 'No file found in request',
            'detail': {
                'FILES_keys': list(request.FILES.keys()),
                'POST_keys': list(request.POST.keys()),
                'content_type': request.content_type,
                'method': request.method
            }
        }, status=400)
    
    # Process the file if we found it in request.FILES
    if file:
        if not file.name.endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)
        
        try:
            # Create a unique key for the file
            file_key = f"manuscripts/{uuid.uuid4()}/{file.name}"
            
            # Upload to S3
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            from io import BytesIO
            file_content = BytesIO(file.read())
            s3.upload_fileobj(
                file_content, 
                settings.AWS_STORAGE_BUCKET_NAME, 
                file_key
            )
            
            print(f"File uploaded to S3: {file_key}")
            
            # Create manuscript record
            manuscript = Manuscript(file=file_key)
            manuscript.save()
            
            print(f"Manuscript created with ID: {manuscript.id}")
            
            return JsonResponse({
                'success': True,
                'manuscript_id': manuscript.id,
                'message': 'File uploaded successfully'
            })
            
        except Exception as e:
            import traceback
            print(f"Error uploading file: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)
    
    # If we got here, something unexpected happened
    return JsonResponse({'error': 'Unexpected request format'}, status=400)

@csrf_exempt
def queue_status(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    status = queue_manager.get_queue_status()
    status['current_ip'] = ip_address
    return JsonResponse(status)




@csrf_exempt
def math_review(request, manuscript_id):
    try:
        manuscript = Manuscript.objects.get(id=manuscript_id)
        result = process_math_review(manuscript.file.path)  # Call the math review agent
        return JsonResponse({"math_review": result})
    except Manuscript.DoesNotExist:
        return JsonResponse({"error": "Manuscript not found"}, status=404)

# @csrf_exempt
# def final_review(request, manuscript_id):
    # try:
        # manuscript = Manuscript.objects.get(id=manuscript_id)
        # include_math = request.GET.get('include_math', 'false') == 'true'
        # result = process_final_review(manuscript.file.path, include_math)  # Call the final review agent
        # return JsonResponse({"final_review": result})
    # except Manuscript.DoesNotExist:
        # return JsonResponse({"error": "Manuscript not found"}, status=404)

@csrf_exempt
def save_feedback(request):
    """Simplified feedback endpoint"""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Feedback attempt with method: {request.method}")
    
    if request.method == 'POST':
        logger.debug(f"Feedback data: {request.POST}")
        # Just return success for now
        return JsonResponse({
            'success': True,
            'message': 'Feedback received'
        })
    
    return JsonResponse({
        'success': False,
        'error': 'Only POST requests are supported'
    }, status=405)

@csrf_exempt
async def cleanup(request):
    try:
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        queue_manager.clear_stale_requests(ip_address)
        return JsonResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        queue_manager.force_cleanup()  # Force cleanup as last resort
        return JsonResponse({"status": "cleaned"}, status=200)

@csrf_exempt
async def reset_queue(request):
    """Emergency endpoint to reset all queues"""
    try:
        queue_manager.force_cleanup()
        return JsonResponse({"status": "reset_successful"})
    except Exception as e:
        logger.error(f"Error in reset_queue: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def review_progress(request, manuscript_id):
    """Return the current review progress for a manuscript."""
    try:
        progress = cache.get(f'review_progress_{manuscript_id}', {
            'stage': 'Initializing...',
            'progress': 0
        })
        return JsonResponse(progress)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
async def compare_review(request, manuscript_id):
    try:
        manuscript = await asyncio.to_thread(Manuscript.objects.get, id=manuscript_id)
        
        if not manuscript or not manuscript.file:
            return JsonResponse({"error": "Manuscript or file not found"}, status=404)
            
        # Set initial progress
        cache.set(f'compare_progress_{manuscript_id}', {
            'stage': 'Running GPT-4o comparison',
            'progress': 10
        })
        
        try:
            all_text = extract_text_from_pdf(manuscript.file.path)
        except Exception as e:
            return JsonResponse({"error": f"Failed to extract text: {str(e)}"}, status=500)
        
        try:
            comparison_agent = ComparisonAgent()
            comparison_review = comparison_agent.run(all_text)
        except Exception as e:
            return JsonResponse({"error": f"Failed to generate comparison: {str(e)}"}, status=500)
        
        cache.set(f'compare_progress_{manuscript_id}', {
            'stage': 'Complete',
            'progress': 100
        })
        
        return JsonResponse({
            "status": "success",
            "comparison_review": comparison_review
        })
        
    except Manuscript.DoesNotExist:
        return JsonResponse({"error": "Manuscript not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in compare_review: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
async def compare_progress(request, manuscript_id):
    try:
        progress_data = cache.get(f'compare_progress_{manuscript_id}', {
            'stage': 'Not started',
            'progress': 0
        })
        return JsonResponse(progress_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_GET
def serve_sitemap(request):
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://paper-reviewer.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return HttpResponse(sitemap_content, content_type='application/xml')

@require_GET
def health_check(request):
    return HttpResponse("OK", status=200)

@csrf_exempt
def test_connection(request):
    """Simple endpoint to test connectivity"""
    import json
    return JsonResponse({
        'status': 'success',
        'message': 'Backend connection working',
        'method': request.method,
        'headers': dict(request.headers),
        'time': str(datetime.now())
    })

def test_upload_page(request):
    """Serve a simple HTML page to test file uploads with detailed error display"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Upload</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .error { color: red; }
            pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Test File Upload</h1>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" name="file" id="fileInput" accept=".pdf">
            <button type="submit">Upload</button>
        </form>
        
        <h2>Results:</h2>
        <div id="results"></div>
        
        <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            const resultsDiv = document.getElementById('results');
            
            if (!fileInput.files.length) {
                resultsDiv.innerHTML = '<p class="error">Please select a file</p>';
                return;
            }
            
            // Create FormData
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            try {
                resultsDiv.innerHTML = '<p>Uploading...</p>';
                console.log('Starting upload');
                
                // Detailed fetch with error handling
                const response = await fetch('/upload/', {
                    method: 'POST',
                    body: formData,
                });
                
                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Response data:', data);
                
                if (response.ok) {
                    resultsDiv.innerHTML = `
                        <p>Upload successful!</p>
                        <p>Manuscript ID: ${data.manuscript_id}</p>
                        <p>File URL: <a href="${data.file_url}" target="_blank">${data.file_url}</a></p>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                } else {
                    resultsDiv.innerHTML = `
                        <p class="error">Upload failed with status ${response.status}</p>
                        <p>Error: ${data.error || 'Unknown error'}</p>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                }
            } catch (error) {
                console.error('Upload error:', error);
                resultsDiv.innerHTML = `
                    <p class="error">Error: ${error.message}</p>
                    <pre>${error.stack || ''}</pre>
                `;
            }
        });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)

@csrf_exempt
def debug_environment(request):
    """Debug endpoint that returns environment information"""
    import json
    import boto3
    import os
    import sys
    from django.conf import settings
    
    debug_info = {
        "request_received": True,
        "python_version": sys.version,
        "environment_vars": dict(os.environ),
        "django_settings": {
            "debug": settings.DEBUG,
            "allowed_hosts": settings.ALLOWED_HOSTS,
            "databases": str(settings.DATABASES),
            "installed_apps": settings.INSTALLED_APPS,
            "middleware": settings.MIDDLEWARE,
        },
        "s3_check": {}
    }
    
    # Try listing S3 buckets to verify permissions
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        buckets = s3.list_buckets()
        debug_info["s3_check"]["can_list_buckets"] = True
        debug_info["s3_check"]["buckets"] = [b["Name"] for b in buckets["Buckets"]]
        
        # Try to create a test file in the bucket
        try:
            test_content = f"Test file created at {datetime.now().isoformat()}"
            s3.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key="debug/test_file.txt",
                Body=test_content
            )
            debug_info["s3_check"]["can_write_to_bucket"] = True
        except Exception as e:
            debug_info["s3_check"]["can_write_to_bucket"] = False
            debug_info["s3_check"]["write_error"] = str(e)
    
    except Exception as e:
        debug_info["s3_check"]["can_list_buckets"] = False
        debug_info["s3_check"]["error"] = str(e)
    
    # Add URL to the response
    debug_info["urls"] = {
        "current": request.build_absolute_uri(),
        "upload_url": request.build_absolute_uri('/upload/'),
        "test_upload_url": request.build_absolute_uri('/test-upload/'),
    }
    
    # Add form processing check
    if request.method == 'POST':
        debug_info["post_data"] = {k: str(v) for k, v in request.POST.items()}
        debug_info["files"] = {k: {"name": v.name, "size": v.size, "content_type": v.content_type} 
                               for k, v in request.FILES.items()}
    
    return JsonResponse(debug_info)

def debug_form(request):
    """Serve a simple HTML form to test file uploads directly to debug endpoint"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Form</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Debug Form</h1>
        <form action="/debug/" method="post" enctype="multipart/form-data">
            <div>
                <label for="textField">Text field:</label>
                <input type="text" id="textField" name="textField" value="Test value">
            </div>
            <div style="margin-top: 10px;">
                <label for="fileInput">Upload a file:</label>
                <input type="file" id="fileInput" name="file">
            </div>
            <div style="margin-top: 10px;">
                <button type="submit">Submit</button>
            </div>
        </form>
        
        <h2>Direct S3 Upload Test:</h2>
        <div id="s3UploadResult"></div>
        <button id="testS3Upload">Test Direct S3 Upload</button>
        
        <script>
        document.getElementById('testS3Upload').addEventListener('click', async function() {
            const resultDiv = document.getElementById('s3UploadResult');
            resultDiv.innerHTML = 'Testing S3 upload...';
            
            try {
                const response = await fetch('/debug/?s3test=true');
                const data = await response.json();
                resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                resultDiv.innerHTML = 'Error: ' + error.message;
            }
        });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)

def presigned_upload_test(request):
    """Serve a simple HTML page to test presigned URL uploads"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>S3 Presigned Upload Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .status { margin: 10px 0; padding: 10px; border-radius: 4px; }
            .error { background-color: #ffeeee; color: #990000; }
            .success { background-color: #eeffee; color: #009900; }
            button { padding: 8px 16px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; }
            input { margin: 10px 0; padding: 8px; }
        </style>
    </head>
    <body>
        <h1>S3 Presigned URL Upload Test</h1>
        
        <div>
            <input type="file" id="fileInput" accept=".pdf">
            <button id="uploadBtn">Upload File</button>
        </div>
        
        <div id="status"></div>
        
        <script>
        document.getElementById('uploadBtn').addEventListener('click', async function() {
            const fileInput = document.getElementById('fileInput');
            const statusDiv = document.getElementById('status');
            
            if (!fileInput.files.length) {
                statusDiv.innerHTML = '<div class="status error">Please select a file</div>';
                return;
            }
            
            const file = fileInput.files[0];
            statusDiv.innerHTML = '<div class="status">Getting presigned URL...</div>';
            
            try {
                // Step 1: Get presigned URL from backend
                const getUrlResponse = await fetch('/upload/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: file.name
                    })
                });
                
                if (!getUrlResponse.ok) {
                    const errorData = await getUrlResponse.json();
                    throw new Error(`Failed to get presigned URL: ${errorData.error || getUrlResponse.statusText}`);
                }
                
                const urlData = await getUrlResponse.json();
                statusDiv.innerHTML += '<div class="status">Got presigned URL, uploading file...</div>';
                console.log('Presigned URL data:', urlData);
                
                // Step 2: Upload file directly to S3 using the presigned URL
                const uploadResponse = await fetch(urlData.presigned_url, {
                    method: urlData.upload_method,
                    body: file,
                    headers: {
                        'Content-Type': 'application/pdf'
                    }
                });
                
                if (!uploadResponse.ok) {
                    throw new Error(`Failed to upload to S3: ${uploadResponse.statusText}`);
                }
                
                // Success!
                const fileUrl = urlData.presigned_url.split('?')[0];
                statusDiv.innerHTML += `
                    <div class="status success">
                        <p>Upload successful!</p>
                        <p>Manuscript ID: ${urlData.manuscript_id}</p>
                        <p>File key: ${urlData.file_key}</p>
                    </div>
                `;
                
            } catch (error) {
                console.error('Upload error:', error);
                statusDiv.innerHTML += `<div class="status error">Error: ${error.message}</div>`;
            }
        });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)

def direct_test(request):
    """Direct test endpoint that can be accessed from the browser"""
    import logging
    import json
    from django.conf import settings
    
    logger = logging.getLogger('django')
    logger.error("DIRECT TEST ENDPOINT CALLED")
    
    response_data = {
        "message": "If you can see this, the backend is working",
        "method": request.method,
        "path": request.path,
        "AWS_STORAGE_BUCKET_NAME": settings.AWS_STORAGE_BUCKET_NAME,
        "timestamp": str(datetime.now())
    }
    
    # Force an error log to see if logging works
    print("DIRECT TEST PRINT STATEMENT")
    logger.error("DIRECT TEST ERROR LOG")
    
    return JsonResponse(response_data)

@csrf_exempt
def get_upload_params(request):
    """Generate parameters for direct S3 upload from frontend"""
    import json
    import boto3
    import uuid
    from django.conf import settings
    
    print("GENERATING UPLOAD PARAMETERS")
    
    try:
        # Create a unique file key
        unique_id = str(uuid.uuid4())
        
        # Return the parameters needed for frontend to upload directly to S3
        return JsonResponse({
            'success': True,
            'uploadParams': {
                'bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'region': settings.AWS_S3_REGION_NAME,
                'accessKeyId': settings.AWS_ACCESS_KEY_ID,
                'secretAccessKey': settings.AWS_SECRET_ACCESS_KEY,
                'fileKeyPrefix': f"manuscripts/{unique_id}/"
            }
        })
    except Exception as e:
        import traceback
        print(f"Error generating upload parameters: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def register_uploaded_file(request):
    """Register an uploaded file in the database"""
    import json
    import boto3
    from django.conf import settings
    
    print("REGISTERING UPLOADED FILE")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        file_key = data.get('fileKey')
        
        if not file_key:
            return JsonResponse({'error': 'No fileKey provided'}, status=400)
        
        # Create manuscript record
        manuscript = Manuscript(file=file_key)
        manuscript.save()
        
        return JsonResponse({
            'success': True,
            'manuscriptId': manuscript.id
        })
    except Exception as e:
        import traceback
        print(f"Error registering file: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

def react_test(request):
    """Test page for the new React upload approach"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>React Upload Fix Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .error { background: #ffdddd; color: #990000; }
            .success { background: #ddffdd; color: #009900; }
            button { padding: 10px; background: #0066cc; color: white; border: none; cursor: pointer; }
            input { margin: 10px 0; padding: 8px; }
        </style>
    </head>
    <body>
        <h1>React Upload Fix Test</h1>
        
        <div>
            <input type="file" id="fileInput" accept=".pdf">
            <button id="uploadBtn">Upload File</button>
        </div>
        
        <div id="status" class="status"></div>
        
        <script src="https://sdk.amazonaws.com/js/aws-sdk-2.1045.0.min.js"></script>
        <script>
        document.getElementById('uploadBtn').addEventListener('click', async function() {
            const fileInput = document.getElementById('fileInput');
            const statusDiv = document.getElementById('status');
            
            if (!fileInput.files.length) {
                statusDiv.innerHTML = 'Please select a file';
                statusDiv.className = 'status error';
                return;
            }
            
            const file = fileInput.files[0];
            statusDiv.innerHTML = 'Starting upload process...';
            statusDiv.className = 'status';
            
            try {
                // Step 1: Get upload parameters
                statusDiv.innerHTML += '<br>Getting upload parameters...';
                const paramsResponse = await fetch('/get-upload-params/');
                if (!paramsResponse.ok) {
                    throw new Error(`Failed to get parameters: ${paramsResponse.statusText}`);
                }
                const paramsData = await paramsResponse.json();
                if (!paramsData.success) {
                    throw new Error(paramsData.error || 'Failed to get upload parameters');
                }
                
                // Step 2: Upload to S3
                statusDiv.innerHTML += '<br>Uploading to S3...';
                const uploadParams = paramsData.uploadParams;
                
                // Configure AWS SDK
                AWS.config.update({
                    accessKeyId: uploadParams.accessKeyId,
                    secretAccessKey: uploadParams.secretAccessKey,
                    region: uploadParams.region
                });
                
                const s3 = new AWS.S3();
                
                // Generate file key
                const fileKey = `${uploadParams.fileKeyPrefix}${file.name}`;
                
                // Upload to S3
                const uploadResult = await new Promise((resolve, reject) => {
                    s3.upload({
                        Bucket: uploadParams.bucket,
                        Key: fileKey,
                        Body: file,
                        ContentType: file.type || 'application/pdf'
                    }, (err, data) => {
                        if (err) reject(err);
                        else resolve(data);
                    });
                });
                
                statusDiv.innerHTML += '<br>S3 upload successful!';
                
                // Step 3: Register with backend
                statusDiv.innerHTML += '<br>Registering uploaded file...';
                const regResponse = await fetch('/register-uploaded-file/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ fileKey })
                });
                
                if (!regResponse.ok) {
                    throw new Error(`Failed to register file: ${regResponse.statusText}`);
                }
                
                const regData = await regResponse.json();
                
                // Success!
                statusDiv.innerHTML = 'Upload process completed successfully!';
                statusDiv.innerHTML += `<br>Manuscript ID: ${regData.manuscriptId}`;
                statusDiv.innerHTML += `<br>File key: ${fileKey}`;
                statusDiv.className = 'status success';
                
            } catch (error) {
                console.error('Upload error:', error);
                statusDiv.innerHTML = `Error: ${error.message}`;
                statusDiv.className = 'status error';
            }
        });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)

def console_fix(request):
    """Page with instructions for fixing upload via console"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Fix via Console</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; max-width: 800px; }
            h1, h2 { color: #333; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .step { margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .code { font-family: monospace; background: #f0f0f0; padding: 2px 4px; }
        </style>
    </head>
    <body>
        <h1>Fix Upload via Console Script</h1>
        
        <div class="step">
            <h2>Step 1: Go to the Paper Reviewer Homepage</h2>
            <p>Open <a href="https://paper-reviewer.com" target="_blank">https://paper-reviewer.com</a> in your browser.</p>
        </div>
        
        <div class="step">
            <h2>Step 2: Open Developer Console</h2>
            <p>Press <span class="code">F12</span> or right-click and select "Inspect", then click on the "Console" tab.</p>
        </div>
        
        <div class="step">
            <h2>Step 3: Paste the following code into the console</h2>
            <pre>
// Add AWS SDK to the page
function loadScript(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = url;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

// The main fix function
async function fixUpload() {
  try {
    // Load AWS SDK if needed
    if (!window.AWS) {
      await loadScript('https://sdk.amazonaws.com/js/aws-sdk-2.1045.0.min.js');
      console.log('AWS SDK loaded');
    }
    
    // Replace the upload function
    window.uploadManuscript = async function(file) {
      console.log('S3 direct upload initiated for file:', file.name);
      
      try {
        // Configure AWS SDK
        AWS.config.update({
          accessKeyId: '',
          secretAccessKey: '',
          region: 'us-east-1'
        });
        
        const s3 = new AWS.S3();
        const bucket = '';
        
        // Generate a unique key
        const fileKey = `manuscripts/${Date.now()}-${file.name}`;
        
        // Upload to S3
        console.log('Starting S3 upload...');
        const uploadResult = await new Promise((resolve, reject) => {
          s3.upload({
            Bucket: bucket,
            Key: fileKey,
            Body: file,
            ContentType: 'application/pdf'
          }, (err, data) => {
            if (err) reject(err);
            else resolve(data);
          });
        });
        
        console.log('S3 upload successful:', uploadResult);
        
        // Create a manuscript record in the database
        const response = await fetch('/upload/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_key: fileKey,
            file_name: file.name
          })
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Backend response error:', response.status, errorText);
          throw new Error(`Backend error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Backend registration successful:', data);
        
        return {
          success: true,
          manuscriptId: data.manuscript_id || 1, // Fallback to 1 if not provided
          message: 'Upload successful'
        };
      } catch (error) {
        console.error('Upload failed:', error);
        return {
          success: false,
          error: error.message || 'Unknown upload error'
        };
      }
    };
    
    // Find the React component
    let found = false;
    for (const key in window) {
      if (key.startsWith('__reactContainer') || key.includes('react')) {
        try {
          if (window[key] && window[key].uploadManuscript) {
            window[key].uploadManuscript = window.uploadManuscript;
            found = true;
            console.log('Found and replaced React upload function');
          }
        } catch (e) {}
      }
    }
    
    if (!found) {
      console.log('Upload function ready but React component not found');
      console.log('Try uploading a manuscript now - it should use the direct S3 upload');
    }
    
    return 'Upload fix applied - try uploading a PDF now';
  } catch (error) {
    console.error('Error fixing upload:', error);
    return 'Failed to apply fix: ' + error.message;
  }
}

// Run the fix
fixUpload().then(console.log);
            </pre>
        </div>
        
        <div class="step">
            <h2>Step 4: Try uploading a PDF manuscript</h2>
            <p>After running the script, try uploading a PDF file through the normal Paper Reviewer interface.</p>
            <p>Check the console for detailed logs of what's happening.</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

