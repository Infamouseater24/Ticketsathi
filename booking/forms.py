from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter email'
    }))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'First Name'
    }))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Last Name'
    }))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number'
    }))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

class BulkShowtimeForm(forms.Form):
    from .models import Screen, Movie
    movie = forms.ModelChoiceField(queryset=Movie.objects.all(), required=True)
    screen = forms.ModelChoiceField(queryset=Screen.objects.all(), required=True)
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    show_times = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'e.g. 10:00, 14:30, 18:00', 'rows': 3}),
        help_text="Comma-separated times in HH:MM format",
        required=True
    )
    price = forms.DecimalField(max_digits=6, decimal_places=2, initial=300.00)

class BulkSeatForm(forms.Form):
    rows = forms.IntegerField(min_value=1, initial=10, help_text="Number of rows (A, B, C...)")
    seats_per_row = forms.IntegerField(min_value=1, initial=10, help_text="Number of seats in each row")