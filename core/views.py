from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Contact, News, HeroBanner, Category, CategoryService, ServicesCards, Job, JobApplication, ServiceFeedback, Footer
from django.views import View
from datetime import datetime
from django.core.paginator import Paginator
import re
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from accounts.utils import paginate_queryset
from accounts.utils import permission_required
from django.db.models.functions import Lower

# Create your views here.

from accounts.views import mainly_allowed_roles





class CategoryServicesAPIView(View):
    def get(self, request, category_id):
        services = CategoryService.objects.filter(category_id=category_id, s_title__isnull=False).values('id', 's_title').order_by('s_title')
        return JsonResponse({'services': list(services)})



class IndexView(View):
    def get(self, request):
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        banners = HeroBanner.objects.all().order_by('id')
        categories = Category.objects.all().order_by('title')
        services_cards = ServicesCards.objects.order_by(Lower('servicename'))
        jobs = Job.objects.all().order_by('title')
        feedbacks = ServiceFeedback.objects.all().order_by('-id')
        count_service = CategoryService.objects.count()
        
        q = request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            categories = categories.filter(Q(title__icontains=q) | Q(description__icontains=q))
            services_cards = services_cards.filter(Q(servicename__icontains=q))


        category_id = request.GET.get('category')
        service_id = request.GET.get('cat_service')

        # If both are selected, redirect to the services listing page
        if category_id and service_id:
            from django.urls import reverse
            from django.shortcuts import redirect
            url = reverse('category.services.listing',
                          kwargs={'pk': category_id})
            return redirect(f"{url}?service={service_id}")

        cat_services = CategoryService.objects.none()
        selected_category = None

        if category_id:
            selected_category = Category.objects.filter(id=category_id).first()
            cat_services = CategoryService.objects.filter(
                category_id=category_id
            ).order_by('s_title')
        elif q:
            # If searching, let's also grab matching cat_services for the first matched category to display
            if categories.exists():
                cat_services = CategoryService.objects.filter(category=categories.first()).order_by('s_title')
        context={
            'selected_category': selected_category,
            'footer': footer,
            'news': news,
            'banners': banners,
            'categories': categories,
            'services_cards': services_cards,
            'jobs': jobs,
            'feedbacks': feedbacks,
            'cat_services': cat_services,
            'count_service':count_service,
        }
        return render(request, 'index.html',context )




class ServicesListView(View):

    def get(self, request, pk):

        footer = Footer.objects.first()

        news = News.objects.all().order_by(
                'id'
            )

        # CATEGORY
        selected_category = get_object_or_404(
                Category,
                pk=pk
            )

        # SERVICE ID
        service_id = request.GET.get(
                'service'
            )

        # ALL SERVICES
        category_services = CategoryService.objects.filter(
                category=selected_category
            ).order_by(
                's_title'
            )

        # FILTER SINGLE SERVICE
        if service_id:

            category_services = category_services.filter(
                    id=service_id
                )

        # PAGINATION
        paginator = Paginator(category_services,3)

        page_number = request.GET.get(
                'page'
            )

        category_servicess = paginator.get_page(
                page_number
            )

        context = {

            'selected_category':
                selected_category,

            'category_servicess':
                category_servicess,

            'category_services':
                CategoryService.objects.filter(
                    category=selected_category
                ),

            'footer':
                footer,

            'news':
                news,

        }

        return render(request,'serviceslist.html',context)
        
        

class Joblisting(View):
    def get(self,request):
        jobs = Job.objects.all().order_by('title')
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        context={'footer':footer,
                 'news':news,
                 'jobs':jobs
                 }
        return render(request, 'joblisting.html',context)
 
 
 
  
class CategoryListing(View):
    def get(self,request):
        categories = Category.objects.all().order_by('title')
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        context={'footer':footer,
                 'news':news,
                 'categories':categories
                 }
        return render(request, 'category_listing.html',context )




class ContactForm(View):
    def get(self, request):
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        context={
            'footer': footer,
            'news': news
        }
        return render(request, 'contact.html',context )

    def post(self, request):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        city = request.POST.get('city', '').strip()
        message = request.POST.get('message', '').strip()

        errors = {}

        if not name:
            errors['name'] = "Name is required"

        if not email:
            errors['email'] = "Email is required"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors['email'] = "Invalid email format"

        if not phone:
            errors['phone'] = "Phone number is required"
        elif not re.match(r"^[6-9]\d{9}$", phone):
            errors['phone'] = "Enter valid 10-digit phone number"

        if not city:
            errors['city'] = "City is required"

        if not message:
            errors['message'] = "Message cannot be empty"

        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        context={
                'errors': errors,
                'old': request.POST,
                'footer': footer,
                'news': news
            }
        if errors:
            return render(request, 'contact.html',context )

        Contact.objects.create(
            name=name,
            email=email,
            phone=phone,
            city=city,
            message=message,
            status='pending'
        )

        messages.success(request, "Your request submitted successfully!")

        return redirect('contact')


