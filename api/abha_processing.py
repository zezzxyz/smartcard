import re
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import cv2
import numpy as np
from pyzbar.pyzbar import decode  # Barcode reader library
import qrcode
import pytesseract

def extract_data_from_abha(pdf_path, password=None):
    data = {}
    images = []

    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)

        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    return {'error': 'Wrong password'}
            else:
                return {'error': 'Password required'}

        # Extract text and images from each page
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text with vertical text handling
            full_text += extract_text_from_page(page)

            # Extract images
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Convert image to base64 string
                image = Image.open(io.BytesIO(image_bytes))
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                images.append((img_str, image))

                # Face detection
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                open_cv_image = np.array(image.convert('RGB'))
                open_cv_image = open_cv_image[:, :, ::-1].copy()
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                if len(faces) > 0:
                    data['profile_photo'] = img_str
                    break  # Stop after finding the first face (assuming one profile photo per document)

        # Extract ABHA number
        abha_number_match = re.search(r'\b91-\d{4}-\d{4}-\d{4}\b', full_text)
        if abha_number_match:
            data['abha_number'] = abha_number_match.group(0)

        # Extract ABHA address
        abha_address_match = re.search(r'\b\d{14}@abdm\b', full_text)
        if abha_address_match:
            data['abha_address'] = abha_address_match.group(0)

        # Extract name (mixed case name support)
        name_pattern = re.compile(r'\b[A-Za-z]+\s+[A-Za-z]+(?:\s+[A-Za-z]+)?\b')
        name_match = name_pattern.findall(full_text)
        if name_match:
            data['name'] = name_match[0].strip()

        # Extract Hindi name
        hindi_name_pattern = re.compile(r'([\u0900-\u097F\s]+)', re.DOTALL)
        hindi_name_match = hindi_name_pattern.findall(full_text)
        if hindi_name_match:
            data['hindi_name'] = hindi_name_match[0].strip()

        # Extract date of birth
        dob_match = re.search(r'\b(\d{2}-\d{2}-\d{4})\b', full_text)
        if dob_match:
            data['dob'] = dob_match.group(1)

        # Extract mobile number
        mobile_match = re.search(r'\b\d{10}\b', full_text)
        if mobile_match:
            data['mobile'] = mobile_match.group(0)

        # Extract gender (improved regex for abbreviations)
        gender_match = re.search(r'\b(Male|Female|M|F)\b', full_text, re.IGNORECASE)
        if gender_match:
            english_gender = gender_match.group(0).capitalize()
            data['gender'] = english_gender if len(english_gender) > 1 else ('Male' if english_gender == 'M' else 'Female')

        # QR Code Detection with Image Preprocessing
        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            gray = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)[1]
            decoded_objects = decode(gray)

            for obj in decoded_objects:
                qr_code_data = obj.data.decode('utf-8')
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_code_data)
                qr.make(fit=True)
                qr_img = qr.make_image(fill='black', back_color='white')
                buffered = io.BytesIO()
                qr_img.save(buffered, format="PNG")
                qr_img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                data['qr_code_image'] = qr_img_str
                break

    except Exception as e:
        print(f"Error extracting data from PDF: {e}")

    return data


def extract_text_from_page(page):
    """ Extracts and processes text from a PDF page. Handles vertical text. """
    full_text = ""
    
    # Extract text blocks from the page
    text_blocks = page.get_text("blocks")
    for block in text_blocks:
        block_text = block[4]
        # Check if the block has vertical text (needs rotation adjustment)
        if block[6] != 0:  # Check if text block is rotated
            block_text = handle_vertical_text(block_text, block[6])
        full_text += block_text + "\n"
    
    return full_text

def handle_vertical_text(text, rotation):
    """ Adjusts the text based on its rotation to handle vertical text. """
    if rotation == 90 or rotation == 270:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]  # Reverse each line to correct vertical text
        text = '\n'.join(lines)
    return text
