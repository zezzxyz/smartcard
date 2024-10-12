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

def extract_data_from_pan(pdf_path, password=None):
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

                # Detect signature or thumbprint based on size or other characteristics
                width, height = image.size
                if 50 < width < 400 and 20 < height < 200:  # Adjust these thresholds based on your documents
                    data['signature_or_thumbprint'] = img_str

        # Extract Hindi address
        hindi_address = extract_hindi_address(full_text)
        data['address_hindi'] = hindi_address

        # Extract card number in the format of 5 capital letters, 4 digits, and 1 capital letter (e.g., MJMPS9952C)
        card_number_match = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', full_text)
        if card_number_match:
            data['card_number'] = card_number_match.group(0)

        # Extract primary name
        name_pattern = re.compile(r'\b[A-Z]+\s+[A-Z]+(?:\s+[A-Z]+)?\b')
        name_match = name_pattern.findall(full_text)
        if name_match:
            # Assuming the first match is the primary name
            data['name'] = name_match[0].strip()

        # Extract father's name
        father_name_pattern = re.compile(r'\b[A-Z]+\s+[A-Z]+(?:\s+[A-Z]+)?\b')

        # Find all possible names
        all_names = father_name_pattern.findall(full_text)

        # Remove the primary name from the list of all names
        if 'name' in data:
            all_names = [name for name in all_names if name != data['name']]

        # If any names are left, assume the first one is the father's name
        if all_names:
            data['father_name'] = all_names[0].strip()

        # Extract Hindi name
        hindi_name_pattern = re.compile(r'To\s*\n\s*([\u0900-\u097F\s]+)', re.DOTALL)
        hindi_name_match = hindi_name_pattern.search(full_text)
        if hindi_name_match:
            data['hindi_name'] = hindi_name_match.group(1).strip()
        else:
            data['hindi_name'] = None

        # Extract date of birth in the format dd/mm/yyyy
        dob_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', full_text)
        if dob_match:
            data['dob'] = dob_match.group(1)

        # Extract English address
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

        # Extract VID
        vid_match = re.search(r'\bVID\s*:\s*(\d{4}\s\d{4}\s\d{4}\s\d{4})\b', full_text)
        if vid_match:
            data['vid'] = vid_match.group(1).replace(' ', '')

        # Extract mobile number
        mobile_match = re.search(r'\bMobile:\s*(\d{10})\b', full_text)
        if mobile_match:
            data['mobile'] = mobile_match.group(1)

        # Define mappings for English to Hindi gender
        gender_mapping = {
            'Male': 'पुरुष',
            'Female': 'महिला'
        }

        # Extract gender in English
        gender_match = re.search(r'\b(Male|Female)\b', full_text, re.IGNORECASE)

        if gender_match:
            english_gender = gender_match.group(0).capitalize()
            data['gender_english'] = english_gender
            data['gender_hindi'] = gender_mapping.get(english_gender, 'Unknown')

        # Face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                # Assuming the first face is the profile photo
                data['profile_photo'] = img_str
                break  # Stop after finding the first face (assuming one profile photo per document)

            # Decode QR code
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
    if rotation == 90:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]  # Reverse each line to correct vertical text
        text = '\n'.join(lines)
    elif rotation == 270:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]  # Reverse each line to correct vertical text
        text = '\n'.join(lines)
    return text

def extract_hindi_address(full_text):
    hindi_address_pattern = re.compile(
        r'पता[:\s]*([\u0900-\u097F\s,०-९\-]+(?:\s+\d{6})?)',
        re.DOTALL
    )
    hindi_address_match = hindi_address_pattern.search(full_text)
    if hindi_address_match:
        return hindi_address_match.group(1).strip()
    else:
        return "No Hindi address found"
