from django import template
from django.urls import reverse
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def affiliate_url(context, url=None, ref_code=None):
    """
    Génère un URL d'affiliation pour l'utilisateur courant ou un code spécifique.
    """
    request = context["request"]

    # Récupérer le code de référence
    if ref_code is None and request.user.is_authenticated:
        ref_code = request.user.referral_code

    if ref_code is None:
        return url if url else request.build_absolute_uri("/")

    # Construire l'URL
    if url is None:
        url = request.build_absolute_uri("/")
    elif not url.startswith("http"):
        if url.startswith("/"):
            url = request.build_absolute_uri(url)
        else:
            try:
                url = request.build_absolute_uri(reverse(url))
            except Exception:
                url = request.build_absolute_uri("/" + url)

    # Ajouter le paramètre de référence
    ref_param = getattr(settings, "AFFILIATE_REF_PARAM", "ref")
    separator = "&" if "?" in url else "?"

    return f"{url}{separator}{ref_param}={ref_code}"


@register.simple_tag(takes_context=True)
def affiliate_share_links(context, url=None, ref_code=None):
    """
    Génère des liens de partage pour médias sociaux avec code d'affiliation.
    """
    # Construire l'URL d'affiliation
    aff_url = affiliate_url(context, url, ref_code)
    site_name = context.get("site_name", "EscortDollars")
    title = context.get("share_title", f"Rejoignez {site_name}")

    return {
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={aff_url}",
        "twitter": f"https://twitter.com/intent/tweet?url={aff_url}&text={title}",
        "whatsapp": f"https://wa.me/?text={title}%20{aff_url}",
        "email": f"mailto:?subject={title}&body=Découvrez {site_name}:%20{aff_url}",
        "copy": aff_url,
    }


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def status_color(status):
    """
    Retourne la classe de couleur Bootstrap appropriée pour le statut
    """
    status_colors = {
        "pending": "warning",
        "approved": "success",
        "rejected": "danger",
        "paid": "success",
        "cancelled": "danger",
    }
    return status_colors.get(status, "secondary")
