from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from django.contrib.auth import logout
# Create your views here.


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    data = {
        'form':form
    }
    return render(request, "accounts/signup.html", data)


# def user_logout(request):
#     logout(request)
#     return redirect("login")
