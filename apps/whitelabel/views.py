from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WhiteLabel
from .forms import WhiteLabelForm


@login_required
def site_list(request):
    sites = WhiteLabel.objects.filter(owner=request.user)
    return render(request, "whitelabel/sites/list.html", {"sites": sites})


@login_required
def create_site(request):
    if request.method == "POST":
        form = WhiteLabelForm(request.POST, request.FILES)
        if form.is_valid():
            site = form.save(commit=False)
            site.owner = request.user
            site.save()
            messages.success(request, "White label site created successfully!")
            return redirect("whitelabel:sites")
    else:
        form = WhiteLabelForm()

    return render(request, "whitelabel/sites/create.html", {"form": form})


@login_required
def site_detail(request, pk):
    site = get_object_or_404(WhiteLabel, pk=pk, owner=request.user)
    return render(request, "whitelabel/sites/detail.html", {"site": site})


@login_required
def edit_site(request, pk):
    site = get_object_or_404(WhiteLabel, pk=pk, owner=request.user)
    if request.method == "POST":
        form = WhiteLabelForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "White label site updated successfully!")
            return redirect("whitelabel:site_detail", pk=site.pk)
    else:
        form = WhiteLabelForm(instance=site)

    return render(request, "whitelabel/sites/edit.html", {"form": form, "site": site})


@login_required
def delete_site(request, pk):
    site = get_object_or_404(WhiteLabel, pk=pk, owner=request.user)
    if request.method == "POST":
        site.delete()
        messages.success(request, "White label site deleted successfully!")
        return redirect("whitelabel:sites")

    return render(request, "whitelabel/sites/delete.html", {"site": site})