@method_decorator(permission_required('core.view_contact'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ContactListView(LoginRequiredMixin,View):
    def get(self, request):
        contacts = Contact.objects.all().order_by('-contact_created_at')
        page_obj = paginate_queryset(request, contacts, 10)

        return render(request, 'pages/contact/list.html', {
            'contacts': page_obj,
            'page_obj': page_obj
        })

@method_decorator(permission_required('core.change_contact'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ContactUpdateView(LoginRequiredMixin,View):
    def get(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        return render(request, 'pages/contact/update.html', {
            'contact': contact
        })

    def post(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)

        status = request.POST.get('status')

        if not status:
            messages.error(request, "Status is required")
            return redirect('contact.update', pk=pk)

        contact.status = status
        contact.save()

        messages.success(request, "Status updated successfully!")
        return redirect('list.contact')


@method_decorator(permission_required('core.delete_contact'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteContact(LoginRequiredMixin,View):
    def get(self, request, pk):
        conatct = get_object_or_404(Contact, pk=pk)
        conatct.delete()
        messages.success(request, "Contact  deleted")
        return redirect('list.contact')


@method_decorator(never_cache, name='dispatch')
class FeedbackForm(LoginRequiredMixin,View):

    def get(self, request):
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        return render(request, 'feedback.html', {'footer': footer, 'news': news})

    def post(self, request):

        service_name = request.POST.get('service_name')
        customer_name = request.POST.get('customer_name')
        customer_type = request.POST.get('customer_type')
        rating = request.POST.get('rating')
        description = request.POST.get('description')
        image = request.FILES.get('image')

        if not service_name:
            messages.error(request, "Service name is required")
            return redirect('feedbackform')

        if not customer_name:
            messages.error(request, "Customer name is required")
            return redirect('feedbackform')

        if not customer_type or customer_type == "Select Type":
            messages.error(request, "Please select customer type")
            return redirect('feedbackform')

        if not rating:
            messages.error(request, "Please select rating")
            return redirect('feedbackform')

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                messages.error(request, "Invalid rating value")
        except:
            messages.error(request, "Invalid rating value")
            return redirect('feedbackform')

        if not description:
            messages.error(request, "Description is required")
            return redirect('feedbackform')

        ServiceFeedback.objects.create(
            service_name=service_name,
            customer_name=customer_name,
            customer_type=customer_type,
            rating=rating,
            description=description,
            image=image
        )

        messages.success(request, "Feedback submitted successfully")

        return redirect('feedbackform')


@method_decorator(permission_required('core.view_servicefeedback'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListFeedback(LoginRequiredMixin,View):
    def get(self, request):
        feedbacks = ServiceFeedback.objects.all().order_by('-feedback_created_at')
        page_obj = paginate_queryset(request, feedbacks, 10)
        return render(request, 'pages/feedback/list.html', {
            'feedbacks': page_obj,
            'page_obj': page_obj,
            
        })


@method_decorator(permission_required('core.delete_servicefeedback'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteFeedback(LoginRequiredMixin,View):
    def get(self, request, id):
        feebback = get_object_or_404(ServiceFeedback, id=id)
        feebback.delete()
        messages.success(request, "feedback deleted")
        return redirect('list.feedback')




@method_decorator(never_cache, name='dispatch')
@method_decorator(permission_required('core.view_news'),name='dispatch')
class NewsListView(LoginRequiredMixin,View):

    def get(self, request):

        news = News.objects.all().order_by('-news_created_at')

        # PAGINATION
        page_obj = paginate_queryset(request, news, 10)

        return render(request,'pages/news/list_news.html',
            {
                'news': page_obj,
                'page_obj': page_obj
            }
        )


@method_decorator(never_cache, name='dispatch')
@method_decorator(permission_required('core.add_news'),name='dispatch')
class CreateNews(LoginRequiredMixin,View):
    def get(self, request):
        return render(request, 'pages/news/create_news.html')

    def post(self, request):
        news_headline = request.POST.get('news_headline')

        news = News.objects.create(
            content=news_headline

        )
        news.save()
        messages.success(request,"News created successfully")
        return redirect('news.list')
    
    


@method_decorator(never_cache, name='dispatch')
@method_decorator(permission_required('core.change_news'),name='dispatch')
class UpdateNews(LoginRequiredMixin,View):

    def get(self, request, pk):
        news = get_object_or_404(News, pk=pk)
        return render(request, 'pages/news/update_news.html', {'news': news})

    def post(self, request, pk):
        news = get_object_or_404(News, pk=pk)

        news.content = request.POST.get('update_headline')
        news.create_date = datetime.now()
        news.save()
        messages.success(request,"News Updated successfully")

        return redirect('news.list')



@method_decorator(never_cache, name='dispatch')
@method_decorator(permission_required('core.delete_news'),name='dispatch')
class DeleteNews(LoginRequiredMixin,View):
    def get(self, request, pk):
        news = get_object_or_404(News, pk=pk)
        news.delete()
        messages.error(request,"News Deeleted ")
        return redirect('news.list')


@method_decorator(permission_required('core.view_herobanner'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListBanner(LoginRequiredMixin,View):
    def get(self, request):
        banner = HeroBanner.objects.all().order_by("-id")
        page_obj = paginate_queryset(request, banner, 10)
        return render(request,'pages/hero_section/list_banner.html',
            {
                'banner': page_obj,
                'page_obj': page_obj
            }
        )

@method_decorator(permission_required('core.add_herobanner'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateBanner(LoginRequiredMixin,View):
    def get(self, request):
        return render(request, 'pages/hero_section/create_banner.html')

    def post(self, request):
        image = request.FILES.get('image')
        heading = request.POST.get('heading')
        sub_heading = request.POST.get('sub_heading')
        banner_save = HeroBanner.objects.create(
            heading=heading,
            sub_heading=sub_heading,
            image=image
        )
        banner_save.save()
        messages.success(request,"Created banner successfully")

        return redirect("list.banner")

@method_decorator(permission_required('core.change_herobanner'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateBanner(LoginRequiredMixin,View):

    def get(self, request, pk):
        banner = get_object_or_404(HeroBanner, pk=pk)
        return render(request, 'pages/hero_section/update_banner.html', {'banner': banner})

    def post(self, request, pk):
        banner = get_object_or_404(HeroBanner, pk=pk)

        banner.heading = request.POST.get('heading')
        banner.sub_heading = request.POST.get('sub_heading')

        image = request.FILES.get('image')
        if image:
            banner.image = image

        banner.save()
        messages.error(request,"Updated banner successfully")

        return redirect('list.banner')

@method_decorator(permission_required('core.delete_herobanner'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteBanner(LoginRequiredMixin,View):
    def get(self, request, pk):
        banner = get_object_or_404(HeroBanner, pk=pk)
        banner.delete()
        messages.error(request,"deleted banner successfully")
        return redirect('list.banner')


@method_decorator(permission_required('core.view_category'),name='dispatch')
class ListCategory(View):
    def get(self, request):
        categories = Category.objects.all().order_by('-category_created_at')

        paginator = Paginator(categories, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'pages/categories/list.html', {
            'categories': page_obj,
            'page_obj': page_obj
        })

@method_decorator(permission_required('core.add_category'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateCategory(LoginRequiredMixin,View):
    def get(self, request):
        return render(request, 'pages/categories/create.html')

    def post(self, request):
        icon = request.FILES.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        badge = request.POST.get('badge')
        tags = request.POST.get('tags')
        category_about_des = request.POST.get('category_about_des')
        banner_img = request.FILES.get('banner_image')
        category_about_img = request.FILES.get('category_about_img')

        Category.objects.create(
            icon=icon,
            title=title,
            description=description,
            badge=badge,
            tags=tags,
            category_about_des=category_about_des,
            category_about_img=category_about_img,
            banner_image=banner_img,
        )
        messages.success(request,"Created category successfully")
        return redirect('list.category')


@method_decorator(permission_required('core.change_category'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateCategory(LoginRequiredMixin,View):

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return render(request, 'pages/categories/update.html', {
            'category': category
        })

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)

        # Text fields
        category.title = request.POST.get('title')
        category.description = request.POST.get('description')
        category.badge = request.POST.get('badge')
        category.tags = request.POST.get('tags')
        category.category_about_des = request.POST.get('category_about_des')

        # Image fields (ONLY update if new file uploaded)
        if request.FILES.get('icon'):
            category.icon = request.FILES.get('icon')

        if request.FILES.get('category_about_img'):
            category.category_about_img = request.FILES.get(
                'category_about_img')

        if request.FILES.get('banner_image'):
            category.banner_image = request.FILES.get('banner_image')

        category.save()
        messages.success(request,"Updated Category successfully")

        return redirect('list.category')


@method_decorator(permission_required('core.delete_category'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteCaregory(LoginRequiredMixin,View):
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        messages.error(request,"Deleted Category")
        return redirect('list.category')


@method_decorator(permission_required('core.view_categoryservice'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListCategoryService(LoginRequiredMixin,View):
    def get(self, request):
        categories = Category.objects.all()

        category_id = request.GET.get('category')
        selected_category = None
        services = CategoryService.objects.none()

        # if category selected
        if category_id:
            selected_category = Category.objects.filter(id=category_id).first()

            if selected_category:
                services = CategoryService.objects.filter(
                    category=selected_category
                ).order_by('-categoryservice_created_at')

        paginator = Paginator(services, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'pages/categoryservice/list.html', {
            'categories': categories,
            'selected_category': selected_category,
            'services': page_obj,   # use paginated object
            'page_obj': page_obj,
        })



@method_decorator(permission_required('core.add_categoryservice'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateCategoryService(LoginRequiredMixin,View):

    def get(self, request):
        categories = Category.objects.all()
        return render(request, 'pages/categoryservice/create.html', {
            'categories': categories
        })

    def post(self, request):
        category_id = request.POST.get('category')

        if not category_id:
            return redirect('add.categories.service')

        category = get_object_or_404(Category, id=category_id)

        CategoryService.objects.create(
            category=category,
            s_tag=request.POST.get('s_tag'),
            s_title=request.POST.get('s_title'),
            s_desc=request.POST.get('s_desc'),
            image=request.FILES.get('image')
        )
        messages.success(request,"Created Category Services successfully")

        if 'save_add_more' in request.POST:
            return redirect('add.categories.service')

        return redirect('list.category.services')



@method_decorator(permission_required('core.change_categoryservice'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateCategoryService(LoginRequiredMixin,View):
    def get(self, request, id):
        services = get_object_or_404(CategoryService, id=id)
        return render(request, 'pages/categoryservice/update.html', {'services': services})

    def post(self, request, id):
        services = get_object_or_404(CategoryService, id=id)

        services.s_tag = request.POST.get('s_tag')
        services.s_title = request.POST.get('s_title')
        services.s_desc = request.POST.get('s_desc')
        image = request.FILES.get('image')
        if image:
            services.image = image
        services.save()
        messages.success(request,"Updated Category Services successfully")
        return redirect('list.category.services')



@method_decorator(permission_required('core.delete_categoryservice'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteCategoryService(LoginRequiredMixin,View):
    def get(self, request, id):
        service = get_object_or_404(CategoryService, id=id)
        service.delete()
        messages.error(request,"Deleted Category Services")
        return redirect('list.category.services')



@method_decorator(permission_required('core.view_servicescards'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListServices(LoginRequiredMixin,View):
    def get(self, request):
        services = ServicesCards.objects.all().order_by('-id')
        page_obj = paginate_queryset(request,services,10)
        return render(request, 'pages/services/list.html', {'services': page_obj,'page_obj': page_obj,})


@method_decorator(permission_required('core.add_servicescards'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateService(LoginRequiredMixin,View):
    def get(self, request):
        return render(request, 'pages/services/create.html')

    def post(self, request):
        servicename = request.POST.get('servicename')
        serviceicon = request.FILES.get('serviceicon')
        service_image = request.FILES.get('service_image')

        ServicesCards.objects.create(
            servicename=servicename,
            serviceicon=serviceicon,
            service_image=service_image,
        )
        messages.success(request,"Created Service successfully")
        if 'save_add_more' in request.POST:
            return redirect('add.services')
        

        return redirect('services.list')


@method_decorator(permission_required('core.change_servicescards'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateServices(LoginRequiredMixin,View):
    def get(self, request, id):
        services = get_object_or_404(ServicesCards, id=id)
        return render(request, 'pages/services/update.html', {'services': services})

    def post(self, request, id):
        services = get_object_or_404(ServicesCards, id=id)
        services.servicename = request.POST.get('servicename')

        if request.FILES.get('serviceicon'):
            services.serviceicon = request.FILES.get('serviceicon')
        if request.FILES.get('service_image'):
            services.service_image = request.FILES.get('service_image')
        services.save()
        messages.success(request,"Updated Service successfully")
        return redirect('services.list')


@method_decorator(permission_required('core.delete_servicescards'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteServices(LoginRequiredMixin,View):
    def get(self, request, id):
        services = get_object_or_404(ServicesCards, id=id)
        services.delete()
        messages.error(request,"Service Deleted")
        return redirect('services.list')


@method_decorator(permission_required('core.view_job'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListJobs(LoginRequiredMixin, View):

    def get(self, request):

        jobs = Job.objects.all().order_by('-job_created_at')

        page_obj = paginate_queryset(request, jobs, 10)

        return render(
            request,
            'pages/jobs/list.html',
            {
                'jobs': page_obj,
                'page_obj': page_obj,
            }
        )


@method_decorator(permission_required('core.add_job'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateJob(LoginRequiredMixin,View):

    def get(self, request):
        return render(request, 'pages/jobs/create.html')

    def post(self, request):
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status')
        job_type = request.POST.get('job_type')
        work_mode = request.POST.get('work_mode')
        icon = request.FILES.get('icon')

        if not title or not description:
            messages.error(request, "Title and Description are required")
            return render(request, 'pages/jobs/create.html')

        Job.objects.create(
            title=title,
            description=description,
            status=status,
            job_type=job_type,
            work_mode=work_mode,
            icon=icon,
        )

        messages.success(request, "Job created successfully!")

        return redirect('list.jobs')


@method_decorator(permission_required('core.change_job'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateJob(LoginRequiredMixin,View):
    def get(self, request, id):
        job = get_object_or_404(Job, id=id)
        return render(request, 'pages/jobs/update.html', {'job': job})

    def post(self, request, id):
        job = get_object_or_404(Job, id=id)

        job.title = request.POST.get('title')
        job.description = request.POST.get('description')
        job.status = request.POST.get('status')
        job.job_type = request.POST.get('job_type')
        job.work_mode = request.POST.get('work_mode')

        if request.FILES.get('icon'):
            job.icon = request.FILES.get('icon')

        job.save()
        messages.success(request, "Job Updated successfully!")

        return redirect('list.jobs')

@method_decorator(permission_required('core.delete_job'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteJob(LoginRequiredMixin,View):
    def get(self, request, id):
        job = get_object_or_404(Job, id=id)
        job.delete()
        messages.error(request, "Deleted Job!")
        return redirect('list.jobs')
    
    
    

class JobApplications(View):

    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        return render(request, 'jobapply.html', {'job': job,'footer':footer,'news':news})

    def post(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        footer = Footer.objects.first()
        news = News.objects.all().order_by('id')
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        experience = request.POST.get('experience')
        salary = request.POST.get('salary')
        address = request.POST.get('address')

        resume = request.FILES.get('resume')
        photo = request.FILES.get('photo')

        errors = {}

       
        if not name:
            errors['name'] = "Name is required"

        if not email or "@" not in email:
            errors['email'] = "Valid email required"

        if not phone or len(phone) < 10:
            errors['phone'] = "Valid phone required"

        if not experience:
            errors['experience'] = "Experience required"

        if not salary:
            errors['salary'] = "Expected salary required"

        if not address:
            errors['address'] = "Address required"

        if not photo:
            errors['photo'] = "photo required"

        if resume and not resume.name.endswith(('.pdf', '.doc', '.docx')):
            errors['resume'] = "Only PDF/DOC files allowed"

        if photo and not photo.name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            errors['photo'] = "Only image files allowed"

        if errors:
            return render(request, 'jobapply.html', {
                'job': job,
                'footer':footer,
                'news':news,
                'errors': errors
            })

        
        JobApplication.objects.create(
            job=job,
            name=name,
            email=email,
            phone=phone,
            experience=experience,
            expected_salary=salary,
            address=address,
            resume=resume,
            photo=photo
        )

        messages.success(request, "Application submitted successfully!")
        return redirect('job.apply', job_id=job.id)


@method_decorator(permission_required('core.view_jobapplication'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminJobApplicationsView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):

        if request.user.role not in mainly_allowed_roles:

            return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)


    def get(self, request):

        applications = JobApplication.objects.select_related(
            "job"
        ).order_by("-id")


        q = request.GET.get("q")


        if q:

            applications = applications.filter(
                Q(name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q) |
                Q(job__title__icontains=q)
            )


        page_obj = paginate_queryset(request,applications,10)

        context=            {
                "applications": page_obj,
                "page_obj": page_obj,
                "q": q,
            }
        return render(request,"admin/job_applications.html",context)


@method_decorator(permission_required('core.view_footer'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ListFooter(LoginRequiredMixin,View):
    def get(self, request):
        footers = Footer.objects.all().order_by('-id')
        page_obj = paginate_queryset(request, footers, 10)
        return render(request, 'pages/footer/list.html', {
            'footers': page_obj,
            'page_obj': page_obj
        })


@method_decorator(permission_required('core.add_footer'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CreateFooter(LoginRequiredMixin,View):

    def get(self, request):
        return render(request, 'pages/footer/create.html')

    def post(self, request):
        logo_image = request.FILES.get('logo_image')
        cart_image = request.FILES.get('cart_image')
        footer_description = request.POST.get('footer_description')
        phone_num = request.POST.get('phone_num')
        whatsapp_num = request.POST.get('whatsapp_num')
        email = request.POST.get('email')
        address = request.POST.get('address')

        facebook = request.POST.get('facebook')
        instagram = request.POST.get('instagram')
        twitter = request.POST.get('twitter')
        whatsapp = request.POST.get('whatsapp')

        errors = []

        if not footer_description:
            errors.append("Footer description is required")

        if not phone_num:
            errors.append("Phone number is required")

        if not whatsapp_num:
            errors.append("WhatsApp number is required")

        if not email:
            errors.append("Email is required")

        if not address:
            errors.append("Address is required")

        if errors:
            for error in errors:
                messages.error(request, error)

            return render(request, 'pages/footer/create.html')

        Footer.objects.create(
            logo_image=logo_image,
            cart_image=cart_image,
            footer_description=footer_description,
            phone_num=phone_num,
            whatsapp_num=whatsapp_num,
            email=email,
            address=address,
            facebook=facebook,
            instagram=instagram,
            twitter=twitter,
            whatsapp=whatsapp,
        )

        messages.success(request, "Footer created successfully ")
        return redirect('list.footer')
    
    
@method_decorator(permission_required('core.change_footer'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UpdateFooter(LoginRequiredMixin,View):

    def get(self, request, id):
        footer = get_object_or_404(Footer, id=id)
        return render(request, 'pages/footer/update.html', {'footer': footer})

    def post(self, request, id):
        footer = get_object_or_404(Footer, id=id)

        logo_image = request.FILES.get('logo_image')
        cart_image = request.FILES.get('cart_image')
        footer_description = request.POST.get('footer_description')
        phone_num = request.POST.get('phone_num')
        whatsapp_num = request.POST.get('whatsapp_num')
        email = request.POST.get('email')
        address = request.POST.get('address')

        facebook = request.POST.get('facebook')
        instagram = request.POST.get('instagram')
        twitter = request.POST.get('twitter')
        whatsapp = request.POST.get('whatsapp')

        errors = []

        if not footer_description:
            errors.append("Footer description is required")

        if not phone_num:
            errors.append("Phone number is required")

        if not whatsapp_num:
            errors.append("WhatsApp number is required")

        if not email:
            errors.append("Email is required")

        if not address:
            errors.append("Address is required")

        if errors:
            for error in errors:
                messages.error(request, error)

            return render(request, 'pages/footer/update.html', {'footer': footer})

        footer.footer_description = footer_description
        footer.phone_num = phone_num
        footer.whatsapp_num = whatsapp_num
        footer.email = email
        footer.address = address

        footer.facebook = facebook
        footer.instagram = instagram
        footer.twitter = twitter
        footer.whatsapp = whatsapp

        if logo_image:
            footer.logo_image = logo_image
        if cart_image:
            footer.cart_image = cart_image

        footer.save()

        messages.success(request, "Footer updated successfully ")
        return redirect('list.footer')

@method_decorator(permission_required('core.delete_footer'),name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DeleteFooter(LoginRequiredMixin,View):
    def get(self, request, id):
        footer = get_object_or_404(Footer, id=id)
        footer.delete()
        messages.success(request, 'footer item deleted successfully')
        return redirect('list.footer')




class PrivacyPolicyView(View):

    def get(self, request):

        return render(request,
            "privacy_policy.html"
        )
        

