#id_card_generator/api/views.py
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import User, Vendor, IDCardFormat, IDCard, Payment, Transaction, PDFUpload, IDCardData,  Wallet, ApiWallet
from .serializers import VendorSerializer, IDCardSerializer, TransactionSerializer
from .printer import get_connected_printers, Printer
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadPDFForm, IDCardForm, UploadPANForm, UploadelectionForm, UploadAyushmanForm, UploadEshramForm, UploadAbhaForm, UploadaadhaarForm
from django.contrib.auth.decorators import login_required
from .utils import extract_data_from_pdf, enhance_photo, generate_id_card_image, validate_date_format
from .pdf_processing import extract_data_from_pdf
from .pan_processing import extract_data_from_pan
from .election_processing import extract_data_from_election
from .ayushman_processing import extract_data_from_ayushman
from .eshram_processing import extract_data_from_eshram
from .abha_processing import extract_data_from_abha
from .aadhaar_processing import extract_data_from_aadhaar
from django.core.exceptions import ValidationError
from datetime import datetime
import base64
from django.contrib import messages  # Import the messages module
import logging

from decimal import Decimal
logger = logging.getLogger(__name__)
from datetime import date  # Add this import
from django.utils import timezone  # Import timezone for datetime handling


User = get_user_model()

def index(request):
    return HttpResponse("Welcome to the ID Card Generator API!")

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def top_up_wallet(self, request, pk=None):
        vendor = self.get_object()
        amount = request.data.get('amount', 0)
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        vendor.wallet_balance += float(amount)
        vendor.save()
        return Response({'status': 'wallet topped up', 'wallet_balance': vendor.wallet_balance})

class IDCardViewSet(viewsets.ModelViewSet):
    queryset = IDCard.objects.all()
    serializer_class = IDCardSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def create_from_pdf(self, request):
        pdf = request.FILES.get('pdf')
        if not pdf:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        info = extract_data_from_pdf(pdf)
        if not info or 'card_number' not in info:
            return Response({'error': 'Failed to extract card number from PDF'}, status=status.HTTP_400_BAD_REQUEST)
        id_card = IDCard.objects.create(
            card_number=info['card_number'],
            name=info.get('name', ''),
            dob=info.get('dob'),
            expiry_date=info.get('expiry_date', None)  # Handle optional expiry_date
        )
        return Response(IDCardSerializer(id_card).data)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

class PrinterViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def list_printers(self, request):
        printers = get_connected_printers()
        return Response({'printers': printers})

    @action(detail=False, methods=['post'])
    def print_id_card(self, request):
        printer_name = request.data.get('printer_name')
        id_card_info = request.data.get('id_card_info')
        if not printer_name or not id_card_info:
            return Response({'error': 'Printer name and ID card info are required'}, status=status.HTTP_400_BAD_REQUEST)
        printer = Printer(printer_name)
        result = printer.print_id_card(id_card_info)
        return Response({'result': result})

class PhotoEnhancementViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def enhance_photo(self, request):
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'error': 'Photo is required'}, status=status.HTTP_400_BAD_REQUEST)
        enhanced_photo = enhance_photo(photo)
        response = HttpResponse(content_type="image/jpeg")
        enhanced_photo.save(response, "JPEG")
        return response

