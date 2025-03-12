"""
URL configuration for manuscript_review project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from review import views
from django.views.generic import TemplateView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView
from review.views import save_feedback, serve_sitemap, health_check, debug_environment, debug_form, presigned_upload_test, direct_test, get_upload_params, register_uploaded_file, console_fix

urlpatterns = [
    path("admin/", admin.site.urls),
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('math-review/<int:manuscript_id>/', views.math_review, name='math_review'),
    path('full-review/<int:manuscript_id>/', views.full_review, name='full_review'),
    path('', TemplateView.as_view(template_name="index.html")),
    path('queue-status/', views.queue_status, name='queue_status'),
    path('favicon.ico', RedirectView.as_view(
        url=staticfiles_storage.url('favicon.ico')), name='favicon'),
    path('save-feedback/', save_feedback, name='save-feedback'),
    path('review-progress/<int:manuscript_id>/', views.review_progress, name='review_progress'),
    path('compare-review/<str:manuscript_id>/', views.compare_review, name='compare_review'),
    path('compare-progress/<str:manuscript_id>/', views.compare_progress, name='compare_progress'),
    path('sitemap.xml', serve_sitemap, name='serve_sitemap'),
    path('api/health/', views.health_check, name='health_check'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('test-upload/', views.test_upload_page, name='test_upload_page'),
    path('debug/', views.debug_environment, name='debug_environment'),
    path('debug-form/', views.debug_form, name='debug_form'),
    path('presigned-test/', views.presigned_upload_test, name='presigned_upload_test'),
    path('direct-test/', views.direct_test, name='direct_test'),
    path('get-upload-params/', views.get_upload_params, name='get_upload_params'),
    path('register-uploaded-file/', views.register_uploaded_file, name='register_uploaded_file'),
    path('react-test/', views.react_test, name='react_test'),
    path('console-fix/', views.console_fix, name='console_fix'),
]

#urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    

