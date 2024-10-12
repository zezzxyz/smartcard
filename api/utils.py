# api/utils.py
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from PyPDF2 import PdfFileReader
import io
import re
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime
from django.core.files.storage import default_storage
from django.conf import settings
import os

def validate_date_format(date_str):
    """Validate if the date is in DD/MM/YYYY format."""
    try:
        datetime.strptime(date_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def extract_data_from_pdf(pdf_path, password=''):
    try:
        doc = fitz.open(pdf_path)
        if password:
            doc.authenticate(password)
        page = doc.load_page(0)
        text = page.get_text("text")
        print("Extracted Text:", text)  # Debugging line

        image = extract_image_from_pdf(page, doc)
        qr_code = extract_qr_code_from_pdf(page, doc)

        dob_raw = extract_dob(text)
        dob = dob_raw
        #dob = convert_date_format(dob_raw) if dob_raw else None

        data = {
            'name': extract_name(text),
            'dob': dob,
            'card_number': extract_card_number(text),
            'image': image,
            'qr_code': qr_code,
            'expiry_date': None,  # Set expiry_date to None if not present
        }
        print("Extracted Data:", data)  # Debugging line
        return data
    except fitz.FitzError as e:
        print(f"Error with PyMuPDF: {str(e)}")
    except Exception as e:
        print(f"General Error: {str(e)}")
    return {}






    


    

def extract_image_from_pdf(page, doc):
    try:
        for image_index in range(len(page.get_images(full=True))):
            image_list = page.get_images(full=True)
            xref = image_list[image_index][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            return image
    except Exception as e:
        print(f"Error extracting image: {str(e)}")
        return None

def extract_qr_code_from_pdf(page, doc):
    try:
        for image_index in range(len(page.get_images(full=True))):
            image_list = page.get_images(full=True)
            xref = image_list[image_index][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            qr_codes = decode(image)
            if qr_codes:
                return qr_codes[0].data.decode('utf-8')
        return None
    except Exception as e:
        print(f"Error extracting QR code: {str(e)}")
        return None

#def extract_name(text):
#    match = re.search(r"Name:\s*(.*)", text)
#    return match.group(1).strip() if match else None

#def extract_name(text):
#    match = re.search(r"(?:(?:नामांकन|Enrolment No.)[:\s]*\d+\/\d+\/\d+\s*)?(.+?)\nC/O", text, re.DOTALL)
#    if match:
#        name_block = match.group(1).strip().split("\n")
#        name_lines = [line for line in name_block if not line.strip().startswith("C/O")]
#        if name_lines:
#            return name_lines[-1].strip()  # Return the last non-"C/O" line as the name
#    return None

def extract_name(text):
    print("Text for Name Extraction:", text)  # Debugging line
    match = re.search(r"(?:(?:नामांकन|Enrolment No.)[:\s]*\d+\/\d+\/\d+\s*)?(.+?)\nC/O", text, re.DOTALL)
    if match:
        name_block = match.group(1).strip().split("\n")
        print("Extracted Name Block:", name_block)  # Debugging line
        name_lines = [line for line in name_block if not line.strip().startswith("C/O")]
        if name_lines:
            return name_lines[-1].strip()
    return None

def extract_dob(text):
    print("Text for DOB Extraction:", text)  # Debugging line
    match = re.search(r"ज‼म\s*ितिथ/DOB[:\s]*(\d{2}/\d{2}/\d{4})", text)
    if not match:
        match = re.search(r"DOB[:\s]*(\d{2}/\d{2}/\d{4})", text)
    if not match:
        match = re.search(r"DOB[:\s]*(\d{2}-\d{2}-\d{4})", text)
    if not match:
        match = re.search(r"जन्म तिथि[:\s]*(\d{2}/\d{2}/\d{4})", text)
    if not match:
        match = re.search(r"जन्म तिथि[:\s]*(\d{2}-\d{2}-\d{4})", text)
    return match.group(1) if match else None
    print("Extracted DOB:", dob)  # Debugging line
    return dob
#def extract_dob(text):
#    match = re.search(r"DOB:\s*(\d{2}-\d{2}-\d{4})", text)
#    return match.group(1).strip() if match else None

def extract_card_number(text):
    print("Text for Card Number Extraction:", text)  # Debugging line
    match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b', text)
    return match.group(0).replace(' ', '').strip() if match else None

def enhance_photo(photo):
    image = Image.open(photo)
    enhancer = ImageEnhance.Color(image)
    enhanced_image = enhancer.enhance(2.0)
    return enhanced_image

def generate_id_card_image(id_card, data):
    # Define the paths for templates
    front_template_path = os.path.join(settings.BASE_DIR, 'static', 'id_card_front_template.png')
    back_template_path = os.path.join(settings.BASE_DIR, 'static', 'id_card_back_template.png')

    if not os.path.exists(front_template_path):
        raise FileNotFoundError(f"Front template file not found: {front_template_path}")
    if not os.path.exists(back_template_path):
        raise FileNotFoundError(f"Back template file not found: {back_template_path}")

    # Use default_storage.open to read the files
    with default_storage.open(front_template_path) as front_file, \
         default_storage.open(back_template_path) as back_file:
        # Your existing code to generate ID card images goes here.
        # For example, if you're using PIL for image manipulation:
        from PIL import Image

        front_image = Image.open(front_template_path)
        back_image = Image.open(back_template_path)

        # Add code to customize the images using `id_card` and `data`

        # Save the final images to paths where they can be accessed
        front_image_path = os.path.join(settings.MEDIA_ROOT, f'front_{id_card.id}.png')
        back_image_path = os.path.join(settings.MEDIA_ROOT, f'back_{id_card.id}.png')

        front_image.save(front_image_path)
        back_image.save(back_image_path)

        return front_image_path, back_image_path




def test_extract_name():
    text = "Pawan Gunilal Bopche"
    #print("Extracted Name:", extract_name(text))

def test_extract_dob():
    text = "08/10/1990"
    #print("Extracted DOB:", extract_dob(text))

def test_extract_card_number():
    text = "6021 8729 1111"
    #print("Extracted Card Number:", extract_card_number(text))

test_extract_name()
test_extract_dob()
test_extract_card_number()