@login_required
def dashboard(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
    except Vendor.DoesNotExist:
        return render(request, 'dashboard.html', {'error': 'Vendor profile not found'}, status=404)
    
    context = {
        'wallet_balance': vendor.wallet_balance
    }
    return render(request, 'dashboard.html', context)

def test_view(request):
    return render(request, 'test.html')



@login_required
def id_card_input(request):
    if request.method == 'POST':
        form = UploadPDFForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_pdf(pdf_path, password)

                # Debugging: Print the extracted data
                print("Extracted Data:", data)

                if not data:
                    return HttpResponse("Failed to extract information from the PDF.", status=400)

                # Ensure all required fields are present
                required_fields = ['name', 'dob', 'card_number']
                missing_fields = [field for field in required_fields if field not in data or not data[field]]

                if missing_fields:
                    return HttpResponse(f"Missing required fields: {', '.join(missing_fields)}", status=400)

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)
                
                id_card_format = get_object_or_404(IDCardFormat, format_name='Aadhar Card Format')
                id_card = IDCard.objects.create(
                    user=user,
                    name=data['name'],
                    dob=data['dob'],
                    card_number=data['card_number'],
                    vendor=vendor,
                    id_format=id_card_format,
                    expiry_date=data.get('expiry_date', None)  # Handle optional expiry_date
                )
                front_image_path, back_image_path = generate_id_card_image(id_card, data)
                return HttpResponse(f'ID Card generated successfully. Front: {front_image_path}, Back: {back_image_path}')
            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'id_card_input.html', {'form': form})

@login_required
def id_card_output(request):
    id_cards = IDCard.objects.filter(user=request.user)
    return render(request, 'id_card_output.html', {'id_cards': id_cards})


