from threading import Lock, Semaphore
from collections import deque
import time
import threading

class RequestQueueManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.active_requests = {}
        self.max_concurrent = 4  # Default value
        self.semaphore = threading.Semaphore(self.max_concurrent)
        self.last_cleanup = time.time()

    def register_request(self, request_id, ip_address, request_type):
        with self._lock:
            self.active_requests[request_id] = {
                'ip': ip_address,
                'type': request_type,
                'timestamp': time.time()
            }
            return self.semaphore.acquire(blocking=False)

    def finish_request(self, request_id):
        with self._lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
                self.semaphore.release()

    def clear_ip_requests(self, ip_address):
        with self._lock:
            request_ids = [
                req_id for req_id, info in self.active_requests.items()
                if info['ip'] == ip_address
            ]
            for req_id in request_ids:
                self.finish_request(req_id)

    def get_queue_position(self, request_id, request_type='upload'):
        queue = self.upload_queue if request_type == 'upload' else self.review_queue
        lock = self.upload_lock if request_type == 'upload' else self.review_lock
        
        with lock:
            try:
                for i, (queued_id, _) in enumerate(queue):
                    if queued_id == request_id:
                        return i + 1
                return 0
            except ValueError:
                return 0

    def get_queue_status(self, request_type='upload'):
        active_dict = self.active_uploads if request_type == 'upload' else self.active_reviews
        queue = self.upload_queue if request_type == 'upload' else self.review_queue
        lock = self.upload_lock if request_type == 'upload' else self.review_lock
        
        with lock:
            return {
                'active_requests': len(active_dict),
                'queue_length': len(queue),
                'max_concurrent': self.max_concurrent
            }

    def force_cleanup(self):
        """Force cleanup of all requests and reset semaphores"""
        with self._lock:
            self.active_requests.clear()
            
            # Reset semaphores
            while self.semaphore.acquire(blocking=False):
                pass
            for _ in range(self.max_concurrent):  # Reset to initial value
                self.semaphore.release()

    def set_max_concurrent(self, value):
        """Set the maximum number of concurrent requests"""
        with self._lock:
            # First, clean up existing semaphore
            while self.semaphore.acquire(blocking=False):
                pass
            # Create new semaphore with new value
            self.max_concurrent = value
            self.semaphore = threading.Semaphore(value)
            # Initialize the semaphore to its full value
            for _ in range(value):
                self.semaphore.release()
