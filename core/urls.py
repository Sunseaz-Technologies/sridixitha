from django.urls import path
from core.views import *

urlpatterns = [
     
    path("", IndexView.as_view(), name="indexpage"),
    path("categories/listing/",CategoryListing.as_view(),name='categoy.listings'),
    
    path('sridixitha/servicespagelist/<int:pk>/',
         ServicesListView.as_view(), name='category.services.listing'),
    # New AJAX endpoint
     path('api/category/<int:category_id>/services/',CategoryServicesAPIView.as_view(),name='category.services.api'),


    path('sridixitha/contact/', ContactForm.as_view(), name='contact'),
    path('list/contact/', ContactListView.as_view(), name='list.contact'),
    path('update/conatct/<int:pk>/',
         ContactUpdateView.as_view(), name='update.contact'),
    path('delete/contact/<int:pk>/',
         DeleteContact.as_view(), name='delete.contact'),


    path("sridixitha/feebackform/", FeedbackForm.as_view(), name='feedbackform'),


    path("list/news/", NewsListView.as_view(), name="news.list"),
   
    path("create/", CreateNews.as_view(), name="createnews"),
    path("update/news/<int:pk>/", UpdateNews.as_view(), name="update.news"),
    path("delete/news/<int:pk>/", DeleteNews.as_view(), name="delete.news"),



    path("list/banner/", ListBanner.as_view(), name="list.banner"),
    path("create/banner/", CreateBanner.as_view(), name="create.banner"),
    path("update/banner/<int:pk>/", UpdateBanner.as_view(), name="update.banner"),
    path('delete/banner/<int:pk>/', DeleteBanner.as_view(), name="delete.banner"),

    path('create/category/', CreateCategory.as_view(), name="create.category"),
    path('list/category/', ListCategory.as_view(), name="list.category"),
    path('update/category/<int:pk>/',
         UpdateCategory.as_view(), name="update.category"),
    path('delete/category/<int:pk>/',
         DeleteCaregory.as_view(), name="delete.category"),

    path('add/category/service/', CreateCategoryService.as_view(),
         name='add.categories.service'),
    path('list/category/services', ListCategoryService.as_view(),
         name='list.category.services'),
    path('update/category/services/<int:id>/',
         UpdateCategoryService.as_view(), name='update.category.services'),
    path('delete/category/severice/<int:id>/',
         DeleteCategoryService.as_view(), name='delete.category.services'),


    path('list/services/', ListServices.as_view(), name="services.list"),
    path('create/services/', CreateService.as_view(), name="add.services"),
    path('update/services/<int:id>/',
         UpdateServices.as_view(), name='update.services'),
    path('delete/services/<int:id>/',
         DeleteServices.as_view(), name='delete.services'),


    path('list/jobs/', ListJobs.as_view(), name='list.jobs'),
    path('create/jobs/', CreateJob.as_view(), name='add.jobs'),
    path('update/jobs/<int:id>/', UpdateJob.as_view(), name='update.jobs'),
    path('delete/jobs/<int:id>/', DeleteJob.as_view(), name='delete.jobs'),


    path('apply/job/<int:job_id>/', JobApplications.as_view(), name='job.apply'),
    path('job/listing/',Joblisting.as_view(),name='jobs.listing'),

    path('list/feedback/', ListFeedback.as_view(), name='list.feedback'),
    path('delete/feedback/<int:id>/',
         DeleteFeedback.as_view(), name='delete.feedback'),

    path('list/footer/', ListFooter.as_view(), name='list.footer'),
    path('cretae/footer/', CreateFooter.as_view(), name='create.footer'),
    path('update/footer/<int:id>/', UpdateFooter.as_view(), name='update.footer'),
    path('delete/footer/<int:id>/', DeleteFooter.as_view(), name='delete.footer'),
    path("job-applications/",AdminJobApplicationsView.as_view(),name="admin_job_applications"),
    path("privacy-policy/",PrivacyPolicyView.as_view(),name="privacy_policy"),
]