def validate_date_format(date_str):
    try:
        datetime.strptime(date_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def parse_date_ddmmyyyy(date_str):
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        raise ValidationError(f"Date format is invalid. Expected DD/MM/YYYY, got {date_str}")

from django.db import IntegrityError

@login_required
def upload_pdf(request):
    if request.method == 'POST':
        form = UploadPDFForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                # Extract data from the PDF
                data = extract_data_from_pdf(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_pdf')

                # Ensure all required fields are present
                required_fields = ['name', 'dob', 'card_number']
                missing_fields = [field for field in required_fields if field not in data or not data[field]]

                if missing_fields:
                    return HttpResponse(f"Missing required fields: {', '.join(missing_fields)}", status=400)

                # Parse and validate date format
                dob = data.get('dob', '')
                if dob:
                    try:
                        parsed_dob = parse_date_ddmmyyyy(dob)
                        data['dob'] = parsed_dob  # Update the data dictionary with the parsed date
                    except ValidationError as e:
                        return HttpResponse(f"Date format is invalid: {str(e)}", status=400)
                else:
                    return HttpResponse("Date of birth is required.", status=400)

                user = request.user  # Get the logged-in user
                vendor = get_object_or_404(Vendor, user=user)  # Get the vendor associated with the user
                wallet = get_object_or_404(Wallet, user=user)  # Get the wallet for the user

                # Check if the card_number already exists for the user
                id_card_instance = IDCard.objects.filter(user=user, card_number=data['card_number']).first()

                # Step 1: Deduct amount from vendor's wallet only if the card does not exist
                deduction_amount = Decimal('2.00')  # Define the deduction amount as Decimal

                if not id_card_instance:
                    if wallet.deduct_amount(deduction_amount):  # Deduct amount
                        wallet.refresh_from_db()  # Fetch the updated balance after deduction
                        vendor.wallet_balance = wallet.balance  # Sync vendor's balance with wallet
                        vendor.save()  # Save the updated wallet balance

                        # Create an entry in the api_wallet_log table for the deduction
                        ApiWallet.objects.create(
                            user=user,
                            balance=wallet.balance,
                            deduction_amount=deduction_amount,
                            card_number=data['card_number'],
                            deduction_date_time=timezone.now()  # Ensure this is correct
                        )

                        # Log the transaction
                        logger.info(f"Wallet transaction created: User {user.id}, Card Number: {data['card_number']}, Amount: {deduction_amount}")

                        # Fetch the IDCardFormat instance you want to use
                        id_card_format = get_object_or_404(IDCardFormat, format_name='Aadhar Card Format')  # Ensure it exists

                        # Create a new IDCard instance
                        id_card_instance = IDCard.objects.create(
                            user=user,
                            name=data['name'],
                            dob=data['dob'],
                            card_number=data['card_number'],
                            vendor=vendor,
                            id_format=id_card_format,
                            expiry_date=data.get('expiry_date', None)  # Handle optional expiry_date
                        )
                    else:
                        messages.error(request, "Insufficient balance in your wallet to process this transaction.")
                        return redirect('upload_pdf')  # Redirect back if insufficient balance
                else:
                    logger.info(f"ID card already exists for user {user.id} with card number {data['card_number']}, skipping wallet deduction and card creation.")

                # Convert dates to string for JSON serialization
                data['dob'] = data['dob'].strftime('%Y-%m-%d') if isinstance(data['dob'], date) else data['dob']
                if 'expiry_date' in data and data['expiry_date'] is not None:
                    data['expiry_date'] = data['expiry_date'].strftime('%Y-%m-%d')

                # Step 3: Store the extracted data (ID Card Data) regardless of card existence
                IDCardData.objects.create(user=user, id_card=id_card_instance, data=data)

                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form,
                    'pdf_upload_id': pdf_upload.id,  # Pass the PDF upload ID to the context for future reference
                }
                return render(request, 'review_data.html', context)

            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")  # Log the error
                messages.error(request, f"An error occurred: {str(e)}")
                return redirect('upload_pdf')
    else:
        form = UploadPDFForm()
    return render(request, 'upload_pdf.html', {'form': form})





@login_required
def wallet(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
    except Vendor.DoesNotExist:
        return render(request, 'wallet.html', {'error': 'Vendor not found'}, status=404)
    
    context = {
        'wallet_balance': vendor.wallet_balance
    }
    return render(request, 'wallet.html', context)


@login_required
def wallet_view(request):
    user = request.user

    # Debugging output to check user ID
    logger.info(f"Current user ID: {user.id}")

    # Get wallet logs specifically for the current user
    wallet_logs = ApiWallet.objects.filter(user=user)
    
    # Debugging output to check the count of logs
    logger.info(f"Fetched wallet logs for user {user.id}: {wallet_logs.count()} entries found.")

    # Get the current wallet balance
    try:
        vendor = Vendor.objects.get(user=user)
        wallet_balance = vendor.wallet_balance
    except Vendor.DoesNotExist:
        wallet_balance = 0  # Default to 0 if vendor does not exist

    # Create context
    context = {
        'wallet_balance': wallet_balance,
        'wallet_logs': wallet_logs if wallet_logs.exists() else None,
    }

    return render(request, 'wallet.html', context)







   




@login_required
def review_data(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')  # Get the uploaded PDF file
        if pdf_file:
            # Process the PDF
            pdf_path = pdf_file.temporary_file_path()
            data = extract_data_from_pdf(pdf_path)

            # Encode profile photos in base64
            profile_photos = []
            for img_bytes in data.get('images', []):
                base64_img = base64.b64encode(img_bytes).decode('utf-8')
                profile_photos.append(base64_img)

            context = {
                'name': data.get('name'),
                'dob': data.get('dob'),
                'card_number': data.get('card_number'),
                'profile_photos': profile_photos,  # Pass photos to the template
                'pdf_upload_id': request.POST.get('pdf_upload_id', '')  # Handle the PDF upload ID
            }

            return render(request, 'review_data.html', context)
    
    # Render the review_data template without data if not a POST request
    return render(request, 'review_data.html')

@login_required
def save_id_card(request):
    if request.method == 'POST':
        pdf_upload_id = request.POST.get('pdf_upload_id')
        pdf_upload = get_object_or_404(PDFUpload, id=pdf_upload_id)
        data = extract_data_from_pdf(pdf_upload.pdf_file.path, pdf_upload.password)

        user = request.user
        vendor = get_object_or_404(Vendor, user=user)
        id_card_format = get_object_or_404(IDCardFormat, format_name='Aadhar Card Format')
        id_card = IDCard.objects.create(
            user=user,
            name=data['name'],
            dob=data['dob'],
            card_number=data['card_number'],
            vendor=vendor,
            id_format=id_card_format,
            expiry_date=data.get('expiry_date', None)  # Handle optional expiry_date
        )

        front_image_path, back_image_path = generate_id_card_image(id_card, data)
        return HttpResponse(f'ID Card generated successfully. Front: {front_image_path}, Back: {back_image_path}')


# backend/id_card_generator/api/views.py
def edit_id_card(request):
    # Logic to retrieve and edit ID card data
    # Provide a form to edit the existing data
    pass






@login_required
def upload_pan(request):
    if request.method == 'POST':
        form = UploadPANForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_pan(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_pan')

                # Ensure all required fields are present
                required_fields = ['name', 'dob', 'card_number']
                missing_fields = [field for field in required_fields if field not in data or not data[field]]

                if missing_fields:
                    return HttpResponse(f"Missing required fields: {', '.join(missing_fields)}", status=400)

                # Parse and validate date format
                dob = data.get('dob', '')
                if dob:
                    try:
                        parsed_dob = parse_date_ddmmyyyy(dob)
                        data['dob'] = parsed_dob  # Update the data dictionary with the parsed date
                    except ValidationError as e:
                        return HttpResponse(f"Date format is invalid: {str(e)}", status=400)
                else:
                    return HttpResponse("Date of birth is required.", status=400)

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)

                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_pan.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_pan.html', {'form': form})


@login_required
def upload_election(request):
    if request.method == 'POST':
        form = UploadelectionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_election(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_election')

                # Ensure all required fields are present
                required_fields = ['name', 'dob', 'card_number']
                missing_fields = [field for field in required_fields if field not in data or not data[field]]

                if missing_fields:
                    return HttpResponse(f"Missing required fields: {', '.join(missing_fields)}", status=400)

               

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)

                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_election.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_election.html', {'form': form})


@login_required
def upload_ayushman(request):
    if request.method == 'POST':
        form = UploadAyushmanForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_ayushman(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_ayushman')

                # Ensure all required fields are present
                required_fields = ['name', 'dob', 'card_number']
                missing_fields = [field for field in required_fields if field not in data or not data[field]]

                if missing_fields:
                    return HttpResponse(f"Missing required fields: {', '.join(missing_fields)}", status=400)

                

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)

                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_ayushman.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_ayushman.html', {'form': form})


@login_required
def upload_eshram(request):
    if request.method == 'POST':
        form = UploadEshramForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_eshram(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_eshram')

                

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)
                
                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_eshram.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_eshram.html', {'form': form})


@login_required
def upload_abha(request):
    if request.method == 'POST':
        form = UploadAbhaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_abha(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_abha')

                

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)
                
                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_abha.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_abha.html', {'form': form})

@login_required
def upload_aadhaar(request):
    if request.method == 'POST':
        form = UploadaadhaarForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pdf_upload = form.save()
                pdf_path = pdf_upload.pdf_file.path
                password = form.cleaned_data.get('password', '')

                data = extract_data_from_aadhaar(pdf_path, password)

                if 'error' in data:
                    messages.error(request, data['error'])
                    return redirect('upload_aadhaar')

                # Parse and validate date format
                dob = data.get('dob', '')
                if dob:
                    try:
                        parsed_dob = parse_date_ddmmyyyy(dob)
                        data['dob'] = parsed_dob  # Update the data dictionary with the parsed date
                    except ValidationError as e:
                        return HttpResponse(f"Date format is invalid: {str(e)}", status=400)
                else:
                    return HttpResponse("Date of birth is required.", status=400)

                

                user = request.user
                vendor = get_object_or_404(Vendor, user=user)
                
                # Render a review template with extracted data
                context = {
                    'data': data,
                    'form': form
                }
                return render(request, 'review_aadhaar.html', context)

            except Exception as e:
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = UploadPDFForm()
    return render(request, 'upload_aadhaar.html', {'form': form})





