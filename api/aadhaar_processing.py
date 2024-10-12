# id_card_generator/api/aadhaar_processing.py
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
from googletrans import Translator
import unicodedata

def extract_data_from_aadhaar(pdf_path, password=None):
    data = {}
    images = []
    translator = Translator()

    try:
        doc = fitz.open(pdf_path)

        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    return {'error': 'Wrong password'}
            else:
                return {'error': 'Password required'}

        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += extract_text_from_page(page)

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                images.append((img_str, image))

        data['address_hindi'] = extract_hindi_address(full_text)

        english_address_match = re.search(
            r'Address[:\s]*(.*?)(?=\n\d{6}\s|\n(?:VID|Date:|Signature|$))',
            full_text,
            re.DOTALL
        )
        
        if english_address_match:
            address = english_address_match.group(1).strip()
            pincode_match = re.search(r'\b\d{6}\b', address)
            if pincode_match:
                pincode_end_index = pincode_match.end()
                data['address'] = address[:pincode_end_index].strip()
            else:
                data['address'] = address
            
            hindi_translation = translator.translate(address[:pincode_end_index].strip(), src='en', dest='hi').text
            data['address_english'] = address
            data['address_hindi_translated'] = hindi_translation

        card_number_match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b', full_text)
        if card_number_match:
            data['card_number'] = card_number_match.group(0).replace(' ', '')

        name_match = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b', full_text)
        for potential_name1 in name_match:
            if "Enrolment" not in potential_name1 and "VID" not in potential_name1 and "DOB" not in potential_name1:
                data['name'] = potential_name1
                break

        name_match_english = re.findall(r'\b[A-Z][a-z]*(?:\s[A-Z][a-z]*)+', full_text)
        for potential_name in name_match_english:
            if "Enrolment" not in potential_name and "VID" not in potential_name and "DOB" not in potential_name:
                data['name_english'] = potential_name
                break

        data['hindi_name'] = extract_hindi_name(full_text)

        dob_match = re.search(r'DOB:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if dob_match:
            data['dob'] = dob_match.group(1)

        vid_match = re.search(r'\bVID\s*:\s*(\d{4}\s\d{4}\s\d{4}\s\d{4})\b', full_text)
        if vid_match:
            data['vid'] = vid_match.group(1).replace(' ', '')

        mobile_match = re.search(r'\bMobile:\s*(\d{10})\b', full_text)
        if mobile_match:
            data['mobile'] = mobile_match.group(1)

        gender_mapping = {
            'Male': 'पुरुष',
            'Female': 'महिला'
        }

        gender_match = re.search(r'\b(Male|Female)\b', full_text, re.IGNORECASE)
        if gender_match:
            english_gender = gender_match.group(0).capitalize()
            data['gender_english'] = english_gender
            data['gender_hindi'] = gender_mapping.get(english_gender, 'Unknown')

        # Extract issued date
        issued_date_match = re.search(r'Aadhaar\s+no\.\s+issued\s*:\s*(.*?)\n', full_text)
        if issued_date_match:
            data['issued_date'] = issued_date_match.group(1).strip()
        
        # Extract details date
        details_date_match = re.search(r'Details\s+as\s+on\s*:\s*(.*?)\n', full_text)
        if details_date_match:
            data['details_date'] = details_date_match.group(1).strip()

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                data['profile_photo'] = img_str

            decoded_objects = decode(open_cv_image)
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


def extract_hindi_name(full_text):
    # More general pattern to capture Hindi names
    hindi_name_pattern = re.compile(r'To\s*\n\s*([\u0900-\u097F\s]+)', re.DOTALL)
    
    hindi_name_matches = hindi_name_pattern.findall(full_text)
    
    if hindi_name_matches:
        # Example: Return the first match or refine based on specific criteria
        raw_hindi_name = hindi_name_matches[0].strip()
        print(f"Raw Hindi Name Extracted: {raw_hindi_name}")
        
        normalized_hindi_name = unicodedata.normalize('NFC', raw_hindi_name)
        print(f"Normalized Hindi Name: {normalized_hindi_name}")
        
        return normalized_hindi_name
    else:
        return None



def extract_text_from_page(page):
    full_text = ""
    text_blocks = page.get_text("blocks")
    for block in text_blocks:
        block_text = block[4]
        rotation = block[6]
        if rotation in [90, 270]:
            block_text = handle_vertical_text(block_text, rotation)
        full_text += block_text + "\n"
    return full_text

def handle_vertical_text(text, rotation):
    if rotation == 90:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]
        text = '\n'.join(lines)
    elif rotation == 270:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]
        text = '\n'.join(lines)
    return text

def extract_hindi_address(full_text):
    # Print full text to debug
    print("Full Text:\n", full_text)
    
    # Regular expression to capture Hindi text before 'Address:'
    hindi_address_pattern = re.compile(
        r'([\u0900-\u097F\s,०-९\-]+)\s*Address:',
        re.DOTALL
    )
    
    hindi_address_match = hindi_address_pattern.search(full_text)
    
    # Debug output to check if the pattern matches anything
    if hindi_address_match:
        print("Hindi Address Match Found:")
        print(hindi_address_match.group(1))
        return hindi_address_match.group(1).strip()
    else:
        print("No Hindi Address Found")
        return "No Hindi address found"