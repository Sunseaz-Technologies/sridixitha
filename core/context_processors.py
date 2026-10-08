from accounts.models import Cart
from core.models import Footer

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = cart.total_items
        except Cart.DoesNotExist:
            pass
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key)
                count = cart.total_items
            except Cart.DoesNotExist:
                pass
                
    footer = Footer.objects.first()
    return {
        'cart_count': count,
        'footer': footer
    }
