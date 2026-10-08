import requests as http_requests
from user_agents import parse as ua_parse
from .models import Visitor


class VisitorTrackingMiddleware:
    """
    Tracks every anonymous (non-logged-in) visitor.
    Logged-in users (any role) are skipped.
    Saves: IP, country, state, city, browser, device, OS, page URL.
    """

    # Skip these paths — admin static, media, ajax, api
    SKIP_PATHS = (
        "/admin/",
        "/static/",
        "/media/",
        "/favicon.ico",
        "/api/",
        "/login/",
        "/logout/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ── Skip logged-in users (superadmin, admin, vendor, customer, etc.)
        if request.user.is_authenticated:
            return response

        # ── Skip unwanted paths
        path = request.path
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return response

        # ── Skip AJAX / non-HTML requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return response

        # ── Get real IP (handles proxies / load balancers)
        ip = self._get_ip(request)
        if not ip or ip in ("127.0.0.1", "::1"):
            return response

        # ── Parse User-Agent
        ua_string = request.META.get("HTTP_USER_AGENT", "")
        ua         = ua_parse(ua_string)

        browser = ua.browser.family  or "Unknown"
        os_name = ua.os.family       or "Unknown"

        if ua.is_mobile:
            device = "Mobile"
        elif ua.is_tablet:
            device = "Tablet"
        elif ua.is_pc:
            device = "Desktop"
        else:
            device = "Unknown"

        # ── Geo-lookup via ip-api.com (free, no key needed)
        country = state = city = "Unknown"
        try:
            geo = http_requests.get(
                f"http://ip-api.com/json/{ip}?fields=country,regionName,city,status",
                timeout=2,
            ).json()

            if geo.get("status") == "success":
                country = geo.get("country",    "Unknown")
                state   = geo.get("regionName", "Unknown")
                city    = geo.get("city",        "Unknown")

        except Exception:
            pass  # geo lookup failed — still save the visit

        # ── Save or update visitor record (unique per IP)
        try:
            Visitor.objects.update_or_create(
                ip_address=ip,
                defaults={
                    "country":          country,
                    "state":            state,
                    "city":             city,
                    "browser":          browser,
                    "device":           device,
                    "operating_system": os_name,
                    "page_url":         request.path,
                    # visited_at uses auto_now so it updates automatically
                },
            )
        except Exception:
            pass

        return response

    # ── Helper: extract real IP ───────────────────────────────────
    def _get_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")