# id_card_generator/api/forms.py

from django import forms
from .models import IDCard, IDCardFormat, PDFUpload, IDCardData



class UploadPDFForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']

class UploadPANForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']

class UploadelectionForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']

class UploadAyushmanForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']

class UploadEshramForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']


class UploadAbhaForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']


class UploadaadhaarForm(forms.ModelForm):
    password = forms.CharField(max_length=100, required=False, widget=forms.PasswordInput)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file', 'password']









class IDCardForm(forms.ModelForm):
    class Meta:
        model = IDCard
        fields = ['id_number', 'name', 'photo', 'id_format', 'vendor', 'dob', 'expiry_date', 'card_number']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise forms.ValidationError('Please enter a valid date.')
        return dob

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if not expiry_date:
            raise forms.ValidationError('Please enter a valid date.')
        return expiry_date



class IDCardDataForm(forms.ModelForm):
    class Meta:
        model = IDCardData
        fields = ['data']  # Add your actual fields here

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request:
            instance.user = self.request.user  # Set the user here

            # Get the ID card ID from the request
            id_card_id = self.request.POST.get('id_card_id')
            try:
                id_card = IDCard.objects.get(id=id_card_id)
                instance.id_card = id_card
                instance.vendor = id_card.vendor  # Set vendor from the IDCard
            except IDCard.DoesNotExist:
                raise forms.ValidationError("ID Card does not exist.")

        if commit:
            instance.save()
        return instance
