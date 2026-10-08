import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models import CategoryService
from .models import Cart, CartItem, Booking, BookingItem

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
        return cart

class AddToCartView(View):
    def post(self, request, *args, **kwargs):
        service_id = request.POST.get('service_id')
        if not service_id:
            try:
                data = json.loads(request.body)
                service_id = data.get('service_id')
            except:
                pass

        if not service_id:
            return JsonResponse({'status': 'error', 'message': 'Service ID is required'}, status=400)

        service = get_object_or_404(CategoryService, id=service_id)
        cart = get_or_create_cart(request)
        
        # Check if already in cart
        if CartItem.objects.filter(cart=cart, service=service).exists():
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'redirect',
                    'url': '/login/?next=/cart/'
                })
            return JsonResponse({'status': 'error', 'message': 'Service is already in your cart', 'cart_count': cart.total_items})
        
        # Add to cart
        CartItem.objects.create(cart=cart, service=service)
            
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'redirect',
                'url': '/login/?next=/cart/'
            })

        return JsonResponse({'status': 'success', 'message': f'{service.s_title} added to cart', 'cart_count': cart.total_items})

class RemoveFromCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        item_id = request.POST.get('item_id')
        if not item_id:
            try:
                data = json.loads(request.body)
                item_id = data.get('item_id')
            except:
                pass

        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()

        return JsonResponse({'status': 'success', 'message': 'Service removed from cart', 'cart_count': cart.total_items})

class ClearCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        return JsonResponse({'status': 'success', 'message': 'Cart cleared', 'cart_count': 0})

class CartView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        items = cart.items.select_related('service').all()
        context = {
            'cart': cart,
            'items': items,
        }
        return render(request, 'cart/cart_page.html', context)

class CheckoutView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        if cart.total_items == 0:
            return redirect('cart_view')
            
        context = {
            'items': cart.items.select_related('service').all(),
            'user': request.user
        }
        return render(request, 'cart/checkout.html', context)

    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        if cart.total_items == 0:
            return redirect('cart_view')

        name = request.POST.get('name')
        phone = request.POST.get('phone')
        city = request.POST.get('city')
        area = request.POST.get('area', '')
        pincode = request.POST.get('pincode', '')
        base_address = request.POST.get('address', '')
        problem = request.POST.get('problem', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        scheduled_time = request.POST.get('scheduled_time')

        # Combine address fields
        full_address = base_address
        if area:
            full_address += f", Area: {area}"
        if pincode:
            full_address += f", Pincode: {pincode}"

        if not all([name, phone, base_address, start_date]):
            context = {
                'items': cart.items.all(),
                'error': 'Name, Phone, Address and Start Date are required.'
            }
            return render(request, 'cart/checkout.html', context)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Find matched admin based on city
        matched_admin = User.objects.filter(
            role="admin",
            city__iexact=city,
            is_active=True
        ).first()

        created_bookings = []
        for item in cart.items.all():
            service = item.service
            category = service.category if hasattr(service, 'category') else None

            # Find matching vendor if any
            vendor = User.objects.filter(
                role="vendor",
                services=service
            ).first()

            # Create Booking
            booking = Booking.objects.create(
                user=request.user,
                admin=matched_admin,
                name=name,
                phone=phone,
                city=city,
                address=full_address,
                problem=problem,
                status='pending',
                service=service,
                category=category,
                vendor=vendor,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else start_date,
                scheduled_date=start_date if start_date else None,
                scheduled_time=scheduled_time if scheduled_time else None
            )

            # Move CartItem to BookingItem
            BookingItem.objects.create(
                booking=booking,
                service=service,
                vendor=vendor,
                status='pending',
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else start_date,
                scheduled_date=start_date if start_date else None,
                scheduled_time=scheduled_time if scheduled_time else None,
            )
            created_bookings.append(booking)

        # Clear cart
        cart.items.all().delete()

        # Redirect to the first booking's success page or my_bookings if empty
        if created_bookings:
            return redirect('booking_success', booking_id=created_bookings[0].id)
        return redirect('my_bookings')

class BookingSuccessView(LoginRequiredMixin, View):
    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        context = {
            'booking': booking
        }
        return render(request, 'cart/booking_success.html', context)
